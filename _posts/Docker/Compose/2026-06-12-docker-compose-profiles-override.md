---
title: "Docker Compose Profiles와 Override를 활용한 로컬 개발 환경 분리"
description: "서비스가 비대해진 로컬 개발 환경에서 Docker Compose Profiles와 compose.override.yaml을 활용해 리소스 낭비를 막고 개발자별 맞춤형 환경을 구성하는 실무 전략을 정리합니다."
date: 2026-06-12 12:00:00 +0900
tags: [docker-compose, profiles, compose-override, local-environment, multi-env]
mermaid: true
---

> 마이크로서비스와 인프라 컴포넌트가 늘어날수록 `docker compose up` 한 번에 노트북 팬이 이륙하고 메모리가 고갈되는 문제를 겪게 됩니다. 모든 개발자가 일상적인 API 작업에 Kafka나 모니터링 도구까지 띄울 필요는 없습니다. Compose의 `profiles` 속성과 `compose.override.yaml` 병합 메커니즘을 결합해 가볍고 유연한 로컬 개발 환경을 설계하는 방법을 소개합니다.

---

## 1. 배경: "그냥 `docker compose up` 치면 되잖아요"의 한계

시스템이 성장하면서 단일 서비스 형태였던 아키텍처는 자연스럽게 세분화됩니다. 핵심 도메인 API 외에도 인증 서버, 결제 워커, 비동기 메시지 브로커, 검색 엔진, 모니터링 에이전트까지 로컬 개발 환경에 하나둘씩 추가되기 마련입니다.

초기에는 "신규 입사자도 명령어 한 줄이면 전체 환경이 뜬다"는 장점 때문에 모든 컴포넌트를 단일 `compose.yaml` 파일에 차곡차곡 모아두었습니다. 하지만 인프라 규모가 커지면서 로컬 개발 환경(DX)에서 심각한 병목이 나타나기 시작했습니다.

### 1.1 10개가 넘는 컨테이너와 노트북 팬의 비명

단순히 회원가입 API 로직이나 DB 쿼리 하나를 수정하고 검증하려는데, 터미널에 `docker compose up -d`를 입력하는 순간 다음과 같은 일들이 벌어집니다.

- **컨테이너 폭풍 기동**: PostgreSQL, Redis는 물론이고 Kafka 3개 브로커 노드, Zookeeper/KRaft, Elasticsearch, Logstash, Kibana, Prometheus, Grafana, Mailpit 등 10~15개의 컨테이너가 일제히 CPU와 메모리를 점유합니다.
- **메모리 고갈과 시스템 버벅임**: Docker Desktop(가상머신)에 할당된 16GB 메모리 중 14GB 이상이 순식간에 잠식되며, IntelliJ IDEA의 코드 인덱싱과 Gradle 빌드가 멈칫거리기 시작합니다.
- **배터리 광탈과 소음**: 맥북의 팬이 최대 속도로 회전하며, 외부 미팅이나 카페에서 작업할 때 배터리가 1~2시간 만에 바닥납니다.

### 1.2 "개발자마다 지금 필요한 컴포넌트는 완전히 다르다"

실제 개발 업무를 가만히 들여다보면, 모든 엔지니어가 전체 인프라 스택을 상시 가동할 이유는 전혀 없습니다.

| 개발자 역할 / 현재 작업 | 필수 인프라 | 불필요한 인프라 (리소스 낭비) |
| :--- | :--- | :--- |
| **백엔드 CRUD / API 개발** | PostgreSQL, Redis | Kafka, Elasticsearch, Grafana |
| **이벤트 컨슈머 / EDA 개발** | PostgreSQL, Redis, Kafka | Elasticsearch, Kibana, Grafana |
| **검색 쿼리 최적화 작업** | PostgreSQL, Elasticsearch | Kafka, Mailpit |
| **프론트엔드 연동 디버깅** | Mock Server, Auth, Core API | Grafana, Prometheus, Worker |

팀원마다 담당 도메인과 로컬에서 당장 필요한 의존성이 다름에도 불구하고, "공통 파일 하나로 관리한다"는 명목하에 모두가 동일한 풀스택 컨테이너를 강제로 띄우고 있었던 셈입니다.

그렇다고 개발자마다 별도의 `docker-compose-backend.yml`, `docker-compose-kafka.yml`처럼 파일을 쪼개서 관리하자니, 중복 설정이 늘어나고 공통 설정이 바뀔 때마다 동기화가 깨지는 또 다른 관리 지옥이 펼쳐졌습니다.

---

## 2. 해결 전략: Profiles와 Override의 역할 분담

Docker Compose는 이러한 환경 분리와 개인화를 위해 강력한 네이티브 기능 두 가지를 제공합니다. 바로 **Compose Profiles**와 **Override 병합 메커니즘**입니다.

```mermaid
flowchart TD
    subgraph GitRepo["Git 형상 관리 (팀 표준)"]
        Base["compose.yaml (기본 인프라 정의)"]
        P_Core["Core (프로필 없음): PostgreSQL, Redis"]
        P_Event["Profile: event (Kafka, Kafka-UI)"]
        P_Debug["Profile: debug (Mailpit, Jaeger)"]
        Base --- P_Core
        Base --- P_Event
        Base --- P_Debug
    end

    subgraph LocalOnly["Git 비추적 (.gitignore)"]
        Override["compose.override.yaml (개인별 로컬 오버라이드)"]
        O_Port["로컬 디버깅 전용 외부 포트 노출 (예: DB 5433)"]
        O_Env["개인 커스텀 환경변수 (LOG_LEVEL=DEBUG 등)"]
        Override --- O_Port
        Override --- O_Env
    end

    Merge{"Docker Compose 자동 병합 Engine"}
    Base --> Merge
    Override --> Merge

    Command["CLI 명령어: docker compose --profile event up -d"] --> Merge
    Merge --> Final["최종 기동: Core + Event 서비스 + 개인별 포트/환경변수"]
```

두 기능은 담당하는 관심사가 명확히 다릅니다:

1. **Profiles (`profiles: [...]`)**: 
   - **"어떤 서비스들을 선별적으로 기동할 것인가?"**
   - Git으로 팀 전체가 공유하며, 서비스의 도메인(역할)별로 논리적 그룹을 지정합니다.
2. **Override (`compose.override.yaml`)**:
   - **"기본 설정 위에 나만의 로컬 설정을 어떻게 덧씌울 것인가?"**
   - Git에 커밋하지 않고 각 개발자의 로컬 머신에만 존재하며, 포트 충돌 회피, 디버깅 포트 추가, 개인 인증키 주입 등을 담당합니다.

---

## 3. Compose Profiles로 서비스 선별 기동하기

`profiles` 속성은 Compose v2.0 이상에서 표준으로 지원되는 기능입니다. 서비스 정의 블록에 `profiles` 리스트를 선언하면, 해당 프로필이 CLI 옵션이나 환경 변수로 명시적으로 호출되지 않는 한 **기본 기동(`docker compose up`) 대상에서 자동으로 제외**됩니다.

### 3.1 실전 `compose.yaml` 구조 설계

다음은 PostgreSQL과 Redis를 공통 기반으로 두고, Kafka 이벤트 스택과 디버깅 도구를 프로필로 분리한 실무 템플릿입니다.

```yaml
# compose.yaml
name: myapp-local

services:
  # ==========================================================
  # [Core] 프로필 미지정: 모든 개발자가 기본적으로 사용하는 인프라
  # ==========================================================
  postgres:
    image: postgres:17-alpine
    container_name: local-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: appuser
      POSTGRES_PASSWORD: appsecret
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U appuser -d myapp"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: local-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  # ==========================================================
  # [Profile: event] 메시지 큐 및 이벤트 스트리밍 작업 전용
  # ==========================================================
  kafka:
    image: apache/kafka:3.9.0
    container_name: local-kafka
    profiles: ["event"]
    ports:
      - "9092:9092"
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_LISTENERS: PLAINTEXT://:9092,CONTROLLER://:9093
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@localhost:9093
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      KAFKA_LOG_DIRS: /tmp/kraft-combined-logs

  kafka-ui:
    image: provectuslabs/kafka-ui:latest
    container_name: local-kafka-ui
    profiles: ["event"]
    ports:
      - "8989:8080"
    environment:
      KAFKA_CLUSTERS_0_NAME: local-cluster
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:9092
    depends_on:
      - kafka

  # ==========================================================
  # [Profile: debug] 메일 발송 검증 및 추적용 보조 도구
  # ==========================================================
  mailpit:
    image: axllent/mailpit:latest
    container_name: local-mailpit
    profiles: ["debug"]
    ports:
      - "8025:8025" # Web UI
      - "1025:1025" # SMTP Port

volumes:
  pgdata:
```

### 3.2 필요한 서비스만 선별해서 기동하기

이제 상황에 맞게 명령어를 골라 사용할 수 있습니다.

#### ① 일상적인 백엔드 API/DB 개발 (최소 리소스)
```bash
$ docker compose up -d
```
아무런 옵션 없이 실행하면 `profiles`가 명시되지 않은 `postgres`와 `redis`만 기동됩니다. 메모리 점유율은 300MB 미만이며, 2초 만에 기동이 끝납니다.

#### ② 결제 비동기 이벤트 컨슈머 작업 시
```bash
$ docker compose --profile event up -d
```
코어 인프라인 DB, Redis와 함께 `event` 프로필에 속한 `kafka` 및 `kafka-ui`가 함께 실행됩니다.

#### ③ 이벤트와 메일 발송 디버깅을 동시에 검증할 때
복수의 프로필 플래그를 이어붙여 실행할 수 있습니다.
```bash
$ docker compose --profile event --profile debug up -d
```

#### ④ 전체 시스템 통합 테스트가 필요할 때
```bash
$ docker compose --profile "*" up -d
```
와일드카드(`*`)를 지정하면 프로필 지정 여부와 관계없이 정의된 모든 컨테이너가 한 번에 기동됩니다.

{: .prompt-tip }
> **매번 `--profile` 타이핑이 번거롭다면?**
> 프로젝트 루트의 `.env` 파일에 `COMPOSE_PROFILES=event,debug`를 선언해두면, CLI에 매번 옵션을 적지 않아도 `docker compose up -d`만으로 지정한 프로필들이 자동 활성화됩니다.
> ```bash
> # .env
> COMPOSE_PROFILES=event
> ```

---

## 4. `compose.override.yaml`로 개발자별 로컬 환경 개인화하기

프로필로 기동할 서비스의 종류를 통제할 수 있게 되었지만, 여전히 해결되지 않는 로컬 개발의 문제가 있습니다.

- "내 로컬 PC에는 로컬 PostgreSQL이 이미 5432 포트를 쓰고 있어서 충돌이 납니다."
- "저는 쿼리 튜닝 중이라 데이터베이스 로그(`POSTGRES_LOG_STATEMENT=all`)를 켜두고 싶습니다."
- "컨테이너 내부 디버깅을 위해 JVM 원격 디버그 포트(5005)를 임시로 열어야 합니다."

이런 요구사항들을 공통 `compose.yaml`에 반영하면 다른 팀원들의 로컬 환경이 깨지거나 Git 충돌이 발생합니다. 이때 사용하는 것이 바로 **`compose.override.yaml`**입니다.

### 4.1 오버라이드 자동 병합(Merge) 메커니즘

Docker Compose는 별도의 `-f` 옵션 없이 `docker compose` 명령을 실행할 때, **기본적으로 `compose.yaml`을 읽은 뒤 동일 디렉터리에 `compose.override.yaml`이 존재하면 자동으로 두 파일을 읽어 병합(Deep Merge)**합니다.

```
[명령어 실행: docker compose up]
       │
       ▼
1. compose.yaml 읽기 (팀 공통 기반 설정)
       │
       ▼
2. compose.override.yaml 존재 여부 확인
       │
       ├── 없음: compose.yaml 단독 실행
       └── 있음: Deep Merge 규칙에 따라 설정 병합 후 최종 실행
```

따라서 팀 공통 저장소의 `.gitignore`에 다음과 같이 등록해두어야 합니다.

```gitignore
# .gitignore
compose.override.yaml
docker-compose.override.yml
.env.local
```

### 4.2 병합(Merge)의 핵심 규칙과 주의사항

Compose 파일이 병합될 때 데이터 타입에 따라 동작 방식이 다릅니다. 이 차이를 이해하지 못하면 원치 않는 설정 덮어쓰기가 발생할 수 있습니다.

1. **단일 값 (스칼라 값: image, container_name 등)**:
   - `compose.override.yaml`의 값으로 **완전히 대체(Overwrite)**됩니다.
2. **딕셔너리 / 매핑 (키-값 구조: environment, labels 등)**:
   - 키 단위로 병합됩니다. 동일한 키가 있으면 오버라이드 파일의 값으로 덮어쓰고, 새로운 키는 추가됩니다.
3. **리스트 (배열 구조: ports, volumes 등)**:
   - 기본적으로 **추가(Append / Concatenate)**됩니다.

{: .prompt-warning }
> **포트(ports) 설정 시 주의점**
> 리스트 구조는 덮어쓰기가 아니라 **배열에 추가**됩니다.
> 만약 `compose.yaml`에 `5432:5432`가 지정되어 있고, 오버라이드 파일에 `5433:5432`를 선언하면 포트가 바뀌는 것이 아니라 **호스트의 5432와 5433 두 포트가 모두 바인딩**됩니다. 
> 기존 포트를 완전히 변경하고 싶다면 기본 파일에서는 포트를 선언하지 않거나, 오버라이드 파일에서 명시적 바인딩 주소를 다르게 주어야 합니다.

### 4.3 실전 `compose.override.yaml` 작성 예제

다음은 특정 개발자가 자신의 로컬 머신 특성에 맞춰 작성한 `compose.override.yaml` 예시입니다.

```yaml
# compose.override.yaml (Git 미추적 - 개인 로컬 전용)
services:
  postgres:
    # 1. 로컬 5432 포트 충돌 방지를 위해 호스트 5433 포트로 추가 노출
    ports:
      - "127.0.0.1:5433:5432"
    # 2. 로컬 쿼리 튜닝을 위한 환경변수 주입 (기존 DB명/계정 설정과 병합됨)
    environment:
      POSTGRES_INITDB_ARGS: "--encoding=UTF-8"
    command: >
      postgres
      -c log_statement=all
      -c log_duration=on
      -c logging_collector=on

  kafka:
    # 3. 로컬 네트워크 격리를 위해 특정 내부 IP에만 바인딩
    environment:
      KAFKA_LOG_RETENTION_HOURS: 1 # 디스크 공간 절약을 위해 보관 주기 축소

  # 4. 나만의 개인 로컬 유틸리티 컨테이너 추가 (팀 파일엔 없음)
  pgweb:
    image: sosedoff/pgweb:latest
    container_name: local-pgweb
    ports:
      - "8081:8081"
    environment:
      DATABASE_URL: "postgres://appuser:appsecret@postgres:5432/myapp?sslmode=disable"
    depends_on:
      - postgres
```

팀원 A는 위의 설정을 통해 호스트의 `5433` 포트로 DB에 접속하고 웹 브라우저(`http://localhost:8081`)로 GUI DB 클라이언트를 사용할 수 있지만, 이 설정은 Git에 전혀 반영되지 않으므로 팀원 B의 환경에는 일절 영향을 미치지 않습니다.

---

## 5. 최종 구성 검증: `docker compose config`

복수의 프로필과 오버라이드 파일이 얽혔을 때, 실제로 어떤 설정이 도커 데몬에 전달되는지 헷갈릴 수 있습니다. 이때 가장 유용한 명령어가 바로 `docker compose config`입니다.

```bash
$ docker compose --profile event config
```

이 명령어는 컨테이너를 실제로 기동하지 않고, `compose.yaml`과 `compose.override.yaml`, 환경 변수가 모두 병합된 **최종 렌더링 명세**를 YAML 형태로 터미널에 출력해 줍니다.

### 실제 병합 결과 출력 확인

```terminal
name: myapp-local
services:
  kafka:
    container_name: local-kafka
    environment:
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@localhost:9093
      KAFKA_LISTENERS: PLAINTEXT://:9092,CONTROLLER://:9093
      KAFKA_LOG_DIRS: /tmp/kraft-combined-logs
      KAFKA_LOG_RETENTION_HOURS: "1"          # <-- override에서 주입됨
      KAFKA_NODE_ID: "1"
      KAFKA_PROCESS_ROLES: broker,controller
    image: apache/kafka:3.9.0
    ports:
      - mode: ingress
        target: 9092
        published: "9092"
        protocol: tcp
  postgres:
    command:
      - postgres
      - -c
      - log_statement=all                      # <-- override에서 추가된 커맨드
      - -c
      - log_duration=on
    container_name: local-postgres
    environment:
      POSTGRES_DB: myapp
      POSTGRES_PASSWORD: appsecret
      POSTGRES_USER: appuser
    image: postgres:17-alpine
    ports:
      - mode: ingress
        target: 5432
        published: "5432"
        protocol: tcp
      - mode: ingress
        target: 5432
        host_ip: 127.0.0.1
        published: "5433"                      # <-- override에서 추가된 포트
        protocol: tcp
  redis:
    container_name: local-redis
    image: redis:7-alpine
    ports:
      - mode: ingress
        target: 6379
        published: "6379"
        protocol: tcp
```

터미널 출력을 통해:
1. `mailpit` (debug 프로필)은 제외되었고,
2. `kafka` (event 프로필)는 정상 포함되었으며,
3. `postgres`의 포트 목록에 5433과 log_statement 커맨드가 깔끔하게 합성되었음을 눈으로 직접 확인할 수 있습니다.

---

## 6. 팀 표준 협업을 위한 권장 워크플로우

팀 단위로 Compose를 운영할 때는 다음의 세 가지 규칙을 문서화해두면 신규 입사자 온보딩과 유지보수가 비약적으로 수월해집니다.

### 6.1 `compose.override.yaml.example` 템플릿 제공

신규 팀원이 들어왔을 때 오버라이드 파일에 어떤 내용을 적을 수 있는지 헤매지 않도록, 예제 파일을 저장소에 함께 커밋해둡니다.

```bash
# 신규 프로젝트 셋업 가이드
$ cp compose.override.yaml.example compose.override.yaml
$ # 본인의 로컬 포트나 디버그 플래그에 맞게 수정 후 기동
$ docker compose up -d
```

### 6.2 CI/CD 환경에서의 격리 보장

GitHub Actions나 Jenkins 같은 CI 파이프라인에서 Compose를 띄워 통합 테스트를 수행할 때는, 혹시 모를 로컬 오버라이드 파일의 간섭을 원천 차단해야 합니다. 

명시적으로 파일 경로를 지정하면 `compose.override.yaml`의 자동 탐색이 비활성화됩니다.

```bash
# CI 파이프라인 스크립트
# -f 옵션으로 단일 파일을 지정하면 override 자동 병합이 동작하지 않습니다.
docker compose -f compose.yaml --profile event up -d --wait
```

{: .prompt-info }
> CI 환경에서는 필요한 테스트 프로필(예: `--profile event`)만 선별하여 실행 시간을 단축하고 러너의 리소스 소모를 최소화할 수 있습니다.

---

## 7. 정리: 로컬 개발 환경도 아키텍처 설계가 필요합니다

우리는 흔히 운영(Production) 환경의 아키텍처와 리소스 최적화에는 많은 시간을 쏟으면서도, 정작 매일 8시간 이상 마주하는 로컬 개발 환경(DX)은 방치하곤 합니다. "컴퓨터가 느리면 램을 올려야지"라며 무심코 넘기기에는 개발자의 집중력과 생산성 저하가 너무 큽니다.

오늘 다룬 핵심 내용을 요약하면 다음과 같습니다:

1. **Compose Profiles**:
   - `profiles: ["도메인"]` 설정을 통해 무거운 인프라(Kafka, ES, Monitoring)를 기본 기동 대상에서 격리합니다.
   - 필요한 작업에 따라 `docker compose --profile <name> up`으로 3~5초 만에 가볍게 기동합니다.
2. **Compose Override**:
   - `compose.override.yaml`은 Git에 올리지 않는 개인화 레이어입니다.
   - 포트 충돌 해결, 로컬 소스 마운트, 디버그 환경변수 주입을 팀 공통 설정 손상 없이 우아하게 해결합니다.
3. **`docker compose config`**:
   - 두 레이어가 어떻게 결합되었는지 최종 명세를 즉시 검증하고 트러블슈팅할 수 있습니다.

로컬 환경이 무거워 개발에 집중하기 어려웠다면, 지금 팀의 `compose.yaml`을 열고 서비스마다 적절한 `profiles`를 부여하는 것부터 시작해 보시길 권합니다.
