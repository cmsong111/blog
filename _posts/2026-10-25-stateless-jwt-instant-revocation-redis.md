---
title: "무상태(Stateless) JWT의 한계 넘기: 전체 로그아웃과 탈퇴 시 액세스 토큰 즉시 무효화하는 전략"
description: 무상태(Stateless) JWT 환경에서 사용자가 전체 로그아웃하거나 회원 탈퇴했을 때 잔여 유효시간이 남은 액세스 토큰을 Redis 기반으로 즉시 무효화하는 아키텍처를 다룹니다.
date: 2026-10-25 12:00:00 +0900
categories: [spring-boot]
tags: [spring-boot, spring-security, jwt, redis, token-revocation]
mermaid: true
image:
  path: /assets/images/2026-10-25/logout-all-api-response.png
  alt: 전체 로그아웃 API 성공 응답 화면
---

> 무상태(Stateless) JWT는 서버가 세션 상태를 저장하지 않는 확장성을 제공하지만, 전체 로그아웃이나 회원 탈퇴 시 잔여 유효기간이 남은 액세스 토큰을 즉시 무효화하기 어렵다는 구조적 딜레마를 가집니다. 본 글에서는 개별 토큰 블랙리스트의 메모리 낭비를 극복하고, Redis 기반의 사용자별 '토큰 버전(Token Version)' 관리 기법을 통해 O(1) 메모리로 즉각적인 토큰 폐기를 구현한 실무 아키텍처를 소개합니다.
{: .prompt-info }

## 문제 상황: "탈퇴한 회원이 여전히 API를 호출할 수 있다?" 무상태 JWT의 딜레마

JWT(JSON Web Token) 기반 인증의 가장 큰 매력은 **무상태성(Stateless)**입니다. 서버는 사용자의 세션을 메모리나 데이터베이스에 유지할 필요 없이, 토큰 내부의 암호화 서명(`Signature`)과 만료 일시(`exp`)만 검증하면 즉시 유효한 요청으로 신뢰할 수 있습니다.

하지만 서비스 운영 환경에서 다음과 같은 보안 시나리오를 마주하면 무상태성은 큰 취약점으로 변합니다.

1. **기기 분실 또는 계정 탈취 의심**: 사용자가 보안 위협을 느껴 **"모든 기기에서 로그아웃"**을 실행한 경우
2. **비밀번호 변경**: 비밀번호를 바꾼 즉시 기존에 로그인되어 있던 다른 모든 디바이스의 세션을 강제 종료해야 하는 경우
3. **회원 탈퇴**: 불량 이용자를 강제 탈퇴 처리했거나 본인이 직접 회원 탈퇴를 완료한 경우

일반적으로 리프레시 토큰(Refresh Token)은 저장소(DB 또는 Redis)에 화이트리스트로 관리되므로 저장소의 레코드를 지우면 새로운 액세스 토큰 재발급을 막을 수 있습니다. 그러나 **이미 클라이언트 브라우저나 앱에 발급되어 잔여 수명(예: 15분~30분)이 남아 있는 액세스 토큰**은 서버가 개입할 방법이 없습니다.

탈퇴 처리가 끝난 사용자가 잔여 유효기간이 남은 액세스 토큰으로 여전히 개인정보를 조회하거나 커뮤니티에 글을 작성할 수 있다면, 이는 데이터 무결성과 개인정보 보호 측면에서 심각한 결함입니다.

---

## 전략 비교: 모든 액세스 토큰 JTI 블랙리스트 vs 유저별 무효화 기준 시점 vs 토큰 버전

잔여 유효시간이 남은 무상태 토큰을 강제로 무효화하기 위해 주로 검토되는 세 가지 전략을 비교해 보았습니다.

| 비교 항목 | 1. 개별 토큰 JTI 블랙리스트 | 2. 유저별 무효화 시각 (Timestamp) | 3. 유저별 토큰 버전 (Token Version) ⭐ |
| :--- | :--- | :--- | :--- |
| **저장 방식** | 로그아웃된 모든 토큰의 `jti`를 Redis에 저장 | 유저별 로그아웃 시각(`invalidatedAt`) 기록 | 유저별 토큰 버전 식별자(UUID) 1개 저장 |
| **전체 로그아웃 지원** | 불가능 (발급된 모든 JTI 추적 불가) | 가능 (`iat < invalidatedAt` 비교) | 가능 (버전 값만 새로운 UUID로 갱신) |
| **메모리 복잡도** | $O(N)$ (활성 토큰 수에 비례하여 급증) | $O(1)$ (유저당 1개 키) | $O(1)$ (유저당 1개 키, 약 88 Bytes) |
| **경합 및 동기화 이슈** | 없음 | 분산 서버 간 시계 오차(Clock Skew) 및 초 단위 정밀도 경합 존재 | 없음 (UUID 단순 일치 여부 비교) |

### 1. 개별 토큰 블랙리스트 (JTI Blacklist)
단일 기기 로그아웃에는 유용하지만, 사용자가 발급받은 수많은 디바이스의 모든 액세스 토큰 ID를 서버가 일일이 기억하고 있지 않는 한 "모든 기기 동시 로그아웃"을 처리할 수 없습니다. 또한 트래픽이 커질수록 Redis 메모리에 블랙리스트 키가 눈덩이처럼 불어납니다.

### 2. 유저별 무효화 시각 대조 (Invalidated Timestamp)
유저가 전체 로그아웃한 시각(`invalidatedAt`)을 기록해 두고, JWT의 발급 시각(`iat`)이 이보다 이전이면 거부하는 방식입니다. 개념은 단순하지만 치명적인 한계가 있습니다. JWT 표준(RFC 7519)에서 `iat` 클레임은 밀리초가 아닌 **초(Second) 단위** Unix 타임스탬프입니다. 따라서 동일한 1초 내에 토큰 재발급과 로그아웃 요청이 연달아 일어날 경우 경합(Race Condition)이 발생하여 정상 토큰이 거부되거나 무효화되어야 할 토큰이 통과될 위험이 있습니다.

### 3. 유저별 토큰 버전 관리 (Token Version Store) — 채택
이 문제를 해결하기 위해 제가 채택한 방식은 **사용자별 단일 토큰 버전(Token Version)** 관리입니다.
- JWT 클레임에 `token_version` 문자열을 포함하여 발급합니다.
- Redis에는 사용자별로 현재 유효한 버전 식별자(`token:version:{userId}`)를 단 하나만 저장합니다.
- 전체 로그아웃이나 회원 탈퇴 시 Redis의 버전을 새로운 UUID로 교체합니다.
- 인증 필터에서 토큰의 `token_version`과 Redis의 현재 버전을 대조하여, 불일치하면 서명 유효 여부와 무관하게 즉시 401로 차단합니다.

초 단위 타임스탬프 비교 없이 문자열 동등성 검사만 수행하므로 시계 오차나 레이스 컨디션이 원천적으로 차단되며, Redis 메모리도 유저당 단 1개의 키만 사용하므로 매우 경제적입니다.

---

## 아키텍처 설계: Redis `TokenVersionStore` 및 발급 시각 대조 필터

전체적인 인증 및 검증 아키텍처의 흐름은 다음과 같습니다.

```mermaid
sequenceDiagram
    autonumber
    actor Client as 클라이언트 (App/Web)
    participant Filter as JwtDecoder (Spring Security)
    participant Redis as Redis (TokenVersionStore)
    participant DB as UserRepository (RDB)
    participant Controller as Business API

    Client->>Filter: API 요청 (Bearer AccessToken)
    Note over Filter: 1차: 암호화 서명(HS256) 및 exp 검증
    alt 서명 위조 또는 만료
        Filter-->>Client: 401 Unauthorized (AUTH-001 / AUTH-002)
    else 유효한 서명
        Filter->>Redis: GET token:version:{userId}
        Redis-->>Filter: 현재 활성 버전 반환
        alt 토큰 내 version != Redis currentVersion
            Filter-->>Client: 401 Unauthorized (AUTH-008 REVOKED_TOKEN)
        else 버전 일치
            Filter->>DB: 계정 활성 상태 확인 (existsById)
            alt 계정 탈퇴/삭제 상태
                Filter-->>Client: 401 Unauthorized (AUTH-008 REVOKED_TOKEN)
            else 활성 회원
                Filter->>Controller: SecurityContext 인증 위임 및 비즈니스 로직 수행
                Controller-->>Client: 200 OK 응답
            end
        end
    end
```

### Redis 토큰 버전 저장소 구현

토큰 버전 관리의 핵심은 **"토큰의 잔여 수명보다 무효화 표식이 먼저 만료되지 않도록 보장"**하는 것입니다.

```kotlin
// src/main/kotlin/io/github/cmsong111/cotton_bat_server/auth/application/TokenVersionStore.kt
package io.github.cmsong111.cotton_bat_server.auth.application

import io.github.cmsong111.cotton_bat_server.security.jwt.JwtProperties
import java.util.UUID
import org.springframework.data.redis.core.StringRedisTemplate
import org.springframework.stereotype.Component

/** 전체 폐기와 동시에 발급 중인 토큰도 같은 버전으로 무효화한다. */
@Component
class TokenVersionStore(
    private val redis: StringRedisTemplate,
    properties: JwtProperties,
) {
    // 리프레시 토큰과 액세스 토큰 중 더 긴 TTL에 여유 시간(ClockSkew)을 더해 만료 시간 설정
    private val ttl = maxOf(properties.refreshTokenTtl, properties.accessTokenTtl) + properties.clockSkew

    fun current(userId: String): String = redis.opsForValue().get(key(userId)) ?: ""

    /** 
     * 새 토큰보다 먼저 폐기 표식이 만료되지 않게 조회와 TTL 갱신을 한 번에 원자적으로 수행한다(GETEX). 
     */
    fun forIssue(userId: String): String = redis.opsForValue().getAndExpire(key(userId), ttl) ?: ""

    /**
     * 전체 로그아웃 또는 탈퇴 시 호출하여 새로운 UUID로 버전을 덮어쓴다.
     */
    fun revoke(userId: String) {
        redis.opsForValue().set(key(userId), UUID.randomUUID().toString(), ttl)
    }

    private fun key(userId: String): String = "token:version:$userId"
}
```

- `forIssue(userId)`: 토큰을 발급할 때 Redis의 `GETEX` 명령어를 활용하여, 현재 버전을 가져오면서 TTL을 최신 상태로 원자적으로 연장합니다. 이를 통해 활발히 이용 중인 사용자의 버전 키가 먼저 소멸되는 현상을 방지합니다.
- `revoke(userId)`: 새로운 난수 UUID를 키에 할당하고 최대 토큰 수명만큼 TTL을 지정합니다. 기존에 발급되었던 모든 토큰은 이 순간 즉시 구버전이 됩니다.

---

## 구현: 전체 로그아웃과 회원 탈퇴 시 즉각 무효화

### 1. Spring Security 검증기 (`ActiveTokenValidator`)

Spring Security의 `NimbusJwtDecoder`에 커스텀 `OAuth2TokenValidator<Jwt>`를 등록하여 서명 검증 직후 토큰 버전을 대조하도록 구성합니다.

```kotlin
// src/main/kotlin/io/github/cmsong111/cotton_bat_server/security/jwt/JwtConfig.kt
package io.github.cmsong111.cotton_bat_server.security.jwt

import io.github.cmsong111.cotton_bat_server.auth.application.TokenVersionStore
import io.github.cmsong111.cotton_bat_server.user.domain.UserRepository
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.security.oauth2.core.DelegatingOAuth2TokenValidator
import org.springframework.security.oauth2.core.OAuth2Error
import org.springframework.security.oauth2.core.OAuth2ErrorCodes
import org.springframework.security.oauth2.core.OAuth2TokenValidator
import org.springframework.security.oauth2.core.OAuth2TokenValidatorResult
import org.springframework.security.oauth2.jwt.Jwt
import org.springframework.security.oauth2.jwt.JwtDecoder
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder
import java.util.UUID

@Configuration
class JwtConfig(
    private val properties: JwtProperties,
    private val tokenVersions: TokenVersionStore,
    private val userRepository: UserRepository,
) {
    @Bean
    fun jwtDecoder(): JwtDecoder {
        val decoder = NimbusJwtDecoder.withSecretKey(secretKey).build()

        // 1. 표준 서명 및 만료 시간 검증기 (CPU 암호화 연산)
        val standardValidators = DelegatingOAuth2TokenValidator(
            ExpiryValidator(properties),
            JwtTimestampValidator(properties.clockSkew),
            JwtIssuerValidator(properties.issuer),
            JwtClaimValidator<String>(JwtProvider.TOKEN_TYPE_CLAIM) { it == JwtProvider.ACCESS_TOKEN_TYPE },
        )

        // 2. 토큰 버전 및 계정 활성 상태 검증기 (Redis & DB 연산)
        val activeTokens = ActiveTokenValidator(tokenVersions, userRepository)

        decoder.setJwtValidator { token ->
            val result = standardValidators.validate(token)
            // 표준 검증을 통과한 유효한 서명의 토큰만 Redis를 조회하여 부하를 최소화
            if (result.hasErrors()) result else activeTokens.validate(token)
        }
        return decoder
    }

    /** 발급 시각의 초 단위 경합 없이 폐기 버전과 현재 계정의 활성 상태를 검사한다. */
    private class ActiveTokenValidator(
        private val versions: TokenVersionStore,
        private val users: UserRepository,
    ) : OAuth2TokenValidator<Jwt> {
        override fun validate(token: Jwt): OAuth2TokenValidatorResult {
            val userId = runCatching { UUID.fromString(token.subject) }.getOrNull()
                ?: return OAuth2TokenValidatorResult.failure(OAuth2Error(OAuth2ErrorCodes.INVALID_TOKEN, "유효한 sub가 없습니다.", null))
            
            val version = token.getClaimAsString(JwtProvider.TOKEN_VERSION_CLAIM) ?: ""
            // 토큰 내부 버전이 Redis의 최신 버전과 다르거나 회원이 탈퇴(소프트 삭제)된 경우 즉시 차단
            if (version != versions.current(userId.toString()) || !users.existsById(userId)) {
                return OAuth2TokenValidatorResult.failure(OAuth2Error(REVOKED_ERROR_CODE, "폐기된 토큰입니다.", null))
            }
            return OAuth2TokenValidatorResult.success()
        }
    }

    companion object {
        const val REVOKED_ERROR_CODE = "token_revoked"
    }
}
```

### 2. 전체 로그아웃 및 회원 탈퇴 서비스 연동

사용자가 전체 로그아웃하거나 회원 탈퇴를 요청할 때, 서비스 레이어에서 `TokenService.revokeAll(userId)`을 호출하여 버전 교체와 리프레시 토큰 삭제를 원자적으로 수행합니다.

```kotlin
// src/main/kotlin/io/github/cmsong111/cotton_bat_server/auth/application/TokenService.kt
@Service
class TokenService(
    private val refreshTokenRepository: RefreshTokenRepository,
    private val tokenVersions: TokenVersionStore,
) {
    /**
     * 모든 기기의 토큰을 즉시 폐기한다.
     * 1. Redis의 토큰 버전을 새 UUID로 교체 -> 기존 모든 액세스 토큰 무효화
     * 2. Redis에 저장된 해당 유저의 모든 리프레시 토큰 일괄 삭제
     */
    fun revokeAll(userId: String) {
        tokenVersions.revoke(userId)
        refreshTokenRepository.deleteAll(refreshTokenRepository.findAllByUserId(userId))
    }
}
```

```kotlin
// src/main/kotlin/io/github/cmsong111/cotton_bat_server/user/application/UserService.kt
@Service
class UserService(
    private val userRepository: UserRepository,
    private val tokenService: TokenService,
) {
    /**
     * 회원 탈퇴. 유저 엔티티를 삭제 처리하고 모든 토큰을 즉시 무효화한다.
     */
    @Transactional
    fun withdraw(userId: UUID) {
        findUser(userId).delete()
        tokenService.revokeAll(userId.toString())
    }
}
```

---

## 성능 최적화: 매 API 요청마다 Redis를 조회할 때의 부하 방지 기법

"순수 무상태 JWT의 장점은 I/O 없이 CPU 서명 연산만으로 인가를 끝내는 것인데, 매 요청마다 Redis를 조회하면 부하가 생기지 않는가?"라는 의문이 들 수 있습니다. 이 점을 보완하기 위해 다음과 같은 설계 원칙을 적용했습니다.

### 1. 선(先) 서명 검증, 후(後) Redis 조회
공격자가 임의로 위조한 비정상 JWT나 이미 만료된 쓰레기 토큰이 무차별적으로 들어올 때 매번 Redis 네트워크 I/O가 발생하면 Redis 서버에 DoS 공격이 될 수 있습니다.
따라서 `JwtConfig` 코드에서 볼 수 있듯이, **1단계로 CPU 기반의 암호학적 서명(Signature)과 `exp` 만료 검증을 먼저 통과한 토큰에 한해서만** 2단계로 Redis `token:version` 조회를 수행하도록 구성했습니다.

### 2. 단일 Key 단순 GET 연산 ($O(1)$)
Redis에서 Set을 조회하거나 키 패턴 검색(`KEYS`)을 수행하지 않고, 정확히 `token:version:{userId}` 단일 String Key에 대해 인메모리 `GET` 연산만 수행합니다. 일반적으로 Redis 단일 인스턴스에서 단순 GET 연산은 **0.1~0.3ms 미만**으로 처리되므로 애플리케이션 응답 속도에 주는 영향이 극히 미미합니다.

### 3. 고트래픽 대응: 로컬 캐시(Caffeine) 계층 도입 (선택적)
초당 수만 건 이상의 트래픽이 집중되는 대규모 환경이라면, 앞단에 1~3초의 아주 짧은 TTL을 가진 로컬 인메모리 캐시(Caffeine Cache)를 둘 수 있습니다. 1~3초의 무효화 지연(Eventual Consistency)을 용인하는 대신, 동일 사용자의 연속 API 호출 시 발생하는 Redis I/O를 95% 이상 절감할 수 있습니다.

---

## 검증 및 결과 확인

실제 구현된 API를 호출하여 전체 로그아웃 및 잔여 토큰 즉시 무효화 동작을 검증해 보았습니다.

### 1. 전체 로그아웃 API 호출 (`POST /api/v1/auth/logout-all`)

다양한 기기(PC 브라우저, 모바일 앱 등)에 로그인되어 있는 상태에서 전체 로그아웃 엔드포인트를 호출합니다.

```bash
curl -X POST https://api.namju.kim/api/v1/auth/logout-all \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI..."
```

![전체 로그아웃 API 성공 응답 화면](/assets/images/2026-10-25/logout-all-api-response.png)

요청 즉시 200 OK 응답을 반환하며 내부적으로 `tokenVersions.revoke(userId)`가 트리거되어 해당 유저의 최신 토큰 버전이 갱신됩니다.

### 2. 잔여 유효시간이 남은 기존 액세스 토큰으로 접근 시도

전체 로그아웃 전에 발급받아 **아직 만료 시간(`exp`)이 28분이나 남아 있는 이전 액세스 토큰**을 헤더에 실어 내 정보 조회(`GET /api/v1/users/me`)를 시도했습니다.

```bash
curl -X GET https://api.namju.kim/api/v1/users/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI... (로그아웃 이전 토큰)"
```

![폐기된 토큰 접근 차단 401 응답 화면](/assets/images/2026-10-25/revoked-token-access-denied-401.png)

서명 자체는 유효하지만 `ActiveTokenValidator`에서 토큰에 담긴 `token_version`과 Redis의 현재 버전이 불일치함을 감지하고, **401 Unauthorized (`AUTH-008: 폐기된 토큰입니다. 다시 로그인해 주세요.`)**로 즉시 요청을 차단했습니다.

### 3. Redis 저장소 상태 및 메모리 확인

`redis-cli`를 통해 Redis 내부의 키 상태와 TTL을 조회해 보았습니다.

![Redis 토큰 버전 및 TTL 검증 터미널 화면](/assets/images/2026-10-25/redis-user-invalidated-timestamp.png)

- `token:version:{userId}` 키에 새로운 UUID가 정상 저장되어 있습니다.
- 키의 TTL은 리프레시 토큰의 최대 수명(약 14일)으로 자동 설정되어 있어, 별도의 배치 청소 작업 없이도 잔여 토큰이 모두 만료되면 메모리에서 자동 소멸합니다.
- 사용자당 메모리 점유율은 약 **88 Bytes**에 불과하여, 대규모 사용자 풀에서도 매우 가볍게 동작함을 확인할 수 있습니다.

---

## 정리

무상태 JWT의 높은 확장성을 유지하면서도 보안 요구사항(전체 로그아웃, 회원 탈퇴 즉시 차단)을 만족하기 위해 다음과 같은 설계를 적용했습니다.

1. **토큰 버전 패턴**: 개별 JTI 블랙리스트 방식의 메모리 폭증과 타임스탬프 방식의 시계 오차/경합 문제를 동시에 해결했습니다.
2. **원자적 TTL 연장 (`GETEX`)**: 토큰 발급 시마다 버전 키의 TTL을 원자적으로 연장하여, 활성 세션의 무효화 표식이 먼저 증발하는 엣지 케이스를 방지했습니다.
3. **단계별 검증 파이프라인**: Spring Security 디코더에서 CPU 암호 서명 검증을 1차로 수행한 후 유효한 토큰에 대해서만 Redis를 조회하도록 최적화하여 인프라 부하를 최소화했습니다.

무상태 아키텍처와 즉각적인 세션 제어 사이에서 고민하고 계신 분들에게 실용적인 레퍼런스가 되기를 바랍니다. 실제 전체 소스코드는 아래 GitHub 저장소에서 확인하실 수 있습니다.

{% linkpreview "https://github.com/cmsong111/cotton-bat-server" %}
