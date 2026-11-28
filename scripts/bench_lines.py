# SPDX-License-Identifier: MIT
"""Per-line latency of slopdam on log-slop's test split, in every port that runs here.

    python scripts/bench_lines.py              # rules: Python, JavaScript (needs `cd js && npm run build`), Go
    python scripts/bench_lines.py --chatter    # also the chatter model on CPU (needs slopdam[chatter])

Each line is timed on its own after a warm-up pass, and the table gives the median, p95 and p99 of
those times plus lines per second. The inputs are the 5,000 test rows of hf/dataset/generate.py at
its default seed, so every run sees the same text. scripts/bench.py is the quick version CI runs.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "hf" / "dataset"))

from slopdam import Sanitizer, __version__  # noqa: E402

JS = """
import { readFileSync } from "node:fs";
const { Sanitizer } = await import(process.argv[1]);
const lines = readFileSync(process.argv[2], "utf8").trim().split("\\n").map((l) => JSON.parse(l).input);
const s = new Sanitizer({ profile: process.argv[3], level: process.argv[4] });
for (const l of lines) s.clean(l);
const ns = lines.map((l) => { const t = process.hrtime.bigint(); s.clean(l); return Number(process.hrtime.bigint() - t); });
console.log(JSON.stringify(ns));
"""


def inputs() -> list:
    import generate  # hf/dataset/generate.py

    return [r["input"] for r in generate.build(0, 0, 5000, 20261125)["test"]]


def summary(ns: list) -> tuple:
    ns = sorted(ns)
    pick = lambda q: ns[min(len(ns) - 1, int(q * len(ns)))] / 1000  # noqa: E731
    return statistics.median(ns) / 1000, pick(0.95), pick(0.99), len(ns) / (sum(ns) / 1e9)


def python_times(lines, profile, level):
    s = Sanitizer(profile, level)
    for line in lines:
        s.clean(line)
    out = []
    for line in lines:
        t = time.perf_counter_ns()
        s.clean(line)
        out.append(time.perf_counter_ns() - t)
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--chatter", action="store_true", help="also time the chatter model on CPU")
    a = p.parse_args(argv)
    lines = inputs()
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "lines.jsonl"
        data.write_text("".join(json.dumps({"input": x}, ensure_ascii=False) + "\n" for x in lines), encoding="utf-8")
        for profile, level in (("reader", "basic"), ("dev", "basic"), ("reader", "strong")):
            name = f"{profile}, {level}"
            rows.append((f"Python {platform.python_version()}", name, summary(python_times(lines, profile, level))))
            esm = ROOT / "js" / "dist" / "esm" / "index.js"
            if shutil.which("node") and esm.exists():
                out = subprocess.run(["node", "--input-type=module", "-e", JS, esm.as_uri(), str(data), profile, level],
                                     capture_output=True, text=True, check=True)
                rows.append((f"Node {subprocess.run(['node', '--version'], capture_output=True, text=True).stdout.strip()}",
                             name, summary(json.loads(out.stdout))))
            if shutil.which("go"):
                out = subprocess.run(["go", "run", "./internal/bench", str(data), profile, level], cwd=ROOT / "go",
                                     capture_output=True, text=True, check=True)
                go = subprocess.run(["go", "env", "GOVERSION"], capture_output=True, text=True).stdout.strip()
                rows.append((go.replace("go", "Go ", 1), name, summary(json.loads(out.stdout))))
        if a.chatter:
            from slopdam import chatter

            tagger = chatter.tagger()
            cleaned = [Sanitizer().clean(x) for x in lines[:1000]]
            tagger(cleaned[:50])
            ns = []
            for line in cleaned:
                t = time.perf_counter_ns()
                tagger([line])
                ns.append(time.perf_counter_ns() - t)
            rows.append(("chatter model, CPU", "one line at a time", summary(ns)))
            t = time.perf_counter_ns()
            tagger(cleaned, batch=64)
            per = (time.perf_counter_ns() - t) / len(cleaned)
            rows.append(("chatter model, CPU", "batches of 64", (per / 1000, None, None, 1e9 / per)))

    cpu = platform.processor() or platform.machine()
    try:
        cpu = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip() or cpu
    except OSError:
        pass
    print(f"slopdam {__version__}, {len(lines):,} lines of log-slop test, {cpu}, {platform.system()}\n")
    print("| Runtime | Setting | Median (µs) | p95 (µs) | p99 (µs) | Lines per second |")
    print("|---|---|---:|---:|---:|---:|")
    for runtime, name, (med, p95, p99, rate) in rows:
        f = lambda v: "" if v is None else f"{v:,.1f}"  # noqa: E731
        print(f"| {runtime} | {name} | {f(med)} | {f(p95)} | {f(p99)} | {rate:,.0f} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
