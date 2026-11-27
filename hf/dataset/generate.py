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
SPLITS = ("train", "validation", "test")
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
# Chatty openers. A few match slopdam's tone.chatty rule (which only reports them); the rest are
# not covered by any rule. Either way `target` drops them and `reader` keeps them. The *_TEST lists
# are only used in the test split, so a model scored there has to handle openers it never saw.
CHATTY = {
    "en": ["Let's go!", "Here's the summary:", "Awesome!", "Great news!", "Alright,", "All set!", "Heads up:",
           "Just so you know,", "Quick update:", "Nice!", "Boom!", "Done and dusted:", "Perfect!", "Hooray!",
           "Good to go:", "Sweet!", "Great,", "Cool,", "Phew,", "So,", "Wonderful!", "Yay!",
           "Here is what happened:", "Great job!", "All done!", "Nice one!", "Whew!", "Huzzah!",
           "In short,", "TL;DR:", "To sum up,", "As requested,", "Status update:", "Good catch!", "Brilliant!",
           "Success!", "Well,", "Now,", "First things first:", "Here you go:"],
    "ko": ["살펴보겠습니다.", "해볼게요.", "좋은 소식입니다!", "자,", "알려드립니다:", "참고로", "짜잔!", "확인해 보니",
           "정리하면", "좋습니다!", "네,", "결론적으로", "좋아요!", "다행스럽게도", "음,", "알겠습니다.", "보시다시피",
           "기쁜 소식입니다!", "요약하자면,", "먼저,", "그럼", "결과적으로", "참고하세요:", "잘 됐네요!", "완료했어요!",
           "여기 있습니다:", "확인 결과", "요컨대", "멋지네요!", "드디어 해냈습니다!", "알려드리면,"],
}
# More training openers, built from parts so the model sees many shapes rather than one list. No
# word here appears in CHATTY_TEST, LOOKALIKE_TEST or hf/model/handwritten2.jsonl.
_EN_WORDS = ["Great", "Cool", "Nice", "Sweet", "Awesome", "Perfect", "Wonderful", "Brilliant", "Splendid", "Lovely",
             "Neat", "Superb", "Yay", "Hooray", "Huzzah", "Whew", "Phew", "Boom", "Bam", "Wow", "Yes", "Alright",
             "Well", "So", "Now", "Hmm", "Ah", "Aha", "Done", "Success", "Gotcha", "Yep", "Indeed", "Absolutely"]
_EN_PHRASES = ["Here's the {x}:", "Here is the {x}:", "Quick {x}:", "Just a quick {x}:", "A short {x}:", "Small {x}:",
               "The {x}:", "Some {x}:", "Big {x}:", "Latest {x}:"]
_EN_NOUNS = ["update", "recap", "summary", "status", "rundown", "note", "result", "report", "overview"]
_KO_STEMS = ["좋네요", "멋져요", "훌륭합니다", "해냈어요", "끝났어요", "성공입니다", "공유드립니다",
             "전달드립니다", "확인했습니다", "시작할게요", "알아봤습니다", "결과 나왔습니다", "보시죠",
             "요약해 드릴게요", "됐네요", "좋아요", "깔끔하네요", "역시나"]
_KO_CONNECTIVES = ["핵심만 말하면", "간단히 말해", "결론부터 말하면", "요약하면", "돌아보면", "덧붙이자면", "알고 보니",
                   "살펴보니", "따라서", "그래서", "그러므로", "덕분에", "결국", "한편", "이어서", "마지막으로"]
CHATTY["en"] += [w + p for w in _EN_WORDS for p in ("!", ",", ":", ".")] + [
    t.format(x=n) for t in _EN_PHRASES for n in _EN_NOUNS]
CHATTY["ko"] += [w + p for w in _KO_STEMS for p in ("!", ".", ":")] + [
    c + p for c in _KO_CONNECTIVES for p in ("", ",")]
CHATTY = {lang: list(dict.fromkeys(v)) for lang, v in CHATTY.items()}
CHATTY_TEST = {
    "en": ["Voila!", "Good news:", "Fantastic!", "FYI:", "Here we go:", "Excellent!", "Okay,", "Hurrah!",
           "Heads-up,", "Good stuff:", "Real quick:", "Guess what?"],
    "ko": ["해보겠습니다.", "완벽합니다!", "말씀드리면", "다행히", "알려 드릴게요:", "정리해 보면", "와!", "좋은 결과입니다!",
           "말하자면", "소식 전해 드려요:"],
}
# Lines that start with a word that only looks like an opener. They are hard negatives: nothing
# in them may be removed. As with the openers, the *_TEST list only appears in the test split.
LOOKALIKE = {
    "en": ["Finally block ran in {name}", "Nice level set to {i} for {name}", "Perfect hash rebuilt for {name}",
           "Great Lakes shard {n} is online", "Cool-down of {n}s applied to {name}", "Awesome-lib {ver} installed",
           "Boom gate {n} reported a fault", "Sweet spot search took {ms}ms", "Alright-cli exited with code {code}",
           "Yay-service returned {code}", "Heads-up display disabled for {name}", "Update count is {n} for {name}",
           "Success rate for {name} is {pct}%", "Now playing queue has {n} items", "Brilliant-cut asset {n} uploaded",
           "So-called retries disabled for {name}", "Well-known path {path} not found", "Wonderful.png uploaded to {path}"],
    "ko": ["결론 필드가 비어 있습니다 ({name})", "자동 재시도 {n}회 실패", "참고 문서 {n}개를 색인했습니다",
           "정리 작업 {n}건 완료", "네트워크 지연 {ms}ms", "좋은글 게시판 {n}건 백업", "음성 파일 {n}개 변환",
           "알림 설정 {n}건 갱신", "먼저 온 요청 {n}건 처리", "확인 버튼 클릭 {n}건", "요약 리포트 {n}건 생성",
           "완료율 {pct}%", "기쁨 스티커 {n}개 판매", "그럼블 서비스 응답 코드 {code}", "멋 쇼핑몰 주문 {n}건 동기화",
           "다행정 구역 데이터 {n}건 갱신", "여기어때 연동 토큰 갱신", "자바 힙 사용량 {pct}%"],
}
LOOKALIKE_TEST = {
    "en": ["Excellent tier quota used: {pct}%", "Fantastic4 cluster scaled to {n}", "FYI-bot posted {n} messages",
           "Voila.png uploaded to {path}", "Good news feed refreshed for {name}", "Real-time sync lag {ms}ms"],
    "ko": ["완벽성 검사 {n}건 통과", "와이파이 신호 약함 ({name})", "말하기 평가 {n}건 채점", "해보기 버튼 노출 {n}회",
           "다행복 카드 발급 {n}건", "정리해고 문서 열람 권한 변경"],
}
# Filler adverbs. Korean ones in the rule list are removed at the strong level; the others have no rule.
FILLER = {"ko": ["성공적으로 ", "완벽하게 ", "무사히 ", "깔끔하게 "], "en": ["Successfully ", "Seamlessly "]}
FILLER_TEST = {"ko": ["드디어 ", "순조롭게 "], "en": ["Finally "]}
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


def line(rng: random.Random, lang: str, pool: dict, roll: float, inline: bool = False, plain: bool = False) -> dict:
    """One message: a clean base, then traces injected according to a random plan.

    Two texts are built side by side: `text` gets every trace, `kept` gets all but the
    rewrite-only ones (filler, chatty), so slopdam's reader output of `kept` is the target."""
    templates = pool["templates"]
    tid = rng.randrange(len(templates))
    template = templates[tid][1]
    allowed = [k for k in KINDS if not (inline and k in LINE_SHAPE) and not (plain and k in REWRITE_ONLY)]
    kinds = rng.sample(allowed, k=rng.choice([1, 1, 2, 2, 3, 4])) if roll >= 0.25 else []
    if "heading" in kinds and "bullet" in kinds:
        kinds.remove("bullet")  # "• # text" is not something anyone writes
    # A range like 2024-2025 gets an en or em dash only when that trace is injected.
    base = fill(rng, template, rng.choice(["–", "—", "ㅡ"]) if "range_dash" in kinds else "-")
    tail = rng.choice(TAILS[lang])
    tid = f"{lang}-{templates[tid][0]:03d}"
    if roll < 0.15:  # clean message: nothing to change
        return {"lang": lang, "template_id": tid, "input": base, "kept": base, "injected": []}
    if roll < 0.25:  # hard negative: looks risky, must not change
        text = hard_negative(rng, base) if rng.random() < 0.6 else fill(rng, rng.choice(pool["lookalike"]))
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
        f = rng.choice(pool["filler"])
        if lang == "ko":
            t[0] = f + t[0]
        elif t[0][:1].isupper() and t[0][1:2].islower():
            t[0] = f + t[0][0].lower() + t[0][1:]
        else:
            kinds.remove("filler")
            if not kinds:
                kinds.append("pictograph")
    if "chatty" in kinds:
        opener = rng.choice(pool["chatty"])
        if lang == "en" and opener[-1] in ",:" and t[0][:1].isupper() and t[0][1:2].islower() and rng.random() < 0.5:
            t[0] = t[0][0].lower() + t[0][1:]  # "Great, saved 3 rows": target capitalizes it again
        t[0] = opener + " " + t[0]
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


# --- structured output ---------------------------------------------------------------------------
# A traced message inside a log format: the structure must survive, the message gets cleaned.
CLASSES = ["OrderService", "UserRepository", "PaymentClient", "CacheWarmer", "JobRunner", "Ingestor"]


def _ts(rng: random.Random) -> str:
    return f"2025-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}T{rng.randint(0, 23):02d}:{rng.randint(0, 59):02d}:{rng.randint(0, 59):02d}Z"


def _json_line(rng, msg):
    level = rng.choice(["info", "warn", "error", "debug"])
    fields = {"ts": _ts(rng), "level": level, rng.choice(["msg", "message"]): msg}
    fields[rng.choice(["user_id", "request_id", "shard", "attempt"])] = rng.randint(1, 9999)
    return json.dumps(fields, ensure_ascii=False, separators=(",", ":") if rng.random() < 0.5 else (", ", ": "))


def _logfmt(rng, msg):
    key = rng.choice(["msg", "message", "error", "errmsg"])
    return f'ts={_ts(rng)} level={rng.choice(["info", "warn", "error"])} {key}="{msg}" {rng.choice(KVS)}'


def _prefixed(rng, msg):
    t = _ts(rng).replace("T", " ").rstrip("Z")
    return rng.choice([
        f"{t} INFO  [main] c.e.{rng.choice(CLASSES)} - {msg}",
        f"[{t}] {rng.choice(['INFO', 'WARN', 'ERROR'])}: {msg}",
        f"{t} {rng.choice(['I', 'W', 'E'])} {rng.choice(NAMES)}[{rng.randint(100, 9999)}]: {msg}",
    ])


FORMATS = {"json_line": _json_line, "logfmt": _logfmt, "log_prefix": _prefixed}


def structured(rng: random.Random, lang: str, pool: dict) -> dict:
    """One traced message in a log format. Openers and fillers are left out: they are judged at
    the start of a line, which here is the format, not the message."""
    for _ in range(20):
        part = line(rng, lang, pool, 0.25 + 0.75 * rng.random(), inline=True, plain=True)
        if '"' not in part["input"] and "\\" not in part["input"]:
            break
    kind = rng.choice(sorted(FORMATS))
    state = rng.getstate()
    text = FORMATS[kind](rng, part["input"])
    rng.setstate(state)  # same timestamp, level and fields around both messages
    kept = FORMATS[kind](rng, part["kept"])
    return {"lang": lang, "template_id": part["template_id"], "input": text, "kept": kept,
            "injected": sorted(set(part["injected"]) | {kind})}


# Output that only looks risky: stack traces, tables, diffs and JSON data. slopdam must leave it
# exactly as it is. Half of the shapes only appear in the test split.
def _py_trace(rng):
    f = rng.choice(["main.py", "worker.py", "jobs/run.py"])
    return (f"Traceback (most recent call last):\n  File \"/app/{f}\", line {rng.randint(2, 400)}, in <module>\n"
            f"    {rng.choice(['main()', 'run(job)', 'sync()'])}\n{rng.choice(['ValueError', 'KeyError', 'TimeoutError'])}: "
            f"{rng.choice(['bad value', 'user_id', 'timed out after 30s'])}")


def _java_trace(rng):
    c = rng.choice(CLASSES)
    return (f"java.lang.{rng.choice(['IllegalStateException', 'NullPointerException'])}: {rng.choice(['Queue full', 'id is null'])}\n"
            f"\tat com.example.{c}.run({c}.java:{rng.randint(10, 300)})\n\tat java.base/java.lang.Thread.run(Thread.java:833)")


def _go_panic(rng):
    return (f"panic: {rng.choice(['runtime error: index out of range [3] with length 3', 'nil map write'])}\n"
            f"goroutine 1 [running]:\nmain.main()\n\t/app/main.go:{rng.randint(5, 90)} +0x{rng.randint(16, 255):x}")


def _cells(rng):
    rows = [(n, str(rng.randint(0, 999))) for n in rng.sample(NAMES, 3)]
    w0 = max(len("name"), *(len(r[0]) for r in rows)) + 2
    w1 = max(len("count"), *(len(r[1]) for r in rows)) + 2
    return rows, w0, w1


def _ascii_table(rng):
    rows, w0, w1 = _cells(rng)
    border = f"+{'-' * w0}+{'-' * w1}+"
    body = [f"| {a.ljust(w0 - 1)}| {b.rjust(w1 - 2)} |" for a, b in [("name", "count")] + rows]
    return "\n".join([border, body[0], border, *body[1:], border])


def _box_table(rng):
    rows, w0, w1 = _cells(rng)
    line_ = lambda l, m, r: f"{l}{'─' * w0}{m}{'─' * w1}{r}"  # noqa: E731
    body = [f"│ {a.ljust(w0 - 1)}│ {b.rjust(w1 - 2)} │" for a, b in [("name", "count")] + rows]
    return "\n".join([line_("┌", "┬", "┐"), body[0], line_("├", "┼", "┤"), *body[1:], line_("└", "┴", "┘")])


def _md_table(rng):
    rows, w0, w1 = _cells(rng)
    body = [f"| {a.ljust(w0 - 1)}| {b.ljust(w1 - 1)}|" for a, b in [("name", "count")] + rows]
    return "\n".join([body[0], f"|{'-' * w0}|{'-' * w1}|", *body[1:]])


def _kubectl(rng):
    pods = [(f"{n}-{rng.randint(1000, 9999):x}", rng.choice(["1/1", "0/1", "2/2"]), rng.choice(["Running", "Pending", "CrashLoopBackOff"]),
             str(rng.randint(0, 12))) for n in rng.sample(NAMES, 3)]
    cols = [("NAME", 0), ("READY", 1), ("STATUS", 2), ("RESTARTS", 3)]
    w = [max(len(h), *(len(p[i]) for p in pods)) + 3 for h, i in cols]
    fmt = lambda r: "".join(v.ljust(w[i]) for i, v in enumerate(r)).rstrip()  # noqa: E731
    return "\n".join([fmt([h for h, _ in cols]), *(fmt(p) for p in pods)])


def _diff(rng):
    a = rng.randint(1, 200)
    return (f"@@ -{a},3 +{a},3 @@\n-timeout = {rng.randint(5, 60)}\n+timeout = {rng.randint(61, 120)}\n"
            f" retries = {rng.randint(1, 5)}")


def _json_data(rng):
    return json.dumps({"range": f"{rng.randint(2015, 2024)}-{rng.randint(2025, 2026)}", "route": f"{rng.choice(NAMES)}->{rng.choice(NAMES)}",
                       "flag": rng.choice(["--force", "--dry-run", "-v"]), "since": f"{rng.randint(2015, 2025)}-01-01"})


SHAPES = {"train": [_py_trace, _ascii_table, _md_table, _diff, _json_data],
          "test": [_java_trace, _go_panic, _box_table, _kubectl]}


def shape(rng: random.Random, lang: str, split: str) -> dict:
    f = rng.choice(SHAPES["test" if split == "test" else "train"])
    text = f(rng)
    assert READER.clean(text) == text, (f.__name__, text)
    return {"lang": lang, "template_id": f"shape-{f.__name__.strip('_')}", "input": text, "kept": text, "injected": []}


def make(rng: random.Random, lang: str, pool: dict, split: str = "train") -> dict:
    """A single line (78%), a multi-line summary block the way assistants write them (8%: an
    optional title, then two to four items with inline traces only), a traced message inside a
    log format (10%), or structured output that must not change (4%)."""
    roll = rng.random()
    if roll < 0.04:
        return shape(rng, lang, split)
    if roll < 0.14:
        return structured(rng, lang, pool)
    if roll >= 0.22:
        return line(rng, lang, pool, rng.random())
    parts = [line(rng, lang, pool, 0.25 + 0.75 * rng.random(), inline=True) for _ in range(rng.randint(2, 4))]
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
    pools = {split: {lang: {
        "templates": [(i, t) for i, t in enumerate(TEMPLATES[lang]) if (i % HELD_OUT == HELD_OUT - 1) == (split == "test")],
        "chatty": (CHATTY_TEST if split == "test" else CHATTY)[lang],
        "filler": (FILLER_TEST if split == "test" else FILLER)[lang],
        "lookalike": (LOOKALIKE_TEST if split == "test" else LOOKALIKE)[lang],
    } for lang in TEMPLATES} for split in SPLITS}
    seen, splits = set(), {"train": [], "validation": [], "test": []}
    for split, count in (("test", test_rows), ("validation", validation_rows), ("train", rows)):
        while len(splits[split]) < count:
            lang = "ko" if rng.random() < 0.5 else "en"
            row = make(rng, lang, pools[split][lang], split)
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
