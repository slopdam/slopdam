// SPDX-License-Identifier: MIT
/**
 * Translate the Python `re` patterns in the spec into JavaScript regular expressions
 * with the `u` flag, keeping Python's meaning:
 *
 *   \w \s \d \b   Unicode-aware, as in Python 3 (JavaScript's are ASCII-only)
 *   \A \Z         start and end of the whole string
 *   \UXXXXXXXX    \u{X}
 *   .             any character except \n (JavaScript also stops at \r, \u2028, \u2029)
 *   ^ $           Python's anchors; with the multiline flag only \n separates lines (in
 *                 JavaScript's m mode \r, \u2028 and \u2029 do too), so no JS flag is used
 *   (?P<name>     (?<name>
 *
 * Python's character classes, measured on its Unicode database: \w is letters, numbers and
 * "_" (categories L*, N*); \s is the set below; str.isdigit() is Nd plus PY_DIGIT_EXTRA.
 */

export const PY_WORD = "\\p{L}\\p{N}_";
export const PY_SPACE = "\\t-\\r\\x1c-\\x20\\x85\\xa0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000";
const PY_DIGIT_EXTRA =
  "\\u{B2}-\\u{B3}\\u{B9}\\u{1369}-\\u{1371}\\u{19DA}\\u{2070}\\u{2074}-\\u{2079}\\u{2080}-\\u{2089}" +
  "\\u{2460}-\\u{2468}\\u{2474}-\\u{247C}\\u{2488}-\\u{2490}\\u{24EA}\\u{24F5}-\\u{24FD}\\u{24FF}" +
  "\\u{2776}-\\u{277E}\\u{2780}-\\u{2788}\\u{278A}-\\u{2792}\\u{10A40}-\\u{10A43}\\u{10E60}-\\u{10E68}" +
  "\\u{11052}-\\u{1105A}\\u{1F100}-\\u{1F10A}";

export const isAlnum = (c: string): boolean => /^[\p{L}\p{N}]$/u.test(c);
const DIGIT_RE = new RegExp(`^[\\p{Nd}${PY_DIGIT_EXTRA}]$`, "u");
export const isDigit = (c: string): boolean => DIGIT_RE.test(c);
const SPACE_RE = new RegExp(`[${PY_SPACE}]`, "u");
export const isSpace = (c: string): boolean => SPACE_RE.test(c);

/** Python's str.strip() / str.rstrip() with no argument. */
export function pyStrip(s: string): string {
  return s.replace(new RegExp(`^[${PY_SPACE}]+|[${PY_SPACE}]+$`, "gu"), "");
}
export function pyRstrip(s: string): string {
  return s.replace(new RegExp(`[${PY_SPACE}]+$`, "u"), "");
}

const LINE_BREAK = /\r\n|[\n\r\v\f\x1c-\x1e\x85\u2028\u2029]/;

/** Python's str.splitlines(). */
export function splitlines(s: string): string[] {
  if (s === "") return [];
  const parts = s.split(LINE_BREAK);
  if (parts[parts.length - 1] === "") parts.pop();
  return parts;
}

// Characters JavaScript allows after a backslash in u-mode without a special meaning.
const SYNTAX = "^$\\.*+?()[]{}|/";
const WORD_BOUNDARY = `(?:(?<=[${PY_WORD}])(?![${PY_WORD}])|(?<![${PY_WORD}])(?=[${PY_WORD}]))`;

export function translate(src: string, multiline = false): string {
  let out = "";
  let inClass = false;
  let i = 0;
  const unsupported = (what: string): never => {
    throw new SyntaxError(`slopdam: cannot translate ${what} in /${src}/`);
  };
  while (i < src.length) {
    const ch = src[i]!;
    if (ch === "\\") {
      const n = src[i + 1] ?? unsupported("a trailing backslash");
      i += 2;
      switch (n) {
        case "w": out += inClass ? PY_WORD : `[${PY_WORD}]`; continue;
        case "s": out += inClass ? PY_SPACE : `[${PY_SPACE}]`; continue;
        case "d": out += "\\p{Nd}"; continue;
        case "W": out += inClass ? unsupported("\\W in a class") : `[^${PY_WORD}]`; continue;
        case "S": out += inClass ? unsupported("\\S in a class") : `[^${PY_SPACE}]`; continue;
        case "D": out += inClass ? unsupported("\\D in a class") : "\\P{Nd}"; continue;
        case "b": out += inClass ? "\\x08" : WORD_BOUNDARY; continue;
        case "B": out += inClass ? unsupported("\\B in a class") : `(?!${WORD_BOUNDARY})`; continue;
        case "A": out += inClass ? unsupported("\\A in a class") : "(?<![\\s\\S])"; continue;
        case "Z": out += inClass ? unsupported("\\Z in a class") : "(?![\\s\\S])"; continue;
        case "U": out += `\\u{${src.slice(i, i + 8).replace(/^0+(?=.)/, "")}}`; i += 8; continue;
        case "u": out += `\\u${src.slice(i, i + 4)}`; i += 4; continue;
        case "x": out += `\\x${src.slice(i, i + 2)}`; i += 2; continue;
        case "n": case "t": case "r": case "f": case "v": case "0":
          out += "\\" + n; continue;
      }
      if (/[1-9]/.test(n)) { out += "\\" + n; continue; }
      if (/[A-Za-z0-9]/.test(n)) unsupported(`\\${n}`);
      out += SYNTAX.includes(n) || (inClass && n === "-") ? "\\" + n : n;
      continue;
    }
    if (inClass) {
      if (ch === "]") inClass = false;
      out += ch;
      i++;
      continue;
    }
    if (ch === "[") {
      inClass = true;
      out += ch;
      i++;
      if (src[i] === "^") { out += "^"; i++; }
      if (src[i] === "]") { out += "\\]"; i++; }
      continue;
    }
    if (ch === ".") { out += "[^\\n]"; i++; continue; }
    if (ch === "^") { out += multiline ? "(?<![^\\n])" : "(?<![\\s\\S])"; i++; continue; }
    if (ch === "$") { out += multiline ? "(?![^\\n])" : "(?=\\n?(?![\\s\\S]))"; i++; continue; }
    if (src.startsWith("(?P<", i)) { out += "(?<"; i += 4; continue; }
    if (src.startsWith("(?P=", i) || src.startsWith("(?#", i) || /^\(\?[aiLmsux]/.test(src.slice(i))) {
      unsupported("an inline flag or named back reference");
    }
    out += ch;
    i++;
  }
  return out;
}

/** A global, Unicode JavaScript RegExp for a spec pattern and its flags. */
export function compile(pattern: string, flags: readonly string[] = []): RegExp {
  return new RegExp(translate(pattern, flags.includes("multiline")), "gu");
}
