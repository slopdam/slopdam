// SPDX-License-Identifier: MIT
package io.github.slopdam;

/** Shortcuts with the default options (reader profile, basic level). */
public final class Slopdam {
  private Slopdam() {}

  private static final class Default {
    static final Sanitizer SANITIZER = Sanitizer.builder().build();
  }

  /** Removes AI traces from text: {@code clean("✅ **Saved** — 3 rows 🎉")} is "Saved: 3 rows". */
  public static String clean(String text) {
    return Default.SANITIZER.clean(text);
  }
}
