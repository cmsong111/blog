# 표준 태그 사전 (tag-taxonomy.md)

**남주의 커밋로그([https://namju.kim](https://namju.kim))**의 모든 포스트는 아래 **표준 태그 사전(103개)**을 우선 재사용합니다.

## 태그 작성 원칙
1. **형식**: 100% 영문 소문자 `kebab-case` (`^[a-z0-9]+(?:-[a-z0-9]+)*$`) — 대문자, 한글, 공백, 점(`.`) 금지
2. **개수**: 포스트당 **3~5개** (단일 포스트 내 중복 태그 금지)
3. **중복 금지**: 동의어(`ci`/`cicd` → `ci-cd`, `test` → `testing`, `cache` → `caching`), 약어+풀네임 동시 기재(`mcp`+`model-context-protocol` → `mcp`), 카테고리명 중복 1회성 태그 생성 금지
4. **신규 태그 추가 기준**: 기존 103개 태그로 표현할 수 없고 **향후 2편 이상 반복 사용될 핵심 기술/개념 키워드**일 때만 추가하며, 추가 시 이 문서에도 함께 등록합니다.

---

## 도메인별 표준 태그 목록 (103개)

### 1. 언어 · 핵심 프레임워크 (14)
`java` · `kotlin` · `typescript` · `ruby` · `spring` · `spring-boot` · `spring-security` · `spring-ai` · `spring-mvc` · `jpa` · `swing` · `thymeleaf` · `gradle` · `refactoring`

### 2. Java 표준 · 아키텍처 · 백엔드 설계 (15)
`jsr` · `jakarta-ee` · `jdbc` · `json` · `json-schema` · `ddd` · `architecture` · `backend` · `concurrency` · `transaction` · `async` · `reactive` · `batch` · `parsing` · `rest-api`

### 3. API · 통신 · 데이터 · 캐시 (10)
`rest-client` · `websocket` · `sse` · `database` · `postgresql` · `redis` · `caching` · `storage` · `networking` · `dns`

### 4. AI · LLM · 에이전트 (15)
`ai` · `llm` · `gemini` · `ollama` · `ai-agent` · `agent-skills` · `mcp` · `tool-calling` · `prompt-engineering` · `structured-output` · `rag` · `multimodal` · `guardrails` · `hitl` · `search-grounding`

### 5. 보안 · 인증 (6)
`security` · `jwt` · `oauth2` · `sso` · `oidc` · `https`

### 6. Docker · Linux · DevOps · 홈랩 (15)
`docker` · `docker-compose` · `homelab` · `linux` · `ci-cd` · `github-actions` · `github` · `git` · `nginx` · `healthcheck` · `monitoring` · `prometheus` · `grafana` · `observability` · `logging` · `automation`

### 7. 프론트엔드 · Vite · 빌드 (14)
`frontend` · `vite` · `vite-plugin` · `rollup` · `build-tools` · `css` · `assets` · `dev-server` · `ssr` · `monorepo` · `code-splitting` · `compression` · `dx` · `documentation`

### 8. 테스트 · 성능 · 블로그 운영 (13)
`testing` · `fixture-monkey` · `mock-data` · `troubleshooting` · `performance` · `blog` · `jekyll` · `chirpy` · `github-pages` · `seo` · `adsense` · `cdn` · `configuration`
