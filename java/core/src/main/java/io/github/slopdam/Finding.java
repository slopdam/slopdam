// SPDX-License-Identifier: MIT
package io.github.slopdam;

import java.util.Objects;
import java.util.Optional;

/** One trace {@link Sanitizer#clean(String)} would change. Offsets are UTF-16 indexes into the input. */
public final class Finding {
  final String ruleId;
  final String description;
  final int start;
  final int end;
  final String text;
  final String fix;

  Finding(String ruleId, String description, int start, int end, String text, String fix) {
    this.ruleId = ruleId;
    this.description = description;
    this.start = start;
    this.end = end;
    this.text = text;
    this.fix = fix;
  }

  public String ruleId() {
    return ruleId;
  }

  public String description() {
    return description;
  }

  public int start() {
    return start;
  }

  public int end() {
    return end;
  }

  public String text() {
    return text;
  }

  /** The replacement, or empty when the rule only reports. */
  public Optional<String> fix() {
    return Optional.ofNullable(fix);
  }

  @Override
  public String toString() {
    return ruleId + " " + text + " -> " + (fix == null ? "<report>" : "'" + fix + "'") + " @" + start + ":" + end;
  }

  @Override
  public boolean equals(Object o) {
    if (!(o instanceof Finding)) return false;
    Finding f = (Finding) o;
    return start == f.start && end == f.end && ruleId.equals(f.ruleId) && text.equals(f.text) && Objects.equals(fix, f.fix);
  }

  @Override
  public int hashCode() {
    return Objects.hash(ruleId, start, end, text, fix);
  }
}
