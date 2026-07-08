#!/usr/bin/env python3
"""Brute-force docs audit — every page, every image, every SVG.

Walks docs/_build/html with HTTP fetches + HTML parsing, then runs a
hard-edged check for:

- broken <img src=...> targets (404 / wrong content-type)
- broken/zero-sized <img src="*.svg">
- inline <svg> blocks with no width AND no viewBox (will collapse)
- broken <link> stylesheets / <script> assets
- broken in-page anchor links (#foo where #foo does not exist)
- pages with stray markdown (e.g. `**text**` that bled past Sphinx)
- the dartwork-design.css overlay actually loads on every page

Runs against a local Sphinx server (default http://localhost:8080).
Outputs a JSON report. Exit 0 = clean, exit 1 = issues found.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, urljoin

# ---------------------------------------------------------------------------
# HTML parsing — pull out the asset URLs and structural anchors we audit.
# ---------------------------------------------------------------------------


class PageParser(HTMLParser):
    """Collects <img>, <svg>, <link>, <a>, and a few inline-style flags."""

    def __init__(self) -> None:
        super().__init__()
        self.imgs: list[dict] = []
        self.svgs: list[dict] = []
        self.links: list[dict] = []
        self.anchors: list[str] = []  # href targets ("#foo" or full URLs)
        self.ids: set[str] = set()  # id="" attributes seen on the page
        self.stylesheets: list[str] = []
        self.scripts: list[str] = []
        self.svg_depth = 0
        self._current_svg: dict | None = None

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "img":
            self.imgs.append(
                {
                    "src": a.get("src", ""),
                    "alt": a.get("alt", "") or "",
                    "width": a.get("width", ""),
                    "height": a.get("height", ""),
                    "style": a.get("style", "") or "",
                }
            )
        elif tag == "svg":
            self.svg_depth += 1
            if self.svg_depth == 1:
                # Only audit top-level <svg>; nested ones are decorative.
                self._current_svg = {
                    "width": a.get("width", ""),
                    "height": a.get("height", ""),
                    "viewBox": a.get("viewbox", "") or a.get("viewBox", ""),
                    "role": a.get("role", "") or "",
                    "aria_label": a.get("aria-label", "") or "",
                    "style": a.get("style", "") or "",
                    "class": a.get("class", "") or "",
                }
                self.svgs.append(self._current_svg)
        elif tag == "link":
            rel = (a.get("rel") or "").lower()
            if "stylesheet" in rel and a.get("href"):
                self.stylesheets.append(a["href"])
        elif tag == "script" and a.get("src"):
            self.scripts.append(a["src"])
        elif tag == "a" and a.get("href"):
            self.anchors.append(a["href"])

    def handle_endtag(self, tag: str) -> None:
        if tag == "svg":
            self.svg_depth = max(0, self.svg_depth - 1)
            if self.svg_depth == 0:
                self._current_svg = None


def parse_page(html: str) -> PageParser:
    p = PageParser()
    p.feed(html)
    return p


# ---------------------------------------------------------------------------
# HTTP helpers.
# ---------------------------------------------------------------------------


def fetch(url: str, *, timeout: float = 8.0) -> tuple[int, bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "brute-check/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            ctype = r.headers.get("Content-Type", "")
            return r.status, body, ctype
    except urllib.error.HTTPError as e:
        return e.code, b"", ""
    except (urllib.error.URLError, TimeoutError) as e:
        return 0, b"", str(e)


def head(url: str, *, timeout: float = 6.0) -> tuple[int, int, str]:
    """HEAD request → (status, content-length, content-type)."""
    req = urllib.request.Request(
        url, method="HEAD", headers={"User-Agent": "brute-check/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            length = int(r.headers.get("Content-Length", "0") or 0)
            ctype = r.headers.get("Content-Type", "")
            return r.status, length, ctype
    except urllib.error.HTTPError as e:
        return e.code, 0, ""
    except (urllib.error.URLError, TimeoutError):
        return 0, 0, ""


# ---------------------------------------------------------------------------
# Per-page audit.
# ---------------------------------------------------------------------------

ASSET_CACHE: dict[str, tuple[int, int, str]] = {}


def head_cached(url: str) -> tuple[int, int, str]:
    if url not in ASSET_CACHE:
        ASSET_CACHE[url] = head(url)
    return ASSET_CACHE[url]


def audit_page(base: str, rel_url: str) -> dict:
    page_url = urljoin(base + "/", rel_url)
    status, body, _ctype = fetch(page_url)
    issues: list[dict] = []
    if status != 200:
        return {
            "url": rel_url,
            "page_status": status,
            "issues": [
                {"type": "page-fetch-fail", "status": status, "url": page_url}
            ],
        }

    html = body.decode("utf-8", errors="replace")
    p = parse_page(html)

    # ── 1. stylesheets — confirm the design overlay is present + links 200.
    # The overlay was renamed radix-design.css -> dartwork-design.css when
    # the docs dropped Radix; checking the old name flagged every page.
    has_design_css = any("dartwork-design.css" in s for s in p.stylesheets)
    if not has_design_css:
        issues.append(
            {"type": "missing-design-css", "stylesheets": p.stylesheets}
        )

    for href in p.stylesheets + p.scripts:
        if href.startswith(("data:", "javascript:", "mailto:")):
            continue
        full = urljoin(page_url, href)
        if not full.startswith(base):
            continue  # skip external CDN (google fonts, etc.)
        st, _, _ = head_cached(full)
        if st >= 400 or st == 0:
            issues.append({"type": "asset-404", "href": href, "status": st})

    # ── 2. <img> targets — every src must 200; SVG-typed ones must be SVG
    for img in p.imgs:
        src = img["src"]
        if not src or src.startswith("data:"):
            continue
        full = urljoin(page_url, src)
        if not full.startswith(base):
            continue
        st, length, type_ = head_cached(full)
        if st >= 400 or st == 0:
            issues.append(
                {"type": "img-404", "src": src, "status": st, "alt": img["alt"]}
            )
            continue
        if length == 0:
            issues.append(
                {
                    "type": "img-zero-bytes",
                    "src": src,
                    "alt": img["alt"],
                    "ctype": type_,
                }
            )
        if src.endswith(".svg") and "svg" not in type_.lower():
            issues.append(
                {
                    "type": "svg-wrong-ctype",
                    "src": src,
                    "ctype": type_,
                    "alt": img["alt"],
                }
            )

    # ── 3. inline <svg> — viewBox OR explicit width+height required
    for i, svg in enumerate(p.svgs):
        has_viewbox = bool(svg["viewBox"].strip())
        has_dims = bool(svg["width"].strip()) and bool(svg["height"].strip())
        # CSS-sized via style attribute counts too
        style_sized = bool(re.search(r"\bwidth\s*:", svg["style"])) or bool(
            re.search(r"\bheight\s*:", svg["style"])
        )
        # SVGs inside icon classes ("eva-…", "octicon", "feather", "lucide")
        # are typically CSS-sized via container — skip those.
        css_managed = any(
            tok in svg["class"]
            for tok in ("icon", "octicon", "feather", "lucide", "eva-", "rx-")
        )
        if not (has_viewbox or has_dims or style_sized or css_managed):
            issues.append(
                {
                    "type": "svg-undimensioned",
                    "index": i,
                    "class": svg["class"][:80],
                    "role": svg["role"],
                }
            )

    # ── 4. in-page anchor links resolve to a real id on the page
    for href in p.anchors:
        if not href.startswith("#"):
            continue
        if href == "#":
            continue
        _, frag = urldefrag(href)
        if frag and frag not in p.ids:
            # Skip ones that match a heading-id pattern we can't see
            # (Sphinx adds anchors via JS sometimes). Best-effort flag.
            issues.append({"type": "dangling-anchor", "href": href})

    # ── 5. Stray markdown that didn't get processed
    for pattern in (
        r"\*\*[^*\n]{2,80}\*\*",  # **bold** outside code
        r"\[[^\]]{2,80}\]\([^)]+\)",  # [text](url)
    ):
        for m in re.finditer(pattern, html):
            # ignore if inside a <code>/<pre> block — quick heuristic
            window = html[max(0, m.start() - 80) : m.start()]
            if "<code" in window.lower() or "<pre" in window.lower():
                continue
            if "</code>" in window.lower() or "</pre>" in window.lower():
                # window saw a closing tag — text is *after* the block
                pass
            else:
                continue  # be conservative; only flag clear cases
            issues.append(
                {
                    "type": "stray-markdown",
                    "match": m.group(0)[:80],
                    "pos": m.start(),
                }
            )
            break  # one per pattern per page is enough

    return {
        "url": rel_url,
        "page_status": status,
        "counts": {
            "imgs": len(p.imgs),
            "svgs": len(p.svgs),
            "stylesheets": len(p.stylesheets),
            "scripts": len(p.scripts),
            "anchors": len(p.anchors),
            "ids": len(p.ids),
        },
        "issues": issues,
        "has_design_css": has_design_css,
    }


# ---------------------------------------------------------------------------
# Page enumeration.
# ---------------------------------------------------------------------------


def list_pages(root: Path) -> list[str]:
    # _downloads can contain standalone HTML fragments copied from static
    # assets. They are downloadable artifacts, not Sphinx pages with the docs
    # shell or dartwork-design.css link.
    skip_dirs = {"_downloads", "_modules", "_static", "_sources"}
    out: list[str] = []
    for p in root.rglob("*.html"):
        parts = set(p.parts)
        if parts & skip_dirs:
            continue
        out.append(str(p.relative_to(root)).replace("\\", "/"))
    return sorted(out)


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="http://localhost:8080")
    ap.add_argument(
        "--html-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent
        / "docs"
        / "_build"
        / "html",
    )
    ap.add_argument("--out", type=Path, default=Path("brute_check_report.json"))
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    pages = list_pages(args.html_root)
    if args.limit:
        pages = pages[: args.limit]
    print(f"Auditing {len(pages)} pages from {args.base} …", file=sys.stderr)

    reports: list[dict] = []
    t0 = time.time()
    for i, page in enumerate(pages, 1):
        r = audit_page(args.base, page)
        reports.append(r)
        if i % 25 == 0:
            print(f"  [{i}/{len(pages)}] {page}", file=sys.stderr)

    issues_by_type: dict[str, int] = defaultdict(int)
    total = 0
    for r in reports:
        for it in r["issues"]:
            issues_by_type[it["type"]] += 1
            total += 1

    summary = {
        "base": args.base,
        "pages_audited": len(reports),
        "total_issues": total,
        "by_type": dict(sorted(issues_by_type.items(), key=lambda kv: -kv[1])),
        "elapsed_seconds": round(time.time() - t0, 1),
        "cache_hits": len(ASSET_CACHE),
    }

    args.out.write_text(
        json.dumps(
            {"summary": summary, "pages": reports}, indent=2, ensure_ascii=False
        )
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
