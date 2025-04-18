---
title: 프리온보딩 BE 챌린지 8월 사전 과제 - 이미지 업로드 기능
description: 인터페이스를 통한 다양한 구현체 생성
date: 2024-08-03 12:00:00 +0000
categories: [spring-boot, wanted-be-challenge]
tags: [원티드, 백엔드, 챌린지, spring-boot]
mermaid: true
image:
  path: https://static.wanted.co.kr/images/events/4818/6f9f8e47.jpg
---

## Storage Service Class 다이어그램

```mermaid
classDiagram
    class StorageService {
        <<interface>>
        +uploadFile(file: MultipartFile): String
    }

    class AWSS3StorageService {
        -amazonS3Client: AmazonS3Client
    }

    class MinIOStorageService {
        -restClient: RestClient
    }

    class MockStorageService

    StorageService <|.. AWSS3StorageService
    StorageService <|.. MinIOStorageService
    StorageService <|.. MockStorageService
```


{% linkpreview "https://github.com/cmsong111/Wanted-PreOnBoarding-Backend-Challenge" %}
