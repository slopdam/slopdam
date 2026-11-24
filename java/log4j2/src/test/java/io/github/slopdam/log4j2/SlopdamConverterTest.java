// SPDX-License-Identifier: MIT
package io.github.slopdam.log4j2;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.apache.logging.log4j.Level;
import org.apache.logging.log4j.core.LogEvent;
import org.apache.logging.log4j.core.impl.Log4jLogEvent;
import org.apache.logging.log4j.core.layout.PatternLayout;
import org.apache.logging.log4j.message.ParameterizedMessage;
import org.junit.jupiter.api.Test;

class SlopdamConverterTest {
  private static LogEvent event(Level level, String format, Object... args) {
    return Log4jLogEvent.newBuilder().setLevel(level).setLoggerName("test")
        .setMessage(new ParameterizedMessage(format, args)).build();
  }

  @Test
  void profilePerLayout() {
    // Log4j finds %slopdam through the plugin index the annotation processor writes.
    PatternLayout console = PatternLayout.newBuilder().withPattern("%slopdam").build();
    PatternLayout file = PatternLayout.newBuilder().withPattern("%level %slopdam{dev}").build();

    LogEvent info = event(Level.INFO, "✅ **Saved** {} rows — done!", 3);
    LogEvent error = event(Level.ERROR, "❌ 업로드 실패 ㅡ 재시도");
    assertEquals("Saved 3 rows: done!", console.toSerializable(info));
    assertEquals("업로드 실패: 재시도", console.toSerializable(error));
    assertEquals("INFO [OK] Saved 3 rows - done!", file.toSerializable(info));
    assertEquals("ERROR 업로드 실패 - 재시도", file.toSerializable(error));
  }
}
