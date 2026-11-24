# 블로그 운영 및 유지보수 플레이북 (operations-guide.md)

**남주의 커밋로그([https://namju.kim](https://namju.kim))**를 장기적으로 안정·쾌적하게 운영하기 위한 기술 설정, 수익화(AdSense) 구조, 정기 유지보수 체크리스트를 정리한 문서입니다.

---

## 1. Google AdSense 수동 광고 운영 구조

- **정책**: 자동 광고(Auto Ads)는 포스트 카드 내부 깨짐 및 본문 무작위 삽입을 유발하므로 **OFF**를 유지하고, 아래 **수동 광고 단위 3종**만 사용합니다 (`ca-pub-9883771255224638`).
- **구현 파일**:
  - 로더: `_includes/metadata-hook.html` (`jekyll.environment == 'production'`일 때만 로드)
  - 배치 스크립트: `assets/js/adsense-layout.js` (Chirpy `_layouts/` 덮어쓰기 없음 → 테마 업그레이드 안전)
  - 스타일: `assets/css/jekyll-theme-chirpy.scss`

| 슬롯 이름 | `data-ad-slot` | 포맷 | 노출 위치 및 조건 |
| :--- | :--- | :--- | :--- |
| `namju-sidebar-vertical` | `5274823967` | 디스플레이 수직형 (`vertical`) | **넓은 화면(`>= 1200px`) 전용**. 포스트 페이지에서는 목차(`#toc-wrapper`) 바로 아래, 홈/목록 페이지에서는 `Trending Tags` 아래 `sticky` 고정 |
| `namju-in-article` | `4516149753` (PC) / `9442007524` (모바일) | 인아티클 (`fluid`, PC) / 슬림 가로 `320×100px` (모바일) | 포스트 본문(`.content`) 내 직계 `<h2>`가 **4개 이상**이면 45% 지점 `<h2>` 직전에 1개, **8개 이상**이면 78% 지점 `<h2>` 직전에 1개 추가 (PC는 인아티클, 모바일은 상하가 짧은 `320×100px` 슬림 배너 고정) |
| `namju-post-bottom` | `9442007524` | 디스플레이 수평형 (`horizontal`) | 포스트 본문 끝(`.post-tail-wrapper` 직전). 데스크톱(`>= 768px`)은 본문 폭 수평형(`fullWidthResponsive: false`), **모바일(`< 768px`)은 공식 슬림 배너 `320×100px` 고정** |

### 글 작성 시 광고·목차 궁합 팁
- 본문 직계 `<h2>` 섹션을 **4~7개**로 구성하면 중간 인아티클 광고가 1개만 가장 자연스러운 위치에 들어가며, 우측 목차(`#toc-wrapper #toc`, `max-height: 42vh`) 아래 세로형 광고도 한눈에 보입니다.
- 좁은 화면(`< 1200px`)에서는 사이드바 광고 자체가 DOM에 주입되지 않으므로 `availableWidth=0` 콘솔 에러가 발생하지 않습니다.

---

## 2. 초안(`_drafts/`) 및 발행(`_posts/`) 라이프사이클

1. **초안 작성 중**: 본문이 600자 미만이거나 링크·메모만 있는 글은 `_drafts/{카테고리}/YYYY-MM-DD-slug.md`에 보관합니다.
2. **발행 승격 조건**:
   - 코드·Mermaid 제외 순수 본문 1,500자 이상
   - `title`, `description`, `date`(오늘 이하, 비어 있는 날짜), `tags` 완비
   - `qa_check.py` 오류 0건 통과
3. **발행 이동**: `_posts/{카테고리}/`로 이동 후 커밋·푸시

---

## 3. 정기 유지보수 체크리스트 (월간 / 분기별)

```bash
# 원커맨드 전체 저장소 건강 점검
python3 .agents/skills/blog-writing/scripts/qa_check.py
```

1. **기술 최신성 점검 (분기별)**:
   - 홈서버 컨테이너(Docker 이미지 아카이브/유지보수 중단 여부), Spring Boot / Spring AI / Vite 메이저 릴리즈 변경점 확인
   - 더 이상 동작하지 않는 글은 상단에 `{: .prompt-warning }`으로 변경 이력과 대안 도구 안내 추가
   - 후속 버전(v1 → v2) 글 발행 시 기존 글 상단에 `{: .prompt-info }` 크로스 링크 추가
2. **자산 및 설정 점검**:
   - `assets/images/` 내 미사용(고아) 이미지 및 1MB 초과 이미지 정리
   - `_config.yml` `exclude` 및 `.github/workflows/pages-deploy.yml` `paths-ignore`에 내부 문서·스킬 폴더가 누락되지 않았는지 확인
3. **인프라·테마 버전 점검 (반기별)**:
   - `jekyll-theme-chirpy`, `jekyll`, `html-proofer`, GitHub Actions, Ruby 버전, `.devcontainer/devcontainer.json` 베이스 이미지 LTS 상태 확인
