# SPDX-License-Identifier: MIT
"""Keep spec/ in sync with the Python reference implementation.

    python scripts/gen_spec.py            rewrite spec/rules.json and the expected outputs in spec/conformance.json
    python scripts/gen_spec.py --check    exit 1 if either file is out of date (used in CI)

spec/conformance.json is curated by hand: add an "input" (and optional "options"),
then run this script to fill in "reader" and "dev". Review the diff before committing:
a changed expected value is an output change (see GOVERNANCE.md).
"""
from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from slopdam import rules  # noqa: E402

SPEC = ROOT / "spec"
SPEC_VERSION = 1
FLAGS = {re.M: "multiline"}


def _action(action) -> dict:
    if action is None:
        return {"kind": "report"}
    if callable(action):
        return {"kind": "function", "name": action.__name__.lstrip("_")}
    return {"kind": "replace", "value": action}


def rules_json() -> dict:
    return {
        "spec_version": SPEC_VERSION,
        "profiles": list(rules.PROFILES),
        "levels": list(rules.LEVELS),
        "dash_inline": rules.DASH_INLINE,
        "default_dash_inline": "colon",
        "protected_spans": rules._PROTECT.pattern,
        "charsets": {
            "hyphens": rules.HYPHENS,
            "dashes": rules.DASHES,
            "hangul_eu": rules.EU,
            "box_lines": rules.LINES,
            "emoji": rules._EMOJI_CLASS,
            "status": rules._STATUS,
            "hangul_choseong": rules.CHOSEONG,
        },
        # dash_run: a neighbor counts as part of a word when it is a letter or digit, a protected
        # span, or one of these (before the dash: closers, after it: openers).
        "dash_word_before": rules._CLOSERS,
        "dash_word_after": rules._OPENERS,
        "tidy": {"scope": "changed_lines", "multi_space": rules._MULTI_SPACE.pattern,
                 "quote_space": rules._QUOTE_SPACE.pattern, "max_passes": rules._MAX_PASSES},
        "status_redundant_at": {tag: logging.getLevelName(n) for tag, n in rules._REDUNDANT.items()},
        "rules": [
            {
                "id": r.id,
                "level": r.level,
                "description": r.description,
                "pattern": r.pattern.pattern,
                "flags": [name for flag, name in FLAGS.items() if r.pattern.flags & flag],
                "actions": {p: _action(a) for p, a in r.actions.items()},
            }
            for r in rules.RULES
        ],
    }


def expected(case: dict) -> dict:
    opts = case.get("options", {})
    levelno = logging.getLevelName(opts["log_level"]) if "log_level" in opts else None
    out = {}
    for profile in rules.PROFILES:
        s = rules.Sanitizer(profile, level=opts.get("level", "basic"), dash_inline=opts.get("dash_inline", "colon"))
        out[profile] = s.clean(case["input"], levelno)
    return out


def dump(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def main(argv: list) -> int:
    check = "--check" in argv
    conf_path = SPEC / "conformance.json"
    conf = json.loads(conf_path.read_text(encoding="utf-8"))
    for group in conf["groups"]:
        for case in group["cases"]:
            case.update(expected(case))
    outputs = {SPEC / "rules.json": dump(rules_json()), conf_path: dump(conf)}

    stale = [p for p, text in outputs.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
    if check:
        for p in stale:
            print(f"{p.relative_to(ROOT)} is out of date: run python scripts/gen_spec.py", file=sys.stderr)
        return 1 if stale else 0
    for p in stale:
        p.write_text(outputs[p], encoding="utf-8")
        print(f"wrote {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
