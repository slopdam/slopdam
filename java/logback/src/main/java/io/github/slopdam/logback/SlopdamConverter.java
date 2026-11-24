// SPDX-License-Identifier: MIT
package io.github.slopdam.logback;

import ch.qos.logback.classic.Level;
import ch.qos.logback.classic.pattern.ClassicConverter;
import ch.qos.logback.classic.spi.ILoggingEvent;
import io.github.slopdam.Sanitizer;
import java.util.List;

/**
 * The log message with AI traces removed. Register it, then use {@code %slopdam} in place of
 * {@code %msg}, with an optional profile per appender:
 *
 * <pre>{@code
 * <conversionRule conversionWord="slopdam" class="io.github.slopdam.logback.SlopdamConverter"/>
 * <appender name="CONSOLE" ...><encoder><pattern>%slopdam%n</pattern></encoder></appender>
 * <appender name="FILE" ...><encoder><pattern>%level %slopdam{dev}%n</pattern></encoder></appender>
 * }</pre>
 *
 * Options: profile (reader or dev), then level (basic, strong or strict). The logging event
 * itself is not changed, so other appenders see the original message.
 */
public class SlopdamConverter extends ClassicConverter {
  private Sanitizer sanitizer = Sanitizer.builder().build();

  @Override
  public void start() {
    List<String> options = getOptionList();
    Sanitizer.Builder b = Sanitizer.builder();
    if (options != null && !options.isEmpty() && !options.get(0).isEmpty()) b.profile(options.get(0).trim());
    if (options != null && options.size() > 1) b.level(options.get(1).trim());
    try {
      sanitizer = b.build();
    } catch (IllegalArgumentException e) {
      addError(e.getMessage());
      return;
    }
    super.start();
  }

  @Override
  public String convert(ILoggingEvent event) {
    return sanitizer.clean(event.getFormattedMessage(), level(event.getLevel()));
  }

  static int level(Level level) {
    if (level.isGreaterOrEqual(Level.ERROR)) return Sanitizer.ERROR;
    if (level.isGreaterOrEqual(Level.WARN)) return Sanitizer.WARNING;
    if (level.isGreaterOrEqual(Level.INFO)) return Sanitizer.INFO;
    return Sanitizer.DEBUG;
  }
}
