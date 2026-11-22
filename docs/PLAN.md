# slopdam 기획안 (v0.2)

> 이름: **slopdam** (슬롭댐, 결정 근거 [NAMING.md](NAMING.md)). 상세 설계는 [DESIGN.md](DESIGN.md), 근거 자료는 [RESEARCH.md](RESEARCH.md), 규칙 목록은 [RULES.md](RULES.md).

## 1. 문제 정의

AI 코딩 도구로 소스코드를 만들면 로그와 출력 문자열에 생성 모델의 흔적이 그대로 남습니다.

| 유형 | 예시 | 문제 |
|---|---|---|
| 대시류 | `완료 — 다음`, `완료 ㅡ 다음`, `ㅡㅡㅡ`, `───` | 한국어 문장과 어울리지 않고, 검색과 파싱을 방해 |
| 장식 이모지 | `✅ 저장 완료`, `🚀 서버 시작` | 로그 레벨과 중복되고, 터미널과 수집기에서 깨짐 |
| 구분선 | `==========`, `ㅡㅡㅡㅡㅡ` | 수집기에 의미 없는 줄이 쌓임 |
| 마크다운 | `**중요**`, `### 단계 1` | 로그는 마크다운을 렌더링하지 않음 |
| 특수 문장부호 | `“ ”`, `…`, `→`, `•` | 키보드로 다시 입력할 수 없고 검색이 안 됨 |
| 과한 어조 | `성공적으로 완료되었습니다! 🎉` | 운영 메시지의 톤과 맞지 않음 |
| 보이지 않는 문자, 전각 | ZWSP, NBSP, `，` `（` | 비교와 파싱 실패의 원인 |

## 2. 목적: 독자에 따라 두 가지로 분류

| | **1. `reader` (기본)** | 2. `dev` |
|---|---|---|
| 목표 | **일반 사용자가 편하게 읽는** 담백한 한국어 | **개발자가 보기 편한**, 정보 손실 없는 형태 |
| 대상 출력 | CLI 메시지, 알림, 리포트, 화면 오류 문구 | 로그 파일, 수집기, DEBUG 로그, 커밋/주석 린트 |
| `완료 ㅡ 다음` | `완료: 다음` | `완료 - 다음` |
| `2024–2025` | `2024~2025` | `2024-2025` |
| `✅ 저장` | `저장` | `[OK] 저장` |
| `완료!` | `완료.` | `완료!` |

탐지 엔진은 하나이고, 프로필은 "무엇으로 바꾸는가"만 다릅니다. 로거 하나에 핸들러 두 개(화면은 reader, 파일은 dev)를 붙이는 방식이 기본 사용법입니다.

## 3. 접근 방식: 두 개의 축

```
                 ┌──────── 규칙 엔진 (core) ────────┐
                 │ 탐지: 규칙 ID + 패턴 + 문맥 판정   │
                 │ 액션: reader / dev 별 치환         │
                 │ 레벨: basic / strong / strict      │
                 └───────┬───────────────┬──────────┘
                         │               │
     (A) 런타임: Formatter/Filter    (B) 정적: Linter/CLI
     - Python logging (완료)          - slopdam check (완료)
     - structlog, loguru (v0.2)       - slopdam fix (v0.2)
     - pino, winston (v0.3)           - pre-commit, CI, SARIF
```

## 4. 로드맵

### v0.1 (완료)
- 규칙 엔진, Python `logging` 포맷터/필터, `slopdam check` / `clean`, pre-commit 훅

### v0.2 (프로토타입 반영 완료 표시 ✔)
- ✔ reader / dev 프로필, basic / strong / strict 레벨
- ✔ 대시 계열 25종 문맥 판정 (`ㅡ` 3종 코드포인트 포함)
- ✔ 보호 구역 (URL, 인라인 코드, key=value, 경로)
- ✔ dev 상태 이모지 태그, 로그 레벨 중복 생략
- ✔ 규칙 ID 체계, 접두어 단위 비활성화, `# slopdam: ignore[...]`, JSON 출력
- ✔ 멱등성 테스트
- ✔ `slopdam fix` (AST 기반, 문자열 리터럴만 수정, 서식 자리와 f-string 표현식 보존)
- ✔ 설정 파일 `slopdam.toml` / `[tool.slopdam]`, `check --scope strings`
- [ ] 이모지 범위표 생성 스크립트 (`emoji-data.txt`), `regex` 모듈 선택 사용
- [ ] structlog / loguru 어댑터
- [ ] 골든 코퍼스, 오탐 코퍼스, hypothesis 속성 테스트, 벤치마크

### v0.3
- [ ] `profile="auto"` (핸들러 종류, 로그 레벨, 환경 변수로 자동 분류)
- [ ] 언어 공통 규칙 YAML (`rules/*.yaml`) + 코드 생성
- [ ] JS/TS 패키지 (pino/winston 포맷터, ESLint 플러그인), tree-sitter 기반 린트
- [ ] SARIF, GitHub annotation 출력

### v0.4
- [ ] Java (Logback Converter, Log4j2 RewritePolicy), Go (`slog.Handler`)

### 범위 밖
- AI가 썼는지 판별하는 기능 (근거: RESEARCH.md 1장, 신뢰도 낮음)
- LLM을 이용한 문장 재작성. 결정적 규칙만 다룹니다.

## 5. 설계 원칙

1. **결정적**: 같은 입력과 설정이면 항상 같은 출력
2. **멱등**: `clean(clean(x)) == clean(x)`
3. **보수적**: 한자, 가나, 날짜, CLI 옵션, URL, 경로, 코드는 건드리지 않음
4. **트레이스백 불변**: 예외 스택은 원본 그대로
5. **설명 가능**: 모든 변경에 규칙 ID, 린터는 수정안까지 표시

## 6. 오픈소스 운영

- 라이선스: **MIT** 확정. 근거와 의존성/데이터 정책은 [LICENSING.md](LICENSING.md), 외부 구성 요소는 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)
- 기여: DCO 서명 ([CONTRIBUTING.md](../CONTRIBUTING.md)), 행동 강령 Contributor Covenant 2.1, 보안 신고 [SECURITY.md](../SECURITY.md), 운영과 버전 정책 [GOVERNANCE.md](../GOVERNANCE.md)
- 저장소: 모노레포 `packages/python`, `packages/js`, `rules/`
- 기여 규칙: 새 규칙은 탐지 예, 오탐 방지 예, reader/dev 기대 결과를 테스트로 함께 제출
- 배포: PyPI `slopdam`, npm `@slopdam/*`

## 7. 남은 질문

1. 2015 개정 문장 부호 규정 원문 확인 후 범위 표기 기본값(`~`) 유지 여부
