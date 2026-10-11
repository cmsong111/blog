---
title: "Docker Compose를 활용한 로컬 개발 환경 구축 (Spring Boot, PostgreSQL, Redis)"
description: "신규 입사자 온보딩부터 로컬 통합 테스트까지, Spring Boot에 필요한 PostgreSQL과 Redis를 Docker Compose v2로 표준화하고 안전하게 격리·구축하는 실무 템플릿과 노하우를 다룹니다."
date: 2026-06-04 12:00:00 +0900
tags: [docker, docker-compose, spring-boot, postgresql, redis, local-development]
mermaid: true
---

> 팀원마다 다른 DB 버전과 설정으로 인한 "내 로컬에서는 되는데요?" 문제를 해결하기 위해, Docker Compose v2(`compose.yaml`)를 활용하여 Spring Boot, PostgreSQL, Redis 로컬 개발 환경을 단 한 번의 명령어로 표준화하고 안전하게 격리·구축하는 실무 전략을 정리합니다.

---

## 1. "내 로컬에선 되는데요": 로컬 개발 환경의 파편화 문제

팀에 새로운 동료가 합류하거나 기존 프로젝트를 새로운 머신에 세팅할 때 흔히 겪는 광경이 있습니다.

- 어떤 팀원은 Homebrew로 설치한 PostgreSQL 15를 사용하고, 다른 팀원은 과거 프로젝트에서 쓰던 17 버전을 그대로 띄워 둡니다.
- 버전 간 사소한 SQL 문법 차이(예: JSON 연산자, UUID 생성 함수)나 기본 콜레이션(Collation) 차이로 인해 로컬 테스트 결과가 달라집니다.
- 로컬 머신 백그라운드에 이미 실행 중인 Redis 데몬과 포트(6379)가 충돌하여 애플리케이션 기동이 실패합니다.
- 설정 파일(`application.yml`)에 제각각 다른 로컬 계정 정보와 비밀번호를 하드코딩해 두었다가 실수로 커밋하는 사고가 일어납니다.

이러한 **환경 불일치(Environment Drift)**는 온보딩 시간을 늘릴 뿐 아니라, 코드 리뷰와 로컬 디버깅 비용을 크게 증가시킵니다. 인프라를 코드(IaC)로 관리하는 철학은 클라우드 프로덕션뿐만 아니라 **로컬 개발 환경**에서도 동일하게 적용되어야 합니다.

Docker Compose는 다중 컨테이너 환경을 선언적 명세서로 정의하여, 신규 입사자도 `docker compose up -d` 명령어 단 한 줄로 10초 만에 프로덕션과 동일한 버전의 격리된 인프라를 구축할 수 있게 해줍니다.

---

## 2. 전체 아키텍처 및 네트워크 통신 구조

로컬 개발 환경에서는 보통 IDE(IntelliJ 등)에서 Spring Boot 애플리케이션을 직접 실행하고, 외부 의존성인 PostgreSQL과 Redis만 컨테이너로 격리하여 띄우는 구성을 선호합니다. 코드 수정 시 빠른 핫 리로딩(Live Reload)과 IDE 디버거를 그대로 활용하기 위해서입니다.

```mermaid
flowchart TD
    subgraph Host["Host Machine (macOS / Linux / Windows)"]
        Dev["개발자 IDE (IntelliJ IDEA)"]
        Spring["Spring Boot App (Local Port: 8080)"]
        Dev -->|디버깅 & 실행| Spring
    end

    subgraph DockerEnv["Docker Compose (local-network)"]
        direction TB
        PG["PostgreSQL 17 Container\n(local-postgres:5432)"]
        RD["Redis 7 Container\n(local-redis:6379)"]
        VolPG[("postgres_data\n(Named Volume)")]
        VolRD[("redis_data\n(Named Volume)")]

        PG --- VolPG
        RD --- VolRD
    end

    Spring -->|localhost:5432\n(JDBC URL)| PG
    Spring -->|localhost:6379\n(Lettuce Driver)| RD

    classDef host fill:#e8f4fd,stroke:#2b7de9,stroke-width:2px;
    classDef docker fill:#eef9f0,stroke:#2e7d32,stroke-width:2px;
    class Host host;
    class DockerEnv docker;
```

컨테이너들은 Docker 브리지 네트워크(`local-network`) 내부에서 안전하게 격리되며, 호스트 머신의 Spring Boot 애플리케이션이 접근할 수 있도록 지정된 포트(5432, 6379)로 포트 포워딩됩니다. 또한 컨테이너가 내려가더라도 개발 데이터가 유실되지 않도록 **네임드 볼륨(Named Volume)**으로 데이터를 영속화합니다.

---

## 3. 환경변수 분리와 유연한 포트 관리 (`.env`)

Compose 파일을 작성할 때 접속 계정이나 포트 번호를 직접 하드코딩하는 것은 피해야 합니다. 다른 프로세스와의 포트 충돌을 피하기 위해 포트를 변경해야 하거나, 개발자마다 민감한 정보를 다르게 관리해야 할 수 있기 때문입니다.

Compose v2는 프로젝트 루트에 위치한 `.env` 파일을 자동으로 읽어 환경변수로 치환합니다.

### 3.1 `.env.example` 템플릿 정의

저장소(Git)에는 실제 비밀번호가 포함된 `.env` 대신, 기본값이 정의된 템플릿 파일(`.env.example`)을 커밋합니다.

```ini
# PostgreSQL Configuration
POSTGRES_HOST_PORT=5432
POSTGRES_DB=app_dev
POSTGRES_USER=app_user
POSTGRES_PASSWORD=local_secret_password!

# Redis Configuration
REDIS_HOST_PORT=6379
REDIS_PASSWORD=local_redis_secret!
```

> [!WARNING]
> `.env` 파일은 실제 동작에 쓰이는 민감 정보를 담을 수 있으므로 반드시 `.gitignore`에 등록해야 합니다. 신규 작업자는 `cp .env.example .env` 명령어로 복사한 후 로컬 환경에 맞게 조정하도록 유도합니다.
{: .prompt-warning }

---

## 4. 실전 `compose.yaml` 표준 구성

Compose 스펙이 정식 표준화되면서 구형 하이픈 표기법(`docker-compose.yml`) 대신 **`compose.yaml`**이 공식 권장 파일명으로 채택되었습니다. 최신 Compose v2 사양에 맞춘 완성형 파일입니다.

```yaml
services:
  postgres:
    image: postgres:17-alpine
    container_name: local-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-app_dev}
      POSTGRES_USER: ${POSTGRES_USER:-app_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-local_secret_password!}
      TZ: Asia/Seoul
    ports:
      - "${POSTGRES_HOST_PORT:-5432}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - local-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-app_user} -d ${POSTGRES_DB:-app_dev}"]
      interval: 5s
      timeout: 5s
      retries: 5
      start_period: 10s

  redis:
    image: redis:7-alpine
    container_name: local-redis
    restart: unless-stopped
    command: ["redis-server", "--requirepass", "${REDIS_PASSWORD:-local_redis_secret!}", "--appendonly", "yes"]
    ports:
      - "${REDIS_HOST_PORT:-6379}:6379"
    volumes:
      - redis_data:/data
    networks:
      - local-network
    healthcheck:
      test: ["CMD-SHELL", "redis-cli -a ${REDIS_PASSWORD:-local_redis_secret!} ping | grep PONG"]
      interval: 5s
      timeout: 3s
      retries: 5
      start_period: 5s

networks:
  local-network:
    driver: bridge

volumes:
  postgres_data:
    name: local_postgres_data
  redis_data:
    name: local_redis_data
```

### 핵심 설계 포인트 분석

1. **변수 기본값(`:-`) 문법**:
   `${POSTGRES_DB:-app_dev}`처럼 콜론-하이픈 문법을 사용하면, 로컬 머신에 `.env` 파일이 없거나 환경변수가 비어 있더라도 안정적으로 기본값을 적용하여 컨테이너가 즉시 뜹니다.

2. **Alpine 경량 베이스 이미지**:
   `postgres:17-alpine`과 `redis:7-alpine`을 사용하여 이미지 다운로드 속도를 단축하고 로컬 디스크 낭비를 줄였습니다.

3. **신뢰성 있는 헬스체크(Healthcheck)**:
   - PostgreSQL: 단순히 포트 오픈 여부만 확인하는 것이 아니라, 내부 유틸리티인 `pg_isready`를 사용해 실제 데이터베이스 쿼리 수신 준비가 끝났는지 검증합니다.
   - Redis: `redis-cli ping`에 비밀번호 인증 옵션(`-a`)을 함께 전달하여 인증 상태까지 점검합니다.

4. **네임드 볼륨 네이밍 명시**:
   `volumes.postgres_data.name` 속성을 명시적으로 지정하여, 프로젝트 디렉터리 경로가 변경되어도 볼륨 이름이 일관되게 유지되도록 보장합니다.

---

## 5. Spring Boot `application-local.yml` 연동

Docker 인프라가 준비되었다면, 로컬 프로파일(`local`)에서 동작할 Spring Boot 설정을 맞춥니다.

`src/main/resources/application-local.yml`:

```yaml
spring:
  config:
    activate:
      on-profile: local

  datasource:
    url: jdbc:postgresql://localhost:${POSTGRES_HOST_PORT:5432}/${POSTGRES_DB:app_dev}
    username: ${POSTGRES_USER:app_user}
    password: ${POSTGRES_PASSWORD:local_secret_password!}
    driver-class-name: org.postgresql.Driver
    hikari:
      pool-name: LocalHikariPool
      maximum-pool-size: 10
      minimum-idle: 5
      connection-timeout: 30000

  jpa:
    hibernate:
      ddl-auto: update
    show-sql: true
    properties:
      hibernate:
        format_sql: true
        default_batch_fetch_size: 100

  data:
    redis:
      host: localhost
      port: ${REDIS_HOST_PORT:6379}
      password: ${REDIS_PASSWORD:local_redis_secret!}
      timeout: 3000ms
      lettuce:
        pool:
          max-active: 8
          max-idle: 8
          min-idle: 2
```

> [!TIP]
> Spring Boot 3.1 이상에서는 `spring-boot-docker-compose` 모듈을 의존성에 추가할 수도 있습니다. 이 경우 애플리케이션 시작 시 IDE가 `compose.yaml`을 감지하여 자동으로 컨테이너를 올리고, 데이터소스 URL과 비밀번호를 스프링 컨텍스트에 자동 바인딩(Service Connection)해 주는 편의 기능을 제공합니다.
{: .prompt-tip }

---

## 6. 구동 검증 및 운영 노하우

### 6.1 컨테이너 기동 및 상태 확인

프로젝트 루트에서 다음 명령어를 실행하여 서비스를 백그라운드로 띄웁니다.

```bash
# 1. 환경변수 파일 복사 (최초 1회)
cp .env.example .env

# 2. 백그라운드 모드로 전체 컨테이너 기동
docker compose up -d

# 3. 컨테이너 헬스체크 및 포트 매핑 확인
docker compose ps
```

실행 후 터미널 출력 결과:

```text
NAME             IMAGE                COMMAND                  SERVICE    CREATED          STATUS                    PORTS
local-postgres   postgres:17-alpine   "docker-entrypoint.s…"   postgres   12 seconds ago   Up 11 seconds (healthy)   0.0.0.0:5432->5432/tcp
local-redis      redis:7-alpine       "docker-entrypoint.s…"   redis      12 seconds ago   Up 11 seconds (healthy)   0.0.0.0:6379->6379/tcp
```

`STATUS` 열에 `(healthy)` 표시가 정상적으로 나타나면 애플리케이션이 연결을 맺을 준비가 완료된 것입니다.

---

### 6.2 실무 트러블슈팅 가이드

#### Q1. 로컬에 이미 설치된 PostgreSQL/Redis 때문에 포트가 충돌하는 경우

기존 데몬을 종료하기 곤란한 상황이라면, `compose.yaml`을 수정할 필요 없이 로컬의 `.env` 파일에서 호스트 포트 번호만 변경하면 됩니다.

```ini
# .env 수정 예시
POSTGRES_HOST_PORT=15432
REDIS_HOST_PORT=16379
```

컨테이너 내부 포트(5432, 6379)는 유지된 채 호스트 노출 포트만 변경되므로 Spring Boot 설정과 충돌 없이 공존할 수 있습니다.

#### Q2. 스키마 변경이나 테스트 데이터 오염으로 DB를 완전히 초기화하고 싶을 때

컨테이너를 단순히 재시작하는 것만으로는 네임드 볼륨에 저장된 데이터가 초기화되지 않습니다. 볼륨 삭제 옵션(`-v` 또는 `--volumes`)을 함께 주어 깨끗하게 리셋합니다.

```bash
# 컨테이너 및 네임드 볼륨 완전 삭제
docker compose down -v

# 깨끗한 상태에서 신규 기동
docker compose up -d
```

> [!CAUTION]
> `docker compose down -v`는 네임드 볼륨(`local_postgres_data`, `local_redis_data`)을 디스크에서 영구적으로 삭제합니다. 보존해야 하는 로컬 테스트 데이터가 있다면 사전에 덤프를 백업해 두어야 합니다.
{: .prompt-warning }

---

## 7. 마치며

로컬 인프라를 일관되게 관리하는 것은 개발팀의 기본적인 생산성을 지키는 핵심 발판입니다. 

1. `compose.yaml`을 통해 데이터베이스와 캐시의 메이저 버전을 명시적으로 통일하고,
2. `.env` 파일을 통해 보안과 유연한 포트 매핑을 보장하며,
3. 헬스체크와 네임드 볼륨으로 기동 신뢰성과 데이터 영속성을 확보했습니다.

이제 새로 합류하는 팀원에게 "README에 적힌 Docker Compose 명령어 한 줄 실행하고 Spring Boot를 실행해 보세요"라는 명쾌한 안내만으로 온보딩 과정을 끝마칠 수 있습니다.
