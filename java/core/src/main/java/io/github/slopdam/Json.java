// SPDX-License-Identifier: MIT
package io.github.slopdam;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** A small JSON reader for the spec files, so the library needs nothing outside the JDK. */
final class Json {
  private final String s;
  private int i;

  private Json(String s) {
    this.s = s;
  }

  /** Objects become {@code Map<String, Object>}, arrays {@code List<Object>}, numbers {@code Double}. */
  static Object parse(String text) {
    Json p = new Json(text);
    Object v = p.value();
    p.space();
    if (p.i != p.s.length()) throw p.error("trailing characters");
    return v;
  }

  private IllegalArgumentException error(String what) {
    return new IllegalArgumentException("slopdam: bad JSON at " + i + ": " + what);
  }

  private void space() {
    while (i < s.length() && " \t\r\n".indexOf(s.charAt(i)) >= 0) i++;
  }

  private Object value() {
    space();
    if (i >= s.length()) throw error("unexpected end");
    char c = s.charAt(i);
    switch (c) {
      case '{': return object();
      case '[': return array();
      case '"': return string();
      case 't': return literal("true", Boolean.TRUE);
      case 'f': return literal("false", Boolean.FALSE);
      case 'n': return literal("null", null);
      default: return number();
    }
  }

  private Object literal(String word, Object v) {
    if (!s.startsWith(word, i)) throw error("expected " + word);
    i += word.length();
    return v;
  }

  private Map<String, Object> object() {
    Map<String, Object> m = new LinkedHashMap<>();
    i++;
    space();
    if (s.charAt(i) == '}') {
      i++;
      return m;
    }
    while (true) {
      space();
      String k = string();
      space();
      if (s.charAt(i++) != ':') throw error("expected :");
      m.put(k, value());
      space();
      char c = s.charAt(i++);
      if (c == '}') return m;
      if (c != ',') throw error("expected , or }");
    }
  }

  private List<Object> array() {
    List<Object> a = new ArrayList<>();
    i++;
    space();
    if (s.charAt(i) == ']') {
      i++;
      return a;
    }
    while (true) {
      a.add(value());
      space();
      char c = s.charAt(i++);
      if (c == ']') return a;
      if (c != ',') throw error("expected , or ]");
    }
  }

  private String string() {
    if (s.charAt(i) != '"') throw error("expected string");
    StringBuilder out = new StringBuilder();
    i++;
    while (true) {
      char c = s.charAt(i++);
      if (c == '"') return out.toString();
      if (c != '\\') {
        out.append(c);
        continue;
      }
      char e = s.charAt(i++);
      switch (e) {
        case 'n': out.append('\n'); break;
        case 't': out.append('\t'); break;
        case 'r': out.append('\r'); break;
        case 'b': out.append('\b'); break;
        case 'f': out.append('\f'); break;
        case 'u':
          out.append((char) Integer.parseInt(s.substring(i, i + 4), 16));
          i += 4;
          break;
        default: out.append(e);
      }
    }
  }

  private Double number() {
    int start = i;
    while (i < s.length() && "+-0123456789.eE".indexOf(s.charAt(i)) >= 0) i++;
    if (start == i) throw error("unexpected character");
    return Double.valueOf(s.substring(start, i));
  }
}
