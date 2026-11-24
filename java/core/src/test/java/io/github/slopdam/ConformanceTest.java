// SPDX-License-Identifier: MIT
package io.github.slopdam;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;
import org.junit.jupiter.api.DynamicTest;
import org.junit.jupiter.api.TestFactory;

/** Every case of the repository's spec/conformance.json, for both profiles. */
class ConformanceTest {
  @SuppressWarnings("unchecked")
  @TestFactory
  Stream<DynamicTest> conformance() throws Exception {
    Map<String, Object> doc = (Map<String, Object>) Json.parse(Files.readString(Path.of("../../spec/conformance.json")));
    List<DynamicTest> tests = new ArrayList<>();
    for (Object g : (List<Object>) doc.get("groups")) {
      Map<String, Object> group = (Map<String, Object>) g;
      List<Object> cases = (List<Object>) group.get("cases");
      for (int i = 0; i < cases.size(); i++) {
        Map<String, Object> c = (Map<String, Object>) cases.get(i);
        Map<String, Object> o = (Map<String, Object>) c.getOrDefault("options", Map.of());
        for (String profile : List.of("reader", "dev")) {
          Sanitizer.Builder b = Sanitizer.builder().profile(profile);
          if (o.containsKey("level")) b.level((String) o.get("level"));
          if (o.containsKey("dash_inline")) b.dashInline((String) o.get("dash_inline"));
          Sanitizer s = b.build();
          int level = o.containsKey("log_level") ? Sanitizer.level((String) o.get("log_level")) : Sanitizer.NONE;
          String input = (String) c.get("input");
          String want = (String) c.get(profile);
          tests.add(DynamicTest.dynamicTest(group.get("id") + "/" + i + "/" + profile, () -> {
            assertEquals(want, s.clean(input, level), "clean");
            assertEquals(want, s.clean(want, level), "idempotent");
          }));
        }
      }
    }
    if (tests.size() < 200) throw new AssertionError("only " + tests.size() + " conformance checks");
    return tests.stream();
  }
}
