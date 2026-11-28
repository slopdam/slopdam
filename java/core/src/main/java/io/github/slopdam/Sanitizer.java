// SPDX-License-Identifier: MIT
package io.github.slopdam;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Strips the traces AI coding tools leave in log messages: em dashes and the Korean ㅡ, emoji,
 * separator lines, markdown bold, curly quotes and invisible characters.
 *
 * <p>The Java port of <a href="https://github.com/slopdam/slopdam">slopdam</a>. Rules, character
 * sets and their order come from the repository's language-neutral spec ({@code rules.json},
 * packaged with the classes); only the four context-dependent actions are written here,
 * following spec/README.md step by step. Instances are immutable and thread-safe.
 *
 * <pre>{@code
 * Slopdam.clean("✅ **Saved** — 3 rows 🎉");                    // "Saved: 3 rows"
 * Sanitizer dev = Sanitizer.builder().profile("dev").build();
 * dev.clean("✅ Upload done — 3 files");                        // "[OK] Upload done - 3 files"
 * dev.clean("❌ Upload failed", Sanitizer.ERROR);                // "Upload failed"
 * }</pre>
 */
public final class Sanitizer {
  /** Log levels on Python's logging scale, to drop a dev status tag the level already says. */
  public static final int NONE = -1, DEBUG = 10, INFO = 20, WARNING = 30, ERROR = 40, CRITICAL = 50;

  // ---- the spec -------------------------------------------------------------------------------
  private static final Map<String, Object> SPEC = loadSpec();
  private static final List<String> PROFILES = strings(SPEC.get("profiles"));
  private static final List<String> LEVELS = strings(SPEC.get("levels"));
  private static final Map<String, Object> DASH_INLINE = map(SPEC.get("dash_inline"));
  private static final Pattern PROTECT = PyRegex.compile((String) SPEC.get("protected_spans"), false);
  private static final Pattern MULTI_SPACE = PyRegex.compile((String) map(SPEC.get("tidy")).get("multi_space"), false);
  private static final Pattern QUOTE_SPACE = PyRegex.compile((String) map(SPEC.get("tidy")).get("quote_space"), false);
  private static final int MAX_PASSES = ((Double) map(SPEC.get("tidy")).get("max_passes")).intValue();
  private static final String WORD_BEFORE = (String) SPEC.get("dash_word_before");
  private static final String WORD_AFTER = (String) SPEC.get("dash_word_after");
  private static final Pattern CHOSEONG =
      Pattern.compile("[" + map(SPEC.get("charsets")).get("hangul_choseong") + "]");
  private static final Pattern HAN_KANA =
      Pattern.compile("[" + map(SPEC.get("charsets")).get("han_kana") + "]");
  private static final Map<Integer, String> STATUS_OF = new HashMap<>();
  private static final Map<String, Object> REDUNDANT = map(SPEC.get("status_redundant_at"));
  private static final List<Map<String, Object>> RULE_SPECS = new ArrayList<>();
  private static final List<Pattern> RULE_PATTERNS = new ArrayList<>();

  /** The version of slopdam's spec this library implements. */
  public static final int SPEC_VERSION = ((Double) SPEC.get("spec_version")).intValue();

  static {
    map(map(SPEC.get("charsets")).get("status")).forEach((tag, chars) ->
        ((String) chars).codePoints().forEach(cp -> STATUS_OF.put(cp, tag)));
    for (Object r : (List<?>) SPEC.get("rules")) {
      Map<String, Object> rule = map(r);
      RULE_SPECS.add(rule);
      RULE_PATTERNS.add(PyRegex.compile((String) rule.get("pattern"), strings(rule.get("flags")).contains("multiline")));
    }
  }

  private static Map<String, Object> loadSpec() {
    try (InputStream in = Sanitizer.class.getResourceAsStream("rules.json")) {
      if (in == null) throw new IllegalStateException("slopdam: rules.json is missing from the jar");
      return map(Json.parse(new String(in.readAllBytes(), StandardCharsets.UTF_8)));
    } catch (IOException e) {
      throw new IllegalStateException("slopdam: cannot read rules.json", e);
    }
  }

  @SuppressWarnings("unchecked")
  private static Map<String, Object> map(Object o) {
    return (Map<String, Object>) o;
  }

  @SuppressWarnings("unchecked")
  private static List<String> strings(Object o) {
    return o == null ? Collections.emptyList() : (List<String>) o;
  }

  // ---- options --------------------------------------------------------------------------------
  /** Options for a Sanitizer. The defaults are reader, basic and colon. */
  public static final class Builder {
    private String profile = "reader";
    private String level = "basic";
    private List<String> disable = Collections.emptyList();
    private String dashInline = (String) SPEC.get("default_dash_inline");

    private Builder() {}

    /** "reader" (plain text for people) or "dev" (grep-friendly text for tools). */
    public Builder profile(String profile) {
      this.profile = profile;
      return this;
    }

    /** "basic", "strong" (also removes filler words) or "strict" (also reports any non-ASCII symbol). */
    public Builder level(String level) {
      this.level = level;
      return this;
    }

    /** Rule IDs or groups to turn off, such as "emoji" or "dash.run". */
    public Builder disable(String... ids) {
      this.disable = Arrays.asList(ids);
      return this;
    }

    /** Rule IDs or groups to turn off. */
    public Builder disable(Collection<String> ids) {
      this.disable = new ArrayList<>(ids);
      return this;
    }

    /** What an inline dash becomes in reader: "colon", "comma", "hyphen" or "space". */
    public Builder dashInline(String dashInline) {
      this.dashInline = dashInline;
      return this;
    }

    /** @throws IllegalArgumentException for an unknown profile, level or dash style */
    public Sanitizer build() {
      return new Sanitizer(this);
    }
  }

  public static Builder builder() {
    return new Builder();
  }

  // ---- the engine -----------------------------------------------------------------------------
  private interface Action {
    String apply(Matcher m, String s, Context ctx);
  }

  private static final class Context {
    final String profile;
    final String dashInline;
    final int levelno;

    Context(String profile, String dashInline, int levelno) {
      this.profile = profile;
      this.dashInline = dashInline;
      this.levelno = levelno;
    }
  }

  private static final class Rule {
    final String id;
    final String description;
    final Pattern pattern;
    final Action action; // null: report only

    Rule(String id, String description, Pattern pattern, Action action) {
      this.id = id;
      this.description = description;
      this.pattern = pattern;
      this.action = action;
    }
  }

  private static final int PUA = 0xF0000;

  private static boolean isPua(int cp) {
    return cp >= 0xF0000 && cp <= 0xFFFFD;
  }

  private static boolean wordish(int cp, String extra) {
    return PyRegex.isAlnum(cp) || extra.indexOf(cp) >= 0 || isPua(cp);
  }

  /** Python logging level names to numbers. */
  public static int level(String name) {
    switch (name.toUpperCase(Locale.ROOT)) {
      case "CRITICAL": case "FATAL": return CRITICAL;
      case "ERROR": return ERROR;
      case "WARNING": case "WARN": return WARNING;
      case "INFO": return INFO;
      case "DEBUG": case "TRACE": return DEBUG;
      default: return NONE;
    }
  }

  private static final Map<String, Action> FUNCTIONS = new HashMap<>();

  static {
    // Chinese and Japanese write this punctuation full width, so a line with kana or CJK
    // ideographs keeps it; elsewhere it becomes ASCII.
    FUNCTIONS.put("fullwidth", (m, s, ctx) -> {
      int end = s.indexOf('\n', m.start());
      if (HAN_KANA.matcher(s.substring(s.lastIndexOf('\n', m.start() - 1) + 1, end < 0 ? s.length() : end)).find()) {
        return m.group();
      }
      StringBuilder out = new StringBuilder();
      for (char c : m.group().toCharArray()) out.append(c >= 0xFF01 && c <= 0xFF5E ? (char) (c - 0xFEE0) : c);
      return out.toString();
    });
    FUNCTIONS.put("unwrap", (m, s, ctx) -> m.group(1) == null ? "" : m.group(1));
    // Inside a double-quoted string a plain quote would end it, so it is escaped.
    FUNCTIONS.put("quote_double", (m, s, ctx) -> {
      int start = s.lastIndexOf('\n', m.start() - 1) + 1, n = 0;
      for (int j = start; j < m.start(); j++) {
        if (s.charAt(j) == '"' && (j == start || s.charAt(j - 1) != '\\')) n++;
      }
      return n % 2 == 1 ? "\\\"" : "\"";
    });
    FUNCTIONS.put("status_tag", (m, s, ctx) -> {
      String tag = STATUS_OF.get(m.group(1).codePointAt(0));
      Object at = REDUNDANT.get(tag);
      if (ctx.levelno != NONE && at != null && ctx.levelno >= level((String) at)) return "";
      return tag + " ";
    });
    FUNCTIONS.put("dash_run", (m, s, ctx) -> {
      int start = m.start(), end = m.end();
      String lead = m.group(1), run = m.group(2), trail = m.group(3);
      if (run.charAt(0) == 'ᅳ' && start + lead.length() > 0) {
        int before = s.codePointBefore(start + lead.length());
        if (CHOSEONG.matcher(new String(Character.toChars(before))).matches()) return m.group(); // old-style syllable
      }
      int prev = start > 0 ? s.codePointBefore(start) : '\n';
      int next = end < s.length() ? s.codePointAt(end) : '\n';
      boolean inner = wordish(prev, WORD_BEFORE) && wordish(next, WORD_AFTER);
      if (run.codePointCount(0, run.length()) >= 2) return inner ? " " : ""; // separator: ㅡㅡ, ──
      if (PyRegex.isDigit(prev) && PyRegex.isDigit(next)) return ctx.profile.equals("reader") ? "~" : "-";
      int lineStart = start == 0 ? 0 : s.lastIndexOf('\n', start - 1) + 1;
      if (PyRegex.strip(s.substring(lineStart, start)).isEmpty() && !trail.isEmpty()) return lead + "- ";
      if (inner) return ctx.profile.equals("reader") ? ctx.dashInline : " - ";
      return "";
    });
  }

  /** Python's Match.expand for the replacement strings in the spec (\1, \g<1>, \g<name>). */
  private static String expand(String template, Matcher m) {
    StringBuilder out = new StringBuilder();
    for (int i = 0; i < template.length(); i++) {
      char c = template.charAt(i);
      if (c != '\\' || i + 1 >= template.length()) {
        out.append(c);
        continue;
      }
      char n = template.charAt(i + 1);
      if (Character.isDigit(n)) {
        int j = i + 1;
        while (j < template.length() && Character.isDigit(template.charAt(j))) j++;
        String g = m.group(Integer.parseInt(template.substring(i + 1, j)));
        out.append(g == null ? "" : g);
        i = j - 1;
      } else if (n == 'g' && i + 2 < template.length() && template.charAt(i + 2) == '<') {
        int close = template.indexOf('>', i + 3);
        String name = template.substring(i + 3, close);
        String g = name.chars().allMatch(Character::isDigit) ? m.group(Integer.parseInt(name)) : m.group(name);
        out.append(g == null ? "" : g);
        i = close;
      } else if (n == 'n') {
        out.append('\n');
        i++;
      } else if (n == 't') {
        out.append('\t');
        i++;
      } else if (n == '\\') {
        out.append('\\');
        i++;
      } else {
        out.append(c);
      }
    }
    return out.toString();
  }

  private interface Replacer {
    String apply(Matcher m);
  }

  /** Python's re.sub with a function: every non-overlapping match, left to right. */
  private static String sub(Pattern p, String s, Replacer fn) {
    Matcher m = p.matcher(s);
    if (!m.find()) return s;
    StringBuilder out = new StringBuilder();
    int last = 0;
    do {
      out.append(s, last, m.start()).append(fn.apply(m));
      last = m.end();
    } while (m.find());
    return out.append(s, last, s.length()).toString();
  }

  private final String profile;
  private final String dashInline;
  private final List<Rule> rules = new ArrayList<>();

  private Sanitizer(Builder b) {
    if (!PROFILES.contains(b.profile)) throw new IllegalArgumentException("slopdam: unknown profile " + b.profile + ", expected one of " + PROFILES);
    if (!LEVELS.contains(b.level)) throw new IllegalArgumentException("slopdam: unknown level " + b.level + ", expected one of " + LEVELS);
    Object inline = DASH_INLINE.get(b.dashInline);
    if (inline == null) throw new IllegalArgumentException("slopdam: unknown dash inline style " + b.dashInline);
    profile = b.profile;
    dashInline = (String) inline;
    for (int i = 0; i < RULE_SPECS.size(); i++) {
      Map<String, Object> r = RULE_SPECS.get(i);
      String id = (String) r.get("id");
      if (LEVELS.indexOf((String) r.get("level")) > LEVELS.indexOf(b.level)) continue;
      if (b.disable.stream().anyMatch(d -> id.equals(d) || id.startsWith(d + "."))) continue;
      Map<String, Object> a = map(map(r.get("actions")).get(profile));
      if (a == null) continue;
      Action action;
      switch ((String) a.get("kind")) {
        case "replace":
          String value = (String) a.get("value");
          action = (m, s, ctx) -> expand(value, m);
          break;
        case "function":
          action = FUNCTIONS.get((String) a.get("name"));
          if (action == null) throw new IllegalStateException("slopdam: spec function " + a.get("name") + " is not implemented");
          break;
        default:
          action = null;
      }
      rules.add(new Rule(id, (String) r.get("description"), RULE_PATTERNS.get(i), action));
    }
  }

  private String apply(String text, Context ctx) {
    for (Rule r : rules) {
      if (r.action == null) continue;
      String current = text;
      text = sub(r.pattern, current, m -> r.action.apply(m, current, ctx));
    }
    return text;
  }

  /** Removes AI traces from text. */
  public String clean(String text) {
    return clean(text, NONE);
  }

  /**
   * Removes AI traces from a log message at the given level ({@link #ERROR}, {@link #WARNING},
   * ...), so that dev drops a [FAIL] or [WARN] tag the level already says.
   */
  public String clean(String text, int level) {
    Context ctx = new Context(profile, dashInline, level);
    text = String.join("\n", PyRegex.splitlines(text));
    for (int pass = 0; pass < MAX_PASSES; pass++) {
      String cleaned = cleanOnce(text, ctx);
      if (cleaned.equals(text)) break;
      text = cleaned;
    }
    return text;
  }

  private String cleanOnce(String text, Context ctx) {
    List<String> saved = new ArrayList<>();
    String masked = sub(PROTECT, text, m -> {
      String kept = m.group();
      String code = m.group("code");
      // reader drops the backticks, but only when the code itself is clean.
      if (code != null && profile.equals("reader") && apply(code, ctx).equals(code)) kept = code;
      saved.add(kept);
      return new String(Character.toChars(PUA + saved.size() - 1));
    });
    // No rule adds or removes a line break, so lines compare one to one. Only lines a rule
    // changed are tidied, while protected spans are still masked.
    String[] before = masked.split("\n", -1);
    String[] after = apply(masked, ctx).split("\n", -1);
    for (int i = 0; i < after.length; i++) {
      if (i < before.length && after[i].equals(before[i])) continue;
      after[i] = sub(QUOTE_SPACE, sub(MULTI_SPACE, after[i], m -> " "), m -> "");
    }
    String out = String.join("\n", after);
    StringBuilder restored = new StringBuilder();
    out.codePoints().forEach(cp -> {
      if (isPua(cp) && cp - PUA < saved.size()) restored.append(saved.get(cp - PUA));
      else restored.appendCodePoint(cp);
    });
    List<String> lines = new ArrayList<>();
    for (String line : PyRegex.splitlines(restored.toString())) {
      line = lines.isEmpty() ? PyRegex.strip(line) : PyRegex.rstrip(line);
      if (!line.isEmpty()) lines.add(line);
    }
    return String.join("\n", lines);
  }

  /**
   * What {@link #clean(String)} would change, in one pass and without tidying, with offsets as
   * UTF-16 indexes into text.
   */
  public List<Finding> findings(String text) {
    Context ctx = new Context(profile, dashInline, NONE);
    StringBuilder work = new StringBuilder();
    List<int[]> spans = new ArrayList<>(); // per char of work: its span in text
    int last = 0;
    Matcher pm = PROTECT.matcher(text);
    while (pm.find()) {
      for (int i = last; i < pm.start(); i++) {
        work.append(text.charAt(i));
        spans.add(new int[] {i, i + 1});
      }
      String placeholder = new String(Character.toChars(PUA));
      work.append(placeholder);
      for (int k = 0; k < placeholder.length(); k++) spans.add(new int[] {pm.start(), pm.end()});
      last = pm.end();
    }
    for (int i = last; i < text.length(); i++) {
      work.append(text.charAt(i));
      spans.add(new int[] {i, i + 1});
    }

    List<Finding> found = new ArrayList<>();
    String cur = work.toString();
    for (Rule r : rules) {
      StringBuilder pieces = new StringBuilder();
      List<int[]> newSpans = new ArrayList<>();
      int pos = 0, start = 0, end = 0;
      boolean changed = false;
      Matcher m = r.pattern.matcher(cur);
      while (m.find()) {
        String fix = r.action == null ? null : r.action.apply(m, cur, ctx);
        String matched = m.group();
        if (!matched.isEmpty()) {
          start = spans.get(m.start())[0];
          end = spans.get(m.end() - 1)[1];
          if (!PyRegex.strip(matched).isEmpty() && !matched.equals(fix)) {
            found.add(new Finding(r.id, r.description, start, end, PyRegex.strip(text.substring(start, end)), fix));
          }
        }
        if (fix == null || fix.equals(matched)) continue;
        changed = true;
        pieces.append(cur, pos, m.start());
        newSpans.addAll(spans.subList(pos, m.start()));
        pieces.append(fix);
        for (int k = 0; k < fix.length(); k++) newSpans.add(new int[] {start, end});
        pos = m.end();
      }
      if (changed) {
        pieces.append(cur, pos, cur.length());
        newSpans.addAll(spans.subList(pos, spans.size()));
        cur = pieces.toString();
        spans = newSpans;
      }
    }
    found.sort((a, b) -> a.start != b.start ? Integer.compare(a.start, b.start) : Integer.compare(b.end, a.end));
    List<Finding> kept = new ArrayList<>();
    for (Finding f : found) {
      // drop hits nested inside an earlier one (e.g. emoji.status + emoji.pictograph)
      if (kept.stream().noneMatch(k -> k.start <= f.start && f.end <= k.end)) kept.add(f);
    }
    return kept;
  }
}
