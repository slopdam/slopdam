<h1 align="center">JavaScript용 slopdam</h1>

<p align="center"><i><a href="https://github.com/slopdam/slopdam">slopdam</a>의 JavaScript, TypeScript 구현: 긴 대시, 이모지, 구분선, 마크다운이 로그에 남지 않게 합니다.</i></p>

<p align="center"><a href="https://github.com/slopdam/slopdam/blob/main/js/README.md">English</a> | <b>한국어</b></p>

<p align="center">
  <a href="https://github.com/slopdam/slopdam/actions/workflows/ci.yml"><img src="https://github.com/slopdam/slopdam/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/slopdam/slopdam/blob/main/spec/README.ko.md"><img src="https://img.shields.io/badge/spec-v1%20conformance%20tested-informational.svg" alt="명세 v1: 적합성 테스트"></a>
  <a href="https://github.com/slopdam/slopdam/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="라이선스: MIT"></a>
</p>

`@slopdam/core`는 AI 코딩 도구가 로그 메시지와 콘솔 출력에 남기는 흔적을 걷어냅니다. 긴 대시와 그와 닮은 선(한글 `ㅡ` 포함), 장식 이모지, 구분선, 마크다운 굵은 글씨, 둥근 따옴표, 보이지 않는 문자가 대상입니다. Python 패키지와 같은 [적합성 사례](https://github.com/slopdam/slopdam/blob/main/spec/README.ko.md)로 테스트하므로 결과가 똑같습니다.

```
입력  : ✅ **저장 완료** ㅡ 2024–2025년 데이터 3건 처리했습니다! 🎉
reader: 저장 완료: 2024~2025년 데이터 3건 처리했습니다.
dev   : [OK] 저장 완료 - 2024-2025년 데이터 3건 처리했습니다!
```

- `reader`(기본): 사람이 읽는 글. CLI 메시지, 알림, 보고서에 씁니다.
- `dev`: 검색하기 쉬운 글. 로그 파일과 수집기에 씁니다. 상태 이모지는 지우지 않고 `[OK]`, `[FAIL]`, `[WARN]`으로 바꿉니다.

## 설치

Node.js 20 이상 또는 최신 브라우저에서 동작합니다. 실행 의존성이 없고, ESM과 CommonJS 빌드에 TypeScript 타입이 들어 있습니다.

```bash
npm install @slopdam/core
```

첫 npm 배포(`js-v0.1.0`)를 준비 중입니다. 그 전에는 이 저장소의 `js/`에서 빌드해 쓰세요.

## 사용법

```js
import { clean, Sanitizer } from "@slopdam/core";

clean("✅ **저장 완료** ㅡ 3건 처리했습니다! 🎉");         // "저장 완료: 3건 처리했습니다."
clean("✅ **Saved** — 3 rows 🎉");                      // "Saved: 3 rows"

const dev = new Sanitizer({ profile: "dev" });
dev.clean("✅ 업로드 완료 ㅡ 3개 파일");                  // "[OK] 업로드 완료 - 3개 파일"
dev.clean("❌ 업로드 실패", "error");                     // "업로드 실패" (로그 레벨이 이미 실패를 말함)

console.log(dev.findings("log.info('🚀 시작 ㅡ 정상')"));
// [ { ruleId: 'emoji.pictograph', text: '🚀', fix: '', ... },
//   { ruleId: 'dash.run', text: 'ㅡ', fix: ' - ', ... } ]
```

CommonJS에서도 `require("@slopdam/core")`로 똑같이 씁니다.

### 옵션

| 옵션 | 값 | 기본값 |
|---|---|---|
| `profile` | `"reader"`, `"dev"` | `"reader"` |
| `level` | `"basic"`, `"strong"`(군더더기 표현도 제거), `"strict"`(ASCII가 아닌 기호를 모두 알림) | `"basic"` |
| `disable` | 끌 규칙 ID나 군. 예: `["emoji"]`, `["dash.run"]` | `[]` |
| `dashInline` | `reader`에서 문장 중간 대시를 바꿀 문자: `"colon"`, `"comma"`, `"hyphen"`, `"space"` | `"colon"` |

`clean()`의 두 번째 인자는 로그 레벨입니다. 이름(`"error"`, `"warning"`)이나 Python logging 숫자(40, 30)로 줍니다. `findings()`는 `clean()`이 바꿀 부분을 돌려주며, `start`와 `end`는 입력 안의 UTF-16 위치입니다.

URL, 인라인 코드, `key=value`의 값, 파일 경로는 바꾸지 않습니다. 두 번 정리해도 한 번 정리한 결과와 같습니다.

## Python과 같은 결과를 내는 방법

규칙을 손으로 다시 쓰지 않습니다. 빌드할 때 저장소의 [spec/](https://github.com/slopdam/slopdam/blob/main/spec/README.ko.md)을 직접 읽고, 그 안의 패턴은 패키지를 불러올 때 Python 정규식 문법에서 변환됩니다(유니코드 `\w`, `\s`, `\b`와 Python의 `^`, `$`). 문맥에 따라 바꾸는 동작 네 가지만 TypeScript로 작성했습니다. PR마다 Python 패키지와 이 패키지의 ESM, CommonJS 빌드에 같은 적합성 사례를 실행하므로 한 언어에서만 규칙이 바뀔 수 없습니다. 무작위 입력 20,000개에서 두 패키지의 결과가 같았습니다.

## 로드맵

slopdam 0.5 마일스톤의 일부입니다([로드맵](https://github.com/slopdam/slopdam/blob/main/ROADMAP.ko.md)). 이 핵심 패키지를 먼저 만들고, 다음으로 pino, winston 포맷터와 `eslint-plugin-slopdam`을 만듭니다.

## 기여

규칙 변경은 Python 기준 구현과 `spec/`에서 적합성 사례와 함께 한 번만 합니다. 이 패키지는 다음 빌드에서 이를 반영하고, 같은 PR에서 통과 여부가 드러납니다. 기여는 slopdam의 [기여 안내](https://github.com/slopdam/slopdam/blob/main/CONTRIBUTING.ko.md)(DCO 서명), [행동 강령](https://github.com/slopdam/slopdam/blob/main/CODE_OF_CONDUCT.ko.md), [보안 정책](https://github.com/slopdam/slopdam/blob/main/SECURITY.ko.md)을 따릅니다.

```bash
cd js
npm install
npm test          # 빌드한 뒤 적합성 사례와 API 테스트를 실행
```

## 라이선스

[MIT](https://github.com/slopdam/slopdam/blob/main/LICENSE)
