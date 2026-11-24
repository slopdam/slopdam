<p align="center">
  <img src="https://raw.githubusercontent.com/slopdam/slopdam/main/docs/assets/logo.png" alt="slopdam logo: tangled lines held back by a dam, straight lines flowing out" width="140">
</p>

<h1 align="center">slopdam for Java</h1>

<p align="center"><i>The Java port of <a href="https://github.com/slopdam/slopdam">slopdam</a>: em dashes, emoji, separator lines and markdown stay out of your logs.</i></p>

<p align="center"><b>English</b> | <a href="https://github.com/slopdam/slopdam/blob/main/java/README.ko.md">한국어</a></p>

<p align="center">
  <a href="https://github.com/slopdam/slopdam/actions/workflows/ci.yml"><img src="https://github.com/slopdam/slopdam/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/slopdam/slopdam/blob/main/spec/README.md"><img src="https://img.shields.io/badge/spec-v1%20conformance%20tested-informational.svg" alt="Spec v1: conformance tested"></a>
  <a href="https://github.com/slopdam/slopdam/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
</p>

`slopdam` removes the traces AI coding tools leave in log messages and console output: em dashes and look-alike lines (including the Korean `ㅡ`), decorative emoji, separator lines, markdown bold, curly quotes and invisible characters. It gives exactly the same output as the Python, JavaScript and Go packages, because all of them are tested against the same [conformance cases](https://github.com/slopdam/slopdam/blob/main/spec/README.md).

```
input : ✅ **Saved** — 3 rows processed 🎉
reader: Saved: 3 rows processed
dev   : [OK] Saved - 3 rows processed
```

- `reader` (default): plain text for people, such as CLI messages, alerts and reports.
- `dev`: grep-friendly text for log files and collectors. Status emoji become `[OK]`, `[FAIL]` and `[WARN]` instead of disappearing.

## Modules

| Artifact | What it is | Dependencies |
|---|---|---|
| `io.github.slopdam:slopdam` | `Sanitizer`: clean text, list findings | none |
| `io.github.slopdam:slopdam-logback` | `%slopdam` for Logback patterns | Logback (yours) |
| `io.github.slopdam:slopdam-log4j2` | `%slopdam` for Log4j 2 patterns | Log4j 2 (yours) |

Java 11 or later. The first release to Maven Central is on the way; until then, build with `mvn install` in `java/`.

## Use

```java
import io.github.slopdam.Sanitizer;
import io.github.slopdam.Slopdam;

Slopdam.clean("✅ **Saved** — 3 rows 🎉");                 // "Saved: 3 rows"
Slopdam.clean("✅ **저장 완료** ㅡ 3건 처리했습니다! 🎉");    // "저장 완료: 3건 처리했습니다."

Sanitizer dev = Sanitizer.builder().profile("dev").build();
dev.clean("✅ Upload done — 3 files");                      // "[OK] Upload done - 3 files"
dev.clean("❌ Upload failed", Sanitizer.ERROR);             // "Upload failed" (the level already says it)
dev.findings("log.info(\"🚀 Started — ok\")");             // emoji.pictograph 🚀 @10:13, dash.run — @20:23
```

The builder takes `profile` (`"reader"`, `"dev"`), `level` (`"basic"`, `"strong"`, `"strict"`), `disable` (rule IDs or groups such as `"emoji"`) and `dashInline` (`"colon"`, `"comma"`, `"hyphen"`, `"space"`). A `Sanitizer` is immutable and thread-safe. Findings use UTF-16 offsets into the input. URLs, inline code, `key=value` values and file paths are never changed, and cleaning twice gives the same result as cleaning once.

### Logback

```xml
<conversionRule conversionWord="slopdam" class="io.github.slopdam.logback.SlopdamConverter"/>

<appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
  <encoder><pattern>%slopdam%n</pattern></encoder>                      <!-- Saved 3 rows: done! -->
</appender>
<appender name="FILE" class="ch.qos.logback.core.FileAppender">
  <file>app.log</file>
  <encoder><pattern>%level %slopdam{dev}%n</pattern></encoder>          <!-- INFO [OK] Saved 3 rows - done! -->
</appender>
```

### Log4j 2

```xml
<Console name="Console"><PatternLayout pattern="%slopdam%n"/></Console>
<File name="File" fileName="app.log"><PatternLayout pattern="%level %slopdam{dev}%n"/></File>
```

In both, `%slopdam` takes the place of `%msg`, with options `{profile}` or `{profile, level}`. Each appender can use its own profile, the logging event itself is not changed, and stack traces are left as they are. Log4j finds the converter on the class path.

## How it stays in step with Python

The rules are not rewritten by hand. The build packages the repository's [spec/rules.json](https://github.com/slopdam/slopdam/blob/main/spec/README.md) into the jar; its patterns are translated from Python's regular expression dialect when the class loads (Unicode `\w`, `\s` and `\b`, and Python's `^` and `$`), and only the four context-dependent actions are written in Java. Every pull request runs the conformance cases against Python, JavaScript, Go and Java. On 20,000 random inputs, Java and Python gave identical results.

## Roadmap

Part of slopdam milestone 0.6 ([roadmap](https://github.com/slopdam/slopdam/blob/main/ROADMAP.md)), with the Go module.

## Contributing

A rule change is made once, in the Python reference and `spec/`, with conformance cases; the next build here picks it up. Contributions follow the slopdam [contribution guide](https://github.com/slopdam/slopdam/blob/main/CONTRIBUTING.md) (DCO sign-off), [code of conduct](https://github.com/slopdam/slopdam/blob/main/CODE_OF_CONDUCT.md) and [security policy](https://github.com/slopdam/slopdam/blob/main/SECURITY.md).

```bash
cd java
mvn test
```

## License

[MIT](https://github.com/slopdam/slopdam/blob/main/LICENSE)
