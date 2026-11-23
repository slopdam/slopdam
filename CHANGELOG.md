# Changelog

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning follows the output stability policy in [GOVERNANCE.md](GOVERNANCE.md).

## [Unreleased]

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
