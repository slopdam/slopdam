# SPDX-License-Identifier: MIT
"""Command line entry point.

    slopdam check [PATH ...]   report rule hits, exit 1 if any
    slopdam fix [PATH ...]     rewrite string literals in Python files (--diff to preview)
    slopdam clean              read stdin, write cleaned text to stdout

Settings come from slopdam.toml or [tool.slopdam] in pyproject.toml (see config.py);
command line options win over the file. Exit codes: 0 clean, 1 findings, 2 usage or config error.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
from typing import Iterator

from .config import SCOPES, Config, ConfigError, config_from_env, load_config
from .fixer import fix_source
from . import __version__
from .rules import DASH_INLINE, LEVELS, PROFILES, RULES, Sanitizer

SOURCE_EXTS = {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".java", ".kt", ".go", ".rb", ".php", ".rs", ".swift"}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__", ".tox", "target"}

# Lines that look like a log/print call: logger.info(, logging.warning(, console.log(, print(, println(, slog.Info(, Log.d(
LOG_CALL = re.compile(r"(?:\blog\w*|\bconsole|\bprint\w*|\bfmt\.(?:Print|Sprint|Fprint)\w*|\bslog)\s*[.(]", re.I)
# slopdam: ignore            -> skip the whole line
# slopdam: ignore[dash,emoji] -> skip only those rule ids / prefixes
COMMENT_PREFIXES = ("#", "//", "/*", "*", "--")  # comment-only lines are not log calls
IGNORE = re.compile(r"slopdam:\s*ignore(?:\[([\w.,\s-]+)\])?")


def iter_files(paths: list, cfg: Config) -> Iterator[str]:
    for path in paths:
        if os.path.isfile(path):
            yield path
            continue
        for root, dirs, files in os.walk(path):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for name in sorted(files):
                full = os.path.join(root, name)
                if os.path.splitext(name)[1] in SOURCE_EXTS and cfg.selects(full):
                    yield full


def _ignored(rule_id: str, ids: list) -> bool:
    return any(rule_id == i or rule_id.startswith(i + ".") for i in ids)


def _resolve(args: argparse.Namespace) -> Config:
    """Merge the settings file with command line options (options win)."""
    cfg = load_config(args.config or config_from_env(), start=(getattr(args, "paths", None) or ["."])[0])
    cfg.profile = args.profile or cfg.profile
    cfg.level = args.level or cfg.level
    cfg.dash_inline = args.dash_inline or cfg.dash_inline
    cfg.disable = tuple(cfg.disable) + tuple(args.disable)
    if getattr(args, "all", False):
        cfg.scope = "all"
    elif getattr(args, "scope", None):
        cfg.scope = args.scope
    return cfg


def _sanitizer(cfg: Config) -> Sanitizer:
    return Sanitizer(cfg.profile, cfg.level, disable=cfg.disable, dash_inline=cfg.dash_inline)


def _read(path: str):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except (UnicodeDecodeError, OSError) as e:
        print(f"{path}: skipped ({e})", file=sys.stderr)
        return None


def _line_hits(text: str, sanitizer: Sanitizer, scope: str):
    for lineno, line in enumerate(text.splitlines(), 1):
        if scope != "all" and (line.lstrip().startswith(COMMENT_PREFIXES) or not LOG_CALL.search(line)):
            continue
        ignore = IGNORE.search(line)
        if ignore and not ignore.group(1):
            continue
        ids = [i.strip() for i in ignore.group(1).split(",")] if ignore else []
        for f in sanitizer.findings(line):
            if not _ignored(f.rule_id, ids):
                yield lineno, f.start + 1, f.rule_id, f.text, f.fix


def check(args: argparse.Namespace) -> int:
    cfg = _resolve(args)
    sanitizer = _sanitizer(cfg)
    results = []
    for path in iter_files(args.paths, cfg):
        text = _read(path)
        if text is None:
            continue
        if cfg.scope in ("log-calls", "strings") and path.endswith(".py"):
            # Python: exact string literals from the syntax tree, the same targets fix rewrites.
            try:
                _, edits = fix_source(text, sanitizer, scope=cfg.scope)
                hits = sorted((e.line, e.col, e.rule_id, e.before, e.after) for e in edits)
            except SyntaxError:
                hits = list(_line_hits(text, sanitizer, "log-calls"))
        else:
            hits = list(_line_hits(text, sanitizer, "all" if cfg.scope == "all" else "log-calls"))
        results += [(path, *h) for h in hits]

    if args.format == "json":
        json.dump([{"path": p, "line": n, "col": c, "rule": r, "text": t, "fix": x} for p, n, c, r, t, x in results],
                  sys.stdout, ensure_ascii=False, indent=2)
        print()
    elif args.format == "github":
        # https://docs.github.com/actions/reference/workflow-commands-for-github-actions#setting-a-warning-message
        for path, lineno, col, rule, text, fix in results:
            print(f"::warning file={_gh(_uri(path), True)},line={lineno},col={col},title=slopdam {rule}::{_gh(_message(text, fix))}")
    elif args.format == "sarif":
        json.dump(_sarif(results), sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        for path, lineno, col, rule, text, fix in results:
            shown = "report only" if fix is None else f"-> {fix!r}"
            print(f"{path}:{lineno}:{col}: {rule} {text!r} {shown}")
        if results:
            print(f"\n{len(results)} finding(s), profile={cfg.profile}", file=sys.stderr)
    return 1 if results else 0


def _message(text: str, fix) -> str:
    return f"{text!r} (report only)" if fix is None else f"{text!r} -> {fix!r}"


def _gh(value: str, prop: bool = False) -> str:
    """Escape a workflow command value (properties also escape ':' and ',')."""
    value = value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    return value.replace(":", "%3A").replace(",", "%2C") if prop else value


def _uri(path: str) -> str:
    path = path.replace(os.sep, "/")
    return path[2:] if path.startswith("./") else path


def _sarif(results: list) -> dict:
    """SARIF 2.1.0 for GitHub code scanning and other SARIF viewers."""
    ids = sorted({r for _, _, _, r, _, _ in results})
    descriptions = {r.id: r.description for r in RULES}
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {
                "name": "slopdam",
                "version": __version__,
                "informationUri": "https://github.com/slopdam/slopdam",
                "rules": [{"id": i, "shortDescription": {"text": descriptions.get(i, i)}} for i in ids],
            }},
            "results": [{
                "ruleId": rule,
                "level": "warning",
                "message": {"text": _message(text, fix)},
                "locations": [{"physicalLocation": {
                    "artifactLocation": {"uri": _uri(path)},
                    "region": {"startLine": lineno, "startColumn": col},
                }}],
            } for path, lineno, col, rule, text, fix in results],
        }],
    }


def fix(args: argparse.Namespace) -> int:
    cfg = _resolve(args)
    sanitizer = _sanitizer(cfg)
    scope = "strings" if cfg.scope == "all" else cfg.scope
    changed_files, changed, skipped = 0, 0, 0
    for path in iter_files(args.paths, cfg):
        if not path.endswith(".py"):
            skipped += 1
            continue
        text = _read(path)
        if text is None:
            continue
        try:
            new, edits = fix_source(text, sanitizer, scope=scope)
        except SyntaxError as e:
            print(f"{path}: skipped (does not parse: {e.msg} at line {e.lineno})", file=sys.stderr)
            continue
        applied = [e for e in edits if e.after is not None]
        if new == text:
            continue
        changed_files += 1
        changed += len(applied)
        if args.diff:
            sys.stdout.writelines(difflib.unified_diff(
                text.splitlines(keepends=True), new.splitlines(keepends=True), f"a/{path}", f"b/{path}"))
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)
            for e in applied:
                print(f"{path}:{e.line}:{e.col}: {e.rule_id} {e.before!r} -> {e.after!r}")
    verb = "would fix" if args.diff else "fixed"
    note = f", {skipped} non-Python file(s) skipped" if skipped else ""
    print(f"{verb} {changed} issue(s) in {changed_files} file(s){note}", file=sys.stderr)
    return 1 if args.diff and changed_files else 0


def clean(args: argparse.Namespace) -> int:
    sanitizer = _sanitizer(_resolve(args))
    for line in sys.stdin:
        cleaned = sanitizer.clean(line)
        if cleaned:
            sys.stdout.write(cleaned + "\n")
    return 0


def main(argv: list = None) -> int:
    parser = argparse.ArgumentParser(prog="slopdam", description="Strip AI-generated patterns from log output.")
    parser.add_argument("--config", metavar="FILE", help="settings file (default: nearest slopdam.toml or pyproject.toml)")
    parser.add_argument("--profile", choices=PROFILES, help="reader: for end users (default), dev: for developers")
    parser.add_argument("--level", choices=LEVELS)
    parser.add_argument("--dash-inline", choices=tuple(DASH_INLINE), help="reader: what an inline dash becomes")
    parser.add_argument("--disable", action="append", default=[], metavar="RULE_ID", help="turn off a rule or rule group (repeatable)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="lint source files")
    p_check.add_argument("paths", nargs="*", default=["."])
    p_check.add_argument("--scope", choices=SCOPES, help="log-calls (default), strings (Python literals), all (every line)")
    p_check.add_argument("--all", action="store_true", help="same as --scope all")
    p_check.add_argument("--format", choices=("text", "json", "github", "sarif"), default="text",
                         help="github: annotations for GitHub Actions, sarif: for code scanning")
    p_check.set_defaults(func=check)

    p_fix = sub.add_parser("fix", help="rewrite string literals in Python files")
    p_fix.add_argument("paths", nargs="*", default=["."])
    p_fix.add_argument("--scope", choices=("log-calls", "strings"), help="log-calls (default) or every non-docstring string")
    p_fix.add_argument("--diff", action="store_true", help="print a diff instead of writing; exit 1 if anything would change")
    p_fix.set_defaults(func=fix)

    p_clean = sub.add_parser("clean", help="clean stdin to stdout")
    p_clean.set_defaults(func=clean)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ConfigError as e:
        print(f"slopdam: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
