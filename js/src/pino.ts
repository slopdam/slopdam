// SPDX-License-Identifier: MIT
/**
 * pino integration. Spread the options into pino():
 *
 *   import pino from "pino";
 *   import { slopdamPino } from "@slopdam/core/pino";
 *   const log = pino({ ...slopdamPino({ profile: "dev" }) });
 *
 * The message string of every log call is cleaned before pino serializes it. A call whose
 * message was only a separator line, with no object or error, is dropped. Objects and
 * errors are never changed. pino is not imported here.
 */
import { Sanitizer, type SanitizerOptions } from "./sanitizer.js";

export interface SlopdamPinoOptions extends SanitizerOptions {
  /** Merge with hooks you already pass to pino. */
  hooks?: { logMethod?: LogMethodHook };
}

type LogFn = (...args: unknown[]) => void;
type LogMethodHook = (this: unknown, args: unknown[], method: LogFn, level: number) => void;

/** pino's numbers (10 trace ... 60 fatal) as the level names slopdam understands. */
function levelName(level: number): string {
  if (level >= 60) return "critical";
  if (level >= 50) return "error";
  if (level >= 40) return "warning";
  if (level >= 30) return "info";
  return "debug";
}

export function slopdamPino(options: SlopdamPinoOptions = {}): { hooks: { logMethod: LogMethodHook } } {
  const { hooks, ...sanitizerOptions } = options;
  const sanitizer = new Sanitizer(sanitizerOptions);
  const next = hooks?.logMethod;

  function logMethod(this: unknown, args: unknown[], method: LogFn, level: number): void {
    // log([mergingObject], [message], [...interpolationValues])
    const at = typeof args[0] === "string" ? 0 : typeof args[1] === "string" ? 1 : -1;
    if (at >= 0) {
      const cleaned = sanitizer.clean(args[at] as string, levelName(level));
      if (!cleaned && at === 0 && args.length === 1) return; // only a separator line
      args = [...args];
      args[at] = cleaned;
    }
    if (next) next.call(this, args, method, level);
    else method.apply(this, args);
  }

  return { hooks: { logMethod } };
}
