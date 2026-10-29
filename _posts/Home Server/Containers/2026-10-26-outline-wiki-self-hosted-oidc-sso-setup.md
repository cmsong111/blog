---
title: "Authelia OIDC와 연동하는 프라이빗 지식 베이스 Outline Wiki 자체 호스팅"
description: "노션 스타일의 고성능 오픈소스 위키 Outline을 Docker Compose로 배포하고, 별도의 AWS S3 없이 로컬 스토리지로 파일을 저장하며 Authelia OIDC와 Gmail SMTP를 결합한 완전한 프라이빗 지식 관리 시스템을 완성합니다."
date: 2026-10-26 10:00:00 +0900
tags: [docker, docker-compose, homelab, outline, wiki, oidc, sso, postgresql, redis]
mermaid: true
---

> 노션(Notion)의 폐쇄성과 네트워크 지연을 극복하기 위해, 초고속 실시간 마크다운 에디터를 제공하는 오픈소스 지식 관리 도구 Outline을 배포하고 외부 클라우드 종속성 없이 Authelia OIDC SSO 및 로컬 파일 스토리지로 연동하는 방법을 정리합니다.

---

## 1. 홈랩에 Outline 위키가 필요한 이유

홈랩에서 서버 설정, 네트워크 토폴로지, 개인 스터디 노트를 기록할 때 노션(Notion)과 같은 클라우드 도구를 사용하면 다음과 같은 아쉬움이 남습니다:

- 외부 네트워크 장애 시 로컬 문서에 접근 불가
- 민감한 인프라 시크릿이나 개인 문서의 외부 서버 저장에 따른 보안 우려
- 자체 호스팅 서비스들과의 통합 로그인(SSO) 불가

**Outline**은 모던 웹 기술 스택(React, Node.js)으로 제작된 아름답고 빠른 오픈소스 문서 플랫폼입니다. 실시간 동시 편집, 슬래시(`/`) 커맨드, 코드 블록 강조, 계층형 문서 트리 등을 완벽히 지원합니다.

다만 Outline은 자체 로컬 회원가입 기능이 없으며, **반드시 표준 OIDC(OpenID Connect) 또는 외부 IdP(Google, Slack 등)를 통한 로그인만을 강제**하도록 설계되어 있습니다. 앞서 구축한 **Authelia OIDC Provider**가 바로 이 요구조건을 충족하는 완벽한 짝이 됩니다.

---

## 2. Outline Wiki 서비스 아키텍처

홈랩 v2에서 Outline은 외부 AWS S3나 복잡한 오브젝트 스토리지를 별도로 띄우지 않고, **로컬 볼륨 파일 스토리지(`FILE_STORAGE: local`) 모드**를 적용하여 리소스를 최소화했습니다.

```mermaid
flowchart TD
    subgraph Ingress["웹 게이트웨이"]
        User["사용자 브라우저"] -->|"HTTPS (outline.namju.kim)"| NPM["Nginx Proxy Manager"]
    end

    subgraph Knowledge["Knowledge 스택 (Docker Compose)"]
        NPM --> Outline["Outline Wiki Server<br/>(Node.js / Port 3000)"]
        VolData[("로컬 파일 볼륨<br/>/var/lib/outline/data")]
        Outline --- VolData
    end

    subgraph CoreTiers["인증 및 코어 데이터 계층"]
        Outline -->|"OIDC SSO 토큰 교환"| Auth["Authelia (SSO)"]
        Outline -->|"실시간 세션 / 캐시"| RD["Redis 8 (Alpine)"]
        Outline -->|"문서 영속 저장"| PG["PostgreSQL (DB: outline)"]
    end

    subgraph External["외부 알림"]
        Outline -.->|"문서 초대 / 알림 (SMTP 465)"| Gmail["Gmail SMTP Server"]
    end
```

---

## 3. Outline Docker Compose 환경 정의

`services/knowledge/docker-compose.yaml` 파일 명세입니다.

```yaml
# services/knowledge/docker-compose.yaml
name: knowledge

services:
  outline:
    image: outlinewiki/outline:latest
    container_name: outline
    restart: unless-stopped
    environment:
      TZ: Asia/Seoul
      NODE_ENV: production
      PORT: "3000"

      # 외부 공개 URL 및 프록시 신뢰 설정
      URL: https://outline.namju.kim
      FORCE_HTTPS: "false"
      PROXY_HEADERS_TRUSTED: "true"

      # 애플리케이션 시크릿 키 (openssl rand -hex 32)
      SECRET_KEY: ${OUTLINE_SECRET_KEY:?required}
      UTILS_SECRET: ${OUTLINE_UTILS_SECRET:?required}

      # PostgreSQL 및 Redis 연동
      DATABASE_URL: "postgres://outline_user:${OUTLINE_DB_PASSWORD}@postgres:5432/outline"
      PGSSLMODE: disable
      REDIS_URL: redis://redis:6379

      # AWS S3 없이 로컬 디렉터리에 첨부 파일 저장 (25MB 제한)
      FILE_STORAGE: local
      FILE_STORAGE_LOCAL_ROOT_DIR: /var/lib/outline/data
      FILE_STORAGE_UPLOAD_MAX_SIZE: "26214400"

      # Authelia OIDC SSO 연동
      OIDC_CLIENT_ID: outline
      OIDC_CLIENT_SECRET: ${OUTLINE_OIDC_SECRET:?required}
      OIDC_AUTH_URI: https://auth.namju.kim/api/oidc/authorization
      OIDC_TOKEN_URI: https://auth.namju.kim/api/oidc/token
      OIDC_USERINFO_URI: https://auth.namju.kim/api/oidc/userinfo
      OIDC_USERNAME_CLAIM: preferred_username
      OIDC_DISPLAY_NAME: Authelia
      OIDC_SCOPES: "openid offline_access profile email"

      # 문서 알림 및 초대용 SMTP (Gmail 앱 비밀번호)
      EMAIL_ENABLED: "true"
      SMTP_HOST: smtp.gmail.com
      SMTP_PORT: 465
      SMTP_SECURE: true
      SMTP_USERNAME: ${OUTLINE_SMTP_USER:?required}
      SMTP_PASSWORD: ${OUTLINE_SMTP_PASSWORD:?required}
      SMTP_FROM_EMAIL: ${OUTLINE_SMTP_FROM_EMAIL:?required}
      SMTP_REPLY_EMAIL: ${OUTLINE_SMTP_FROM_EMAIL:?required}

    volumes:
      - outline_data:/var/lib/outline/data

    networks:
      - proxy_network
      - database_network

volumes:
  outline_data:

networks:
  proxy_network:
    external: true
  database_network:
    external: true
```

### 트러블슈팅: 리버스 프록시 헤더 불일치 방지
Nginx Proxy Manager 뒤에서 구동할 때 `PROXY_HEADERS_TRUSTED: "true"`를 선언하지 않으면 Outline이 HTTPS 프로토콜을 인지하지 못하고 무한 리다이렉트 루프에 빠집니다. 또한 `FORCE_HTTPS: "false"`로 두어 SSL 종료(SSL Termination) 처리를 Nginx에 전임하는 것이 안전합니다.

---

## 4. Authelia OIDC 클라이언트 등록

`identity/authelia/configuration.yml`의 `identity_providers.oidc.clients` 섹션에 Outline 클라이언트를 등록합니다:

```yaml
# identity/authelia/configuration.yml (Outline OIDC 발췌)
      - client_id: outline
        client_name: Outline
        client_secret: '$pbkdf2-sha512$310000$/xmjkLoxQOA.zHN4vXwdqg$OXtGoOfLtdVVDA8Y0EiZ.zaSffbl/f9U8KKg8g7yUbTrLV6MIcsVGirISKsM7bfe5MPcia8sCNcFsEbj5S8mxg'
        public: false
        authorization_policy: one_factor
        require_pkce: false
        redirect_uris:
          - https://outline.namju.kim/auth/oidc.callback
        scopes:
          - openid
          - offline_access
          - profile
          - email
        response_types:
          - code
        grant_types:
          - authorization_code
          - refresh_token
        token_endpoint_auth_method: client_secret_post
```

- **`redirect_uris`**: 반드시 `https://outline.namju.kim/auth/oidc.callback`으로 지정해야 합니다.
- **`scopes`**: 유저 식별 및 장기 로그인을 위해 `offline_access`와 `email` 스코프가 필수적으로 포함되어야 합니다.

---

## 5. 실행 및 지식 베이스 구축 검증

컨테이너를 기동합니다:

```bash
docker compose up -d
```

기동 후 `https://outline.namju.kim`에 접속하면 모던한 환영 화면과 함께 **"Authelia로 계속하기"** 버튼이 나타납니다.

```mermaid
flowchart LR
    Step1["1. https://outline.namju.kim 접속"] --> Step2["2. Authelia로 계속하기 클릭"]
    Step2 --> Step3["3. Authelia SSO 로그인 (LLDAP 계정)"]
    Step3 --> Step4["4. 동의 후 Outline 위키 메인 진입"]
```

버튼을 누르면 홈랩 통합 인증 포털(`auth.namju.kim`)로 이동하며, LLDAP 계정으로 로그인하는 즉시 Outline에 사용자가 생성되면서 워크스페이스 대시보드로 진입합니다. 이미지를 첨부하면 로컬 볼륨(`/var/lib/outline/data`)에 안전하게 저장되며, 초고속 로컬 네트워크 환경에서 지연 없이 문서를 정리할 수 있습니다.

이로써 홈랩 v2의 **데이터베이스 프로비저닝 ➔ LLDAP 중앙 계정 ➔ Authelia SSO/Forward Auth ➔ Gitea CI/CD ➔ Outline 지식 베이스**로 이어지는 완결된 제로 트러스트 프라이빗 인프라 구축이 모두 마무리되었습니다.
