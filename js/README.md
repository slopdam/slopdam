<h1 align="center">slopdam for JavaScript</h1>

<p align="center"><i>The JavaScript and TypeScript port of <a href="https://github.com/slopdam/slopdam">slopdam</a>: em dashes, emoji, separator lines and markdown stay out of your logs.</i></p>

<p align="center"><b>English</b> | <a href="https://github.com/slopdam/slopdam/blob/main/js/README.ko.md">한국어</a></p>

<p align="center">
  <a href="https://github.com/slopdam/slopdam/actions/workflows/ci.yml"><img src="https://github.com/slopdam/slopdam/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/slopdam/slopdam/blob/main/spec/README.md"><img src="https://img.shields.io/badge/spec-v1%20conformance%20tested-informational.svg" alt="Spec v1: conformance tested"></a>
  <a href="https://github.com/slopdam/slopdam/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
</p>

`@slopdam/core` removes the traces AI coding tools leave in log messages and console output: em dashes and look-alike lines (including the Korean `ㅡ`), decorative emoji, separator lines, markdown bold, curly quotes and invisible characters. It gives exactly the same output as the Python package, because both are tested against the same [conformance cases](https://github.com/slopdam/slopdam/blob/main/spec/README.md).

```
input : ✅ **Saved** — 3 rows processed 🎉
reader: Saved: 3 rows processed
dev   : [OK] Saved - 3 rows processed
```

- `reader` (default): plain text for people, such as CLI messages, alerts and reports.
- `dev`: grep-friendly text for log files and collectors. Status emoji become `[OK]`, `[FAIL]` and `[WARN]` instead of disappearing.

## Install

Node.js 20 or later, or any modern browser. No runtime dependencies; ESM and CommonJS builds with TypeScript types.

```bash
npm install @slopdam/core
```

## Use

```js
import { clean, Sanitizer } from "@slopdam/core";

clean("✅ **Saved** — 3 rows 🎉");                      // "Saved: 3 rows"
clean("✅ **저장 완료** ㅡ 3건 처리했습니다! 🎉");         // "저장 완료: 3건 처리했습니다."

const dev = new Sanitizer({ profile: "dev" });
dev.clean("✅ Upload done — 3 files");                   // "[OK] Upload done - 3 files"
dev.clean("❌ Upload failed", "error");                   // "Upload failed" (the level already says it)

console.log(dev.findings("log.info('🚀 Started — ok')"));
// [ { ruleId: 'emoji.pictograph', text: '🚀', fix: '', start: 10, end: 13, ... },
//   { ruleId: 'dash.run', text: '—', fix: ' - ', ... } ]
```

`require("@slopdam/core")` works the same way in CommonJS.

### pino

```js
import pino from "pino";
import { slopdamPino } from "@slopdam/core/pino";

const log = pino({ ...slopdamPino({ profile: "dev" }) });
log.info("✅ **Saved** %d rows — done!", 3);   // msg: "[OK] Saved 3 rows - done!"
log.error(err, "❌ Upload failed");            // msg: "Upload failed", err untouched
```

The message of every call is cleaned before pino writes it. Objects and errors are left as they are, and a call that only printed a separator line is dropped. The profile applies to the whole logger; to send `reader` text to one place and `dev` text to another, use two loggers. If you already pass `hooks.logMethod`, give it to `slopdamPino({ hooks })` so both run.

### winston

```js
import winston from "winston";
import { slopdamWinston } from "@slopdam/core/winston";

const { combine, printf, json } = winston.format;
winston.createLogger({
  transports: [
    new winston.transports.Console({ format: combine(slopdamWinston(), printf((i) => i.message)) }),
    new winston.transports.File({ filename: "app.log", format: combine(slopdamWinston({ profile: "dev" }), json()) }),
  ],
});
// console: "Saved 3 rows: done!"   app.log: {"message":"[OK] Saved 3 rows - done!", ...}
```

winston gives every transport its own copy of the entry, so each one can use its own profile. Put `slopdamWinston()` after `format.splat()` and before `colorize()`, `printf()`, `simple()` or `json()`. Stack traces are kept as they are.

Neither integration imports pino or winston, so `@slopdam/core` still has no runtime dependencies.

### ESLint

```js
// eslint.config.js
import slopdam from "@slopdam/core/eslint";

export default [slopdam.configs.recommended];   // or slopdam.configs.dev
```

```
$ npx eslint src/
src/sync.js
  4:13  warning  emoji.pictograph: '✅' should be ''  slopdam/no-slop
  4:41  warning  dash.run: '—' should be ': '        slopdam/no-slop

$ npx eslint --fix src/
-  log.info(`✅ Synced ${rows.length} rows — done`);
+  log.info(`Synced ${rows.length} rows: done`);
```

The rule `slopdam/no-slop` checks the string arguments of `console.*` calls and of logger calls whose receiver contains `log` (`log.info`, `this.logger.warn`), including template literals and `"a" + b` concatenations. `eslint --fix` edits only the text of the literal: quotes, escape sequences, `${...}` expressions and `%s` placeholders stay, and no space is added at either end. Options:

```js
rules: {
  "slopdam/no-slop": ["warn", {
    profile: "dev",              // same options as Sanitizer: level, disable, dashInline
    receivers: "log|console|audit", // regular expression for the receiver of a log call
    functions: ["print"],        // plain functions to check as well
  }],
}
```

### Options

| Option | Values | Default |
|---|---|---|
| `profile` | `"reader"`, `"dev"` | `"reader"` |
| `level` | `"basic"`, `"strong"` (also removes filler words), `"strict"` (also reports any non-ASCII symbol) | `"basic"` |
| `disable` | rule IDs or groups, such as `["emoji"]` or `["dash.run"]` | `[]` |
| `dashInline` | what an inline dash becomes in `reader`: `"colon"`, `"comma"`, `"hyphen"`, `"space"` | `"colon"` |

The second argument of `clean()` is the log level, as a name (`"error"`, `"warning"`) or a Python logging number (40, 30). `findings()` returns what `clean()` would change, with `start` and `end` as UTF-16 offsets into the input.

URLs, inline code, `key=value` values and file paths are never changed. Cleaning twice gives the same result as cleaning once.

## How it stays in step with Python

The rules are not rewritten by hand. The build reads the repository's [spec/](https://github.com/slopdam/slopdam/blob/main/spec/README.md) directly; its patterns are translated from Python's regular expression dialect when the package loads (Unicode `\w`, `\s` and `\b`, and Python's `^` and `$`), and only the four context-dependent actions are written in TypeScript. Every pull request runs the conformance cases against the Python package and against this package's ESM and CommonJS builds, so a rule cannot change in one language only. On 20,000 random inputs the two packages gave identical results.

## Roadmap

Part of slopdam milestone 0.5 ([roadmap](https://github.com/slopdam/slopdam/blob/main/ROADMAP.md)): the core package, the pino and winston integrations and the ESLint rule.

## Contributing

A rule change is made once, in the Python reference and `spec/`, with conformance cases; this package picks it up on the next build, and the same pull request shows whether it passes. Contributions follow the slopdam [contribution guide](https://github.com/slopdam/slopdam/blob/main/CONTRIBUTING.md) (DCO sign-off), [code of conduct](https://github.com/slopdam/slopdam/blob/main/CODE_OF_CONDUCT.md) and [security policy](https://github.com/slopdam/slopdam/blob/main/SECURITY.md).

```bash
cd js
npm install
npm test          # builds, then runs the conformance suite and API tests
```

## License

[MIT](https://github.com/slopdam/slopdam/blob/main/LICENSE)
