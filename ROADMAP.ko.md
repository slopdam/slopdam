# 로드맵

[English](ROADMAP.md) | [한국어](ROADMAP.ko.md)

slopdam은 팀이 쓰는 모든 언어에서 AI가 남긴 흔적이 로그와 화면에 나오지 않게 합니다. 이 문서는 프로젝트가 어디로, 어떤 순서로 가는지 적습니다. 날짜는 약속하지 않으며, 마일스톤은 체크리스트를 마치면 배포합니다. 의견과 제안은 이슈로 남겨 주세요.

## 모든 언어에 같은 개념

모든 구현은 다음 네 가지를 지킵니다.

1. **엔진 하나, 프로필 둘.** 탐지는 같고, `reader`는 사람이 읽기 쉬운 문장을, `dev`는 grep과 파싱이 쉬운 문장을 씁니다.
2. **흔적을 막는 두 지점.** 실행 중에는 그 언어의 로거용 포맷터가 출력을 정리합니다. 병합 전에는 린터가 소스 코드의 흔적을 찾고, 안전한 것은 고칩니다.
3. **결정적이고 보수적.** 같은 입력과 설정이면 결과가 늘 같고, 두 번 정리해도 바뀌지 않으며, 날짜, 옵션, URL, 경로, 코드, 한중일 본문은 건드리지 않습니다. 규칙은 모델도 네트워크도 쓰지 않습니다. 단어 목록으로는 다 잡을 수 없는 인사말을 위한 모델([chatter-tagger](https://huggingface.co/slopdam/chatter-tagger)) 하나만 선택 사항으로 두며, 기본으로 꺼져 있고, 지우기만 하며, 모든 삭제는 정해진 안전 장치를 통과해야 합니다.
4. **실행 의존성 없음.** 언어별 핵심 패키지는 외부 의존성 없이 동작합니다. 표준 라이브러리로 명세를 돌릴 수 없는 경우만 예외입니다: Go는 `regexp`에 뒤쪽 탐색과 역참조가 없어 regexp2를 씁니다.

## 다른 언어가 같은 결과를 내는 방법

```
slopdam/ (이 저장소)
  ├── spec/    규칙 목록 + 적합성 사례
  ├── src/     Python    slopdam            기준 구현, CLI, pre-commit, GitHub Action
  ├── js/      JS/TS     @slopdam/core      0.5
  ├── go/      Go        slopdam            0.6
  ├── java/    JVM       slopdam            0.6
  └── rust/    Rust      slopdam (crate)    계획
```

- [spec/](spec/README.ko.md)은 Python과 무관하게 동작을 정의합니다. `spec/conformance.json`의 모든 사례를 통과하면 올바른 구현이며, 각 구현의 CI가 이 사례를 실행합니다.
- 모든 구현은 이 저장소 안의 자기 폴더에 두고, 그 생태계의 빌드, 테스트, 배포 도구를 그대로 씁니다. `spec/`을 직접 읽으므로 규칙 변경과 그것이 모든 언어에 미치는 영향을 PR 하나에서 검토하고 테스트합니다.
- 패키지마다 배포 태그가 따로 있습니다(Python은 `v0.x`, JavaScript는 `js-v0.x`).
- 새 규칙은 적합성 사례와 함께 명세에 먼저 들어가고, 각 구현은 새 사례를 통과하는 것으로 따라옵니다.
- 언어별 패키지가 나오기 전에도 어느 언어에서나 CLI를 쓸 수 있습니다. 소스 코드는 `slopdam check`, 출력은 파이프로 `slopdam clean`, 그리고 pre-commit 훅과 GitHub Action이 있습니다.

## 계획된 패키지

| 언어 | 패키지 | 실행 중 연동 | 린트 연동 |
|---|---|---|---|
| Python | `slopdam` (PyPI) | `logging`, 다음은 structlog와 loguru | `slopdam check`와 `fix`, pre-commit, GitHub Action |
| JavaScript, TypeScript | `@slopdam/core` (npm) | pino, winston | ESLint 규칙 (`@slopdam/core/eslint`) |
| Go | `github.com/slopdam/slopdam/go` | `slog.Handler`, zap core | `go vet` 분석기 |
| Java, Kotlin | `io.github.slopdam:slopdam` (Maven Central) | Logback, Log4j 2 `%slopdam` 변환기 | CLI |
| Rust | `slopdam` (crates.io) | `tracing` 레이어, `log` | CLI |
| 모든 언어 | CLI | 파이프로 `slopdam clean` | CLI, pre-commit, GitHub Action |

## 마일스톤

### 0.3: 언어 중립 기반 (배포됨)

- [x] 명세: 기준 구현에서 생성하고 CI에서 확인하는 규칙 목록과 적합성 사례
- [x] GitHub Action (`uses: slopdam/slopdam@v0.3.0`)
- [x] `check --format github`(PR 주석)과 `--format sarif`(코드 스캐닝)
- [x] 타입 정보(`py.typed`)와 CI의 패키지 빌드 검사

### 0.4: Python 연동과 규칙 품질 (배포됨)

- [x] structlog, loguru 어댑터
- [x] 속성 기반 테스트(멱등성, 보호 구역)와 CI 벤치마크
- [x] 편집기와 다른 도구를 위한 `slopdam check -` (표준 입력 검사)

### 0.5: JavaScript와 TypeScript (배포됨: PyPI slopdam 0.5.0, npm @slopdam/core 0.2.0)

- [x] 모든 적합성 사례를 통과하는 `@slopdam/core` ([js/](js/README.ko.md), Node.js 20 이상, ESM과 CommonJS)
- [x] 첫 npm 배포 (`js-v0.1.0`)
- [x] pino, winston 연동 (`@slopdam/core/pino`, `@slopdam/core/winston`)
- [x] ESLint 규칙 `slopdam/no-slop` (`@slopdam/core/eslint`): 로그 호출의 문자열 인자 검사와 자동 수정

### 0.6: Go와 JVM (배포됨: Go 모듈 0.1.0, Java 0.1.0, slopdam 0.6.0, @slopdam/core 0.2.1)

- [x] 모든 적합성 사례를 통과하는 Go 모듈 ([go/](go/README.ko.md))
- [x] `log/slog` 핸들러 (`slopdam.NewHandler`)
- [x] 자동 수정을 제안하는 `go vet` 분석기 (`slopdamvet`)
- [x] 모든 적합성 사례를 통과하는 Java 라이브러리 ([java/](java/README.ko.md)), Logback과 Log4j 2용 `%slopdam` 변환기 포함

### 0.7: 데이터와 인사말 모델 (진행 중, slopdam 0.7.0과 @slopdam/core 0.3.0에 1a, 1b, slopdam 0.8.0과 @slopdam/core 0.4.0에 2a 반영)

[log-slop](https://huggingface.co/datasets/slopdam/log-slop) 데이터셋과 [chatter-tagger](https://huggingface.co/slopdam/chatter-tagger) 모델을 Hugging Face에 공개했습니다. 이번 단계에서는 데이터를 실제 로그에 더 가깝게 만들고, 규칙으로 할 수 있는 일은 규칙으로 옮기고, 모델을 slopdam이 도는 곳에서 쓸 수 있게 합니다.

- [x] 1. log-slop v5: 구조화된 로그와 여러 줄 로그 (JSON lines, logfmt, 스택 트레이스, 표) ([#34](https://github.com/slopdam/slopdam/issues/34))
- [x] 1a. 엔진의 구조화 출력 처리: 정렬된 열과 표는 유지하고 logfmt 메시지는 정리, 명세와 모든 구현에 반영 ([#40](https://github.com/slopdam/slopdam/issues/40))
- [x] 1b. JSON과 logfmt 문자열 안의 둥근 따옴표는 `\"`로 바꿔 줄이 깨지지 않게 함 ([#43](https://github.com/slopdam/slopdam/pull/43))
- [x] 2a. 중국어와 일본어 줄은 전각 문장 부호(`，：！`)를 그대로 둠, 명세와 모든 구현에 반영
- [x] 2. log-slop v6: 일본어와 중국어 메시지, 네 언어로 손으로 쓴 정답 세트 ([#35](https://github.com/slopdam/slopdam/issues/35))
- [ ] 3. 알려진 인사말은 규칙으로: `tone.chatty` 목록을 늘리고 `strong` 단계에서 고치기, 명세와 모든 구현에 반영 ([#36](https://github.com/slopdam/slopdam/issues/36))
- [ ] 4. `slopdam[chatter]`: Python과 `slopdam clean --chatter`에서 인사말 모델 사용, 기본은 꺼짐 ([#37](https://github.com/slopdam/slopdam/issues/37))
- [ ] 5. 브라우저 데모에서 인사말 모델 실행 (ONNX) ([#38](https://github.com/slopdam/slopdam/issues/38))
- [ ] 6. chatter-tagger v2: v5로 학습하고, 새로 쓴 손글씨 세트에서 같은 기준을 넘을 때만 공개 ([#39](https://github.com/slopdam/slopdam/issues/39))

### 0.8: Rust와 편집기

- [ ] `tracing` 레이어를 갖춘 Rust 크레이트
- [ ] `check --format json` 기반 편집기 지원 (VS Code부터)

### 1.0: 안정판

- [ ] 명세를 고정하기 전에 직접 쓴 표 대신 유니코드 `emoji-data.txt`에서 생성한 이모지 범위로 채우기
- [ ] 명세 버전 1 고정, 출력 변경은 메이저 버전에서만
- [ ] 모든 구현이 CI에서 전체 적합성 사례를 통과
- [ ] 명세에서 규칙 문서를 생성하는 문서 사이트

## 범위 밖

- AI가 쓴 글인지 판별하기. 믿을 만하게 할 수 없고, slopdam은 그걸 알 필요가 없습니다.
- 언어 모델로 문장 다시 쓰기. 규칙은 결정적이며, 선택 사항인 인사말 모델은 줄 맨 앞의 인사말을 지우는 일만 할 수 있습니다.

## 참여 방법

- slopdam이 놓친 흔적이나 잘못 바꾼 문장을 이슈 템플릿으로 알려 주세요. 확인된 사례는 적합성 사례가 됩니다.
- 언어 구현 시작하기: 이슈로 언어를 맡겠다고 알린 뒤, 새 폴더에서 `conformance.json`을 통과할 때까지 명세를 구현합니다.
- 먼저 [CONTRIBUTING.ko.md](CONTRIBUTING.ko.md)를 읽어 주세요. 모든 커밋에 DCO 서명이 필요합니다.
