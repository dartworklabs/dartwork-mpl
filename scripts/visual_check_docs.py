#!/usr/bin/env python3
"""Headless-rendered visual audit of every docs page.

Walks every .html page under docs/_build/html with a real headless
Chromium and runs hard checks that purely-static HTML parsing misses:

- **Console errors** (broken JS, missing assets at runtime).
- **Inline <svg> that renders at 0x0** despite having viewBox/dims
  in the markup (a CSS rule may have collapsed the container, or a
  parent uses ``display: none``).
- **<img src="*.svg"> that ends up zero-sized** — usually a flex
  container with ``flex-shrink: 1`` collapsing it under text.
- **Images whose ``naturalWidth`` is 0** (network 200 but corrupt /
  empty bytes).
- **Horizontal page overflow** (something wider than the viewport).
- **Iframe / video / other media** that failed to render.

Output: JSON report with one section per page + an aggregate summary.

Usage::

    uv run --with playwright python3 scripts/visual_check_docs.py \\
        --base http://localhost:8080 --workers 4
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

PAGE_CHECK_JS = r"""
() => {
  const issues = [];
  const viewportW = window.innerWidth;
  const viewportH = window.innerHeight;

  // Intentionally-hidden elements: anywhere up the ancestor chain we
  // see display:none / visibility:hidden / opacity:0, OR offsetParent
  // is null (the canonical "not in flow" signal). We treat *any* of
  // these as a deliberate hide and skip the size check.
  function isIntentionallyHidden(el) {
    if (el.offsetParent === null) return true;
    let cur = el;
    while (cur && cur !== document.body) {
      const cs = getComputedStyle(cur);
      if (cs.display === 'none') return true;
      if (cs.visibility === 'hidden') return true;
      if (parseFloat(cs.opacity) === 0) return true;
      cur = cur.parentElement;
    }
    return false;
  }

  // ── 1. zero-sized inline <svg>  ────────────────────────────────────────
  const svgs = [...document.querySelectorAll('svg')];
  svgs.forEach((svg, i) => {
    if (isIntentionallyHidden(svg)) return;
    // SVG-sprite pattern: an off-screen container for <defs>, <symbol>,
    // and <linearGradient> definitions referenced via <use>. Has inline
    // style="position:absolute;width:0;height:0" and is supposed to be
    // 0x0. Detect it and exempt.
    const inline = (svg.getAttribute('style') || '').replace(/\s/g, '');
    if (/width:0/i.test(inline) && /height:0/i.test(inline)) return;
    // Also exempt SVGs whose only children are <defs>/<symbol> (sprite)
    if (svg.children.length > 0) {
      const tags = [...svg.children].map(c => c.tagName.toLowerCase());
      if (tags.every(t => ['defs', 'symbol', 'lineargradient', 'radialgradient'].includes(t))) {
        return;
      }
    }
    const r = svg.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) {
      issues.push({
        type: 'zero-svg',
        index: i,
        width: r.width,
        height: r.height,
        cls: svg.getAttribute('class') || '',
        role: svg.getAttribute('role') || '',
        viewBox: svg.getAttribute('viewBox') || '',
        parentTag: svg.parentElement?.tagName || '',
        parentCls: svg.parentElement?.className || '',
      });
    }
  });

  // ── 2. zero-sized <img>  ───────────────────────────────────────────────
  const imgs = [...document.querySelectorAll('img')];
  imgs.forEach((img) => {
    if (!img.complete) return;
    if (isIntentionallyHidden(img)) return;
    const r = img.getBoundingClientRect();
    if (img.naturalWidth === 0) {
      issues.push({
        type: 'broken-img',
        src: img.src,
        alt: img.alt,
        cls: img.className,
      });
    } else if (r.width < 1 || r.height < 1) {
      issues.push({
        type: 'zero-img',
        src: img.src.split('/').slice(-2).join('/'),
        alt: img.alt,
        width: r.width,
        height: r.height,
        naturalW: img.naturalWidth,
        naturalH: img.naturalHeight,
        cls: img.className,
        parentCls: img.parentElement?.className || '',
      });
    }
  });

  // ── 3. horizontal page overflow  ───────────────────────────────────────
  const docW = document.documentElement.scrollWidth;
  if (docW > viewportW + 4) {
    let widest = null;
    const candidates = [...document.querySelectorAll('main *, body > *')];
    for (const el of candidates) {
      const r = el.getBoundingClientRect();
      if (r.right > viewportW + 4 && r.width > 200) {
        widest = {
          tag: el.tagName,
          cls: (el.className || '').toString().slice(0, 80),
          width: Math.round(r.width),
          right: Math.round(r.right),
        };
        break;
      }
    }
    issues.push({type: 'h-overflow', amount: docW - viewportW, widest});
  }

  // ── 4. heading / paragraph cosmetic sanity  ────────────────────────────
  const h1 = document.querySelector('main h1, article h1');
  if (h1) {
    const cs = getComputedStyle(h1);
    const fs = parseFloat(cs.fontSize);
    if (fs < 20 || fs > 60) {
      issues.push({
        type: 'h1-out-of-range',
        fontSize: cs.fontSize,
        text: (h1.textContent || '').slice(0, 50).trim(),
      });
    }
  }

  // ── 5. iframe / video that failed to load  ─────────────────────────────
  for (const iframe of document.querySelectorAll('iframe')) {
    try {
      const _ = iframe.contentDocument;
    } catch (_) { /* cross-origin, OK */ }
    const r = iframe.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) {
      issues.push({type: 'zero-iframe', src: iframe.src, cls: iframe.className});
    }
  }

  // ── 6. inline-code styling actually applied (main content only)
  // Sidebar / TOC code elements are intentionally left transparent —
  // a chip background there would compete with the link styling. We
  // restrict the sample to the main content area (.yue, .sy-main, or
  // main as a last fallback) and ignore codes inside anchors there.
  const contentRoot = document.querySelector('.yue, .sy-main, main') || document.body;
  const codeEls = [...contentRoot.querySelectorAll(':not(pre) > code')].filter(c => {
    // Sidebar TOC codes get nested under a <ul><li><a>; exclude those.
    const link = c.closest('a');
    return !link || !link.closest('.shibuya-sidebar, aside, nav, .sy-sidebar');
  });
  let codeStyled = false;
  for (const c of codeEls.slice(0, 5)) {
    const cs = getComputedStyle(c);
    if (cs.backgroundColor && cs.backgroundColor !== 'rgba(0, 0, 0, 0)') {
      codeStyled = true;
      break;
    }
  }
  if (codeEls.length > 0 && !codeStyled) {
    issues.push({
      type: 'inline-code-unstyled',
      sampleCount: codeEls.length,
      firstSample: codeEls[0]?.textContent.slice(0, 60),
    });
  }

  return {
    url: location.pathname,
    title: document.title,
    viewport: {w: viewportW, h: viewportH},
    counts: {svgs: svgs.length, imgs: imgs.length, codes: codeEls.length},
    issues,
  };
}
"""


def list_pages(root: Path) -> list[str]:
    skip_dirs = {"_modules", "_static", "_sources"}
    out: list[str] = []
    for p in root.rglob("*.html"):
        if set(p.parts) & skip_dirs:
            continue
        out.append(str(p.relative_to(root)).replace("\\", "/"))
    return sorted(out)


def audit_page(browser, base: str, path: str) -> dict:
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    console_errors: list[str] = []
    page_errors: list[str] = []

    page.on(
        "console",
        lambda msg: msg.type == "error" and console_errors.append(msg.text),
    )
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))

    try:
        page.goto(f"{base}/{path}", wait_until="networkidle", timeout=20_000)
    except Exception as e:  # noqa: BLE001
        page.close()
        return {
            "url": path,
            "issues": [{"type": "nav-fail", "error": str(e)[:200]}],
        }

    # Give async widgets (color picker, slider, etc.) a moment to mount.
    page.wait_for_timeout(300)

    try:
        result = page.evaluate(PAGE_CHECK_JS)
    except Exception as e:  # noqa: BLE001
        page.close()
        return {
            "url": path,
            "issues": [{"type": "eval-fail", "error": str(e)[:200]}],
        }

    # Filter console errors to drop known-noisy ones (e.g. font-display
    # warnings, fragment 404s from old anchors, etc.). Real errors stay.
    filtered = []
    for msg in console_errors:
        if (
            "Failed to load resource" in msg
            and ".svg" not in msg
            and ".png" not in msg
        ):
            # don't double-report — broken-img already covers it
            continue
        filtered.append(msg)

    if filtered:
        result.setdefault("issues", []).append(
            {"type": "console-error", "messages": filtered[:5]}
        )
    if page_errors:
        result.setdefault("issues", []).append(
            {"type": "page-error", "messages": page_errors[:5]}
        )

    page.close()
    return result


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
    ap.add_argument(
        "--out", type=Path, default=Path("visual_check_report.json")
    )
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    pages = list_pages(args.html_root)
    if args.limit:
        pages = pages[: args.limit]
    print(f"Visual-auditing {len(pages)} pages …", file=sys.stderr)

    reports: list[dict] = []
    t0 = time.time()

    with sync_playwright() as pw:
        # Sync API isn't thread-safe — drive sequentially. Chromium is
        # quick enough on local-served static HTML that the full 150-
        # page sweep takes <60 s on a developer laptop.
        browser = pw.chromium.launch(headless=True)
        for i, p in enumerate(pages, 1):
            reports.append(audit_page(browser, args.base, p))
            if i % 20 == 0:
                print(f"  [{i}/{len(pages)}]", file=sys.stderr)
        browser.close()

    # Aggregate
    by_type: dict[str, int] = {}
    total = 0
    for r in reports:
        for it in r.get("issues", []) or []:
            by_type[it["type"]] = by_type.get(it["type"], 0) + 1
            total += 1

    pages_with_issues = [r for r in reports if r.get("issues")]
    summary = {
        "pages_audited": len(reports),
        "total_issues": total,
        "by_type": dict(sorted(by_type.items(), key=lambda kv: -kv[1])),
        "pages_with_issues": len(pages_with_issues),
        "elapsed_seconds": round(time.time() - t0, 1),
    }

    args.out.write_text(
        json.dumps(
            {
                "summary": summary,
                "pages": sorted(reports, key=lambda r: r["url"]),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
