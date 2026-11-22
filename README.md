# slopdam

AI로 생성한 코드의 로그와 출력에 남는 흔적을 걷어내는 **로거 포맷터 + 린터**입니다. 대상은 `ㅡ` `—` `───` 대시류, `✅🚀` 이모지, `=====` 구분선, `**굵게**` 마크다운, `“둥근 따옴표”` 등입니다.

누가 읽는지에 따라 두 가지로 정리합니다.

```
입력  : ✅ **저장 완료** ㅡ 2024–2025년 데이터 3건 처리했습니다! 🎉

reader: 저장 완료: 2024~2025년 데이터 3건 처리했습니다.          ← 일반 사용자용 (기본)
dev   : [OK] 저장 완료 - 2024-2025년 데이터 3건 처리했습니다!    ← 개발자용
```

> 초안 v0.2. 기획 [docs/PLAN.md](docs/PLAN.md) · 상세 설계 [docs/DESIGN.md](docs/DESIGN.md) · 리서치 [docs/RESEARCH.md](docs/RESEARCH.md) · 규칙 [docs/RULES.md](docs/RULES.md)

## 프로필

| 프로필 | 누구를 위한 출력인가 | 쓰는 곳 |
|---|---|---|
| `reader` (기본) | 일반 사용자가 편하게 읽는 담백한 한국어 | CLI 메시지, 알림, 리포트, 화면 오류 문구 |
| `dev` | 개발자가 보고 검색하기 편한, 정보 손실 없는 형태 | 로그 파일, 로그 수집기, DEBUG 로그 |

레벨은 `basic`(기본), `strong`(상투 표현 `성공적으로` 등도 삭제), `strict`(비ASCII 기호를 린터에서 경고) 세 가지입니다.

## 1. 런타임 포맷터

```python
import logging
from slopdam import PlainFormatter, PlainFilter

console = logging.StreamHandler()                            # 사람이 보는 화면
console.setFormatter(PlainFormatter("%(message)s"))          # reader (기본)
console.addFilter(PlainFilter())                             # 구분선만 찍는 로그는 버림

file = logging.FileHandler("app.log")                        # 개발자, 수집기
file.setFormatter(PlainFormatter("%(asctime)s %(levelname)s %(message)s", profile="dev"))

logging.basicConfig(level=logging.INFO, handlers=[console, file])
logging.info("✅ 처리 %s건 ㅡ 완료!", 3)
# 화면  : 처리 3건: 완료.
# 파일  : 2026-11-21 ... INFO [OK] 처리 3건 - 완료!
```

- 원본 로그 레코드는 바뀌지 않으므로 핸들러마다 다른 프로필을 쓸 수 있습니다.
- 예외 트레이스백, URL, 백틱 안 코드, `key=value` 의 값, 파일 경로는 건드리지 않습니다.

## 2. 정적 린터

```bash
slopdam check src/                         # 로그/print 호출 라인 검사, 걸리면 exit 1
slopdam --profile dev check src/
slopdam check --all --format json src/
slopdam --disable emoji check src/         # 규칙 그룹 단위로 끄기
```

```
src/app.py:12:17: dash.run 'ㅡ' -> ': '
src/app.py:15:14: emoji.pictograph '✅' -> ''
```

줄 끝에 `# slopdam: ignore` 를 붙이면 그 줄을 건너뜁니다. `# slopdam: ignore[emoji]` 처럼 규칙을 지정할 수도 있습니다.

### 자동 수정 (Python)

문법 트리로 로그/print 호출의 문자열 인자만 찾아 고칩니다. 따옴표, `f`/`r` 접두어, 이스케이프, f-string의 `{...}`, `%s` 같은 서식 자리는 그대로 두고, 결과가 컴파일되지 않으면 쓰지 않습니다.

```bash
slopdam fix --diff src/          # 미리 보기 (바뀔 내용이 있으면 exit 1)
slopdam fix src/                 # 고치기
slopdam fix --scope strings src/ # 독스트링을 뺀 모든 문자열
```

```diff
-logger.info("✅ 저장 완료 ㅡ %s건 처리!", n)
+logger.info("저장 완료: %s건 처리.", n)
```

### 설정 파일

저장소의 `slopdam.toml` 또는 `pyproject.toml` 의 `[tool.slopdam]` 을 읽습니다. 명령줄 옵션이 우선하고, 설정 오류는 exit 2입니다.

```toml
profile = "dev"
level = "basic"
disable = ["emoji.status"]

[dash]
inline = "colon"

[lint]
scope = "log-calls"   # log-calls | strings | all
exclude = ["tests/**"]
```

pre-commit:

```yaml
repos:
  - repo: https://github.com/slopdam/slopdam
    rev: v0.2.0
    hooks:
      - id: slopdam
```

## 3. 파이프

```bash
tail -f app.log | slopdam clean
```

## 라이선스와 기여

[MIT](LICENSE). 기여 방법은 [CONTRIBUTING.md](CONTRIBUTING.md) (DCO 서명), 보안 신고는 [SECURITY.md](SECURITY.md), 운영 방식은 [GOVERNANCE.md](GOVERNANCE.md).

## 개발

```bash
pip install -e .
python -m pytest
```
