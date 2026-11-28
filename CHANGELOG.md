# Changelog

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning follows the output stability policy in [GOVERNANCE.md](GOVERNANCE.md).

## [Unreleased]

### Output changes
- At the `strong` level, `tone.chatty` removes a known opener at the start of a line when more text follows: about 80 phrases in English, Korean, Japanese and Chinese (`Great news!`, `Heads up:`, `Here's the summary:`, `살펴보겠습니다.`, `좋은 소식입니다!`, `さて、`, `好消息！`). The next word is capitalized when it is a plain lowercase word with a vowel, so `Heads up: cache warmed` becomes `Cache warmed` while `npm` and `k8s-node-01` keep their case. A line start may have indentation, a list marker, a heading marker or dev's `[OK]` tag. `basic` output does not change; the existing report-only `tone.chatty` rule still flags chatty phrases anywhere. The spec gains the `opener` function and a conformance group, `chatty`, with look-alike lines that must not change (`Great Lakes shard`, `Finally block ran`, `FYI-bot`, `결론 필드가`, `状態：OK`). On 20,000 random inputs at `strong`, JavaScript, Go and Java match Python exactly (#36).

### Changed
- `go/vet` requires the core module at go/v0.3.0 instead of v0.1.0, so its findings and suggested fixes match slopdam 0.8.0: the structured-output fixes (#40), the quote fix (#43) and full-width punctuation kept on Chinese and Japanese lines (#49). Released as go/vet/v0.2.0.

## [0.8.0] - 2026-11-28

### Output changes
- Chinese and Japanese lines keep their full-width punctuation. `width.fullwidth` used to turn `处理完成，共 42 条记录。` into `处理完成,共 42 条记录。` and `注意：` into `注意:`, mixing the two widths on one line. A line with kana or CJK ideographs is now left as written; Korean and English lines still get ASCII. The spec gains `charsets.han_kana` and a conformance group, `cjk`. On 20,000 random inputs, JavaScript, Go and Java match Python exactly. Found while adding Japanese and Chinese to log-slop (#35).

## [0.7.0] - 2026-11-28

### Output changes
- A curly double quote inside a double-quoted string becomes `\"`, so JSON lines and logfmt messages stay valid: `{"msg":"from “analytics”"}` becomes `{"msg":"from \"analytics\""}` instead of breaking the JSON. Outside a string it still becomes `"`. Found while building structured log data for log-slop (#34).
- Structured output is left intact (#40). Found while building structured log data for log-slop (#34). In every port:
  - Only lines a rule changed are tidied. A line with no trace keeps its spacing, so aligned columns such as `kubectl get pods` output and tables are no longer squeezed (`NAME      READY` used to become `NAME READY`).
  - A dash run that touches a table edge (`+ |` or a box-drawing corner or junction) is kept: `+------+`, `|------|` and `┌─────┬─────┐` used to lose their dashes.
  - The value of a logfmt key ending in `msg`, `message` or `error` is cleaned: `msg="✅ Saved — done"` becomes `msg="Saved: done"`. Other `key=value` values stay protected.
  - No space is left before a closing quote when a trace at the end of a quoted string is removed: `{"msg":"Saved 🎉"}` becomes `{"msg":"Saved"}`, not `{"msg":"Saved "}`.
  - `md.fence` no longer consumes the line break after a fence; the empty line it leaves is dropped as before, so the output is the same.
- The spec's `tidy` block gains `scope` and `quote_space`. A new conformance group, `structured`, covers tables, aligned columns, logfmt, JSON lines, stack traces and diffs. On 20,000 random inputs, JavaScript, Go and Java match Python exactly.

### Fixed
- `go/vet` v0.1.0 was tagged on the commit before its `go.mod` dropped the `replace` directive, so `go install .../slopdamvet@v0.1.0` refused it. v0.1.1 is the first installable version, and `go.mod` retracts v0.1.0 so `@latest` never picks it.

## [0.6.0] - 2026-11-25

### Added
- `java/`: the Java library `io.github.slopdam:slopdam` (Java 11+, no dependencies) with `Sanitizer.clean` and `findings`, plus `slopdam-logback` and `slopdam-log4j2`, which add a `%slopdam` pattern converter with a profile per appender. It passes every conformance case, and on 20,000 random inputs it matched the Python package exactly. CI runs it on Java 17 and 21.
- `go/`: the Go module `github.com/slopdam/slopdam/go`, with `Clean`, `Sanitizer.Clean`, `CleanLevel` and `Findings`. It passes every conformance case, and on 20,000 random inputs it matched the Python package exactly. CI runs it on Go 1.22 and the current release and checks that `spec_data.go` matches `spec/rules.json`. Module versions are tagged `go/v*`. `slopdam.NewHandler` wraps a `log/slog` handler and cleans record messages; it passes the standard `slogtest` checks. `go/vet` (its own module) is a `go/analysis` analyzer with suggested fixes, run as `slopdamvet` or `go vet -vettool`.
- Logo (`docs/assets/logo.svg`, `logo.png`, and a square `avatar.png` for the GitHub and npm avatars), shown at the top of the READMEs.

### Fixed
- `slopdam fix` repeats its edits until the string stops changing, so one run is enough when removing a trace exposes another: `"‒• 항목"` used to become `"• 항목"` and needed a second run to reach `"- 항목"`. Found by the Go analyzer's fuzz run.

## [0.5.0] - 2026-11-24

### Added
- `js/`: `@slopdam/core`, the JavaScript and TypeScript package, in this repository. It reads `spec/` directly and passes every conformance case in its ESM and CommonJS builds; CI runs it on Node.js 20, 22 and 24. npm releases use `js-v*` tags. It includes pino (`@slopdam/core/pino`) and winston (`@slopdam/core/winston`) integrations and an ESLint rule (`@slopdam/core/eslint`). See `js/CHANGELOG.md`.
- `spec/rules.json` now holds every constant a port needs: `charsets.hangul_choseong`, `dash_word_before` and `dash_word_after` for `dash_run`, and `tidy` (the space-collapsing pattern and the pass limit). Found while writing the JavaScript port.

### Output changes
- A dash next to a quote is judged as sitting between words: `A — "B"` becomes `A: "B"` (`A - "B"` in `dev`) instead of `A"B"`, and `“A” — B` becomes `"A": B`. Quotes (`" ' “ ” ‘ ’`) join the brackets and `%` in `dash_word_before` and `dash_word_after`. Found by the ESLint rule's tests.

## [0.4.1] - 2026-11-24

### Added
- README demo recording and screenshots in English and Korean, made from real runs on a sample project by `scripts/demo/make_demo.py`.

### Fixed
- `PlainFilter` on one handler no longer changes what the next handler sees. With the README setup (reader on the console, dev in the file), the file used to get the reader text, without `[OK]` tags. On Python 3.12+ the filter gives its handler a cleaned copy; before 3.12 it keeps the original message for `PlainFilter` and `PlainFormatter` on later handlers.

## [0.4.0] - 2026-11-24

### Added
- `slopdam check -` checks text from stdin; `--stdin-filename NAME` checks it as if it were that file.
- structlog processor (`slopdam.integrations.structlog.SlopdamProcessor`) and loguru patcher (`slopdam.integrations.loguru.SlopdamPatcher`). Neither library is a dependency.
- Property-based tests (Hypothesis) for idempotency, protected spans and finding spans, and `scripts/bench.py`, shown in the CI job summary.
- `test` extra: `pip install -e ".[test]"` installs everything the test suite uses.
- Conformance cases for the bugs below.

### Fixed
- `clean()` raised `IndexError` when the input already contained a character from the private-use range U+F0000 to U+FFFFD. Such characters are now kept as they are.
- `clean()` was not always idempotent. Removing one trace could expose another that an earlier rule would have caught (`‒•`, `‒# x`), `\r` and other line separators were not treated as line ends by the rules, and an indented line after an empty first line kept its indentation. `clean()` now normalizes line breaks and repeats until the text stops changing. Lines with nothing to clean take the same time as before; lines with traces take about twice as long (one more pass to confirm).
- Spaces inside protected spans (inline code, quoted `key=value` values) are no longer collapsed.

### Output changes
- `dash.hyphen` and `dash.wave` run before the markdown rules, so `‐‐‐` on its own line is removed like `---` (it used to become `---`).

## [0.3.0] - 2026-11-24

### Added
- `spec/`: a language-neutral rule catalog (`rules.json`) and conformance cases (`conformance.json`) that every implementation must pass. Both are generated from the Python source with `scripts/gen_spec.py` and checked in CI.
- GitHub Action: `uses: slopdam/slopdam@v0.3.0` runs `slopdam check` and shows findings as pull request annotations.
- `check --format github` (workflow annotations) and `--format sarif` (code scanning).
- `py.typed`, so type checkers use slopdam's type hints.
- The pre-commit hook also checks Rust, Ruby, PHP and Swift files, matching the CLI.
- ROADMAP.md: plan for JavaScript, Go, JVM and Rust packages built on the spec.

## [0.2.0] - 2026-11-23

### Added
- `reader` (default) and `dev` profiles, and `basic`, `strong` and `strict` levels.
- Context-aware handling of 25 dash-like characters, including the Hangul `ㅡ` (U+3161, U+FFDA, U+1173).
- Protected spans: URLs, inline code, `key=value` values and paths.
- `dev` status tags (`[OK]`, `[FAIL]`, `[WARN]`), omitted when the log level already says the same thing.
- Rule IDs, disabling by ID or group, `# slopdam: ignore[...]`, `check --format json`, `--dash-inline`.
- `slopdam fix`: rewrites string arguments of log and print calls in Python files (or every string with `--scope strings`) using the syntax tree. Keeps quotes, prefixes, escapes, f-string expressions and placeholders, and writes only code that compiles. `--diff` previews.
- Configuration in `slopdam.toml` or `[tool.slopdam]` in `pyproject.toml` (profile, level, disable, dash.inline, lint.scope/include/exclude), plus `--config` and `SLOPDAM_CONFIG`. Uses `tomllib` on Python 3.11+ and a built-in subset parser before that.
- `check --scope strings`: checks Python string literals instead of lines.
- Exit code `2` for usage and configuration errors.
- MIT license, contribution guide (DCO), code of conduct, security policy and governance, in English and Korean.

### Output changes
- `md.emphasis` no longer treats `__x__` as bold. It used to suggest removing `__name__` in `logging.getLogger(__name__)`. Only `**x**` is handled.
- `check` on Python files (default `log-calls` scope) reads the string arguments of log calls from the syntax tree instead of whole lines. Results now match `fix`: a dash next to a placeholder such as `%s` and a status emoji at the start of a string are judged correctly. Other languages are still checked line by line.
- Removing an emoji also removes the spaces right after it, so `a\n⚠️ b` becomes `a\nb` instead of `a\n b`. Indentation and the space after a keycap (`1️⃣`) are kept.
- Linter suggestions match the cleaned output: rules are applied in the same order as `clean()`. For example, in `**저장 완료** ㅡ 다음` the suggestion for `ㅡ` is now `: ` instead of removal. Characters inside protected spans are no longer reported.
- A dash inside a sentence becomes `: ` instead of ` - ` in the `reader` profile (`완료 — 다음` becomes `완료: 다음`). Use `--profile dev` or `--dash-inline hyphen` for the previous result.
- `ㅡㅡ` is removed (it used to be kept).
- `!` right after Hangul becomes `.` by default (it used to require the `ko` preset).
- The `default`, `ko` and `strict` presets are replaced by profiles and levels.

## [0.1.0]

### Added
- Rule engine, Python `logging` formatter and filter, `check` and `clean` commands, pre-commit hook.
