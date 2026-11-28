# SPDX-License-Identifier: MIT
"""Rewrite string literals in Python source, keeping everything else byte for byte.

The AST picks which literals to touch (log/print call arguments, or every non-docstring
string); the tokenizer gives their exact text. Only literal text changes: quotes, prefixes,
escape sequences and f-string ``{...}`` parts are kept, and the result must compile.
"""
from __future__ import annotations

import ast
import io
import re
import tokenize
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

from .rules import _MAX_PASSES, Finding, Sanitizer

LOG_METHODS = {"debug", "info", "warning", "warn", "error", "exception", "critical", "fatal", "log"}
IGNORE = re.compile(r"slopdam:\s*ignore(?:\[([\w.,\s-]+)\])?")
FSTRING_START = getattr(tokenize, "FSTRING_START", None)  # Python 3.12+ splits f-strings into tokens
FSTRING_END = getattr(tokenize, "FSTRING_END", None)
_PREFIX = re.compile(r"^([A-Za-z]*)('''|\"\"\"|'|\")", re.S)

Pos = Tuple[int, int]  # (line, column in characters), as tokenize reports it


@dataclass(frozen=True)
class Edit:
    line: int
    col: int
    rule_id: str
    before: str
    after: Optional[str]  # None: report-only rule, nothing was changed


def _is_log_call(node: ast.Call) -> bool:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id == "print"
    if isinstance(func, ast.Attribute) and func.attr in LOG_METHODS:
        receiver = ast.unparse(func.value) if hasattr(ast, "unparse") else _dotted(func.value)
        return "log" in receiver.lower()
    return False


def _dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _dotted(node.value) + "." + node.attr
    return ""


def _docstring_nodes(tree: ast.AST) -> set:
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                out.add(id(first.value))
    return out


def _string_nodes(tree: ast.AST, scope: str) -> Iterable[ast.AST]:
    def is_str(n):
        return isinstance(n, ast.JoinedStr) or (isinstance(n, ast.Constant) and isinstance(n.value, str))

    def message_parts(node):
        # The strings that end up in the message: the argument itself, both sides of + and the left of %,
        # both branches of `a if c else b`, the string before .format(), and the arguments of a plain
        # function such as tr(...), _(...) or gettext(...). Not method calls (", ".join), subscripts or
        # anything else that only uses a string as data.
        if is_str(node):
            yield node
        elif isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
            yield from message_parts(node.left)
            if isinstance(node.op, ast.Add):
                yield from message_parts(node.right)
        elif isinstance(node, ast.IfExp):
            yield from message_parts(node.body)
            yield from message_parts(node.orelse)
        elif isinstance(node, ast.Call) and not _is_log_call(node):
            if isinstance(node.func, ast.Name):
                for arg in node.args:
                    yield from message_parts(arg)
            elif isinstance(node.func, ast.Attribute) and node.func.attr == "format":
                yield from message_parts(node.func.value)

    if scope == "log-calls":
        seen = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _is_log_call(node):
                for arg in [*node.args, *(k.value for k in node.keywords if k.arg is None)]:
                    for part in message_parts(arg):
                        if id(part) not in seen:
                            seen.add(id(part))
                            yield part
        return
    docs = _docstring_nodes(tree)
    for node in ast.walk(tree):
        if is_str(node) and id(node) not in docs:
            yield node


def _char_col(lines: List[str], line: int, byte_col: int) -> int:
    """AST columns are UTF-8 byte offsets; tokenize columns are characters."""
    return len(lines[line - 1].encode("utf-8")[:byte_col].decode("utf-8", errors="ignore"))


def _spans(source: str, scope: str) -> List[Tuple[Pos, Pos]]:
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True) or [""]
    out = []
    for node in _string_nodes(tree, scope):
        if getattr(node, "end_lineno", None) is None:
            continue
        start = (node.lineno, _char_col(lines, node.lineno, node.col_offset))
        end = (node.end_lineno, _char_col(lines, node.end_lineno, node.end_col_offset))
        out.append((start, end))
    return out


def _string_tokens(source: str) -> Iterable[Tuple[Pos, Pos]]:
    """(start, end) of every string literal token; a 3.12+ f-string counts as one."""
    depth, fstart = 0, None
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if FSTRING_START is not None and tok.type == FSTRING_START:
            if depth == 0:
                fstart = tok.start
            depth += 1
        elif FSTRING_END is not None and tok.type == FSTRING_END:
            depth -= 1
            if depth == 0:
                yield fstart, tok.end
        elif tok.type == tokenize.STRING and depth == 0:
            yield tok.start, tok.end


def _literal_parts(body: str, is_f: bool) -> List[Tuple[int, int]]:
    """Index ranges of `body` that are literal text (f-string expressions excluded)."""
    if not is_f:
        return [(0, len(body))]
    parts, i, start, n = [], 0, 0, len(body)
    while i < n:
        if body.startswith("{{", i) or body.startswith("}}", i):
            i += 2
            continue
        if body[i] == "{":
            parts.append((start, i))
            depth, i = 1, i + 1
            while i < n and depth:
                depth += {"{": 1, "}": -1}.get(body[i], 0)
                i += 1
            start = i
            continue
        i += 1
    parts.append((start, n))
    return [(a, b) for a, b in parts if b > a]


# Placeholders that stand for a value at run time: "%s", "%(name)d", "{}", "{0:>4}".
_PLACEHOLDER = re.compile(r"%(?:\([^)]*\))?[-#0 +]*\d*(?:\.\d+)?[sdifrxXeEgGcoaub%]|\{[^{}]*\}")
_MASK_BASE = 0xF8000  # private use plane, treated as a word character by the dash rule


def _mask(body: str, is_f: bool):
    """Swap f-string expressions and format placeholders for single word-like characters.

    The rules then judge a dash next to ``{n}`` or ``%s`` as sitting between words, and can
    never edit inside an expression. Returns (masked text, original pieces, index mapper).
    """
    spans = []
    if is_f:
        cursor = 0
        for a, b in _literal_parts(body, True):
            if a > cursor:
                spans.append((cursor, a))
            cursor = b
        if cursor < len(body):
            spans.append((cursor, len(body)))
    else:
        spans = [m.span() for m in _PLACEHOLDER.finditer(body) if m.group(0) != "%%"]
    out, pieces, index, last = [], [], [], 0
    for a, b in spans:
        out.append(body[last:a])
        index.extend(range(last, a))
        out.append(chr(_MASK_BASE + len(pieces)))
        index.append(a)
        pieces.append(body[a:b])
        last = b
    out.append(body[last:])
    index.extend(range(last, len(body) + 1))
    return "".join(out), pieces, lambda i: index[min(i, len(index) - 1)]


def _unmask(text: str, pieces: List[str]) -> Optional[str]:
    seen = [ord(c) - _MASK_BASE for c in text if _MASK_BASE <= ord(c) < _MASK_BASE + len(pieces)]
    if seen != list(range(len(pieces))):
        return None
    return re.sub("[%s-%s]" % (chr(_MASK_BASE), chr(_MASK_BASE + max(len(pieces), 1))),
                  lambda m: pieces[ord(m.group(0)) - _MASK_BASE], text)


def _rewrite(text: str, sanitizer: Sanitizer, ignored: List[str], quote: str, raw: bool) -> Tuple[str, List[Finding]]:
    """Apply each finding's fix at its span. Returns new text and the findings (report-only ones too)."""
    out, last, applied = [], 0, []
    for f in sanitizer.findings(text):
        if f.start < last or any(f.rule_id == i or f.rule_id.startswith(i + ".") for i in ignored):
            continue
        if f.fix is None:
            applied.append(f)
            continue
        fix = f.fix
        if quote[0] in fix or "\\" in fix:
            if raw:
                continue  # cannot escape inside a raw string
            fix = fix.replace("\\", "\\\\").replace(quote[0], "\\" + quote[0])
        out.append(text[last:f.start])
        out.append(fix)
        last = f.end
        applied.append(f)
    out.append(text[last:])
    return "".join(out), applied


def fix_source(source: str, sanitizer: Sanitizer, scope: str = "log-calls") -> Tuple[str, List[Edit]]:
    """Return the fixed source and the edits made. Raises SyntaxError if the input does not parse."""
    targets = _spans(source, scope)
    if not targets:
        return source, []
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    def absolute(pos: Pos) -> int:
        return offsets[pos[0] - 1] + pos[1]

    replacements, edits = [], []
    for start, end in _string_tokens(source):
        if not any(s <= start and end <= e for s, e in targets):
            continue
        line_text = lines[start[0] - 1]
        ignore = IGNORE.search(line_text)
        if ignore and not ignore.group(1):
            continue
        ignored = [i.strip() for i in ignore.group(1).split(",")] if ignore else []
        a, b = absolute(start), absolute(end)
        token = source[a:b]
        m = _PREFIX.match(token)
        if not m or "b" in m.group(1).lower():
            continue
        prefix, quote = m.group(1), m.group(2)
        body_start = len(prefix) + len(quote)
        body = token[body_start:len(token) - len(quote)]
        masked, pieces, where = _mask(body, "f" in prefix.lower())
        text, applied = _rewrite(masked, sanitizer, ignored, quote, "r" in prefix.lower())
        # Repeat until stable, as clean() does: removing one trace can expose another
        # (the dash in "‒•" leaves a bullet at the start of the string).
        for _ in range(_MAX_PASSES - 1):
            again, _ = _rewrite(text, sanitizer, ignored, quote, "r" in prefix.lower())
            if again == text:
                break
            text = again
        new_body = _unmask(text, pieces)
        if new_body is None:
            continue  # a rule swallowed a placeholder: leave this literal alone
        if body.strip() and not new_body.strip():
            continue  # nothing but a symbol ("✓ " if ok else "✗ "): the symbol is the message
        # Do not leave a space at either end that the original literal did not have.
        if body == body.lstrip():
            new_body = new_body.lstrip(" \t")
        if body == body.rstrip():
            new_body = new_body.rstrip(" \t")
        for f in applied:
            edits.append(Edit(start[0], start[1] + body_start + where(f.start) + 1, f.rule_id, f.text,
                              None if f.fix is None else f.fix))
        new_token = token[:body_start] + new_body + quote
        if new_token != token:
            replacements.append((a, b, new_token))

    for a, b, new in sorted(replacements, reverse=True):
        source = source[:a] + new + source[b:]
    compile(source, "<slopdam fix>", "exec")  # never hand back code that does not compile
    return source, edits


def fix_file(path: str, sanitizer: Sanitizer, scope: str = "log-calls", write: bool = True) -> Tuple[Optional[str], List[Edit]]:
    """Fix one Python file. Returns (new source or None when unchanged, edits)."""
    with open(path, encoding="utf-8") as f:
        source = f.read()
    new, edits = fix_source(source, sanitizer, scope)
    if new == source:
        return None, []
    if write:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)
    return new, edits
