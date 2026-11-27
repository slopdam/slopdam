# SPDX-License-Identifier: MIT
"""Property-based tests: invariants that must hold for any input, not just known cases.

SLOPDAM_EXAMPLES=20000 python -m pytest tests/test_properties.py runs a longer search.
"""
import os

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

from slopdam import Sanitizer  # noqa: E402
from slopdam.rules import DASHES, EU, HYPHENS, LINES  # noqa: E402

SANITIZERS = [Sanitizer(p, l) for p in ("reader", "dev") for l in ("basic", "strong", "strict")]

# Text weighted toward what slopdam cares about: Hangul, dashes, emoji, markdown, spaces.
TRACES = list(DASHES + EU + HYPHENS + LINES) + ["✅", "❌", "⚠️", "🚀", "🎉", "**", "#", "`", "…", "“", "”", "→", "•", "​", " ", "!", "~"]
PIECES = st.one_of(
    st.text(max_size=8),
    st.text(alphabet="가나다라마바사완료저장 ", max_size=8),
    st.text(alphabet="abc xyz 0123456789-=_.:/", max_size=8),
    st.sampled_from(TRACES),
    st.sampled_from([" ", "\n", "\t", "  "]),
)
TEXT = st.lists(PIECES, max_size=12).map("".join)
PLAIN_ASCII = st.text(alphabet=st.characters(min_codepoint=0x20, max_codepoint=0x7E, exclude_characters="*#=-_~+`"), max_size=40)
PROTECTED = st.one_of(
    st.from_regex(r"https://[a-z]{1,8}\.com/[a-z—–ㅡ✅]{1,8}", fullmatch=True),
    st.from_regex(r"`[a-z—ㅡ✅ ]{1,8}`", fullmatch=True).filter(lambda s: s.strip("` ")),
    st.from_regex(r"/tmp/[a-z—ㅡ]{1,8}\.txt", fullmatch=True),
)
FAST = settings(max_examples=int(os.environ.get("SLOPDAM_EXAMPLES", "300")), deadline=None)


@FAST
@given(TEXT, st.sampled_from(SANITIZERS))
def test_idempotent(text, s):
    once = s.clean(text)
    assert s.clean(once) == once


@FAST
@given(TEXT, st.sampled_from(SANITIZERS), st.sampled_from([None, 10, 20, 30, 40, 50]))
def test_never_raises_and_returns_text(text, s, levelno):
    out = s.clean(text, levelno)
    assert isinstance(out, str)
    assert not out.startswith((" ", "\t")) and "\n\n" not in out


@FAST
@given(TEXT, st.sampled_from(SANITIZERS))
def test_findings_spans_point_into_the_input(text, s):
    for f in s.findings(text):
        assert 0 <= f.start < f.end <= len(text)
        assert f.text == text[f.start:f.end].strip()


@FAST
@given(PROTECTED, st.text(alphabet="가나다 ", max_size=6), st.sampled_from(SANITIZERS))
def test_protected_spans_survive(span, prefix, s):
    out = s.clean(f"{prefix} {span} 확인")
    if s.profile == "reader" and span.startswith("`"):
        # reader may drop the backticks of clean inline code; its content stays as written,
        # inner spaces included, since no rule changes it (the ends of a line are still trimmed).
        assert span in out or span.strip("`").strip() in out
    else:
        assert span in out  # byte for byte


@FAST
@given(PLAIN_ASCII)
def test_plain_ascii_sentences_unchanged(text):
    # Single-line ASCII text without markdown or separator characters has nothing to clean,
    # apart from the whitespace tidying every line gets.
    expected = " ".join(text.split()) if text.strip() else ""
    for s in SANITIZERS[:2]:
        assert " ".join(s.clean(text).split()) == expected
