---
name: clean-log-messages
description: Write log, print and console messages without AI-style traces (em dashes, the Hangul ㅡ, emoji, markdown bold, curly quotes, separator lines, chatty openers such as "Great news!" or "살펴보겠습니다."), and check or fix them with slopdam. Use when writing or reviewing logging code, when the slopdam hook reports findings, or when the user asks to clean log output.
---

# Clean log messages

Log messages are read in terminals, log files and dashboards, and parsed by tools. Write them in plain text.

## When writing a log message

- No em or en dashes (`—`, `–`) or the Hangul `ㅡ` used as a dash. Use `: ` or `, `, or `~` for a range (`2024~2025`).
- No emoji, status icons (`✅`, `❌`) or decorative symbols. The log level already says success or failure.
- No markdown: no `**bold**`, `#` headings, bullet symbols (`•`) or separator lines (`=====`, `─────`).
- Straight quotes only (`"`, `'`), and `...` rather than `…`.
- No chatty openers or filler: drop `Great news!`, `Heads up:`, `Here's the summary:`, `살펴보겠습니다.`, `성공적으로`. Start with what happened: `Saved 3 rows`, `3건 저장`.
- Keep identifiers, URLs, paths, `key=value` pairs and code exactly as they are.
- In Chinese and Japanese, full-width punctuation (`，：。`) is correct; keep it.

## Checking and fixing

When the slopdam hook lists findings after an edit, rewrite those messages and keep their meaning. If a character is intended (a test fixture, a string that is not a message), leave it and say why, or add `# slopdam: ignore` (or `// slopdam: ignore`) on that line.

```bash
slopdam check src/              # log calls in source files; exit 1 on findings
slopdam check --all notes.txt   # every line, not only log calls
slopdam fix src/ --diff         # preview rewrites of Python string literals
slopdam fix src/                # apply them
slopdam clean < app.log         # clean text on stdin
```

The project's settings live in `slopdam.toml` or `[tool.slopdam]` in `pyproject.toml` (`profile`, `level`, `disable`, `exclude`). `profile = "dev"` writes `[OK]` and ` - ` instead of removing them; `level = "strong"` also removes Korean filler words and about 80 known openers.

If slopdam is not installed, ask the user before installing it: `pip install slopdam` (Python 3.9 or later, no dependencies).
