---
title: Chirpy 테마로 GitHub Pages 블로그 시작하기
description: Jekyll Chirpy Starter 템플릿을 사용하여 GitHub Pages 기반의 정적 블로그를 생성하고, GitHub Actions 자동 배포 파이프라인을 구축하는 전체 과정을 다룹니다.
date: 2025-03-01 12:00:00 +0900
categories: [Blog, GitHub-Pages]
tags: [Chirpy, Jekyll, GitHub-Pages, Starter, GitHub-Actions]
mermaid: true
image:
  path: /assets/images/2025-03-01/chirpy-home-card-preview.png
  alt: Jekyll Chirpy 테마 초기 홈 화면
---

> 개발자의 성장을 기록하고 기술적인 고민을 아카이빙하기 위해 GitHub Pages와 Jekyll Chirpy 테마를 선택하여 첫 기술 블로그를 개설하고 자동 배포를 구축한 과정을 공유합니다.

---

## 1. 블로그 플랫폼 선택의 고민

개발을 시작하면서 배운 지식과 프로젝트 트러블슈팅 경험을 기록할 플랫폼을 찾기 위해 여러 선택지를 검토했습니다.

| 플랫폼 | 장점 | 단점 | 비용 |
| :--- | :--- | :--- | :---: |
| **GitHub Pages** | • Git 기반 버전 관리<br>• 무제한 코드 커스터마이징<br>• 마크다운(Markdown) 네이티브 | • 초기 설정 및 빌드 환경 러닝커브<br>• 플러그인 의존성 관리 필요 | **무료** |
| **Velog** | • 개발자 친화적 기본 마크다운<br>• 간편한 글 작성 및 피드 노출 | • 자체 커스텀 도메인 불가<br>• 디자인 및 레이아웃 수정 불가 | 무료 |
| **Tistory** | • 손쉬운 관리자 UI<br>• 자체 광고 및 수익화 기능 | • 플랫폼 정책 변경 위험<br>• Git 버전 관리 미지원 | 무료 |
| **WordPress** | • 방대한 플러그인 및 테마 생태계<br>• 강력한 CMS 기능 | • 호스팅 서버 및 도메인 유지비<br>• 정기적인 보안 업데이트 관리 | 유료 |

제가 가장 중요하게 생각한 기준은 네 가지였습니다:

1. **Git 버전 관리**: 글 작성과 수정을 코드처럼 `git commit` 히스토리로 추적할 수 있는가?
2. **완전한 커스터마이징**: 레이아웃, CSS, 메타데이터를 필요에 따라 제약 없이 확장할 수 있는가?
3. **개발자 친화성**: 로컬 IDE(VS Code)에서 마크다운으로 작성하고 터미널에서 즉시 프리뷰할 수 있는가?
4. **유지비용 무료**: 트래픽이나 스토리지에 따른 호스팅 비용이 일절 들지 않는가?

이 모든 조건을 완벽하게 충족하는 솔루션은 **GitHub Pages**였습니다.

---

## 2. 왜 Chirpy 테마인가?

[Jekyll Themes](https://github.com/topics/jekyll-theme) 생태계에는 수많은 오픈소스 테마가 존재합니다. 그중에서도 **Chirpy(`jekyll-theme-chirpy`)**를 최종 선택한 이유는 다음과 같습니다:

- **완성도 높은 반응형 UI**: 데스크톱, 태블릿, 모바일 환경 모두에서 미려하게 반응하는 레이아웃.
- **다크 모드 기본 지원**: 독자의 OS 설정에 맞추거나 수동으로 전환 가능한 테마 토글 내장.
- **엔지니어링 기능 완비**: Mermaid 다이어그램, 수식(MathJax), 코드 문법 하이라이팅, 우측 목차(TOC) 기본 탑재.
- **체계적인 배포 아키텍처**: 과거의 복잡한 로컬 빌드 배포 방식에서 벗어나, **GitHub Actions 표준 워크플로우**를 공식 Starter로 지원.

---

## 3. Chirpy 스타터로 저장소 생성하기

Chirpy 테마는 테마 소스 코드 전체를 포크(Fork)하는 대신, 필요한 설정과 포스트만 깔끔하게 관리할 수 있는 **Starter 템플릿**을 공식 권장합니다.

```mermaid
flowchart LR
    A["chirpy-starter 템플릿"] -->|Use this template| B["<username>.github.io"]
    B -->|git push| C["GitHub Actions CI"]
    C -->|pages-deploy.yml| D["GitHub Pages 호스팅"]
```

### Step 1. chirpy-starter 템플릿 사용

1. 공식 [chirpy-starter 저장소](https://github.com/cotes2020/chirpy-starter/)에 접속합니다.
2. 우측 상단의 녹색 **`Use this template`** 버튼을 누르고 **`Create a new repository`**를 선택합니다.
3. 저장소 이름(Repository name)을 반드시 아래 규칙에 맞게 지정합니다:
   - 개인 루트 도메인 사용 시: **`<본인의-GitHub-아이디>.github.io`**
   - 예: `cmsong111.github.io`

> 💡 **저장소 네이밍 팁**: 저장소 이름을 `<username>.github.io`로 생성하면 서브 디렉토리 없이 `https://<username>.github.io/` 주소로 블로그가 바로 연결됩니다.

---

## 4. GitHub Pages 및 배포 파이프라인 구성

저장소를 생성했다면, GitHub Actions가 커밋을 감지하여 자동으로 Jekyll 사이트를 빌드하고 배포할 수 있도록 GitHub 저장소 설정을 변경해야 합니다.

### Step 1. 배포 소스를 GitHub Actions로 전환

1. 생성한 저장소의 **`Settings`** 탭으로 이동합니다.
2. 좌측 메뉴에서 **`Pages`**를 클릭합니다.
3. **`Build and deployment`** 섹션의 **`Source`** 항목을 기본값인 `Deploy from a branch`에서 **`GitHub Actions`**로 변경합니다.

![GitHub Pages 배포 소스 설정 화면](/assets/images/2025-03-18/github-pages-custom-domain-settings.png)

### Step 2. 자동 배포 워크플로우 (`pages-deploy.yml`)의 역할

`chirpy-starter` 템플릿에는 `.github/workflows/pages-deploy.yml` 파일이 이미 포함되어 있습니다. 이 파일은 `main` 브랜치에 코드가 푸시될 때마다 다음 단계들을 자동으로 실행합니다:

1. **Ruby 환경 설정**: Jekyll 구동에 필요한 Ruby 버전을 세팅합니다.
2. **의존성 설치**: `Gemfile.lock`에 명시된 Jekyll 및 테마 Gem을 설치합니다.
3. **사이트 빌드**: `bundle exec jekyll build`를 실행하여 정적 HTML/CSS 자산을 컴파일합니다.
4. **HTML 무결성 검증 (htmlproofer)**: 사이트 내 링크 깨짐, 이미지 누락, HTML 문법 오류를 사전 검사합니다.
5. **GitHub Pages 아티팩트 업로드**: 검증을 통과한 `_site` 결과물을 안전하게 배포합니다.

```yaml
# .github/workflows/pages-deploy.yml 핵심 단계 발췌
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Ruby
        uses: ruby/setup-ruby@v1
        with:
          ruby-version: 3.3
          bundler-cache: true

      - name: Build Site
        run: bundle exec jekyll build -d _site

      - name: Test site
        run: |
          bundle exec htmlproofer _site \
            --disable-external \
            --ignore-urls "/^http:\/\/127.0.0.1/,/^http:\/\/0.0.0.0/,/^http:\/\/localhost/"
```

빌드가 성공적으로 완료되면 GitHub Actions 탭에서 초록색 체크 표시와 함께 배포 URL이 활성화됩니다.

![GitHub Actions 배포 파이프라인 실행 화면](/assets/images/2025-03-01/github-actions-deploy-workflow.png)

---

## 5. 로컬 개발 환경에서 실시간 미리보기

원격 저장소에 커밋하기 전에 로컬 컴퓨터에서 글을 작성하고 디자인을 실시간으로 확인하는 개발 루프를 구성합니다.

### 1) 저장소 클론 및 의존성 설치
```bash
git clone https://github.com/<username>/<username>.github.io.git blog
cd blog
bundle install
```

### 2) 로컬 Jekyll 개발 서버 실행
```bash
bundle exec jekyll serve --livereload
```

실행 후 브라우저에서 `http://localhost:4000`에 접속하면, 마크다운 파일을 수정하고 저장할 때마다 브라우저가 자동으로 새로고침되며 변경 사항이 즉각 반영됩니다.

![Chirpy 테마 첫 화면 렌더링 확인](/assets/images/2025-03-01/chirpy-home-card-preview.png)

---

## 6. 마무리 및 다음 단계

이제 나만의 기술 블로그를 운영하기 위한 가장 기본적이면서도 견고한 뼈대가 완성되었습니다. 

`main` 브랜치에 글을 작성하여 푸시하기만 하면 GitHub Actions가 알아서 검증과 빌드를 거쳐 전 세계에 무료로 배포해 주는 완전 자동화 시스템을 갖추게 되었습니다.

다음 포스트에서는 블로그의 제목, 다국어 및 한국 시간대(KST) 설정, 방문자와 소통하기 위한 **Utterances 댓글 연동**, 그리고 프라이버시 친화적인 **GoatCounter 방문자 통계 연동** 등 필수적인 `_config.yml` 핵심 환경 설정법을 단계별로 다루어 보겠습니다.