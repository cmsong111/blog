# AI 에이전트 지침서 (AGENTS.md)

이 문서는 AI 어시스턴트(Antigravity, Claude Code, Copilot 등)가 **남주의 커밋로그([https://namju.kim](https://namju.kim))** 저장소에서 작업할 때 항상 준수해야 하는 **아키텍처 규칙, 스킬 연계, Git 작업 수칙**을 정의합니다.

> ⚠️ **블로그 포스트 작성·수정 시 필수 확인**
> - 포스트 작성·수정·리팩토링 작업 시에는 반드시 **`blog-writing` 스킬**([.agents/skills/blog-writing/SKILL.md](.agents/skills/blog-writing/SKILL.md))과 그 하위 참조 문서([writing-tone.md](.agents/skills/blog-writing/references/writing-tone.md))를 먼저 읽고 페르소나, 문체, Front Matter/Mermaid 규격, 상세 집필 체크리스트, QA 절차를 준수해야 합니다. (Claude Code는 `.claude/skills` 심볼릭 링크를 통해 동일한 스킬을 자동 인식합니다.)
> - **AI 작성 사실 비노출 원칙**: 공개 블로그 포스트 본문·요약·메타데이터·주석 어디에도 **AI(Antigravity, Claude, ChatGPT 등)를 활용해 블로그 글을 작성·생성·검수했다는 내용이 들어가서는 안 됩니다.** 모든 글은 작성자(김남주)가 직접 경험하고 정리한 1인칭 엔지니어링 기록으로만 서술합니다.

---

## 1. 블로그 아키텍처 개요

- **엔진**: Jekyll v4.4.x + `jekyll-theme-chirpy` v7.6.0 (Gem 기반 배포)
- **런타임**: Ruby 3.4 (GitHub Actions 및 Dev Container 표준)
- **배포 환경**: GitHub Pages (`.github/workflows/pages-deploy.yml`) + 프로덕션 이미지 CDN(`_config_prod.yml`, jsDelivr)
- **개발 환경**: VS Code Dev Container (`.devcontainer/devcontainer.json`, Debian Bookworm 기반)

| 경로 | 용도 및 주의사항 |
| :--- | :--- |
| `_posts/{대분류}/{중분류}/` | 계층형 카테고리 디렉토리 구조 및 블로그 포스트 마크다운 파일 (`YYYY-MM-DD-title.md`) |
| `_drafts/` | 미완성 초안 포스트 보관소 (프로덕션 빌드 제외) |
| `assets/images/YYYY-MM-DD/` | 포스트 이미지 자산 저장소 (`/` 경로 사용 시 프로덕션 jsDelivr CDN 자동 적용) |
| `.agents/skills/blog-writing/` | 글쓰기·페르소나·QA 표준 스킬 (SSOT, `.claude/skills`에서 심볼릭 링크) |
| `_includes/metadata-hook.html` | **Chirpy 공식 확장 훅** (네이버 서치어드바이저, 애드센스, linkpreview CSS, `noindex`, `BreadcrumbList` JSON-LD, 접근성 스크립트 주입용). **절대 `_includes/head.html`을 통째로 덮어쓰지 말 것!** |
| `_includes/linkpreview.html` | `jekyll-linkpreview` OG 지원 사이트용 미리보기 카드 템플릿 |
| `_includes/linkpreview_nog.html` | OpenGraph가 없는 사이트용 fallback 템플릿 |
| `_plugins/category-folder-hook.rb` | `_posts/{대분류}/{중분류}/` 폴더 경로 기반 카테고리 자동 주입 훅 (Front Matter에 `categories` 생략) |
| `_plugins/posts-lastmod-hook.rb` | Git 커밋 히스토리 기반 `last_modified_at` 자동 주입 훅 |
| `_plugins/seo-sitemap-hook.rb` | 얇은 태그 아카이브(`/tags/*/`)·페이지네이션(`/page2+/`) `sitemap.xml` 제외 및 `noindex` 자동 주입 훅 |
| `_plugins/image-dimensions-hook.rb` | 로컬 이미지의 고유 `width`/`height` 자동 주입 훅 (CLS 방지, `fastimage` 활용) |
| `_plugins/locale-override-hook.rb` | Chirpy 테마 로케일 라벨(`post.relate_posts` 등) 인메모리 오버라이드 훅 |

---

## 2. 품질 및 빌드 검증 (Quality Assurance)

변경 작업이 끝나면 보고 전 반드시 빌드·링크·Mermaid 검증을 수행합니다(호스트에 Ruby 3.4가 없는 경우 Python 정적 검증을 수행하고 CI 빌드 확인 안내).

```bash
# 1. 사이트 빌드 검증
bundle exec jekyll build -d /tmp/_site

# 2. 내부 링크, 이미지 깨짐, 프로토콜 검사 (htmlproofer)
bundle exec htmlproofer /tmp/_site \
  --disable-external \
  --ignore-urls "/^http:\/\/127.0.0.1/,/^http:\/\/0.0.0.0/,/^http:\/\/localhost/"
```

---

## 3. Git 및 작업 수칙

- **작업 브랜치**: 사용자의 요청에 따라 별도의 feature 브랜치 없이 **`main` 브랜치에서 직접 작업**합니다(단, 원격 환경에서 검토가 필요할 때는 PR 브랜치 사용 가능).
- **⚠️ 커밋(Commit) 및 업로드(Push) 권한 원칙 (환경별 구분)**:
  - **로컬 환경 (사용자 PC / Dev Container)**:
    - **AI 에이전트는 절대 직접 `git commit` 또는 `git push`를 실행하지 않습니다.**
    - 작업 및 QA 검증 완료 후 변경 파일 내역과 아래 형식의 추천 커밋 명령어만 텍스트로 제시합니다:
      ```bash
      git add -A
      git commit -m "문서: [작업 요약]"
      git push origin main
      ```
  - **원격 클라우드 VM 환경 (Antigravity 클라우드 세션 등)**:
    - 사용자가 직접 원격 VM의 워킹 트리에 접근할 수 없으므로, **작업 및 QA 검증 완료 후 사용자의 명시적 승인을 받아** `git commit`·`git push`(또는 브랜치 푸시 후 GitHub PR 생성)를 대행할 수 있습니다.
    - 단, 승인 없이 임의로 커밋·푸시하지 않으며 커밋 전 변경 파일 목록과 커밋 메시지를 투명하게 안내합니다.
- **커밋 메시지 작성 원칙 (100% 한글 작성)**:
  - 영문 접두사(`docs:`, `fix:`, `feat:` 등) 대신 **순수 한글로만 작성**합니다.
  - 예시:
    - `"글 작성: 자바 표준 스펙 시리즈 1~12편 완결"`
    - `"수정: 목차 접힘 현상 SCSS 오버라이드로 해결"`
    - `"유지보수: AGENTS.md 배포 제외 및 미사용 리소스 정리"`
    - `"설정: 글쓰기 가이드라인을 공용 에이전트 스킬로 마이그레이션"`
