// SPDX-License-Identifier: MIT
package io.github.slopdam;

import java.util.regex.Pattern;

/**
 * Translates the Python {@code re} patterns in the spec into {@link Pattern} syntax with
 * Python's meaning, as js/src/pyregex.ts does for JavaScript:
 *
 * <ul>
 *   <li>{@code \w \s \d \b}: Unicode-aware, as in Python 3, written as explicit classes
 *   <li>{@code \A \Z}: start and end of the whole string
 *   <li>{@code \UXXXXXXXX}: {@code \x{X}}
 *   <li>{@code .}: any character except a line feed
 *   <li>{@code ^ $}: Python's anchors; with the multiline flag only a line feed separates lines
 *   <li>{@code (?P<name>}: {@code (?<name>}
 * </ul>
 */
final class PyRegex {
  static final String WORD = "\\p{L}\\p{N}_";
  static final String SPACE =
      "\\t-\\r\\x1c-\\x20\\x85\\xa0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000";
  private static final String BOUNDARY =
      "(?:(?<=[" + WORD + "])(?![" + WORD + "])|(?<![" + WORD + "])(?=[" + WORD + "]))";
  private static final String SYNTAX = "^$\\.*+?()[]{}|/";

  private PyRegex() {}

  static Pattern compile(String pattern, boolean multiline) {
    return Pattern.compile(translate(pattern, multiline));
  }

  static String translate(String src, boolean multiline) {
    StringBuilder out = new StringBuilder();
    boolean inClass = false;
    int i = 0;
    while (i < src.length()) {
      char ch = src.charAt(i);
      if (ch == '\\') {
        if (i + 1 >= src.length()) throw unsupported("a trailing backslash", src);
        char n = src.charAt(i + 1);
        i += 2;
        switch (n) {
          case 'w': out.append(inClass ? WORD : "[" + WORD + "]"); continue;
          case 's': out.append(inClass ? SPACE : "[" + SPACE + "]"); continue;
          case 'd': out.append("\\p{Nd}"); continue;
          case 'W': case 'S': case 'D': case 'B': case 'A': case 'Z':
            if (inClass) throw unsupported("\\" + n + " in a class", src);
            switch (n) {
              case 'W': out.append("[^" + WORD + "]"); break;
              case 'S': out.append("[^" + SPACE + "]"); break;
              case 'D': out.append("\\P{Nd}"); break;
              case 'B': out.append("(?!" + BOUNDARY + ")"); break;
              case 'A': out.append("(?<![\\s\\S])"); break;
              default: out.append("(?![\\s\\S])"); break;
            }
            continue;
          case 'b': out.append(inClass ? "\\x08" : BOUNDARY); continue;
          case 'U':
            out.append("\\x{").append(src, i, i + 8).append('}');
            i += 8;
            continue;
          case 'u':
            out.append("\\u").append(src, i, i + 4);
            i += 4;
            continue;
          case 'x':
            out.append("\\x").append(src, i, i + 2);
            i += 2;
            continue;
          case 'n': case 't': case 'r': case 'f': case 'v': case '0':
            out.append('\\').append(n);
            continue;
          default:
            break;
        }
        if (n >= '1' && n <= '9') out.append('\\').append(n);
        else if (Character.isLetterOrDigit(n)) throw unsupported("\\" + n, src);
        else if (SYNTAX.indexOf(n) >= 0 || (inClass && n == '-')) out.append('\\').append(n);
        else out.append(n);
        continue;
      }
      if (inClass) {
        if (ch == ']') inClass = false;
        out.append(ch);
        i++;
        continue;
      }
      if (ch == '[') {
        inClass = true;
        out.append(ch);
        i++;
        if (i < src.length() && src.charAt(i) == '^') out.append(src.charAt(i++));
        if (i < src.length() && src.charAt(i) == ']') {
          out.append("\\]");
          i++;
        }
      } else if (ch == '.') {
        out.append("[^\\n]");
        i++;
      } else if (ch == '^') {
        out.append(multiline ? "(?<![^\\n])" : "(?<![\\s\\S])");
        i++;
      } else if (ch == '$') {
        out.append(multiline ? "(?![^\\n])" : "(?=\\n?(?![\\s\\S]))");
        i++;
      } else if (src.startsWith("(?P<", i)) {
        out.append("(?<");
        i += 4;
      } else if (src.startsWith("(?P=", i) || src.startsWith("(?#", i)) {
        throw unsupported("a named back reference or comment", src);
      } else {
        out.append(ch);
        i++;
      }
    }
    return out.toString();
  }

  private static IllegalArgumentException unsupported(String what, String src) {
    return new IllegalArgumentException("slopdam: cannot translate " + what + " in /" + src + "/");
  }

  // Python's character tests: str.isalnum() is letters and numbers (L*, N*); str.isdigit() is
  // Nd plus the characters below; whitespace is the SPACE set.
  private static final Pattern DIGIT = Pattern.compile(
      "[\\p{Nd}\\x{B2}-\\x{B3}\\x{B9}\\x{1369}-\\x{1371}\\x{19DA}\\x{2070}\\x{2074}-\\x{2079}"
          + "\\x{2080}-\\x{2089}\\x{2460}-\\x{2468}\\x{2474}-\\x{247C}\\x{2488}-\\x{2490}\\x{24EA}"
          + "\\x{24F5}-\\x{24FD}\\x{24FF}\\x{2776}-\\x{277E}\\x{2780}-\\x{2788}\\x{278A}-\\x{2792}"
          + "\\x{10A40}-\\x{10A43}\\x{10E60}-\\x{10E68}\\x{11052}-\\x{1105A}\\x{1F100}-\\x{1F10A}]");
  private static final Pattern ALNUM = Pattern.compile("[\\p{L}\\p{N}]");
  private static final Pattern IS_SPACE = Pattern.compile("[" + SPACE + "]");

  static boolean isAlnum(int cp) {
    return ALNUM.matcher(new String(Character.toChars(cp))).matches();
  }

  static boolean isDigit(int cp) {
    return DIGIT.matcher(new String(Character.toChars(cp))).matches();
  }

  static boolean isSpace(char c) {
    return IS_SPACE.matcher(String.valueOf(c)).matches();
  }

  /** Python's str.strip(). */
  static String strip(String s) {
    int a = 0, b = s.length();
    while (a < b && isSpace(s.charAt(a))) a++;
    while (b > a && isSpace(s.charAt(b - 1))) b--;
    return s.substring(a, b);
  }

  /** Python's str.rstrip(). */
  static String rstrip(String s) {
    int b = s.length();
    while (b > 0 && isSpace(s.charAt(b - 1))) b--;
    return s.substring(0, b);
  }

  /** Python's str.splitlines(). */
  static java.util.List<String> splitlines(String s) {
    java.util.List<String> lines = new java.util.ArrayList<>();
    int start = 0;
    for (int i = 0; i < s.length(); i++) {
      char c = s.charAt(i);
      if (c == '\r') {
        lines.add(s.substring(start, i));
        if (i + 1 < s.length() && s.charAt(i + 1) == '\n') i++;
        start = i + 1;
      } else if (c == '\n' || c == 0x0b || c == 0x0c || c == 0x1c || c == 0x1d || c == 0x1e
          || c == 0x85 || c == 0x2028 || c == 0x2029) {
        lines.add(s.substring(start, i));
        start = i + 1;
      }
    }
    if (start < s.length()) lines.add(s.substring(start));
    return lines;
  }
}
