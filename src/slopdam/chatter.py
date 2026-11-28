# SPDX-License-Identifier: MIT
"""Remove chatty openers ("Great news!", "Heads up:", "살펴보겠습니다.") with slopdam/chatter-tagger.

    pip install "slopdam[chatter]"

    from slopdam.chatter import strip
    strip(["Great news! Successfully deployed api — 3 pods", "Finally block ran in auth"])
    # ['Successfully deployed api: 3 pods', 'Finally block ran in auth']

    slopdam clean --chatter < app.log

`strip` runs slopdam's rules first, then the model: it was trained on slopdam's `reader` output.
The model only deletes; it never writes new text. Every deletion also has to pass `guard`, a fixed
set of rules (one run of whole words at the start of a line, ending in punctuation or a Korean
connective, no digits, paths, file names or key=value), so a line the model is unsure about comes
back unchanged. Japanese and Chinese openers are cut at full-width punctuation ("さて、", "好的，").

The model is downloaded from the Hugging Face Hub on first use, at the revision in `REVISION`.
This file has no dependency on the rest of slopdam except in `strip`, so it is also published on
the Hub as the model's `chatter.py`.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Optional

MODEL = "slopdam/chatter-tagger"
REVISION = "c0f0e70d082bd2b28d91d48f083585441193c8a0"  # v2
INSTALL = 'the chatter model needs the optional dependencies: pip install "slopdam[chatter]"'

KEEP, DELETE, UPPER = 0, 1, 2
MAX_PIECES = 256

LINE_START = re.compile(r"[ \t]*(?:[-*+•][ \t]+|#{1,6}[ \t]+|\d+[.)][ \t]+)?")
UNSAFE = re.compile(r"[0-9/\\_=@]|\.\w|\w\.\w")
# An opener ends in punctuation (full width in Japanese and Chinese), or (Korean only) in a
# connective ending such as -면, -로, -히. A Japanese or Chinese span ending in "：" is not one:
# there it is far more often a label ("状態：", "来源：") than an opener, and unseen labels
# cannot be told from unseen openers.
CJK_PUNCT = "、，！？：。"
OPENER_END = re.compile(r"(?:[,:!?.…、，！？。]|[가-힣]*[면로히도피대럼과만데])$")
# A log level, a diagnostic label or an exception name says what the line is: never an opener.
LOG_LABEL = re.compile(
    r"(?i:panic|fatal|error|err|warn|warning|info|debug|trace|note|hint|caution|caused by|exception|traceback"
    r"|경고|오류|에러|참고|주의|치명적 오류|알림|警告|エラー|注意|情報|致命的エラー|错误|提示|信息|严重|致命错误)(?![\w-])"
    r"|\w*(?:Error|Exception|Warning)(?![\w-])"
)
_CJK = "가-힣\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff"
MIXED = re.compile(rf"[A-Za-z].*[{_CJK}]|[{_CJK}].*[A-Za-z]", re.S)  # "orders에서", "payments磁盘" are content


def rebuild(text: str, offsets: list, labels: list) -> str:
    """Apply piece tags to text. Spaces after a deleted piece are dropped (line breaks stay);
    leading gaps are kept."""
    out, pos, deleted = [], 0, False
    for (s, e), t in zip(offsets, labels):
        gap = text[pos:s]
        out.append(gap if not deleted or pos == 0 else "\n" * gap.count("\n"))
        if t != DELETE:
            piece = text[s:e]
            out.append(piece[:1].upper() + piece[1:] if t == UPPER else piece)
        deleted, pos = t == DELETE, e
    if not deleted:
        out.append(text[pos:])
    return "".join(out)


def whole_words(offsets: list, labels: list, text: str = "") -> list:
    """Let the first piece of each word decide for the whole word, so a word is never cut in half.
    Japanese and Chinese have no spaces, so full-width punctuation also ends a word there."""
    out, first = [], KEEP
    for i, ((s, _), t) in enumerate(zip(offsets, labels)):
        if i == 0 or s != offsets[i - 1][1] or (s > 0 and text[s - 1] in CJK_PUNCT):
            first = t
            out.append(t)
        else:
            out.append(DELETE if first == DELETE else KEEP)
    return out


def guard(text: str, offsets: list, labels: list) -> list:
    """The safety envelope around the model. Per line, deletions are kept only if they form one
    run of whole pieces starting where the line's text starts (after a list or heading marker),
    leave something behind, end in punctuation (not a full-width "：") or a Korean connective ending, and contain no
    digits, paths, file names, key=value or a mix of Latin with Hangul, kana or CJK ideographs, and
    do not start with a log level, a diagnostic label or an exception name ("panic:", "Warning:",
    "경고:", "エラー：", "ValueError:"). Upper-casing
    is kept only on the first piece after that run. Any other line is left exactly as it was."""
    out = list(labels)
    line_start = 0
    lines = []
    for line in text.split("\n"):
        lines.append((line_start, line_start + len(line)))
        line_start += len(line) + 1
    for a, b in lines:
        idx = [i for i, (s, _) in enumerate(offsets) if a <= s < b]
        if not idx or all(labels[i] == KEEP for i in idx):
            continue
        start = LINE_START.match(text, a, b).end()
        run = [i for i in idx if labels[i] == DELETE]
        first_kept = next((i for i in idx if labels[i] != DELETE and offsets[i][0] >= start), None)
        span = text[offsets[run[0]][0] : offsets[run[-1]][1]] if run else ""
        ok = not run or (
            offsets[run[0]][0] == start
            and run == list(range(run[0], run[-1] + 1))
            and first_kept is not None
            and first_kept == run[-1] + 1
            and not UNSAFE.search(span)
            and OPENER_END.search(span)
            and not MIXED.search(span)
            and not LOG_LABEL.match(span)
        )
        uppers = [i for i in idx if labels[i] == UPPER]
        ok = ok and all(i == first_kept and run for i in uppers)
        if not ok:
            for i in idx:
                out[i] = KEEP
    return out


def predict(model, tok, texts: list, device, batch: int = 64, use_guard: bool = True) -> list:
    import torch

    model.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(texts), batch):
            chunk = texts[i : i + batch]
            enc = tok(chunk, return_offsets_mapping=True, add_special_tokens=False, padding=True,
                      truncation=True, max_length=MAX_PIECES, return_tensors="pt")
            offsets = enc.pop("offset_mapping")
            pred = model(**{k: v.to(device) for k, v in enc.items()}).logits.argmax(-1).cpu()
            for k, text in enumerate(chunk):
                n = int(enc["attention_mask"][k].sum())
                spans = offsets[k, :n].tolist()
                labels = whole_words(spans, pred[k, :n].tolist(), text)
                out.append(rebuild(text, spans, guard(text, spans, labels) if use_guard else labels))
    return out


def _load():
    try:
        import torch
        from transformers import AutoModelForTokenClassification, AutoTokenizer
    except ImportError as e:
        raise ImportError(INSTALL) from e
    from transformers.utils import logging

    logging.set_verbosity_error()  # keep stderr for real errors in a log pipe
    logging.disable_progress_bar()
    return torch, AutoModelForTokenClassification, AutoTokenizer


class ChatterTagger:
    """Load the tagger from the Hub (or a local folder) and strip openers from lines of text."""

    def __init__(self, path: str = MODEL, device: str = "cpu", revision: Optional[str] = None):
        torch, Model, Tokenizer = _load()
        if revision is None and path == MODEL:
            revision = REVISION
        self.device = torch.device(device)
        self.tok = Tokenizer.from_pretrained(path, revision=revision)
        self.model = Model.from_pretrained(path, revision=revision).to(self.device)

    def __call__(self, texts: list, batch: int = 64) -> list:
        return predict(self.model, self.tok, list(texts), self.device, batch)


@lru_cache(maxsize=None)
def tagger(device: str = "cpu") -> ChatterTagger:
    """The pinned model, loaded once per process."""
    return ChatterTagger(device=device)


def strip(lines, profile: str = "reader", level: str = "basic", device: str = "cpu") -> list:
    """Clean each line with slopdam's rules, then remove the opener the model finds, if any.

    The model was trained on `reader` output; with `dev` it still never deletes more than the
    guard allows, but it finds fewer openers."""
    from .rules import Sanitizer

    sanitizer = Sanitizer(profile, level)
    cleaned = [sanitizer.clean(line) for line in lines]
    todo = [i for i, line in enumerate(cleaned) if line.strip()]
    if todo:
        for i, out in zip(todo, tagger(device)([cleaned[i] for i in todo])):
            cleaned[i] = out
    return cleaned
