// SPDX-License-Identifier: MIT
/**
 * winston integration: a format that cleans info.message.
 *
 *   import winston from "winston";
 *   import { slopdamWinston } from "@slopdam/core/winston";
 *
 *   winston.createLogger({
 *     transports: [
 *       new winston.transports.Console({ format: winston.format.combine(slopdamWinston(), winston.format.simple()) }),
 *       new winston.transports.File({ filename: "app.log",
 *         format: winston.format.combine(slopdamWinston({ profile: "dev" }), winston.format.json()) }),
 *     ],
 *   });
 *
 * Put it after format.splat() and before colorize(), printf(), simple() or json(). winston gives
 * each transport its own copy of the log entry, so transports can use different profiles. An
 * entry whose message was only a separator line is dropped, unless it carries a stack trace.
 * winston is not imported here: any object with a transform() method is a winston format.
 */
import { Sanitizer, type SanitizerOptions } from "./sanitizer.js";

export interface WinstonInfo {
  level: string;
  message: unknown;
  stack?: unknown;
  [key: string | symbol]: unknown;
}

export interface SlopdamFormat {
  options: SanitizerOptions;
  transform(info: WinstonInfo): WinstonInfo | false;
}

// winston's npm levels, as the names slopdam understands. Custom levels pass through as they are.
const LEVELS: Record<string, string> = { error: "error", warn: "warning", info: "info", http: "info", verbose: "debug", debug: "debug", silly: "debug" };

export function slopdamWinston(options: SanitizerOptions = {}): SlopdamFormat {
  const sanitizer = new Sanitizer(options);
  return {
    options,
    transform(info) {
      if (typeof info.message !== "string") return info;
      const cleaned = sanitizer.clean(info.message, LEVELS[info.level] ?? info.level);
      if (!cleaned && !info.stack) return false; // only a separator line
      info.message = cleaned;
      return info;
    },
  };
}
