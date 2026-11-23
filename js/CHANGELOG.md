# Changelog

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Output follows slopdam's spec; see its [GOVERNANCE.md](https://github.com/slopdam/slopdam/blob/main/GOVERNANCE.md) for the output stability policy.

## [Unreleased]

### Added
- `@slopdam/core`: `clean()`, `Sanitizer` with `clean()` and `findings()`, profiles, levels, `disable` and `dashInline`, as in the Python package.
- Implements slopdam spec version 1, read from `../spec`. Every conformance case passes in the ESM and CommonJS builds. On 20,000 random inputs the output of `clean()` and `findings()` matched the Python package exactly.
- Python's regular expression dialect is translated when the package loads, including Unicode `\w`, `\s` and `\b`, and `^` and `$` that treat only `\n` as a line break.
