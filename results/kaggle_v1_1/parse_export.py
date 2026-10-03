"""Turn the export text of a Kaggle run notebook into per-item labels and tables.

The run notebooks (../../../kaggle-upload/make_run_notebook.py) end with an EXPORT cell. Its lines were read
back from the editor's Table of contents (each line shown as an output heading "Lnnnn <line>"), so the input
here is a text file with those lines, in any surrounding noise; only lines starting "Lnnnn " are used.

    python3 parse_export.py export_raw_*.txt --md tables.md --json labels.json

Codes (one per item, same as the notebook's code_of):
  . clean  s stuffed  l listed enum value  r v1.0 item where a repurposed flag fired (info only)   -> correct
  D decline where declining is right                                                             -> correct
  x valid but fails the item's checks  R repurposed  N decline where the tool could serve the request
  P phantom argument  E out-of-enum  T wrong type  M missing required  O other invalid  W wrong tool
  U unparseable  Q schema fault together with a misuse  - no reply
"""
import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FAMILY_ORDER = ("conventional", "near_miss", "inexpressible", "enum_pressure", "nested", "control",
                "repurposing", "matched_control")
CORRECT = set(".slrD")
FAULTS = set("PETMOWQU")
CANNOT = {"repurposing", "inexpressible", "enum_pressure", "conventional", "nested"}   # decline is right
CAN = {"control", "matched_control", "near_miss"}                                      # decline is wrong
COND = {"n": "neutral", "i": "instructed", "m": "may_decline"}


def load_items():
    items = [json.loads(l) for l in (ROOT / "data" / "items.jsonl").read_text().splitlines() if l.strip()]
    ordered = sorted(items, key=lambda it: (FAMILY_ORDER.index(it["family"]), it["id"]))
    probe = []
    for fam in FAMILY_ORDER:
        fam_items = sorted((it for it in items if it["family"] == fam and it.get("core")), key=lambda it: it["id"])
        probe.extend(fam_items[:1])
    probe_ids = {it["id"] for it in probe}
    return ordered, [it for it in ordered if it["id"] in probe_ids]


def read_lines(paths):
    lines = {}
    for p in paths:
        for raw in Path(p).read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*L(\d{4}) (.*)$", raw)
            if m:
                lines[int(m.group(1))] = m.group(2).rstrip()
    if not lines:
        sys.exit("no 'Lnnnn ' lines found")
    missing = [i for i in range(max(lines) + 1) if i not in lines]
    if missing:
        print(f"WARNING: {len(missing)} export lines missing, first {missing[:10]}", file=sys.stderr)
    return [lines[i] for i in sorted(lines)]


def parse(lines, ordered, probe):
    sec, out = None, {"header": lines[0], "log": [], "cost": {}, "labels": {}, "replies": []}
    models = {}
    pending = None
    for line in lines[1:]:
        if line.startswith("== "):
            sec = line.split()[1]
            continue
        if sec == "LOG":
            out["log"].append(line)
        elif sec == "COST":
            m = re.match(r"(\d\d) (\S+) (\S+) n=(\d+) nocost=(\d+) \$([\d.]+) in=(\S+) out=(\S+) maxout=(\S+) lat=(\S+)", line)
            if m:
                idx, model, cond = m.group(1), m.group(2), m.group(3)
                models[idx] = model
                out["cost"][(model, cond)] = dict(n=int(m.group(4)), nocost=int(m.group(5)), cost=float(m.group(6)),
                                                  mean_in=m.group(7), mean_out=m.group(8), max_out=m.group(9),
                                                  lat=m.group(10))
        elif sec == "LABELS":
            m = re.match(r"(\d\d)([nim])(p?) ([.\w\- ]+)$", line)
            if m and not line.startswith("    "):
                pending = (models.get(m.group(1), m.group(1)), COND[m.group(2)], bool(m.group(3)),
                           m.group(4).replace(" ", ""))
            elif line.strip().startswith("sum") and pending:
                model, cond, is_probe, codes = pending
                want = Counter(dict((kv[0], int(kv[1:])) for kv in line.split()[1:]))
                if Counter(codes) != want:
                    print(f"WARNING: checksum mismatch {model} {cond}: {Counter(codes)} vs {want}", file=sys.stderr)
                tgt = probe if is_probe else ordered
                if len(codes) != len(tgt):
                    print(f"WARNING: {model} {cond}: {len(codes)} codes for {len(tgt)} items", file=sys.stderr)
                out["labels"][(model, cond)] = {"probe": is_probe,
                                                "codes": {it["id"]: k for it, k in zip(tgt, codes)}}
                pending = None
        elif sec == "TABLE":
            out.setdefault("table", []).append(line)
        elif sec == "CORRECT":
            out.setdefault("by_family", []).append(line)
        elif sec == "ITEMS":
            # export v2: "<idx><c> k:id,id  k:id" lists every code other than '.'; everything else is '.'
            m = re.match(r"(\d\d)([nim]) ?(.*)$", line)
            if m:
                model, cond = models.get(m.group(1), m.group(1)), COND[m.group(2)]
                listed = {}
                for part in m.group(3).split():
                    k, _, ids = part.partition(":")
                    for iid in filter(None, ids.split(",")):
                        listed[iid] = k
                ids = {iid for iid in listed}
                is_probe = ids <= {it["id"] for it in probe} and (model, cond) in out["cost"] \
                    and out["cost"][(model, cond)]["n"] <= len(probe)
                tgt = probe if is_probe else ordered
                unknown = ids - {it["id"] for it in tgt}
                if unknown:
                    print(f"WARNING: {model} {cond}: unknown item ids {sorted(unknown)[:5]}", file=sys.stderr)
                out["labels"][(model, cond)] = {"probe": is_probe,
                                                "codes": {it["id"]: listed.get(it["id"], ".") for it in tgt}}
        elif sec == "REPLIES":
            out["replies"].append(line)
    for line in out.get("table", []):          # cross-check the in-kernel table against the reconstructed codes
        m = re.match(r"(\d\d)([nim])p? n=(\d+)/(\d+) correct=(\d+)", line)
        if m:
            key = (models.get(m.group(1), m.group(1)), COND[m.group(2)])
            lab = out["labels"].get(key)
            if lab:
                codes = [k for k in lab["codes"].values() if k != "-"]
                got = (len(codes), sum(k in CORRECT for k in codes))
                if got != (int(m.group(3)), int(m.group(5))):
                    print(f"WARNING: {key}: table says n={m.group(3)} correct={m.group(5)}, codes give {got}",
                          file=sys.stderr)
    return out


def wilson(k, n):
    if not n:
        return (float("nan"), float("nan"))
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (100 * (c - h) / d, 100 * (c + h) / d)


def pct(k, n):
    return f"{100 * k / n:.1f}% ({k}/{n})" if n else "-"


def tables(data, ordered):
    fam_of = {it["id"]: it["family"] for it in ordered}
    full = {k: v for k, v in data["labels"].items() if not v["probe"]}
    models = sorted({m for m, _ in full}, key=lambda m: m.lower())
    md = []

    md.append("## Score (the task's number): correct / items, full set\n")
    md.append("| Model | neutral | instructed | may_decline | cost (3 conditions) |")
    md.append("|---|---|---|---|---|")
    for m in models:
        row, cost = [], 0.0
        for c in ("neutral", "instructed", "may_decline"):
            v = full.get((m, c))
            cost += data["cost"].get((m, c), {}).get("cost", 0.0)
            if not v:
                row.append("-")
                continue
            codes = [k for k in v["codes"].values() if k != "-"]
            row.append(pct(sum(k in CORRECT for k in codes), len(codes)))
        md.append(f"| {m} | " + " | ".join(row) + f" | ${cost:.3f} |")

    md.append("\n## Where it goes wrong, per model and condition\n")
    md.append("Phantom = phantom argument on the four phantom families (conventional, near_miss, inexpressible, "
              "nested). Enum = out-of-enum on enum_pressure. Repurposed = R or Q on the 28 repurposing items. "
              "Controls = correct on control + matched_control. Declines: right = on families the tool cannot serve, "
              "wrong = on control, matched_control, near_miss.\n")
    md.append("| Model | Condition | Phantom | Enum | Repurposed | Any schema fault | Controls | Declined (right) | Declined (wrong) |")
    md.append("|---|---|---|---|---|---|---|---|---|")
    for m in models:
        for c in ("neutral", "instructed", "may_decline"):
            v = full.get((m, c))
            if not v:
                continue
            by = defaultdict(list)
            for iid, k in v["codes"].items():
                if k != "-":
                    by[fam_of[iid]].append(k)
            ph = [k for f in ("conventional", "near_miss", "inexpressible", "nested") for k in by[f]]
            rep = by["repurposing"]
            ctl = by["control"] + by["matched_control"]
            allc = [k for f in by for k in by[f]]
            cannot = [k for f in CANNOT for k in by[f]]
            can = [k for f in CAN for k in by[f]]
            md.append(f"| {m} | {c} | {pct(ph.count('P'), len(ph))} | {pct(by['enum_pressure'].count('E'), len(by['enum_pressure']))} "
                      f"| {pct(sum(k in 'RQ' for k in rep), len(rep))} | {pct(sum(k in FAULTS for k in allc), len(allc))} "
                      f"| {pct(sum(k in CORRECT for k in ctl), len(ctl))} "
                      f"| {pct(cannot.count('D'), len(cannot)) if c == 'may_decline' else '-'} "
                      f"| {pct(can.count('N'), len(can)) if c == 'may_decline' else '-'} |")

    md.append("\n## Correct by family, neutral condition\n")
    md.append("| Model | " + " | ".join(FAMILY_ORDER) + " |")
    md.append("|---|" + "---|" * len(FAMILY_ORDER))
    for m in models:
        v = full.get((m, "neutral"))
        if not v:
            continue
        cells = []
        for f in FAMILY_ORDER:
            ks = [k for iid, k in v["codes"].items() if fam_of[iid] == f and k != "-"]
            cells.append(f"{sum(k in CORRECT for k in ks)}/{len(ks)}")
        md.append(f"| {m} | " + " | ".join(cells) + " |")

    md.append("\n## Repurposing family: must call against may decline (paired by model and item)\n")
    pairs = Counter()
    for m in models:
        a, b = full.get((m, "neutral")), full.get((m, "may_decline"))
        if not (a and b):
            continue
        for iid, k in a["codes"].items():
            if fam_of[iid] != "repurposing" or k == "-" or b["codes"].get(iid, "-") == "-":
                continue
            pairs[(k in "RQ", b["codes"][iid] in "RQ")] += 1
    n = sum(pairs.values())
    if n:
        md.append(f"- {n} pairs. Repurposed only when it had to call: {pairs[(True, False)]}; only when it could "
                  f"decline: {pairs[(False, True)]}; both: {pairs[(True, True)]}; neither: {pairs[(False, False)]}.")
        b, c = pairs[(True, False)], pairs[(False, True)]
        if b + c:
            p = min(1.0, 2 * sum(math.comb(b + c, i) for i in range(0, min(b, c) + 1)) / 2 ** (b + c))
            md.append(f"- Exact McNemar (two-sided) on {b + c} discordant pairs: p = {p:.2g}.")
    return "\n".join(md) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--md")
    ap.add_argument("--json")
    a = ap.parse_args()
    ordered, probe = load_items()
    data = parse(read_lines(a.files), ordered, probe)
    if a.json:
        Path(a.json).write_text(json.dumps({
            "header": data["header"], "log": data["log"],
            "cost": [dict(model=m, cond=c, **v) for (m, c), v in data["cost"].items()],
            "labels": [dict(model=m, cond=c, **v) for (m, c), v in data["labels"].items()],
            "replies": data["replies"]}, indent=1), encoding="utf-8")
    md = tables(data, ordered)
    if a.md:
        Path(a.md).write_text(md, encoding="utf-8")
    else:
        print(md)


if __name__ == "__main__":
    main()
