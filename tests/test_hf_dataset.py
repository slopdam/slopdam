# SPDX-License-Identifier: MIT
"""The Hugging Face dataset generator: deterministic, and its labels are slopdam's output."""
import importlib.util
from pathlib import Path

from slopdam import Sanitizer

spec = importlib.util.spec_from_file_location("hf_generate", Path(__file__).resolve().parent.parent / "hf" / "dataset" / "generate.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


def test_same_seed_same_rows():
    assert gen.build(200, 20, 20, 7) == gen.build(200, 20, 20, 7)


def test_labels_match_slopdam_and_negatives_stay():
    data = gen.build(600, 60, 60, 11)
    inputs = [r["input"] for split in gen.SPLITS for r in data[split]]
    assert len(inputs) == len(set(inputs))  # no input in two splits or twice
    reader, dev = Sanitizer("reader"), Sanitizer("dev")
    for r in data["train"]:
        assert r["reader"] == reader.clean(r["input"])
        assert r["dev"] == dev.clean(r["input"])
        for f in r["findings"]:
            assert r["input"][f["start"]:f["end"]].strip() == f["text"]
        if not r["injected"]:
            assert not r["changed"], r["input"]  # clean rows and hard negatives must not change
        if not set(r["injected"]) & gen.REWRITE_ONLY:
            assert r["target"] == r["reader"]  # target only goes beyond the rules for filler and chatter
        else:
            assert r["target"] != r["reader"]
    assert {r["lang"] for r in data["train"]} == {"en", "ko"}
    assert len(data["conformance"]) >= 100


def test_test_split_uses_held_out_templates():
    data = gen.build(600, 60, 60, 13)
    seen = {r["template_id"] for split in ("train", "validation") for r in data[split]}
    assert seen.isdisjoint({r["template_id"] for r in data["test"]})


def test_test_split_uses_held_out_openers():
    data = gen.build(600, 60, 300, 17)
    held = tuple(p for lang in ("en", "ko") for p in gen.CHATTY_TEST[lang] + gen.FILLER_TEST[lang])
    trained = tuple(p for lang in ("en", "ko") for p in gen.CHATTY[lang] + gen.FILLER[lang])
    assert not set(held) & set(trained)
    rewrites = [r for r in data["test"] if r["target"] != r["reader"]]
    assert rewrites and all(not r["input"].startswith(trained) for r in rewrites if "block" not in r["injected"]
                            and not set(r["injected"]) - {"chatty", "filler"})


def test_lookalikes_are_untouched_and_held_out():
    for lang in ("en", "ko"):
        assert not set(gen.LOOKALIKE[lang]) & set(gen.LOOKALIKE_TEST[lang])
    reader = Sanitizer("reader")
    rng = gen.random.Random(3)
    for lang in ("en", "ko"):
        for t in gen.LOOKALIKE[lang] + gen.LOOKALIKE_TEST[lang]:
            text = gen.fill(rng, t)
            assert reader.clean(text) == text, text
