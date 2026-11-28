# Rule catalog

[English](RULES.md) | [한국어](RULES.ko.md)

Rules run in the order listed. `reader` is the default profile. "off" means the rule does not run in that profile; "report" means the linter reports it but nothing is changed.

| ID | Level | Matches | `reader` (default) | `dev` |
|---|---|---|---|---|
| `space.invisible` | basic | Zero-width space, ZWNJ, word joiner, BOM, soft hyphen | Removed | Removed |
| `space.nbsp` | basic | No-break space, narrow no-break space, ideographic space | Space | Space |
| `width.fullwidth` | basic | `，：；（）！？［］｛｝` on a line with no kana or CJK ideographs | Halfwidth | Halfwidth |
| `quote.double` / `quote.single` | basic | `“ ” „` / `‘ ’ ‚` | `"` / `'` (`\"` inside a double-quoted string, so JSON and logfmt stay valid) | Same as reader |
| `punct.ellipsis` | basic | `…` `⋯` | `...` | `...` |
| `punct.arrow` | basic | `→ ⇒ ➜ ➡ ⟶` / `← ⇐ ⬅` / `↔ ⇔` | `->` / `<-` / `<->` | Same |
| `punct.bullet` | basic | `• ◦ ▪ ● ▶ ►` at the start of a line | `- ` | `- ` |
| `emoji.status` | basic | ✅ ❌ ⚠️ and similar at the start of a message | off (`emoji.pictograph` removes it) | `[OK]` `[FAIL]` `[WARN]`, omitted when the log level already says it |
| `emoji.pictograph` | basic | Emoji and pictographs, ZWJ sequences, variation selectors, keycaps, flags | Removed | Removed |
| `md.heading` | basic | `#` to `######` and a space at the start of a line | Removed | Removed |
| `md.fence` | basic | A line with a code fence | Line removed | Line removed |
| `md.hr` | basic | A line made only of `---`, `***` or `___` | Line removed | Line removed |
| `md.emphasis` | basic | `**x**` (`__x__` is not matched because it collides with Python names such as `__name__`) | `x` | `x` |
| (protected) | | `` `x` `` | Backticks dropped when the code inside is clean | Kept |
| `dash.hyphen` | basic | `‐ ‑ − ﹣ －` | `-` | `-` |
| `dash.wave` | basic | `〜 ～` | `~` | `~` |
| `dash.run` | basic | **`ㅡ` `ￚ` `ᅳ`**, `‒ – — ― ⸺ ⸻ ﹘ ︱ ︲ ⹀`, `─ ━ ┄`-`┋` `╌`-`╏` `═ ⎯ ⏤ ➖` | See the table below | See the table below |
| `dash.cjk-run` | basic | Three or more `一 ー ｰ` in a row | Removed | Removed |
| `dash.ascii-run` | basic | Five or more of the same `= - * # ~ _ +`, not touching `+` or `\|` (a table border such as `+-----+` stays) | Removed | Removed |
| `tone.exclaim` | basic | `!` right after Hangul | `.` | off |
| `tone.filler` | strong | Korean filler words such as `성공적으로` | Removed | report |
| `tone.chatty` | strong | A known opener at the start of a line, before more text: `Great news!`, `Heads up:`, `살펴보겠습니다.`, `さて、`, `好消息！` (about 80 in four languages) | Removed, next word capitalized | Removed, next word capitalized |
| `tone.chatty` | basic | Chatty phrases such as `Let's` and `Here's` | report | report |
| `symbol.non-ascii` | strict | Any symbol that is not a letter, digit, space or ASCII | report | report |

## How `dash.run` decides

A run of dash-like characters is judged by what is next to it.

| Context | Example | `reader` | `dev` |
|---|---|---|---|
| Two or more in a row | `ㅡㅡ`, `──`, `——` | Removed | Removed |
| Between digits | `3ㅡ5`, `2024–2025` | `~` | `-` |
| Start of a line, followed by a space | `ㅡ item` | `- ` | `- ` |
| Between words, with or without spaces | `done ㅡ next`, `done—next` | `: ` (change with `--dash-inline`) | ` - ` |
| Anything else (end of line, next to punctuation) | `done ㅡ`, `done ㅡ, next` | Removed | Removed |

A conjoining `ᅳ` (U+1173) right after a leading consonant is part of a syllable and is left alone. In Python string literals, placeholders such as `%s`, `{0}` and f-string expressions count as words.

## Protected spans

No rule touches URLs, inline code in backticks, the value in `key=value`, or paths that start with `/`, `./`, `../` or `~/`. The exception is the message of a logfmt line: the value of a key ending in `msg`, `message` or `error` (`msg="✅ Saved — done"`) is cleaned like any text.

A dash run that touches a table edge (`+ |` or a box-drawing corner or junction such as `┌ ┬ ┼ ║`) is part of a table and is kept, so `┌─────┬─────┐` and `|------|------|` stay.

## After the rules

In a line a rule changed, repeated spaces collapse to one and no space is left before a closing quote (`{"msg":"Saved 🎉"}` becomes `{"msg":"Saved"}`). A line no rule changed keeps its spacing, so aligned columns (`kubectl get pods`, tables) stay as they are. Then leading and trailing spaces and empty lines are removed. If the result is empty, `PlainFilter` drops the log record.

## Checklist for a new rule

1. Inputs that must be caught.
2. Inputs that must not be caught (dates such as `2026-11-21`, `--dry-run`, `一般`, `ㅋㅋ`).
3. Expected output for `reader` and `dev`.
4. The level, and why.
5. An idempotency case.
