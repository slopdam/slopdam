// SPDX-License-Identifier: MIT
// The pino and winston integrations against the real libraries (dev dependencies only).
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { Writable } from "node:stream";
import { test } from "node:test";
import pino from "pino";
import winston from "winston";
import { slopdamPino } from "../dist/esm/pino.js";
import { slopdamWinston } from "../dist/esm/winston.js";

const require = createRequire(import.meta.url);

function sink() {
  const lines = [];
  const stream = new Writable({
    write(chunk, _enc, done) {
      lines.push(...chunk.toString().split("\n").filter(Boolean));
      done();
    },
  });
  return { stream, lines };
}

test("pino: messages are cleaned, objects and errors are not", () => {
  const { stream, lines } = sink();
  const log = pino({ ...slopdamPino({ profile: "dev" }), base: undefined, timestamp: false }, stream);
  log.info("✅ **Saved** %d rows — done!", 3);
  log.info({ user: "a—b", note: "✅ kept" }, "🚀 Started — ok");
  log.info("==========");
  log.error(new Error("boom — original"), "❌ Upload failed");
  log.warn("⚠️ 디스크 부족 ㅡ 확인");
  const out = lines.map((l) => JSON.parse(l));
  assert.deepEqual(out.map((o) => o.msg), [
    "[OK] Saved 3 rows - done!",
    "Started - ok",
    "Upload failed",          // the error level already says it failed
    "디스크 부족 - 확인",       // ...and the warning level says it is a warning
  ]);
  assert.equal(out[1].user, "a—b");
  assert.equal(out[1].note, "✅ kept");
  assert.equal(out[2].err.message, "boom — original");
});

test("pino: reader profile and an existing logMethod hook", () => {
  const { stream, lines } = sink();
  const seen = [];
  const hooks = { logMethod(args, method) { seen.push(args[0]); method.apply(this, args); } };
  const log = pino({ ...slopdamPino({ hooks }), base: undefined, timestamp: false }, stream);
  log.info("✅ **저장 완료** ㅡ 3건 처리했습니다! 🎉");
  assert.equal(JSON.parse(lines[0]).msg, "저장 완료: 3건 처리했습니다.");
  assert.deepEqual(seen, ["저장 완료: 3건 처리했습니다."]);
});

test("winston: a profile per transport", () => {
  const console = sink();
  const file = sink();
  const { combine, printf, json } = winston.format;
  const logger = winston.createLogger({
    level: "info",
    transports: [
      new winston.transports.Stream({ stream: console.stream, format: combine(slopdamWinston(), printf((i) => i.message)) }),
      new winston.transports.Stream({ stream: file.stream, format: combine(slopdamWinston({ profile: "dev" }), json()) }),
    ],
  });
  logger.info("✅ **Saved** 3 rows — done! 🎉");
  logger.info("ㅡㅡㅡㅡㅡㅡ");
  logger.error("❌ Upload failed — see https://example.com/runs/42");
  assert.deepEqual(console.lines, ["Saved 3 rows: done!", "Upload failed: see https://example.com/runs/42"]);
  assert.deepEqual(file.lines.map((l) => JSON.parse(l).message), ["[OK] Saved 3 rows - done!", "Upload failed - see https://example.com/runs/42"]);
});

test("winston: after splat, before the final format; stack traces are kept", () => {
  const { stream, lines } = sink();
  const { combine, splat, errors, json } = winston.format;
  const logger = winston.createLogger({
    format: combine(errors({ stack: true }), splat(), slopdamWinston({ profile: "dev" }), json()),
    transports: [new winston.transports.Stream({ stream })],
  });
  logger.warn("⚠️ %s rows — slow", 3);
  logger.error(new Error("boom — original"));
  const [warn, err] = lines.map((l) => JSON.parse(l));
  assert.equal(warn.message, "3 rows - slow");
  assert.equal(err.message, "boom - original");
  assert.match(err.stack, /boom — original/);
});

test("CommonJS subpaths", () => {
  assert.equal(typeof require("../dist/cjs/pino.js").slopdamPino, "function");
  assert.equal(typeof require("../dist/cjs/winston.js").slopdamWinston, "function");
});
