---
title: "Kotlin과 Spring Boot 기반 회원 및 인증 API 설계와 구현"
description: "Kotlin과 Spring Boot 환경에서 Soft Delete 기반 User 엔티티, @field: 유효성 검증, RTR 토큰 재발급, CQRS 회원 API를 설계하고 구현한 과정을 정리합니다."
date: 2024-08-02 12:00:00 +0000
tags: [spring-boot, kotlin, jwt, backend]
image:
  path: /assets/images/2024-08-01/wanted-challenge-banner.jpg
  alt: 프리온보딩 백엔드 챌린지 회원 및 인증 API 배너
---

> Kotlin과 Spring Boot 환경에서 `User` 엔티티 설계, `@field:` 유효성 검증, RTR 토큰 재발급, CQRS 기반 회원 조회·탈퇴 API 구현을 정리합니다.

> 기준 환경: Kotlin 1.9, Spring Boot 3.5, Java 21, Hibernate 6, Spring Data Redis
{: .prompt-info }

## User 엔티티 설계와 Soft Delete·지연 로딩 전략

`User` 엔티티는 `BaseTimeEntity`를 상속해 `createdAt`과 `updatedAt`을 JPA Auditing으로 관리합니다. 삭제에는 Hibernate 6.4의 `@SoftDelete(columnName = "is_deleted")`를 적용해 게시글·댓글의 참조 무결성을 보존합니다. `delete()` 호출 시 `UPDATE`가 실행되며 조회 시 `is_deleted = false` 조건이 자동 추가됩니다.

```kotlin
// src/main/kotlin/org/project/portfolio/user/domain/User.kt
@Entity
@Table(name = "users")
@SoftDelete(columnName = "is_deleted")
class User(
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    val id: Long = 0L,
    @Column(unique = true)
    var email: String,
    var name: String,
    var phone: String,
    var profileImage: String? = null,
    var password: String,
    @ElementCollection(fetch = FetchType.LAZY)
    @Enumerated(EnumType.STRING)
    var roles: MutableSet<UserRole> = mutableSetOf(UserRole.USER),
) : BaseTimeEntity() {
    companion object {
        fun create(email: String, name: String, phone: String, password: String): User {
            return User(
                email = email,
                name = name,
                phone = phone,
                password = password,
                profileImage = "https://i.pravatar.cc/300?img=${(1..70).random()}",
            )
        }
    }

    fun addRole(role: UserRole) {
        roles.add(role)
    }

    fun changePassword(encodedPassword: String) {
        this.password = encodedPassword
    }
}
```

`roles`는 `FetchType.EAGER` 대신 `FetchType.LAZY`를 선택했습니다. `EAGER`는 권한이 불필요한 조회에서도 매번 `user_roles` 추가 쿼리를 유발하기 때문입니다. `LAZY`를 쓰면 로그인·재발급·내 정보 조회 시점에만 로딩되며, `open-in-view: false` 환경에서는 트랜잭션 안에서 DTO로 변환해 `LazyInitializationException`을 예방합니다.

## Kotlin @field: 타깃 기반 요청 유효성 검증

Kotlin `data class`의 주 생성자 프로퍼티에 Jakarta Validation을 적용할 때는 `@field:` 타깃을 명시해야 합니다. 타깃을 생략하면 컴파일러가 `param -> property -> field` 순으로 어노테이션을 생성자 파라미터에 붙여 Hibernate Validator가 필드 검증을 건너뛰게 됩니다.

```kotlin
// src/main/kotlin/org/project/portfolio/auth/presentation/request/RegisterForm.kt
@Schema(description = "회원가입 폼")
data class RegisterForm(
    @field:Schema(description = "이메일", example = "test12345@test.com")
    @field:Size(max = 254, message = "이메일은 254자 이하로 입력해주세요")
    @field:Pattern(
        regexp = "^[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$",
        message = "이메일 형식이 올바르지 않습니다",
    )
    val email: String,
    @field:Pattern(
        regexp = "^01(?:0|1|[6-9])-(?:\\d{3}|\\d{4})-\\d{4}\$",
        message = "전화번호 형식이 올바르지 않습니다",
    )
    @field:Schema(description = "전화번호", example = "010-1234-5678")
    @field:NotNull(message = "전화번호를 입력해주세요")
    val phone: String,
    @field:Schema(description = "이름", example = "홍길동")
    @field:NotBlank(message = "이름을 입력해주세요")
    @field:Pattern(
        regexp = "^[가-힣a-zA-Z]{2,10}\$",
        message = "이름은 한글 또는 영어로만 작성해주세요",
    )
    val name: String,
    @field:Schema(description = "비밀번호", example = "Password1234~!")
    @field:NotBlank(message = "비밀번호를 입력해주세요")
    @field:Size(min = 8, max = 72, message = "비밀번호는 8자 이상 72자 이하로 입력해주세요")
    @field:Pattern(
        regexp = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[^\\da-zA-Z]).{5,}\$",
        message = "비밀번호는 대소문자, 숫자, 특수문자를 포함한 5자 이상이어야 합니다",
    )
    val password: String,
)
```

`PasswordChangeRequest`도 동일한 규칙을 적용했습니다. 이메일 상한 254자는 RFC 5321 표준, 비밀번호 상한 72자는 `BCryptPasswordEncoder`의 72바이트 입력 제한을 반영한 기준입니다.

```kotlin
// src/main/kotlin/org/project/portfolio/user/presentation/request/PasswordChangeRequest.kt
@Schema(description = "비밀번호 변경 요청")
data class PasswordChangeRequest(
    @field:Schema(description = "현재 비밀번호", example = "Password1234~!")
    @field:NotBlank(message = "현재 비밀번호를 입력해주세요")
    val currentPassword: String,
    @field:Schema(description = "새 비밀번호", example = "NewPassword1234~!")
    @field:NotBlank(message = "새 비밀번호를 입력해주세요")
    @field:Size(min = 8, max = 72, message = "비밀번호는 8자 이상 72자 이하로 입력해주세요")
    @field:Pattern(
        regexp = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[^\\da-zA-Z]).{5,}\$",
        message = "비밀번호는 대소문자, 숫자, 특수문자를 포함한 5자 이상이어야 합니다",
    )
    val newPassword: String,
)
```

## 인증 API와 RTR 기반 토큰 수명주기 관리

`AuthController`와 `AuthService`는 회원가입, 이메일 중복 확인, 로그인, 토큰 재발급, 로그아웃을 제공합니다.

| 기능 | 엔드포인트 | 성공 응답 | 실패 응답 |
| :--- | :--- | :--- | :--- |
| 회원가입 | `POST /api/v1/auth/register` | `201 Created` (`UserSummaryResponse`) | `409 Conflict` |
| 이메일 중복 확인 | `POST /api/v1/auth/register/email` | `200 OK` (`EmailCheckResponse`) | `409 Conflict` |
| 로그인 | `POST /api/v1/auth/login` | `200 OK` (`TokenResponse`) | `400 Bad Request` |
| 토큰 재발급 | `POST /api/v1/auth/refresh` | `200 OK` (`TokenResponse`) | `401 Unauthorized` |
| 로그아웃 | `POST /api/v1/auth/logout` | `204 No Content` | `401 Unauthorized` |

회원가입은 `201 Created`와 `Location: /api/v1/users/{id}`를 반환하며, 로그인 실패는 이메일 미존재와 비밀번호 불일치에 동일한 메시지를 내려 계정 열거를 차단합니다.

재발급은 **RTR(Refresh Token Rotation)**을 적용했습니다. 로그인 시 UUID `jit`을 Redis(TTL 7일)에 저장하고, `POST /api/v1/auth/refresh`에서 `Refresh-Token` 헤더의 `jit`을 검증한 뒤 기존 키를 삭제하고 새 `jit`을 발급합니다. `POST /api/v1/auth/logout`도 해당 `jit`을 삭제해 즉시 무효화합니다.

```kotlin
// src/main/kotlin/org/project/portfolio/auth/application/AuthService.kt
@Service
class AuthService(
    private val userRepository: UserRepository,
    private val refreshTokenRepository: RefreshTokenRedisRepository,
    private val jwtProvider: JwtProvider,
    private val passwordEncoder: PasswordEncoder,
) {
    @Transactional
    fun login(email: String, password: String): TokenResponse {
        val user: User = userRepository.findByEmail(email)
            ?: throw BadRequestException(message = "이메일 또는 비밀번호가 잘못되었습니다.")
        if (!passwordEncoder.matches(password, user.password)) {
            throw BadRequestException(message = "이메일 또는 비밀번호가 잘못되었습니다.")
        }

        val refreshToken: String = UUID.randomUUID().toString()
        refreshTokenRepository.save(RefreshToken(jit = refreshToken, email = user.email))

        return TokenResponse(
            accessToken = jwtProvider.createAccessToken(email = user.email, roles = user.roles),
            refreshToken = jwtProvider.createRefreshToken(email = user.email, jit = refreshToken),
        )
    }

    @Transactional
    fun reissueAccessToken(token: String): TokenResponse {
        val refreshToken: RefreshToken = jwtProvider.decodeRefreshToken(token)
        if (!refreshTokenRepository.existsById(refreshToken.jit)) {
            throw UnauthorizedException("리프레시 토큰이 존재하지 않습니다.")
        }

        val user: User = userRepository.findByEmail(refreshToken.email)
            ?: throw UnauthorizedException("유저가 존재하지 않습니다.")

        refreshTokenRepository.deleteById(refreshToken.jit)

        val newRefreshToken: String = UUID.randomUUID().toString()
        refreshTokenRepository.save(RefreshToken(jit = newRefreshToken, email = user.email))

        return TokenResponse(
            accessToken = jwtProvider.createAccessToken(email = user.email, roles = user.roles),
            refreshToken = jwtProvider.createRefreshToken(email = user.email, jit = newRefreshToken),
        )
    }

    @Transactional
    fun logout(token: String) {
        val refreshToken: RefreshToken = jwtProvider.decodeRefreshToken(token)
        refreshTokenRepository.deleteById(refreshToken.jit)
    }
}
```

## CQRS 기반 회원 서비스와 응답 DTO 분리

회원 도메인은 `UserQueryService`(`@Transactional(readOnly = true)`)와 `UserCommandService`로 CQRS를 적용해 Dirty Checking 비용을 줄이고 Read Replica 확장에 대비했습니다.

```kotlin
// src/main/kotlin/org/project/portfolio/user/application/UserQueryService.kt
@Service
@Transactional(readOnly = true)
class UserQueryService(
    private val userRepository: UserRepository,
) {
    fun getUser(email: String): User {
        return userRepository.findByEmail(email)
            ?: throw NotFoundException(User::class.java, mapOf("email" to email))
    }

    fun getUser(userId: Long): User {
        return userRepository.findByIdOrNull(userId)
            ?: throw NotFoundException(User::class.java, mapOf("userId" to userId))
    }
}
```

응답 DTO도 호출 대상에 따라 분리했습니다. 본인 조회(`GET /api/v1/user`)는 `@AuthenticationPrincipal jwt: Jwt`로 인증 주체를 확인해 `UserResponse`를 반환하고, 공개 프로필(`GET /api/v1/users/{userId}`)은 전화번호·권한·수정일시를 제외한 `UserPublicResponse`만 내려줍니다.

| 구분 | 엔드포인트 | 응답 DTO | 포함 필드 |
| :--- | :--- | :--- | :--- |
| 내 정보 조회 | `GET /api/v1/user` | `UserResponse` | `id`, `email`, `name`, `phone`, `profileImage`, `roles`, `createdAt`, `updatedAt` |
| 공개 프로필 | `GET /api/v1/users/{userId}` | `UserPublicResponse` | `id`, `email`, `name`, `profileImage`, `createdAt` |

```kotlin
// src/main/kotlin/org/project/portfolio/user/presentation/UserController.kt
@GetMapping("/user")
@PreAuthorize("isAuthenticated()")
fun getUserInfo(@AuthenticationPrincipal jwt: Jwt): ResponseEntity<UserResponse> {
    return ResponseEntity.ok(UserResponse.from(userQueryService.getUser(email = jwt.subject)))
}

@GetMapping("/users/{userId}")
fun getUserPublicProfile(@PathVariable userId: Long): ResponseEntity<UserPublicResponse> {
    return ResponseEntity.ok(UserPublicResponse.from(userQueryService.getUser(userId = userId)))
}
```

## 안전한 회원 탈퇴와 운영 시 주의사항

`email`의 `UNIQUE` 제약과 `@SoftDelete`를 함께 쓰면 탈퇴 행이 남아 동일 이메일 재가입 시 충돌이 발생합니다. `UserCommandService.deleteUser()`는 삭제 직전 `.deleted.<timestamp>` 접미사를 붙여 유니크 슬롯을 비웁니다.

```kotlin
// src/main/kotlin/org/project/portfolio/user/application/UserCommandService.kt
@Service
@Transactional
class UserCommandService(
    private val userRepository: UserRepository,
    private val passwordEncoder: PasswordEncoder,
) {
    fun changePassword(email: String, currentPassword: String, newPassword: String) {
        val user: User = userRepository.findByEmail(email)
            ?: throw NotFoundException(User::class.java, mapOf("email" to email))
        if (!passwordEncoder.matches(currentPassword, user.password)) {
            throw BadRequestException("현재 비밀번호가 일치하지 않습니다.")
        }
        user.changePassword(passwordEncoder.encode(newPassword))
    }

    fun deleteUser(email: String) {
        val user: User = userRepository.findByEmail(email)
            ?: throw NotFoundException(User::class.java, mapOf("email" to email))

        user.email = "${user.email}.deleted.${System.currentTimeMillis()}"
        userRepository.delete(user)
    }
}
```

DB 벤더별 부분 인덱스 없이 H2와 PostgreSQL 모두에서 재가입을 허용할 수 있습니다. 다만 운영 환경에서는 두 가지를 점검해야 합니다.

> **운영 시 주의사항**
> - **컬럼 길이 확보**: 최대 254자 이메일에 `.deleted.<timestamp>`(22자)가 붙으므로 DB `email` 컬럼 길이는 320자 이상으로 잡아야 `Data truncation`을 예방할 수 있습니다.
> - **세션 무효화**: 탈퇴 시 활성 Refresh Token을 함께 폐기하고, Access Token 즉시 차단이 필요하면 Redis 블랙리스트를 연동합니다.
{: .prompt-warning }

{% linkpreview "https://github.com/cmsong111/Wanted-PreOnBoarding-Backend-Challenge" %}
