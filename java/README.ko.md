<p align="center">
  <img src="https://raw.githubusercontent.com/slopdam/slopdam/main/docs/assets/logo.png" alt="slopdam logo: tangled lines held back by a dam, straight lines flowing out" width="140">
</p>

<h1 align="center">Java용 slopdam</h1>

<p align="center"><i><a href="https://github.com/slopdam/slopdam">slopdam</a>의 Java 구현: 긴 대시, 이모지, 구분선, 마크다운이 로그에 남지 않게 합니다.</i></p>

<p align="center"><a href="https://github.com/slopdam/slopdam/blob/main/java/README.md">English</a> | <b>한국어</b></p>

<p align="center">
  <a href="https://github.com/slopdam/slopdam/actions/workflows/ci.yml"><img src="https://github.com/slopdam/slopdam/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/slopdam/slopdam/blob/main/spec/README.ko.md"><img src="https://img.shields.io/badge/spec-v1%20conformance%20tested-informational.svg" alt="명세 v1: 적합성 테스트"></a>
  <a href="https://github.com/slopdam/slopdam/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="라이선스: MIT"></a>
</p>

`slopdam`은 AI 코딩 도구가 로그 메시지와 콘솔 출력에 남기는 흔적을 걷어냅니다. 긴 대시와 그와 닮은 선(한글 `ㅡ` 포함), 장식 이모지, 구분선, 마크다운 굵은 글씨, 둥근 따옴표, 보이지 않는 문자가 대상입니다. Python, JavaScript, Go 패키지와 같은 [적합성 사례](https://github.com/slopdam/slopdam/blob/main/spec/README.ko.md)로 테스트하므로 결과가 똑같습니다.

```
입력  : ✅ **저장 완료** ㅡ 2024–2025년 데이터 3건 처리했습니다! 🎉
reader: 저장 완료: 2024~2025년 데이터 3건 처리했습니다.
dev   : [OK] 저장 완료 - 2024-2025년 데이터 3건 처리했습니다!
```

- `reader`(기본): 사람이 읽는 글. CLI 메시지, 알림, 보고서에 씁니다.
- `dev`: 검색하기 쉬운 글. 로그 파일과 수집기에 씁니다. 상태 이모지는 지우지 않고 `[OK]`, `[FAIL]`, `[WARN]`으로 바꿉니다.

## 모듈

| 아티팩트 | 내용 | 의존성 |
|---|---|---|
| `io.github.slopdam:slopdam` | `Sanitizer`: 텍스트 정리, 결과 목록 | 없음 |
| `io.github.slopdam:slopdam-logback` | Logback 패턴용 `%slopdam` | Logback(사용 중인 것) |
| `io.github.slopdam:slopdam-log4j2` | Log4j 2 패턴용 `%slopdam` | Log4j 2(사용 중인 것) |

Java 11 이상에서 동작하며, Maven Central에서 받습니다.

```xml
<dependency>
  <groupId>io.github.slopdam</groupId>
  <artifactId>slopdam</artifactId>            <!-- 또는 slopdam-logback, slopdam-log4j2 -->
  <version>0.1.0</version>
</dependency>
```

## 사용법

```java
import io.github.slopdam.Sanitizer;
import io.github.slopdam.Slopdam;

Slopdam.clean("✅ **저장 완료** ㅡ 3건 처리했습니다! 🎉");    // "저장 완료: 3건 처리했습니다."
Slopdam.clean("✅ **Saved** — 3 rows 🎉");                 // "Saved: 3 rows"

Sanitizer dev = Sanitizer.builder().profile("dev").build();
dev.clean("✅ 업로드 완료 ㅡ 3개 파일");                     // "[OK] 업로드 완료 - 3개 파일"
dev.clean("❌ 업로드 실패", Sanitizer.ERROR);                // "업로드 실패" (로그 레벨이 이미 실패를 말함)
dev.findings("log.info(\"🚀 Started — ok\")");             // emoji.pictograph 🚀 @10:13, dash.run — @20:23
```

빌더는 `profile`(`"reader"`, `"dev"`), `level`(`"basic"`, `"strong"`, `"strict"`), `disable`(`"emoji"` 같은 규칙 ID나 군), `dashInline`(`"colon"`, `"comma"`, `"hyphen"`, `"space"`)을 받습니다. `Sanitizer`는 변경할 수 없고 여러 스레드에서 함께 써도 안전합니다. 결과 위치는 입력 안의 UTF-16 위치입니다. URL, 인라인 코드, `key=value`의 값, 파일 경로는 바꾸지 않고, 두 번 정리해도 한 번 정리한 결과와 같습니다.

### Logback

```xml
<conversionRule conversionWord="slopdam" class="io.github.slopdam.logback.SlopdamConverter"/>

<appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
  <encoder><pattern>%slopdam%n</pattern></encoder>                      <!-- 저장 완료: 3건 처리했습니다. -->
</appender>
<appender name="FILE" class="ch.qos.logback.core.FileAppender">
  <file>app.log</file>
  <encoder><pattern>%level %slopdam{dev}%n</pattern></encoder>          <!-- INFO [OK] 저장 완료 - 3건 처리했습니다! -->
</appender>
```

### Log4j 2

```xml
<Console name="Console"><PatternLayout pattern="%slopdam%n"/></Console>
<File name="File" fileName="app.log"><PatternLayout pattern="%level %slopdam{dev}%n"/></File>
```

두 경우 모두 `%msg` 자리에 `%slopdam`을 쓰고, 옵션은 `{profile}` 또는 `{profile, level}`입니다. 어펜더마다 다른 프로필을 쓸 수 있고, 로그 이벤트 자체는 바꾸지 않으며, 스택 트레이스는 그대로 둡니다. Log4j는 클래스 경로에서 변환기를 찾습니다.

## Python과 같은 결과를 내는 방법

규칙을 손으로 다시 쓰지 않습니다. 빌드할 때 저장소의 [spec/rules.json](https://github.com/slopdam/slopdam/blob/main/spec/README.ko.md)을 jar에 넣고, 그 안의 패턴은 클래스를 불러올 때 Python 정규식 문법에서 변환됩니다(유니코드 `\w`, `\s`, `\b`와 Python의 `^`, `$`). 문맥에 따라 바꾸는 동작 네 가지만 Java로 작성했습니다. PR마다 Python, JavaScript, Go, Java에 같은 적합성 사례를 실행합니다. 무작위 입력 20,000개에서 Java와 Python의 결과가 같았습니다.

## 로드맵

Go 모듈과 함께 slopdam 0.6 마일스톤의 일부입니다([로드맵](https://github.com/slopdam/slopdam/blob/main/ROADMAP.ko.md)).

## 기여

규칙 변경은 Python 기준 구현과 `spec/`에서 적합성 사례와 함께 한 번만 합니다. 여기서는 다음 빌드에서 반영됩니다. 기여는 slopdam의 [기여 안내](https://github.com/slopdam/slopdam/blob/main/CONTRIBUTING.ko.md)(DCO 서명), [행동 강령](https://github.com/slopdam/slopdam/blob/main/CODE_OF_CONDUCT.ko.md), [보안 정책](https://github.com/slopdam/slopdam/blob/main/SECURITY.ko.md)을 따릅니다.

```bash
cd java
mvn test
```

## 라이선스

[MIT](https://github.com/slopdam/slopdam/blob/main/LICENSE)
