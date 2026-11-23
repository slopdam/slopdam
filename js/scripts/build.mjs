// SPDX-License-Identifier: MIT
// Build ESM and CommonJS output. src/spec.generated.ts is written from ../spec/rules.json
// (the spec in this repository) first.
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";

const tsc = (...args) => execFileSync(process.execPath, ["node_modules/typescript/bin/tsc", ...args], { stdio: "inherit" });

writeFileSync(
  "src/spec.generated.ts",
  "// Generated from ../spec/rules.json by scripts/build.mjs. Do not edit.\n" +
    'import type { RulesSpec } from "./types.js";\n\n' +
    `export const SPEC: RulesSpec = ${readFileSync("../spec/rules.json", "utf8").trim()};\n`,
);
rmSync("dist", { recursive: true, force: true });
tsc("-p", "tsconfig.json");
tsc("-p", "tsconfig.json", "--module", "CommonJS", "--outDir", "dist/cjs");
mkdirSync("dist/cjs", { recursive: true });
writeFileSync("dist/cjs/package.json", JSON.stringify({ type: "commonjs" }) + "\n");
console.log("built dist/esm and dist/cjs");
