---
title: 무료 더미 이미지 및 프로필 아바타 생성 API 모음
description: 백엔드 및 프론트엔드 목(Mock) 데이터 구축에 유용한 무료 더미 이미지, 프로필 아바타(DiceBear, UI Avatars, Pravatar), 플레이스홀더, 도메인 파비콘 API 엔드포인트와 실무 활용법을 정리합니다.
date: 2024-09-02 12:00:00 +0000
tags: [Dummy, API, Image, Mock-Data, Avatar]
image:
  path: https://picsum.photos/536/354
---

백엔드 API를 개발하거나 프론트엔드와 협업하다 보면, 실제 서비스 릴리즈 전 단계에서 화면을 구성하고 기능을 검증하기 위한 **더미(Mock) 데이터**가 필수적입니다.

특히 사용자 프로필 사진, 게시글 썸네일, 제휴사 로고 등의 이미지 데이터는 텍스트만 채워 넣었을 때보다 UI 레이아웃의 완성도와 여백을 파악하는 데 큰 차이를 만듭니다. 매번 로컬 정적 파일이나 S3 버킷에 테스트용 이미지를 번거롭게 업로드하지 않아도, **URL 파라미터만으로 즉시 고품질 이미지를 생성해 주는 신뢰성 높은 무료 API들**을 정리했습니다.

---

## 1. DiceBear - 결정론적(Deterministic) 벡터 프로필 아바타 API

가장 추천하는 프로필 아바타 생성 서비스는 [DiceBear](https://www.dicebear.com/)입니다. 

DiceBear의 가장 강력한 장점은 **시드(Seed) 기반의 결정론적 생성(Deterministic Generation)**입니다. 임의의 난수로 매번 바뀌는 것이 아니라, 고유한 식별자(이메일, 닉네임, UUID 등)를 `seed` 값으로 전달하면 **언제나 동일한 고유 캐릭터 아바타가 반환**됩니다.

> https://api.dicebear.com/9.x/{style}/{svg|png}?seed={seed}
{: .prompt-info }

### 주요 스타일 비교

DiceBear는 다양한 일러스트레이터와 협업하여 수준 높은 아트 스타일을 제공합니다.

| 스타일 | 미리보기 | 요청 URL 및 용도 |
| :--- | :---: | :--- |
| **Lorelei**<br>(감성 일러스트 인물) | ![Lorelei](https://api.dicebear.com/9.x/lorelei/svg?seed=Namju&size=96) | `https://api.dicebear.com/9.x/lorelei/svg?seed=Namju`<br>단정하고 현대적인 일반 사용자 프로필 |
| **Bottts**<br>(조립형 로봇) | ![Bottts](https://api.dicebear.com/9.x/bottts/svg?seed=Namju&size=96) | `https://api.dicebear.com/9.x/bottts/svg?seed=Namju`<br>시스템 봇, 관리자, 기술적인 느낌의 계정 |
| **Avataaars**<br>(플랫 캐릭터) | ![Avataaars](https://api.dicebear.com/9.x/avataaars/svg?seed=Namju&size=96) | `https://api.dicebear.com/9.x/avataaars/svg?seed=Namju`<br>캐주얼한 커뮤니티 기본 프로필 |
| **Notionists**<br>(노션 스타일 흑백) | ![Notionists](https://api.dicebear.com/9.x/notionists/svg?seed=Namju&size=96) | `https://api.dicebear.com/9.x/notionists/svg?seed=Namju`<br>미니멀하고 세련된 생산성 도구 UI |
| **Identicon**<br>(기하학 해시 패턴) | ![Identicon](https://api.dicebear.com/9.x/identicon/svg?seed=Namju&size=96) | `https://api.dicebear.com/9.x/identicon/svg?seed=Namju`<br>GitHub 스타일의 고유 식별자 해시 배지 |
| **Initials**<br>(텍스트 이니셜) | ![Initials](https://api.dicebear.com/9.x/initials/svg?seed=Namju&size=96) | `https://api.dicebear.com/9.x/initials/svg?seed=Namju`<br>알파벳 첫 글자 기반 깔끔한 배지 |

### 실무 활용 패턴 (Kotlin / Spring Boot)

엔티티 생성이나 회원가입 시 프로필 이미지를 등록하지 않은 사용자에게 아래와 같이 기본 URL을 부여할 수 있습니다:

```kotlin
data class User(
    val id: UUID,
    val email: String,
    val nickname: String,
    // 사용자가 프로필을 업로드하지 않은 경우 이메일 또는 닉네임을 seed로 고유 아바타 자동 매핑
    val profileImageUrl: String = "https://api.dicebear.com/9.x/lorelei/svg?seed=${email.ifBlank { nickname }}"
)
```

- **포맷 지원**: URL 확장자로 `.svg`와 `.png`를 모두 지원합니다. 벡터 선명도가 필요한 웹/앱에서는 `.svg`, 레거시 이미지 뷰어 지원이 필요하면 `.png`를 사용합니다.
- **파라미터 커스텀**: `backgroundColor=b6e3f4,c0aede` (배경색 지정), `radius=50` (원형 라운딩 처리) 등의 옵션도 간편하게 쿼리 스트링으로 전달할 수 있습니다.

---

## 2. UI Avatars - 텍스트 이니셜 기반 심플 프로필 API

[UI Avatars](https://ui-avatars.com/)는 슬랙(Slack)이나 노션(Notion)처럼 사용자의 이름 또는 닉네임의 앞 글자(이니셜)를 따서 깔끔한 원형 배지로 만들어 주는 서비스입니다.

복잡한 일러스트 없이 이름 기반의 미니멀한 UI를 선호할 때 기본값으로 사용하기에 최적입니다.

> https://ui-avatars.com/api/?name={Name}&background={color}&color={fontColor}&rounded=true
{: .prompt-info }

| 설정 옵션 | 미리보기 | 요청 URL |
| :--- | :---: | :--- |
| **기본 영문** | ![UI Avatar](https://ui-avatars.com/api/?name=Namju+Kim&size=96) | `https://ui-avatars.com/api/?name=Namju+Kim` |
| **원형 + 랜덤 배경색** | ![UI Avatar Round](https://ui-avatars.com/api/?name=Namju+Kim&rounded=true&background=random&size=96) | `https://ui-avatars.com/api/?name=Namju+Kim&rounded=true&background=random` |
| **한글 지원 + 컬러 커스텀** | ![UI Avatar Korean](https://ui-avatars.com/api/?name=홍길동&rounded=true&background=0D8ABC&color=fff&size=96) | `https://ui-avatars.com/api/?name=홍길동&rounded=true&background=0D8ABC&color=fff` |

- 영문뿐만 아니라 **한글 이름(예: `홍길동` ➔ `홍`)**도 깨짐 없이 첫 음절을 추출하여 렌더링해 줍니다.
- `rounded=true`를 추가하면 완전한 원형 아바타로 생성되며, `bold=true`로 글씨 굵기를 강조할 수도 있습니다.

---

## 3. Lorem Picsum - 고품질 사진 더미 이미지 API

[Lorem Picsum](https://picsum.photos/)은 Unsplash의 고해상도 풍경, 건축, 사물 사진을 원하는 가로/세로 비율로 즉시 불러올 수 있는 가장 대표적인 플레이스홀더 사진 서비스입니다.

블로그 게시글 썸네일, 상품 목록(e-Commerce), 갤러리 피드 목업에 가장 잘 어울립니다.

### 랜덤 이미지

새로고침할 때마다 새로운 사진을 무작위로 서빙합니다.

> https://picsum.photos/{width}/{height}
{: .prompt-info }

- `height`를 생략하면 정사각형 비율로 생성됩니다.
- 흑백 사진이 필요하면 `?grayscale`, 흐림 효과가 필요하면 `?blur` 쿼리를 붙일 수 있습니다.

| 미리보기 | 규격 | 요청 URL |
| :---: | :--- | :--- |
| ![Lorem Picsum 250x160](https://picsum.photos/250/160) | 250 × 160 직사각형 | `https://picsum.photos/250/160` |
| ![Lorem Picsum 160x160](https://picsum.photos/160/160) | 160 × 160 정사각형 | `https://picsum.photos/160` |

### 고정 이미지 (ID 및 Seed 지정)

테스트 시 매번 이미지가 바뀌면 레이아웃 비교가 어려우므로, 고유 ID나 시드를 지정해 고정된 이미지를 가져올 수 있습니다.

> https://picsum.photos/id/{id}/{width}/{height}<br>
> https://picsum.photos/seed/{seed}/{width}/{height}
{: .prompt-info }

| 미리보기 | 방식 | 요청 URL |
| :---: | :--- | :--- |
| ![Lorem Picsum Fixed ID](https://picsum.photos/id/237/250/160) | 고정 ID (강아지 사진) | `https://picsum.photos/id/237/250/160` |
| ![Lorem Picsum Seed](https://picsum.photos/seed/spring/250/160) | Seed 문자열 고정 | `https://picsum.photos/seed/spring/250/160` |

---

## 4. Placehold.co - UI 와이어프레임 및 규격 플레이스홀더 API

UI 와이어프레임 설계나 배너 광고 영역, 상세 페이지 레이아웃을 잡을 때는 실제 사진보다 **"이 영역의 가로·세로 픽셀 크기"**가 명시된 플레이스홀더가 훨씬 유용합니다.

과거에 많이 쓰이던 `via.placeholder.com`이 서비스 불안정 및 인증 개편을 겪으면서, 최근에는 [Placehold.co](https://placehold.co/)가 빠르고 안정적인 표준 대안으로 널리 사용되고 있습니다.

> https://placehold.co/{width}x{height}/{backgroundColor}/{textColor}?text={customText}
{: .prompt-info }

| 스타일 | 미리보기 | 요청 URL |
| :--- | :---: | :--- |
| **기본 규격 박스** | ![Placehold Basic](https://placehold.co/240x120) | `https://placehold.co/300x200` |
| **텍스트 라벨 커스텀** | ![Placehold Text](https://placehold.co/240x120/png?text=Main+Banner) | `https://placehold.co/300x200/png?text=Main+Banner` |
| **다크 테마 색상 지정** | ![Placehold Dark](https://placehold.co/240x120/212529/ffffff?text=Card+View) | `https://placehold.co/300x200/212529/ffffff?text=Card+View` |

- 기본적으로 SVG로 빠르게 렌더링되며, URL 끝에 `.png`, `.webp`, `.jpg`를 붙여 포맷을 자유롭게 바꿀 수 있습니다.
- 폰트 및 배경 색상을 HEX 코드(`212529/ffffff`)로 직관적으로 제어할 수 있어 다크 모드 목업에 유용합니다.

---

## 5. Pravatar - 실사 인물 사진 프로필 API

[Pravatar](https://pravatar.cc/)는 일러스트가 아닌 **실제 인물 얼굴 사진**이 필요한 경우에 적합한 프로필 전용 API입니다.

> https://i.pravatar.cc/{size}?img={id}
{: .prompt-info }

| 구분 | 미리보기 | 요청 URL |
| :--- | :---: | :--- |
| **랜덤 실사 인물** | ![Pravatar Random](https://i.pravatar.cc/96) | `https://i.pravatar.cc/250` |
| **고정 ID 지정 (`img=1~70`)** | ![Pravatar Fixed](https://i.pravatar.cc/96?img=12) | `https://i.pravatar.cc/250?img=12` |

- `?img={1~70}` 파라미터로 특정 인물 사진을 고정하여 재현성 있는 테스트 데이터를 구성할 수 있습니다.

---

## 6. 도메인 로고/파비콘 API: Google Favicon API (Logo.dev 대체)

외부 제휴사 목록, 소셜 로그인 제공자(Google, GitHub, Naver, Kakao), 북마크 링크 카드 등을 구현할 때 도메인별 대표 로고가 필요합니다.

> [!WARNING]
> 기존에 널리 사용되던 `img.logo.dev/{domain}`은 인증 토큰(API Key) 필수 정책으로 변경되어, 현재 토큰 없이 호출 시 `404 Not Found` 또는 `invalid api token` 오류가 발생합니다.

별도의 회원가입이나 API Key 발급 없이 즉시 전 세계 모든 웹사이트의 고해상도 로고를 가져올 수 있는 가장 안정적인 무료 대안은 **Google Favicon API**입니다.

> https://www.google.com/s2/favicons?domain={domain}&sz={size}
{: .prompt-info }

- `domain`: 조회할 대상 도메인 주소 (예: `google.com`, `github.com`, `naver.com`)
- `sz`: 이미지 크기 픽셀 (예: `32`, `64`, `128`)

| 도메인 | 파비콘 로고 | 요청 URL |
| :--- | :---: | :--- |
| **Google** (`google.com`) | ![Google Favicon](https://www.google.com/s2/favicons?domain=google.com&sz=64) | `https://www.google.com/s2/favicons?domain=google.com&sz=128` |
| **GitHub** (`github.com`) | ![GitHub Favicon](https://www.google.com/s2/favicons?domain=github.com&sz=64) | `https://www.google.com/s2/favicons?domain=github.com&sz=128` |
| **Naver** (`naver.com`) | ![Naver Favicon](https://www.google.com/s2/favicons?domain=naver.com&sz=64) | `https://www.google.com/s2/favicons?domain=naver.com&sz=128` |
| **Apple** (`apple.com`) | ![Apple Favicon](https://www.google.com/s2/favicons?domain=apple.com&sz=64) | `https://www.google.com/s2/favicons?domain=apple.com&sz=128` |

구글의 글로벌 CDN 인프라를 통해 캐싱되므로 응답 속도가 매우 빠르고 서버 다운 걱정 없이 안정적으로 동작합니다.

---

## 7. 목적별 더미 이미지 API 추천 요약

| 용도 | 추천 API | 대표 특징 |
| :--- | :--- | :--- |
| **회원 프로필 (일러스트/캐릭터)** | **DiceBear** (`lorelei`, `bottts`) | Seed 기반 동일 이미지 100% 보장, 다양한 테마, SVG/PNG 지원 |
| **회원 프로필 (이니셜 배지)** | **UI Avatars** | 성명 첫 음절 자동 추출, 한글 지원, 미니멀 UI |
| **회원 프로필 (실사 인물 사진)** | **Pravatar** | 실제 사람 얼굴 사진, 고정 ID 지원 |
| **피드·블로그·상품 썸네일** | **Lorem Picsum** | 고화질 사진, 가로/세로 비율 자유 설정, 흑백/블러 지원 |
| **와이어프레임·배너 플레이스홀더** | **Placehold.co** | 픽셀 규격 텍스트 명시, 커스텀 배경색, 가벼운 용량 |
| **기업 제휴사 로고·도메인 아이콘** | **Google Favicon API** | 무제한 무료, API 키 불필요, 구글 글로벌 CDN 캐싱 |

더미 데이터를 구성할 때 위의 목적별 API들을 적절히 조합하면, 별도의 스토리지 비용이나 이미지 파일 관리 부담 없이 실무와 동일한 수준의 풍부한 테스트 환경을 구축할 수 있습니다.