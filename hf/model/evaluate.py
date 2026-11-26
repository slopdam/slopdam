# SPDX-License-Identifier: MIT
"""Score a trained tagger on handwritten.jsonl: log lines written by hand, with openers the
generator never uses, plus lines that only look like chatter and must stay as they are.

    python hf/model/evaluate.py
"""
from __future__ import annotations

import json

import torch

from train import OUT, HERE, Tagger, predict


def main() -> int:
    saved = torch.load(OUT / "tagger.pt", map_location="cpu")
    vocab = saved["vocab"]
    model = Tagger(len(vocab) + 2)
    model.load_state_dict(saved["state"])
    rows = [json.loads(line) for line in open(HERE / "handwritten.jsonl", encoding="utf-8")]
    outputs = predict(model, [r["reader"] for r in rows], vocab, torch.device("cpu"))
    chatter = [y == r["target"] for r, y in zip(rows, outputs) if r["chatter"]]
    plain = [y == r["target"] for r, y in zip(rows, outputs) if not r["chatter"]]
    for r, y in zip(rows, outputs):
        mark = "ok  " if y == r["target"] else "MISS"
        print(f"{mark} {r['reader']!r}\n     -> {y!r}" + ("" if y == r["target"] else f"\n     want {r['target']!r}"))
    result = {"chatter_removed": f"{sum(chatter)}/{len(chatter)}", "left_alone": f"{sum(plain)}/{len(plain)}"}
    (OUT / "handwritten.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
