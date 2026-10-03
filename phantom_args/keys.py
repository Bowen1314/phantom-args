"""API-key loading.

The key is read from a dotenv-style file (or, failing that, from one named
environment variable) and is never printed, logged, or written anywhere.
Only the single requested variable is read; every other key-like variable in
the file or the environment is ignored.
"""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

# A key variable may only ever be sent to its pinned host.
KEY_HOST_PINS = {
    "NEBIUS_API_KEY": "api.tokenfactory.nebius.com",
}


class KeyError_(RuntimeError):
    pass


def load_key(var: str = "NEBIUS_API_KEY", key_file: str | os.PathLike | None = None) -> str:
    """Return the value of `var` from `key_file` (dotenv format) or os.environ."""
    if key_file:
        path = Path(key_file).expanduser()
        if not path.is_file():
            raise KeyError_(f"key file not found: {path}")
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):].lstrip()
            name, sep, value = line.partition("=")
            if not sep or name.strip() != var:
                continue
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            if value:
                return value
        raise KeyError_(f"{var} not found in {path}")
    value = os.environ.get(var, "")
    if not value:
        raise KeyError_(f"{var} is not set (pass --key-file or export {var})")
    return value


def check_host(var: str, base_url: str) -> None:
    """Refuse to send a pinned key to any host other than its own."""
    pinned = KEY_HOST_PINS.get(var)
    host = urlparse(base_url).hostname or ""
    if urlparse(base_url).scheme != "https":
        raise KeyError_("base URL must be https")
    if pinned and host != pinned:
        raise KeyError_(f"{var} may only be sent to {pinned}, not {host}")


def describe(var: str, value: str) -> str:
    """Safe description for logs: the variable name and the value's length only."""
    return f"{var} (len={len(value)})"
