# Changelog

형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 를 따르고, 버전 정책은 [GOVERNANCE.md](GOVERNANCE.md) 4장을 따릅니다.

## [Unreleased] (0.2.0.dev0)

### 변경
- 프로젝트 이름을 가칭 `plainlog` 에서 **`slopdam`** 으로 변경: 패키지 `slopdam`, import `from slopdam import ...`, CLI `slopdam`, 무시 주석 `# slopdam: ignore`, pre-commit 훅 id `slopdam` ([docs/NAMING.md](docs/NAMING.md))

### 추가
- `slopdam fix`: Python 파일의 로그/print 문자열 인자(또는 `--scope strings` 로 모든 문자열)를 문법 트리 기준으로 고침. 따옴표, 접두어, 이스케이프, f-string 표현식, 서식 자리 보존. 컴파일 검사 후에만 저장. `--diff` 로 미리 보기
- 설정 파일: `slopdam.toml` 또는 `pyproject.toml` 의 `[tool.slopdam]` (profile, level, disable, dash.inline, lint.scope/include/exclude). `--config`, `SLOPDAM_CONFIG`. Python 3.11+ 는 `tomllib`, 그 이전은 내장 부분 파서
- `check --scope strings`: Python 파일을 줄이 아니라 문자열 리터럴 단위로 검사
- 종료 코드 2: 옵션이나 설정 오류
- `reader`(기본) / `dev` 프로필, `basic` / `strong` / `strict` 레벨
- 대시 계열 25종 문맥 판정 (`ㅡ` U+3161, U+FFDA, U+1173 포함)
- 보호 구역: URL, 인라인 코드, `key=value` 의 값, 경로
- `dev` 상태 이모지 태그 (`[OK]` `[FAIL]` `[WARN]`), 로그 레벨과 겹치면 생략
- 규칙 ID 체계, 접두어 단위 비활성화, `# slopdam: ignore[...]`, `check --format json`, `--dash-inline`
- LICENSE(MIT), THIRD_PARTY_NOTICES, CONTRIBUTING(DCO), CODE_OF_CONDUCT, SECURITY, GOVERNANCE

### 출력 변경
- `md.emphasis` 가 `__x__` 를 더 이상 굵은 글씨로 보지 않음: `logging.getLogger(__name__)` 의 `__name__` 을 지우라고 하던 오탐 수정. `**x**` 만 처리
- Python 파일의 `check` (기본 `log-calls`) 가 줄이 아니라 문법 트리로 로그 호출의 문자열 인자를 검사: `fix` 와 결과가 같아지고, 서식 자리(`%s`) 옆 대시와 문자열 맨 앞 상태 이모지를 바르게 판정. 다른 언어는 계속 줄 단위
- 이모지를 지울 때 바로 뒤 공백도 함께 지움: 여러 줄 글에서 둘째 줄부터 맨 앞 이모지를 지우면 공백 하나가 남던 문제 수정 (`a\n⚠️ b` 가 `a\n b` 에서 `a\nb` 로). 들여쓰기와 키캡(`1️⃣`) 뒤 공백은 유지
- 린터(`check`)의 수정안이 실제 정리 결과와 같아짐: 규칙을 `clean()`과 같은 순서로 적용해 판정 (예: `**저장 완료** ㅡ 다음` 에서 `ㅡ` 의 수정안이 삭제에서 `: ` 로). 보호 구역(URL, 인라인 코드, `key=value` 의 값, 경로) 안의 문자는 더 이상 보고하지 않음
- 문장 안 대시: `완료 — 다음` 의 결과가 `완료 - 다음` 에서 `완료: 다음` 으로 바뀜 (reader). 이전 동작은 `--profile dev` 또는 `--dash-inline hyphen`
- `ㅡㅡ` 가 삭제됨 (이전에는 유지)
- 한글 뒤 `!` 가 기본으로 `.` 로 바뀜 (이전에는 `ko` 프리셋에서만)
- 프리셋 `default` / `ko` / `strict` 가 프로필과 레벨로 대체됨

## [0.1.0]

### 추가
- 규칙 엔진, Python `logging` 포맷터와 필터, `check` / `clean` CLI, pre-commit 훅
