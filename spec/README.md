# slopdam specification

[English](README.md) | [한국어](README.ko.md)

This folder defines slopdam's behavior independently of any programming language. The Python package is the reference implementation. A port to another language (JavaScript, Go, Java, Rust and others) is correct when it passes every case in `conformance.json`.

| File | Contents | Edited by |
|---|---|---|
| `rules.json` | Profiles, levels, character sets, protected spans and the ordered rule list | Generated from the Python source |
| `conformance.json` | Inputs with the exact `reader` and `dev` output for each | Inputs by hand, outputs generated |

Both files are regenerated with `python scripts/gen_spec.py`. CI runs it with `--check`, so the spec can never drift from the reference implementation.

## Algorithm

`clean(text, options)` first turns every line break (`\r\n`, `\r`, `\u2028` and the others Python's `str.splitlines` knows) into `\n`. Then it runs one pass of these steps:

1. Protect spans. Every match of `protected_spans` (URL, inline code, the value of `key=value`, path) is replaced by a placeholder that no rule matches.
2. Apply the rules in the order of `rules.json`. A rule is active when the profile has an action for it, its level is at or below the chosen level, and it is not disabled. Each rule replaces all of its matches in the text produced by the previous rule.
3. Collapse every run of two or more spaces or tabs after a non-space character into one space (`tidy.multi_space`). Protected spans are still masked, so the spaces inside them stay.
4. Restore the protected spans. In `reader`, inline code loses its backticks when the code itself would not change.
5. Tidy the lines: strip both ends of the first non-empty line and the right end of the others, drop empty lines, and join them with `\n`.

Removing one trace can expose another (`‒•` leaves a bullet at the start of the line), so when a pass changes the text, run another pass on its result, until a pass changes nothing (at most `tidy.max_passes` passes). The result is therefore idempotent: `clean(clean(x)) == clean(x)`.

A character from the private-use range U+F0000 to U+FFFFD that is already in the input is treated as a protected span, so implementations may use that range for their placeholders.

## Actions

| `kind` | Meaning |
|---|---|
| `replace` | Replace the match with `value`. `\1` refers to the first capture group. |
| `report` | Leave the text alone; linters report the match without a fix. |
| `function` | Context-dependent replacement, described below. |

| Function | Behavior |
|---|---|
| `fullwidth` | Map full-width punctuation to its ASCII form. |
| `unwrap` | Replace the match with its first capture group. |
| `status_tag` | `dev` only. Replace a leading status emoji with `[OK] `, `[FAIL] ` or `[WARN] `. Return nothing when the log level is at or above `status_redundant_at` for that tag. |
| `dash_run` | Decide what a run of dashes means from its neighbors, in this order: part of an old Hangul syllable, that is the run starts with `ᅳ` right after a character from `charsets.hangul_choseong` (keep); two or more characters (separator: a space between words, otherwise nothing); between digits (range: `~` in `reader`, `-` in `dev`); at the start of a line and followed by space (list marker `- `); between words (`dash_inline` in `reader`, ` - ` in `dev`); otherwise nothing. "Between words" means the character before the run (spaces around it included) is a letter, a digit, a protected span or one of `dash_word_before`, and the character after it is a letter, a digit, a protected span or one of `dash_word_after`. |

## Regular expressions

Patterns use Python `re` syntax. Notes for other engines:

- `\w`, `\d` and `\s` are Unicode-aware. In JavaScript use the `u` flag and Unicode property classes.
- `\A` means the start of the whole string, not the start of a line.
- `flags: ["multiline"]` makes `^` and `$` match at line boundaries.
- Lookbehinds are fixed width.

## Versioning

`spec_version` changes only when the meaning of the files changes, not when rules or cases are added. Each port states which `spec_version` it implements and runs `conformance.json` in its own CI. A change to an expected output is an output change and follows the policy in [GOVERNANCE.md](../GOVERNANCE.md).
