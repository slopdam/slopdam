# Changelog

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Output follows slopdam's spec; see its [GOVERNANCE.md](https://github.com/slopdam/slopdam/blob/main/GOVERNANCE.md) for the output stability policy.

## [0.6.0] - 2026-11-28

### Output changes
- From the spec (#65): a dash between a digit and a short identifier with a number is a range (`H1–H5` becomes `H1~H5`, `dev`: `H1-H5`); a single dash used as an empty cell (`{name:<15} –`, `| – |`) becomes an ASCII `-` instead of disappearing.

## [0.5.0] - 2026-11-28

### Output changes
- From the spec (#36): at the `strong` level, `tone.chatty` removes about 80 known openers at the start of a line when more text follows (`Great news!`, `Heads up:`, `살펴보겠습니다.`, `さて、`), and capitalizes the next word when it is a plain lowercase word with a vowel. `basic` output does not change.

## [0.4.0] - 2026-11-28

### Output changes
- From the spec (#49): a line with kana or CJK ideographs keeps its full-width punctuation (`处理完成，共 42 条记录。` stays as written); Korean and English lines still get ASCII.

## [0.3.0] - 2026-11-28

### Output changes
- From the spec (#40, #43): lines no rule changed keep their spacing, so aligned columns and tables are no longer squeezed; dash runs touching a table edge (`+------+`, `┌─────┐`) stay; the message of a logfmt line (`msg=`, `message=`, `error=`) is cleaned; a curly quote inside a double-quoted string becomes `\"`, so JSON lines stay valid; no space is left before a closing quote.

## [0.2.1] - 2026-11-25

### Fixed
- `slopdam/no-slop` applies its fix until the string stops changing, so one `eslint --fix` pass is enough when removing a trace exposes another (`"‒• 항목"` becomes `"- 항목"`).
- Messages show the source text; they used to show an internal placeholder where a `%s` or `${...}` was inside the reported span.

## [0.2.0] - 2026-11-24

### Added
- `@slopdam/core/eslint`: an ESLint flat-config plugin with the rule `slopdam/no-slop` and `recommended` and `dev` configs. It checks string arguments of `console.*` and logger calls (template literals and `+` concatenations included) and fixes them like `slopdam fix` does for Python: only the literal's text changes, and quotes, escapes, `${...}` and `%s` stay. On 135,536 generated log calls every fixed file parsed and a second run changed nothing.

### Output changes
- From the spec: a dash next to a quote keeps the words apart (`A — "B"` becomes `A: "B"`).

## [0.1.0] - 2026-11-24

### Added
- `@slopdam/core/pino`: `slopdamPino()` returns pino options whose `hooks.logMethod` cleans each message. pino levels map to slopdam's, so `dev` drops a status tag the level already says.
- `@slopdam/core/winston`: `slopdamWinston()` is a winston format that cleans `info.message`; each transport can use its own profile.
- Neither integration imports its library; pino and winston are dev dependencies for the tests only.
- `@slopdam/core`: `clean()`, `Sanitizer` with `clean()` and `findings()`, profiles, levels, `disable` and `dashInline`, as in the Python package.
- Implements slopdam spec version 1, read from `../spec`. Every conformance case passes in the ESM and CommonJS builds. On 20,000 random inputs the output of `clean()` and `findings()` matched the Python package exactly.
- Python's regular expression dialect is translated when the package loads, including Unicode `\w`, `\s` and `\b`, and `^` and `$` that treat only `\n` as a line break.
