---
title: "Spring Boot에서 별도 라이브러리 없이 .env 파일 로드하는 방법"
description: "Spring Boot 내장 spring.config.import로 별도 라이브러리 없이 .env 파일을 로드하는 방법과 프로퍼티 우선순위, 프로덕션 Fail-Fast 구성, 실무 주의사항을 정리합니다."
date: 2024-10-20 12:00:00 +0900
tags: [spring-boot, dotenv, configuration, security, properties]
---

> Spring Boot 2.4부터 도입된 `spring.config.import`를 활용하면 외부 라이브러리나 IDE 플러그인 없이 `.env` 파일을 불러올 수 있습니다. 내부 로딩 원리와 우선순위, 프로덕션 Fail-Fast 구성, 실무 주의사항을 정리합니다.

> 본 문서는 Spring Boot 3.x (Spring Boot 2.4 이상) 기준으로 작성되었습니다.
{: .prompt-info }

## 외부 라이브러리나 IDE 플러그인 대신 내장 기능을 쓰는 이유

로컬 개발에서 DB 비밀번호나 JWT 시크릿, API 키를 관리할 때 `.env` 파일이 편리하지만 Spring Boot는 기본적으로 `.env`를 읽지 않습니다. 이 때문에 `dotenv-java` 같은 라이브러리나 IntelliJ EnvFile 플러그인을 쓰는 경우가 많습니다. 하지만 플러그인은 `./gradlew bootRun` 같은 CLI 실행에서 동작하지 않고, 외부 라이브러리는 버전 업그레이드마다 호환성을 챙겨야 합니다.

| 구분 | `spring.config.import` (내장) | `dotenv-java` 등 | IDE 플러그인 (EnvFile) |
| :--- | :--- | :--- | :--- |
| 의존성 | 불필요 | 라이브러리 추가 | IDE 플러그인 설치 |
| CLI 지원 | 지원 | 지원 | 미지원 |
| 통합 방식 | `Environment` 네이티브 | 별도 초기화 | OS 환경변수 주입 |
| 문법 | Java `.properties` | Shell `.env` | 플러그인별 상이 |

내장 `spring.config.import`는 의존성 없이 IDE와 CLI 실행 환경을 통일합니다. 다만 Shell 변수 치환 같은 `.env` 전용 문법이 꼭 필요하다면 전용 라이브러리가 적합합니다.

## ConfigDataEnvironmentPostProcessor의 내부 동작 원리와 우선순위

애플리케이션 기동 시 `ConfigDataEnvironmentPostProcessor`가 `spring.config.import`를 감지하고 `StandardConfigDataLocationResolver`가 `optional:file:.env[.properties]`를 해석합니다.

- `optional:`: 파일이 없어도 예외를 던지지 않고 넘어갑니다.
- `file:.env`: 파일 시스템에서 `.env`를 탐색합니다.
- `[.properties]`: 확장자가 없는 `.env` 파일을 `PropertiesPropertySourceLoader`가 `.properties` 포맷으로 파싱하도록 힌트를 제공합니다.

파싱된 키-값은 `PropertySource`로 `Environment`에 등록되며, 최종 적용 우선순위는 다음과 같습니다.

1. **OS 환경변수 (`systemEnvironment`)**: Docker `-e`, Kubernetes Secret, CI 환경변수가 최우선입니다.
2. **`.env` 파일**: 임포트된 외부 파일은 자신을 선언한 `application.yml`보다 우선순위가 높습니다.
3. **`application.yml` 기본값**: `${KEY:default}` 폴백 값은 상위 소스에 키가 없을 때만 쓰입니다.

이 구조 덕분에 로컬에서는 `.env`로 값을 덮어쓰고, 운영에서는 `.env` 없이 OS 환경변수만 주입해도 그대로 동작합니다.

## 로컬 개발과 프로덕션 Fail-Fast 설정 구성

안전한 운영을 위해 공통 `application.yml`에는 로컬용 기본값을 두고, `application-prod.yml`에서는 민감 정보의 기본값을 제거해 누락 시 기동 단계에서 즉시 실패(Fail-Fast)하도록 구성합니다.

```yaml
# src/main/resources/application.yml
spring:
  application:
    name: portfolio

  config:
    import: optional:file:.env[.properties]

  profiles:
    default: local

jwt:
  secret: ${JWT_SECRET:local-dev-secret-key-for-testing-only}
  issuer: ${JWT_ISSUER:localhost}
  access-expiry: ${JWT_ACCESS_EXPIRATION:3600}
  refresh-expiry: ${JWT_REFRESH_EXPIRATION:604800}

storage:
  imgbb:
    api-key: ${IMGBB_API_KEY:dummy-api-key}
```

```yaml
# src/main/resources/application-prod.yml
spring:
  datasource:
    url: ${DATABASE_URL}
    username: ${DATABASE_USERNAME}
    password: ${DATABASE_PASSWORD}
    driver-class-name: ${DATABASE_DRIVER:org.postgresql.Driver}

  data:
    redis:
      host: ${REDIS_HOST:localhost}
      port: ${REDIS_PORT:6379}
      database: ${REDIS_DATABASE:0}
      username: ${REDIS_USERNAME:}
      password: ${REDIS_PASSWORD:}

jwt:
  secret: ${JWT_SECRET}
```

`prod` 프로파일에서 `DATABASE_URL`이나 `JWT_SECRET`이 빠지면 더미 값으로 실행되지 않고 `IllegalArgumentException: Could not resolve placeholder` 예외로 기동이 중단됩니다. 또한 팀원과 키 목록을 공유하기 위해 `.env.template`만 Git에 커밋하고 `.env`는 `.gitignore`에 등록합니다.

```properties
# .env.template (Git 커밋)
JWT_SECRET=
IMGBB_API_KEY=
```

```gitignore
# .gitignore
.env
```

```bash
cp .env.template .env
```

## 실무 적용 시 자주 겪는 주의사항

### 1. `optional:` 누락 시 CI/Docker 기동 실패

`optional:` 없이 `file:.env[.properties]`만 적으면 `.env`가 없는 CI나 Docker 환경에서 `ConfigDataLocationNotFoundException`이 발생하며 부팅에 실패합니다. 로컬 전용 파일에는 반드시 `optional:`을 붙여야 합니다.

### 2. Shell `.env`와 Java `.properties`의 따옴표 처리 차이

Shell이나 Node.js `dotenv`는 양옆 따옴표(`"..."`)를 제거하지만, `PropertiesPropertySourceLoader`는 Java `.properties` 규칙을 따라 따옴표를 값의 일부로 포함합니다.

```properties
# 잘못된 예시: 따옴표까지 문자열에 포함됨
JWT_SECRET="my-secret-key"

# 올바른 예시: 따옴표 없이 순수 값만 작성
JWT_SECRET=my-secret-key
```

> 주의: 따옴표가 섞이면 API 401 오류나 JWT 서명 검증 실패로 이어집니다. 백슬래시(`\`) 역시 이스케이프 문자로 해석되므로 `\\`로 작성해야 합니다.
{: .prompt-warning }

### 3. Working Directory 기준 경로 주의

`file:.env`는 프로젝트 루트가 아니라 **JVM 실행 시점의 현재 작업 디렉토리(Working Directory)** 기준입니다. 멀티 모듈 하위 경로나 다른 위치에서 `java -jar`로 실행하면 `.env`를 찾지 못하므로, IDE 작업 디렉토리를 루트로 맞추거나 `optional:file:.env[.properties];optional:file:../.env[.properties]`로 상위 경로를 함께 지정합니다.

## 정리

`spring.config.import: optional:file:.env[.properties]`에 `.env.template` 공유, `.gitignore` 차단, `application-prod.yml`의 Fail-Fast 구성을 결합하면 별도 라이브러리 없이도 로컬 편의성과 운영 보안을 함께 챙길 수 있습니다.

{% linkpreview "https://docs.spring.io/spring-boot/reference/features/external-config.html" %}
