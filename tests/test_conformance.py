# SPDX-License-Identifier: MIT
"""The Python package must pass the language-neutral cases in spec/conformance.json."""
import json
import logging
from pathlib import Path

import pytest

from slopdam import Sanitizer

SPEC = json.loads((Path(__file__).resolve().parent.parent / "spec" / "conformance.json").read_text(encoding="utf-8"))
CASES = [(g["id"], c) for g in SPEC["groups"] for c in g["cases"]]


@pytest.mark.parametrize("group, case", CASES, ids=[f"{g}-{i}" for i, (g, _) in enumerate(CASES)])
@pytest.mark.parametrize("profile", ["reader", "dev"])
def test_conformance(group, case, profile):
    opts = case.get("options", {})
    levelno = logging.getLevelName(opts["log_level"]) if "log_level" in opts else None
    s = Sanitizer(profile, level=opts.get("level", "basic"), dash_inline=opts.get("dash_inline", "colon"))
    assert s.clean(case["input"], levelno) == case[profile]
    assert s.clean(case[profile], levelno) == case[profile]  # idempotent
