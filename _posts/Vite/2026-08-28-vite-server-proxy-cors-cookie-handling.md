---
title: "Vite server.proxy 설정을 활용한 로컬 CORS 해결 및 인증 쿠키 포워딩"
description: "Vite 개발 서버의 server.proxy 옵션을 통해 로컬 개발 환경의 CORS 제약과 SameSite 인증 쿠키 누락 문제를 해결하고, proxyRes 후킹으로 Set-Cookie 도메인을 재작성하는 실무 기법을 정리합니다."
date: 2026-08-28 12:00:00 +0900
tags: [vite, server-proxy, cors, cookies, dev-server]
mermaid: true
---

> 로컬 개발 환경에서 SPA 프론트엔드와 독립된 백엔드 API 서버를 연동할 때 브라우저의 동일 출처 정책(SOP)으로 인한 CORS 오류와 인증 쿠키 유실은 빈번히 마주하는 장벽입니다. 본 글에서는 Vite 개발 서버의 `server.proxy` 옵션이 내부적으로 어떻게 동작하는지 분석하고, 호스트 헤더 변경(`changeOrigin`), 경로 재작성(`rewrite`), 그리고 `configure` 이벤트 훅을 활용해 백엔드의 `Set-Cookie` 헤더를 로컬 도메인에 맞게 변환하여 세션을 안전하게 유지하는 실무 구현법을 정리합니다.

---

## 1. 배경: 로컬 개발 환경에서의 CORS와 인증 쿠키 문제

현대 웹 애플리케이션 개발에서는 프론트엔드와 백엔드가 서로 다른 포트나 도메인에서 실행되는 경우가 일반적입니다:

- **프론트엔드 (Vite Dev Server)**: `http://localhost:5173`
- **백엔드 API 서버 (Spring Boot / Express)**: `http://localhost:8080`

브라우저는 보안을 위해 **동일 출처 정책(Same-Origin Policy, SOP)**을 강제합니다. 프토토콜, 호스트, 포트 중 하나라도 다르면 브라우저는 서로 다른 출처(Origin)로 간주합니다.

이때 백엔드에 `Access-Control-Allow-Origin` 설정이 되어 있지 않거나, 브라우저의 OPTIONS 프리플라이트(Preflight) 요청이 거부되면 즉시 CORS 에러가 발생합니다. 더 큰 문제는 **인증 쿠키(Session Cookie, Refresh Token)**입니다. 백엔드에서 `Set-Cookie` 헤더를 내려줄 때 `Domain`이 백엔드 주소로 지정되어 있거나 `SameSite=Strict/Lax` 및 `Secure` 속성이 걸려 있다면, 다른 출처인 `localhost:5173` 브라우저는 이 쿠키의 저장을 거부하거나 후속 API 요청 시 쿠키를 전송하지 않습니다.

이러한 문제를 해결하기 위해 백엔드 코드 전반에 불필요한 로컬 전용 CORS 완화 코드를 넣는 대신, **Vite 개발 서버 자체를 리버스 프록시(Reverse Proxy)로 동작**시키는 것이 가장 깔끔한 실무적 접근법입니다.

---

## 2. Vite `server.proxy` 아키텍처와 동작 원리

Vite 개발 서버는 내부적으로 Node.js 기반의 `connect` HTTP 프레임워크와 검증된 프록시 라이브러리인 `http-proxy` 패키지를 사용하여 프록시 파이프라인을 구축합니다.

```mermaid
sequenceDiagram
    autonumber
    actor Browser as 브라우저 (localhost:5173)
    participant Vite as Vite Dev Server (localhost:5173)
    participant Backend as 백엔드 API (localhost:8080)

    Note over Browser,Vite: 브라우저는 단일 출처(localhost:5173)로 인식
    Browser->>Vite: GET /api/v1/users/me (Cookie: SESSIONID=...)
    Note over Vite: 1. server.proxy 라우트 매칭<br/>2. rewrite: /api/v1 제거<br/>3. changeOrigin: Host 헤더 변경
    Vite->>Backend: GET /v1/users/me (Host: localhost:8080)
    Backend-->>Vite: 200 OK (Set-Cookie: SESSIONID=...; Domain=8080)
    Note over Vite: configure(proxyRes) 훅:<br/>Set-Cookie의 Domain을 localhost:5173에 맞게 재작성
    Vite-->>Browser: 200 OK (Set-Cookie: SESSIONID=...; Path=/; SameSite=Lax)
    Note over Browser: 출처 일치로 쿠키 정상 저장 & CORS 없음
```

브라우저 관점에서는 모든 네트워크 요청이 `localhost:5173`이라는 동일한 출처로 향하기 때문에 브라우저 레벨의 CORS 검사 자체가 발생하지 않습니다. Vite 개발 서버가 중계자 역할을 맡아 백엔드로 요청을 포워딩하고 응답을 다시 브라우저로 반환합니다.

---

## 3. `server.proxy` 핵심 설정 옵션 상세 분석

`vite.config.ts` 파일의 `server.proxy` 속성에 프록시 규칙을 객체 형태로 선언합니다.

```typescript
// vite.config.ts
import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      // '/api'로 시작하는 모든 요청을 프록시 처리
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
        secure: false,
        ws: true
      }
    }
  }
});
```

### 3.1 `target`
- 프록시된 요청을 최종 전달할 대상 백엔드 서버의 기본 URL입니다.

### 3.2 `changeOrigin: true`
- 프록시 요청 시 HTTP `Host` 헤더를 `target`의 호스트(`localhost:8080`)로 변경할지 여부를 지정합니다.
- 많은 백엔드 프레임워크(스프링 부트, Nginx 가상 호스트)는 수신된 `Host` 헤더를 검사하여 가상 호스팅 라우팅이나 보안 필터링을 수행합니다. `changeOrigin: true`로 설정해야 백엔드가 올바른 타깃 요청으로 정상 인식합니다.

### 3.3 `rewrite`
- 클라이언트가 요청한 URL 경로에서 특정 접두사(Prefix)를 제거하거나 변경할 때 사용하는 함수입니다.
- 예를 들어 프론트엔드는 `/api/v1/users`로 호출하고, 백엔드는 `/v1/users` 엔드포인트를 기대할 경우 `path.replace(/^\/api/, '')`를 적용해 일치시킵니다.

### 3.4 `ws: true`
- WebSocket 프로토콜 프록시를 활성화합니다. 백엔드에서 SockJS, STOMP, 또는 원시 WebSocket을 사용할 때 필수적입니다.

---

## 4. 실무 심화: 인증 쿠키(Set-Cookie) 포워딩 및 도메인 리라이트

로컬 개발 환경에서 가장 까다로운 시나리오는 백엔드가 로그인 성공 시 `Set-Cookie` 헤더를 응답할 때 발생합니다. 

백엔드가 실서버 또는 독립 개발망 도메인(`Domain=.backend.internal`)을 명시했거나 `Secure` 속성을 포함하고 있는 경우, 로컬 HTTP 환경인 브라우저는 해당 쿠키를 거부합니다.

이 문제는 Vite의 `configure` 옵션을 통해 해결할 수 있습니다. `configure` 훅을 사용하면 내부 `http-proxy` 인스턴스의 생명주기 이벤트(`proxyReq`, `proxyRes`, `error`)에 직접 접근할 수 있습니다:

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import type { HttpProxy } from 'vite';

export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
        configure: (proxy: HttpProxy.Server) => {
          // 1. 요청 전송 시 디버깅 로그 기록
          proxy.on('proxyReq', (proxyReq, req) => {
            console.log(`[vite:proxy] ${req.method} ${req.url} -> ${proxyReq.path}`);
          });

          // 2. 백엔드 응답 가로채기 (Set-Cookie 재작성)
          proxy.on('proxyRes', (proxyRes, req, res) => {
            const setCookieHeaders = proxyRes.headers['set-cookie'];

            if (setCookieHeaders) {
              const rewrittenCookies = setCookieHeaders.map((cookieStr) => {
                return cookieStr
                  // 백엔드 특정 Domain 속성을 제거하여 localhost에 귀속되도록 조정
                  .replace(/Domain=[^;]+;?/gi, '')
                  // HTTP 로컬 개발 환경에서 거부되지 않도록 Secure 속성 제거
                  .replace(/Secure;?/gi, '')
                  // 크로스 사이트 컨텍스트 호환을 위해 SameSite를 Lax로 조정
                  .replace(/SameSite=Strict/gi, 'SameSite=Lax')
                  .trim();
              });

              // 수정된 쿠키 헤더를 응답 객체에 다시 할당
              proxyRes.headers['set-cookie'] = rewrittenCookies;
              console.log('[vite:proxy] Rewritten Set-Cookie for local dev:', rewrittenCookies);
            }
          });

          // 3. 프록시 연결 장애 에러 핸들링
          proxy.on('error', (err, req, res) => {
            console.error('[vite:proxy] Proxy error encountered:', err.message);
          });
        }
      }
    }
  }
});
```

위 설정을 적용하면 백엔드가 응답한 세션 쿠키에서 문제가 되는 `Domain`과 `Secure` 플래그가 안전하게 정제되어 브라우저(`localhost:5173`)로 전달되므로, 브라우저는 쿠키를 신뢰하고 세션을 지속 유지할 수 있습니다.

---

## 5. 실행 결과 및 동작 검증

작성한 Vite 프록시 설정이 정상 동작하는지 터미널에서 API 요청 및 쿠키 응답 헤더를 통해 검증합니다.

### 5.1 프록시 경유 API 요청 및 응답 검증

Vite 개발 서버가 구동 중인 포트(`5173`)로 `/api/v1/users/me`를 호출했을 때, 접두사가 제거되어 백엔드(`localhost:8080`)로 포워딩되고 200 OK 응답이 반환되는 화면입니다.

![Vite 개발 서버 프록시를 경유한 API 호출 및 응답 디버깅 검증](/assets/images/2026-08-28/vite-proxy-request-debug-terminal.png)
_Vite 개발 서버 프록시를 경유한 API 호출 및 응답 디버깅 검증_

브라우저는 백엔드의 실제 포트 번호나 도메인을 직접 알 필요 없이, 동일 출처 내에서 JSON 데이터를 성공적으로 수신함을 확인할 수 있습니다.

### 5.2 Set-Cookie 헤더 리라이트 검증

로그인 API 요청 시 백엔드가 반환한 세션 쿠키가 `configure` 프록시 훅에 의해 `Domain=localhost` 및 `SameSite=Lax` 속성으로 올바르게 변환되어 전달되는 터미널 응답 덤프 화면입니다.

![프록시 configure 훅을 통한 세션 쿠키 도메인 리라이트 및 수신 검증](/assets/images/2026-08-28/vite-proxy-cookie-rewrite-terminal.png)
_프록시 configure 훅을 통한 세션 쿠키 도메인 리라이트 및 수신 검증_

---

## 6. 정리 및 프로덕션 환경과의 일관성 유지

Vite의 `server.proxy`는 로컬 개발 환경에서 CORS와 쿠키 정책을 우회하기 위한 훌륭한 도구입니다. 다만 개발을 진행할 때 다음 아키텍처 원칙을 준수하는 것이 중요합니다:

1. **상대 경로(Relative Path) 호출 유지**: 프론트엔드 코드 내부의 API 클라이언트(Axios, Fetch 등)는 기본 URL(`baseURL`)을 `http://localhost:8080`처럼 하드코딩하지 않고 `/api`와 같은 상대 경로로 작성해야 합니다.
2. **프로덕션 인프라와의 일관성**: 개발 환경에서 Vite 개발 서버가 수행한 프록시 역할은, 실제 프로덕션 배포 시 Nginx나 클라우드 API Gateway의 리버스 프록시 설정(`location /api { proxy_pass http://backend; }`)과 1:1로 정확히 대응되므로 추가적인 프론트엔드 코드 수정 없이 매끄럽게 배포할 수 있습니다.
