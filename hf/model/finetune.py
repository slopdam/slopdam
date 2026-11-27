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
import time

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

from chatter import DELETE, KEEP, UPPER, predict, rebuild
from train import HERE, OUT, load, score, tags

BASE = "distilbert/distilbert-base-multilingual-cased"


def pieces(tok, text: str) -> list:
    return tok(text, return_offsets_mapping=True, add_special_tokens=False)["offset_mapping"]


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
