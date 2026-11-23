# AI 에이전트 지침서 (AGENTS.md)

이 문서는 AI 어시스턴트(Antigravity, Claude Code, Copilot 등)가 **남주의 커밋로그([https://namju.kim](https://namju.kim))** 저장소에서 작업할 때 항상 준수해야 하는 **아키텍처 규칙, 스킬 연계, Git 작업 수칙**을 정의합니다.

> ⚠️ **블로그 포스트 작성·수정 시 필수 확인**
> 포스트 작성·수정·리팩토링 작업 시에는 반드시 **`blog-writing` 스킬**([.agents/skills/blog-writing/SKILL.md](.agents/skills/blog-writing/SKILL.md))과 그 하위 참조 문서([writing-tone.md](.agents/skills/blog-writing/references/writing-tone.md))를 먼저 읽고 페르소나, 문체, Front Matter/Mermaid 규격, 상세 집필 체크리스트, QA 절차를 준수해야 합니다.
> (Claude Code는 `.claude/skills` 심볼릭 링크를 통해 동일한 스킬을 자동 인식합니다.)

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
| `_includes/metadata-hook.html` | **Chirpy 공식 확장 훅** (네이버 서치어드바이저, 애드센스, linkpreview CSS 주입용). **절대 `_includes/head.html`을 통째로 덮어쓰지 말 것!** |
| `_includes/linkpreview.html` | `jekyll-linkpreview` OG 지원 사이트용 미리보기 카드 템플릿 |
| `_includes/linkpreview_nog.html` | OpenGraph가 없는 사이트용 fallback 템플릿 |
| `_plugins/category-folder-hook.rb` | `_posts/{대분류}/{중분류}/` 폴더 경로 기반 카테고리 자동 주입 훅 (Front Matter에 `categories` 생략) |
| `_plugins/posts-lastmod-hook.rb` | Git 커밋 히스토리 기반 `last_modified_at` 자동 주입 훅 |

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

- **작업 브랜치**: 사용자의 요청에 따라 별도의 feature 브랜치 없이 **`main` 브랜치에서 직접 작업**합니다.
- **⚠️ 커밋(Commit) 및 업로드(Push) 권한 원칙**:
  - **AI 에이전트는 절대 직접 `git commit` 또는 `git push`를 실행하지 않습니다.**
  - 코드/글 작성 및 QA 검증 완료 후, 변경 사항을 최종 커밋하고 원격 저장소에 푸시하는 것은 **전적으로 사용자(김남주)의 고유 권한 영역**입니다.
  - AI 에이전트는 작업이 끝나면 변경된 파일 내역을 투명하게 안내하고, 사용자가 직접 복사해서 실행할 수 있는 추천 커밋 명령어만 텍스트로 제시해야 합니다:
    ```bash
    git add -A
    git commit -m "문서: [작업 요약]"
    git push origin main
    ```
- **커밋 메시지 추천 원칙 (100% 한글 작성)**:
  - 영문 접두사(`docs:`, `fix:`, `feat:` 등) 대신 **순수 한글로만 작성**하여 추천합니다.
  - 예시:
    - `"글 작성: 자바 표준 스펙 시리즈 1~12편 완결"`
    - `"수정: 목차 접힘 현상 SCSS 오버라이드로 해결"`
    - `"유지보수: AGENTS.md 배포 제외 및 미사용 리소스 정리"`
    - `"설정: 글쓰기 가이드라인을 공용 에이전트 스킬로 마이그레이션"`
