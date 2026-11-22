# 프로젝트 이름 리서치 (2026-11-21)

> **결정: `slopdam`** (2026-11-21). 저장소 전체를 가칭 `plainlog` 에서 변경 완료.

## 1. 판단 기준

오픈소스 이름 가이드에서 공통으로 강조하는 것과 이 프로젝트의 사정을 합쳤습니다.

1. **모든 곳에서 같은 이름**: 명령어, 패키지, import, 저장소, 문서에 그대로 쓰이므로 PyPI, npm, GitHub 조직명이 모두 비어 있어야 합니다. [opensource.com](https://opensource.com/article/18/2/choosing-project-names-four-key-considerations), [FOSSHub](https://www.fosshub.com/resources/maintainers/project-naming/)
2. **검색 가능성**: 흔한 단어는 검색에서 묻힙니다. 고유한 이름일수록 유리합니다. [18F 가이드](https://github.com/18F/open-source-guide/blob/ca1fd0f66bee0553e4c2aaf92d08d8eb24ed4a1d/pages/naming-your-project.md)
3. **기존 사용 확인**: 다른 활발한 커뮤니티가 쓰는 이름은 피합니다. 상표 확인도 필요합니다. [Apache Incubator](https://incubator.apache.org/guides/names.html)
4. **짧고 하이픈 없는 소문자**: `pip install x`, `import x`, `npx x` 에서 그대로 쓸 수 있어야 합니다.
5. **화제성 (이 프로젝트 고유 기준)**: 한 줄 설명 없이 이름만 봐도 "아, 그거" 하고 공유하고 싶어야 합니다.

## 2. 화제성 근거: 'slop'

- Merriam-Webster는 2025년 올해의 단어로 **"slop"** 을 선정했습니다. 뜻풀이는 "주로 AI가 대량으로 만든 저품질 디지털 콘텐츠"입니다. [PBS](https://www.pbs.org/newshour/nation/merriam-websters-word-of-the-year-for-2025-is-ais-slop), [TechCrunch](https://techcrunch.com/2025/12/15/merriam-webster-names-slop-the-word-of-the-year/)
- 호주 Macquarie 사전은 **"AI slop"** 을 골랐고, Collins는 **"vibe coding"** 을 골랐습니다. [PopSci](https://www.popsci.com/technology/slop-vibe-coding-and-glazing-ai-dominates-2025s-words-of-the-year/)
- 즉 "AI로 코드를 만들고(vibe coding), 그 결과물의 흔적(slop)을 치운다"는 이야기가 이미 대중적인 언어로 자리 잡았습니다. 이름에 `slop`을 넣으면 설명이 거의 필요 없습니다.

**단, 이미 붐비는 영역입니다.** `deslop`(코드베이스 대상 도구, JS 브랜치 검사 도구, PyPI 문서 재작성 도구 등 여러 개), `unslop`, `no-ai-slop` 등이 있습니다. [agent-sh/deslop](https://github.com/agent-sh/deslop), [dabit3/deslop](https://github.com/dabit3/deslop), [PyPI unslop](https://pypi.org/project/unslop/), [no-ai-slop](https://ossinsight.io/analyze/petergyang/no-ai-slop). 따라서 `slop` 단독 변형(de-, un-, no-)은 피하고 **이 프로젝트만의 차별점(로그, 한국어, 막는다)을 붙인 조합**이 필요합니다.

## 3. 후보 이름 사용 여부 (직접 조회)

PyPI(`pypi.org/pypi/<name>/json`), npm(`registry.npmjs.org/<name>`), GitHub 사용자/조직명(`api.github.com/users/<name>`), GitHub 저장소 이름 검색 결과입니다. 2026-11-21 기준이며 언제든 바뀔 수 있습니다.

| 후보 | PyPI | npm | GitHub 조직 | 같은 이름 저장소 | 비고 |
|---|---|---|---|---|---|
| **slopdam** | 비어 있음 | 비어 있음 | 비어 있음 | 0개 | 모두 비어 있음 |
| **eulog** | 비어 있음 | 비어 있음 | 사용 중 | (eulogy 계열 검색 잡음) | 조직명은 다른 이름 필요 |
| **dambaek** | 비어 있음 | 비어 있음 | 비어 있음 | 4개 (별 1개 이하) | |
| logwash | 비어 있음 | 비어 있음 | 비어 있음 | 6개 (별 0개) | |
| logdam | 비어 있음 | 비어 있음 | 사용 중 | 0개 | |
| dashkill | 비어 있음 | 비어 있음 | 사용 중 | 7개 | |
| plainlog (현재 가칭) | **사용 중** | **사용 중** | - | - | 바꿔야 함 |
| deslop, unslop, slopmop, slopstop, sloplint, hushlog | 사용 중 | 사용 중 | - | - | 탈락 |
| noslop, slopfree, nodash, plainify | 비어 있음 | 사용 중 | - | - | 탈락 (npm 필요) |
| ssak | 사용 중 | 비어 있음 | - | - | 탈락 |

> 현재 가칭 `plainlog` 는 PyPI와 npm에 이미 있으므로 **어떤 경우든 이름을 바꿔야 합니다.**

## 4. 추천

### 1순위: `slopdam` (슬롭댐)

> **"AI slop이 로그로 흘러넘치기 전에 막는 댐"**

- **화제성**: 2025년 올해의 단어 `slop`을 그대로 씁니다. 영어권에서 설명이 필요 없습니다.
- **차별점이 이름에 들어 있음**: 기존 도구는 "지운다(de-, un-)"인데, 이 프로젝트는 **출력 단계(포맷터)와 커밋 단계(린터)에서 막는** 구조입니다. 댐(dam)이 이 구조를 정확히 표현합니다.
- **한국어 이중 의미**: `dam` = **담**백. reader 프로필이 만드는 "담백한 문장"과 이어집니다. 한국 커뮤니티 소개 문구로 쓰기 좋습니다. ("슬롭은 막고, 문장은 담백하게")
- **가용성**: PyPI, npm, GitHub 조직, 저장소 이름이 모두 비어 있습니다. 유일하게 전 항목이 깨끗한 후보입니다.
- **사용 예**: `pip install slopdam`, `slopdam check src/`, `from slopdam import PlainFormatter`
- 약점: `slop`이 유행어라 몇 년 뒤 낡은 느낌이 날 수 있습니다. 다만 사전에 등재된 단어라 금방 사라지지는 않을 것으로 봅니다.

### 2순위: `eulog` (ㅡlog)

> **"A eulogy for your em dashes."** (당신의 em dash에 바치는 추도사)

- `ㅡ`의 이름이 '으(eu)'이고, 두벌식 `m` 키입니다. `eu` + `log` = **eulog** 이고, 영어로 읽으면 **eulogy(추도사)** 처럼 들립니다. "대시를 장례 치러주는 로거"라는 농담이 바로 통합니다.
- 한국 개발자에게는 "ㅡ 지우는 로거"라는 정체성이 가장 선명합니다.
- 약점: GitHub 조직명 `eulog`가 이미 사용 중입니다 (`eulog-dev` 등으로 대체). 'ㅡ' 맥락을 모르는 사람에게는 설명이 한 번 필요합니다.

### 3순위: `dambaek` (담백)

- 한국어 정체성이 가장 강하고, reader 프로필의 목표("담백한 문장")와 정확히 일치합니다.
- 약점: 영어권에서 발음과 의미 전달이 어렵습니다. 국내 중심이라면 1순위로 올려도 됩니다.

### 정리

| | 글로벌 화제성 | 한국 정체성 | 기능 설명력 | 가용성 |
|---|---|---|---|---|
| **slopdam** | 높음 | 중간 (담) | 높음 (막는다) | 전부 비어 있음 |
| eulog | 중간 (말장난) | 높음 (ㅡ) | 중간 | GitHub 조직만 사용 중 |
| dambaek | 낮음 | 매우 높음 | 중간 | 전부 비어 있음 |

**결론: `slopdam`을 추천합니다.** 2순위 `eulog`의 말장난은 버릴 필요 없이, README 첫 문단이나 발표 제목("A eulogy for your em dashes")으로 쓰면 됩니다. 서브 브랜드는 따로 만들지 않습니다 (이름이 여러 개면 힘이 분산된다는 지적이 있습니다. [opensource.com](https://opensource.com/business/16/3/kill-off-extra-brand-names)).

## 5. 확정 전 할 일

- [x] 상표 검색: USPTO, KIPRIS 모두 동일 상표 0건. 유사 상표 3건(미국, 출원 중)은 주의 대상. 상세 보고서는 비공개로 관리
- [ ] 이름 선점: PyPI와 npm에 빈 0.0.1 패키지를 올리고, GitHub 조직을 만들기 (사용자가 직접 진행)
- [x] 도메인: `.com` `.io` `.ai` 미등록 확인, `.dev` 등은 등록기관에서 최종 확인
- [x] 저장소 전체의 `plainlog` 를 `slopdam` 으로 일괄 변경 (패키지 디렉터리, import, CLI, 무시 주석, 문서)
