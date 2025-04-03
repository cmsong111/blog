---
title: 무료 더미 이미지 API
description: 
date: 2024-09-02 12:00:00 +0000
categories: [Development]
tags: [Dummy, API, Image]
image:
  path: https://picsum.photos/536/354
---

## 더미 이미지 API의 필요성

백엔드 개발을 진행하다보면, 더미 데이터를 채워야 하는 경우가 많습니다.

특히, 프론트엔드 측에서 이러한 요구를 해오는 경우가 많은데, 진짜 어쩔수 없는 부분인가 싶기도 합니다. 


## Lorem Picsum - 더미 이미지 API

제가 자주 사용하는 더미이미지 API는 [picsum.photos](https://picsum.photos/)입니다.

정말 간단하게 사용할 수 있습니다.

### 랜덤 이미지 

> https://picsum.photos/{width}/{height}
{: .prompt-info }

> 랜덤 이미지는 새로고침할 때마다 다른 이미지를 보여줍니다.<br>
> 한번 새로고침 해보세요.


- `width`와 `height`는 각각 가로, 세로 크기를 의미합니다.
- `hight`가 생략되면 정사각형으로 이미지가 생성됩니다.

| image | URL |
|-------|-----|
| ![image](https://picsum.photos/250/200) | [https://picsum.photos/300/200](https://picsum.photos/300/200) |
| ![image](https://picsum.photos/250) | [https://picsum.photos/250](https://picsum.photos/250) |

### 고정 이미지

> https://picsum.photos/id/{id}/{width}/{height}
{: .prompt-info }

- 랜덤 이미지 API와 동일하게 `width`와 `height`를 설정할 수 있습니다.
- `id`는 고정된 이미지를 가져오기 위한 값입니다
- `id`는 1부터 대략 1000까지의 값을 가집니다.

| image | URL |
|-------|-----|
| ![image](https://picsum.photos/id/250/250) | [https://picsum.photos/id/250/250](https://picsum.photos/id/250/250)
| ![image](https://picsum.photos/id/400/250/200) | [https://picsum.photos/id/400/250/200](https://picsum.photos/id/400/250/200) |

## Pravatar - 더미 프로필 이미지 API
> https://i.pravatar.cc/{width}
{: .prompt-info }

> https://i.pravatar.cc/{width}?img={id}
{: .prompt-info }

- `width`는 가로 크기를 의미합니다. (최대 1000)
- `id`는 고정된 이미지를 가져오기 위한 값입니다.

| image | URL |
|-------|-----|
| ![image](https://i.pravatar.cc/250) | [https://i.pravatar.cc/250](https://i.pravatar.cc/250) |
| ![image](https://i.pravatar.cc/250?img=1) | [https://i.pravatar.cc/250?img=1](https://i.pravatar.cc/250?img=1) |


## Logo Dev API - 기업 로고 API

> https://img.logo.dev/{domain}
{: .prompt-info }

- `domain`은 해당 기업의 도메인입니다.

| image | URL |
|-------|-----|
| ![image](https://img.logo.dev/google.com) | [https://img.logo.dev/google.com](https://img.logo.dev/google.com) |
| ![image](https://img.logo.dev/apple.com) | [https://img.logo.dev/apple.com](https://img.logo.dev/apple.com) |
| ![image](https://img.logo.dev/microsoft.com) | [https://img.logo.dev/microsoft.com](https://img.logo.dev/microsoft.com) |
| ![image](https://img.logo.dev/amazon.com) | [https://img.logo.dev/amazon.com](https://img.logo.dev/amazon.com) |
| ![image](https://img.logo.dev/facebook.com) | [https://img.logo.dev/facebook.com](https://img.logo.dev/facebook.com) |
| ![image](https://img.logo.dev/instagram.com) | [https://img.logo.dev/instagram.com](https://img.logo.dev/instagram.com) |
| ![image](https://img.logo.dev/youtube.com) | [https://img.logo.dev/youtube.com](https://img.logo.dev/youtube.com) |
| ![image](https://img.logo.dev/samsung.com) | [https://img.logo.dev/samsung.com](https://img.logo.dev/samsung.com) |
| ![image](https://img.logo.dev/lg.com) | [https://img.logo.dev/lg.com](https://img.logo.dev/lg.com) |
| ![image](https://img.logo.dev/naver.com) | [https://img.logo.dev/naver.com](https://img.logo.dev/naver.com) |