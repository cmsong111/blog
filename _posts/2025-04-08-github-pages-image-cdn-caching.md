---
title: GitHub Pages 이미지 대역폭 한계 극복하기 (jsDelivr 무료 글로벌 CDN 캐싱)
description: GitHub Pages의 월 100GB 트래픽 한계를 극복하기 위해, VS Code 로컬 작성 환경을 완벽히 유지하면서 배포 시에만 jsDelivr 글로벌 CDN으로 전역 자동 변환하는 환경 분리 아키텍처를 구현합니다.
date: 2025-04-08 12:00:00 +0900
categories: [Blog, GitHub-Pages]
tags: [GitHub-Pages, Jekyll, Chirpy, CDN, jsDelivr, Caching, Web-Performance]
mermaid: true
image:
  path: /assets/images/2025-04-08/cdn-environment-isolation.png
  alt: 로컬 개발 환경과 프로덕션 CDN 이미지 경로 자동 분리 아키텍처
---

> GitHub Pages는 무료 정적 호스팅을 제공하지만 월 100GB라는 소프트 대역폭(Bandwidth) 제한이 존재합니다. 이미지는 이 용량을 가장 빠르게 소진시키는 주범입니다. VS Code에서의 쾌적한 로컬 작성 경험을 100% 보존하면서, 프로덕션 배포 시에만 무료 글로벌 CDN으로 자동 치환되는 '환경 분리 이미지 캐싱 아키텍처'를 구축한 과정을 공유합니다.

---

## 1. 문제의식: GitHub Pages의 보이지 않는 한계와 이미지 에셋

GitHub Pages는 개발자가 무료로 기술 블로그를 운영하기에 가장 훌륭한 플랫폼이지만, [GitHub 공식 사용 가이드라인](https://docs.github.com/en/pages/getting-started-with-github-pages/guidelines-for-github-pages)을 자세히 살펴보면 다음과 같은 엄격한 사용량 제한이 명시되어 있습니다:

- **월간 대역폭(Bandwidth) 소프트 제한**: **월 100GB**
- **저장소(Repository) 권장 용량**: **1GB 미만**
- **시간당 빌드 제한**: 시간당 최대 10회

블로그 글에 첨부되는 고해상도 PNG 스크린샷이나 다이어그램은 한 장당 300KB ~ 1MB를 훌쩍 넘깁니다. 

포스트 하나에 이미지 3장(약 2MB)이 포함되어 있다면, 방문자 1명이 해당 글을 열람할 때마다 2MB 이상의 대역폭이 소모됩니다. 월간 방문자가 늘어나거나 검색엔진 크롤러가 사이트를 수집하기 시작하면 100GB의 대역폭은 생각보다 빠르게 고갈될 수 있습니다.

따라서 **이미지 에셋의 트래픽을 외부 무료 CDN으로 완전히 오프로딩(Offloading)**하여, GitHub Pages 서버는 텍스트(HTML/CSS/JS)만 가볍게 서빙하도록 만들어야 했습니다.

---

## 2. 개발자 경험(DX)의 딜레마: 로컬과 배포 환경의 충돌

무료 이미지 CDN을 도입할 때 가장 큰 걸림돌은 **개발자 작성 경험(Developer Experience, DX)**이었습니다.

마크다운 본문에 CDN 절대 URL(`https://cdn.jsdelivr.net/...`)을 하드코딩하면 다음과 같은 심각한 문제가 발생합니다:

1. **VS Code 마크다운 미리보기 불가**: 로컬 에디터에서 글을 쓸 때 아직 원격에 푸시되지 않은 이미지의 미리보기가 완전히 깨집니다.
2. **로컬 개발 서버(`localhost:4000`) 확인 불가**: 로컬에서 `jekyll serve`를 실행해도 원격 이미지를 불러오지 못해 새 글 검증이 불가능합니다.
3. **작성의 번거로움**: 이미지를 캡처할 때마다 매번 원격 CDN URL을 계산해서 붙여넣어야 합니다.

제가 원했던 이상적인 워크플로우는 명확했습니다:

> **"로컬 VS Code에서는 지금까지 하던 대로 `/assets/images/...` 상대 경로로 작성하고 로컬에서 즉시 확인하며, GitHub Actions로 배포될 때만 빌드 타임에 전역 CDN 주소로 자동 치환되는 시스템"**

---

## 3. 해결의 실마리: Chirpy의 `cdn` 변수와 Jekyll 다중 설정

Jekyll Chirpy 테마의 코어 소스 코드를 분석하던 중, 테마 내부에 이미 CDN을 지원하기 위한 파이프라인이 내장되어 있음을 발견했습니다.

### 1) Chirpy의 미디어 URL 렌더링 메커니즘
Chirpy 테마는 마크다운 본문의 이미지를 렌더링할 때 `_includes/media-url.html`을 통과시킵니다:

```liquid
{% raw %}<!-- Chirpy 코어: _includes/media-url.html 발췌 -->
{% if site.cdn %}
  {% assign url = site.cdn | append: '/' | append: url %}
{% endif %}{% endraw %}
```

즉, Jekyll 설정(`site.cdn`)에 CDN 엔드포인트가 정의되어 있으면, 마크다운에 적힌 모든 `/assets/images/...` 경로 앞에 CDN 주소를 자동으로 접두사(Prefix)로 붙여주는 완벽한 기능을 이미 갖추고 있었습니다.

### 2) Jekyll 다중 설정 파일(`--config`)을 통한 환경 분리
Jekyll은 빌드 명령어 실행 시 여러 개의 설정 파일을 콤마(`,`)로 연결하여 오버라이드할 수 있습니다:

```bash
bundle exec jekyll build --config _config.yml,_config_prod.yml
```

이를 활용하면:
- **로컬 개발 (`_config.yml`)**: `cdn:` 값을 빈 문자열로 두어 로컬 디스크 파일 경로 사용.
- **프로덕션 배포 (`_config_prod.yml`)**: 프로덕션 빌드 시에만 글로벌 CDN 엔드포인트를 주입.

이 두 가지를 조합하면 로컬 작성 경험을 단 1%도 해치지 않으면서 배포 시에만 CDN으로 전환되는 완벽한 아키텍처가 완성됩니다.

![로컬 개발 환경과 프로덕션 CDN 이미지 경로 자동 분리 아키텍처](/assets/images/2025-04-08/cdn-environment-isolation.png)

---

## 4. 무료 글로벌 Multi-CDN 선정: 왜 jsDelivr인가?

GitHub 공개 저장소를 원본 소스(Origin)로 삼아 무료로 전 세계에 캐싱해 주는 서비스 중 **[jsDelivr](https://www.jsdelivr.com/)**을 선택했습니다:

- **완전 무료 & 오픈소스**: 회원가입, 신용카드 등록, API 키 발급이 일절 필요 없습니다.
- **글로벌 Multi-CDN 인프라**: Cloudflare, Fastly, Akamai의 글로벌 Anycast 엣지 네트워크를 통합 운영하여 전 세계 어디서든 수십 밀리초(ms) 단위의 응답 속도를 보장합니다.
- **GitHub 저장소 직결 URL 문법**:
  ```text
  https://cdn.jsdelivr.net/gh/<GitHub-사용자명>/<저장소명>@<브랜치명>/<경로>
  ```
- **공식 CORS 및 WebP/HTTP2 지원**: 모든 브라우저와 서치엔진에서 경고 없이 완벽히 동작합니다.

---

## 5. 실전 구현 단계

### Step 1. 프로덕션 전용 설정 파일 생성 (`_config_prod.yml`)

프로젝트 루트 디렉토리에 **`_config_prod.yml`** 파일을 신규 생성하고 jsDelivr CDN 엔드포인트를 정의합니다:

```yaml
# _config_prod.yml
# 프로덕션(배포) 환경 전용 오버라이드 설정
# GitHub Actions 배포 시 적용: bundle exec jekyll build --config _config.yml,_config_prod.yml

# 전역 이미지 CDN 엔드포인트 (jsDelivr 오픈소스 Multi-CDN)
# '/'로 시작하는 모든 미디어 리소스(포스트 이미지, 아바타 등)에 자동으로 접두어로 추가됩니다.
# 로컬 개발 환경(_config.yml)에서는 빈 값으로 유지되어 로컬 상대 경로가 그대로 사용됩니다.
cdn: 'https://cdn.jsdelivr.net/gh/cmsong111/blog@main'
```

기존 `_config.yml`의 `cdn:` 항목은 그대로 비워둡니다.

### Step 2. GitHub Actions 배포 워크플로우 수정

`.github/workflows/pages-deploy.yml` 파일에서 Jekyll 빌드 명령어를 찾아 `--config _config.yml,_config_prod.yml` 옵션을 추가합니다:

```yaml
# .github/workflows/pages-deploy.yml
      - name: Build site
        # 기존: bundle exec jekyll b -d "_site${{ steps.pages.outputs.base_path }}"
        # 수정: _config_prod.yml을 함께 불러와 cdn 설정을 프로덕션에만 오버라이드
        run: bundle exec jekyll b -d "_site${{ steps.pages.outputs.base_path }}" --config _config.yml,_config_prod.yml
        env:
          JEKYLL_ENV: "production"
```

![GitHub Actions Runner의 Multi-Config 빌드 로그](/assets/images/2025-04-08/jekyll-multi-config-build.png)

CI 러너가 두 개의 설정 파일을 차례로 로드하여 빌드하며, `HTML-Proofer` 테스트 역시 외부 링크 예외 옵션(`--disable-external`) 덕분에 오류 없이 완벽하게 통과합니다.

---

## 6. 캐시 동작 및 HTTP 응답 검증

배포 후 실제 생성된 HTML 소스 코드와 jsDelivr CDN 서버의 HTTP 응답 헤더를 `curl`로 검증해 보았습니다.

```bash
curl -ILs "https://cdn.jsdelivr.net/gh/cmsong111/blog@main/assets/images/2025-03-18/dns-records-setup.png" | head -n 12
```

![jsDelivr Multi-CDN 캐시 적중 및 응답 헤더 검증 화면](/assets/images/2025-04-08/jsdelivr-cdn-cache-hit.png)

```http
HTTP/2 200 
date: Sun, 04 Oct 2026 14:30:04 GMT
content-type: image/png
content-length: 34652
access-control-allow-origin: *
cache-control: public, max-age=604800, s-maxage=43200
x-jsd-version: main
x-jsd-version-type: branch
```

- **`cache-control: public, max-age=604800, s-maxage=43200`**:
  - 방문자의 브라우저에는 **7일(`max-age=604800`)** 동안 캐싱되어 재방문 시 네트워크 요청이 아예 발생하지 않습니다.
  - 전 세계 CDN 엣지 서버에는 **12시간(`s-maxage=43200`)** 동안 캐싱되어 GitHub 원본 저장소로의 트래픽을 완벽히 차단합니다.
- **`x-jsd-version: main`**: GitHub의 `main` 브랜치 최신 커밋 상태와 정확하게 연동됨을 나타냅니다.

---

## 7. 보너스 팁: 이미지 즉시 캐시 갱신 (Purge API)

이미지를 새로 수정하여 같은 파일명으로 다시 푸시했을 때, 엣지 캐시가 만료될 때까지 기다리지 않고 즉시 갱신하고 싶다면 jsDelivr의 **공식 Purge API**를 단 한 줄의 명령어로 호출할 수 있습니다:

```bash
# 특정 이미지의 CDN 엣지 캐시 즉시 무효화
curl -X POST "https://purge.jsdelivr.net/gh/cmsong111/blog@main/assets/images/2025-04-08/sample.png"
```

호출 즉시 전 세계 엣지 노드의 캐시가 초기화되고 GitHub 저장소의 최신 이미지를 다시 페치하여 동기화합니다.

---

## 8. 마치며

이번 이미지 CDN 캐싱 아키텍처 도입을 통해 얻은 성과는 다음과 같습니다:

1. **GitHub Pages 월 100GB 대역폭 제한 완전 탈피**: 대용량 이미지 트래픽이 0MB로 떨어져 트래픽 초과 걱정이 완전히 사라졌습니다.
2. **글로벌 로딩 속도(TTFB) 개선**: 방문자와 가장 가까운 Anycast Edge POP에서 이미지를 즉시 전달하여 체감 로딩 속도가 획기적으로 개선되었습니다.
3. **개발자 작성 경험(DX) 100% 보존**: 마크다운 본문에는 여전히 `/assets/images/...` 로컬 경로만 작성하면 되므로, VS Code 미리보기와 로컬 개발 환경이 전혀 깨지지 않습니다.

동일한 고민을 하고 계신 정적 블로그 운영자분들께 이 **'Jekyll 환경 분리 + jsDelivr 오픈소스 CDN'** 조합을 적극 추천합니다.
