// SPDX-License-Identifier: MIT
/** Shape of slopdam's spec/rules.json (spec_version 1). */

export type Profile = "reader" | "dev";
export type Level = "basic" | "strong" | "strict";

export type ActionSpec =
  | { kind: "replace"; value: string }
  | { kind: "report" }
  | { kind: "function"; name: string };

export interface RuleSpec {
  id: string;
  level: Level;
  description: string;
  pattern: string;
  flags: string[];
  actions: Partial<Record<Profile, ActionSpec>>;
}

export interface RulesSpec {
  spec_version: number;
  profiles: Profile[];
  levels: Level[];
  dash_inline: Record<string, string>;
  default_dash_inline: string;
  protected_spans: string;
  charsets: {
    hyphens: string;
    dashes: string;
    hangul_eu: string;
    box_lines: string;
    emoji: string;
    status: Record<string, string>;
    hangul_choseong: string;
    han_kana: string;
  };
  dash_word_before: string;
  dash_word_after: string;
  tidy: { scope: "changed_lines"; multi_space: string; quote_space: string; max_passes: number };
  status_redundant_at: Record<string, string>;
  rules: RuleSpec[];
}
