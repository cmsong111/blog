"""Validate both language builds after assembling the Pages artifact."""

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from xml.etree import ElementTree


ORIGIN = "https://namju.kim"
CORE_ROUTES = ("/", "/about/", "/archives/", "/categories/", "/tags/")
SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


class Page(HTMLParser):
    def __init__(self, file):
        super().__init__()
        self.in_head = False
        self.in_sidebar = False
        self.has_sidebar = False
        self.lang = ""
        self.locale = ""
        self.canonical = []
        self.alternates = []
        self.switch = []
        self.nav_links = set()
        self.scripts = set()
        self.noindex = False
        self.feed(file.read_text(encoding="utf-8"))
        self.close()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "html":
            self.lang = attrs.get("lang", "")
        elif tag == "head":
            self.in_head = True
        elif tag == "body":
            self.in_head = False
        elif tag == "aside" and attrs.get("id") == "sidebar":
            self.in_sidebar = True
            self.has_sidebar = True
        elif tag == "link" and self.in_head:
            if attrs.get("rel") == "canonical":
                self.canonical.append(attrs.get("href"))
            elif attrs.get("rel") == "alternate" and "hreflang" in attrs:
                self.alternates.append((attrs["hreflang"], attrs.get("href")))
        elif tag == "meta" and self.in_head:
            if attrs.get("property") == "og:locale":
                self.locale = attrs.get("content", "")
            elif attrs.get("name") == "robots":
                self.noindex |= "noindex" in attrs.get("content", "").lower()
        elif tag == "a":
            if attrs.get("id") == "language-switcher":
                self.switch.append((attrs.get("hreflang"), attrs.get("href"), self.in_sidebar))
            if "nav-link" in attrs.get("class", "").split():
                self.nav_links.add(attrs.get("href"))
        elif tag == "script" and "src" in attrs:
            self.scripts.add(urlsplit(attrs["src"]).path)

    def handle_endtag(self, tag):
        if tag == "head":
            self.in_head = False
        elif tag == "aside":
            self.in_sidebar = False


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def route_for(file, root):
    route = "/" + file.relative_to(root).as_posix()
    if file.name == "index.html":
        route = route.removesuffix("index.html")
    return quote(route)


def check_site(root):
    pages = {route_for(file, root): Page(file) for file in root.rglob("*.html")}
    for route in CORE_ROUTES:
        english_route = "/en" + route
        alternates = {"ko": ORIGIN + route, "en": ORIGIN + english_route,
                      "x-default": ORIGIN + route}
        for path in (route, english_route):
            require(path in pages, f"Missing page: {path}")
            require(dict(pages[path].alternates) == alternates, f"Wrong language pair: {path}")

    for route, page in pages.items():
        if not (page.has_sidebar or page.switch or page.alternates):
            continue

        english = route.startswith("/en/")
        lang, other_lang = ("en", "ko") if english else ("ko", "en")
        require(page.lang == lang, f"Wrong HTML language: {route}")
        if english:
            require(page.locale == "en_US", f"Wrong Open Graph locale: {route}")
            require("/en/app.min.js" not in page.scripts, f"Unexpected English PWA app: {route}")

        target = "/" if english else "/en/"
        if page.alternates:
            alternates = dict(page.alternates)
            require(len(page.alternates) == 3 and alternates.keys() == {"ko", "en", "x-default"}
                    and alternates["x-default"] == alternates["ko"],
                    f"Invalid hreflang set: {route}")
            require(page.canonical == [ORIGIN + route] and alternates[lang] == ORIGIN + route
                    and not page.noindex, f"Invalid canonical or indexability: {route}")
            other_url = alternates[other_lang] or ""
            target = other_url.removeprefix(ORIGIN)
            other_page = pages.get(target)
            require(other_url == ORIGIN + target and other_page and other_page.lang == other_lang
                    and dict(other_page.alternates) == alternates,
                    f"Missing or non-reciprocal hreflang target: {route} -> {other_url}")
        require(page.switch == [(other_lang, target, True)] and target in pages,
                f"Invalid sidebar language switch: {route} -> {target}")

    for prefix in ("", "/en"):
        require({prefix + path for path in CORE_ROUTES[1:]} <= pages[prefix + "/"].nav_links,
                f"Missing sidebar tab links: {prefix or '/'}")
        sitemap = root / prefix.lstrip("/") / "sitemap.xml"
        require(sitemap.is_file(), f"Missing sitemap: {sitemap}")
        locations = {node.text for node in ElementTree.parse(sitemap).iter(SITEMAP_NS + "loc")}
        require({ORIGIN + prefix + path for path in CORE_ROUTES} <= locations,
                f"Missing home or tab in sitemap: {sitemap}")
        for url in locations:
            route = (url or "").removeprefix(ORIGIN)
            require(route.startswith("/") and url == ORIGIN + route
                    and route.startswith("/en/") == (prefix == "/en"),
                    f"URL outside sitemap language scope: {url}")
            require(route not in pages or not pages[route].noindex,
                    f"Noindex page listed in sitemap: {url}")

    robots = (root / "robots.txt").read_text(encoding="utf-8").splitlines()
    require({f"Sitemap: {ORIGIN}/sitemap.xml", f"Sitemap: {ORIGIN}/en/sitemap.xml"} <= set(robots),
            "Root robots.txt must list both sitemaps")

    en = root / "en"
    for relative in ("ads.txt", "robots.txt", "assets/images", "plan.html", "AGENTS.html", "tools"):
        require(not (en / relative).exists(), f"Unexpected English artifact: {relative}")
    for relative in ("assets/css/jekyll-theme-chirpy.css", "assets/js/dist/theme.min.js", "feed.xml"):
        require((en / relative).is_file(), f"Missing English asset: {relative}")
    search = json.loads((en / "assets/js/data/search.json").read_text(encoding="utf-8"))
    for post in search:
        require(post["url"].startswith("/en/posts/") and quote(unquote(post["url"])) in pages,
                f"Invalid English search result: {post['url']}")

    swconf = (root / "assets/js/data/swconf.js").read_text(encoding="utf-8")
    deny_paths = re.search(r"\bpaths:\s*\[([^\]]*)\]", swconf)
    require(deny_paths and re.search(r"""['"]/en['"]""", deny_paths[1]),
            "Missing /en in the root service worker cache exclusions")
    print(f"Multilingual checks passed for {len(pages)} HTML files")


if __name__ == "__main__":
    check_site(Path(sys.argv[1]))
