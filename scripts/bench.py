# SPDX-License-Identifier: MIT
"""Measure clean() on typical log lines and print a Markdown table.

    python scripts/bench.py                    # print to stdout
    python scripts/bench.py >> "$GITHUB_STEP_SUMMARY"   # in CI

Numbers are for comparing changes on the same machine, not absolute targets.
"""
from __future__ import annotations

import sys
import timeit
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from slopdam import Sanitizer, __version__  # noqa: E402

CORPUS = {
    "ASCII, nothing to clean": [
        "GET /api/v1/users/42 200 12ms",
        "worker-3 processed batch id=9f2c size=500",
        "retrying connection to db-01:5432 (attempt 2 of 5)",
    ],
    "Korean, nothing to clean": [
        "사용자 42명의 데이터를 동기화했습니다",
        "설정 파일 /etc/app/config.yaml 을 읽었습니다",
        "요청 처리 시간 12ms, 상태 200",
    ],
    "With traces": [
        "✅ **저장 완료** ㅡ 2024–2025년 데이터 3건 처리했습니다! 🎉",
        "🚀 Server started — listening on https://localhost:8080",
        "──── 단계 2 ────  “설정” 확인 중…",
    ],
}
REPEAT = 5


def main() -> int:
    rows = []
    for name, lines in CORPUS.items():
        for profile in ("reader", "dev"):
            s = Sanitizer(profile)
            n = 2000
            best = min(timeit.repeat(lambda: [s.clean(x) for x in lines], number=n, repeat=REPEAT))
            per_line = best / (n * len(lines)) * 1e6
            rows.append((name, profile, per_line, 1e6 / per_line))
    print(f"### slopdam {__version__} benchmark (Python {sys.version.split()[0]})\n")  # slopdam: ignore[md] (Markdown for the job summary)
    print("| Input | Profile | µs per line | Lines per second |")
    print("|---|---|---:|---:|")
    for name, profile, us, rate in rows:
        print(f"| {name} | {profile} | {us:.1f} | {rate:,.0f} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
