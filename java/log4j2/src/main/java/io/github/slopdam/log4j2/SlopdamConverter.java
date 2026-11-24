// SPDX-License-Identifier: MIT
package io.github.slopdam.log4j2;

import io.github.slopdam.Sanitizer;
import org.apache.logging.log4j.Level;
import org.apache.logging.log4j.core.LogEvent;
import org.apache.logging.log4j.core.config.plugins.Plugin;
import org.apache.logging.log4j.core.pattern.ConverterKeys;
import org.apache.logging.log4j.core.pattern.LogEventPatternConverter;
import org.apache.logging.log4j.core.pattern.PatternConverter;

/**
 * The log message with AI traces removed: {@code %slopdam} in a PatternLayout, in place of
 * {@code %msg}, with an optional profile per appender:
 *
 * <pre>{@code
 * <Console name="Console"><PatternLayout pattern="%slopdam%n"/></Console>
 * <File name="File" fileName="app.log"><PatternLayout pattern="%level %slopdam{dev}%n"/></File>
 * }</pre>
 *
 * Options: profile (reader or dev), then level (basic, strong or strict). Log4j finds the
 * plugin on the class path; the event itself is not changed.
 */
@Plugin(name = "SlopdamConverter", category = PatternConverter.CATEGORY)
@ConverterKeys({"slopdam"})
public final class SlopdamConverter extends LogEventPatternConverter {
  private final Sanitizer sanitizer;

  private SlopdamConverter(Sanitizer sanitizer) {
    super("slopdam", "slopdam");
    this.sanitizer = sanitizer;
  }

  /** Called by Log4j with the options in braces. */
  public static SlopdamConverter newInstance(String[] options) {
    Sanitizer.Builder b = Sanitizer.builder();
    if (options != null && options.length > 0 && !options[0].isEmpty()) b.profile(options[0].trim());
    if (options != null && options.length > 1) b.level(options[1].trim());
    return new SlopdamConverter(b.build());
  }

  @Override
  public void format(LogEvent event, StringBuilder out) {
    out.append(sanitizer.clean(event.getMessage().getFormattedMessage(), level(event.getLevel())));
  }

  static int level(Level level) {
    if (level.isMoreSpecificThan(Level.FATAL)) return Sanitizer.CRITICAL;
    if (level.isMoreSpecificThan(Level.ERROR)) return Sanitizer.ERROR;
    if (level.isMoreSpecificThan(Level.WARN)) return Sanitizer.WARNING;
    if (level.isMoreSpecificThan(Level.INFO)) return Sanitizer.INFO;
    return Sanitizer.DEBUG;
  }
}
