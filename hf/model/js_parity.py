# SPDX-License-Identifier: MIT
"""Check hf/space/chatter.js against slopdam.chatter: same word pieces, and the same output from
the same model labels, on log-slop test, the handwritten sets and the real messages.

    python hf/model/js_parity.py      # needs node, transformers and the trained model in out/

The model runs once, in Python; both sides then turn its raw labels into text, so the check covers
the tokenizer, whole_words, guard and rebuild, not the ONNX runtime.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

from chatter import MAX_PIECES, guard, rebuild, whole_words
from train import HERE, OUT, load

ROOT = HERE.parents[1]
# Edge cases: astral characters, a word over 100 characters, combining marks, other scripts.
EXTRA = ["Great news! 🎉 saved 𝔘𝔫𝔦𝔠𝔬𝔡𝔢 rows", "Heads up: " + "x" * 120 + " done", "Café: re\u0301sume\u0301 saved",
         "สวัสดี ครับ: บันทึกแล้ว", "مرحبا: تم الحفظ", "さて、𠮷野家のデータを保存", "好的，\U00020000字段已更新", "Ａｌｌ ｄｏｎｅ！ ok",
         "Well,\u00a0saved\u3000rows", "x\u0085y\u2028z", "", "   ", "a" * 300]
NODE = """
import { readFileSync } from "node:fs";
const js = await import(process.argv[1]);
const vocab = new Map(Object.entries(JSON.parse(readFileSync(process.argv[2], "utf8")).model.vocab));
let pieces = 0, text = 0, n = 0;
for (const line of readFileSync(process.argv[3], "utf8").trim().split("\\n")) {
  const r = JSON.parse(line);
  n++;
  const got = js.tokenize(vocab, [...r.text]);
  const same = got.length === r.ids.length && got.every((p, i) => p.id === r.ids[i] && p.start === r.offsets[i][0] && p.end === r.offsets[i][1]);
  if (!same) { if (pieces++ < 3) console.error("pieces differ:", JSON.stringify(r.text)); continue; }
  const out = js.apply(r.text, r.offsets, r.labels);
  if (out !== r.out) { if (text++ < 3) console.error("output differs:", JSON.stringify(r.text), JSON.stringify(out), JSON.stringify(r.out)); }
}
console.log(JSON.stringify({ lines: n, pieces_differ: pieces, output_differs: text }));
"""


def main() -> int:
    texts = [r["reader"] for r in load("test")]
    for h in (3, 4, 5, 6, 7):
        texts += [json.loads(l)["reader"] for l in open(HERE / f"handwritten{h}.jsonl", encoding="utf-8")]
    texts += [json.loads(l)["input"] for l in open(ROOT / "hf" / "dataset" / "real" / "messages.jsonl", encoding="utf-8")]
    texts += EXTRA
    tok = AutoTokenizer.from_pretrained(OUT / "distilbert-tagger")
    model = AutoModelForTokenClassification.from_pretrained(OUT / "distilbert-tagger").eval()
    rows = []
    with torch.no_grad():
        for i in range(0, len(texts), 64):
            chunk = texts[i : i + 64]
            enc = tok(chunk, return_offsets_mapping=True, add_special_tokens=False, padding=True, truncation=True,
                      max_length=MAX_PIECES, return_tensors="pt")
            offsets = enc.pop("offset_mapping")
            pred = model(**enc).logits.argmax(-1)
            for k, text in enumerate(chunk):
                n = int(enc["attention_mask"][k].sum())
                spans, labels = offsets[k, :n].tolist(), pred[k, :n].tolist()
                out = rebuild(text, spans, guard(text, spans, whole_words(spans, labels, text)))
                rows.append({"text": text, "ids": enc["input_ids"][k, :n].tolist(), "offsets": spans, "labels": labels, "out": out})
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "rows.jsonl"
        data.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        run = subprocess.run(["node", "--input-type=module", "-e", NODE, (ROOT / "hf" / "space" / "chatter.js").as_uri(),
                              str(OUT / "distilbert-tagger" / "tokenizer.json"), str(data)], capture_output=True, text=True)
    sys.stderr.write(run.stderr)
    print(run.stdout.strip())
    result = json.loads(run.stdout)
    return 0 if run.returncode == 0 and not result["pieces_differ"] and not result["output_differs"] else 1


if __name__ == "__main__":
    sys.exit(main())
