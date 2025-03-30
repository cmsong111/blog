---
title: Swing 프로젝트 리팩토링 계획 
description: 게시글 프로젝트 요구사항 분석
date: 2024-06-15 12:00:00 +0000
categories: [Refactoring Project, Java-Swing]
tags: [Java, Swing, Refactoring]
mermaid: true
image:
  path: https://velog.velcdn.com/images/cmsong111/post/24a8b41a-49a7-4813-87f2-fe4b172fa200/image.png
---

대학교에서 Java Swing으로 개발했던 프로젝트를 리팩토링을 진행할 예정이다.

해당 프로젝트의 경우 2학년 2학기 Java 수업에서 진행한 프로젝트로, **Java Swing**을 이용하여 음식점 정보를 조회하는 프로그램을 개발했다.

당시 스프링부트를 공부중이였기 때문에 백엔드 시스템을 구축하여 프론트엔드와 연동하는 방식으로 개발했다.

[음식점 정보 시스템 프로젝트-프론트](https://github.com/cmsong111/Restaurant-information-system/tree/main)

[음식점 정보 시스템 프로젝트-백엔드-참고사항](https://github.com/cmsong111/Restaurant-information-system-server/tree/main)

## 프로젝트 간단 코드 리뷰

1. 패키지 구조가 전혀 없다.
   패키지가 `DTO`, `PAGE`, `HTTP` 로 나눠져 있는 것을 확인할 수 있다.
   패키지명도 대문자로 시작하는 것을 확인할 수 있다.

2. Apache HttpClient 라이브러리를 사용하여 HTTP 통신을 진행하고 있다.
   반복되는 코드가 너무 많으며, Json을 gson 라이브러리로 변환하는 코드등 보일러플레이트 코드가 많다.

3. HomePage, DetailPage 클래스에 데이터를 static으로 보관하며 전역적으로 사용하는 코드가 있다.
   이는 객체지향적이지 않다.
   이를 안드로이드나 여타 프레임워크를 참고하여 리팩토링을 진행할 예정이다.

4. 폰트등 리소스를 직접 로드하는 코드가 있다.
   리소스를 전역적으로 관리하는 방법을 찾아보고 적용할 예정이다.(디자인 패턴 적용)

5. 로깅을 단순하게 출력하는 방식으로 진행하고 있다.
   로깅 라이브러리를 적용하여 리팩토링을 진행할 예정이다.

## 리팩토링 계획

1. 프로젝트 아키텍처 재설계
2. MVC 패턴 적용
3. Java -> Kotlin으로 전환 with 롬복 제거
4. Retrofit2 라이브러리를 활용하여 리팩토링
5. 리액티브 프로그래밍 적용(Reative or Coroutine)

게시글을 작성해 나가며 리팩토링을 진행할 예정이다.
