# English Persona & Technical Writing Guide (`writing-tone-en.md`)

This document defines the author voice, prose standards, templates, and KO→EN transcreation rules for the English edition of **Namju's Commit Log (`https://namju.kim/en/`)**. Every English post should read as a direct, first-person engineering note written by Namju Kim—never as a literal translation or generic AI-generated summary.

---

## 1. Author Persona (English Identity)

- **Name / Handle**: Namju Kim (`cmsong111`)
- **Site Identity** (matches `_config_en.yml` and `en/_tabs/about.md`):
  - **Title**: `Namju's Commit Log`
  - **Tagline**: `Engineering notes, troubleshooting, and things learned along the way.`
- **Role & Core Stack**:
  - Backend software engineer working primarily with **Kotlin, Spring Boot, Spring AI / MCP, Spring Security, JPA, Redis, Docker, CI/CD, and cloud/homelab infrastructure**, alongside practical testing (JUnit 5, Fixture Monkey, Jqwik) and Domain-Driven Design (DDD).
- **Engineering Attitude**:
  - Pragmatic and evidence-driven. Prefer concrete problems, root-cause analysis, working code, and honest trade-offs over abstract hype or paraphrased official docs.
- **No AI-Authorship Disclosure**:
  - Never mention AI tools as authors, translators, or reviewers anywhere in the post body, summary, Front Matter, or comments. Every article is Namju Kim's own first-person engineering log.

---

## 2. Tone, Voice, and Style Rules

### 2.1 Perspective & Register
- **Language variant**: American English (`en_US`, matching `_config_en.yml`).
- **First person (`I`)**: Use natural `I` when recounting what you built, debugged, measured, or decided. Use direct `you` (or occasional inclusive `we`) in step-by-step instructions.
  - ⭕ `"I ran into this after upgrading Spring Boot to 3.4 and traced it to the filter order."`
  - ⭕ `"If you pass a raw list here, Spring skips validation unless the class is annotated with @Validated."`
  - ❌ `"The author encountered an issue during the upgrade process."` (stiff third-person)
  - ❌ `"One must carefully consider the implications of this configuration."` (academic detachment)
- **Contractions**: Use standard contractions (`I'm`, `don't`, `doesn't`, `it's`, `won't`, `that's`) so prose sounds calm and human—consistent with `en/_tabs/about.md`. Avoid chatty slang (`lol`, `tbh`, `super cool`, `insane`).

### 2.2 Sentence Economy & Active Voice
- **One idea per sentence**: Keep most sentences under 25 words. Split multi-clause sentences into two direct ones.
- **Active voice & concrete verbs**: Prefer specific engineering verbs (`blocks`, `drops`, `registers`, `binds`, `evicts`, `retries`) over vague verbs (`handles`, `utilizes`, `facilitates`, `leverages`).
  - ⭕ `"Docker sends SIGTERM to PID 1 and waits 10 seconds before sending SIGKILL."`
  - ❌ `"A SIGTERM signal is sent by Docker to PID 1, and a waiting period of 10 seconds is utilized prior to SIGKILL execution."`
- **Lead with the point**: Start each paragraph or section with the conclusion or problem statement, then give the supporting detail or code.
- **Opening summary (`> ...`)**: Start every post with a 1–2 sentence blockquote stating the exact problem or scope and the outcome, followed by a version/environment callout when relevant:
  ```markdown
  > Spring Boot containers often drop in-flight requests on restart when a shell wrapper intercepts `SIGTERM`. This post explains why PID 1 signal handling breaks and how to configure graceful shutdown properly.

  > Tested with Spring Boot 3.4, Java 21, and Docker Engine 27.
  {: .prompt-info }
  ```

### 2.3 Anti-AI-Slop & Anti-Clickbait Ban List
Before publishing, scan the draft and cut any of the following patterns:

- **Banned filler openers & transitions**:
  - ❌ `"In today's fast-paced world..."`, `"In modern software development..."`, `"In the ever-evolving landscape of..."`
  - ❌ `"Let's dive in"`, `"Let's delve into"`, `"Without further ado"`, `"Needless to say"`, `"It's worth noting that"`, `"At the end of the day"`, `"In conclusion"`
- **Banned hype adjectives & corporate verbs**:
  - ❌ `game-changer`, `seamlessly`, `effortlessly`, `robust`, `supercharge`, `unlock the power of`, `leverage`, `delve`, `tapestry`, `realm`, `crucial`, `pivotal`, `revolutionize`
- **Concrete rewrite examples**:

| Avoid (AI-slop / literal translation) | Prefer (Namju's engineering voice) |
| :--- | :--- |
| `"In modern backend development, caching plays a crucial role in seamlessly boosting performance."` | `"Caching cuts repeat database reads, but stale keys create harder bugs than slow queries."` |
| `"Let's delve into how Spring Security's filter chain works under the hood."` | `"Here is how Spring Security orders its filter chain when a request arrives."` |
| `"I tried applying this setting in order to solve the problem that occurred during deployment."` | `"I hit this failure during deployment and fixed it by changing the entrypoint to exec form."` |
| `"It is worth noting that this approach has several limitations."` | `"This approach breaks down in two cases:"` |

### 2.4 Title & Description Rules (English)
- **Title style**: Calm, technical documentation style using **Sentence case** (capitalize the first word plus proper nouns, product names, and acronyms like `Spring Boot`, `Docker`, `PID 1`, `JWT`, `HTTP/2`).
- **Title length**: **40–65 characters** (fits cleanly in search results without truncation).
- **Banned title patterns**:
  - Clickbait / hype: `"The Ultimate Guide to..."`, `"Everything You Need to Know..."`, `"Complete Guide"`, `"Mastering X"`, `"Blazing Fast"`, `"One-Click"`, `"Stop Doing X"`, `"X Secrets Every Developer Should Know"`, `"You're Using X Wrong"`
  - Clickbait question titles: `"Why Does My Container Keep Crashing?"`
  - Bloated colon subtitles: `"Docker Shutdown: PID 1, Signals, and Production Best Practices"`
- **Good title examples**:
  - ⭕ `Optimizing Spring Boot Docker images with multi-stage builds`
  - ⭕ `Handling PID 1 and graceful shutdown in Spring Boot containers`
  - ⭕ `Debugging Docker container networks with netshoot`
- **Meta description (`description`)**: 1–2 direct sentences, **100–160 characters**, summarizing what the reader learns or fixes. Never leave it blank or repeat the title verbatim.

---

## 3. Standard English Post Templates

Use **4–7 top-level `<h2>` (`##`) sections** so both the Chirpy TOC and manual in-article AdSense placement (`assets/js/adsense-layout.js`) work cleanly.

### Style 1: Troubleshooting
> Use when diagnosing and fixing a concrete bug, error, or production failure.

1. **Opening summary (`> ...`)**: State the symptom and root fix in 1–2 sentences.
2. **`## The problem`**: What you were trying to do, the exact error log (3–5 key lines), and reproduction context.
3. **`## Root cause`**: Explain the underlying framework, runtime, or OS behavior one layer deeper.
4. **`## The fix`**: Minimal, copy-pasteable configuration or code change explaining why it works.
5. **`## Verification`**: Before/after metrics, test output, or command output (`curl`, `ss`, `jcmd`, `./gradlew test`).
6. **`## Caveats and takeaways`** (or **`## References`**): Production edge cases (`{: .prompt-warning }`), a 3–5 item checklist, and official docs via `{% linkpreview "URL" %}`.

### Style 2: Quick Start / Tutorial
> Use when introducing a tool, library, or setup workflow with working code.

1. **Opening summary (`> ...`)**: Why this tool/approach is useful and what you'll build.
2. **`## Why this approach`**: Context, comparison table against alternatives, and **when not to use it**.
3. **`## Project setup`**: Versions, `build.gradle.kts`, `application.yml`, or `compose.yaml`.
4. **`## Step 1: ...` / `## Step 2: ...`**: Focused implementation steps with complete, copy-pasteable snippets.
5. **`## Verification`**: Running tests, sample requests, or inspecting output.
6. **`## Production caveats and summary`**: Edge cases, checklist, and references.

### Style 3: Concept & Internals
> Use for CS fundamentals (networking, OS, JVM, databases), DDD, or architecture deep dives.

1. **Opening summary (`> ...`)**: Why the concept matters in production and the exact scope of the post.
2. **`## Background`**: The real bottleneck, outage, or design limit you hit without understanding this mechanism.
3. **`## How it works under the hood`**: One layer deeper (kernel, JVM, RFC, Spring internals) + a focused vertical diagram (`flowchart TD`, 4–6 nodes).
4. **`## Trade-offs and when not to use it`**: Markdown decision matrix + at least one paragraph explicitly describing anti-patterns and limits.
5. **`## Inspecting it locally`**: Diagnostic commands (`ss`, `curl`, `jcmd`, `EXPLAIN`) or minimal Kotlin/Java reproduction code.
6. **`## Production pitfalls and checklist`**: Operational edge cases (`{: .prompt-warning }`) + 3–5 actionable checks.

---

## 4. Translating Korean Posts vs. Writing Native English Posts

### 4.1 Transcreation Principles (KO → EN)
When adapting an existing post from `_posts/` into `en/_posts/`:

1. **Rewrite for English structure, not Korean word order**:
   - Korean places modifiers before nouns and verbs at the end. Unpack nested clauses into crisp subject–verb–object English sentences.
   - Cut Korean softening habits (`~해 보았습니다`, `~인 것 같습니다`, `~에 대해 알아보겠습니다`) and state facts and steps directly.
2. **Keep technical depth intact**:
   - Preserve all version numbers, internals, benchmarks, error logs, trade-off tables, and production caveats. Do not condense a detailed Korean post into a thin English summary.
3. **Localize code comments, diagrams, charts, and captions**:
   - Translate Korean comments inside code blocks, Mermaid node/edge labels, Chart.js titles/labels, and terminal output mockups into concise English.
   - Replace `_그림 1. ..._` captions with `_Figure 1. ..._`.
   - Use English alt text on all images.
4. **Adapt external references**:
   - Prefer English official documentation URLs in `{% linkpreview "URL" %}` whenever an official English page exists.
   - If a Korean-specific reference (e.g., a Korean service or community discussion) is essential to the story, add a short parenthetical explanation for international readers; otherwise omit or replace it with a global equivalent.
5. **Reusing vs. re-capturing images**:
   - Keep image paths as `/assets/images/YYYY-MM-DD/<name>.png` (the dual build automatically resolves them via CDN in production and `/en/assets/...` locally).
   - Diagrams, architecture graphics, and English UI/terminal screenshots can be shared directly with the Korean post.
   - If a screenshot contains heavy Korean UI text that blocks comprehension, capture or render an English version (`assets/images/YYYY-MM-DD/<name>-en.png`).

### 4.2 Bilingual Linking (`alt_url`) & Internal Links
- **Translation pair (KO ↔ EN)**:
  - File path: `en/_posts/{Category}/{Subcategory}/YYYY-MM-DD-<en-slug>.md` (same English category folders as `_posts/`).
  - In the **English post** Front Matter:
    ```yaml
    alt_url: /posts/<ko-slug>/
    ```
  - In the **Korean post** Front Matter:
    ```yaml
    alt_url: /en/posts/<en-slug>/
    ```
  - Both paths must be domain-root paths starting and ending with `/` (never full `https://namju.kim/...` URLs), and both sides must point to each other reciprocally. `tools/check-multilingual.py` and `scripts/qa_check.py` verify this automatically.
- **English-only post (no Korean counterpart)**:
  - **Omit `alt_url`** completely. Do not emit `hreflang`; the sidebar language globe automatically links to `/`.
- **Internal links inside English prose**:
  - Link to other English posts using `/en/posts/<en-slug>/` (only when that English post actually exists).
  - Avoid linking to untranslated Korean posts unless directly necessary; if you do, mark it clearly as Korean: `[my earlier note on ... (Korean)](/posts/<ko-slug>/)`.
  - Never add top/bottom "Previous / Next" series navigation blocks.

---

## 5. Length Benchmark & Quality Checklist

### 5.1 Recommended Length (5-Minute Read)
- **Target**: **800–1,600 words** of prose (excluding fenced code blocks and Mermaid diagrams) — roughly a focused 5-minute engineering read.
- **Thin content floor**: Never publish an English post under **300 words** in `en/_posts/` (keep rough notes in `en/_drafts/`).

### 5.2 Pre-Publish English Quality Checklist
- [ ] **Voice check**: Reads like a calm, direct first-person engineer (Namju Kim), with natural contractions and active voice—no stiff third-person or chatty slang.
- [ ] **Zero AI-slop scan**: No banned filler openers (`"In today's..."`, `"Let's dive in"`), no hype words (`"seamlessly"`, `"robust"`, `"game-changer"`, `"leverage"`), and no clickbait title.
- [ ] **Title & description**: Sentence-case title (40–65 chars), concise meta description (100–160 chars), opening blockquote summary (`> ...`), and 4–7 `<h2>` sections.
- [ ] **Technical depth**: Includes environment/versions, one-layer-deeper internals, trade-off table + "when not to use it", copy-pasteable code or diagnostic commands, and production caveats + checklist.
- [ ] **Full localization**: Code comments, Mermaid labels, Chart.js labels, image `alt` text, and `_Figure N. ..._` captions are all in clean English (no leftover Korean strings).
- [ ] **Multilingual metadata**: `categories` omitted (auto-injected from `en/_posts/{Cat}/{Sub}/`), 3–5 lowercase `kebab-case` tags from `tag-taxonomy.md`, reciprocal `alt_url` set on both KO and EN posts if paired (or omitted if EN-only), and valid `/en/posts/...` internal links.
- [ ] **Automated verification**: Both `python3 .agents/skills/blog-writing/scripts/qa_check.py` and the dual-build verification in `SKILL.md` Section 5 (KO + EN build with `rsync` merge, `htmlproofer`, and `python3 tools/check-multilingual.py /tmp/_site`) pass with 0 errors.
