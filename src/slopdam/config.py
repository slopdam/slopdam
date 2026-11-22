# SPDX-License-Identifier: MIT
"""Project configuration: ``slopdam.toml`` or ``[tool.slopdam]`` in ``pyproject.toml``.

    profile = "dev"              # reader | dev
    level = "basic"              # basic | strong | strict
    disable = ["emoji.status"]   # rule ids or groups

    [dash]
    inline = "colon"             # colon | comma | hyphen | space (reader only)

    [lint]
    scope = "log-calls"          # log-calls | strings | all
    include = ["src/**"]
    exclude = ["tests/**"]

Other tables (for example ``[github]`` written by a hosted service) are ignored.
Command line options always win over the file.
"""
from __future__ import annotations

import fnmatch
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .rules import DASH_INLINE, LEVELS, PROFILES

SCOPES = ("log-calls", "strings", "all")


class ConfigError(ValueError):
    pass


@dataclass
class Config:
    profile: str = "reader"
    level: str = "basic"
    disable: tuple = ()
    dash_inline: str = "colon"
    scope: str = "log-calls"
    include: tuple = ()
    exclude: tuple = ()
    root: Optional[Path] = None  # directory paths in include/exclude are relative to
    source: Optional[Path] = field(default=None)  # file the settings came from

    def selects(self, path: str) -> bool:
        """Whether a file path passes include/exclude (globs relative to the config directory)."""
        try:
            rel = Path(path).resolve().relative_to((self.root or Path.cwd()).resolve()).as_posix()
        except ValueError:
            rel = Path(path).as_posix()
        if self.include and not any(fnmatch.fnmatch(rel, g) for g in self.include):
            return False
        return not any(fnmatch.fnmatch(rel, g) for g in self.exclude)


def find_config(start: str = ".") -> Optional[Path]:
    """Nearest slopdam.toml, or pyproject.toml with [tool.slopdam], from start up to the repo root."""
    here = Path(start).resolve()
    if here.is_file():
        here = here.parent
    for d in (here, *here.parents):
        if (d / "slopdam.toml").is_file():
            return d / "slopdam.toml"
        pyproject = d / "pyproject.toml"
        if pyproject.is_file() and re.search(r"^\[tool\.slopdam(\.|\])", pyproject.read_text(encoding="utf-8"), re.M):
            return pyproject
        if (d / ".git").exists():
            break
    return None


def load_config(path: Optional[str] = None, start: str = ".") -> Config:
    """Load settings from an explicit file or the nearest one; defaults when there is none."""
    found = Path(path) if path else find_config(start)
    if found is None:
        return Config()
    try:
        data = _parse_toml(found.read_text(encoding="utf-8"))
    except OSError as e:
        raise ConfigError(f"{found}: {e}") from e
    if found.name == "pyproject.toml":
        data = data.get("tool", {}).get("slopdam", {})
    return _from_dict(data, found)


def _from_dict(data: dict, source: Path) -> Config:
    def pick(value, allowed, name):
        if value not in allowed:
            raise ConfigError(f"{source}: {name} must be one of {', '.join(allowed)} (got {value!r})")
        return value

    def strings(value, name):
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise ConfigError(f"{source}: {name} must be a list of strings")
        return tuple(value)

    lint = data.get("lint", {})
    dash = data.get("dash", {})
    return Config(
        profile=pick(data.get("profile", "reader"), PROFILES, "profile"),
        level=pick(data.get("level", "basic"), LEVELS, "level"),
        disable=strings(data.get("disable", []), "disable"),
        dash_inline=pick(dash.get("inline", "colon"), tuple(DASH_INLINE), "dash.inline"),
        scope=pick(lint.get("scope", "log-calls"), SCOPES, "lint.scope"),
        include=strings(lint.get("include", []), "lint.include"),
        exclude=strings(lint.get("exclude", []), "lint.exclude"),
        root=source.parent,
        source=source,
    )


def _parse_toml(text: str) -> dict:
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # optional backport
        except ImportError:
            return _parse_toml_subset(text)
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"invalid TOML: {e}") from e


_KEY = re.compile(r'^([A-Za-z0-9_.-]+|"[^"]*")\s*=\s*(.*)$')


def _parse_toml_subset(text: str) -> dict:
    """Small TOML reader for Python < 3.11 without tomli.

    Enough for slopdam settings and the surrounding pyproject.toml: tables, strings,
    booleans, integers and (multi-line) arrays of those. Anything else is skipped.
    """
    root: dict = {}
    table = root
    pending = ""
    for raw in text.splitlines():
        line = _strip_comment(raw).strip()
        if pending:
            pending += " " + line
            if _balanced(pending):
                _assign(table, pending)
                pending = ""
            continue
        if not line:
            continue
        if line.startswith("[["):  # array of tables: not used by slopdam, skip its keys
            table = {}
            continue
        if line.startswith("["):
            table = root
            for part in line.strip("[] ").split("."):
                table = table.setdefault(part.strip().strip('"'), {})
            continue
        if _KEY.match(line):
            if _balanced(line):
                _assign(table, line)
            else:
                pending = line
    return root


def _strip_comment(line: str) -> str:
    out, quote = [], None
    for ch in line:
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#":
            break
        out.append(ch)
    return "".join(out)


def _balanced(s: str) -> bool:
    depth, quote = 0, None
    for ch in s:
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
    return depth <= 0


def _assign(table: dict, line: str) -> None:
    m = _KEY.match(line)
    if not m:
        return
    key, value = m.group(1).strip('"'), _value(m.group(2).strip())
    if value is not _SKIP:
        table[key] = value


_SKIP = object()


def _value(s: str):
    if s.startswith('"""') or s.startswith("'''"):
        return _SKIP
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1].replace('\\"', '"').replace("\\\\", "\\") if s[0] == '"' else s[1:-1]
    if s in ("true", "false"):
        return s == "true"
    if re.fullmatch(r"[+-]?\d+", s):
        return int(s)
    if s.startswith("[") and s.endswith("]"):
        items, buf, quote = [], "", None
        for ch in s[1:-1]:
            if quote:
                buf += ch
                if ch == quote:
                    quote = None
            elif ch in "\"'":
                quote = ch
                buf += ch
            elif ch == ",":
                items.append(buf.strip())
                buf = ""
            else:
                buf += ch
        if buf.strip():
            items.append(buf.strip())
        values = [_value(i) for i in items if i]
        return _SKIP if any(v is _SKIP for v in values) else values
    return _SKIP


def config_from_env() -> Optional[str]:
    """SLOPDAM_CONFIG points at an explicit settings file."""
    return os.environ.get("SLOPDAM_CONFIG") or None
