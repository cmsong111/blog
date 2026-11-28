#!/usr/bin/env python3
"""
남주의 커밋로그(namju.kim) 한/영 통합 정적 QA 검증 스크립트.

검사 항목:
1. Front Matter 필수 필드 (title, description, date, tags) 및 categories 생략 여부
2. 제목 금지어 (KO 어그로/과장 표현, EN 클릭베이트/AI-slop 표현) 검사
3. 파일명 규칙, 미래 날짜, 언어별 퍼머링크·중분류 카테고리 슬러그 및 전역 태그 슬러그 중복 검사
4. 본문 분량 (코드·Mermaid 제외 순수 본문 KO < 600자 / EN < 300 words Thin Content 오류)
5. 다국어 번역 쌍(alt_url) 형식·대상 실재 여부·양방향 상호 참조(reciprocity) 검사
6. Mermaid 및 Chart.js 문법 (노드/엣지 특수문자 따옴표, 스타일링 HTML 태그, mermaid/chart flag 일치, JSON 유효성)
7. 이미지 무결성 (깨진 로컬 이미지, 빈 alt, 이중 슬래시 /assets//, 외부 핫링크, >1MB 대용량, 고아 이미지)
8. 내부 포스트 링크 (/posts/<slug>/, /en/posts/<slug>/) 깨짐 검사
9. 보안 (API 키 / 토큰 패턴 노출 검사) 및 미이스케이프 Liquid 구문({{ }}, GitHub alert 문법) 검사
10. 설정 검증 (_config.yml, _config_en.yml에 AGENTS.md 제외 여부)

사용법:
  python3 .agents/skills/blog-writing/scripts/qa_check.py
"""

import datetime
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict

POST_ROOTS = (
    ("ko", "_posts"),
    ("en", "en/_posts"),
)

PROHIBITED_TITLE_PATTERNS_KO = [
    r"완벽\s*해결",
    r"완전\s*정복",
    r"초고속",
    r"원클릭",
    r"의\s*모든\s*것",
    r"치명적\s*위험",
]

PROHIBITED_TITLE_PATTERNS_EN = [
    r"\bultimate\s+guide\b",
    r"\beverything\s+you\s+need\s+to\s+know\b",
    r"\bcomplete\s+guide\b",
    r"\bblazing\s+fast\b",
    r"\bone-click\b",
    r"\bgame-changer\b",
    r"\bmastering\b",
    r"\bstop\s+doing\b",
    r"\byou'?re\s+using\b.*\bwrong\b",
]

HOTLINK_DOMAINS = (
    "velog.velcdn.com",
    "static.wanted.co.kr",
    "user-images.githubusercontent.com",
)


def parse_frontmatter(content):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
    if not m:
        return None, content
    return m.group(1), m.group(2)


def get_fm_value(fm, key):
    m = re.search(rf"^{key}:\s*(.*)$", fm, re.M)
    return m.group(1).strip().strip("\"'") if m else ""


def parse_fm_tags(fm):
    lines = fm.splitlines()
    tags = []
    i = 0
    while i < len(lines):
        m = re.match(r"^tags?\s*:\s*(.*)$", lines[i])
        if m:
            rest = m.group(1).strip()
            if rest.startswith("[") and rest.endswith("]"):
                for item in rest[1:-1].split(","):
                    item = item.strip().strip("\"'")
                    if item:
                        tags.append(item)
            elif rest:
                for item in rest.split():
                    item = item.strip("\"'")
                    if item:
                        tags.append(item)
            else:
                i += 1
                while i < len(lines):
                    lm = re.match(r"^\s+-\s+(.*)$", lines[i])
                    if not lm:
                        break
                    item = lm.group(1).strip().strip("\"'")
                    if item:
                        tags.append(item)
                    i += 1
                continue
        i += 1
    return tags


def slugify_tag(tag):
    s = str(tag).strip().lower()
    s = re.sub(r"[^a-z0-9가-힣]+", "-", s)
    return s.strip("-")


def post_route(lang, slug):
    prefix = "/en" if lang == "en" else ""
    return f"{prefix}/posts/{slug}/"


def main():
    today_str = datetime.date.today().isoformat()
    posts_by_lang = {
        lang: sorted(glob.glob(f"{root}/**/*.md", recursive=True))
        for lang, root in POST_ROOTS
    }
    drafts = sorted(
        glob.glob("_drafts/**/*.md", recursive=True)
        + glob.glob("en/_drafts/**/*.md", recursive=True)
    )

    errors = defaultdict(list)
    warnings = defaultdict(list)

    slug_counts = {"ko": Counter(), "en": Counter()}
    valid_slugs = {"ko": set(), "en": set()}
    subcat_parents = {"ko": defaultdict(set), "en": defaultdict(set)}
    route_to_post = {}
    post_records = []
    all_img_refs = set()
    tag_slug_variants = defaultdict(lambda: defaultdict(list))
    declared_alt_urls = {}

    # Pass 1: filename, slug, subcategory structure, and frontmatter parsing
    for lang, root in POST_ROOTS:
        for p in posts_by_lang[lang]:
            rel_dir = os.path.relpath(os.path.dirname(p), root).replace("\\", "/")
            parts = rel_dir.split("/") if rel_dir != "." else []
            for depth in range(1, len(parts)):
                subcat_parents[lang][slugify_tag(parts[depth])].add(
                    "/".join(parts[: depth + 1])
                )

            with open(p, encoding="utf-8") as f:
                content = f.read()

            fm, body = parse_frontmatter(content)
            fname = os.path.basename(p)
            m_fn = re.match(r"^(\d{4}-\d{2}-\d{2})-(.+)\.md$", fname)
            effective_slug = None
            if not m_fn:
                errors["invalid_filename"].append(p)
            else:
                post_date, file_slug = m_fn.group(1), m_fn.group(2)
                fm_slug = get_fm_value(fm, "slug") if fm is not None else ""
                effective_slug = fm_slug or file_slug
                slug_counts[lang][effective_slug] += 1
                valid_slugs[lang].add(effective_slug)
                valid_slugs[lang].add(effective_slug.lower())
                if post_date > today_str:
                    warnings["future_dated_post"].append(f"{p} ({post_date})")

            route = post_route(lang, effective_slug) if effective_slug else None
            if route:
                route_to_post[route] = p

            post_records.append(
                {
                    "lang": lang,
                    "path": p,
                    "route": route,
                    "content": content,
                    "fm": fm,
                    "body": body,
                }
            )

    for lang in ("ko", "en"):
        for slug, cnt in slug_counts[lang].items():
            if cnt > 1:
                errors["duplicate_permalink_slug"].append(
                    f"[{lang}] {slug} ({cnt}회)"
                )

    # Pass 2: per-post content and metadata checks
    for rec in post_records:
        lang = rec["lang"]
        p = rec["path"]
        route = rec["route"]
        content = rec["content"]
        fm = rec["fm"]
        body = rec["body"]

        if fm is None:
            errors["missing_frontmatter"].append(p)
            continue

        # 1. Front Matter fields
        title = get_fm_value(fm, "title")
        desc = get_fm_value(fm, "description")
        date_val = get_fm_value(fm, "date")
        tags_val = get_fm_value(fm, "tags")
        alt_url = get_fm_value(fm, "alt_url")

        if not title:
            errors["missing_title"].append(p)
        if not desc:
            errors["missing_description"].append(p)
        elif len(desc) < 50 or len(desc) > 170:
            warnings["description_length_out_of_range"].append(f"{p} ({len(desc)}자)")
        if not date_val:
            errors["missing_date"].append(p)
        if not tags_val and not re.search(r"^tags:\s*\n\s*-", fm, re.M):
            warnings["missing_tags"].append(p)
        else:
            post_tags = parse_fm_tags(fm)
            seen_in_post = set()
            for tag in post_tags:
                if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", tag):
                    errors["invalid_tag_format"].append(f"{p}: {tag}")
                if tag in seen_in_post:
                    errors["duplicate_tag_in_post"].append(f"{p}: {tag}")
                seen_in_post.add(tag)
                tag_slug_variants[slugify_tag(tag)][tag].append(p)
            if len(post_tags) < 3 or len(post_tags) > 5:
                warnings["tag_count_out_of_range"].append(
                    f"{p} ({len(post_tags)}개)"
                )
        if re.search(r"^categories:\s*\S", fm, re.M):
            warnings["explicit_categories_in_fm"].append(p)

        # 1b. Bilingual alt_url validation
        if alt_url:
            if "://" in alt_url or not alt_url.startswith("/") or not alt_url.endswith("/"):
                errors["invalid_alt_url_format"].append(f"{p}: {alt_url}")
            else:
                expected_prefix = "/en/posts/" if lang == "ko" else "/posts/"
                if not alt_url.startswith(expected_prefix):
                    errors["invalid_alt_url_target_lang"].append(
                        f"{p}: {alt_url} (기대 접두사: {expected_prefix})"
                    )
                elif alt_url not in route_to_post:
                    errors["broken_alt_url"].append(f"{p} -> {alt_url}")
                if route:
                    declared_alt_urls[route] = alt_url

        # 2. Title style check
        if lang == "ko":
            for pat in PROHIBITED_TITLE_PATTERNS_KO:
                if re.search(pat, title):
                    warnings["prohibited_title_word"].append(f"{p}: {title}")
        else:
            for pat in PROHIBITED_TITLE_PATTERNS_EN:
                if re.search(pat, title, re.IGNORECASE):
                    warnings["prohibited_title_word"].append(f"{p}: {title}")

        # 3. Prose length (excluding code & mermaid blocks)
        prose = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
        if lang == "ko":
            prose_chars = len(re.sub(r"\s+", "", prose))
            if prose_chars < 600:
                errors["thin_content_under_600"].append(f"{p} ({prose_chars}자)")
        else:
            prose_words = len(
                re.findall(r"\b[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*\b", prose)
            )
            if prose_words < 300:
                errors["thin_content_under_300_words"].append(
                    f"{p} ({prose_words} words)"
                )

        # 4. Mermaid checks
        mermaid_blocks = re.findall(r"```mermaid\n(.*?)\n```", body, re.DOTALL)
        fm_mermaid = bool(re.search(r"^mermaid:\s*true\b", fm, re.M))
        if mermaid_blocks and not fm_mermaid:
            errors["mermaid_missing_fm_flag"].append(p)
        if not mermaid_blocks and fm_mermaid:
            warnings["mermaid_unused_fm_flag"].append(p)

        for block in mermaid_blocks:
            for line in block.splitlines():
                s = line.strip()
                if not s or s.startswith("%%"):
                    continue
                if re.search(r'[A-Za-z0-9_]+\[[^"\n]*[\(\)\/:][^"\n]*\]', s):
                    errors["mermaid_unquoted_node"].append(f"{p}: {s[:90]}")
                if re.search(r"<(font|span|div)[\s/>]", s, re.I):
                    errors["mermaid_styling_html"].append(f"{p}: {s[:90]}")
                for em in re.findall(r"\|([^\|]+)\|", s):
                    if not (em.startswith('"') and em.endswith('"')) and re.search(
                        r"[\(\)\/:&,]", em
                    ):
                        errors["mermaid_unquoted_edge"].append(f"{p}: |{em}|")

        # 4b. Chart.js block checks (```json ... ``` followed by {: .chart-js })
        chart_blocks = re.findall(
            r"```json\s*\n(.*?)\n```\s*\n\{:\s*\.chart-js\s*\}", body, re.DOTALL
        )
        fm_chart = bool(re.search(r"^chart:\s*true\b", fm, re.M))
        if chart_blocks and not fm_chart:
            errors["chart_missing_fm_flag"].append(p)
        if not chart_blocks and fm_chart:
            warnings["chart_unused_fm_flag"].append(p)
        for c_idx, c_block in enumerate(chart_blocks, 1):
            try:
                parsed = json.loads(c_block)
                if not isinstance(parsed, dict) or "type" not in parsed or "data" not in parsed:
                    errors["invalid_chart_json"].append(
                        f"{p} (chart #{c_idx}: type/data 필드 누락)"
                    )
            except json.JSONDecodeError as exc:
                errors["invalid_chart_json"].append(f"{p} (chart #{c_idx}: {exc.msg})")

        # 5. Image checks
        if "/assets//" in content:
            errors["double_slash_assets_path"].append(p)

        for alt_text, im in re.findall(r"!\[([^\]]*)\]\((/assets/[^)\s]+)\)", body):
            if not alt_text.strip():
                warnings["empty_image_alt"].append(f"{p}: {im}")
            clean = im.lstrip("/").split("?")[0].split("#")[0]
            all_img_refs.add(clean)
            if not os.path.exists(clean):
                errors["broken_local_image"].append(f"{p}: {im}")

        for im in re.findall(r"^\s*path:\s*(/assets/\S+)", fm, re.M):
            clean = im.lstrip("/").split("?")[0].split("#")[0]
            all_img_refs.add(clean)
            if not os.path.exists(clean):
                errors["broken_fm_image"].append(f"{p}: {im}")

        for im in re.findall(r'<img[^>]+src=["\'](/assets/[^"\']+)["\']', body):
            clean = im.lstrip("/").split("?")[0].split("#")[0]
            all_img_refs.add(clean)
            if not os.path.exists(clean):
                errors["broken_html_image"].append(f"{p}: {im}")

        # External hotlinks outside code blocks
        for dom in HOTLINK_DOMAINS:
            if dom in (fm + "\n" + prose):
                warnings["external_hotlink_image"].append(f"{p} ({dom})")

        # 6. Internal /posts/... and /en/posts/... links
        for full, prefix, slug in re.findall(
            r"\]\((/(en/)?posts/([^)#\s/]+)/?(?:#[^)\s]*)?)\)", prose
        ):
            target_lang = "en" if prefix == "en/" else "ko"
            if (
                slug not in valid_slugs[target_lang]
                and slug.lower() not in valid_slugs[target_lang]
            ):
                errors["broken_internal_post_link"].append(f"{p} -> {full}")

        # 7. Security: API keys / tokens
        if re.search(r"AIza[0-9A-Za-z\-_]{35}", content):
            errors["potential_google_api_key"].append(p)
        if re.search(r"sk-[0-9A-Za-z]{20,}", content):
            errors["potential_sk_key"].append(p)
        if re.search(r"ghp_[0-9A-Za-z]{36}", content):
            errors["potential_ghp_token"].append(p)

        # 8. Unescaped Liquid syntax in prose outside code blocks/inline code and {% raw %}...{% endraw %}
        #    (Fenced code blocks and inline code spans are automatically escaped by _plugins/code-raw-escape-hook.rb)
        body_no_raw = re.sub(
            r"\{%-?\s*raw\s*-?%\}.*?\{%-?\s*endraw\s*-?%\}",
            lambda m: "\n" * m.group(0).count("\n"),
            body,
            flags=re.DOTALL,
        )
        in_fence = False
        fence_char = ""
        fence_len = 0
        for line_no, line in enumerate(body_no_raw.splitlines(), 1):
            if not in_fence:
                fm_open = re.match(r"^(?:[ \t]*>[ \t]?)*[ \t]{0,3}(`{3,}|~{3,})([^\r\n]*)$", line)
                if fm_open and (fm_open.group(1)[0] == "~" or "`" not in fm_open.group(2)):
                    in_fence = True
                    fence_char = fm_open.group(1)[0]
                    fence_len = len(fm_open.group(1))
                    continue
                if re.match(r"^>\s*\[!(?:NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]", line):
                    errors["github_alert_syntax"].append(
                        f"{p} (본문 {line_no}행): {line.strip()[:80]}"
                    )
                pm = re.match(r"^\{:\s*\.prompt-([a-z-]+)\s*\}\s*$", line)
                if pm and pm.group(1) not in ("tip", "info", "warning", "danger"):
                    errors["invalid_chirpy_prompt"].append(
                        f"{p} (본문 {line_no}행): .prompt-{pm.group(1)}"
                    )
                prose_line = re.sub(r"(`+)(?!`).+?(?<!`)\1(?!`)", "", line)
                if "{{" in prose_line:
                    errors["unescaped_liquid_expression"].append(
                        f"{p} (본문 {line_no}행): {line.strip()[:80]}"
                    )
            else:
                stripped = re.sub(r"^(?:[ \t]*>[ \t]?)*", "", line)
                if re.match(rf"^[ \t]{{0,3}}{re.escape(fence_char)}{{{fence_len},}}[ \t]*$", stripped):
                    in_fence = False
                    fence_char = ""
                    fence_len = 0

    # Pass 3: cross-post checks (alt_url reciprocity, subcategory & tag slugs)
    for src_route, target_route in sorted(declared_alt_urls.items()):
        if target_route in route_to_post:
            reverse = declared_alt_urls.get(target_route)
            if reverse != src_route:
                errors["non_reciprocal_alt_url"].append(
                    f"{src_route} -> {target_route} (역참조: {reverse or '없음'})"
                )

    for lang in ("ko", "en"):
        cat_prefix = "/en" if lang == "en" else ""
        for slug, paths in sorted(subcat_parents[lang].items()):
            if len(paths) > 1:
                errors["duplicate_subcategory_name"].append(
                    f"{cat_prefix}/categories/{slug}/ -> {', '.join(sorted(paths))}"
                )

    for slug, variants in sorted(tag_slug_variants.items()):
        if len(variants) > 1:
            detail = ", ".join(
                f"{var}({len(files)}건)" for var, files in sorted(variants.items())
            )
            errors["duplicate_tag_slug"].append(f"/tags/{slug}/ -> {detail}")

    # Check drafts + tabs + configs for image references so draft/tab images aren't flagged as orphan
    extra_refs = set()
    for pat in [
        "_drafts/**/*.md",
        "en/_drafts/**/*.md",
        "_tabs/*.md",
        "en/_tabs/*.md",
        "_config.yml",
        "_config_en.yml",
        "_includes/*.html",
        "_data/**/*",
    ]:
        for ef in glob.glob(pat, recursive=True):
            if os.path.isfile(ef):
                txt = open(ef, encoding="utf-8", errors="ignore").read()
                for im in re.findall(r"assets/images/[^\s\"'\)]+", txt):
                    extra_refs.add(im.split("?")[0].split("#")[0])

    # Orphan and large (>1MB) images
    if os.path.isdir("assets/images"):
        for root, _, files in os.walk("assets/images"):
            for fn in files:
                if fn == ".DS_Store":
                    continue
                fp = os.path.join(root, fn).replace("\\", "/")
                if fp not in all_img_refs and fp not in extra_refs:
                    warnings["orphan_image"].append(fp)
                sz = os.path.getsize(fp)
                if sz > 1024 * 1024:
                    warnings["large_image_over_1mb"].append(
                        f"{fp} ({sz / 1024 / 1024:.2f} MB)"
                    )

    # Config checks
    for cfg in ("_config.yml", "_config_en.yml"):
        if os.path.isfile(cfg):
            if "AGENTS.md" not in open(cfg, encoding="utf-8").read():
                errors["config_missing_agents_exclude"].append(cfg)

    ko_count = len(posts_by_lang["ko"])
    en_count = len(posts_by_lang["en"])
    print(
        f"=== 남주의 커밋로그 QA 결과 (공개 포스트 KO {ko_count}편 / EN {en_count}편 / 초안 {len(drafts)}편) ==="
    )
    if errors:
        print(f"\n[ERRORS: {sum(len(v) for v in errors.values())}건]")
        for k, items in sorted(errors.items()):
            print(f"  - {k} ({len(items)}건):")
            for it in items[:10]:
                print(f"      * {it}")
    else:
        print("\n[ERRORS: 0건] 치명적 오류 없음")

    if warnings:
        print(f"\n[WARNINGS: {sum(len(v) for v in warnings.values())}건]")
        for k, items in sorted(warnings.items()):
            print(f"  - {k} ({len(items)}건):")
            for it in items[:10]:
                print(f"      * {it}")
    else:
        print("[WARNINGS: 0건] 경고 없음")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
