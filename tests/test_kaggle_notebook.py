"""Runs kaggle/benchmark_notebook.py against a local STAND-IN for `kaggle_benchmarks`.

This does not verify Kaggle's API (nobody here can run that without an
account). It verifies that our own notebook code is internally consistent:
it executes end to end, scores what the model said, writes the resumable
record file, never repeats a cached call, and stops at the session budget.
The stand-in implements only what the library's docs describe.
"""
import contextlib
import json
import sys
import types
from pathlib import Path

import pytest

from phantom_args.prompt import CONDITIONS, build_prompt

ROOT = Path(__file__).resolve().parent.parent
NOTEBOOK = ROOT / "kaggle" / "benchmark_notebook.py"
ITEMS = [json.loads(line) for line in (ROOT / "data" / "items.jsonl").read_text(encoding="utf-8").splitlines() if line]


class FakeUsage:
    def __init__(self, nano):
        self.input_tokens, self.output_tokens, self.total_cost_nanodollars = 330, 45, nano


class FakeLLM:
    """Answers with the item's trap call on enum_pressure items and the reference call elsewhere."""

    def __init__(self, name, cost_nano=200_000):
        self.name, self.cost_nano, self.calls = name, cost_nano, 0
        self.by_prompt = {build_prompt(it, c): it for it in ITEMS for c in CONDITIONS}
        self.extra = []

    def prompt(self, text, temperature=None, extra_api_params=None):     # kaggle-benchmarks 0.6.1 has extra_api_params
        self.calls += 1
        self.extra.append(extra_api_params)
        item = self.by_prompt[text]
        call = item["trap"] if item["family"] == "enum_pressure" else item["reference"]
        FakeKbench.current_chat.usage = FakeUsage(self.cost_nano)
        return "```json\n" + json.dumps(call) + "\n```"


class FakeKbench(types.ModuleType):
    current_chat = None


def make_stub(llm):
    kb = FakeKbench("kaggle_benchmarks")

    class Run:
        def __init__(self, result):
            self.result, self.passed = result, True

    class Task:
        def __init__(self, fn):
            self.fn = fn

        def run(self, llm=None, *args, **kwargs):
            return Run(self.fn(llm, *args, **kwargs))

        def evaluate(self, **kwargs):
            raise NotImplementedError("the stand-in has no evaluate(); the notebook must fall back to its plain loop")

    def task(name=None, *, description=None, version=1, store_task=True, store_run=True):   # kaggle-benchmarks 0.6.1
        return lambda fn: Task(fn)

    @contextlib.contextmanager
    def new(name):
        chat = types.SimpleNamespace(usage=None, messages=[])
        FakeKbench.current_chat = chat
        yield chat

    @contextlib.contextmanager
    def enable_cache():
        yield

    kb.task = task
    kb.llm = llm
    kb.llms = {llm.name: llm}
    kb.chats = types.SimpleNamespace(new=new)
    kb.client = types.SimpleNamespace(enable_cache=enable_cache)
    kb.assertions = types.SimpleNamespace(assert_true=lambda *a, **k: None, assert_fail=lambda *a, **k: None)
    return kb


def execute(tmp_path, monkeypatch, llm, **overrides):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setitem(sys.modules, "kaggle_benchmarks", make_stub(llm))
    source = NOTEBOOK.read_text(encoding="utf-8")
    for name, value in overrides.items():
        marker = f"\n{name} = "
        start = source.index(marker) + 1
        end = source.index("\n", start)
        source = source[:start] + f"{name} = {value!r}" + source[end:]
    ns = {"__name__": "notebook"}
    exec(compile(source, str(NOTEBOOK), "exec"), ns)
    return ns


def test_notebook_runs_scores_and_resumes(tmp_path, monkeypatch, capsys):
    llm = FakeLLM("fake/model-a")
    ns = execute(tmp_path, monkeypatch, llm, SUBSET="full")
    n = len(ITEMS)
    n_enum = sum(it["family"] == "enum_pressure" for it in ITEMS)
    assert llm.calls == n
    assert ns["run"].result == pytest.approx((n - n_enum) / n)        # every enum item answered with its trap
    lines = (tmp_path / "phantom_records.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == n and json.loads(lines[0])["model"] == "fake/model-a"
    assert ns["SESSION"]["spent_usd"] == pytest.approx(n * 200_000 / 1e9)
    out = capsys.readouterr().out
    assert "enum_pressure | out_of_enum" in out and f"({n_enum}/{n_enum};" in out

    # second execution in the same directory: everything is cached, no paid call is repeated
    again = FakeLLM("fake/model-a")
    ns2 = execute(tmp_path, monkeypatch, again, SUBSET="full")
    assert again.calls == 0 and ns2["run"].result == ns["run"].result


def test_auto_subset_falls_back_to_core_for_an_expensive_model(tmp_path, monkeypatch):
    llm = FakeLLM("fake/pricey", cost_nano=10_000_000)                # $0.01 per call -> full set projected at $2.02
    execute(tmp_path, monkeypatch, llm, SUBSET="auto")
    assert llm.calls == sum(bool(it["core"]) for it in ITEMS) == 80


def test_auto_subset_runs_everything_for_a_cheap_model(tmp_path, monkeypatch):
    llm = FakeLLM("fake/cheap", cost_nano=100_000)
    execute(tmp_path, monkeypatch, llm, SUBSET="auto")
    assert llm.calls == len(ITEMS)


def test_items_the_parallel_pass_missed_are_retried(tmp_path, monkeypatch):
    """If evaluate() returns with some rows unanswered (an API error on both attempts), the sequential pass
    answers them, so a run ends with every item answered."""
    llm = FakeLLM("fake/flaky")
    stub = make_stub(llm)
    real_task = stub.task

    def task(name=None, **kw):
        wrap = real_task(name, **kw)

        def deco(fn):
            t = wrap(fn)
            t.evaluate = lambda llm, evaluation_data, **_: [t.fn(llm[0], **row) for i, row in
                                                             enumerate(evaluation_data.to_dict("records")) if i % 2 == 0]
            return t
        return deco

    stub.task = task
    monkeypatch.chdir(tmp_path)
    monkeypatch.setitem(sys.modules, "kaggle_benchmarks", stub)
    ns = {"__name__": "notebook"}
    exec(compile(NOTEBOOK.read_text(encoding="utf-8"), str(NOTEBOOK), "exec"), ns)
    assert llm.calls == len(ITEMS) and len(ns["RECORDS"]) == len(ITEMS)


def test_output_cap_is_sent_and_a_reply_that_hits_it_is_marked(tmp_path, monkeypatch):
    """Kaggle's proxy reserves quota per call from the output cap, so every call carries max_tokens."""
    class Long(FakeLLM):
        def prompt(self, text, temperature=None, extra_api_params=None):
            reply = super().prompt(text, temperature, extra_api_params)
            if self.by_prompt[text]["id"] == "ctrl-01":
                FakeKbench.current_chat.usage.output_tokens = 8000          # used the whole cap
            return reply

    llm = Long("fake/long")
    ns = execute(tmp_path, monkeypatch, llm)
    assert llm.extra and all(e == {"max_tokens": 8000} for e in llm.extra)
    truncated = [k for k, r in ns["RECORDS"].items() if r["truncated"]]
    assert truncated == [("fake/long", "ctrl-01", "neutral")]


def test_older_library_without_extra_api_params_still_runs(tmp_path, monkeypatch):
    class Old(FakeLLM):
        def prompt(self, text, temperature=None):
            return super().prompt(text, temperature)

    llm = Old("fake/old")
    execute(tmp_path, monkeypatch, llm, ONLY_FAMILIES=["control"])
    assert llm.calls == sum(it["family"] == "control" for it in ITEMS) and llm.extra == [None] * llm.calls


def test_default_is_the_full_item_set(tmp_path, monkeypatch):
    """The leaderboard setting: every model answers all items, whatever it costs per call (up to the budget)."""
    llm = FakeLLM("fake/pricey", cost_nano=5_000_000)                 # $0.005 per call -> $1.01 for 202 items
    execute(tmp_path, monkeypatch, llm)
    assert llm.calls == len(ITEMS)


def test_session_budget_stops_paid_calls(tmp_path, monkeypatch):
    llm = FakeLLM("fake/pricey", cost_nano=50_000_000)                # $0.05 per call
    ns = execute(tmp_path, monkeypatch, llm, SUBSET="full", SESSION_BUDGET_USD=1.0)
    assert llm.calls == 20                                            # 20 x $0.05 = $1.00, then nothing more is sent
    assert ns["SESSION"]["spent_usd"] == pytest.approx(1.0)


def test_may_decline_condition_and_family_filter(tmp_path, monkeypatch):
    """CONDITION = "may_decline" sends the third prompt; ONLY_FAMILIES narrows the item set."""
    class Decliner(FakeLLM):
        def prompt(self, text, temperature=None):
            self.calls += 1
            assert "cannot_do" in text                               # the may_decline sentence is in the prompt
            FakeKbench.current_chat.usage = FakeUsage(self.cost_nano)
            return '{"cannot_do": "The tool has no such filter."}'

    llm = Decliner("fake/decliner")
    ns = execute(tmp_path, monkeypatch, llm, SUBSET="full", CONDITION="may_decline",
                 TASK_NAME="phantom_args_may_decline", ONLY_FAMILIES=["repurposing", "matched_control"])
    n_rep = sum(it["family"] == "repurposing" for it in ITEMS)
    n_ctl = sum(it["family"] == "matched_control" for it in ITEMS)
    assert llm.calls == n_rep + n_ctl
    assert ns["TASK_NAME"] == "phantom_args_may_decline"
    assert ns["run"].result == pytest.approx(n_rep / (n_rep + n_ctl))  # declining is right on repurposing, wrong on controls


def test_condition_and_task_name_must_agree(tmp_path, monkeypatch):
    with pytest.raises(AssertionError, match="TASK_NAME"):
        execute(tmp_path, monkeypatch, FakeLLM("fake/x"), CONDITION="may_decline")   # TASK_NAME left at neutral


def test_every_library_call_is_inside_the_adapter_cell():
    """Except the main task's decorator, which the editor's panel must see as a literal `@kbench.task(...)`."""
    source = NOTEBOOK.read_text(encoding="utf-8")
    start = source.index("# ============================================================================= KAGGLE ADAPTER")
    end = source.index("END OF KAGGLE ADAPTER")
    outside = source[:start] + source[end:]
    outside = "\n".join(line for line in outside.splitlines() if not line.lstrip().startswith("#"))  # code, not comments
    decorator = '\n@kbench.task(name="phantom_args_neutral",'
    assert outside.count(decorator) == 1
    assert "kbench" not in outside.replace(decorator, "") and "import kaggle_benchmarks" not in outside
    assert source.count("import kaggle_benchmarks as kbench") == 1
    ipynb = json.loads((ROOT / "kaggle" / "benchmark_notebook.ipynb").read_text(encoding="utf-8"))
    cells = ["".join(c["source"]) for c in ipynb["cells"] if c["cell_type"] == "code"]
    assert sum("kbench" in c for c in cells) == 2                     # the adapter cell and the tasks cell
    assert cells[-1].rstrip().endswith("%choose phantom_args_neutral")


# Learned on Kaggle (2026-10-02, kaggle-benchmarks 0.6.1): the editor's Benchmark Task panel reads the source
# without running it. It shows an f-string task name unresolved, cannot see a task behind a wrapper or an
# indented decorator, and finds no task at all once an HTML/SVG tag name in angle brackets (it was the SVG tag
# "text", in parser.py's docstring) appears anywhere in the notebook.
HTML_SVG_TAGS = {"a", "audio", "b", "base", "body", "br", "button", "canvas", "circle", "code", "div", "embed",
                 "foreignobject", "form", "g", "head", "hr", "html", "i", "iframe", "img", "input", "line", "link",
                 "math", "meta", "noscript", "object", "option", "p", "path", "polygon", "pre", "rect", "script",
                 "select", "source", "span", "style", "svg", "table", "td", "template", "text", "textarea", "th",
                 "title", "tr", "tspan", "video"}
NOTEBOOKS = {"neutral": ROOT / "kaggle" / "benchmark_notebook.ipynb",
             "instructed": ROOT / "kaggle" / "benchmark_notebook_instructed.ipynb",
             "may_decline": ROOT / "kaggle" / "benchmark_notebook_may_decline.ipynb"}


@pytest.mark.parametrize("condition", sorted(NOTEBOOKS))
def test_notebook_follows_the_task_panel_rules(condition):
    import re
    nb = json.loads(NOTEBOOKS[condition].read_text(encoding="utf-8"))
    source = "\n".join("".join(c["source"]) for c in nb["cells"])
    assert re.search(rf'^CONDITION = "{condition}"', source, flags=re.MULTILINE)
    assert re.search(rf'^TASK_NAME = "phantom_args_{condition}" ', source, flags=re.MULTILINE)   # a plain literal
    assert source.rstrip().endswith(f"%choose phantom_args_{condition}")
    assert len(re.findall(rf'^@kbench\.task\(name="phantom_args_{condition}",', source, flags=re.MULTILINE)) == 1
    assert "enable_cache(" not in source.replace("kbench.client.enable_cache()`", "")
    tags = {m.lower() for m in re.findall(r"</?\s*([A-Za-z][A-Za-z0-9]*)[^<>\n]{0,80}>", source)}
    assert not tags & HTML_SVG_TAGS, f"tag-like text hides the task from the editor panel: {sorted(tags & HTML_SVG_TAGS)}"


def cli_task_names(source: str) -> list:
    """What `kaggle b t push` sees (Kaggle CLI 2.2.4, KaggleApi._get_task_names_from_file): every function decorated
    with something named `task`, its name taken from a string-literal `name=` or first argument, else derived from
    the function name. A variable as the name is NOT resolved."""
    import ast
    import re
    source = re.sub(r"^[ \t]*(?:%(?!%)|!)\w[^\n]*$", "", source, flags=re.MULTILINE)
    names = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            func = dec.func if isinstance(dec, ast.Call) else dec
            if not ((isinstance(func, ast.Name) and func.id == "task") or (isinstance(func, ast.Attribute) and func.attr == "task")):
                continue
            name = None
            if isinstance(dec, ast.Call):
                name = next((k.value.value for k in dec.keywords if k.arg == "name" and isinstance(k.value, ast.Constant)), None)
                if name is None and dec.args and isinstance(dec.args[0], ast.Constant):
                    name = dec.args[0].value
            names.append(str(name) if name else node.name.title().replace("_", " "))
    return names


PY_FILES = {"neutral": NOTEBOOK,
            "instructed": ROOT / "kaggle" / "benchmark_notebook_instructed.py",
            "may_decline": ROOT / "kaggle" / "benchmark_notebook_may_decline.py"}


@pytest.mark.parametrize("condition", sorted(PY_FILES))
def test_cli_push_finds_exactly_the_condition_task(condition):
    """`kaggle b t push phantom-args-<condition> -f <file>` requires the slugified decorator name to match."""
    source = PY_FILES[condition].read_text(encoding="utf-8")
    assert cli_task_names(source) == [f"phantom_args_{condition}"]
    import ast
    decorators = [d for n in ast.walk(ast.parse(source)) if isinstance(n, ast.FunctionDef) for d in n.decorator_list
                  if isinstance(d, ast.Call) and getattr(d.func, "attr", None) == "task"]
    for kw in decorators[0].keywords:                  # Kaggle: "Task name and description must each be at most 255 characters."
        if kw.arg in ("name", "description"):
            assert len(ast.literal_eval(kw.value)) <= 255, kw.arg
    assert f'\nTASK_NAME = "phantom_args_{condition}" ' in source and f'\nCONDITION = "{condition}"' in source
    assert "\nkb_choose(TASK_NAME)" in source and "\nrun = kb_run(phantom_args, kb_default_llm())" in source
