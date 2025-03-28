---
title: Jekyll 블로그 세팅하기 (댓글, 조회수, SEO 등)
description: Chirpy를 활용한 간단하게 Jekyll 블로그 세팅하기
date: 2025-03-02 12:00:00 +0000
categories: [Blog, GitHub-Pages]
tags: [Chirpy, Jekyll, GitHub-Pages]
mermaid: true
image:
  path: https://camo.githubusercontent.com/7deb9e4905ab1e73cec83fa80f3a5d0c7f613e6b522a9fdc41d5c79fad37eda8/68747470733a2f2f6368697270792d696d672e6e65746c6966792e6170702f636f6d6d6f6e732f646576696365732d6d6f636b75702e706e67
---

## 블로그 Header 설정하기

```yaml
lang: ko
timezone: Asia/Seoul
```

## 댓글

Chirpy 테마는 기본적으로 댓글 기능을 제공하고 있습니다.

이전에 손쉽게 사용했던 utterances를 사용하기로 하겠습니다.

레포지토리에 utterances를 설치하면, 블로그에 댓글 기능을 추가할 수 있습니다.

다음과 같이 `_config.yml` 파일에 설정을 추가합니다.

```yaml
comments:
  provider: utterances # [disqus | giscus | utterances]
  # utterances settings › https://utteranc.es/
  utterances:
    repo: cmsong111/blog
    issue_term: pathname # < url | pathname | title | ...>
```

## 웹 사이트 분석

### 조회수

GoatCounter를 사용하여 무료로 블로그에 조회수 기능을 추가할 수 있습니다.

[GoatCounter](https://www.goatcounter.com/)에 가입하고, 도메인을 등록한 후, 아래와 같이 `_config.yml` 파일에 설정을 추가합니다.

```yaml
analytics:
  goatcounter:
    id: cmsong111
pageviews:
  provider: goatcounter 
```

### 구글 애널리틱스
구글 애널리틱스를 사용하여 블로그의 트래픽을 분석할 수 있습니다.
[Google Analytics](https://analytics.google.com/)에 가입하고, 도메인을 등록한 후, 아래와 같이 `_config.yml` 파일에 설정을 추가합니다.

```yaml
# Web Analytics Settings
analytics:
  google:
    id: G-XXXXXXXXXX 
```


## 검색 엔진 등록

Chirpy 테마는 기본적으로 site-map, seo 플러그인을 내장하고 있습니다.

따라서 별도의 세팅없이 sitemap.xml 파일과 robots.txt 파일이 생성됩니다.

이제 구글 서치 콘솔에 가입하고, 도메인을 등록한 후, 본인 사이즈 확인을 진행하면 됩니다.

이후, 헤더에 메타태그 검증 방식을 선택 후 아래와 같이 키값만 복사해서 `_config.yml` 파일에 추가합니다.

```yaml
# Site Verification Settings
webmaster_verifications:
  google: pWvXEtxit9b2Jb1B...
  bing: 3FCE53F92232E6E585B...
```

따로 네이버의 사이트 등록을 희망한다면  _include/head.html 파일에 아래와 같이 추가합니다.

```html
<head>
  <meta name="naver-site-verification" content="858f23c8777819..." />
</head>
```

> `head.html` 파일이 없으신 분들은 [에드센스 세팅](#구글-에드센스) 부분을 참고하여 추가하시면 됩니다.
{: .prompt-tip }

### SEO

Chirpy 테마는 기본적으로 SEO 최적화가 되어 있습니다.
따라서 config 파일만 수정해서 손쉽게 SEO 최적화를 할 수 있습니다.

```yaml
# 블로그 SEO
title: 남주의 커밋로그
tagline: A text-focused Jekyll theme 
description: >
  개발하면서 생각한 것들, 배운 것들, 그리고 나의 기록을 남기는 공간입니다.
url: "https://namju.kim"

# 공유시 나타날 작성자 명
github:
  username: cmsong111 
twitter:
  username: 김남주
# 작성자 클릭시 나오는 페이지
social:
  name: 김남주
  email: cmsong111@naver.com 
  links:
    - https://github.com/cmsong111 # 첫 번째 링크가 작성자 클릭시 나오는 링크
    - https://www.linkedin.com/in/kimnamju/

```

## 구글 에드센스

구글 애드센스를 사용하여 블로그에 광고를 추가할 수 있습니다.

Chirpy 테마는 에드센스 기능을 제공하고 있지 않습니다.

따라서 설정을 커스텀을 해야 합니다.

구글 에드센스 사이트에 가입 후, 광고 스크립트를 삽입해야 하는데, 헤더 구문을 어디에 추가해야할 지 처음에는 참 난감했습니다.. 

그래서 공통 헤더파일에 스크립트 구문을 추가하기 위해 Chirpy의 공통 헤더 파일을 구했습니다 

head.html파일은 [Chirpy 테마의 원본 레포지토리에서](https://github.com/cotes2020/jekyll-theme-chirpy/blob/master/_includes/head.html) 내려받아 동일한 경로에 복사해두면 됩니다.

그리고, 아래와 같이 구글 애드센스 스크립트를 추가합니다.

```html
<head>
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-9883771255224638" crossorigin="anonymous"></script>
</head>
```

이후, 깃허브 페이지에 배포를 진행하고, 우클릭 -> 검사하기를 통해 광고가 잘 나오는지 확인합니다.

> 제 세팅이 궁금하신 분들은, [남주의 커밋로그 레포지토리](https://github.com/cmsong111/blog)를 참고하시면 됩니다.
{: .prompt-info }
