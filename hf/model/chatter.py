# SPDX-License-Identifier: MIT
"""Remove chatty openers ("Great news!", "Heads up:", "살펴보겠습니다.") from log lines.

    from slopdam import clean
    from chatter import ChatterTagger

    tagger = ChatterTagger("slopdam/chatter-tagger")
    tagger([clean("Great news! Successfully deployed api — 3 pods")])
    # ['Successfully deployed api: 3 pods']

Run slopdam first: the model was trained on slopdam's `reader` output. It only deletes; it never
writes new text. Every deletion also has to pass `guard`, a fixed set of rules (one run of whole
words at the start of a line, ending in punctuation or a Korean connective, no digits, paths, file
names or key=value), so a line the model is unsure about comes back unchanged.
"""
from __future__ import annotations

import re

KEEP, DELETE, UPPER = 0, 1, 2
MAX_PIECES = 256

LINE_START = re.compile(r"[ \t]*(?:[-*+•][ \t]+|#{1,6}[ \t]+|\d+[.)][ \t]+)?")
UNSAFE = re.compile(r"[0-9/\\_=@]|\.\w|\w\.\w")
# An opener ends in punctuation, or (Korean only) in a connective ending such as -면, -로, -히.
OPENER_END = re.compile(r"(?:[,:!?.…]|[가-힣]*[면로히도피대럼과만데])$")
MIXED = re.compile(r"[A-Za-z].*[가-힣]|[가-힣].*[A-Za-z]", re.S)  # "orders에서" is content


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


def whole_words(offsets: list, labels: list) -> list:
    """Let the first piece of each word decide for the whole word, so a word is never cut in half."""
    out, first = [], KEEP
    for i, ((s, _), t) in enumerate(zip(offsets, labels)):
        if i == 0 or s != offsets[i - 1][1]:
            first = t
            out.append(t)
        else:
            out.append(DELETE if first == DELETE else KEEP)
    return out


def guard(text: str, offsets: list, labels: list) -> list:
    """The safety envelope around the model. Per line, deletions are kept only if they form one
    run of whole pieces starting where the line's text starts (after a list or heading marker),
    leave something behind, end in punctuation or a Korean connective ending, and contain no
    digits, paths, file names, key=value or a mix of Latin and Hangul. Upper-casing
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
                labels = whole_words(spans, pred[k, :n].tolist())
                out.append(rebuild(text, spans, guard(text, spans, labels) if use_guard else labels))
    return out


class ChatterTagger:
    """Load the tagger from the Hub (or a local folder) and strip openers from lines of text."""

    def __init__(self, path: str = "slopdam/chatter-tagger", device: str = "cpu"):
        import torch
        from transformers import AutoModelForTokenClassification, AutoTokenizer

        self.device = torch.device(device)
        self.tok = AutoTokenizer.from_pretrained(path)
        self.model = AutoModelForTokenClassification.from_pretrained(path).to(self.device)

    def __call__(self, texts: list, batch: int = 64) -> list:
        return predict(self.model, self.tok, list(texts), self.device, batch)
