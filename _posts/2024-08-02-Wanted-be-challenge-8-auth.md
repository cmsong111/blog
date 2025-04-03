---
title: 프리온보딩 BE 챌린지 8월 사전 과제 - 회원 API
description: JWT 인증을 이용한 회원 API 제작
date: 2024-08-02 12:00:00 +0000
categories: [spring-boot, wanted-be-challenge]
tags: [원티드, 백엔드, 챌린지, spring-boot]
mermaid: true
image:
  path: https://static.wanted.co.kr/images/events/4818/6f9f8e47.jpg
---

## 유저 관련 요구사항

유저와 관련된 요구사항은 다음과 같습니다.

- 이메일 - 이메일 형식에 맞는지 검증
- 휴대폰 번호 - 숫자와 하이폰으로 구성된 형식 검즘
- 작성자 - 아이디 대소문자 및 한글 이름 검즘
- 비밀번호 - 대소문자, 숫자 5개 이상, 특수문자 포함 2개 이상 검즘

## 유저 엔티티 설계

각 요구사항에 맞게 유저 엔티티를 설계해보겠습니다

> 스프링 시큐리티와 관련된 도메인과 유저 도메인은 분리하여 설계하였습니다.
>
> 스프링 시큐리티의 영역이 궁금하신 분들은 [시큐리티 설정](/posts/Wanted-be-challenge-8-security)을 참고하시기 바랍니다.
{: .prompt-info }

```kotlin
/** 유저 엔티티 */
@Entity
@Table(name = "users")
class User(
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    val id: Long = 0L,
    /** 유저 이메일 */
    @Column(unique = true)
    var email: String,
    /** 유저 이름 */
    var name: String,
    /** 유저 핸드폰 번호 */
    var phone: String,
    /** 유저 프로필 이미지 */
    var profileImage: String? = null,
    /** 유저 비밀번호 */
    var password: String,
    /** 유저 역할(권한) */
    @ElementCollection(fetch = FetchType.EAGER)
    @Enumerated(EnumType.STRING)
    var roles: MutableSet<UserRole> = mutableSetOf(UserRole.USER),
    override var createdAt: Instant = Instant.now(),
    override var updatedAt: Instant = Instant.now(),
) : BaseEntity() {
    companion object {
        /** 유저 생성 */
        fun create(email: String, name: String, phone: String, password: String ): User {
            return User(
                email = email,
                name = name,
                phone = phone,
                password = password,
                profileImage = "https://picsum.photos/id/100/200/200",
            )
        }
    }
}
```

## 회원가입 API

회원가입 API는 유저 정보를 입력받아 회원가입을 진행합니다.

회원가입 API에서 요구사항들을 검증하기 위해서 `Jakarta Validation`을 사용하였습니다.

해당 라이브러리를 활용하면 쉽게 유효성 검사를 진행할 수 있습니다.

| 어노테이션  | 설명                                  |
| ----------- | ------------------------------------- |
| `@NotNull`  | null이 아닌지 검증                    |
| `@NotBlank` | null이 아니고 빈 문자열이 아닌지 검증 |
| `@Email`    | 이메일 형식인지 검증                  |
| `@Pattern`  | 정규 표현식에 맞는지 검증             |
| `@Size`     | 문자열의 길이를 검증                  |
| `@Min`      | 숫자가 최소값 이상인지 검증           |
| `@Max`      | 숫자가 최대값 이하인지 검증           |

여기서 한가지 주의할 점은 **Kotlin**에서는 `@NotNull` 어노테이션을 사용하더라도, nullable한 타입을 사용하지 않는다면, 체크가 되지 않습니다.

객체를 생성하는 시점에서 바로 예외가 발생하기 때문입니다.

따라서, `@NotNull` 어노테이션이 아닌, `@NotBlank` 어노테이션을 사용하여 빈 문자열인지 검증하는 것이 좋습니다.

### 회원가입 요청 폼
```kotlin
/** 회원가입 폼 */
@Schema(description = "회원가입 폼")
data class RegisterRequest(
    /** 이메일 */
    @field:Schema(description = "이메일", example = "test12345@test.com")
    @field:Email(message = "이메일 형식이 올바르지 않습니다")
    val email: String,
    /** 전화번호 */
    @field:Pattern(
        regexp = "^01(?:0|1|[6-9])-(?:\\d{3}|\\d{4})-\\d{4}\$",
        message = "전화번호 형식이 올바르지 않습니다",
    )
    @field:Schema(description = "전화번호", example = "010-1234-5678")
    @field:NotNull(message = "전화번호를 입력해주세요")
    val phone: String,
    /** 이름 */
    @field:Schema(description = "이름", example = "홍길동")
    @field:NotBlank(message = "이름을 입력해주세요")
    @field:Pattern(
        regexp = "^[가-힣a-zA-Z]{2,10}\$",
        message = "이름은 한글 또는 영어로만 작성해주세요",
    )
    val name: String,
    /** 비밀번호 */
    @field:Schema(description = "비밀번호", example = "Password1234~!")
    @field:NotBlank(message = "비밀번호를 입력해주세요")
    @field:Pattern(
        regexp = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[^\\da-zA-Z]).{5,}\$",
        message = "비밀번호는 대소문자, 숫자, 특수문자를 포함한 5자 이상이어야 합니다",
    )
    val password: String,
)
```

### AuthController

회원가입 API는 `POST /api/v1/auth/register`로 요청을 보냅니다.

다음과 같이  `@sRequetBody` 어노테이션을 사용하여 body를 전달받으며 `@Valid` 어노테이션을 사용하여 유효성 검사를 진행합니다.

```kotlin
/**
 * 회원가입 API
 * @param registerRequest 회원가입 요청 정보
 * @return JWT 토큰
 */
@PostMapping("/register")
@Operation(summary = "회원가입 API", description = "Create a new user account")
fun register(
    @Valid @RequestBody registerRequest: RegisterRequest,
): ResponseEntity<TokenResponse> {
    return ResponseEntity.ok(authService.register(registerRequest))
}
```
### AuthService
회원가입 API에서 유저 정보를 저장하는 로직을 담당합니다.

회원가입 시 이메일 중복 검사를 진행하며, 비밀번호는 `BCryptPasswordEncoder`를 사용하여 암호화합니다.

이후, JWT 토큰을 발급하여 반환합니다.

```kotlin
@Service
class AuthService(
    private val userRepository: UserRepository,
    private val jwtProvider: JwtProvider,
    private val passwordEncoder: PasswordEncoder,
) {
    /**
     * 회원가입
     * @param registerRequest 회원가입 요청 폼
     * @return JWT 토큰
     */
    @Transactional
    fun register(registerRequest: RegisterRequest): TokenResponse {
        // 중복 확인
        if (userRepository.existsByEmail(registerRequest.email)) {
            throw BusinessException(ErrorCode.USER_ALREADY_EXISTS)
        }

        val user = User(
            email = registerRequest.email,
            name = registerRequest.name,
            phone = registerRequest.phone,
            password = passwordEncoder.encode(registerRequest.password),
        )
        userRepository.save(user)
        return TokenResponse(token = jwtProvider.createToken(user))
    }
}
```

### API 요청 결과
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QHRlc3QuY29tIn0.anftQ7WoGLCy2PzchcnQy1wLi_EBoF9zSmsQBoRjoyQ"
}
```

## 로그인 API (JWT 토큰 발급)

### LoginRequest Form

```kotlin
/** 로그인 폼 */
@Schema(description = "로그인 폼")
data class LoginRequest(
    /** 이메일 */
    @field:Schema(description = "이메일", example = "test@test.com")
    @field:Email(message = "이메일 형식이 아닙니다")
    val email: String = "",
    /** 비밀번호 */
    @field:Schema(description = "비밀번호", example = "Password1234~!")
    @field:NotBlank(message = "비밀번호를 입력해주세요")
    val password: String,
)
```

### AuthController

```kotlin
@RestController
@RequestMapping("/api/v1/auth")
class AuthController(
    private val authService: AuthService,
) {
    @PostMapping("/login")
    @Operation(summary = "로그인 API", description = "Authenticate the user and return the JWT token")
    fun login(
        @Valid @RequestBody loginRequest: LoginRequest,
    ): ResponseEntity<TokenResponse> {
        return ResponseEntity.ok(
            authService.login(
                email = loginRequest.email,
                password = loginRequest.password,
            ),
        )
    }
  }
```

### AuthService
```kotlin
@Service
class AuthService(
    private val userRepository: UserRepository,
    private val jwtProvider: JwtProvider,
    private val passwordEncoder: PasswordEncoder,
) {
    @Transactional(readOnly = true)
    fun login(
        email: String,
        password: String,
    ): TokenResponse {
        // 유저 조회
        val user = userRepository.findByEmail(email)
            ?: throw LoginFailedException()

        // 비밀번호 확인
        if (!passwordEncoder.matches(password, user.password)) {
            throw LoginFailedException()
        }
        // 로그인 성공 및 토큰 발급
        return TokenResponse(
            token = jwtProvider.createToken(user),
        )
    }
}
```

### API 요청 결과

로그인 성공 시 다음과 같이 정상적으로 토큰이 발급된 것을 확인할 수 있습니다.

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QHRlc3QuY29tIn0.anftQ7WoGLCy2PzchcnQy1wLi_EBoF9zSmsQBoRjoyQ"
}
```

{% linkpreview "https://github.com/cmsong111/Wanted-PreOnBoarding-Backend-Challenge" %}

