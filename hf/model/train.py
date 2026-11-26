# SPDX-License-Identifier: MIT
"""Train the slopdam edit tagger on log-slop and score it on the held-out test split.

    python hf/model/train.py                       # reads hf/dataset/out/, writes hf/model/out/

The model never writes text. It reads slopdam's `reader` output one character at a time and tags
each character KEEP, DELETE or UPPER (keep it, upper-cased), which is enough to turn `reader` into
`target` on every row of the dataset. It is trained from scratch: no pretrained weights, only the
synthetic MIT data, so there is no third-party license involved.
"""
from __future__ import annotations

import argparse
import difflib
import json
import random
import time
from pathlib import Path

import torch
from torch import nn

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "dataset" / "out" / "data"
OUT = HERE / "out"
KEEP, DELETE, UPPER = 0, 1, 2
PAD, UNK = 0, 1
MAX_LEN = 512


def tags(reader: str, target: str) -> list:
    """Per-character tags that turn `reader` into `target` (deletions plus upper-casing)."""
    out = [DELETE] * len(reader)
    sm = difflib.SequenceMatcher(None, reader.lower(), target.lower(), autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            for i, j in zip(range(i1, i2), range(j1, j2)):
                out[i] = UPPER if reader[i] != target[j] else KEEP
        elif op != "delete":
            raise ValueError(f"not a deletion: {reader!r} -> {target!r}")
    return out


def apply(reader: str, labels) -> str:
    return "".join(c.upper() if t == UPPER else c for c, t in zip(reader, labels) if t != DELETE)


def load(split: str) -> list:
    with open(DATA / f"{split}.jsonl", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


class Tagger(nn.Module):
    def __init__(self, vocab: int, dim: int = 96, hidden: int = 128, layers: int = 2):
        super().__init__()
        self.emb = nn.Embedding(vocab, dim, padding_idx=PAD)
        self.rnn = nn.LSTM(dim, hidden, num_layers=layers, batch_first=True, bidirectional=True, dropout=0.1)
        self.out = nn.Linear(2 * hidden, 3)

    def forward(self, x):
        h, _ = self.rnn(self.emb(x))
        return self.out(h)


def encode(texts: list, vocab: dict) -> torch.Tensor:
    n = max(len(t) for t in texts)
    x = torch.full((len(texts), n), PAD, dtype=torch.long)
    for i, t in enumerate(texts):
        x[i, : len(t)] = torch.tensor([vocab.get(c, UNK) for c in t], dtype=torch.long)
    return x


def predict(model: Tagger, texts: list, vocab: dict, device, batch: int = 256) -> list:
    model.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(texts), batch):
            chunk = texts[i : i + batch]
            pred = model(encode(chunk, vocab).to(device)).argmax(-1).cpu()
            out += [apply(t, pred[k, : len(t)].tolist()) for k, t in enumerate(chunk)]
    model.train()
    return out


def score(rows: list, outputs: list) -> dict:
    """Exact match where the rules fall short, and how often the model leaves everything else alone."""
    groups = {"rewrite": [], "keep": [], "hard_negative": []}
    for r, y in zip(rows, outputs):
        ok = y == r["target"]
        groups["rewrite" if r["target"] != r["reader"] else "keep"].append(ok)
        if not r["injected"]:
            groups["hard_negative"].append(ok)
    res = {k: round(sum(v) / len(v), 4) for k, v in groups.items() if v}
    res["rows"] = {k: len(v) for k, v in groups.items()}
    for lang in ("en", "ko"):
        sub = [(r, y) for r, y in zip(rows, outputs) if r["lang"] == lang and r["target"] != r["reader"]]
        res[f"rewrite_{lang}"] = round(sum(y == r["target"] for r, y in sub) / len(sub), 4)
    return res


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--epochs", type=int, default=4)
    p.add_argument("--batch", type=int, default=64)
    p.add_argument("--lr", type=float, default=2e-3)
    p.add_argument("--seed", type=int, default=20261127)
    p.add_argument("--device", default="mps" if torch.backends.mps.is_available() else "cpu")
    a = p.parse_args(argv)
    random.seed(a.seed)
    torch.manual_seed(a.seed)
    device = torch.device(a.device)

    train, val, test = (load(s) for s in ("train", "validation", "test"))
    train = [r for r in train if len(r["reader"]) <= MAX_LEN]
    chars = sorted({c for r in train for c in r["reader"]})
    vocab = {c: i + 2 for i, c in enumerate(chars)}
    examples = [(r["reader"], tags(r["reader"], r["target"])) for r in train]

    model = Tagger(len(vocab) + 2).to(device)
    params = sum(p.numel() for p in model.parameters())
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr)
    steps = a.epochs * ((len(examples) + a.batch - 1) // a.batch)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=a.lr, total_steps=steps)
    loss_fn = nn.CrossEntropyLoss(ignore_index=-100)
    print(f"{len(examples)} train rows, vocab {len(vocab)}, {params:,} parameters, device {device}", flush=True)

    start = time.time()
    for epoch in range(a.epochs):
        random.shuffle(examples)
        examples.sort(key=lambda e: len(e[0]) // 16)  # similar lengths per batch, shuffled within buckets
        batches = [examples[i : i + a.batch] for i in range(0, len(examples), a.batch)]
        random.shuffle(batches)
        total = 0.0
        for b in batches:
            x = encode([t for t, _ in b], vocab).to(device)
            y = torch.full(x.shape, -100, dtype=torch.long)
            for i, (_, t) in enumerate(b):
                y[i, : len(t)] = torch.tensor(t)
            loss = loss_fn(model(x).reshape(-1, 3), y.to(device).reshape(-1))
            opt.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            total += loss.item()
        v = score(val, predict(model, [r["reader"] for r in val], vocab, device))
        print(f"epoch {epoch + 1}: loss {total / len(batches):.4f}, validation {v}, {time.time() - start:.0f}s", flush=True)

    result = {
        "parameters": params, "epochs": a.epochs, "seconds": round(time.time() - start),
        "validation": score(val, predict(model, [r["reader"] for r in val], vocab, device)),
        "test": score(test, predict(model, [r["reader"] for r in test], vocab, device)),
    }
    OUT.mkdir(exist_ok=True)
    torch.save({"state": model.state_dict(), "vocab": vocab}, OUT / "tagger.pt")
    (OUT / "metrics.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
