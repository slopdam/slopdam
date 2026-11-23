// SPDX-License-Identifier: MIT
// Every case in slopdam's spec/conformance.json, for both profiles, in the ESM and CommonJS builds.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { describe, test } from "node:test";
import * as esm from "../dist/esm/index.js";

const cjs = createRequire(import.meta.url)("../dist/cjs/index.js");
const spec = JSON.parse(readFileSync(new URL("../../spec/conformance.json", import.meta.url), "utf8"));

for (const [name, lib] of [["esm", esm], ["cjs", cjs]]) {
  describe(`conformance (${name})`, () => {
    for (const group of spec.groups) {
      describe(group.id, () => {
        group.cases.forEach((c, i) => {
          for (const profile of ["reader", "dev"]) {
            test(`${i} ${profile} ${JSON.stringify(c.input).slice(0, 40)}`, () => {
              const o = c.options ?? {};
              const s = new lib.Sanitizer({ profile, level: o.level, dashInline: o.dash_inline });
              assert.equal(s.clean(c.input, o.log_level), c[profile]);
              assert.equal(s.clean(c[profile], o.log_level), c[profile], "idempotent");
            });
          }
        });
      });
    }
  });
}
