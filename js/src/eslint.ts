// SPDX-License-Identifier: MIT
/**
 * ESLint plugin (flat config). The rule slopdam/no-slop reports AI traces in the string
 * arguments of log calls and fixes them:
 *
 *   // eslint.config.js
 *   import slopdam from "@slopdam/core/eslint";
 *   export default [slopdam.configs.recommended];
 *
 * Like `slopdam fix` for Python, a fix edits only the text of the literal: quotes, escape
 * sequences, `${...}` expressions and printf placeholders such as %s stay as they are, and no
 * space is left at either end that the literal did not have. ESLint is not imported here.
 */
import { Sanitizer, type SanitizerOptions } from "./sanitizer.js";

// ESLint's types are not a dependency.
type Node = any;
type Context = any;

export interface NoSlopOptions extends SanitizerOptions {
  /** A call counts as a log call when the receiver's source text matches. Default: /log|console/i. */
  receivers?: string;
  /** Method names of log calls. Default: the common logger levels and console methods. */
  methods?: string[];
  /** Plain function calls to check as well, such as ["print"]. Default: none. */
  functions?: string[];
}

const DEFAULT_METHODS = [
  "log", "info", "warn", "warning", "error", "debug", "trace", "fatal", "critical", "exception",
  "notice", "verbose", "silly", "http",
];
// Same placeholders as the Python fixer: printf-style %s, %d, %(name)s and {...}.
const PLACEHOLDER = /%(?:\([^)]*\))?[-#0 +]*\d*(?:\.\d+)?[sdifrxXeEgGcoaub%jO]|\{[^{}]*\}/g;
// Each masked piece becomes one character from the private-use plane, which the rules treat as
// part of a word (a dash next to it sits between words) and never change.
const MASK_BASE = 0xf8000;

interface Masked {
  text: string;
  pieces: string[];
  /** Index in the masked text -> index in the original body. */
  where: (i: number) => number;
}

function mask(body: string, spans: Array<[number, number]>): Masked {
  let text = "";
  const pieces: string[] = [];
  const index: number[] = [];
  let last = 0;
  for (const [a, b] of spans) {
    text += body.slice(last, a);
    for (let i = last; i < a; i++) index.push(i);
    const c = String.fromCodePoint(MASK_BASE + pieces.length);
    text += c;
    for (let k = 0; k < c.length; k++) index.push(a);
    pieces.push(body.slice(a, b));
    last = b;
  }
  text += body.slice(last);
  for (let i = last; i <= body.length; i++) index.push(i);
  return { text, pieces, where: (i) => index[Math.min(i, index.length - 1)]! };
}

function unmask(text: string, pieces: string[]): string | null {
  const seen: number[] = [];
  for (const c of text) {
    const n = c.codePointAt(0)! - MASK_BASE;
    if (n >= 0 && n < pieces.length) seen.push(n);
  }
  if (seen.length !== pieces.length || seen.some((n, i) => n !== i)) return null; // a rule swallowed a piece
  return [...text].map((c) => {
    const n = c.codePointAt(0)! - MASK_BASE;
    return n >= 0 && n < pieces.length ? pieces[n] : c;
  }).join("");
}

const noSlop = {
  meta: {
    type: "suggestion",
    docs: {
      description: "Disallow AI-generated traces (em dashes, emoji, separators, markdown) in log messages",
      url: "https://github.com/slopdam/slopdam/blob/main/js/README.md#eslint",
    },
    fixable: "code",
    schema: [
      {
        type: "object",
        properties: {
          profile: { enum: ["reader", "dev"] },
          level: { enum: ["basic", "strong", "strict"] },
          disable: { type: "array", items: { type: "string" } },
          dashInline: { enum: ["comma", "colon", "hyphen", "space"] },
          receivers: { type: "string" },
          methods: { type: "array", items: { type: "string" } },
          functions: { type: "array", items: { type: "string" } },
        },
        additionalProperties: false,
      },
    ],
    messages: {
      fixable: "{{rule}}: '{{text}}' should be '{{fix}}'",
      report: "{{rule}}: '{{text}}'",
    },
  },

  create(context: Context) {
    const options: NoSlopOptions = context.options[0] ?? {};
    const { receivers = "log|console", methods = DEFAULT_METHODS, functions = [], ...sanitizerOptions } = options;
    const sanitizer = new Sanitizer(sanitizerOptions);
    const receiverRe = new RegExp(receivers, "i");
    const methodSet = new Set(methods);
    const functionSet = new Set(functions);
    const source = context.sourceCode ?? context.getSourceCode();

    function isLogCall(call: Node): boolean {
      const callee = call.callee;
      if (callee.type === "Identifier") return functionSet.has(callee.name);
      if (callee.type !== "MemberExpression") return false;
      const name = callee.computed ? (callee.property.type === "Literal" ? String(callee.property.value) : null) : callee.property.name;
      return name !== null && methodSet.has(name) && receiverRe.test(source.getText(callee.object));
    }

    /** The literal's body (between the quotes or backticks) and the pieces that must not change. */
    function bodyOf(node: Node): { start: number; body: string; spans: Array<[number, number]>; quote: string } | null {
      const raw: string = source.getText(node);
      const start = node.range[0] + 1;
      const body = raw.slice(1, -1);
      if (node.type === "Literal") {
        if (typeof node.value !== "string") return null;
        const spans: Array<[number, number]> = [];
        for (const m of body.matchAll(PLACEHOLDER)) if (m[0] !== "%%") spans.push([m.index!, m.index! + m[0].length]);
        return { start, body, spans, quote: raw[0]! };
      }
      // Template literal: mask every ${...}, braces and inner spaces included.
      const spans: Array<[number, number]> = node.expressions.map((e: Node): [number, number] => [
        source.getTokenBefore(e).range[1] - 2 - start,
        source.getTokenAfter(e).range[0] + 1 - start,
      ]);
      return { start, body, spans, quote: "`" };
    }

    /** joinedBefore/After: the literal is concatenated with something on that side ("a — " + b). */
    function check(node: Node, joinedBefore: boolean, joinedAfter: boolean): void {
      const part = bodyOf(node);
      if (!part) return;
      const { start, body, quote } = part;
      // An empty piece at a joined end stands for the neighbor, so a dash there is between words.
      const spans: Array<[number, number]> = [
        ...(joinedBefore ? [[0, 0] as [number, number]] : []),
        ...part.spans,
        ...(joinedAfter ? [[body.length, body.length] as [number, number]] : []),
      ];
      const masked = mask(body, spans);
      const found = sanitizer.findings(masked.text);
      if (!found.length) return;

      // Apply each fix at its span, as the Python fixer does; overlapping findings are skipped.
      let out = "";
      let last = 0;
      const shown = [];
      for (const f of found) {
        if (f.start < last) continue;
        shown.push(f);
        if (f.fix === null) continue;
        let fix = f.fix;
        if (fix.includes("\\") || fix.includes(quote) || (quote === "`" && fix.includes("${"))) {
          fix = fix.replace(/\\/g, "\\\\").split(quote).join("\\" + quote).replace(/\$\{/g, "\\${");
        }
        out += masked.text.slice(last, f.start) + fix;
        last = f.end;
      }
      out += masked.text.slice(last);
      let newBody = unmask(out, masked.pieces);
      if (newBody !== null) {
        // Do not leave a space at either end that the original literal did not have.
        if (body === body.replace(/^\s+/, "")) newBody = newBody.replace(/^[ \t]+/, "");
        if (body === body.replace(/\s+$/, "")) newBody = newBody.replace(/[ \t]+$/, "");
      }
      const replacement = newBody !== null && newBody !== body ? quote + newBody + quote : null;

      for (const f of shown) {
        const from = start + masked.where(f.start);
        const to = start + masked.where(f.end);
        context.report({
          node,
          loc: { start: source.getLocFromIndex(from), end: source.getLocFromIndex(to) },
          messageId: f.fix === null ? "report" : "fixable",
          data: { rule: f.ruleId, text: f.text, fix: f.fix ?? "" },
          fix: replacement === null ? null : (fixer: any) => fixer.replaceTextRange(node.range, replacement),
        });
      }
    }

    /** The operands of a + chain, left to right: "a" + b + "c" -> ["a", b, "c"]. */
    function operands(node: Node, out: Node[]): Node[] {
      if (node.type === "BinaryExpression" && node.operator === "+") {
        operands(node.left, out);
        operands(node.right, out);
      } else out.push(node);
      return out;
    }

    const isString = (n: Node): boolean => (n.type === "Literal" && typeof n.value === "string") || n.type === "TemplateLiteral";

    return {
      CallExpression(call: Node) {
        if (!isLogCall(call)) return;
        for (const arg of call.arguments) {
          const parts = operands(arg, []);
          parts.forEach((p, i) => {
            if (isString(p)) check(p, i > 0, i < parts.length - 1);
          });
        }
      },
    };
  },
};

const plugin: { meta: { name: string }; rules: { "no-slop": typeof noSlop }; configs: Record<string, unknown> } = {
  meta: { name: "@slopdam/core/eslint" },
  rules: { "no-slop": noSlop },
  configs: {},
};

plugin.configs = {
  /** slopdam/no-slop as a warning, reader profile. */
  recommended: { name: "slopdam/recommended", plugins: { slopdam: plugin }, rules: { "slopdam/no-slop": "warn" } },
  /** Same, with dev-style fixes ([OK] tags, " - " for dashes). */
  dev: { name: "slopdam/dev", plugins: { slopdam: plugin }, rules: { "slopdam/no-slop": ["warn", { profile: "dev" }] } },
};

export default plugin;
export { noSlop };
