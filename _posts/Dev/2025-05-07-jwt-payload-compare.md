---
title: 서비스별 JWT Payload 구조 비교와 토큰 설계 기준
description: JWT의 등록·공개·비공개 클레임 분류와 실제 서비스별 JWT Payload 구조를 비교 정리합니다.
date: 2025-05-08 12:00:00 +0900
tags: [jwt, security, oauth2]
image:
  path: /assets/images/2025-05-07/jwt-thumbnail.png
---

> ChatGPT, Velog, OKKY에서 실제로 발급되는 JWT를 디코딩해 Payload 구조를 비교하고, 동아리 프로젝트의 토큰 설계에 반영할 기준을 정리합니다.

## JWT Payload 분류

JWT의 Payload에 담기는 값을 클레임(Claim)이라고 부르며, RFC 7519는 클레임을 세 가지로 분류합니다.

### 등록된 클레임(Registered Claims)
> 등록 Claim은 RFC 7519에 이름과 의미가 정의된 표준 Claim입니다. 모두 선택 사항이지만, 상호 운용성을 위해 용도에 맞게 사용하는 것이 권장됩니다.

| Claim Name | 설명           | 예시                                 |
| ---------- | -------------- | ------------------------------------ |
| iss        | JWT 발급자     | https://velog.io                     |
| sub        | JWT 주제       | access_token                         |
| aud        | JWT 사용처     | https://velog.io                     |
| exp        | 만료 시간      | 1747210103 (Unix Timestamp)          |
| nbf        | 사용 가능 시간 | 1747210103  (Unix Timestamp)         |
| iat        | 발급 시간      | 1747123703 (Unix Timestamp)          |
| jti        | JWT ID         | 123e4567-e89b-12d3-a456-426614174000 |

### 공개 클레임(Public Claims)

> 공개 Claim은 여러 서비스가 함께 사용할 수 있도록 공개적으로 정의하는 Claim입니다. <br>
> 다른 서비스와 이름이 충돌하지 않도록 IANA에 등록하거나 URI 형태의 Claim Name을 사용합니다.

| Claim Name                    | 설명          | 예시                                                 |
| ----------------------------- | ------------- | ---------------------------------------------------- |
| "https://example.com/profile" | 사용자 프로필 | { "email": "test@test.com", "email_verified": true } |
| "https://example.com/auth"    | 사용자 인증   | { "user_id": "user-HN29fn12dcj2skw9" }               |

### 비공개 클레임(Private Claims)

> 비공개 Claim은 토큰을 주고받는 당사자끼리만 합의해 사용하는 Claim입니다. 이름 충돌 가능성을 감수하는 대신 짧고 간단하게 정의할 수 있습니다.

| Claim Name | 설명        | 예시   |
| ---------- | ----------- | ------ |
| "user_id"  | 사용자 ID   | 100000 |
| "roles"    | 사용자 권한 | "101"  |

> 고유값처럼 보이는 값과 개인정보는 수정하거나 가려 두었습니다.
{: .prompt-info }

## ChatGPT

### Access Token

```json
{
  "alg": "RS256",
  "kid": "19344e65-bbc9-44d1-a9d0-f957b079bd0e",
  "typ": "JWT"
}
```

```json
{
  "aud": [
    "https://api.openai.com/v1"
  ],
  "client_id": "app_X8zY6vW2fj128rhSH2E7nK1jL5gH",
  "exp": 1748022144,
  "https://api.openai.com/auth": {
    "user_id": "user-HN29fn12dcj2skw9"
  },
  "https://api.openai.com/profile": {
    "email": "user@example.com",
    "email_verified": true
  },
  "iat": 1747158143,
  "iss": "https://auth.openai.com",
  "jti": "d6241dcd-259a-4158-ac5b-2c3c12968b62",
  "nbf": 1747158143,
  "pwd_auth_time": 1743693952591,
  "scp": [
    "openid",
    "email",
    "profile",
    "offline_access",
    "model.request",
    "model.read",
    "organization.read",
    "organization.write"
  ],
  "session_id": "authsess_AhQ5wmSEPI5pfGgudYbG13c4",
  "sub": "google-oauth2|981249867123987"
}
```

## Velog

### Access Token

```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

```json
{
  "user_id": "3cc6dd1b-def8-4323-8e05-217fb6f79fb4",
  "iat": 1747123703,
  "exp": 1747210103,
  "iss": "velog.io",
  "sub": "access_token"
}
```

### Refresh Token

```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

```json
{
  "user_id": "aff46ade-e5e5-4f22-8794-c3948974726d",
  "token_id": "c798e49a-8236-4157-a5b3-5bcb2ea4228c",
  "iat": 1746635394,
  "exp": 1749227394,
  "iss": "velog.io",
  "sub": "refresh_token"
}
```

## OKKY

### Access Token

```json
{
  "alg": "HS512"
}
```

```json
{
  "userId": 100000,
  "avatarId": 196433,
  "personId": 210147,
  "roles": "101",
  "iat": 1747206444,
  "exp": 1747210044
}
```


### Refresh Token

```json
{
  "alg": "HS512"
}
```

```json
{
  "tokenId": "23d5351d-6d49-4f90-8514-cc3bd6455bd5",
  "userId": 100000,
  "iat": 1747206444,
  "exp": 1749798444
}
```


## 서비스별 비교

| 항목 | ChatGPT | Velog | OKKY |
| :--- | :--- | :--- | :--- |
| 서명 알고리즘 | RS256 (비대칭키) | HS256 (대칭키) | HS512 (대칭키) |
| 키 식별자(`kid`) | 있음 | 없음 | 없음 |
| 사용자 식별 | `sub` + 공개 클레임 | `user_id` (UUID) | `userId` (숫자) |
| 권한 정보 | `scp` 배열 | 없음 | `roles` |
| 토큰 종류 구분 | 별도 발급 체계 | `sub`로 구분 | Refresh에 `tokenId` |
| 발급자(`iss`) | 있음 | 있음 | 없음 |

비교해 보면 몇 가지 차이가 눈에 띕니다.

- **서명 방식**: ChatGPT는 RS256과 `kid`를 사용합니다. 공개키로 누구나 검증할 수 있고, `kid`로 여러 키를 구분하므로 키를 교체(rotation)하기 쉽습니다. Velog와 OKKY는 대칭키(HMAC) 방식이라 검증하는 쪽도 같은 비밀키를 알아야 합니다.
- **Refresh Token의 최소화**: Velog와 OKKY의 Refresh Token에는 사용자 식별자와 토큰 ID 정도만 들어 있습니다. 토큰 ID가 있으면 서버에서 특정 Refresh Token만 골라 폐기할 수 있습니다.
- **식별자 노출**: OKKY는 순차적인 숫자 ID를 그대로 담고 있습니다. Payload는 Base64URL 인코딩일 뿐 암호화가 아니므로, 누구나 디코딩해 내부 ID 규모를 짐작할 수 있습니다.

> JWT의 Payload는 서명으로 위·변조만 막을 뿐 내용은 누구나 읽을 수 있습니다. 이메일 같은 개인정보나 내부 시스템 정보는 꼭 필요한 경우가 아니면 담지 않아야 합니다.
{: .prompt-warning }

## 정리

ChatGPT의 토큰이 확장성을 가장 많이 고려한 구조라고 느꼈습니다. 비대칭키와 `kid`, 범위(`scp`) 기반 권한까지 갖추고 있어 외부 API 서버가 독립적으로 토큰을 검증할 수 있습니다.

그동안 동아리 프로젝트에서는 Refresh Token을 크게 신경 쓰지 않고 Access Token의 `exp`만 길게 설정했습니다. Velog처럼 Refresh Token에는 재발급에 필요한 최소 정보만 담고, 토큰 ID로 폐기할 수 있게 발급하는 편이 훨씬 안전하다는 것을 배웠습니다. 다음 토큰 설계 때는 아래 항목을 먼저 점검하려고 합니다.

- [ ] Access Token의 만료 시간을 짧게 두고 Refresh Token으로 재발급하는가?
- [ ] Refresh Token에 토큰 ID(`jti` 등)를 넣어 개별 폐기가 가능한가?
- [ ] Payload에 개인정보나 순차 ID 같은 내부 정보가 노출되지 않는가?
- [ ] 여러 서버가 검증해야 한다면 비대칭키와 `kid` 기반 키 교체를 고려했는가?
