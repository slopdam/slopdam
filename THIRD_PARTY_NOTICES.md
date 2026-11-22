# Third-Party Notices

이 프로젝트가 포함하거나 선택적으로 사용하는 외부 구성 요소와 그 라이선스입니다.
정책은 [docs/LICENSING.md](docs/LICENSING.md) 를 따릅니다.

## 현재 상태 (v0.2.0.dev0)

**런타임 필수 의존성: 없음.** Python 표준 라이브러리만 사용합니다.
저장소에 포함(vendoring)된 외부 데이터나 코드: **없음.**

## 선택 의존성 (설치되어 있으면 사용, 배포물에는 포함하지 않음)

| 구성 요소 | 용도 | 라이선스 (SPDX) | 확인 |
|---|---|---|---|
| [regex](https://pypi.org/project/regex/) | `\p{Extended_Pictographic}` 이모지 탐지 | `Apache-2.0 AND CNRI-Python` | PyPI 메타데이터, 2026-11-21 |

## 개발 의존성 (배포물에 포함하지 않음)

| 구성 요소 | 용도 | 라이선스 (SPDX) |
|---|---|---|
| [pytest](https://pypi.org/project/pytest/) | 테스트 | `MIT` |
| [hatchling](https://pypi.org/project/hatchling/) | 빌드 | `MIT` |

## 포함 예정 데이터 (v0.2 ~ v0.3)

포함하는 시점에 이 파일에 **원문 라이선스 전문**을 붙이고, 데이터 파일 머리말에 출처와 버전을 남깁니다.

| 데이터 | 용도 | 라이선스 (SPDX) | 출처 |
|---|---|---|---|
| Unicode `emoji-data.txt` | 이모지 범위표 생성 | `Unicode-3.0` | https://www.unicode.org/Public/UCD/latest/ucd/emoji/ |
| Unicode `confusables.txt` (UTS #39) | 대시 계열 닮은꼴 문자표 참고 | `Unicode-3.0` | https://www.unicode.org/Public/security/latest/ |
| Unicode 라이선스 원문 | | | https://www.unicode.org/license.txt |
