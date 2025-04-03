---
title: 프리온보딩 BE 챌린지 8월 사전 과제 - API 통합 테스트
description: JUnit5와 WebTestClient을 활용한 API 통합 테스트
date: 2024-08-08 12:00:00 +0000
categories: [spring-boot, wanted-be-challenge]
tags: [원티드, 백엔드, 챌린지, spring-boot]
mermaid: true
image:
  path: https://static.wanted.co.kr/images/events/4818/6f9f8e47.jpg
---

## 테스트 케이스 설계
API 통합 테스트는 API의 동작을 검증하는 중요한 과정입니다.

API 통합 테스트는 실제로 API를 호출하여 응답을 확인하는 방식으로 진행됩니다. 
 
![테스트 스크린샷](/assets//images/2024-08-08/screenshot-1.png)

### API 통합 테스트 시나리오

API 통합테스트를 진행할 때에는, 내가 어떤 API를 호출하고, 어떤 응답을 기대하는지에 대한 시나리오를 작성해야 합니다.

다음은 제가 생각하는 API 통합 테스트 시나리오 중 일부입니다.

#### 회원 API
- 회원 생성 API - POST : `/api/v1/auth/signup`
  - 201 Created - 회원 등록 성공
  - 400 Bad Request - 회원 등록 실패 (이름, 이메일, 비밀번호 없음 등)

- 회원 로그인 API - POST : `/api/v1/auth/signin`
  - 200 OK - 로그인 성공
  - 400 Bad Request - 로그인 실패 (이메일, 비밀번호 없음 등)

#### 게시글 API 
- 게시글 목록 조회 API - GET : `/api/v1/posts`
  - 200 OK - 게시글 조회 성공
  - 404 Not Found - 게시글 없음

- 게시글 생성 API - POST : `/api/v1/posts`
  - 201 Created - 게시글 등록 성공
  - 400 Bad Request - 게시글 등록 실패 (제목, 내용, 작성자 없음 등)
  - 401 Unauthorized - 로그인 필요

- 게시글 수정 API - PATCH : `/api/v1/posts/{postId}`
  - 200 OK - 게시글 수정 성공
  - 400 Bad Request - 게시글 수정 실패 (제목, 내용, 작성자 없음 등)
  - 401 Unauthorized - 로그인 필요
  - 403 Forbidden - 권한 없음 (작성자와 수정자가 다를 경우)
  - 404 Not Found - 게시글 없음

## API 통합 테스트 코드 작성

### Fixtures를 활용한 테스트 데이터 생성
Fixtures는 테스트에서 사용할 데이터를 미리 정의해두고, 테스트 실행 시 해당 데이터를 불러와 사용하는 방법입니다.

Fixtures를 사용하면 테스트 코드가 간결해지고, 데이터 생성 로직을 재사용할 수 있어 유지보수성이 향상됩니다.

{% linkpreview "https://docs.gradle.org/current/userguide/java_testing.html#sec:java_test_fixtures" %}

data.sql 파일을 생성해서 더미데이터를 미리 입력해두고, 테스트 시 해당 데이터를 활용한다면, 더욱 편리하게 테스트를 진행할 수 있습니다.

### JUnit5와 WebTestClient을 활용한 API 통합 테스트

JUnit5와 WebTestClient을 활용하여 API 통합 테스트를 진행합니다.

테스트 코드를 작성할 때에는 `DisplayName` 어노테이션을 활용하여 테스트 가시성을 높이고, 이너클래스와 `@Nested` 어노테이션을 활용하여 테스트 그룹을 나누면, 가시성을 높일 수 있습니다.

아래처럼 Nested 클래스를 활용하여 테스트 그룹을 나누어 작성할 수 있습니다.

```kotlin
@DisplayName("Articles API 통합 테스트")
@DirtiesContext
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class ArticlesApiTest {
    @Nested
    @DisplayName("GET /api/v1/articles")
    inner class GetArticles {
        @Test
        @DisplayName("200 OK")
        fun success() {
            // TODO : 테스트 코드 작성
        }

        @Test
        @DisplayName("400 Bad Request (잘못된 요청)")
        fun badRequest() {
            // TODO : 테스트 코드 작성
        }
    }

    @Nested
    @DisplayName("POST /api/v1/articles")
    inner class PostArticles {
        @Test
        @DisplayName("201 Created")
        fun success() {
            // TODO : 테스트 코드 작성
        }

        @Test
        @DisplayName("400 Bad Request (@Valid)")
        fun badRequest() {
            // TODO : 테스트 코드 작성
        }

        @Test
        @DisplayName("401 Unauthorized")
        fun unauthorized() {
            // TODO : 테스트 코드 작성
        }
    }
}
```

{% linkpreview "https://github.com/cmsong111/Wanted-PreOnBoarding-Backend-Challenge" %}
