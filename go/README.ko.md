<p align="center">
  <img src="https://raw.githubusercontent.com/slopdam/slopdam/main/docs/assets/logo.png" alt="slopdam logo: tangled lines held back by a dam, straight lines flowing out" width="140">
</p>

<h1 align="center">Go용 slopdam</h1>

<p align="center"><i><a href="https://github.com/slopdam/slopdam">slopdam</a>의 Go 구현: 긴 대시, 이모지, 구분선, 마크다운이 로그에 남지 않게 합니다.</i></p>

<p align="center"><a href="https://github.com/slopdam/slopdam/blob/main/go/README.md">English</a> | <b>한국어</b></p>

<p align="center">
  <a href="https://github.com/slopdam/slopdam/actions/workflows/ci.yml"><img src="https://github.com/slopdam/slopdam/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pkg.go.dev/github.com/slopdam/slopdam/go"><img src="https://pkg.go.dev/badge/github.com/slopdam/slopdam/go.svg" alt="Go reference"></a>
  <a href="https://github.com/slopdam/slopdam/blob/main/spec/README.ko.md"><img src="https://img.shields.io/badge/spec-v1%20conformance%20tested-informational.svg" alt="명세 v1: 적합성 테스트"></a>
  <a href="https://github.com/slopdam/slopdam/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="라이선스: MIT"></a>
</p>

`slopdam` 패키지는 AI 코딩 도구가 로그 메시지와 콘솔 출력에 남기는 흔적을 걷어냅니다. 긴 대시와 그와 닮은 선(한글 `ㅡ` 포함), 장식 이모지, 구분선, 마크다운 굵은 글씨, 둥근 따옴표, 보이지 않는 문자가 대상입니다. Python, JavaScript 패키지와 같은 [적합성 사례](https://github.com/slopdam/slopdam/blob/main/spec/README.ko.md)로 테스트하므로 결과가 똑같습니다.

```
입력  : ✅ **저장 완료** ㅡ 2024–2025년 데이터 3건 처리했습니다! 🎉
reader: 저장 완료: 2024~2025년 데이터 3건 처리했습니다.
dev   : [OK] 저장 완료 - 2024-2025년 데이터 3건 처리했습니다!
```

- `reader`(기본): 사람이 읽는 글. CLI 메시지, 알림, 보고서에 씁니다.
- `dev`: 검색하기 쉬운 글. 로그 파일과 수집기에 씁니다. 상태 이모지는 지우지 않고 `[OK]`, `[FAIL]`, `[WARN]`으로 바꿉니다.

## 설치

Go 1.22 이상에서 동작합니다.

```bash
go get github.com/slopdam/slopdam/go
```

## 사용법

```go
import "github.com/slopdam/slopdam/go"

slopdam.Clean("✅ **저장 완료** ㅡ 3건 처리했습니다! 🎉")  // "저장 완료: 3건 처리했습니다."
slopdam.Clean("✅ **Saved** — 3 rows 🎉")               // "Saved: 3 rows"

dev := slopdam.MustNew(slopdam.Options{Profile: "dev"})
dev.Clean("✅ 업로드 완료 ㅡ 3개 파일")                    // "[OK] 업로드 완료 - 3개 파일"
dev.CleanLevel("❌ 업로드 실패", slopdam.LevelError)       // "업로드 실패" (로그 레벨이 이미 실패를 말함)

for _, f := range dev.Findings(`log.Info("🚀 시작 ㅡ 정상")`) {
	fmt.Println(f.RuleID, f.Text, f.Start, f.End) // emoji.pictograph 🚀 10 15, dash.run ㅡ 21 26
}
```

| 옵션 | 값 | 기본값 |
|---|---|---|
| `Profile` | `"reader"`, `"dev"` | `"reader"` |
| `Level` | `"basic"`, `"strong"`(군더더기 표현도 제거), `"strict"`(ASCII가 아닌 기호를 모두 알림) | `"basic"` |
| `Disable` | 끌 규칙 ID나 군. 예: `[]string{"emoji"}`, `[]string{"dash.run"}` | 없음 |
| `DashInline` | `reader`에서 문장 중간 대시를 바꿀 문자: `"colon"`, `"comma"`, `"hyphen"`, `"space"` | `"colon"` |

`Sanitizer`는 여러 고루틴에서 함께 써도 안전합니다. `Findings`는 `Clean`이 바꿀 부분을 돌려주며, `Start`와 `End`는 입력 안의 바이트 위치입니다. URL, 인라인 코드, `key=value`의 값, 파일 경로는 바꾸지 않고, 두 번 정리해도 한 번 정리한 결과와 같습니다.

### log/slog

```go
console := slog.New(slopdam.NewHandler(slog.NewTextHandler(os.Stderr, nil), slopdam.Options{}))
file := slog.New(slopdam.NewHandler(slog.NewJSONHandler(f, nil), slopdam.Options{Profile: "dev"}))

console.Info("✅ **저장 완료** ㅡ 3건 처리했습니다!")   // msg="저장 완료: 3건 처리했습니다."
file.Info("✅ **저장 완료** ㅡ 3건 처리했습니다!")      // "msg":"[OK] 저장 완료 - 3건 처리했습니다!"
file.Error("❌ 업로드 실패", "err", err)               // "msg":"업로드 실패", err는 그대로
```

`NewHandler`는 어떤 `slog.Handler`든 감싸서 모든 레코드의 메시지를 정리합니다. 속성(attribute)은 구조화된 데이터라 그대로 두고, 구분선뿐인 레코드는 버리되 오류가 담겨 있으면 남깁니다. 표준 라이브러리의 `slogtest` 핸들러 검사를 통과합니다.

### go vet

```bash
go install github.com/slopdam/slopdam/go/vet/cmd/slopdamvet@latest
slopdamvet ./...                          # 또는: go vet -vettool=$(which slopdamvet) ./...
```

```
sync.go:12:14: slopdam emoji.pictograph: "✅" should be ""
sync.go:12:33: slopdam dash.run: "ㅡ" should be ": "
```

`slopdamvet -fix ./...`는 제안한 수정을 적용합니다. `log.Printf("✅ %d건 동기화 ㅡ 완료", n)`은 `log.Printf("%d건 동기화: 완료", n)`이 됩니다. `log`, `slog`, `fmt`와 이름에 `log`가 들어간 받는 쪽(`s.logger.Warn`) 호출의 문자열 인자를 검사하고, `"a" + b` 같은 이어 붙이기도 포함합니다. 문자열 안의 글자만 고치며 따옴표, 이스케이프, `%v`, `%d` 같은 서식 동사는 그대로 둡니다. 옵션: `-profile dev`, `-level`, `-disable emoji,dash.run`, `-dash-inline`, `-receivers`. 분석기는 별도 모듈(`go/vet`, Go 1.26 이상)이라 패키지 본체는 `golang.org/x/tools`에 의존하지 않습니다.

## Python과 같은 결과를 내는 방법

규칙을 손으로 다시 쓰지 않습니다. `go generate`가 저장소의 [spec/rules.json](https://github.com/slopdam/slopdam/blob/main/spec/README.ko.md)을 `spec_data.go`로 복사하고, 그 안의 패턴은 패키지를 불러올 때 Python 정규식 문법에서 변환됩니다(유니코드 `\w`, `\s`, `\b`와 Python의 `^`, `$`). 문맥에 따라 바꾸는 동작 네 가지만 Go로 작성했습니다. PR마다 Python, JavaScript, Go에 같은 적합성 사례를 실행합니다. 무작위 입력 20,000개에서 Go와 Python의 결과가 같았습니다.

의존성은 [regexp2](https://github.com/dlclark/regexp2)(MIT) 하나입니다. Go의 `regexp`는 명세의 패턴이 쓰는 뒤쪽 탐색(lookbehind)과 역참조를 지원하지 않기 때문입니다.

## 로드맵

slopdam 0.6 마일스톤의 일부입니다([로드맵](https://github.com/slopdam/slopdam/blob/main/ROADMAP.ko.md)). 이 패키지, `log/slog` 핸들러, `go vet` 분석기로 이루어집니다.

## 기여

규칙 변경은 Python 기준 구현과 `spec/`에서 적합성 사례와 함께 한 번만 합니다. 여기서는 `go generate`를 실행해 반영합니다. 기여는 slopdam의 [기여 안내](https://github.com/slopdam/slopdam/blob/main/CONTRIBUTING.ko.md)(DCO 서명), [행동 강령](https://github.com/slopdam/slopdam/blob/main/CODE_OF_CONDUCT.ko.md), [보안 정책](https://github.com/slopdam/slopdam/blob/main/SECURITY.ko.md)을 따릅니다.

```bash
cd go
go generate ./... && go test ./...
```

## 라이선스

[MIT](https://github.com/slopdam/slopdam/blob/main/LICENSE)
