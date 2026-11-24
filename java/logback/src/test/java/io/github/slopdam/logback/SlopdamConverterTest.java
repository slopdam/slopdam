// SPDX-License-Identifier: MIT
package io.github.slopdam.logback;

import static org.junit.jupiter.api.Assertions.assertTrue;

import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.LoggerContext;
import ch.qos.logback.classic.encoder.PatternLayoutEncoder;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.OutputStreamAppender;
import ch.qos.logback.core.pattern.DynamicConverter;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import java.util.function.Supplier;
import org.junit.jupiter.api.Test;

class SlopdamConverterTest {
  private static OutputStreamAppender<ILoggingEvent> appender(LoggerContext ctx, String pattern, ByteArrayOutputStream out) {
    PatternLayoutEncoder encoder = new PatternLayoutEncoder();
    encoder.setContext(ctx);
    encoder.setPattern(pattern);
    encoder.start();
    OutputStreamAppender<ILoggingEvent> a = new OutputStreamAppender<>();
    a.setContext(ctx);
    a.setEncoder(encoder);
    a.setOutputStream(out);
    a.start();
    return a;
  }

  @Test
  void profilePerAppender() {
    LoggerContext ctx = new LoggerContext();
    ctx.setMDCAdapter(new ch.qos.logback.classic.util.LogbackMDCAdapter()); // as a configured context has
    // what <conversionRule conversionWord="slopdam" .../> registers
    Map<String, Supplier<DynamicConverter>> rules = new HashMap<>();
    rules.put("slopdam", SlopdamConverter::new);
    ctx.putObject(ch.qos.logback.core.CoreConstants.PATTERN_RULE_REGISTRY_FOR_SUPPLIERS, rules);
    ByteArrayOutputStream console = new ByteArrayOutputStream();
    ByteArrayOutputStream file = new ByteArrayOutputStream();
    Logger log = ctx.getLogger("test");
    log.addAppender(appender(ctx, "%slopdam%n", console));
    log.addAppender(appender(ctx, "%level %slopdam{dev}%n", file));

    log.info("✅ **Saved** {} rows — done!", 3);
    log.error("❌ 업로드 실패 ㅡ 재시도", new RuntimeException("boom — original"));

    String c = console.toString(StandardCharsets.UTF_8);
    String f = file.toString(StandardCharsets.UTF_8);
    assertTrue(c.startsWith("Saved 3 rows: done!\n업로드 실패: 재시도\n"), c);
    assertTrue(f.startsWith("INFO [OK] Saved 3 rows - done!\nERROR 업로드 실패 - 재시도\n"), f);
    // Logback appends the stack trace itself; slopdam never touches it.
    assertTrue(c.contains("java.lang.RuntimeException: boom — original"), c);
  }
}
