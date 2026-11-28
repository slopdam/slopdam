// SPDX-License-Identifier: MIT
/**
 * The slopdam engine, following ../spec/README.md step by step.
 * Patterns, character sets and the rule order come from the spec (src/spec.generated.ts);
 * only the four context-dependent actions are written here.
 *
 * Offsets in findings are UTF-16 code unit offsets, as everywhere in JavaScript.
 */
import { compile, isAlnum, isDigit, pyRstrip, pyStrip, splitlines } from "./pyregex.js";
import { SPEC } from "./spec.generated.js";
import type { Level, Profile, RuleSpec } from "./types.js";

export type DashInline = "comma" | "colon" | "hyphen" | "space";

/** Python logging levels: a number (WARNING 30, ERROR 40) or a name such as "error". */
export type LogLevel = number | string;

export interface SanitizerOptions {
  /** "reader" (default): plain text for people. "dev": grep-friendly text for tools. */
  profile?: Profile;
  /** "basic" (default), "strong" or "strict". */
  level?: Level;
  /** Rule IDs or groups to turn off, such as "emoji" or "dash.run". */
  disable?: Iterable<string>;
  /** What an inline dash becomes in the reader profile. Default "colon". */
  dashInline?: DashInline;
}

export interface Finding {
  ruleId: string;
  description: string;
  start: number;
  end: number;
  text: string;
  /** The replacement, or null when the rule only reports. */
  fix: string | null;
}

export const PROFILES: readonly Profile[] = SPEC.profiles;
export const LEVELS: readonly Level[] = SPEC.levels;
export const SPEC_VERSION: number = SPEC.spec_version;

const LOG_LEVELS: Record<string, number> = {
  CRITICAL: 50, FATAL: 50, ERROR: 40, WARNING: 30, WARN: 30, INFO: 20, DEBUG: 10, NOTSET: 0,
};

function levelNumber(level: LogLevel | undefined): number | undefined {
  if (level === undefined) return undefined;
  if (typeof level === "number") return level;
  return LOG_LEVELS[level.toUpperCase()];
}

interface Context {
  profile: Profile;
  dashInline: string;
  levelno: number | undefined;
}

type Fn = (m: RegExpExecArray, ctx: Context) => string;

// --- placeholders for protected spans (spec: algorithm step 1) -------------------------------
const PUA = 0xf0000;
const PUA_RE = /[\u{F0000}-\u{FFFFD}]/u;
const PUA_RE_G = /[\u{F0000}-\u{FFFFD}]/gu;
const PROTECT = compile(SPEC.protected_spans);
const MULTI_SPACE = compile(SPEC.tidy.multi_space);
const QUOTE_SPACE = compile(SPEC.tidy.quote_space);

/** The whole character that ends at index i, or starts at index i. */
function charBefore(s: string, i: number): string {
  const cp = s.codePointAt(i - 1)!;
  if (i >= 2 && cp >= 0xdc00 && cp <= 0xdfff) return s.slice(i - 2, i);
  return s.slice(i - 1, i);
}
function charAt(s: string, i: number): string {
  return String.fromCodePoint(s.codePointAt(i)!);
}

// --- the four context-dependent actions --------------------------------------------------------
const STATUS_OF: Record<string, string> = {};
for (const [tag, chars] of Object.entries(SPEC.charsets.status)) {
  for (const c of chars) STATUS_OF[c] = tag;
}
const CHOSEONG = new RegExp(`^[${SPEC.charsets.hangul_choseong}]$`, "u");
const HAN_KANA = new RegExp(`[${SPEC.charsets.han_kana}]`, "u");
const wordish = (c: string, extra: string): boolean => isAlnum(c) || extra.includes(c) || PUA_RE.test(c);

const FUNCTIONS: Record<string, Fn> = {
  fullwidth: (m) => {
    // Chinese and Japanese write this punctuation full width, so a line with kana or CJK
    // ideographs keeps it; elsewhere it becomes ASCII.
    const end = m.input.indexOf("\n", m.index);
    const line = m.input.slice(m.input.lastIndexOf("\n", m.index - 1) + 1, end < 0 ? undefined : end);
    if (HAN_KANA.test(line)) return m[0];
    return m[0].replace(/[！-～]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0xfee0));
  },

  unwrap: (m) => m[1] ?? "",

  quote_double: (m) => {
    // Inside a double-quoted string a plain quote would end it, so it is escaped.
    const before = m.input.slice(m.input.lastIndexOf("\n", m.index - 1) + 1, m.index);
    let n = 0;
    for (let j = 0; j < before.length; j++) if (before[j] === '"' && (j === 0 || before[j - 1] !== "\\")) n++;
    return n % 2 ? '\\"' : '"';
  },

  status_tag: (m, ctx) => {
    const tag = STATUS_OF[m[1]!]!;
    const at = SPEC.status_redundant_at[tag];
    if (ctx.levelno !== undefined && at !== undefined && ctx.levelno >= levelNumber(at)!) return "";
    return tag + " ";
  },

  dash_run: (m, ctx) => {
    const s = m.input;
    const start = m.index;
    const end = start + m[0].length;
    const lead = m[1]!;
    const run = m[2]!;
    if (run[0] === "ᅳ" && start + lead.length > 0 && CHOSEONG.test(charBefore(s, start + lead.length))) {
      return m[0]; // part of a composed old-style syllable
    }
    const prev = start ? charBefore(s, start) : "\n";
    const next = end < s.length ? charAt(s, end) : "\n";
    const inner = wordish(prev, SPEC.dash_word_before) && wordish(next, SPEC.dash_word_after);
    if ([...run].length >= 2) return inner ? " " : ""; // separator or emoticon: ㅡㅡ, ──
    if (isDigit(prev) && isDigit(next)) return ctx.profile === "reader" ? "~" : "-";
    const head = s.slice(start === 0 ? 0 : s.lastIndexOf("\n", start - 1) + 1, start);
    if (!pyStrip(head) && m[3]) return lead + "- "; // list marker at line start
    if (inner) return ctx.profile === "reader" ? ctx.dashInline : " - ";
    return "";
  },
};

/** Python's Match.expand for the replacement strings in the spec (\1, \g<1>, \g<name>). */
function expand(template: string, m: RegExpExecArray): string {
  return template.replace(/\\(?:(\d+)|g<(\w+)>|(.))/g, (_, num?: string, g?: string, other?: string) => {
    if (num !== undefined) return m[Number(num)] ?? "";
    if (g !== undefined) return (/^\d+$/.test(g) ? m[Number(g)] : m.groups?.[g]) ?? "";
    return { n: "\n", t: "\t", r: "\r", "\\": "\\" }[other!] ?? "\\" + other;
  });
}

/** Python's re.sub with a function: every non-overlapping match, left to right. */
function sub(re: RegExp, text: string, fn: (m: RegExpExecArray) => string): string {
  re.lastIndex = 0;
  let out = "";
  let last = 0;
  for (let m = re.exec(text); m; m = re.exec(text)) {
    out += text.slice(last, m.index) + fn(m);
    last = m.index + m[0].length;
    if (m[0].length === 0) re.lastIndex += (text.codePointAt(re.lastIndex) ?? 0) > 0xffff ? 2 : 1;
  }
  return out + text.slice(last);
}

interface Rule {
  id: string;
  description: string;
  re: RegExp;
  /** null: report only. */
  action: ((m: RegExpExecArray, ctx: Context) => string) | null;
}

function buildRule(spec: RuleSpec, profile: Profile): Rule | null {
  const a = spec.actions[profile];
  if (!a) return null;
  let action: Rule["action"];
  if (a.kind === "report") action = null;
  else if (a.kind === "replace") action = (m) => expand(a.value, m);
  else {
    const fn = FUNCTIONS[a.name];
    if (!fn) throw new Error(`slopdam: spec function ${a.name} is not implemented`);
    action = fn;
  }
  return { id: spec.id, description: spec.description, re: compile(spec.pattern, spec.flags), action };
}

export class Sanitizer {
  readonly profile: Profile;
  readonly level: Level;
  private readonly dashInline: string;
  private readonly rules: Rule[];

  constructor(options: SanitizerOptions = {}) {
    const { profile = "reader", level = "basic", disable = [], dashInline = SPEC.default_dash_inline as DashInline } = options;
    if (!PROFILES.includes(profile)) throw new RangeError(`unknown profile ${JSON.stringify(profile)}, expected one of ${PROFILES.join(", ")}`);
    if (!LEVELS.includes(level)) throw new RangeError(`unknown level ${JSON.stringify(level)}, expected one of ${LEVELS.join(", ")}`);
    const inline = SPEC.dash_inline[dashInline];
    if (inline === undefined) throw new RangeError(`unknown dashInline ${JSON.stringify(dashInline)}, expected one of ${Object.keys(SPEC.dash_inline).join(", ")}`);
    const off = [...disable];
    this.profile = profile;
    this.level = level;
    this.dashInline = inline;
    this.rules = SPEC.rules
      .filter((r) => LEVELS.indexOf(r.level) <= LEVELS.indexOf(level))
      .filter((r) => !off.some((d) => r.id === d || r.id.startsWith(d + ".")))
      .map((r) => buildRule(r, profile))
      .filter((r): r is Rule => r !== null);
  }

  private context(logLevel?: LogLevel): Context {
    return { profile: this.profile, dashInline: this.dashInline, levelno: levelNumber(logLevel) };
  }

  private apply(text: string, ctx: Context): string {
    for (const rule of this.rules) {
      const action = rule.action;
      if (action) text = sub(rule.re, text, (m) => action(m, ctx));
    }
    return text;
  }

  /** Remove AI traces from text. logLevel lets dev drop a status tag the level already says. */
  clean(text: string, logLevel?: LogLevel): string {
    const ctx = this.context(logLevel);
    text = splitlines(text).join("\n");
    for (let pass = 0; pass < SPEC.tidy.max_passes; pass++) {
      const cleaned = this.cleanOnce(text, ctx);
      if (cleaned === text) break;
      text = cleaned;
    }
    return text;
  }

  private cleanOnce(text: string, ctx: Context): string {
    const saved: string[] = [];
    const masked = sub(PROTECT, text, (m) => {
      let kept = m[0];
      // reader drops the backticks, but only when the code itself is clean.
      const code = m.groups?.["code"];
      if (code !== undefined && this.profile === "reader" && this.apply(code, ctx) === code) kept = code;
      saved.push(kept);
      return String.fromCodePoint(PUA + saved.length - 1);
    });
    const applied = this.apply(masked, ctx);
    // No rule adds or removes a line break, so lines compare one to one. Only lines a rule
    // changed are tidied, while protected spans are still masked.
    const before = masked.split("\n");
    let out = applied
      .split("\n")
      .map((line, i) => (line === before[i] ? line : sub(QUOTE_SPACE, sub(MULTI_SPACE, line, () => " "), () => "")))
      .join("\n");
    out = out.replace(PUA_RE_G, (c) => saved[c.codePointAt(0)! - PUA]!);
    const lines: string[] = [];
    for (let line of splitlines(out)) {
      line = lines.length ? pyRstrip(line) : pyStrip(line);
      if (line) lines.push(line);
    }
    return lines.join("\n");
  }

  /** What clean() would change, with spans in the original text (one pass, no tidying). */
  findings(text: string): Finding[] {
    const ctx = this.context();
    let work = "";
    let spans: Array<[number, number]> = []; // per code unit of work: its span in text
    let last = 0;
    for (const m of text.matchAll(PROTECT)) {
      for (let i = last; i < m.index!; i++) { work += text[i]; spans.push([i, i + 1]); }
      const placeholder = String.fromCodePoint(PUA);
      work += placeholder;
      for (let k = 0; k < placeholder.length; k++) spans.push([m.index!, m.index! + m[0].length]);
      last = m.index! + m[0].length;
    }
    for (let i = last; i < text.length; i++) { work += text[i]; spans.push([i, i + 1]); }

    const found: Finding[] = [];
    for (const rule of this.rules) {
      const pieces: string[] = [];
      const newSpans: Array<[number, number]> = [];
      let pos = 0;
      let start = 0;
      let end = 0;
      rule.re.lastIndex = 0;
      for (let m = rule.re.exec(work); m; m = rule.re.exec(work)) {
        const fix = rule.action ? rule.action(m, ctx) : null;
        if (m[0].length > 0) {
          start = spans[m.index]![0];
          end = spans[m.index + m[0].length - 1]![1];
          if (pyStrip(m[0]) && fix !== m[0]) {
            found.push({ ruleId: rule.id, description: rule.description, start, end, text: pyStrip(text.slice(start, end)), fix });
          }
        } else {
          rule.re.lastIndex++;
        }
        if (fix === null || fix === m[0]) continue;
        pieces.push(work.slice(pos, m.index));
        newSpans.push(...spans.slice(pos, m.index));
        pieces.push(fix);
        for (let k = 0; k < fix.length; k++) newSpans.push([start, end]);
        pos = m.index + m[0].length;
      }
      if (pieces.length) {
        pieces.push(work.slice(pos));
        newSpans.push(...spans.slice(pos));
        work = pieces.join("");
        spans = newSpans;
      }
    }
    found.sort((a, b) => a.start - b.start || b.end - a.end);
    const kept: Finding[] = [];
    for (const f of found) {
      // drop hits nested inside an earlier one (e.g. emoji.status + emoji.pictograph)
      if (!kept.some((k) => k.start <= f.start && f.end <= k.end)) kept.push(f);
    }
    return kept;
  }
}

/** Clean text with a one-off Sanitizer. */
export function clean(text: string, options: SanitizerOptions & { logLevel?: LogLevel } = {}): string {
  const { logLevel, ...rest } = options;
  return new Sanitizer(rest).clean(text, logLevel);
}

/** All rule IDs in pipeline order. */
export const RULE_IDS: readonly string[] = [...new Set(SPEC.rules.map((r) => r.id))];
