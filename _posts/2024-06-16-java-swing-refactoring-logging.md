---
title: SLF4J 로깅 라이브러리 추가
description: SLF4J 로깅 라이브러리 추가
date: 2024-06-16 12:00:00 +0000
categories: [Refactoring Project, Java-Swing]
tags: [Java, Swing, Refactoring, SLF4J, Logback]
mermaid: true
image:
  path: https://velog.velcdn.com/images/cmsong111/post/24a8b41a-49a7-4813-87f2-fe4b172fa200/image.png
---

기존 자바 스윙 프로젝트에서는 로깅을 위해 System.out.println()을 사용했습니다. 

![System.out Replace 요청사진](https://velog.velcdn.com/images/cmsong111/post/a586053a-01f0-4d67-aefc-481817ed1f4c/image.png)

이는 성능 문제를 일으킬 수 있으며, 로깅 레벨을 조정할 수 없어 유연성이 부족합니다.

따라서 SLF4J와 Logback을 도입하여 로깅을 개선할 필요가 있습니다. 

SLF4J는 다양한 로깅 프레임워크에 대한 추상화를 제공하여 코드의 일관성을 높이고, Logback은 SLF4J의 기본 구현체로서 강력한 기능을 제공합니다.

## SLF4J란?

SLF4J는 Simple Logging Facade for Java의 약자로, 자바 로깅 라이브러리를 추상화한 인터페이스입니다. 

SLF4J에는 5가지 로깅 레벨이 있습니다.

- TRACE
- DEBUG
- INFO
- WARN
- ERROR

이 중에서 TRACE는 가장 상세한 로깅 레벨이고, ERROR는 가장 심각한 로깅 레벨입니다.

SLF4J는 인터페이스로써, 이를 구현해주기 위해 Logback, Log4j, JUL 구현체가 필요합니다. 

이번 프로젝트에서는 **Logback**을 사용하겠습니다.

## SLF4J 로깅 라이브러리 추가

### 1. Maven을 통한 의존성 추가

Maven을 사용하는 경우, `pom.xml` 파일에 아래와 같이 의존성을 추가합니다.

```xml
<dependency>
    <groupId>ch.qos.logback</groupId>
    <artifactId>logback-classic</artifactId>
    <version>1.5.6</version>
</dependency>
<dependency>
    <groupId>ch.qos.logback</groupId>
    <artifactId>logback-core</artifactId>
    <version>1.5.6</version>
</dependency>
<dependency>
    <groupId>org.slf4j</groupId>
    <artifactId>slf4j-api</artifactId>
    <version>2.1.0-alpha1</version>
</dependency>
```

직접 JAR 파일을 추가하는 경우, SLF4J와 Logback의 JAR 파일을 [Maven Central Repository](https://search.maven.org/)에서 다운로드하여 프로젝트의 `lib` 디렉토리에 추가합니다. 

그리고 IDE에서 해당 JAR 파일을 빌드 경로에 추가해야 합니다.

### 2. Logger 객체 생성 및 로깅

#### 2-1. LoggerFactory를 통한 로깅

LoggerFactory를 통해 Logger를 생성하고, 로깅을 합니다.

```java
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class Main {
    private static final Logger logger = LoggerFactory.getLogger(Main.class);

    public static void main(String[] args) {
        logger.info("Hello, World!");
    }
}
```

`실행 결과`

```shell
03:01:10.885 [main] INFO com.example.Main - Hello, World!
```

#### 2-2. @Slf4j 어노테이션을 통한 로깅 (Lombok 사용)

Lombok 라이브러리를 사용하면 `@Slf4j` 어노테이션을 통해 Logger를 생성할 수 있습니다. 

어노테이션을 사용하면, 보다 편리하게 로깅을 할 수 있습니다.

```java
import lombok.extern.slf4j.Slf4j;

@Slf4j
public class Main {
    public static void main(String[] args) {
        log.info("Hello, World!");
    }
}
```

`실행 결과`

```shell
03:01:10.885 [main] INFO com.example.Main - Hello, World!
```

### 3. logback.xml 설정

logback.xml 파일을 통해 로깅 설정을 변경할 수 있습니다. 

기본 세팅에서는 스프링부트에서 보는 로그와 달리 단색으로 출력됩니다.

색상을 추가하기 위해서는 logback.xml 파일을 수정해야 합니다.

logback.xml 파일을 resources 디렉토리에 추가하고, 아래와 같이 설정합니다.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <appender name="STDOUT" class="ch.qos.logback.core.ConsoleAppender">
        <encoder>
            <Pattern>%d %highlight(%-5level) [%thread] %cyan(%logger{15}): %msg%n</Pattern>
        </encoder>
    </appender>

    <root level="trace">
        <appender-ref ref="STDOUT" />
    </root>
</configuration>
```

- `%highlight(%-5level)`은 로깅 레벨을 색상으로 표시합니다.
- `%cyan(%logger{15})`는 로거 이름을 cyan 색상으로 표시합니다.

```java
logger.trace("This is trace log");
logger.debug("This is debug log");
logger.info("This is info log");
logger.warn("This is warn log");
logger.error("This is error log");
```

![로그 색상 설정](https://velog.velcdn.com/images/cmsong111/post/249d26bb-7f70-4570-a221-a2211d916425/image.png)

로그 레벨에 따라 색상이 다르게 표시되는 것을 확인할 수 있습니다.

## 마무리

SLF4J를 사용하면 다음과 같은 이점을 얻을 수 있습니다:

- 성능 문제 해결: System.out.println() 대신 Logger를 사용하여 성능을 개선할 수 있습니다.
- 로깅 레벨 조정: 필요에 따라 로깅 레벨을 쉽게 변경할 수 있습니다.
- 다양한 로깅 프레임워크 지원: SLF4J는 여러 로깅 프레임워크에 대한 추상화를 제공하여 코드의 일관성을 높입니다.
- 유지보수 용이: Logger를 사용하면 출력 결과를 파일 또는 로깅 전용 서버로 전송하는 등 다양한 로깅 설정을 할 수 있습니다.

이번 포스팅에서는 SLF4J 로깅 라이브러리를 추가하는 방법에 대해 알아보았습니다.
