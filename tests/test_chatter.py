# SPDX-License-Identifier: MIT
"""slopdam.chatter: the guard always runs; the model tests need `pip install "slopdam[chatter]"`."""
import builtins
import io
import sys

import pytest

from slopdam import chatter
from slopdam.chatter import DELETE, KEEP, UPPER, guard, rebuild, whole_words
from slopdam.cli import main


def pieces(text):
    """Word-ish pieces with offsets: runs of letters, then each other non-space character."""
    import re

    return [m.span() for m in re.finditer(r"\w+|[^\w\s]", text)]


def apply(text, deleted_words):
    offsets = pieces(text)
    labels = [DELETE if i < deleted_words else KEEP for i in range(len(offsets))]
    labels = whole_words(offsets, labels, text)
    return rebuild(text, offsets, guard(text, offsets, labels))


@pytest.mark.parametrize("text, n, want", [
    ("Great news! Deployed api", 3, "Deployed api"),
    ("Great news! Deployed api", 2, "Deployed api"),              # "!" belongs to the word "news!"
    ("Rolled back auth", 1, "Rolled back auth"),                    # must end in punctuation
    ("Great news!", 3, "Great news!"),                              # must leave something behind
    ("ERROR: disk full", 2, "ERROR: disk full"),                    # log level
    ("orders에서 테스트 실패", 1, "orders에서 테스트 실패"),            # Latin and Hangul mixed
    ("Saved 3 rows: done", 4, "Saved 3 rows: done"),                # digits
    ("さて、バックアップ完了", 2, "バックアップ完了"),                    # cut at full-width punctuation
    ("状態：OK", 2, "状態：OK"),                                     # a Japanese or Chinese span ending in "："
])
def test_guard(text, n, want):
    assert apply(text, n) == want


def test_upper_only_right_after_the_deletion():
    text = "Heads up: cache warmed"
    offsets = pieces(text)
    assert rebuild(text, offsets, guard(text, offsets, [DELETE, DELETE, DELETE, UPPER, KEEP])) == "Cache warmed"
    assert rebuild(text, offsets, guard(text, offsets, [KEEP, KEEP, KEEP, KEEP, UPPER])) == text


def test_missing_extra_is_a_clear_error(monkeypatch, capsys):
    real = builtins.__import__

    def no_torch(name, *args, **kwargs):
        if name in ("torch", "transformers"):
            raise ImportError(name)
        return real(name, *args, **kwargs)

    chatter.tagger.cache_clear()
    monkeypatch.setattr(builtins, "__import__", no_torch)
    monkeypatch.setattr(sys, "stdin", io.StringIO("Great news! saved\n"))
    assert main(["clean", "--chatter"]) == 2
    assert 'pip install "slopdam[chatter]"' in capsys.readouterr().err
    with pytest.raises(ImportError, match="slopdam\\[chatter\\]"):
        chatter.strip(["Great news! saved"])


@pytest.fixture(scope="module")
def model():
    pytest.importorskip("torch")
    pytest.importorskip("transformers")
    chatter.tagger.cache_clear()
    return chatter.tagger()


def test_strip(model):
    lines = ["✅ Great news! **Deployed** api — 3 pods", "Finally block ran in auth", "", "状態：OK",
             "좋은 소식입니다! 배포 완료"]
    assert chatter.strip(lines) == ["Deployed api: 3 pods", "Finally block ran in auth", "", "状態：OK", "배포 완료"]


def test_cli_chatter(model, monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("Heads up: cache warmed for orders\nuser_id=42 saved\n"))
    assert main(["clean", "--chatter"]) == 0
    assert capsys.readouterr().out == "Cache warmed for orders\nuser_id=42 saved\n"
