# SPDX-License-Identifier: MIT
"""Export the tagger to ONNX and quantize it to int8 for the browser demo.

    python hf/model/export_onnx.py     # writes out/onnx/model.onnx and out/onnx/model_int8.onnx

Needs onnx, onnxruntime and onnxscript besides transformers and torch. The int8 file is the one on
the Hub as onnx/model_int8.onnx: dynamic quantization with one scale per output channel. One scale
per tensor scored 89.9% of unseen openers on log-slop test, under the 90% bar; per channel scored
90.5%. hf/model/js_parity.py checks hf/space/chatter.js, which runs it, against chatter.py.
"""
from __future__ import annotations

import torch
from onnxruntime.quantization import QuantType, quantize_dynamic
from transformers import AutoModelForTokenClassification, AutoTokenizer

from train import OUT


def main() -> int:
    src, dst = OUT / "distilbert-tagger", OUT / "onnx"
    dst.mkdir(parents=True, exist_ok=True)
    model = AutoModelForTokenClassification.from_pretrained(src).eval()
    enc = AutoTokenizer.from_pretrained(src)(["Great news! Deployed api", "さて、バックアップ"], padding=True,
                                             add_special_tokens=False, return_tensors="pt")
    axes = {"batch": 0, "seq": 1}
    torch.onnx.export(model, (enc["input_ids"], enc["attention_mask"]), dst / "model.onnx",
                      input_names=["input_ids", "attention_mask"], output_names=["logits"],
                      dynamic_axes={n: {v: k for k, v in axes.items()} for n in ("input_ids", "attention_mask", "logits")},
                      opset_version=17, dynamo=False)
    quantize_dynamic(dst / "model.onnx", dst / "model_int8.onnx", weight_type=QuantType.QInt8, per_channel=True)
    for name in ("model.onnx", "model_int8.onnx"):
        print(name, (dst / name).stat().st_size // 2**20, "MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
