// SPDX-License-Identifier: MIT
package io.github.slopdam;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import java.util.stream.Collectors;
import org.junit.jupiter.api.Test;

class ApiTest {
  @Test
  void cleanWithOptions() {
    assertEquals("Saved: 3 rows", Slopdam.clean("✅ **Saved** — 3 rows 🎉"));
    assertEquals("저장 완료: 3건 처리했습니다.", Slopdam.clean("✅ **저장 완료** ㅡ 3건 처리했습니다! 🎉"));
    Sanitizer dev = Sanitizer.builder().profile("dev").build();
    assertEquals("[OK] Upload done - 3 files", dev.clean("✅ Upload done — 3 files"));
    assertEquals("Upload failed", dev.clean("❌ Upload failed", Sanitizer.ERROR));
    assertEquals("완료, 다음", Sanitizer.builder().dashInline("comma").build().clean("완료 ㅡ 다음"));
    assertEquals("✅ 완료: 다음", Sanitizer.builder().disable("emoji").build().clean("✅ 완료 ㅡ 다음"));
    assertEquals(1, Sanitizer.SPEC_VERSION);
  }

  @Test
  void invalidOptions() {
    assertThrows(IllegalArgumentException.class, () -> Sanitizer.builder().profile("nope").build());
    assertThrows(IllegalArgumentException.class, () -> Sanitizer.builder().level("max").build());
    assertThrows(IllegalArgumentException.class, () -> Sanitizer.builder().dashInline("semicolon").build());
  }

  @Test
  void findingsPointIntoTheInput() {
    String text = "log.info(\"✅ **Saved** 3 rows — done! 🎉\")";
    List<Finding> found = Sanitizer.builder().build().findings(text);
    assertEquals(
        List.of("emoji.pictograph ✅ ''", "md.emphasis **Saved** 'Saved'", "dash.run — ': '", "emoji.pictograph 🎉 ''"),
        found.stream().map(f -> f.ruleId() + " " + f.text() + " '" + f.fix().orElse("?") + "'").collect(Collectors.toList()));
    for (Finding f : found) assertEquals(f.text(), text.substring(f.start(), f.end()).strip());
    Finding chatty = Sanitizer.builder().build().findings("Let's go").get(0);
    assertTrue(chatty.fix().isEmpty());
  }
}
