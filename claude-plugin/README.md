# slopdam for Claude Code

[English](README.md) | [한국어](README.ko.md)

A Claude Code plugin that keeps AI-style traces out of the log messages Claude writes: em dashes and the Hangul `ㅡ`, emoji, markdown bold, curly quotes, separator lines and chatty openers.

- **Hook.** After every `Write` or `Edit` of a source file, it runs `slopdam check` on that file and passes the findings to Claude (line, rule, suggested fix) next to the tool result. Nothing is blocked and the file is not changed; Claude rewrites the messages itself. Files without findings, and files that are not source code, produce no output.
- **Skill** `clean-log-messages`. How to write plain log messages, and how to run `slopdam check`, `fix` and `clean`.

## Install

In Claude Code:

```
/plugin marketplace add slopdam/slopdam
/plugin install slopdam@slopdam
```

The hook needs slopdam itself (Python 3.9 or later, no dependencies) and `python3` to run:

```bash
pip install slopdam
```

It uses, in order: the command in `SLOPDAM_CMD`, `slopdam` on `PATH`, the slopdam package of the `python3` that runs the hook, then `uvx --from slopdam slopdam`. If none is found, Claude is told once per project.

## Settings

The project's own slopdam settings apply, as on the command line: `slopdam.toml` or `[tool.slopdam]` in `pyproject.toml`. For example, `level = "strong"` also reports the known chatty openers (`Great news!`, `Heads up:`), and `disable = ["emoji"]` turns a rule group off. A line with `# slopdam: ignore` (or `// slopdam: ignore`) is skipped.

## Files

| Path | What it is |
|---|---|
| `.claude-plugin/plugin.json` | Manifest |
| `hooks/hooks.json`, `hooks/check.py` | The `PostToolUse` hook (standard library only) |
| `skills/clean-log-messages/SKILL.md` | The skill |

The marketplace that lists it is `.claude-plugin/marketplace.json` at the root of this repository.
