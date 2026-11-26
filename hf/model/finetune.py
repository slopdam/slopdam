# SPDX-License-Identifier: MIT
"""Fine-tune distilbert-base-multilingual-cased (Apache-2.0) as a token tagger on log-slop.

    python hf/model/finetune.py --check     # how many rows token tags can represent exactly
    python hf/model/finetune.py             # train, then score validation, test and handwritten.jsonl

Same task as train.py, but on word pieces of a model pretrained on Wikipedia in 104 languages,
so it starts out knowing which words are content. Each piece is tagged KEEP, DELETE or UPPER
(keep it with its first letter upper-cased); the whitespace after a deleted piece goes with it.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import time

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

from train import DELETE, HERE, KEEP, OUT, UPPER, load, score, tags

BASE = "distilbert/distilbert-base-multilingual-cased"


def pieces(tok, text: str) -> list:
    return tok(text, return_offsets_mapping=True, add_special_tokens=False)["offset_mapping"]


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


LINE_START = re.compile(r"[ \t]*(?:[-*+•][ \t]+|#{1,6}[ \t]+|\d+[.)][ \t]+)?")
UNSAFE = re.compile(r"[0-9/\\_=@]|\.\w|\w\.\w")
# An opener ends in punctuation, or (Korean only) in a connective ending such as -면, -로, -히.
OPENER_END = re.compile(r"(?:[,:!?.…]|[\uac00-\ud7a3]*[면로히도피대럼과만데서])$")


def guard(text: str, offsets: list, labels: list) -> list:
    """The safety envelope around the model. Per line, deletions are kept only if they form one
    run of whole pieces starting where the line's text starts (after a list or heading marker),
    leave something behind, end in punctuation or a Korean connective ending, and contain no
    digits, paths, file names or key=value. Upper-casing
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
        start = a + LINE_START.match(text, a, b).end() - a
        run = [i for i in idx if labels[i] == DELETE]
        first_kept = next((i for i in idx if labels[i] != DELETE and offsets[i][0] >= start), None)
        ok = (
            not run
            or (
                offsets[run[0]][0] == start
                and run == list(range(run[0], run[-1] + 1))
                and first_kept is not None
                and first_kept == run[-1] + 1
                and not UNSAFE.search(text[offsets[run[0]][0] : offsets[run[-1]][1]])
                and OPENER_END.search(text[offsets[run[0]][0] : offsets[run[-1]][1]])
            )
        )
        uppers = [i for i in idx if labels[i] == UPPER]
        ok = ok and all(i == first_kept and run for i in uppers)
        if not ok:
            for i in idx:
                out[i] = KEEP
    return out


def piece_tags(text: str, target: str, offsets: list):
    """Piece tags from character tags, or None when a piece is only partly deleted."""
    chars = tags(text, target)
    out = []
    for s, e in offsets:
        span = chars[s:e]
        if all(t == DELETE for t in span):
            out.append(DELETE)
        elif all(t == KEEP for t in span[1:]) and span[0] in (KEEP, UPPER):
            out.append(span[0])
        else:
            return None
    return out


def encode(tok, rows: list):
    """(text, offsets, tags) for every row whose target the tags reproduce exactly."""
    keep, lost = [], 0
    for r in rows:
        offsets = pieces(tok, r["reader"])
        labels = piece_tags(r["reader"], r["target"], offsets)
        if labels is None or rebuild(r["reader"], offsets, labels) != r["target"]:
            lost += 1
            continue
        keep.append((r["reader"], offsets, labels))
    return keep, lost


def predict(model, tok, texts: list, device, batch: int = 64, use_guard: bool = True) -> list:
    model.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(texts), batch):
            chunk = texts[i : i + batch]
            enc = tok(chunk, return_offsets_mapping=True, add_special_tokens=False, padding=True,
                      truncation=True, max_length=256, return_tensors="pt")
            offsets = enc.pop("offset_mapping")
            pred = model(**{k: v.to(device) for k, v in enc.items()}).logits.argmax(-1).cpu()
            for k, text in enumerate(chunk):
                n = int(enc["attention_mask"][k].sum())
                spans = offsets[k, :n].tolist()
                labels = whole_words(spans, pred[k, :n].tolist())
                out.append(rebuild(text, spans, guard(text, spans, labels) if use_guard else labels))
    model.train()
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--check", action="store_true")
    p.add_argument("--rows", type=int, default=60000, help="train rows to use")
    p.add_argument("--hand", default="handwritten2.jsonl", help="handwritten set in hf/model/")
    p.add_argument("--epochs", type=int, default=2)
    p.add_argument("--batch", type=int, default=32)
    p.add_argument("--lr", type=float, default=5e-5)
    p.add_argument("--seed", type=int, default=20261127)
    p.add_argument("--device", default="mps" if torch.backends.mps.is_available() else "cpu")
    a = p.parse_args(argv)
    random.seed(a.seed)
    torch.manual_seed(a.seed)
    tok = AutoTokenizer.from_pretrained(BASE)
    # The model's job is chatty openers only: filler adverbs stay with slopdam's word list, since
    # unseen ones cannot be told from content ("Finally block ...").
    train, val, test = ([r for r in load(s) if "filler" not in r["injected"]] for s in ("train", "validation", "test"))
    random.shuffle(train)
    examples, lost = encode(tok, train[: a.rows])
    print(f"{len(examples)} rows usable, {lost} dropped (a piece only partly deleted)", flush=True)
    if a.check:
        return 0

    device = torch.device(a.device)
    model = AutoModelForTokenClassification.from_pretrained(BASE, num_labels=3).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=0.01)
    steps = a.epochs * ((len(examples) + a.batch - 1) // a.batch)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=a.lr, total_steps=steps, pct_start=0.1)
    start = time.time()
    for epoch in range(a.epochs):
        random.shuffle(examples)
        for i in range(0, len(examples), a.batch):
            b = examples[i : i + a.batch]
            enc = tok([t for t, _, _ in b], add_special_tokens=False, padding=True, truncation=True,
                      max_length=256, return_tensors="pt")
            y = torch.full(enc["input_ids"].shape, -100, dtype=torch.long)
            for k, (_, _, labels) in enumerate(b):
                n = min(len(labels), y.shape[1])
                y[k, :n] = torch.tensor(labels[:n])
            loss = model(**{k: v.to(device) for k, v in enc.items()}, labels=y.to(device)).loss
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            if (i // a.batch) % 200 == 0:
                print(f"epoch {epoch + 1} step {i // a.batch}: loss {loss.item():.4f}, {time.time() - start:.0f}s", flush=True)

    hand = [json.loads(line) for line in open(HERE / a.hand, encoding="utf-8")]
    hand_out = predict(model, tok, [r["reader"] for r in hand], device)
    for r, y in zip(hand, hand_out):
        if y != r["target"]:
            print(f"MISS {r['reader']!r} -> {y!r} (want {r['target']!r})")
    result = {
        "base": BASE, "scope": "chatty openers (rows with filler excluded)", "hand": a.hand, "train_rows": len(examples), "epochs": a.epochs, "seconds": round(time.time() - start),
        "validation": score(val, predict(model, tok, [r["reader"] for r in val], device)),
        "test": score(test, predict(model, tok, [r["reader"] for r in test], device)),
        "handwritten": {
            "chatter_removed": f"{sum(y == r['target'] for r, y in zip(hand, hand_out) if r['chatter'])}/{sum(r['chatter'] for r in hand)}",
            "left_alone": f"{sum(y == r['target'] for r, y in zip(hand, hand_out) if not r['chatter'])}/{sum(not r['chatter'] for r in hand)}",
        },
    }
    OUT.mkdir(exist_ok=True)
    model.save_pretrained(OUT / "distilbert-tagger")
    tok.save_pretrained(OUT / "distilbert-tagger")
    (OUT / "distilbert-metrics.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
