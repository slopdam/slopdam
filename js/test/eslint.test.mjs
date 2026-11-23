// SPDX-License-Identifier: MIT
// slopdam/no-slop with ESLint's RuleTester (ESLint is a dev dependency only).
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { describe, it, test } from "node:test";
import { Linter, RuleTester } from "eslint";
import plugin from "../dist/esm/eslint.js";

RuleTester.describe = describe;
RuleTester.it = it;
RuleTester.itOnly = it.only;

const rule = plugin.rules["no-slop"];
const tester = new RuleTester({ languageOptions: { ecmaVersion: "latest", sourceType: "module" } });

tester.run("no-slop", rule, {
  valid: [
    'console.log("Saved 3 rows: done")',
    'logger.info("2026-11-21 user_id=3 --dry-run k8s-node-01")',
    'title("✅ — not a log call")',                       // not a log call
    'const s = "🚀 — just a string";',
    'console.log(`see ${url} for 2024-2025`)',
    'log.info("%s - %d", a, b)',
    'console.log(`a—b`.length)',                            // only direct arguments are checked
    'console.log("https://a.com/x—y and `a—b`")',           // protected spans
    'log.info(3, null, x)',
  ],
  invalid: [
    {
      code: 'console.log("✅ **Saved** 3 rows — done! 🎉")',
      output: 'console.log("Saved 3 rows: done!")',
      errors: [
        { messageId: "fixable", data: { rule: "emoji.pictograph", text: "✅", fix: "" }, column: 14 },
        { messageId: "fixable", data: { rule: "md.emphasis", text: "**Saved**", fix: "Saved" } },
        { messageId: "fixable", data: { rule: "dash.run", text: "—", fix: ": " } },
        { messageId: "fixable", data: { rule: "emoji.pictograph", text: "🎉", fix: "" } },
      ],
    },
    {
      // printf placeholders and the quote style stay; a dash next to %d sits between words
      code: "logger.warn('⚠️ Retrying %d times — “db-01” is slow', n)",
      output: "logger.warn('Retrying %d times: \"db-01\" is slow', n)",
      errors: 4,
    },
    {
      code: 'log.info("완료 “db” 처리")',
      output: 'log.info("완료 \\"db\\" 처리")',               // a new double quote is escaped
      errors: 2,
    },
    {
      // template expressions are never edited, spaces inside ${ } included
      code: "console.error(`❌ ${ count } rows — failed`)",
      output: "console.error(`${ count } rows: failed`)",
      errors: 2,
    },
    {
      code: 'this.logger.info("✅ 저장 ㅡ " + total + "건")',
      output: 'this.logger.info("저장: " + total + "건")',  // the trailing space before + is kept
      errors: 2,
    },
    {
      code: 'console.log("✅ Upload done — 3 files")',
      output: 'console.log("[OK] Upload done - 3 files")',
      options: [{ profile: "dev" }],
      errors: 2,
    },
    {
      code: 'print("완료 ㅡ 다음")',
      output: 'print("완료, 다음")',
      options: [{ functions: ["print"], dashInline: "comma" }],
      errors: 1,
    },
    {
      code: 'console.log("✅ 완료 ㅡ 다음")',
      output: 'console.log("✅ 완료: 다음")',
      options: [{ disable: ["emoji"] }],
      errors: 1,
    },
    {
      code: `console.log("Let's go")`,                        // report-only rule: no fix
      output: null,
      errors: [{ messageId: "report", data: { rule: "tone.chatty", text: "Let's" } }],
    },
    {
      code: 'console.log("‒• 항목")',                     // a fix that exposes another trace is done in one pass
      output: 'console.log("- 항목")',
      errors: [{ messageId: "fixable", data: { rule: "dash.run", text: "‒", fix: "" } }],
    },
    {
      code: 'console.log("```python %s", x)',            // the message shows the source, not a placeholder
      output: null,
      errors: [{ messageId: "fixable", data: { rule: "md.fence", text: "```python %s", fix: "" } }],
    },
    {
      code: 'console.log("\\u2014 ✅ done")',                // escapes stay as they are
      output: 'console.log("\\u2014 done")',
      errors: 1,
    },
  ],
});

test("recommended config works with the Linter", () => {
  const linter = new Linter();
  const config = [plugin.configs.recommended];
  const { output, messages, fixed } = linter.verifyAndFix('console.log("🚀 Server started — port 8080")', config);
  assert.equal(fixed, true);
  assert.equal(output, 'console.log("Server started: port 8080")');
  assert.deepEqual(messages, []);
  const dev = linter.verifyAndFix('console.log("🚀 Server started — port 8080")', [plugin.configs.dev]);
  assert.equal(dev.output, 'console.log("Server started - port 8080")');
});

test("CommonJS build", () => {
  const cjs = createRequire(import.meta.url)("../dist/cjs/eslint.js");
  assert.equal(typeof cjs.default.rules["no-slop"].create, "function");
});
