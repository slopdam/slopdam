# 리서치 노트 (2026-11-21)

설계 결정의 근거를 모았습니다. "확인됨"은 직접 실행하거나 1차 자료로 확인한 내용, "참고"는 2차 자료나 검색 요약이라 원문을 다시 봐야 하는 내용입니다.

## 1. AI 생성 텍스트의 대시 남용

- GPT-4.1이 일반 에세이에서 사람보다 em dash를 약 3.28배 자주 쓴다는 개인 연구가 인용되고 있습니다. **(참고)** [McGill OSS](https://www.mcgill.ca/oss/article/critical-thinking-student-contributors-technology/why-did-llms-steal-our-em-dashes)
- 모델마다 차이가 크고, 사람도 em dash를 쓰기 때문에 **AI 판별 신호로는 약하다**는 지적이 있습니다. [Plagiarism Today](https://www.plagiarismtoday.com/2025/06/26/em-dashes-hyphens-and-spotting-ai-writing/), [Rolling Stone](https://www.rollingstone.com/culture/culture-features/chatgpt-hypen-em-dash-ai-writing-1235314945/)
- 프롬프트로 "쓰지 마"라고 지시해도 완전히 사라지지 않는다는 사용자 보고가 많습니다. [TechRadar](https://www.techradar.com/computing/artificial-intelligence/did-chatgpt-ruin-the-em-dash-heres-how-to-stop-it-putting-them-everywhere), [OpenAI Community](https://community.openai.com/t/chatgpts-em-dash-habit-a-training-artifact-or-design-choice/1115873)

**설계 반영**: slopdam은 "AI가 썼는지 판별"하지 않습니다. 출처와 상관없이 출력 문자열을 정리하는 결정적 도구로 둡니다. 생성 단계에서 프롬프트로 막는 방식은 불완전하므로 **출력 단계(포맷터)와 커밋 단계(린터) 양쪽**에서 막습니다.

## 2. 한국어 문장 부호와 `ㅡ`

- 현행 규정(2015 개정, 2017 어문 규정집 반영)에서 짧은 줄표(-)의 이름은 **붙임표**로 바뀌었습니다. [국립국어원 연구 자료](https://korean.go.kr/niklintro2/20years05_01_01.jsp) **(참고)**
- 부연이나 정정에 쓰는 줄표는 그 말 앞뒤에 다 쓴다는 해설이 있습니다 (2001년, 개정 전 자료). [국립국어원 새국어소식 2001.06](https://www.korean.go.kr/nkview/nknews/200106/35_4.html) **(참고)**
- 기간이나 범위에 물결표(~)를 쓰는 것은 일반적인 관례로 알려져 있지만, 2015 개정 원문의 정확한 문구(붙임표 허용 여부 포함)는 **원문 재확인이 필요**합니다. 규범 원문: [국립국어원 한국어 어문 규범](https://korean.go.kr/kornorms/main/main.do)
- 두벌식 자판에는 줄표(—) 키가 없고, `m` 키가 `ㅡ`입니다. 그래서 사람이 줄표 대신 `ㅡ`를 쳐서 쓰는 관행이 생겼고, AI가 이 관행이 담긴 한국어 텍스트로 학습하면 `ㅡ`도 출력에 나타납니다. 결국 한국어 환경에서는 `—`와 `ㅡ`를 **같은 계열로 묶어 처리**해야 합니다.

**설계 반영**: reader 프로필은 문장 안 줄표를 콜론(`: `)으로, 숫자 범위를 `~`로 바꿉니다. 둘 다 설정으로 바꿀 수 있게 둡니다 (규범 해석이 갈릴 수 있으므로).

## 3. Unicode 사실 확인 (직접 실행, Python 3.9 `unicodedata`)

| 문자 | 코드포인트 | 이름 | 범주 | NFKC 결과 |
|---|---|---|---|---|
| ㅡ | U+3161 | HANGUL LETTER EU | Lo | **U+1173** (사라지지 않음) |
| ￚ | U+FFDA | HALFWIDTH HANGUL LETTER EU | Lo | U+1173 |
| ᅳ | U+1173 | HANGUL JUNGSEONG EU | Lo | U+1173 |
| — | U+2014 | EM DASH | Pd | 그대로 |
| ﹘ | U+FE58 | SMALL EM DASH | Pd | U+2014 |
| ︱ | U+FE31 | VERTICAL EM DASH | Pd | U+2014 |
| － | U+FF0D | FULLWIDTH HYPHEN-MINUS | Pd | U+002D |
| ‑ | U+2011 | NON-BREAKING HYPHEN | Pd | U+2010 |
| ─ | U+2500 | BOX DRAWINGS LIGHT HORIZONTAL | **So** | 그대로 |
| − | U+2212 | MINUS SIGN | **Sm** | 그대로 |
| ➖ | U+2796 | HEAVY MINUS SIGN | So | 그대로 |
| 一 | U+4E00 | CJK UNIFIED IDEOGRAPH-4E00 | **Lo** | 그대로 |
| ー | U+30FC | KATAKANA-HIRAGANA PROLONGED SOUND MARK | Lm | 그대로 |
| 〜 | U+301C | WAVE DASH | Pd | 그대로 |
| ～ | U+FF5E | FULLWIDTH TILDE | Sm | U+007E |

**결론 3가지 (확인됨)**

1. **NFKC 정규화로는 `ㅡ`를 없앨 수 없습니다.** 조합형 중성으로 바뀔 뿐입니다. 그래서 E군(3161, FFDA, 1173)을 명시적으로 다뤄야 합니다.
2. **Unicode 범주 `Pd`(대시 문장부호)만으로는 부족합니다.** `ㅡ`는 Lo(글자), `─`는 So(기호), `−`는 Sm(수학 기호)입니다. 범주 대신 **눈에 비슷해 보이는 문자표**로 계열을 정의해야 합니다.
3. **`一` `ー`는 실제 한자/가나 글자입니다** (Lo/Lm). 단독으로는 지우면 안 되고 3개 이상 연속(구분선)일 때만 처리합니다.

## 4. 이모지 탐지

- 표준 `re` 모듈은 Unicode 속성 이스케이프를 지원하지 않고, 서드파티 `regex` 모듈은 `\p{Extended_Pictographic}`을 지원합니다. [alexwlchan](https://alexwlchan.net/til/2024/regex-library-for-unicode-property-escapes)
- `Extended_Pictographic`은 `Emoji_Presentation`보다 넓고, 앞으로 이모지가 추가될 블록까지 예약되어 있어 미래 대응에 유리합니다. 피부색 수식자, ZWJ, VS16은 따로 처리해야 합니다. [emojifyi](https://emojifyi.com/stories/unicode-emoji-properties/) **(참고)**
- 기준 데이터는 Unicode `emoji-data.txt` 입니다.
- 이 환경(Python 3.9.6)에는 `regex` 모듈이 기본 설치되어 있지 않았습니다 **(확인됨)**.

**설계 반영**: 의존성 없이 동작하도록 `emoji-data.txt`에서 생성한 범위표를 기본으로 넣고, `regex`가 설치되어 있으면 속성 이스케이프를 씁니다. `©` `®` `™` 은 Extended_Pictographic 이지만 제외합니다.

## 5. 기존 도구 조사

| 도구 | 하는 일 | slopdam과의 차이 |
|---|---|---|
| **Ruff RUF001/002/003** | 문자열, 독스트링, 주석의 헷갈리는 Unicode 문자 탐지 (전각 괄호, 키릴 `о` 등). `allowed-confusables` 설정. 데이터는 VS Code의 ambiguous 문자표 기반. [RUF001](https://docs.astral.sh/ruff/rules/ambiguous-unicode-character-string), [RUF002](https://docs.astral.sh/ruff/rules/ambiguous-unicode-character-docstring/), [RUF003](https://docs.astral.sh/ruff/rules/ambiguous-unicode-character-comment/), [문자표 스크립트](https://fuchsia.googlesource.com/third_party/github.com/astral-sh/ruff/+/60e37a4c7311e6df5ded998dfcd20f04352c6d80/scripts/update_ambiguous_characters.py) | 목적이 "헷갈림 방지"(보안/버그). 이모지, 구분선, 마크다운, 한국어 문맥, 런타임 처리는 없음. **로그 호출 범위로 좁히는 기능도 없음** |
| **ftfy** | 깨진 인코딩(모지바케) 복구, `uncurl_quotes`(둥근 따옴표), `fix_character_width`(전각/반각) 등. [문서](https://ftfy.readthedocs.io/en/v5.5.1/), [소스](https://sources.debian.org/src/python-ftfy/6.3.1-1/ftfy/fixes.py) | 인코딩 복구가 주목적. 대시, 이모지, 한국어 처리 없음. S2 단계 설계에 참고 |
| **textlint** + `no-zero-width-spaces`, `preset-japanese` | 일본어 문서 린트 (보이지 않는 문자, 문장 끝 부호 등). [규칙 목록](https://github.com/azu/textlint/wiki/Collection-of-textlint-rule), [preset-japanese](https://socket.dev/npm/package/textlint-rule-preset-japanese) | 마크다운 문서 대상. **한국어 프리셋은 찾지 못함**. 코드 속 로그 문자열이나 런타임 처리는 없음 |
| **UTS #39 confusables / skeleton** | 비슷해 보이는 문자를 원형으로 매핑해 비교. [Unicode TR39](https://unicode.org/reports/tr39/), [Go 구현](https://github.com/mtibben/confusables) | 비교 전용이라 사람이 읽을 결과를 만들지 않음. **문자군(4.1장) 정의에 참고 데이터로 사용** |
| **slop-chop**, **unslopify**, **unslop**, **demdash** | AI 문체(em dash, 상투 표현) 제거 도구. CLI, GitHub Action, 문서 린터 형태. [slop-chop](https://enterprisedna.co/directories/mcp/dcadolph-slop-chop), [unslopify](https://pypi.org/project/unslopify/), [unslop](https://awesome.ecosyste.ms/projects/github.com%2FMohamedAbdallah-14%2Funslop), [demdash](https://github.com/dpup/demdash) | 대상이 산문과 문서. **로거 포맷터 형태, 한국어 `ㅡ`, reader/dev 분리는 없음** (검색 요약 기준, 각 저장소 재확인 필요) |
| **avoid-ai-writing** (Claude 스킬) | AI 문체를 다시 쓰도록 하는 프롬프트. [링크](https://tessl.io/registry/skills/github/pchalasani/claude-code-tools/avoid-ai-writing) | 생성 단계 지시라 결정적이지 않음. 규칙 아이디어(상투 표현 목록) 참고 |

## 6. slopdam의 위치 (차별점)

1. **런타임 포맷터 형태**: 기존 도구는 모두 문서나 소스를 정적으로 다룹니다. 로거에 붙여 출력 시점에 정리하는 도구는 찾지 못했습니다.
2. **한국어 1급 지원**: `ㅡ` 3종 코드포인트, 물결표 범위, 한글 뒤 감탄부호, 한국어 상투 표현.
3. **독자별 출력 (reader/dev)**: 같은 탐지 결과를 일반 사용자용과 개발자용으로 다르게 치환합니다.
4. **로그 호출 범위 린트**: 문자열 전체가 아니라 로그/print 호출 인자만 검사해서 오탐을 줄입니다.

## 7. 후속 확인 목록

- [ ] 2015 개정 문장 부호 규정 원문: 줄표 띄어쓰기, 물결표와 붙임표의 범위 표기
- [ ] slop-chop, unslopify, demdash 저장소의 실제 규칙 목록과 라이선스 (규칙 데이터 재사용 가능 여부)
- [ ] VS Code ambiguous 문자표와 UTS #39 confusables.txt 라이선스 (Unicode License V3 예상)
- [ ] 한국어 상투 표현 목록: 실제 AI 생성 로그 수집 후 빈도 분석
