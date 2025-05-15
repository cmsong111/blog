---
title: 서비스별 JWT Payload 비교
description:  
date: 2025-05-08 12:00:00 +0900
categories: [Development]
tags: [jwt, security]
image:
  path: https://velog.velcdn.com/images/u-nij/post/1cd61745-8a19-4905-91fa-3b44fd9a86fa/image.png
---
## JWT Payload 분류

### 등록된 클레임(Registered Claims)
> 등록 Claim은 JWT의 표준 Claim으로, JWT의 Payload에 포함되어야 하는 Claim입니다. 

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

> 공개 Claim은 JWT의 Payload에 포함될 수 있는 Claim으로, JWT의 Payload에 포함되어야 하는 Claim입니다. <br>
> 공개 Claim 다른 서비스와 충돌하지 않도록 URI로 시작하는 Claim Name을 사용해야 합니다.

| Claim Name                    | 설명          | 예시                                                 |
| ----------------------------- | ------------- | ---------------------------------------------------- |
| "https://example.com/profile" | 사용자 프로필 | { "email": "test@test.com", "email_verified": true } |
| "https://example.com/auth"    | 사용자 인증   | { "user_id": "user-HN29fn12dcj2skw9" }               |

### 비공개 클레임(Private Claims)

> 비공식 Claim은 백엔드와 프론트엔드 간에만 사용되는 Claim으로, 암호화 또는 서명을 필요로 합니다

| Claim Name | 설명        | 예시   |
| ---------- | ----------- | ------ |
| "user_id"  | 사용자 ID   | 100000 |
| "roles"    | 사용자 권한 | "101"  |

> 고유값처럼 보이는 값은 조금씩 수정해두었습니다.
{: .prompt-info }

## Chat GPT

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
    "email": "cmsong111@gmail.com",
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


## 결론

Chat GPT가 정말 잘 만들어서 사용중인것 같다

기존에, 리프래쉬토큰을 크게 신경쓰지않고, Access 토큰의 exp만 길게 설정했었는데, 벨로그처럼, 리프래쉬 전용으로 필요한 데이터만 담아서 발급하는게 좋을 것 같다는것을 느꼈다.
