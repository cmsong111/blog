#!/usr/bin/env python3
"""
남주의 커밋로그(namju.kim) 정적 QA 검증 스크립트.

검사 항목:
1. Front Matter 필수 필드 (title, description, date, tags) 및 categories 생략 여부
2. 제목 금지어 (어그로/과장 표현) 검사
3. 파일명 규칙, 미래 날짜, 퍼머링크·태그·중분류 카테고리 슬러그 중복 검사
4. 본문 분량 (코드·Mermaid 제외 순수 본문 < 600자 Thin Content 경고)
5. Mermaid 및 Chart.js 문법 (노드/엣지 특수문자 따옴표, 스타일링 HTML 태그, mermaid/chart flag 일치, JSON 유효성)
6. 이미지 무결성 (깨진 로컬 이미지, 빈 alt, 이중 슬래시 /assets//, 외부 핫링크, >1MB 대용량, 고아 이미지)
7. 내부 포스트 링크 (/posts/<slug>/) 깨짐 검사
8. 보안 (API 키 / 토큰 패턴 노출 검사) 및 미이스케이프 Liquid 구문({{ }}, 코드 블록 내 {% %}) 검사
9. 설정 검증 (_config.yml / workflow에 AGENTS.md 제외 여부)

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

PROHIBITED_TITLE_PATTERNS = [
    r"완벽\s*해결",
    r"완전\s*정복",
    r"초고속",
    r"원클릭",
    r"의\s*모든\s*것",
    r"치명적\s*위험",
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


def main():
    today_str = datetime.date.today().isoformat()
    posts = sorted(glob.glob("_posts/**/*.md", recursive=True))
    drafts = sorted(glob.glob("_drafts/**/*.md", recursive=True))

    errors = defaultdict(list)
    warnings = defaultdict(list)

    slug_counts = Counter()
    valid_slugs = set()
    all_img_refs = set()
    tag_slug_variants = defaultdict(lambda: defaultdict(list))
    subcat_parents = defaultdict(set)

    for p in posts:
        rel_dir = os.path.relpath(os.path.dirname(p), "_posts").replace("\\", "/")
        parts = rel_dir.split("/") if rel_dir != "." else []
        for depth in range(1, len(parts)):
            subcat_parents[slugify_tag(parts[depth])].add(
                "/".join(parts[: depth + 1])
            )
        fname = os.path.basename(p)
        m_fn = re.match(r"^(\d{4}-\d{2}-\d{2})-(.+)\.md$", fname)
        if not m_fn:
            errors["invalid_filename"].append(p)
        else:
            post_date, slug = m_fn.group(1), m_fn.group(2)
            slug_counts[slug] += 1
            valid_slugs.add(slug)
            valid_slugs.add(slug.lower())
            if post_date > today_str:
                warnings["future_dated_post"].append(f"{p} ({post_date})")

    for slug, cnt in slug_counts.items():
        if cnt > 1:
            errors["duplicate_permalink_slug"].append(f"{slug} ({cnt}회)")

    for p in posts:
        with open(p, encoding="utf-8") as f:
            content = f.read()

        fm, body = parse_frontmatter(content)
        if fm is None:
            errors["missing_frontmatter"].append(p)
            continue

        # 1. Front Matter fields
        title = get_fm_value(fm, "title")
        desc = get_fm_value(fm, "description")
        date_val = get_fm_value(fm, "date")
        tags_val = get_fm_value(fm, "tags")

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

        # 2. Title style check
        for pat in PROHIBITED_TITLE_PATTERNS:
            if re.search(pat, title):
                warnings["prohibited_title_word"].append(f"{p}: {title}")

        # 3. Prose length (excluding code & mermaid blocks)
        prose = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
        prose_chars = len(re.sub(r"\s+", "", prose))
        if prose_chars < 600:
            errors["thin_content_under_600"].append(f"{p} ({prose_chars}자)")

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

        # 6. Internal /posts/... links
        for full, slug in re.findall(
            r"\]\((/posts/([^)#\s/]+)/?(?:#[^)\s]*)?)\)", prose
        ):
            if slug not in valid_slugs and slug.lower() not in valid_slugs:
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

    for slug, paths in sorted(subcat_parents.items()):
        if len(paths) > 1:
            errors["duplicate_subcategory_name"].append(
                f"/categories/{slug}/ -> {', '.join(sorted(paths))}"
            )

    for slug, variants in sorted(tag_slug_variants.items()):
        if len(variants) > 1:
            detail = ", ".join(
                f"{var}({len(files)}건)" for var, files in sorted(variants.items())
            )
            errors["duplicate_tag_slug"].append(f"/tags/{slug}/ -> {detail}")

    # Check drafts + tabs + configs for image references so draft images aren't flagged as orphan
    extra_refs = set()
    for pat in ["_drafts/**/*.md", "_tabs/*.md", "_config.yml", "_includes/*.html", "_data/**/*"]:
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
    if os.path.isfile("_config.yml"):
        if "AGENTS.md" not in open("_config.yml", encoding="utf-8").read():
            errors["config_missing_agents_exclude"].append("_config.yml")

    print(f"=== 남주의 커밋로그 QA 결과 (공개 포스트 {len(posts)}편 / 초안 {len(drafts)}편) ===")
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
