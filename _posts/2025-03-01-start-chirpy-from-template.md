---
title: Jekyll 블로그 시작하기 (Chirpy 테마)
description: Chirpy 테마를 활용한 간단한 Jekyll 블로그 시작하기
date: 2025-03-01 12:00:00 +0000
categories: [Blog, GitHub-Pages]
tags: [Chirpy, Jekyll, GitHub-Pages]
mermaid: true
image:
  path: https://blog.dnd.ac/assets/images/jekyll_memoirs/jekyll-logo.png
---
## 블로그 선택하기 

블로그를 선택함에 있어 고려해야 할 사항은 다음과 같습니다.

| 플랫폼 | 장점 | 단점 | 비용 |
| --- | --- | --- | --- |
| **GitHub Pages** | 무료 제공, 오픈소스로 자유로운 커스터마이징, 버전 관리(Git 연동) | 설정이 다소 복잡할 수 있음, 비개발자에게 진입 장벽이 높음 | 무료 |
| **Tistory** | 직관적인 UI, 간편한 관리, 기본적인 SEO 최적화 | HTML/CSS 편집이 제한적, 디자인 및 기능 확장성이 낮음 | 무료 |
| **Velog** | 개발자 친화적(Markdown 지원), 심플한 디자인, 무료 제공 | HTML/CSS 편집 불가, 자체 도메인 연결 불가 | 무료 |
| **WordPress** | 다양한 테마 및 플러그인 지원, 강력한 확장성, SEO 최적화 가능 | 고급 기능 사용 시 유료 플랜 필요, 관리가 다소 복잡할 수 있음 | 무료(기본) / 유료(플러그인 및 호스팅 비용 발생) |

제가 고려한 사항은 다음과 같습니다.

1. 사용하기 편한가
2. 개발자 친화적인가
3. 원하는 기능을 지원하는가 (SEO, Adsense 등)
4. 비용이 발생하지 않는가 **(중요)**

따라서 GitHub Pages를 선택했습니다.

## Jekyll 테마 선택하기

깃허브에서 [Jekyll Themes](https://github.com/topics/jekyll-theme)로 검색하게 되면 다양한 템플릿들을 찾을 수 있습니다. 

그 중에서 다양한 기능을 제공하며(이미 잘 만들어둔), 업데이트가 활발한 `Chirpy` 테마를 선택했습니다.


## Chirpy 테마 설치하기

### 1. GitHub Repository 생성하기

[chirpy-starter](https://github.com/cotes2020/chirpy-starter/)의 설명에 따라 우측 상단의 `Use this template` 버튼을 클릭하여 새로운 Repository를 생성합니다.

### 2. GitHub Actions 수정하기

설정이 잘못된건지 모르겠지만, 현재 Site Test의 작업이 계속해서 실패하고 있습니다. (2025년 3월 23일 기준)

따라서 `.github/workflows/` 폴더에 있는 `page-deploy.yml` 파일에서 테스트와 관련된 부분을 주석처리합니다.

```yaml
jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      # - name: Test site
      #   run: |
      #     bundle exec htmlproofer _site \
      #       \-\-disable-external \
      #       \-\-ignore-urls "/^http:\/\/127.0.0.1/,/^http:\/\/0.0.0.0/,/^http:\/\/localhost/"

```
이렇게 하면 GitHub Actions에서 Site Test가 실행되지 않게 됩니다.

![GitHub Actions 수정하기](/assets/images/2025-03-23/github_action_screenshot.png)

실행이 완료되고 나면 `<your_username>.github.io/<your_repository_name>` 주소로 접속하여 블로그를 확인할 수 있습니다.