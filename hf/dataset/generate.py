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
# {n}/{m} numbers, {i} at most {m}, {a}-{b} a year range, {name} identifiers, {path}, {url}, {kv}, {ver}, {branch},
# {ms}, {pct}, {loss}, {code}, {port}. Every fifth template is held out for the test split.
EN = [
    "Saved {n} rows to {name}", "Synced {n} records from {name}", "Deployed {name} to production",
    "Upload failed for {path}", "Retrying connection to {name} in {n}s", "Cache warmed for {name}",
    "Processed batch {i} of {m}", "User {name} signed in", "Payment {name} captured", "Job {name} finished",
    "Disk usage at {pct}% on {name}", "Migrated {n} tables", "Request to {url} timed out",
    "Loaded config from {path}", "Indexed {n} documents", "Queue {name} drained", "Backup completed for {name}",
    "Rotated keys for {name}", "Scaled {name} to {n} replicas", "Validation passed for {name}",
    "Skipped {n} duplicate rows", "Exported report for {a}-{b}", "Rate limit reached: {kv}",
    "Health check ok for {name}", "Compiled {n} modules", "Rolled back {name}", "Server listening on port {port}",
    "Build {ver} passed in {ms}ms", "Tests passed: {i} of {m}", "{n} tests failed in {name}",
    "Pushed {ver} to the registry", "Merged {branch} into main", "Created branch {branch}",
    "Epoch {n} finished, loss {loss}", "Checkpoint saved to {path}", "Model {name} loaded in {ms}ms",
    "Evaluated {n} samples, accuracy {pct}%", "Connection pool for {name} exhausted",
    "Slow query on {name} took {ms}ms", "Webhook delivered to {url}", "Email sent to {n} recipients",
    "Token refreshed for {name}", "Login failed for {name}: {kv}", "Certificate for {name} expires in {n} days",
    "Restarted {name} after {n} crashes", "Memory usage at {n}MB on {name}", "Downloaded {n} files from {url}",
    "Parsed {n} lines from {path}", "Wrote {n} bytes to {path}", "Cleaned up {n} temp files",
    "Feature flag {name} enabled", "Cron job {name} started", "Order {n} shipped", "Refund issued for order {n}",
    "Invoice {n} generated for {name}", "Notification queued for {name}", "Session expired for {name}",
    "Retry {i} of {m} for {name}", "Lock acquired on {name}", "Snapshot of {name} created",
    "Replica {name} is {n}s behind", "Index rebuilt for {name} in {ms}ms", "Schema version is now {ver}",
    "Seeded {n} rows into {name}", "Imported {n} contacts from {path}", "Sent {n} events to {name}",
    "Received {n} messages from {name}", "Worker {name} picked up job {n}", "Pipeline {name} took {ms}ms",
    "Bundle size is {n}KB", "Linted {n} files, {i} warnings", "Release {ver} tagged",
    "Container {name} exited with code {code}", "Pod {name} is ready", "DNS for {name} updated",
    "Quota for {name} at {pct}%", "Archived {n} logs from {a}-{b}", "Report for {a}-{b} is ready",
    "Fetched {n} pages from {url}", "Starting {name} with {kv}",
]
KO = [
    "{name}에 {n}건 저장했습니다", "{name}에서 {n}건 동기화했습니다", "{name} 운영 환경에 배포했습니다",
    "{path} 업로드에 실패했습니다", "{n}초 후 {name} 연결을 다시 시도합니다", "{name} 캐시를 채웠습니다",
    "{m}개 중 {i}번째 묶음을 처리했습니다", "{name} 사용자가 로그인했습니다", "{name} 결제를 승인했습니다",
    "{name} 작업을 마쳤습니다", "{name} 디스크 사용량 {pct}%", "테이블 {n}개를 옮겼습니다", "{url} 요청 시간이 초과되었습니다",
    "{path}에서 설정을 읽었습니다", "문서 {n}개를 색인했습니다", "{name} 대기열을 비웠습니다", "{name} 백업을 마쳤습니다",
    "{name} 키를 교체했습니다", "{name}을 복제본 {n}개로 늘렸습니다", "{name} 검증을 통과했습니다",
    "중복 행 {n}개를 건너뛰었습니다", "{a}-{b}년 보고서를 내보냈습니다", "요청 한도에 도달했습니다: {kv}",
    "{name} 상태 확인 정상", "모듈 {n}개를 컴파일했습니다", "{name}을 되돌렸습니다", "{port} 포트에서 대기 중입니다",
    "빌드 {ver} 통과 ({ms}ms)", "테스트 {m}개 중 {i}개 통과", "{name}에서 테스트 {n}개 실패",
    "{ver}을 레지스트리에 올렸습니다", "{branch} 브랜치를 main에 병합했습니다", "{branch} 브랜치를 만들었습니다",
    "{n}번째 에폭 종료, 손실 {loss}", "체크포인트를 {path}에 저장했습니다", "{name} 모델을 {ms}ms 만에 불러왔습니다",
    "샘플 {n}개 평가, 정확도 {pct}%", "{name} 연결 풀이 가득 찼습니다", "{name} 느린 쿼리 {ms}ms",
    "{url}로 웹훅을 보냈습니다", "{n}명에게 메일을 보냈습니다", "{name} 토큰을 갱신했습니다",
    "{name} 로그인 실패: {kv}", "{name} 인증서가 {n}일 후 만료됩니다", "{n}번 중단된 {name}을 다시 시작했습니다",
    "{name} 메모리 사용량 {n}MB", "{url}에서 파일 {n}개를 받았습니다", "{path}에서 {n}줄을 읽었습니다",
    "{path}에 {n}바이트를 썼습니다", "임시 파일 {n}개를 정리했습니다", "{name} 기능 플래그를 켰습니다",
    "{name} 예약 작업을 시작했습니다", "주문 {n}번을 발송했습니다", "주문 {n}번 환불을 처리했습니다",
    "{name} 청구서 {n}번을 만들었습니다", "{name} 알림을 대기열에 넣었습니다", "{name} 세션이 만료되었습니다",
    "{name} 재시도 {m}번 중 {i}번째", "{name} 잠금을 얻었습니다", "{name} 스냅숏을 만들었습니다",
    "{name} 복제본이 {n}초 뒤처져 있습니다", "{name} 색인을 {ms}ms 만에 다시 만들었습니다", "스키마 버전 {ver}",
    "{name}에 {n}행을 채웠습니다", "{path}에서 연락처 {n}개를 가져왔습니다", "{name}에 이벤트 {n}개를 보냈습니다",
    "{name}에서 메시지 {n}개를 받았습니다", "{name} 워커가 {n}번 작업을 가져갔습니다", "{name} 파이프라인 {ms}ms 소요",
    "번들 크기 {n}KB", "파일 {n}개 검사, 경고 {i}개", "{ver} 릴리스 태그를 달았습니다",
    "{name} 컨테이너가 코드 {code}로 종료되었습니다", "{name} 파드 준비 완료", "{name} DNS를 갱신했습니다",
    "{name} 할당량 {pct}% 사용", "{a}-{b}년 로그 {n}개를 보관했습니다", "{a}-{b}년 보고서가 준비되었습니다",
    "{url}에서 페이지 {n}개를 가져왔습니다", "{kv} 설정으로 {name}을 시작합니다",
]
TEMPLATES = {"en": EN, "ko": KO}
HELD_OUT = 5  # template i goes to the test split when i % HELD_OUT == HELD_OUT - 1
TAILS = {
    "en": ["done", "all good", "no errors", "see details", "next step queued", "retry scheduled", "check the dashboard"],
    "ko": ["완료", "문제 없음", "오류 없음", "자세한 내용 확인", "다음 단계 대기 중", "재시도 예약됨", "대시보드 확인"],
}
NAMES = ["orders", "users-db", "billing", "api-gateway", "k8s-node-01", "search", "auth", "reports", "inventory",
         "worker-3", "payments", "cdn", "mailer", "etl", "analytics", "session-store", "jobs", "ledger", "media",
         "notifier", "gateway-eu", "redis-main", "pg-replica-2", "checkout", "recommender", "uploader", "scheduler"]
PATHS = ["/var/log/app.log", "./config/app.yaml", "~/data/export.csv", "/tmp/build-42.tar.gz", "../shared/keys.json",
         "C:\\logs\\service.log", "./models/ckpt-0007.pt", "/etc/nginx/conf.d/site.conf", "s3://backups/2025/db.dump"]
URLS = ["https://api.example.com/v2/orders", "https://status.example.org/incidents/42", "http://localhost:8080/health",
        "https://hooks.example.com/build?id=77", "http://10.0.0.12:9200/_cluster/health"]
KVS = ["user_id=42", "retry=3", "region=ap-northeast-2", "limit=1000", "trace_id=9f2c-77a1", "env=staging",
       "timeout=30s", "attempt=2/5", "status=503"]
VERSIONS = ["v1.4.2", "v2.0.0-rc.1", "0.9.13", "v3.1.0", "2025.11.0"]
BRANCHES = ["fix/login-retry", "feat/export-csv", "chore/deps", "release/2.1", "hotfix/null-check"]

# --- traces ------------------------------------------------------------------------------------
STATUS = {"ok": ["✅", "✔️", "🟢"], "fail": ["❌", "🔴", "⛔"], "warn": ["⚠️", "🟡", "🚨"]}
PICTO = ["🚀", "🎉", "✨", "🔥", "📦", "💾", "🔧", "📊", "🧹", "👀", "💡", "🛠️", "🙌", "📈", "🧪", "⏱️"]
DASHES = ["—", "–", "―", "ㅡ", "─"]
SEPARATORS = ["==========", "----------", "──────────", "ㅡㅡㅡㅡㅡㅡ", "**********", "━━━━━━━━━━", "ーーーーーー", "一一一一一一"]
# Chatty openers. The first ones match slopdam's tone.chatty rule (which only reports them); the
# rest are not covered by any rule. Either way `target` drops them and `reader` keeps them.
CHATTY = {
    "en": ["Let's go!", "Here's the summary:", "Awesome!", "Voila!", "Great news!", "Good news:", "Alright,",
           "All set!", "Heads up:", "Just so you know,", "Quick update:", "Nice!", "Boom!", "Done and dusted:"],
    "ko": ["살펴보겠습니다.", "해볼게요.", "해보겠습니다.", "좋은 소식입니다!", "자,", "알려드립니다:", "참고로",
           "짜잔!", "확인해 보니", "정리하면"],
}
# Filler adverbs. Korean ones match tone.filler (removed at the strong level); "Successfully" has no rule.
FILLER = {"ko": ["성공적으로 ", "완벽하게 ", "무사히 ", "드디어 "], "en": ["Successfully "]}
BLOCK_TITLES = {"en": ["## Summary", "### Results", "**Status**", "## Done"], "ko": ["## 요약", "### 결과", "**상태**", "## 완료"]}

KINDS = ["status_emoji", "pictograph", "bold", "inline_dash", "range_dash", "separator", "heading", "bullet",
         "curly_quotes", "ellipsis", "arrow", "fullwidth", "invisible", "nbsp", "exclaim", "filler", "chatty",
         "unicode_hyphen", "wave_dash", "code_fence"]
REWRITE_ONLY = {"filler", "chatty"}  # kept out of `target`
LINE_SHAPE = {"heading", "bullet", "separator", "code_fence"}  # not used inside a multi-line block


def fill(rng: random.Random, template: str, range_dash: str = "-") -> str:
    a, m = rng.randint(2015, 2025), rng.randint(10, 99)
    template = template.replace("{a}-{b}", "{a}" + range_dash + "{b}")
    return template.format(
        n=rng.randint(2, 9999), m=m, i=rng.randint(1, m), name=rng.choice(NAMES), path=rng.choice(PATHS),
        url=rng.choice(URLS), kv=rng.choice(KVS), a=a, b=a + rng.randint(1, 3), port=rng.choice([80, 443, 8080, 5432]),
        ver=rng.choice(VERSIONS), branch=rng.choice(BRANCHES), ms=rng.randint(3, 98000), pct=round(rng.uniform(50, 99.9), 1),
        loss=round(rng.uniform(0.01, 2.5), 4), code=rng.choice([0, 1, 2, 137, 143]),
    )


def hard_negative(rng: random.Random, base: str) -> str:
    """Text that looks risky but that slopdam must leave alone."""
    return rng.choice([
        lambda: f"{base} --dry-run {rng.choice(KVS)} {rng.choice(URLS)}",
        lambda: f"{base} (exit={rng.choice([0, 1])}, {rng.choice(KVS)})",
        lambda: f"{base} [{rng.choice(PATHS)}]",
        lambda: f"{base} -> {rng.choice(NAMES)}",
        lambda: f"{base}: {rng.choice(VERSIONS)} - {rng.choice(BRANCHES)}",
        lambda: f"{base} --since={rng.randint(2015, 2025)}-01-01 --until=now",
    ])()


def line(rng: random.Random, lang: str, templates: list, roll: float, inline: bool = False) -> dict:
    """One message: a clean base, then traces injected according to a random plan.

    Two texts are built side by side: `text` gets every trace, `kept` gets all but the
    rewrite-only ones (filler, chatty), so slopdam's reader output of `kept` is the target."""
    tid = rng.randrange(len(templates))
    template = templates[tid][1]
    pool = [k for k in KINDS if not (inline and k in LINE_SHAPE)]
    kinds = rng.sample(pool, k=rng.choice([1, 1, 2, 2, 3, 4])) if roll >= 0.25 else []
    if "heading" in kinds and "bullet" in kinds:
        kinds.remove("bullet")  # "• # text" is not something anyone writes
    # A range like 2024-2025 gets an en or em dash only when that trace is injected.
    base = fill(rng, template, rng.choice(["–", "—", "ㅡ"]) if "range_dash" in kinds else "-")
    tail = rng.choice(TAILS[lang])
    tid = f"{lang}-{templates[tid][0]:03d}"
    if roll < 0.15:  # clean message: nothing to change
        return {"lang": lang, "template_id": tid, "input": base, "kept": base, "injected": []}
    if roll < 0.25:  # hard negative: looks risky, must not change
        text = hard_negative(rng, base)
        if READER.clean(text) != text:
            text = f"{base} --dry-run {rng.choice(KVS)}"
        return {"lang": lang, "template_id": tid, "input": text, "kept": text, "injected": []}
    t = [base, base]  # [input, kept]

    def both(f):
        t[0], t[1] = f(t[0]), f(t[1])

    if "range_dash" in kinds and "{a}-{b}" not in template:
        a, d, b = rng.randint(1, 20), rng.choice(DASHES[:2]), rng.randint(1, 9)
        both(lambda s: s + (f" ({a}{d}{a + b})" if lang == "en" else f" ({a}{d}{a + b}건)"))
    if "wave_dash" in kinds:
        a, d, b = rng.randint(1, 20), rng.choice(["〜", "～"]), rng.randint(1, 9)
        both(lambda s: s + (f" ({a}{d}{a + b})" if lang == "en" else f" ({a}{d}{a + b}건)"))
    if "bold" in kinds:
        i = rng.randrange(len(t[0].split(" ")))
        both(lambda s: " ".join(f"**{w}**" if j == i else w for j, w in enumerate(s.split(" "))))
    if "inline_dash" in kinds:
        d = rng.choice(DASHES)
        both(lambda s: f"{s} {d} {tail}")
    if "curly_quotes" in kinds:
        q = " “" + rng.choice(NAMES) + "”" if lang == "en" else " ‘" + rng.choice(NAMES) + "’"
        both(lambda s: s + q)
    if "unicode_hyphen" in kinds:
        h, n = rng.choice(["−", "‐", "－"]), rng.randint(1, 99)
        both(lambda s: f"{s} ({h}{n}%)")
    if "ellipsis" in kinds:
        both(lambda s: s + "…")
    if "arrow" in kinds:
        arrow = f" {rng.choice(NAMES)} {rng.choice(['→', '⇒', '➜'])} {rng.choice(NAMES)}"
        both(lambda s: s + arrow)
    if "fullwidth" in kinds:
        n = rng.randint(1, 9)
        both(lambda s: s.replace(":", "：", 1) if ":" in s else s + f"（{n}）")
    if "invisible" in kinds:
        i, z = rng.randrange(1, len(t[0])), rng.choice(["\u200b", "\u2060", "\ufeff"])
        both(lambda s: s[:i] + z + s[i:])
    if "nbsp" in kinds:
        both(lambda s: s.replace(" ", "\u00a0", 1))
    if "exclaim" in kinds:
        both(lambda s: s + ("!" if lang == "en" else "!!"))
    if "filler" in kinds:
        f = rng.choice(FILLER[lang])
        if lang == "ko":
            t[0] = f + t[0]
        elif t[0][:1].isupper() and t[0][1:2].islower():
            t[0] = f + t[0][0].lower() + t[0][1:]
        else:
            kinds.remove("filler")
            if not kinds:
                kinds.append("pictograph")
    if "chatty" in kinds:
        t[0] = rng.choice(CHATTY[lang]) + " " + t[0]
    if "pictograph" in kinds:
        p, front = rng.choice(PICTO), rng.random() < 0.5
        both(lambda s: f"{p} {s}" if front else f"{s} {p}")
    if "status_emoji" in kinds:
        e = rng.choice(STATUS[rng.choice(list(STATUS))])
        both(lambda s: f"{e} {s}")
    if "heading" in kinds:
        h = rng.choice(["## ", "### ", "# "])
        both(lambda s: h + s)
    if "bullet" in kinds:
        b = rng.choice(["• ", "▶ ", "◦ "])
        both(lambda s: b + s)
    if "separator" in kinds:
        sep, around = rng.choice(SEPARATORS), rng.random() < 0.5
        both(lambda s: f"{sep}\n{s}\n{sep}" if around else f"{s}\n{sep}")
    if "code_fence" in kinds:
        both(lambda s: f"```\n{s}\n```")
    return {"lang": lang, "template_id": tid, "input": t[0], "kept": t[1], "injected": sorted(kinds)}


def make(rng: random.Random, lang: str, templates: list) -> dict:
    """A single line, or (8% of the time) a multi-line summary block the way assistants write them:
    an optional title, then two to four items, each with inline traces only."""
    if rng.random() >= 0.08:
        return line(rng, lang, templates, rng.random())
    parts = [line(rng, lang, templates, 0.25 + 0.75 * rng.random(), inline=True) for _ in range(rng.randint(2, 4))]
    title = [rng.choice(BLOCK_TITLES[lang])] if rng.random() < 0.6 else []
    bullet = rng.choice(["- ", "• ", "* ", ""])
    join = lambda key: "\n".join(title + [bullet + p[key] for p in parts])  # noqa: E731
    injected = sorted({k for p in parts for k in p["injected"]} | {"block"})
    return {"lang": lang, "template_id": parts[0]["template_id"], "input": join("input"), "kept": join("kept"),
            "injected": injected}


READER = Sanitizer("reader")
DEV = Sanitizer("dev")
STRONG = Sanitizer("reader", "strong")


def label(row: dict) -> dict:
    text = row["input"]
    row["reader"] = READER.clean(text)
    row["dev"] = DEV.clean(text)
    row["reader_strong"] = STRONG.clean(text)
    row["target"] = READER.clean(row.pop("kept"))
    row["findings"] = [
        {"rule_id": f.rule_id, "start": f.start, "end": f.end, "text": f.text, "fix": f.fix}
        for f in READER.findings(text)
    ]
    row["rule_ids"] = sorted({f["rule_id"] for f in row["findings"]})
    row["changed"] = row["reader"] != text
    return row


def build(rows: int, validation_rows: int, test_rows: int, seed: int) -> dict:
    rng = random.Random(seed)
    pools = {split: {lang: [(i, t) for i, t in enumerate(TEMPLATES[lang])
                            if (i % HELD_OUT == HELD_OUT - 1) == (split == "test")] for lang in TEMPLATES}
             for split in ("train", "validation", "test")}
    seen, splits = set(), {"train": [], "validation": [], "test": []}
    for split, count in (("test", test_rows), ("validation", validation_rows), ("train", rows)):
        while len(splits[split]) < count:
            lang = "ko" if rng.random() < 0.5 else "en"
            row = make(rng, lang, pools[split][lang])
            if row["input"] in seen:
                continue  # no input appears twice, within or across splits
            seen.add(row["input"])
            row["id"] = f"{split}-{len(splits[split]):06d}"
            splits[split].append(label(row))
    conformance = []
    spec = json.loads((ROOT / "spec" / "conformance.json").read_text(encoding="utf-8"))
    for group in spec["groups"]:
        for i, c in enumerate(group["cases"]):
            conformance.append({"id": f"{group['id']}-{i:02d}", "group": group["id"], "input": c["input"],
                                "options": json.dumps(c.get("options", {})), "reader": c["reader"], "dev": c["dev"]})
    return {**splits, "conformance": conformance}


FIELDS = ["id", "lang", "template_id", "input", "reader", "dev", "reader_strong", "target", "changed", "injected",
          "rule_ids", "findings"]
SPLITS = ("train", "validation", "test")


def write(data: dict, out: Path) -> dict:
    (out / "data").mkdir(parents=True, exist_ok=True)
    (out / "conformance").mkdir(parents=True, exist_ok=True)
    paths = {name: out / "data" / f"{name}.jsonl" for name in SPLITS}
    paths["conformance"] = out / "conformance" / "test.jsonl"
    digests = {}
    for name, path in paths.items():
        rows = data[name]
        lines = [json.dumps({k: r[k] for k in (FIELDS if name != "conformance" else r)}, ensure_ascii=False) for r in rows]
        body = "\n".join(lines) + "\n"
        path.write_text(body, encoding="utf-8")
        digests[name] = hashlib.sha256(body.encode()).hexdigest()[:16]
    train = data["train"]
    stats = {
        "slopdam_version": slopdam.__version__, "spec_version": json.loads((ROOT / "spec" / "rules.json").read_text())["spec_version"],
        "rows": {k: len(v) for k, v in data.items()},
        "templates": {split: len({r["template_id"] for r in data[split]}) for split in SPLITS},
        "changed_share": round(sum(r["changed"] for r in train) / len(train), 3),
        "target_differs_share": round(sum(r["target"] != r["reader"] for r in train) / len(train), 3),
        "lang": {l: sum(r["lang"] == l for r in train) for l in ("en", "ko")},
        "injected": dict(sorted(((k, sum(k in r["injected"] for r in train)) for k in
                                 {x for r in train for x in r["injected"]}), key=lambda x: -x[1])),
        "rules": dict(sorted(((rid, sum(rid in r["rule_ids"] for r in train)) for rid in
                              {x for r in train for x in r["rule_ids"]}), key=lambda x: -x[1])),
        "sha256_16": digests,
    }
    (out / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return stats


def main(argv: list) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--rows", type=int, default=100000, help="train rows")
    p.add_argument("--validation-rows", type=int, default=5000)
    p.add_argument("--test-rows", type=int, default=5000)
    p.add_argument("--seed", type=int, default=20261125)
    p.add_argument("--out", type=Path, default=OUT)
    p.add_argument("--check", action="store_true", help="build twice and compare (determinism)")
    a = p.parse_args(argv)
    stats = write(build(a.rows, a.validation_rows, a.test_rows, a.seed), a.out)
    if a.check:
        again = write(build(a.rows, a.validation_rows, a.test_rows, a.seed), a.out.with_name(a.out.name + "-check"))
        if again["sha256_16"] != stats["sha256_16"]:
            print("not deterministic", file=sys.stderr)
            return 1
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
