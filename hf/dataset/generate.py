# SPDX-License-Identifier: MIT
"""Build the slopdam/log-slop dataset for the Hugging Face Hub.

    python hf/dataset/generate.py                 # writes hf/dataset/out/
    python hf/dataset/generate.py --rows 200 --check   # small run, checks determinism

Every row is a log or console message written for this dataset (English or Korean), with
AI-style traces injected on purpose: em dashes and the Hangul ㅡ, emoji, markdown, curly quotes,
separators and so on. The labels (`reader`, `dev`, `findings`) come from the slopdam engine in
this repository, so they are exactly what slopdam outputs, not human judgments. The same seed
always gives the same files.

Only the standard library and slopdam are needed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import slopdam  # noqa: E402
from slopdam import Sanitizer  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"

# --- messages ----------------------------------------------------------------------------------
# {n} numbers, {a}/{b} a pair of numbers for ranges, {name} identifiers, {path}, {url}, {kv}.
EN = [
    "Saved {n} rows to {name}", "Synced {n} records from {name}", "Deployed {name} to production",
    "Upload failed for {path}", "Retrying connection to {name} in {n}s", "Cache warmed for {name}",
    "Processed batch {n} of {m}", "User {name} signed in", "Payment {name} captured", "Job {name} finished",
    "Disk usage at {n}% on {name}", "Migrated {n} tables", "Request to {url} timed out",
    "Loaded config from {path}", "Indexed {n} documents", "Queue {name} drained", "Backup completed for {name}",
    "Rotated keys for {name}", "Scaled {name} to {n} replicas", "Validation passed for {name}",
    "Skipped {n} duplicate rows", "Exported report for {a}-{b}", "Rate limit reached: {kv}",
    "Health check ok for {name}", "Compiled {n} modules", "Rolled back {name}", "Server listening on port {port}",
]
KO = [
    "{name}에 {n}건 저장했습니다", "{name}에서 {n}건 동기화했습니다", "{name} 운영 환경에 배포했습니다",
    "{path} 업로드에 실패했습니다", "{n}초 후 {name} 연결을 다시 시도합니다", "{name} 캐시를 채웠습니다",
    "{m}개 중 {n}번째 묶음을 처리했습니다", "{name} 사용자가 로그인했습니다", "{name} 결제를 승인했습니다",
    "{name} 작업을 마쳤습니다", "{name} 디스크 사용량 {n}%", "테이블 {n}개를 옮겼습니다", "{url} 요청 시간이 초과되었습니다",
    "{path}에서 설정을 읽었습니다", "문서 {n}개를 색인했습니다", "{name} 대기열을 비웠습니다", "{name} 백업을 마쳤습니다",
    "{name} 키를 교체했습니다", "{name}을 복제본 {n}개로 늘렸습니다", "{name} 검증을 통과했습니다",
    "중복 행 {n}개를 건너뛰었습니다", "{a}-{b}년 보고서를 내보냈습니다", "요청 한도에 도달했습니다: {kv}",
    "{name} 상태 확인 정상", "모듈 {n}개를 컴파일했습니다", "{name}을 되돌렸습니다", "{port} 포트에서 대기 중입니다",
]
TAILS = {
    "en": ["done", "all good", "no errors", "see details", "next step queued", "retry scheduled", "check the dashboard"],
    "ko": ["완료", "문제 없음", "오류 없음", "자세한 내용 확인", "다음 단계 대기 중", "재시도 예약됨", "대시보드 확인"],
}
NAMES = ["orders", "users-db", "billing", "api-gateway", "k8s-node-01", "search", "auth", "reports", "inventory",
         "worker-3", "payments", "cdn", "mailer", "etl", "analytics", "session-store", "jobs"]
PATHS = ["/var/log/app.log", "./config/app.yaml", "~/data/export.csv", "/tmp/build-42.tar.gz", "../shared/keys.json"]
URLS = ["https://api.example.com/v2/orders", "https://status.example.org/incidents/42", "http://localhost:8080/health"]
KVS = ["user_id=42", "retry=3", "region=ap-northeast-2", "limit=1000", "trace_id=9f2c-77a1"]

# --- traces ------------------------------------------------------------------------------------
STATUS = {"ok": ["✅", "✔️", "🟢"], "fail": ["❌", "🔴", "⛔"], "warn": ["⚠️", "🟡", "🚨"]}
PICTO = ["🚀", "🎉", "✨", "🔥", "📦", "💾", "🔧", "📊", "🧹", "👀", "💡", "🛠️"]
DASHES = ["—", "–", "―", "ㅡ", "─"]
SEPARATORS = ["==========", "----------", "──────────", "ㅡㅡㅡㅡㅡㅡ", "**********", "━━━━━━━━━━"]
CHATTY = {"en": ["Let's go!", "Here's the summary:", "Awesome!"], "ko": ["살펴보겠습니다.", "해볼게요."]}
FILLER = {"ko": ["성공적으로 ", "완벽하게 ", "무사히 "], "en": []}

KINDS = ["status_emoji", "pictograph", "bold", "inline_dash", "range_dash", "separator", "heading", "bullet",
         "curly_quotes", "ellipsis", "arrow", "fullwidth", "invisible", "nbsp", "exclaim", "filler", "chatty"]


def fill(rng: random.Random, template: str, range_dash: str = "-") -> str:
    a = rng.randint(2015, 2025)
    template = template.replace("{a}-{b}", "{a}" + range_dash + "{b}")
    return template.format(
        n=rng.randint(2, 9999), m=rng.randint(10, 99), name=rng.choice(NAMES), path=rng.choice(PATHS),
        url=rng.choice(URLS), kv=rng.choice(KVS), a=a, b=a + rng.randint(1, 3), port=rng.choice([80, 443, 8080, 5432]),
    )


def make(rng: random.Random, lang: str) -> dict:
    """One message: a clean base, then traces injected according to a random plan."""
    template = rng.choice(EN if lang == "en" else KO)
    roll = rng.random()
    kinds = rng.sample(KINDS, k=rng.choice([1, 1, 2, 2, 3, 4])) if roll >= 0.25 else []
    kinds = [k for k in kinds if k != "filler" or FILLER[lang]] or (["pictograph"] if kinds else [])
    # A range like 2024-2025 gets an en or em dash only when that trace is injected.
    base = fill(rng, template, rng.choice(["–", "—", "ㅡ"]) if "range_dash" in kinds else "-")
    tail = rng.choice(TAILS[lang])
    if roll < 0.15:  # clean message: nothing to change
        text, kinds = base, []
    elif roll < 0.25:  # hard negative: looks risky, must not change
        text = f"{base} --dry-run {rng.choice(KVS)} {rng.choice(URLS)}"
        kinds = []
    else:
        text = base
        if "range_dash" in kinds and "{a}-{b}" not in template:
            a = rng.randint(1, 20)
            text += f" ({a}{rng.choice(DASHES[:2])}{a + rng.randint(1, 9)})" if lang == "en" else f" ({a}{rng.choice(DASHES[:2])}{a + rng.randint(1, 9)}건)"
        if "bold" in kinds:
            words = text.split(" ")
            i = rng.randrange(len(words))
            words[i] = f"**{words[i]}**"
            text = " ".join(words)
        if "inline_dash" in kinds:
            text += f" {rng.choice(DASHES)} {tail}"
        if "curly_quotes" in kinds:
            text += " “" + rng.choice(NAMES) + "”" if lang == "en" else " ‘" + rng.choice(NAMES) + "’"
        if "ellipsis" in kinds:
            text += "…"
        if "arrow" in kinds:
            text += f" {rng.choice(NAMES)} {rng.choice(['→', '⇒', '➜'])} {rng.choice(NAMES)}"
        if "fullwidth" in kinds:
            text = text.replace(":", "：", 1) if ":" in text else text + "（" + str(rng.randint(1, 9)) + "）"
        if "invisible" in kinds:
            i = rng.randrange(1, len(text))
            text = text[:i] + rng.choice(["\u200b", "\u2060", "\ufeff"]) + text[i:]
        if "nbsp" in kinds:
            text = text.replace(" ", "\u00a0", 1)
        if "exclaim" in kinds:
            text += "!" if lang == "en" else "!!"
        if "filler" in kinds and FILLER[lang]:
            text = rng.choice(FILLER[lang]) + text
        if "chatty" in kinds:
            text = rng.choice(CHATTY[lang]) + " " + text
        if "pictograph" in kinds:
            text = text + " " + rng.choice(PICTO) if rng.random() < 0.5 else rng.choice(PICTO) + " " + text
        if "status_emoji" in kinds:
            text = rng.choice(STATUS[rng.choice(list(STATUS))]) + " " + text
        if "heading" in kinds:
            text = rng.choice(["## ", "### ", "# "]) + text
        if "bullet" in kinds:
            text = rng.choice(["• ", "▶ ", "◦ "]) + text
        if "separator" in kinds:
            sep = rng.choice(SEPARATORS)
            text = f"{sep}\n{text}\n{sep}" if rng.random() < 0.5 else f"{text}\n{sep}"
    return {"lang": lang, "input": text, "injected": sorted(kinds)}


READER = Sanitizer("reader")
DEV = Sanitizer("dev")
STRONG = Sanitizer("reader", "strong")


def label(row: dict) -> dict:
    text = row["input"]
    row["reader"] = READER.clean(text)
    row["dev"] = DEV.clean(text)
    row["reader_strong"] = STRONG.clean(text)
    row["findings"] = [
        {"rule_id": f.rule_id, "start": f.start, "end": f.end, "text": f.text, "fix": f.fix}
        for f in READER.findings(text)
    ]
    row["rule_ids"] = sorted({f["rule_id"] for f in row["findings"]})
    row["changed"] = row["reader"] != text
    return row


def build(rows: int, test_rows: int, seed: int) -> dict:
    rng = random.Random(seed)
    seen, splits = set(), {"train": [], "test": []}
    for split, count in (("test", test_rows), ("train", rows)):
        while len(splits[split]) < count:
            row = make(rng, "ko" if rng.random() < 0.5 else "en")
            if row["input"] in seen:
                continue  # no input appears twice, within or across splits
            seen.add(row["input"])
            row["id"] = f"{split}-{len(splits[split]):05d}"
            splits[split].append(label(row))
    conformance = []
    spec = json.loads((ROOT / "spec" / "conformance.json").read_text(encoding="utf-8"))
    for group in spec["groups"]:
        for i, c in enumerate(group["cases"]):
            conformance.append({"id": f"{group['id']}-{i:02d}", "group": group["id"], "input": c["input"],
                                "options": json.dumps(c.get("options", {})), "reader": c["reader"], "dev": c["dev"]})
    return {"train": splits["train"], "test": splits["test"], "conformance": conformance}


FIELDS = ["id", "lang", "input", "reader", "dev", "reader_strong", "changed", "injected", "rule_ids", "findings"]


def write(data: dict, out: Path) -> dict:
    (out / "data").mkdir(parents=True, exist_ok=True)
    (out / "conformance").mkdir(parents=True, exist_ok=True)
    paths = {"train": out / "data" / "train.jsonl", "test": out / "data" / "test.jsonl",
             "conformance": out / "conformance" / "test.jsonl"}
    digests = {}
    for name, path in paths.items():
        rows = data[name]
        lines = [json.dumps({k: r[k] for k in (FIELDS if name != "conformance" else r)}, ensure_ascii=False) for r in rows]
        body = "\n".join(lines) + "\n"
        path.write_text(body, encoding="utf-8")
        digests[name] = hashlib.sha256(body.encode()).hexdigest()[:16]
    stats = {
        "slopdam_version": slopdam.__version__, "spec_version": json.loads((ROOT / "spec" / "rules.json").read_text())["spec_version"],
        "rows": {k: len(v) for k, v in data.items()},
        "changed_share": round(sum(r["changed"] for r in data["train"]) / len(data["train"]), 3),
        "lang": {l: sum(r["lang"] == l for r in data["train"]) for l in ("en", "ko")},
        "rules": dict(sorted(((rid, sum(rid in r["rule_ids"] for r in data["train"])) for rid in
                              {x for r in data["train"] for x in r["rule_ids"]}), key=lambda x: -x[1])),
        "sha256_16": digests,
    }
    (out / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return stats


def main(argv: list) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--rows", type=int, default=20000, help="train rows")
    p.add_argument("--test-rows", type=int, default=2000)
    p.add_argument("--seed", type=int, default=20261125)
    p.add_argument("--out", type=Path, default=OUT)
    p.add_argument("--check", action="store_true", help="build twice and compare (determinism)")
    a = p.parse_args(argv)
    stats = write(build(a.rows, a.test_rows, a.seed), a.out)
    if a.check:
        again = write(build(a.rows, a.test_rows, a.seed), a.out.with_name(a.out.name + "-check"))
        if again["sha256_16"] != stats["sha256_16"]:
            print("not deterministic", file=sys.stderr)
            return 1
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
