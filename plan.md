# namju.kim 다국어(`/en/` 이중 빌드) 구현 계획

Jekyll과 Chirpy Gem으로 한국어와 영어 사이트를 각각 빌드하고, 결과를 한 GitHub Pages 산출물로 배포합니다. 한국어 URL은 그대로 유지하고 영어 페이지는 `/en/`에 제공합니다. 사용자가 링크를 눌러 언어를 선택하며, 실제 번역 쌍에는 자기 참조 canonical과 상호 `hreflang`을 적용합니다.

## 1. 빌드와 배포 구조

| 빌드 | 공개 경로 | 컬렉션 소스 | 설정 |
| --- | --- | --- | --- |
| 한국어 | `/` | `_posts/`, `_tabs/` | `_config.yml` |
| 영어 | `/en/` | `en/_posts/`, `en/_tabs/` | `_config.yml` + `_config_en.yml` |

두 빌드의 Jekyll 소스 루트는 저장소 루트입니다. 루트 `index.html`, `_includes/`, `_plugins/`, `assets/`를 공유합니다. 헤드 변경에는 기존 `metadata-hook.html`을, 언어 전환에는 저장소의 기존 `topbar.html`을 사용합니다. 프로덕션에서는 기존 커밋 SHA 고정 jsDelivr 설정을 두 빌드에 적용합니다.

## 2. 구현 단계

### Phase 1. 영어 설정과 컬렉션

- `_config_en.yml`에 `lang: en`, `locale: en_US`, `baseurl: /en`, `collections_dir: en`, `pwa.enabled: false`를 설정합니다. 영어 `title`, `tagline`, `description`, `social.name`, `author.name`을 지정하고, `author.url`은 `https://namju.kim/en/about/`로 설정합니다.
- `_config.yml`의 `exclude`에 `en`을 추가합니다. Jekyll은 설정 파일 간 `exclude` 배열을 교체하므로, 영어 오버라이드에는 기존 공통 제외 목록 전체와 영어 빌드에서 제외할 루트 전용 항목(`_posts`, `_tabs`, `_drafts`, `robots.txt`, `ads.txt`)을 명시합니다. 영어 쪽 목록에는 컬렉션을 읽을 수 있도록 `en`을 넣지 않습니다. 공통 제외 항목을 변경할 때 두 목록을 함께 갱신합니다.
- 한국어 PWA의 `pwa.cache.deny_paths`에 `/en`을 추가합니다. 최종 산출물에서 루트 서비스 워커의 캐시 제외 동작과 영어 페이지의 서비스 워커 미등록을 확인합니다.
- `en/_tabs/`에 `about.md`, `archives.md`, `categories.md`, `tags.md`를 작성합니다. 영문 글은 `en/_posts/{대분류}/{중분류}/YYYY-MM-DD-slug.md`에 둡니다.

### Phase 2. 기존 훅 수정

- `locale-override-hook.rb`의 관련 글 제목 오버라이드를 `ko`로 제한합니다. 영어에서는 Chirpy의 기본 영문 레이블을 사용합니다.
- `posts-lastmod-hook.rb`의 Git 조회 경로와 이력 조회 키에 저장소 기준 경로를 사용합니다. 한국어는 `_posts/…`, 영어는 `en/_posts/…`로 맞추고, 빌드당 단일 `git log`와 기존 수정일 적용 기준을 유지합니다.
- Jekyll의 `post.relative_path`는 이미 `collections_dir` 기준이므로 기존 카테고리 훅을 사용합니다. 두 빌드에서 폴더 카테고리, 이미지 크기, 태그·페이지네이션의 `noindex`와 사이트맵 제외, 코드 블록의 Liquid 이스케이프를 산출물로 확인합니다.

### Phase 3. 번역 연결과 사이트맵

- 번역 쌍의 양쪽 Front Matter에 도메인 루트 기준의 `alt_url`을 기록합니다. 예를 들어 한국어 글은 `/en/posts/spring-ai-guide/`를, 영어 글은 `/posts/spring-ai-guide/`를 가리킵니다. 홈과 대응 탭도 같은 방식으로 연결합니다.
- `metadata-hook.html`에서 현재 페이지는 `page.url | absolute_url`에 `strip_index`를 적용하고, 번역 대상은 `site.url`과 `alt_url`을 결합합니다. `alt_url`에는 공개 경로에 필요한 접두사가 이미 포함되어 있으므로 Jekyll의 `relative_url`과 `absolute_url` 필터 적용 대상에서 제외합니다.
- 두 번역 페이지의 `<head>`에 동일한 `ko`, `en`, `x-default` 절대 URL 세트를 출력합니다. `x-default`는 해당 쌍의 한국어 URL을 가리킵니다. 각 페이지의 canonical은 자기 URL을 가리키며, 대응 페이지가 없는 글에는 `hreflang`을 출력하지 않습니다.
- 기존 `_includes/topbar.html`에 키보드로 접근할 수 있는 `KO | EN` 링크를 정적 `<a href>`로 렌더링합니다. 대응 페이지가 있으면 그 페이지로 연결하고, 대응 페이지가 없으면 링크에 홈 이동임을 표시하고 해당 언어의 홈으로 연결합니다.
- 루트 `robots.txt`에 `https://namju.kim/sitemap.xml`과 `https://namju.kim/en/sitemap.xml`을 모두 명시합니다. 각 사이트맵은 해당 언어 빌드의 색인 대상 URL을 담습니다.

### Phase 4. CI와 배포 산출물

- `.github/workflows/pages-deploy.yml`의 링크 미리보기 캐시 키에 `en/_posts/**`를 추가합니다. 기존 Ruby 3.4, 전체 Git 이력 체크아웃, `JEKYLL_ENV=production`, 커밋 SHA 기준 `_config_ci.yml` 생성을 사용합니다.
- 한국어를 기존 Pages 업로드 경로에, 영어를 저장소 밖의 별도 임시 경로에 빌드합니다. CI에서는 `pages_dest`에 기존 Pages 업로드 경로(현재 `_site`)를 지정하고, `en_dest`는 `mktemp -d "$RUNNER_TEMP/jekyll-en.XXXXXX"`로 만듭니다.

  ```bash
  bundle exec jekyll build -d "$pages_dest" --config _config.yml,_config_prod.yml,_config_ci.yml
  bundle exec jekyll build -d "$en_dest" --config _config.yml,_config_prod.yml,_config_ci.yml,_config_en.yml
  ```

- 영어 결과를 `$pages_dest/en/`으로 복사할 때 `assets/images/`, `robots.txt`, `ads.txt`를 제외합니다. `rsync` 필터는 영어 산출물 루트를 기준으로 적용합니다. 이 단계에서 플러그인이 재생성한 영어 `robots.txt`도 걸러냅니다. 영어의 CSS·JS 등은 `/en/assets/…`에서 제공합니다. 이미지 원본은 빌드 중 크기 계산에 사용할 수 있게 두고, 프로덕션 영어 페이지에서 CDN URL을 사용하는지 확인합니다. CDN을 사용하지 않는 로컬 병합 결과에는 영어 이미지도 포함합니다.
- 병합 후 기존 HTMLProofer 검사와 별도의 SEO 검사를 실행하고, 모두 통과한 산출물만 업로드합니다. `qa_check.py`는 `en/_posts/`까지 검사하도록 확장해 Front Matter, 이미지 경로, Mermaid를 검사합니다. 번역 대상의 실재 여부와 상호 참조는 최종 HTML에서 검사합니다.

### Phase 5. 파일럿 발행

- 인프라 단계에서 영문 탭만 있는 빌드를 검증한 뒤, 첫 공개 배포에 기존 기술 글의 영어 번역 **2편**을 포함합니다. 인프라·Docker·Spring·Jekyll 트러블슈팅 글에서 선정하고, 발행 시 한국어 원문에도 대응 `alt_url`을 추가합니다.
- 영문 포스트에서 기존 AdSense 스크립트 로드와 광고 슬롯 배치를 브라우저에서 확인합니다. 발행 2~4주 후 Search Console에서 `/en/` URL의 노출·클릭을, AdSense에서 영어 페이지에 귀속할 수 있는 광고 지표를 확인합니다.

## 3. 배포 전 검증

1. **빌드와 산출물** — 영문 글 0편과 파일럿 2편 구성으로 각각 빌드합니다. 한국어 기존 URL, `/en/`, 영어 탭, 영어 글, CSS·JS·검색·피드 자산이 예상 경로에 있는지 확인합니다. 영어 배포 디렉터리에 내부 문서, 이미지 원본 사본, `robots.txt`, `ads.txt`가 들어가지 않는지 확인합니다.
2. **언어와 canonical** — 영어 홈·탭·글에서 `<html lang="en">`, `og:locale="en_US"`, `/en/`이 한 번 적용된 자기 참조 canonical을 확인합니다. 한국어 대표 페이지에서도 자기 참조 canonical과 한글 UI를 확인합니다.
3. **번역 쌍과 사이트맵** — 최종 HTML에서 양쪽 `hreflang` 세트가 일치하고, 대상 파일이 존재하며, 각 대상의 canonical과 일치하는지 CI에서 검사합니다. 번역 없는 글에는 `hreflang`이 없어야 합니다. 루트 `robots.txt`의 두 사이트맵 URL과 각 사이트맵의 언어별 URL 범위, `noindex` 페이지 제외를 검사합니다.
4. **링크와 브라우저 동작** — 병합 산출물에 기존 `htmlproofer --disable-external` 검사를 실행합니다. JavaScript를 끈 상태에서 번역 쌍과 미번역 글의 홈 이동 링크를 확인합니다. 브라우저에서 `/en/` 검색, PWA 동작, 이미지와 광고 배치를 확인합니다.

## 4. 진행 전 확인 사항

- 영문 블로그 이름과 소개 문구. 제목 후보는 `Namju's Commit Log`이며, 소개 문구 후보는 `Engineering notes, troubleshooting, and things learned along the way.`입니다.
- 첫 배포에 포함할 한국어 원문 2편.
- 기존 AdSense 배치를 유지할지, 배치 개선을 별도 작업으로 진행할지 결정합니다.
