---
name: blog-writing
description: >-
  남주의 커밋로그(namju.kim) 기술 블로그 포스트를 작성·수정·최신화·정기 점검할 때 사용하는 표준 운영 스킬.
  작성자 페르소나, 톤앤매너, SEO·애드센스 연계 구조, Front Matter·카테고리 규격, Mermaid 문법,
  이미지 내재화·보안 규칙, 시리즈 병렬 집필 절차 및 자동 QA 스크립트(scripts/qa_check.py)를 포함합니다.
---

# 남주의 커밋로그 운영 및 글쓰기 스킬 (`blog-writing`)

블로그 포스트 작성·수정·최신화·정기 점검 시 반드시 아래 참조 문서를 확인하고, 작업 종료 전 내장 QA 스크립트(`scripts/qa_check.py`)를 실행해 오류 0건을 검증합니다.

- **톤앤매너·템플릿 3종·심화 집필 체크리스트**: [`references/writing-tone.md`](./references/writing-tone.md)
- **표준 태그 사전 (103개 SSOT)**: [`references/tag-taxonomy.md`](./references/tag-taxonomy.md)
- **블로그 운영·애드센스·정기 유지보수 플레이북**: [`references/operations-guide.md`](./references/operations-guide.md)
- **자동 QA 검증 스크립트**: [`scripts/qa_check.py`](./scripts/qa_check.py)
- **터미널 실행 결과 캡처 생성기**: [`scripts/render_terminal.py`](./scripts/render_terminal.py)
- **웹 캡처 부분 파싱·강조·마스킹 후처리기**: [`scripts/annotate_screenshot.py`](./scripts/annotate_screenshot.py)

---

## 1. 작업 유형별 표준 워크플로우

### A. 신규 포스트 작성 (단편)
1. **톤앤매너 장착**: [`references/writing-tone.md`](./references/writing-tone.md)를 읽고 경어체(`~합니다/~습니다`), 담백한 제목 원칙, 3대 템플릿(트러블슈팅 / 튜토리얼 / 개념·아키텍처 심화) 확인
2. **공식 문서 팩트체크**: 추측 작성 금지. 최신 공식 문서·릴리즈 노트 기준으로 버전과 아티팩트명·설정 키를 검증
3. **경로 · 날짜 · 태그 결정**:
   - `_posts/{대분류}/{중분류}/YYYY-MM-DD-kebab-case-slug.md` (단, 서로 다른 대분류 아래 동일 중분류명 금지)
   - **미래 날짜 금지** (`date <= 오늘`, Jekyll `future: false` 기본값)
   - **퍼머링크 슬러그 중복 금지** (전역 퍼머링크가 `/posts/:title/`이므로 파일명의 `slug`는 저장소 전체에서 유일해야 함)
   - **태그**: [`references/tag-taxonomy.md`](./references/tag-taxonomy.md)의 표준 103개 소문자 kebab-case 태그에서 3~5개 우선 선택
4. **구조 설계 (`<h2>` 4~7개 권장)**:
   - 본문 수동 인아티클 광고(`assets/js/adsense-layout.js`)가 직계 `<h2>` 4개 이상일 때 45% 지점, 8개 이상일 때 78% 지점에 자동 삽입되므로 **`<h2>` 섹션을 4~7개로 균형 있게 나누면 목차(TOC)와 광고 배치가 모두 깔끔하게 동작**합니다.
5. **분량 및 품질 기준**:
   - **코드 블록·Mermaid 제외 순수 본문 1,500 ~ 3,500자 내외** (5분 읽기 분량)
   - 상황별 선택 기준표(Decision Matrix) + "언제 쓰지 말아야 하는가" + 내부 동작 원리(One Layer Deeper) + 복붙 가능한 최소 재현 코드/진단 명령 + 운영 함정(Edge Case) + 마무리 체크리스트 포함
   - 본문 문맥상 기존 블로그 글(`/posts/<slug>/`)과 직결되는 지점이 있다면 **인라인 내부 링크 1~2개**를 자연스럽게 연결 (단, 상·하단 이전/다음 시리즈 네비게이션 블록은 금지)
   - 600자 미만의 메모/링크 1줄 초안은 절대 `_posts/`에 두지 않고 `_drafts/`에 보관 (Thin Content 방지)
6. **QA 실행 및 보고**: `python3 .agents/skills/blog-writing/scripts/qa_check.py` 실행 후 `AGENTS.md` 커밋 컨벤션(`post:` / `edit:` 등 영문 접두사 + 한글 요약)으로 커밋 명령어만 제시 (`git commit`/`push` 금지)

### B. 시리즈 연재 작성 (3편 이상)
1. **스캐폴딩 선행**: 비어 있는 과거/현재 날짜 구간을 확인해 모든 편의 파일명·슬러그·Front Matter를 먼저 생성
2. **독립 완결 원칙 (시리즈 네비게이션 미사용)**: 각 포스트는 단독으로 읽어도 완결되도록 작성하며, **본문 상·하단에 "이전 글 / 다음 글" 시리즈 네비게이션 링크 블록을 넣지 않습니다** (관련 글·카테고리 탐색은 Chirpy 테마 기본 기능에 맡김)
3. **병렬 집필**: 파일 소유권을 겹치지 않게 분할(예: 3편씩)해 작성한 뒤, 전체 시리즈를 대상으로 `qa_check.py`로 문법·분량을 일괄 검증

### C. 기존 포스트 최신화 / 리팩토링
1. **버전·생태계 변화 반영**: 아카이브·지원 종료·Breaking Change가 생긴 글은 원문을 무작정 지우기보다 상단에 `{: .prompt-warning }` 콜아웃으로 변경 이력과 대안(포크/후속 도구)을 명시
2. **후속 버전 글 연결**: v1 → v2처럼 후속 글이 발행되면 기존 글 상단에 `{: .prompt-info }` 콜아웃으로 최신 글 링크 연결

---

## 2. Front Matter · SEO · 카테고리 규격

- `_plugins/category-folder-hook.rb`가 폴더 경로로 `categories`를 자동 주입하므로 **Front Matter에서 `categories`는 생략하고 `tags`만 작성**합니다.
- **표준 카테고리 폴더**:
  - `AI > Concept`: `_posts/AI/Concept/`
  - `Blog > Jekyll`: `_posts/Blog/Jekyll/`
  - `Book > DDD`: `_posts/Book/DDD/`
  - `CS > Database / JVM / Web-Network`: `_posts/CS/{중분류}/`
  - `Dev`: `_posts/Dev/`
  - `Docker > Compose / Container / Image / Network`: `_posts/Docker/{중분류}/`
  - `Home Server > Containers`: `_posts/Home Server/Containers/`
  - `Java > Standard`: `_posts/Java/Standard/`
  - `Java > Swing`: `_posts/Java/Swing/`
  - `Kotlin > Practice`: `_posts/Kotlin/Practice/`
  - `Spring > Feature`: `_posts/Spring/Feature/`
  - `Spring > JPA`: `_posts/Spring/JPA/`
  - `Spring > Observability`: `_posts/Spring/Observability/`
  - `Spring > Redis`: `_posts/Spring/Redis/`
  - `Spring > Spring-AI`: `_posts/Spring/Spring-AI/`
  - `Spring > Testing`: `_posts/Spring/Testing/`
  - `Spring > Wanted-Challenge`: `_posts/Spring/Wanted-Challenge/`
  - `Vite`: `_posts/Vite/`

```yaml
---
title: "핵심 기술 키워드와 적용 대상·목적이 명확한 담백한 제목 (30~55자 권장)"
description: "검색엔진·SNS 카드용 핵심 요약 1~2문장 (80~155자 권장, 절대 누락 금지)"
date: YYYY-MM-DD HH:MM:SS +0900
tags: [spring-boot, kotlin, jpa, redis] # 100% 영문 소문자 kebab-case, 글당 3~5개 (동의어·약어 중복 금지, 기존 표준 태그 우선 재사용)
mermaid: true # 본문에 mermaid 코드 블록이 있을 때만 선언 (없으면 생략)
chart: true # 본문에 {: .chart-js } Chart.js 블록이 있을 때만 선언 (없으면 생략)
image:
  path: /assets/images/YYYY-MM-DD/thumbnail.png # 로컬 저장 시 프로덕션 jsDelivr CDN 자동 적용
  alt: 대표 썸네일 설명
---
```

> **제목 금지어**: 의문형(`~할 때?`, `~죽는 이유`), 과장·어그로 표현(`완벽 해결`, `완전 정복`, `초고속`, `원클릭`, `~의 모든 것`, `치명적 위험`), 그리고 불필요한 콜론(`:`) 부제 나열을 피하고 한 문장으로 간결하게 작성합니다.

---

## 3. 시각 자료 · 캡처 · JS 차트 · 보안 규칙

1. **로컬 내재화 우선 (외부 핫링크 금지)**: `velog.velcdn.com` 등 외부 호스팅 이미지에 의존하지 말고 `assets/images/YYYY-MM-DD/`에 저장해 `/assets/images/...` 경로로 참조합니다(이중 슬래시 `/assets//` 주의). 프로덕션 배포 시 `_config_prod.yml`의 jsDelivr CDN이 자동 적용됩니다.
2. **해상도 · 용량 · 캡션 기준**:
   - Chirpy 본문 폭(2x 레티나) 기준 **가로 1,200~1,600px**, WebP 또는 최적화 PNG **100~300KB**(단일 파일 **1MB 이하** 필수) 권장
   - 모든 본문 이미지에는 구체적 `alt`를 작성하고, 바로 아래 `_그림 1. ..._` 한 줄 캡션을 붙여 스캐닝 가독성을 높입니다.
3. **시각 자료 유형별 의사결정 표 (무엇을 캡처하고 어떻게 만들 것인가)**:

| 유형 | 적합한 장면 | 표준 제작 도구 | 금지 사항 |
| :--- | :--- | :--- | :--- |
| **실제 웹 캡처** | Before/After 변화(DevTools·Lighthouse·Grafana·모바일 390px), 클릭 위치가 헷갈리는 클라우드/콘솔 UI | Antigravity 사이드바 `browser` 서브에이전트 + `scripts/annotate_screenshot.py` | 여백 많은 전체 화면, 코드·YAML 스크린샷 |
| **터미널 PNG** | 테스트 통과, `curl` 응답, `ss`/`jcmd`/`EXPLAIN` 실제 출력 증거 | `scripts/render_terminal.py` (Tokyo Night 다크 테마, Win/Mac/Linux 폰트 대응) | 30줄 이상 긴 로그 통째로 이미지화(핵심 5~12줄만) |
| **JS 수치 차트** | 벤치마크·전후 수치 비교(p99 지연시간, 번들 크기, 메모리 사용량) | 단순 1시리즈: 내장 `mermaid@11` `xychart-beta` / 다중 시리즈·인터랙티브: `chart: true` + `{: .chart-js }` | 의미 없는 AI 감성 배너·스톡 이미지 남발 |
| **구조 다이어그램** | 요청 흐름·상태 전이·아키텍처 | 4~6노드 세로 흐름: Mermaid `flowchart TD` / 넓은 메모리 맵·계층: 고정 비율 SVG/PNG | 모바일에서 글자가 뭉개지는 대형 `flowchart LR` |

4. **Antigravity 사이드바 브라우저 캡처 & 부분 파싱 4단계 파이프라인**:
   - **1단계 (사이드바 웹뷰 열기)**: Antigravity 내장 `browser` 서브에이전트로 대상 URL을 열고 뷰포트(데스크톱 `1280×800` 또는 모바일 `390×844`)와 로딩 완료를 확인합니다.
   - **2단계 (1차 부분 파싱 — DOM 요소 단위 캡처 우선)**: 가능한 경우 특정 CSS 셀렉터/컴포넌트 영역만 지정해 바로 캡처하고, 페이지 전체 문맥이 필요하면 뷰포트 단위로 캡처합니다.
   - **3단계 (2차 부분 파싱 & 후처리 — `scripts/annotate_screenshot.py`)**: 원본 캡처에서 핵심 UI 영역만 정밀 크롭(`--crop` / `--crop-pct` / `--auto-trim`), 클릭 지점 강조 박스(`--box`)·번호 배지(`--badge`), 민감정보 블러/마스킹(`--blur` / `--mask`)을 적용해 `assets/images/YYYY-MM-DD/<descriptive-name>.webp`(또는 `.png`)로 저장합니다.
     ```bash
     python3 .agents/skills/blog-writing/scripts/annotate_screenshot.py \
       --in /path/to/raw-capture.png \
       --out assets/images/YYYY-MM-DD/console-setting.webp \
       --crop-pct 15,10,70,65 \
       --box 420,180,260,48 \
       --badge 405,180,1 \
       --blur 60,40,240,28 \
       --max-width 1400
     ```
   - **4단계 (보안 재확인)**: API 키(`AIza...`, `sk-...`, `ghp_...`), 이메일, 계정 ID가 완전히 가려졌는지 `read_file`로 최종 이미지를 확인합니다(코드에도 환경 변수 `${API_KEY}` 표기).
5. **터미널 실행 결과 캡처 (`scripts/render_terminal.py`)**:
   - 이모지 대신 `✓`, `→`, `●` 기호를 사용하고 핵심 5~12줄만 깔끔하게 렌더링합니다:
     ```bash
     cat << 'EOF' | python3 .agents/skills/blog-writing/scripts/render_terminal.py \
       --title "zsh — ./gradlew test" \
       --out assets/images/YYYY-MM-DD/test-result.png
     [green]kimnamju@mbp[/]:[blue]~/projects/demo[/]$ ./gradlew test
     [green]✓[/] SampleTest > 정상 동작 검증 [muted](38ms)[/]
     [green]BUILD SUCCESSFUL[/] in 1s
     EOF
     ```
6. **문서 내 JS 차트 삽입 규칙 (2가지 방식)**:
   - **방식 A — 내장 Mermaid `xychart-beta` (추가 JS 0바이트, 단순 1시리즈 막대/선 차트 권장)**:
     - Front Matter에 `mermaid: true`만 선언(Chirpy v7.6의 `mermaid@11`이 기본 지원).
     ````markdown
     ```mermaid
     xychart-beta
         title "p99 응답 지연시간 비교 (ms)"
         x-axis ["G1GC", "Generational ZGC"]
         y-axis "Latency (ms)" 0 --> 200
         bar [145, 4]
     ```
     ````
   - **방식 B — 조건부 Chart.js 4 (다중 시리즈·도넛·호버 툴팁 등 인터랙티브 차트)**:
     - Front Matter에 `chart: true`를 선언하면 `_includes/metadata-hook.html`이 해당 글에서만 Chart.js 4와 `assets/js/chart-renderer.js`(다크/라이트 모드 자동 동기화)를 로드합니다.
     - 본문에는 유효한 Chart.js JSON 설정을 ` ```json ` 코드 블록으로 작성하고 직후 줄에 `{: .chart-js }`를 붙입니다:
     ````markdown
     ```json
     {
       "type": "bar",
       "data": {
         "labels": ["HTTP/1.1", "HTTP/2", "HTTP/3"],
         "datasets": [
           { "label": "초기 로딩 (ms)", "data": [820, 460, 310], "backgroundColor": "#7aa2f7" }
         ]
       },
       "options": {
         "plugins": { "title": { "display": true, "text": "프로토콜별 초기 페이지 로딩 비교" } }
       }
     }
     ```
     {: .chart-js }
     ````
7. **외부 참고 링크**: 단순 URL 나열 대신 `{% linkpreview "URL" %}` 태그를 적극 활용합니다.

---

## 4. Mermaid 다이어그램 문법 및 모바일 가독성 수칙

1. **모바일 가독성 우선 (가로 확장 금지)**:
   - 꼭 필요한 아키텍처·흐름 설명에만 사용하고, 단순 비교·목록은 **Markdown 표**로 대체합니다.
   - **세로 방향(`flowchart TD`)을 기본**으로 사용합니다(`flowchart LR`은 노드 2~3개의 초단순 흐름에만 제한적으로 허용).
   - 한 다이어그램에 너무 많은 내용을 담지 않습니다: 핵심 노드 **4~6개 이내**, `sequenceDiagram` 참여자(`participant`) **최대 3~4개 이내**, 노드/화살표 라벨은 **줄당 15자 내외의 짧은 키워드**로 압축합니다.
2. **노드 라벨 특수문자 인용**: 괄호 `()`, 대괄호 `[]`, 중괄호 `{}`, 슬래시 `/`, 콜론 `:`, `&`, `,` 등이 포함되면 반드시 큰따옴표(`A["Docker Engine (/var/run/docker.sock)"]`)로 감쌉니다.
3. **화살표·엣지 라벨**: `flowchart`에서는 `-->`, `-.->`, `==>`만 사용하고, 특수문자·공백이 있는 엣지 라벨은 `-->|"HTTP/WS 프록시"|`처럼 큰따옴표로 감쌉니다.
4. **서브그래프**: 화살표 목적지로 서브그래프 ID 대신 내부 노드 ID를 지정하고, 서브그래프에 직접 `class`를 부여하지 않습니다.
5. **스타일링 HTML 태그 배제**: `<font>`, `<div>`, `<span>`을 사용하지 않습니다(줄바꿈은 `\n` 또는 `<br/>`만 허용).
6. **Front Matter 일치**: 본문에 `mermaid` 블록이 있으면 `mermaid: true`, 없으면 생략해 불필요한 스크립트 로딩을 방지합니다.

---

## 5. 품질 검증 (QA) 절차

작업이 끝나면 보고 전 반드시 아래 QA 스크립트를 실행합니다.

```bash
# 1. 정적 전수 검증 (Front Matter, SEO, 분량, Mermaid, 이미지, 내부 링크, 보안)
python3 .agents/skills/blog-writing/scripts/qa_check.py

# 2. (Dev Container / Ruby 3.4 환경 사용 시) Jekyll 빌드 및 htmlproofer 검증
bundle exec jekyll build -d /tmp/_site
bundle exec htmlproofer /tmp/_site \
  --disable-external \
  --ignore-urls "/^http:\/\/127.0.0.1/,/^http:\/\/0.0.0.0/,/^http:\/\/localhost/"
```
