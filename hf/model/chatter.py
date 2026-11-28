# SPDX-License-Identifier: MIT
"""The tagger's guard and inference live in src/slopdam/chatter.py, which is also published on the
Hub as the model's chatter.py. This file keeps `from chatter import ...` working for the training
and evaluation scripts in this folder."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from slopdam.chatter import (  # noqa: E402,F401
    CJK_PUNCT, DELETE, KEEP, LINE_START, LOG_LABEL, MAX_PIECES, MIXED, OPENER_END, UNSAFE, UPPER, ChatterTagger,
    guard, predict, rebuild, whole_words,
)
