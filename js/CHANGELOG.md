# Changelog

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Output follows slopdam's spec; see its [GOVERNANCE.md](https://github.com/slopdam/slopdam/blob/main/GOVERNANCE.md) for the output stability policy.

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
