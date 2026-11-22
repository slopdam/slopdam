# SPDX-License-Identifier: MIT
"""Rule definitions and the sanitizer engine.

Detection is shared by every profile; only the action differs:

    reader  (default) plain Korean for end users
    dev               grep/parse friendly output for developers and log pipelines

An action is a replacement string, a callable ``(match, ctx) -> str``, or ``None``
(report only, used by the linter). A rule whose ``actions`` has no entry for a
profile is inactive in that profile. See docs/RULES.md for the rule list.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, Optional, Union

PROFILES = ("reader", "dev")
LEVELS = ("basic", "strong", "strict")
DASH_INLINE = {"comma": ", ", "colon": ": ", "hyphen": " - ", "space": " "}

Action = Union[str, Callable[["re.Match[str]", "Context"], str], None]


@dataclass(frozen=True)
class Context:
    profile: str
    dash_inline: str
    levelno: Optional[int] = None


@dataclass(frozen=True)
class Rule:
    id: str
    level: str
    pattern: "re.Pattern[str]"
    actions: Dict[str, Action]
    description: str
    ascii: bool = False  # can match pure-ASCII text (kept on the fast path)

    def active(self, profile: str, level: str) -> bool:
        return profile in self.actions and LEVELS.index(self.level) <= LEVELS.index(level)


@dataclass(frozen=True)
class Finding:
    rule_id: str
    description: str
    start: int
    end: int
    text: str
    fix: Optional[str] = field(default=None)


def _both(action: Action) -> Dict[str, Action]:
    return {"reader": action, "dev": action}


# Protected spans are swapped for one private-use character each and restored at the end.
_PUA = 0xF0000
_PUA_RE = re.compile("[\U000F0000-\U000FFFFD]")
_PROTECT = re.compile(
    r"(?P<url>https?://[^\s<>\"'`]+)"
    r"|`(?P<code>[^`\n]+)`"
    r"|(?<=\w=)(?P<kv>\"[^\"\n]*\"|'[^'\n]*'|[^\s,;)]+)"
    r"|(?<![\w/])(?P<path>(?:~|\.{1,2})?/[^\s\"'`,;)]+)"
)

# --- dash family -------------------------------------------------------------
HYPHENS = "‐‑−﹣－"
DASHES = "‒–—―⸺⸻﹘︱︲⹀"
EU = "ㅡￚᅳ"  # ㅡ, halfwidth ㅡ, conjoining jungseong ㅡ (NFKC target of ㅡ)
LINES = "─━┄-┋╌-╏═⎯⏤➖"
_CHOSEONG = re.compile("[ᄀ-ᅟꥠ-ꥼ]")
_OPENERS, _CLOSERS = "([{", ")]}%"


def _wordish(c: str, extra: str) -> bool:
    return c.isalnum() or c in extra or bool(_PUA_RE.match(c))


def _dash_run(m: "re.Match[str]", ctx: Context) -> str:
    s, (start, end) = m.string, m.span()
    lead, run = m.group(1), m.group(2)
    if run[0] == "ᅳ" and start + len(lead) > 0 and _CHOSEONG.match(s[start + len(lead) - 1]):
        return m.group(0)  # part of a composed old-style syllable
    prev = s[start - 1] if start else "\n"
    nxt = s[end] if end < len(s) else "\n"
    inner = _wordish(prev, _CLOSERS) and _wordish(nxt, _OPENERS)
    if len(run) >= 2:  # separator or emoticon: ㅡㅡ, ──, ——
        return " " if inner else ""
    if prev.isdigit() and nxt.isdigit():
        return "~" if ctx.profile == "reader" else "-"
    head = s[s.rfind("\n", 0, start) + 1 : start]
    if not head.strip() and m.group(3):  # list marker at line start
        return lead + "- "
    if inner:
        return ctx.dash_inline if ctx.profile == "reader" else " - "
    return ""


# --- emoji (section 5) ----------------------------------------------------------
_EMOJI_CLASS = (
    "\U0001F000-\U0001FAFF☀-➿⬀-⯿⌀-⏿■-◿"
    "‼⁉ℹ〰〽㊗㊙Ⓜ"
    "\U0001F1E6-\U0001F1FF\U000E0020-\U000E007F️⃣‍"
)
_STATUS = {
    "[OK]": "✅✔☑\U0001F7E2\U0001F197",
    "[FAIL]": "❌✖\U0001F534⛔\U0001F6AB❎",
    "[WARN]": "⚠\U0001F7E1\U0001F6A8",
}
_STATUS_OF = {c: tag for tag, chars in _STATUS.items() for c in chars}
_REDUNDANT = {"[FAIL]": logging.ERROR, "[WARN]": logging.WARNING}


def _status_tag(m: "re.Match[str]", ctx: Context) -> str:
    tag = _STATUS_OF[m.group(1)]
    if ctx.levelno is not None and ctx.levelno >= _REDUNDANT.get(tag, logging.CRITICAL + 1):
        return ""  # the log level already says it
    return tag + " "


_FULLWIDTH = str.maketrans("，：；（）！？［］｛｝", ",:;()!?[]{}")


def _r(id: str, level: str, pattern: str, actions: Dict[str, Action], description: str,
       flags: int = 0, ascii: bool = False) -> Rule:
    return Rule(id, level, re.compile(pattern, flags), actions, description, ascii)


# Order matters: later rules assume earlier ones already ran.
RULES: tuple = (
    _r("space.invisible", "basic", "[​‌⁠﻿­]", _both(""), "zero-width or invisible character"),
    _r("space.nbsp", "basic", "[  　]", _both(" "), "non-breaking or ideographic space"),
    _r("width.fullwidth", "basic", "[，：；（）！？［］｛｝]", _both(lambda m, c: m.group(0).translate(_FULLWIDTH)), "full-width punctuation"),
    _r("quote.double", "basic", "[“”„]", _both('"'), "curly double quote"),
    _r("quote.single", "basic", "[‘’‚]", _both("'"), "curly single quote"),
    _r("punct.ellipsis", "basic", "[…⋯]", _both("..."), "ellipsis character"),
    _r("punct.arrow", "basic", "[↔⇔]️?", _both("<->"), "arrow symbol"),
    _r("punct.arrow", "basic", "[→⇒➜➡➔⟶]️?", _both("->"), "arrow symbol"),
    _r("punct.arrow", "basic", "[←⇐⬅⟵]️?", _both("<-"), "arrow symbol"),
    _r("punct.bullet", "basic", "^([ \t]*)[•◦▪●▶►][ \t]*", _both(r"\1- "), "bullet symbol", re.M),
    _r("emoji.status", "basic", "\\A[ \t]*([" + "".join(_STATUS_OF) + "])️?[ \t]*", {"dev": _status_tag}, "status emoji"),
    # An emoji takes its trailing spaces with it, so "⚠️ text" on any line leaves no stray indent.
    # Bare combining marks (keycap "1️⃣ ") keep the space, or "1 단계" would become "1단계".
    _r("emoji.pictograph", "basic",
       "[" + _EMOJI_CLASS.replace("️⃣‍", "") + "][" + _EMOJI_CLASS + "]*[ \t]*|[️⃣‍]+",
       _both(""), "emoji or pictograph"),
    _r("md.heading", "basic", r"^[ \t]*#{1,6}[ \t]+", _both(""), "markdown heading marker", re.M, ascii=True),
    _r("md.fence", "basic", r"^[ \t]*```[^\n]*\n?", _both(""), "markdown code fence", re.M, ascii=True),
    _r("md.hr", "basic", r"^[ \t]*([-*_])[ \t]*(?:\1[ \t]*){2,}$", _both(""), "markdown horizontal rule", re.M, ascii=True),
    # Only **bold**: __x__ is far more often a Python name (__name__, __init__) than emphasis.
    _r("md.emphasis", "basic", r"\*\*(.+?)\*\*", _both(lambda m, c: m.group(1)), "markdown bold", ascii=True),
    _r("dash.hyphen", "basic", f"[{HYPHENS}]", _both("-"), "Unicode hyphen or minus"),
    _r("dash.wave", "basic", "[〜～]", _both("~"), "wave dash or full-width tilde"),
    _r("dash.run", "basic", f"([ \t]*)([{DASHES}{EU}{LINES}]+)([ \t]*)", _both(_dash_run), "dash, 'ㅡ' or line character"),
    _r("dash.cjk-run", "basic", "[一ーｰ]{3,}", _both(""), "CJK look-alike separator"),
    _r("dash.ascii-run", "basic", r"([=\-*#~_+])\1{4,}", _both(""), "ASCII separator", ascii=True),
    _r("tone.exclaim", "basic", "(?<=[가-힣])!+", {"reader": "."}, "exclamation after Korean text"),
    _r("tone.filler", "strong", r"(?:성공적으로|완벽하게|무사히|드디어)[ \t]*", {"reader": "", "dev": None}, "filler phrase"),
    _r("tone.chatty", "basic", r"\b(?:Let's|Here's|Voila|Awesome)\b|해볼게요|해보겠습니다|살펴보겠습니다", _both(None), "chatty phrase", ascii=True),
    _r("symbol.non-ascii", "strict", "[^\\w\\s\x00-\x7f\U000F0000-\U000FFFFD]", _both(None), "non-ASCII symbol"),
)

_MULTI_SPACE = re.compile(r"(?<=\S)[ \t]{2,}")


class Sanitizer:
    def __init__(self, profile: str = "reader", level: str = "basic", disable: Iterable[str] = (),
                 dash_inline: str = "colon", extra: Iterable[Rule] = ()):
        if profile not in PROFILES:
            raise ValueError(f"unknown profile {profile!r}, expected one of {PROFILES}")
        if level not in LEVELS:
            raise ValueError(f"unknown level {level!r}, expected one of {LEVELS}")
        if dash_inline not in DASH_INLINE:
            raise ValueError(f"unknown dash_inline {dash_inline!r}, expected one of {tuple(DASH_INLINE)}")
        off = tuple(disable)
        self.profile = profile
        self.dash_inline = DASH_INLINE[dash_inline]
        self.rules = tuple(
            r for r in (*RULES, *extra)
            if r.active(profile, level) and not any(r.id == d or r.id.startswith(d + ".") for d in off)
        )
        self._ascii_rules = tuple(r for r in self.rules if r.ascii)

    def _context(self, levelno: Optional[int]) -> Context:
        return Context(self.profile, self.dash_inline, levelno)

    def _apply(self, text: str, ctx: Context) -> str:
        for rule in self._ascii_rules if text.isascii() else self.rules:
            action = rule.actions[self.profile]
            if action is None:
                continue
            if callable(action):
                text = rule.pattern.sub(lambda m, a=action: a(m, ctx), text)
            else:
                text = rule.pattern.sub(action, text)
        return text

    def clean(self, text: str, levelno: Optional[int] = None) -> str:
        ctx = self._context(levelno)
        saved: list = []

        def protect(m: "re.Match[str]") -> str:
            kept = m.group(0)
            # reader drops the backticks, but only when the code itself is clean;
            # otherwise its content would be exposed to the rules on the next pass.
            if m.lastgroup == "code" and self.profile == "reader" and self._apply(m.group("code"), ctx) == m.group("code"):
                kept = m.group("code")
            saved.append(kept)
            return chr(_PUA + len(saved) - 1)

        text = self._apply(_PROTECT.sub(protect, text), ctx)
        text = _PUA_RE.sub(lambda m: saved[ord(m.group(0)) - _PUA], text)

        lines = []
        for i, line in enumerate(text.splitlines()):
            line = _MULTI_SPACE.sub(" ", line)
            line = line.strip() if i == 0 else line.rstrip()
            if line:
                lines.append(line)
        return "\n".join(lines)

    def findings(self, text: str) -> list:
        """What clean() would change, with spans in the original text.

        Rules run in the same order and on the same intermediate text as clean(), so a
        fix reflects earlier rules (e.g. a dash next to ``**bold**`` is judged after the
        markdown is gone). Each character of the working text remembers the span of the
        original text it came from.
        """
        ctx = self._context(None)
        cur, spans = [], []  # working text and, per character, its (start, end) in `text`
        last = 0
        for m in _PROTECT.finditer(text):
            for i in range(last, m.start()):
                cur.append(text[i])
                spans.append((i, i + 1))
            cur.append(chr(_PUA))  # protected spans are opaque to every rule
            spans.append(m.span())
            last = m.end()
        for i in range(last, len(text)):
            cur.append(text[i])
            spans.append((i, i + 1))
        work = "".join(cur)

        found = []
        for rule in self._ascii_rules if work.isascii() else self.rules:
            action = rule.actions[self.profile]
            pieces, new_spans, pos = [], [], 0
            for m in rule.pattern.finditer(work):
                if action is None:
                    fix = None
                elif callable(action):
                    fix = action(m, ctx)
                else:
                    fix = m.expand(action)
                if m.end() > m.start():
                    start, end = spans[m.start()][0], spans[m.end() - 1][1]
                    if m.group(0).strip() and fix != m.group(0):
                        found.append(Finding(rule.id, rule.description, start, end, text[start:end].strip(), fix))
                if fix is None or fix == m.group(0):
                    continue
                pieces.append(work[pos:m.start()])
                new_spans.extend(spans[pos:m.start()])
                pieces.append(fix)
                new_spans.extend([(start, end)] * len(fix))
                pos = m.end()
            if pieces:
                pieces.append(work[pos:])
                new_spans.extend(spans[pos:])
                work, spans = "".join(pieces), new_spans
        found.sort(key=lambda f: (f.start, -f.end))
        kept: list = []
        for f in found:  # drop hits nested inside an earlier one (e.g. emoji.status + emoji.pictograph)
            if not any(k.start <= f.start and f.end <= k.end for k in kept):
                kept.append(f)
        return kept
