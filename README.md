# slopdam

[English](https://github.com/slopdam/slopdam/blob/main/README.md) | [한국어](https://github.com/slopdam/slopdam/blob/main/README.ko.md)

[![ci](https://github.com/slopdam/slopdam/actions/workflows/ci.yml/badge.svg)](https://github.com/slopdam/slopdam/actions/workflows/ci.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/slopdam/slopdam/blob/main/LICENSE)

**A dam for AI slop in your logs.** slopdam removes the traces AI coding tools leave in log messages and console output: em dashes and look-alike lines (including the Korean `ㅡ`), decorative emoji, separator lines, markdown bold, curly quotes and invisible characters.

It works in two places:

- **When logs are written**: a `logging` formatter and filter clean every message on its way out, with no change to your code.
- **Before code is committed**: a linter reports traces in log calls, and a fixer rewrites the string literals in Python files.

The same trace becomes different text depending on who reads it:

```
input : ✅ **Saved** — 3 rows processed 🎉
reader: Saved: 3 rows processed
dev   : [OK] Saved - 3 rows processed
```

- `reader` (default): plain text for people, such as CLI messages, alerts and reports.
- `dev`: grep-friendly text for log files and collectors. Status emoji become `[OK]`, `[FAIL]` and `[WARN]` instead of disappearing.

slopdam uses deterministic rules (regular expressions and character tables). It does not try to guess whether a model wrote the text: the same input always gives the same output, and every change can be traced to a rule ID.

## Install

slopdam needs Python 3.9 or later and has no runtime dependencies.

```bash
pip install slopdam
```

## Clean log output

```python
import logging
from slopdam import PlainFilter, PlainFormatter

console = logging.StreamHandler()                    # read by people
console.setFormatter(PlainFormatter("%(message)s"))  # reader profile
console.addFilter(PlainFilter())                     # drop lines that were only separators

file = logging.FileHandler("app.log")                # read by tools
file.setFormatter(PlainFormatter("%(asctime)s %(levelname)s %(message)s", profile="dev"))
file.addFilter(PlainFilter(profile="dev"))

logging.basicConfig(level=logging.INFO, handlers=[console, file])
logging.info("✅ Synced %s rows — done", 3)
# console: Synced 3 rows: done
# app.log: 2026-11-23 ... INFO [OK] Synced 3 rows - done
```

- The original log record is never modified, so each handler can use its own profile.
- Tracebacks, URLs, inline code, `key=value` values and file paths are left untouched.

structlog and loguru work the same way. Neither library is required by slopdam.

```python
from slopdam.integrations.structlog import SlopdamProcessor
structlog.configure(processors=[structlog.processors.add_log_level,
                                SlopdamProcessor(profile="dev"),
                                structlog.processors.JSONRenderer()])

from slopdam.integrations.loguru import SlopdamPatcher
logger = logger.patch(SlopdamPatcher(profile="dev"))
```

The structlog processor cleans the event message only; pass `keys=["note"]` to clean other fields too.

## Lint and fix source code

```bash
slopdam check src/                # report traces in log and print calls; exit 1 if any
slopdam --profile dev check src/  # suggestions in the dev style
slopdam fix --diff src/           # preview fixes to Python string literals
slopdam fix src/                  # apply them
git diff | slopdam check -        # check text from stdin
cat app.py | slopdam check --stdin-filename app.py -   # stdin, checked like that file
```

```
src/sync.py:8:18: emoji.pictograph '✅' -> ''
src/sync.py:8:25: dash.run 'ㅡ' -> ': '
```

Python files are read through the syntax tree, so slopdam knows exactly where each string starts and ends. `slopdam fix` changes only the literal text: quotes, prefixes, escape sequences, f-string expressions and placeholders such as `%s` stay as they are, and nothing is written unless the result compiles. Other languages are checked line by line.

To skip a line, add `# slopdam: ignore`, or `# slopdam: ignore[emoji]` to skip one rule group.

## Configuration

slopdam reads `slopdam.toml`, or the `[tool.slopdam]` table in `pyproject.toml`. Command line options take precedence.

```toml
profile = "dev"
level = "basic"
disable = ["emoji.status"]

[lint]
scope = "log-calls"   # log-calls | strings | all
exclude = ["tests/**"]
```

## pre-commit and CI

```yaml
repos:
  - repo: https://github.com/slopdam/slopdam
    rev: v0.4.0
    hooks:
      - id: slopdam
```

GitHub Actions, with findings shown as annotations on the pull request:

```yaml
- uses: actions/checkout@v7
- uses: slopdam/slopdam@v0.4.0
  with:
    paths: src/
```

`slopdam check --format` also writes `json`, `github` (workflow annotations) and `sarif` (GitHub code scanning and other SARIF viewers).

Exit codes: `0` clean, `1` traces found (or `fix --diff` has changes), `2` usage or configuration error.

## Pipe

```bash
tail -f app.log | slopdam clean
```

## Other languages

slopdam is built to work the same way in every language.

- **Now:** `slopdam check` lints log and print calls in JavaScript, TypeScript, Java, Kotlin, Go, Rust, Ruby, PHP and Swift line by line, and the pre-commit hook and GitHub Action cover the same files. `slopdam clean` cleans the output of any program through a pipe: `node server.js 2>&1 | slopdam clean --profile dev`.
- **Native packages:** the behavior is defined independently of Python in [spec/](https://github.com/slopdam/slopdam/blob/main/spec/README.md): the rule catalog and conformance cases that every port must pass. Packages for JavaScript, Go, Java and Rust are planned in the [roadmap](https://github.com/slopdam/slopdam/blob/main/ROADMAP.md).

## Rules

Every rule has an ID such as `dash.run` or `emoji.pictograph`, and can be turned off by ID or by group (`--disable emoji`). Profiles decide what a trace becomes, and levels decide how far slopdam goes: `basic` (default), `strong` (also removes filler words) and `strict` (also reports any non-ASCII symbol). See [docs/RULES.md](https://github.com/slopdam/slopdam/blob/main/docs/RULES.md) for the full catalog.

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](https://github.com/slopdam/slopdam/blob/main/CONTRIBUTING.md); every commit needs a DCO sign-off (`git commit -s`). Report security issues privately as described in [SECURITY.md](https://github.com/slopdam/slopdam/blob/main/SECURITY.md). Project decisions follow [GOVERNANCE.md](https://github.com/slopdam/slopdam/blob/main/GOVERNANCE.md), and the community follows the [Code of Conduct](https://github.com/slopdam/slopdam/blob/main/CODE_OF_CONDUCT.md).

## License

[MIT](https://github.com/slopdam/slopdam/blob/main/LICENSE). Third-party components are listed in [THIRD_PARTY_NOTICES.md](https://github.com/slopdam/slopdam/blob/main/THIRD_PARTY_NOTICES.md).
