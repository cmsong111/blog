---
title: "LLDAP을 활용한 홈랩 경량 중앙 디렉터리 서비스 구축"
description: "OpenLDAP의 복잡한 스키마와 관리 오버헤드를 극복하기 위해 Rust 기반 초경량 디렉터리 도구 LLDAP을 Docker Compose로 배포하고, PostgreSQL 연동 및 내부 격리 네트워크를 적용한 중앙 사용자·그룹 관리 체계를 구축합니다."
date: 2026-10-17 10:00:00 +0900
tags: [docker, docker-compose, homelab, lldap, ldap, identity, postgresql]
mermaid: true
---

> 홈서버에 서비스가 늘어남에 따라 발생하는 계정 파편화 문제를 해결하기 위해, 20MB 내외의 극소 리소스로 동작하는 Rust 기반 디렉터리 서비스 LLDAP을 배포하고 안전한 내부망 기반 계정 관리 체계를 완성합니다.

---

## 1. 홈서버에 LDAP 디렉터리 서비스가 필요한 이유

홈랩에서 포테이너(Portainer), 기티(Gitea), 아웃라인(Outline) 등 다양한 웹 서비스를 운영하다 보면 각 서비스마다 별도의 사용자 계정을 생성하고 비밀번호를 관리해야 하는 불편함이 발생합니다.

- 특정 구성원의 비밀번호를 변경할 때 모든 서비스에 일일이 로그인하여 수정해야 함
- 서비스마다 사용자 이름(`username`) 규칙이 달라 관리 혼선 발생
- 서비스 폐기나 신규 추가 시 권한 회수가 누락되어 보안 홀 유발

이를 해결하는 고전적인 솔루션은 **LDAP(Lightweight Directory Access Protocol)**입니다. 하지만 기존 표준 솔루션인 OpenLDAP이나 FreeIPA, Active Directory는 다음과 같은 홈랩 도입 장벽이 있었습니다:

1. **난해한 스키마와 ldif 문법**: 사용자 하나를 추가하는 데도 복잡한 객체 클래스(`inetOrgPerson`, `posixAccount` 등)와 난해한 ldif 포맷을 작성해야 합니다.
2. **별도의 웹 UI 필요**: phpLDAPadmin 등 낡고 무거운 서드파티 웹 도구를 추가로 띄워야 해 유지보수 부담이 큽니다.
3. **과도한 리소스 낭비**: 수십~수백 명 규모의 소규모 개인 서버에 적용하기에는 너무 무겁습니다.

**LLDAP(Light LDAP)**은 이러한 단점을 완벽하게 보완한 최신 Rust 기반 오픈소스입니다. 직관적인 최신 웹 UI가 내장되어 있으며, 표준 LDAP v3 프로토콜을 온전히 준수하면서도 20~30MB 미만의 극도로 적은 메모리로 동작합니다.

---

## 2. LLDAP 아키텍처 및 네트워크 격리 설계

LLDAP은 웹 관리 포털(Port 17170)과 LDAP 통신 포트(Port 3890)를 제공합니다. 보안을 위해 LDAP 포트는 외부나 호스트 인터페이스에 노출할 필요가 전혀 없으며, 오직 인증 프록시(Authelia)만이 접근할 수 있도록 도커 내부 전용 브릿지 네트워크(`identity_backend`)로 격리합니다.

```mermaid
flowchart TD
    subgraph Ingress["외부 접속 계층"]
        Client["관리자 브라우저"] --> NPM["Nginx Proxy Manager<br/>(id.namju.kim)"]
    end

    subgraph Identity["Identity 스택 (Docker Compose)"]
        NPM -->|"HTTPS 역방향 프록시 (Port 17170)"| LLDAP["LLDAP 컨테이너<br/>(Rust 기반 디렉터리 엔진)"]

        subgraph PrivateNet["전용 내부망: identity_backend (internal: true)"]
            LLDAP ---|"LDAP 프로토콜 (Port 3890)"| Authelia["Authelia (SSO 포털)"]
        end
    end

    subgraph DataTier["데이터베이스 계층: database_network"]
        LLDAP -->|"영속 데이터 저장"| PG["PostgreSQL (DB: lldap)"]
    end
```

- **`proxy_network`**: Nginx Proxy Manager를 통해 웹 UI(`https://id.namju.kim`)에 접속하기 위한 외부 브릿지 네트워크.
- **`identity_backend` (`internal: true`)**: 외부 인터넷 게이트웨이가 차단된 순수 내부 도커 브릿지망으로, Authelia와 LLDAP 간의 평문 LDAP 쿼리가 도커 호스트 외부로 누출되지 않도록 원천 차단합니다.
- **`database_network`**: 앞선 1편에서 프로비저닝한 `lldap` PostgreSQL 데이터베이스에 연결합니다.

---

## 3. LLDAP Docker Compose 환경 구성

`identity/docker-compose.yaml`에 정의된 LLDAP 서비스 명세입니다.

```yaml
# identity/docker-compose.yaml (LLDAP 발췌)
name: identity

services:
  lldap:
    image: lldap/lldap:stable
    container_name: lldap
    restart: unless-stopped
    environment:
      TZ: Asia/Seoul

      # LDAP 기본 식별자(Base DN) 및 관리자 계정
      LLDAP_LDAP_BASE_DN: "dc=namju,dc=kim"
      LLDAP_LDAP_USER_DN: "admin"
      LLDAP_LDAP_USER_EMAIL: "${LLDAP_ADMIN_EMAIL}"
      LLDAP_LDAP_USER_PASS: "${LLDAP_ADMIN_PASSWORD:?required}"

      # 보안 서명 및 암호화 시드 (openssl rand -hex 32)
      LLDAP_JWT_SECRET: "${LLDAP_JWT_SECRET:?required}"
      LLDAP_KEY_SEED: "${LLDAP_KEY_SEED:?required}"

      # 공개 웹 UI URL
      LLDAP_HTTP_URL: "https://id.namju.kim"

      # PostgreSQL 데이터베이스 연결 문자열
      LLDAP_DATABASE_URL: "postgres://lldap_user:${LLDAP_DB_PASSWORD}@postgres:5432/lldap"

    volumes:
      - lldap_data:/data

    networks:
      - proxy_network
      - identity_backend
      - database_network

    healthcheck:
      test:
        - CMD
        - /app/lldap
        - healthcheck
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

volumes:
  lldap_data:

networks:
  proxy_network:
    external: true
  identity_backend:
    driver: bridge
    internal: true
  database_network:
    external: true
```

### 보안 시드 생성
`LLDAP_JWT_SECRET`과 `LLDAP_KEY_SEED`는 OpenSSL을 통해 32바이트 이상의 무작위 난수로 생성하여 `.env` 파일에 저장합니다:

```bash
openssl rand -hex 32 # LLDAP_JWT_SECRET
openssl rand -hex 32 # LLDAP_KEY_SEED
```

---

## 4. 사용자 및 권한 그룹(RBAC) 모델링

LLDAP 배포가 완료되면 `https://id.namju.kim`에 접속하여 관리자 계정으로 로그인한 뒤, 홈랩 전체 서비스에서 공통으로 참조할 그룹 체계를 정의합니다.

### 표준 그룹 구성

| 그룹명 (CN) | 용도 및 권한 범위 | 할당 서비스 예시 |
| :--- | :--- | :--- |
| `admin` | 시스템 인프라 전권 (Portainer, Uptime Kuma 등) | Portainer, Uptime Kuma, Nginx |
| `developer` | 개발 리소스 접근 권한 (소스 코드 저장소, CI 파이프라인) | Gitea, Gitea Runner |
| `guest` | 읽기 및 사내 지식 베이스 접근 권한 | Outline Wiki |

```mermaid
flowchart LR
    subgraph Groups["LLDAP 그룹 (cn)"]
        G_Admin["cn=admin"]
        G_Dev["cn=developer"]
        G_Guest["cn=guest"]
    end

    subgraph Users["사용자 (uid)"]
        U_Namju["uid=namju"]
        U_Guest["uid=family_guest"]
    end

    U_Namju --> G_Admin
    U_Namju --> G_Dev
    U_Namju --> G_Guest
    U_Guest --> G_Guest
```

1. **Groups 탭**:
   - `admin`, `developer`, `guest` 세 가지 그룹을 생성합니다.
2. **Users 탭**:
   - 메인 사용자를 등록하고 이메일, 닉네임, 비밀번호를 지정합니다.
   - 메인 사용자를 `admin`, `developer`, `guest` 그룹에 모두 추가합니다.
   - 외부 게스트 계정이 필요한 경우 `guest` 그룹만 부여하여 서비스 접근 권한을 최소화합니다.

---

## 5. 서비스 정상 동작 및 LDAP 쿼리 테스트

컨테이너를 구동하고 헬스체크 및 포트 상태를 점검합니다.

```bash
# 컨테이너 실행
docker compose up -d lldap

# 헬스체크 상태 확인
docker inspect --format='{% raw %}{{json .State.Health.Status}}{% endraw %}' lldap
# 출력: "healthy"
```

동일 네트워크 상에서 LDAP 검색 요청이 정상 응답하는지 `ldapsearch` 명령어로 검증할 수 있습니다:

```bash
docker run --rm --network identity_backend osixia/openldap:latest \
  ldapsearch -x -H ldap://lldap:3890 \
  -b "dc=namju,dc=kim" \
  -D "uid=admin,ou=people,dc=namju,dc=kim" \
  -w "your_admin_password" \
  "(uid=namju)"
```

정상적으로 사용자의 DN(`uid=namju,ou=people,dc=namju,dc=kim`)과 소속 그룹 정보가 조회되면 중앙 계정 디렉터리 준비가 완료됩니다. 다음 글에서는 이 LLDAP을 백엔드로 삼아 모든 웹 서비스의 관문을 단일 인증(SSO)으로 통합하는 **Authelia** 구축을 진행합니다.
