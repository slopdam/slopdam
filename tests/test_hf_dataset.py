# SPDX-License-Identifier: MIT
"""The Hugging Face dataset generator: deterministic, and its labels are slopdam's output."""
import importlib.util
from pathlib import Path

from slopdam import Sanitizer

spec = importlib.util.spec_from_file_location("hf_generate", Path(__file__).resolve().parent.parent / "hf" / "dataset" / "generate.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


def test_same_seed_same_rows():
    assert gen.build(200, 20, 7) == gen.build(200, 20, 7)


def test_labels_match_slopdam_and_negatives_stay():
    data = gen.build(300, 30, 11)
    inputs = [r["input"] for split in ("train", "test") for r in data[split]]
    assert len(inputs) == len(set(inputs))  # no input in both splits or twice
    reader, dev = Sanitizer("reader"), Sanitizer("dev")
    for r in data["train"]:
        assert r["reader"] == reader.clean(r["input"])
        assert r["dev"] == dev.clean(r["input"])
        for f in r["findings"]:
            assert r["input"][f["start"]:f["end"]].strip() == f["text"]
        if "--dry-run" in r["input"] and not r["injected"]:
            assert not r["changed"], r["input"]  # hard negatives must not change
    assert {r["lang"] for r in data["train"]} == {"en", "ko"}
    assert len(data["conformance"]) >= 100
