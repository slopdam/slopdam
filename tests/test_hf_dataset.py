# SPDX-License-Identifier: MIT
"""The Hugging Face dataset generator: deterministic, and its labels are slopdam's output."""
import importlib.util
import json
import re
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
    assert {r["lang"] for r in data["train"]} == {"en", "ko", "ja", "zh"}
    assert len(data["conformance"]) >= 100


def test_test_split_uses_held_out_templates():
    data = gen.build(600, 60, 60, 13)
    seen = {r["template_id"] for split in ("train", "validation") for r in data[split]}
    assert seen.isdisjoint({r["template_id"] for r in data["test"]})


def test_test_split_uses_held_out_openers():
    data = gen.build(600, 60, 300, 17)
    held = tuple(p for lang in gen.TEMPLATES for p in gen.CHATTY_TEST[lang] + gen.FILLER_TEST[lang])
    trained = tuple(p for lang in gen.TEMPLATES for p in gen.CHATTY[lang] + gen.FILLER[lang])
    assert not set(held) & set(trained)
    rewrites = [r for r in data["test"] if r["target"] != r["reader"]]
    assert rewrites and all(not r["input"].startswith(trained) for r in rewrites if "block" not in r["injected"]
                            and not set(r["injected"]) - {"chatty", "filler"})


def test_lookalikes_are_untouched_and_held_out():
    for lang in gen.TEMPLATES:
        assert not set(gen.LOOKALIKE[lang]) & set(gen.LOOKALIKE_TEST[lang])
    reader = Sanitizer("reader")
    rng = gen.random.Random(3)
    for lang in gen.TEMPLATES:
        for t in gen.LOOKALIKE[lang] + gen.LOOKALIKE_TEST[lang]:
            text = gen.fill(rng, t)
            assert reader.clean(text) == text, text


def test_structured_rows_keep_their_structure():
    data = gen.build(1500, 50, 300, 19)
    rows = [r for split in gen.SPLITS for r in data[split]]
    jsonl = [r for r in rows if "json_line" in r["injected"]]
    assert jsonl and all(json.loads(r["reader"]) and json.loads(r["dev"]) for r in jsonl)
    logfmt = [r for r in rows if "logfmt" in r["injected"]]
    unescaped = re.compile(r'(?<!\\)"')
    assert logfmt and all(r["reader"].startswith("ts=") and len(unescaped.findall(r["reader"])) == 2 for r in logfmt)
    shapes = [r for r in rows if r["template_id"].startswith("shape-")]
    assert shapes and all(not r["changed"] and r["dev"] == r["input"] for r in shapes)
    train = {r["template_id"] for r in data["train"] if r["template_id"].startswith("shape-")}
    test = {r["template_id"] for r in data["test"] if r["template_id"].startswith("shape-")}
    assert train and test and train.isdisjoint(test)


def test_japanese_and_chinese_keep_full_width_punctuation():
    data = gen.build(1500, 50, 50, 23)
    rows = [r for r in data["train"] if r["lang"] in gen.CJK]
    assert rows and "fullwidth" not in {k for r in rows for k in r["injected"]}
    for r in rows:
        for c in "，：（）":
            assert r["reader"].count(c) == r["input"].count(c), r["input"]


def test_japanese_and_chinese_labels_are_kept_and_held_out():
    for lang in gen.CJK:
        assert not set(gen.LABELS[lang]) & set(gen.LABELS_TEST[lang])
    data = gen.build(1500, 50, 300, 29)
    labeled = [r for r in data["test"] if r["lang"] in gen.CJK and "：" in r["target"].split("\n")[0][:6]]
    assert labeled
    for r in data["test"]:
        head = r["target"].split("：")[0]
        assert head not in sum((gen.LABELS[l] for l in gen.CJK), []), r["input"]
