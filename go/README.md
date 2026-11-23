<p align="center">
  <img src="https://raw.githubusercontent.com/slopdam/slopdam/main/docs/assets/logo.png" alt="slopdam logo: tangled lines held back by a dam, straight lines flowing out" width="140">
</p>

<h1 align="center">slopdam for Go</h1>

<p align="center"><i>The Go port of <a href="https://github.com/slopdam/slopdam">slopdam</a>: em dashes, emoji, separator lines and markdown stay out of your logs.</i></p>

<p align="center"><b>English</b> | <a href="https://github.com/slopdam/slopdam/blob/main/go/README.ko.md">한국어</a></p>

<p align="center">
  <a href="https://github.com/slopdam/slopdam/actions/workflows/ci.yml"><img src="https://github.com/slopdam/slopdam/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pkg.go.dev/github.com/slopdam/slopdam/go"><img src="https://pkg.go.dev/badge/github.com/slopdam/slopdam/go.svg" alt="Go reference"></a>
  <a href="https://github.com/slopdam/slopdam/blob/main/spec/README.md"><img src="https://img.shields.io/badge/spec-v1%20conformance%20tested-informational.svg" alt="Spec v1: conformance tested"></a>
  <a href="https://github.com/slopdam/slopdam/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
</p>

Package `slopdam` removes the traces AI coding tools leave in log messages and console output: em dashes and look-alike lines (including the Korean `ㅡ`), decorative emoji, separator lines, markdown bold, curly quotes and invisible characters. It gives exactly the same output as the Python and JavaScript packages, because all three are tested against the same [conformance cases](https://github.com/slopdam/slopdam/blob/main/spec/README.md).

```
input : ✅ **Saved** — 3 rows processed 🎉
reader: Saved: 3 rows processed
dev   : [OK] Saved - 3 rows processed
```

- `reader` (default): plain text for people, such as CLI messages, alerts and reports.
- `dev`: grep-friendly text for log files and collectors. Status emoji become `[OK]`, `[FAIL]` and `[WARN]` instead of disappearing.

## Install

Go 1.22 or later.

```bash
go get github.com/slopdam/slopdam/go
```

## Use

```go
import "github.com/slopdam/slopdam/go"

slopdam.Clean("✅ **Saved** — 3 rows 🎉")               // "Saved: 3 rows"
slopdam.Clean("✅ **저장 완료** ㅡ 3건 처리했습니다! 🎉")  // "저장 완료: 3건 처리했습니다."

dev := slopdam.MustNew(slopdam.Options{Profile: "dev"})
dev.Clean("✅ Upload done — 3 files")                     // "[OK] Upload done - 3 files"
dev.CleanLevel("❌ Upload failed", slopdam.LevelError)    // "Upload failed" (the level already says it)

for _, f := range dev.Findings(`log.Info("🚀 Started — ok")`) {
	fmt.Println(f.RuleID, f.Text, f.Start, f.End) // emoji.pictograph 🚀 10 15, dash.run — 22 27
}
```

| Option | Values | Default |
|---|---|---|
| `Profile` | `"reader"`, `"dev"` | `"reader"` |
| `Level` | `"basic"`, `"strong"` (also removes filler words), `"strict"` (also reports any non-ASCII symbol) | `"basic"` |
| `Disable` | rule IDs or groups, such as `[]string{"emoji"}` or `[]string{"dash.run"}` | none |
| `DashInline` | what an inline dash becomes in `reader`: `"colon"`, `"comma"`, `"hyphen"`, `"space"` | `"colon"` |

A `Sanitizer` is safe for concurrent use. `Findings` reports what `Clean` would change, with `Start` and `End` as byte offsets into the input. URLs, inline code, `key=value` values and file paths are never changed, and cleaning twice gives the same result as cleaning once.

## How it stays in step with Python

The rules are not rewritten by hand. `go generate` copies the repository's [spec/rules.json](https://github.com/slopdam/slopdam/blob/main/spec/README.md) into `spec_data.go`; its patterns are translated from Python's regular expression dialect when the package loads (Unicode `\w`, `\s` and `\b`, and Python's `^` and `$`), and only the four context-dependent actions are written in Go. Every pull request runs the conformance cases against Python, JavaScript and Go. On 20,000 random inputs, Go and Python gave identical results.

The one dependency is [regexp2](https://github.com/dlclark/regexp2) (MIT), because Go's `regexp` has no lookbehind or back references, which the spec's patterns use.

## Roadmap

Part of slopdam milestone 0.6 ([roadmap](https://github.com/slopdam/slopdam/blob/main/ROADMAP.md)): this package first, then a `log/slog` handler and a `go vet` analyzer.

## Contributing

A rule change is made once, in the Python reference and `spec/`, with conformance cases; run `go generate` here to pick it up. Contributions follow the slopdam [contribution guide](https://github.com/slopdam/slopdam/blob/main/CONTRIBUTING.md) (DCO sign-off), [code of conduct](https://github.com/slopdam/slopdam/blob/main/CODE_OF_CONDUCT.md) and [security policy](https://github.com/slopdam/slopdam/blob/main/SECURITY.md).

```bash
cd go
go generate ./... && go test ./...
```

## License

[MIT](https://github.com/slopdam/slopdam/blob/main/LICENSE)
