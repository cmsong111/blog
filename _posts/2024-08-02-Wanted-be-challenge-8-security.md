---
title: 프리온보딩 BE 챌린지 8월 사전 과제 - 스프링 시큐리티 설정 
description: JWT 인증을 이용한 스프링 시큐리티 설정
date: 2024-08-02 15:00:00 +0000
categories: [spring-boot, wanted-be-challenge]
tags: [원티드, 백엔드, 챌린지, spring-boot]
mermaid: true
image:
  path: https://static.wanted.co.kr/images/events/4818/6f9f8e47.jpg
---


## UserDetailsService 및 UserDetails 구현

스프링 시큐리티에서 사용자 정보를 가져오기 위해서는 `UserDetailsService` 인터페이스를 구현해야 합니다.

`UserDetailsService` 인터페이스는 스프링 필터를 통과하기 위한 사용자 정보를 가져오는 메소드를 정의합니다.

User엔티티에 `UserDetails`를 구현하지 않았음으로, 다음과 같이 `UserDetails`를 생성하여 반환하게끔 세팅해줍니다.

```kotlin
@Service
class CustomUserDetailsService(
    private val userRepository: UserRepository,
) : UserDetailsService {
    /**
     * 스프링 시큐리티에서 사용되는 사용자명으로 정보 조회하는 메소드
     * @param username 사용자명
     * @return 사용자 정보
     */
    override fun loadUserByUsername(username: String): UserDetails {
        val user: User = userRepository.findByEmail(username)
            ?: throw IllegalArgumentException("User not found with email: $username")

        return org.springframework.security.core.userdetails.User.builder()
            .username(user.email)
            .password(user.password)
            .authorities(user.roles)
            .build()
    }
}
```

## JWT에 대한 설정

기본적인 세션 인증방식을 활용하였다면, `UserDetailsService` 를 생성함으로써 끝낼 수 있지만, JWT를 사용하기 위해서는 조금 복잡한 세팅이 필요합니다.

한번 천천히 살펴보도록 하겠습니다.

### Header Util - 헤더에서 Bearer 토큰을 추출하는 유틸리티

HttpServletRequest 에서 Bearer 토큰을 추출하는 유틸리티 클래스를 생성합니다.

```kotlin
object TokenResolver {
    /**
     * 헤더에서 Bearer 토큰을 추출한다.
     * @param request HttpServletRequest
     * @return 토큰
     */
    fun resolveToken(request: HttpServletRequest): String? {
        // 헤더에서 토큰 추출
        val tokenFromHeader: String? = request.getHeader(AUTHORIZATION_HEADER)
        if (tokenFromHeader != null && tokenFromHeader.startsWith(BEARER_PREFIX)) {
            return tokenFromHeader.substring(7)
        }
        return null
    }

    const val AUTHORIZATION_HEADER = "Authorization"
    const val BEARER_PREFIX = "Bearer "
}
```

### JWT 토큰 프로바이더

JWT토큰에는 보통 다음과 같은 정보가 포함됩니다.

| 이름       | 설명                                    | 예시                                 |
| ---------- | --------------------------------------- | ------------------------------------ |
| jti        | JWT의 고유 식별자                       | 550e8400-e29b-41d4-a716-446655440000 |
| sub        | 주제 (Subject), 일반적으로 사용자 ID    | 12345                                |
| iss        | 발급자 (Issuer)                         | "my-auth-server"                     |
| iat        | 발급 시간 (Issued At), UNIX 타임스탬프  | 1712236800 (2024-04-04T00:00:00Z)    |
| exp        | 만료 시간 (Expiration), UNIX 타임스탬프 | 1712240400 (2024-04-04T01:00:00Z)    |
| aud (선택) | 대상 Audience (토큰이 사용될 대상)      | "my-client-app"                      |


따라서, 다음과 같이 JWT 토큰을 담당하는 클래스를 하나 생성하면 편리하게 사용할 수 있습니다.

```kotlin
data class AuthenticatedUser(
    /** JWT ID */
    val jti: String,
    /** 사용자 ID */
    val userId: Long,
    /** 사용자 이메일 */
    val email: String,
    /** 사용자 역할 */
    val roles: Set<UserRole>,
    /** 발급자 */
    val issuer: String,
    /** 발급 시간 */
    val issuedAt: Instant,
    /** 만료 시간 */
    val expiry: Instant,
)
```

JWT 프로바이더에서는 JWT 토큰을 생성하고, 검증하는 메소드를 구현합니다.

JWT Payload를 클래스로 만들어두었기 떄문에, 해당 값으로 decode 하면 매우 편리합니다

```kotlin
@Component
@EnableConfigurationProperties(JwtProperties::class)
class JwtProvider(
    private val jwtProperties: JwtProperties,
) {
    private val key: SecretKey = Keys.hmacShaKeyFor(jwtProperties.secret.toByteArray())

    fun createToken(
        user: User,
        expiry: Long? = null,
    ): String {
        val now = Instant.now()
        return Jwts.builder()
            .id(UUID.randomUUID().toString())
            .subject(user.id.toString())
            .claim("email", user.email)
            .claim("roles", user.roles.joinToString(",") { it.authority })
            .issuer(jwtProperties.issuer)
            .issuedAt(Date.from(now))
            .expiration(Date.from(now.plusSeconds(expiry ?: jwtProperties.expiry)))
            .signWith(key)
            .compact()
    }

    fun decode(token: String): AuthenticatedUser {
        val claims = try {
            Jwts.parser()
                .verifyWith(key)
                .requireIssuer(jwtProperties.issuer)
                .build()
                .parseSignedClaims(token)
                .payload
        } catch (e: Exception) {
            throw IllegalArgumentException("Invalid token", e)
        }

        return AuthenticatedUser(
            jti = claims.id,
            userId = claims.subject.toLong(),
            email = claims["email"] as String,
            roles = (claims["roles"] as String).split(",").map { UserRole.valueOf(it.substring("ROLE_".length)) }.toSet(),
            issuer = claims.issuer,
            issuedAt = claims.issuedAt.toInstant(),
            expiry = claims.expiration.toInstant(),
        )
    }
}

```

### JWT 토큰 필터

JWT 토큰 필터는 스프링 시큐리티의 필터 체인에서 JWT 토큰을 검증하는 역할을 합니다. 

이 필터는 요청이 들어올 때마다 실행되며, JWT 토큰이 유효한지 확인하고, 유효한 경우 인증 정보를 SecurityContext에 저장합니다.

**SecurityContext에 authentication 속성의 경우 object 타입으로 설정되어 있습니다.**

즉, 어떠한 클래스라도 담을 수 있다는 의미입니다.

따라서, 여기에 `AuthenticatedUser` 객체를 를 담아주면 됩니다. 

그럼 바로 컨트룰러에서 `@AuthenticationPrincipal` 어노테이션을 통해 authentication에 세팅된 `AuthenticatedUser`를 주입받을 수 있습니다. [예시](#jwt-인증-사용-예제)


```kotlin
class JwtTokenFilter(
    private val tokenProvider: JwtProvider,
) : OncePerRequestFilter() {
    override fun doFilterInternal(
        request: HttpServletRequest,
        response: HttpServletResponse,
        filterChain: FilterChain,
    ) {
        TokenResolver.resolveToken(request)?.let { token ->
            val authenticatedUser: AuthenticatedUser = try {
                tokenProvider.decode(token)
            } catch (e: Exception) {
                logger.error(e.message)
                return
            }
            val authentication = UsernamePasswordAuthenticationToken(authenticatedUser, token, authenticatedUser.roles)
            SecurityContextHolder.getContext().authentication = authentication
        }
        filterChain.doFilter(request, response)
    }
}
```

### 시큐리티 설정

스프링 시큐리티 설정은 `SecurityConfig` 클래스를 통해 이루어집니다. 

이 클래스는 `@Configuration`과 `@EnableWebSecurity` 어노테이션을 사용하여 스프링 시큐리티를 활성화합니다.

```kotlin
/** 스프링 시큐리티 설정 */
@Configuration
@EnableWebSecurity
@EnableMethodSecurity
class SecurityConfig(
    private val userDetailsService: UserDetailsService,
    private val jwtProvider: JwtProvider,
    private val customAuthenticationEntryPoint: CustomAuthenticationEntryPoint,
    private val customAccessDeniedHandler: CustomAccessDeniedHandler,
) {
    @Bean
    fun securityFilterChain(http: HttpSecurity): SecurityFilterChain {
        return http
            .csrf { it.disable() }
            .headers { it.disable() }
            .sessionManagement { it.disable() }
            .authorizeHttpRequests {
                it
                    .anyRequest().permitAll()
            }
            .userDetailsService(userDetailsService)
            .addFilterBefore(JwtTokenFilter(jwtProvider), UsernamePasswordAuthenticationFilter::class.java)
            .exceptionHandling {
                it.authenticationEntryPoint(customAuthenticationEntryPoint)
                it.accessDeniedHandler(customAccessDeniedHandler)
            }
            .build()
    }
}
```

## JWT 인증 사용 예제

시큐리티 컨텍스트 에 담긴 `AuthenticatedUser`를 사용하여 인증된 사용자 정보를 가져올 수 있습니다.

`@AuthenticationPrincipal` 어노테이션을 사용하여 `AuthenticatedUser`를 주입받습니다.

그럼 위에서 세팅한대로, userID, email, roles 등의 정보를 사용할 수 있습니다.

```kotlin
/** User API 컨트롤러 */
@Tag(name = "User", description = "The user API")
@RestController
@RequestMapping("/api/v1/user")
class UserController(
    private val userService: UserService,
) {
    /**
     * 내 정보 조회 API
     * @param authenticatedUser 로그인 정보
     * @return 사용자 정보
     */
    @GetMapping
    @Operation(summary = "내 정보 조회 API")
    @SecurityRequirement(name = "Bearer Authentication")
    fun getUserInfo(
        @AuthenticationPrincipal authenticatedUser: AuthenticatedUser,
    ): ResponseEntity<User> {
        return ResponseEntity.ok(userService.getUser(authenticatedUser.email))
    }
}
```
###  API 반환 결과
```json
{
  "id": 4,
  "email": "test123456@test.com",
  "name": "홍길동",
  "phone": "010-1234-5678",
  "profileImage": null,
  "password": "$2a$10$MIXRQdEhf4uEuolEp/C5iOVP8BspmIwbqmz58yix94JNmBW/d/ply",
  "roles": [
    "USER"
  ],
  "createdAt": "2025-04-03T15:23:20.180573Z",
  "updatedAt": "2025-04-03T15:23:20.180573Z"
}
```

### 추가 활용 방안

`@Secured("ROLE_ADMIN")` 어노테이션을 사용하여 특정 역할을 가진 사용자만 접근할 수 있도록 설정할 수 있습니다.

이를 잘 활용하면, **[요구사항이었던 관리자는 모든 게시글 수정 및 삭제 가능]**과 같은 기능을 쉽게 구현할 수 있습니다.



{% linkpreview "https://github.com/cmsong111/Wanted-PreOnBoarding-Backend-Challenge" %}

