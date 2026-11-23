// SPDX-License-Identifier: MIT
import assert from "node:assert/strict";
import { test } from "node:test";
import { clean, LEVELS, PROFILES, RULE_IDS, Sanitizer, SPEC_VERSION } from "../dist/esm/index.js";
import { splitlines, translate } from "../dist/esm/pyregex.js";

test("exports", () => {
  assert.deepEqual(PROFILES, ["reader", "dev"]);
  assert.deepEqual(LEVELS, ["basic", "strong", "strict"]);
  assert.equal(SPEC_VERSION, 1);
  assert.ok(RULE_IDS.includes("dash.run") && RULE_IDS.includes("emoji.pictograph"));
});

test("clean() with options", () => {
  assert.equal(clean("완료 ㅡ 다음"), "완료: 다음");
  assert.equal(clean("완료 ㅡ 다음", { dashInline: "comma" }), "완료, 다음");
  assert.equal(clean("❌ 실패", { profile: "dev" }), "[FAIL] 실패");
  assert.equal(clean("❌ 실패", { profile: "dev", logLevel: "error" }), "실패");
  assert.equal(clean("❌ 실패", { profile: "dev", logLevel: 40 }), "실패");
  assert.equal(clean("성공적으로 저장", { level: "strong" }), "저장");
});

test("disable by rule ID or group", () => {
  assert.equal(new Sanitizer({ disable: ["emoji"] }).clean("✅ 완료 ㅡ 다음"), "✅ 완료: 다음");
  assert.equal(new Sanitizer({ disable: ["dash.run"] }).clean("✅ 완료 ㅡ 다음"), "완료 ㅡ 다음");
  assert.equal(new Sanitizer({ disable: ["dash"] }).clean("a — b"), "a — b");
});

test("invalid options throw", () => {
  assert.throws(() => new Sanitizer({ profile: "nope" }), RangeError);
  assert.throws(() => new Sanitizer({ level: "max" }), RangeError);
  assert.throws(() => new Sanitizer({ dashInline: "semicolon" }), RangeError);
});

test("findings point into the input, with UTF-16 offsets", () => {
  const text = 'log.info("✅ **Saved** 3 rows — done! 🎉")';
  const found = new Sanitizer().findings(text);
  assert.deepEqual(found.map((f) => [f.ruleId, f.text, f.fix]), [
    ["emoji.pictograph", "✅", ""],
    ["md.emphasis", "**Saved**", "Saved"],
    ["dash.run", "—", ": "],
    ["emoji.pictograph", "🎉", ""],
  ]);
  for (const f of found) assert.equal(text.slice(f.start, f.end).trim(), f.text);
});

test("findings skip protected spans and report-only rules have no fix", () => {
  assert.deepEqual(new Sanitizer().findings("see https://a.com/x—y and `a—b`"), []);
  const [f] = new Sanitizer().findings("Let's go");
  assert.equal(f.ruleId, "tone.chatty");
  assert.equal(f.fix, null);
});

test("translator keeps Python's meaning", () => {
  const re = (p, f) => new RegExp(translate(p), f ?? "u");
  assert.ok(re("^\\w+$").test("저장_3"));           // Unicode \w
  assert.ok(re("^\\s$").test("\u3000"));             // Unicode \s
  assert.ok(!re("^\\s$").test("\ufeff"));            // ...without the BOM, like Python
  assert.ok(re("\\bLet's\\b").test("Let's go"));
  assert.ok(!re("\\bLet's\\b").test("가Let's"));     // \b around Hangul is not a boundary
  assert.ok(re("\\Aa", "mu").test("a\nb") && !re("\\Ab", "mu").test("a\nb"));
  const ml = (p) => new RegExp(translate(p, true), "u");
  assert.ok(ml("^b$").test("a\nb\nc"));
  assert.ok(!ml("^b").test("a\rb") && !ml("^b").test("a\u2028b")); // only \n starts a line, as in Python
  assert.ok(new RegExp(translate("a$"), "u").test("a\n") && !new RegExp(translate("^b"), "u").test("a\nb"));
  assert.ok(re("[\\U0001F600]").test("😀"));
  assert.equal(translate("(?P<url>x)"), "(?<url>x)");
  assert.equal(translate('[^\\"]'), '[^"]');
  assert.throws(() => translate("(?i)x"), SyntaxError);
});

test("splitlines matches Python", () => {
  assert.deepEqual(splitlines(""), []);
  assert.deepEqual(splitlines("a\n"), ["a"]);
  assert.deepEqual(splitlines("a\n\nb"), ["a", "", "b"]);
  assert.deepEqual(splitlines("a\r\nb\rc\u2028d"), ["a", "b", "c", "d"]);
});
