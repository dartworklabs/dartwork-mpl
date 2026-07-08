#!/usr/bin/env python3
"""Targeted docs layout regression checks.

This complements ``visual_check_docs.py`` with page-specific geometry checks for
the docs width contract:

- gallery thumbnail media slots keep a stable visual ratio
- article-local wide blocks do not break out into the right page TOC
- no horizontal overflow, excluding Shibuya offcanvas/sidebar surfaces
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

CHECKS: list[dict[str, Any]] = [
    {
        "path": "examples_gallery/index.html",
        "viewports": [
            {"width": 390, "height": 844},
            {"width": 1024, "height": 900},
            {"width": 1440, "height": 1000},
            {"width": 1680, "height": 1050},
        ],
        "gallery": True,
    },
    {
        "path": "color_system/categorical-palettes.html",
        "viewports": [
            {"width": 390, "height": 844},
            {"width": 1440, "height": 1000},
            {"width": 1680, "height": 1050},
        ],
        "wide": True,
    },
]

LAYOUT_CHECK_JS = r"""
(opts) => {
  const issues = [];
  const viewportW = window.innerWidth;
  const collapsed = (el) => {
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return (
      cs.display === 'none' ||
      cs.visibility === 'hidden' ||
      r.width < 1 ||
      r.height < 1
    );
  };
  const visibleInViewport = (el) => {
    if (collapsed(el)) return false;
    const r = el.getBoundingClientRect();
    return r.right > 0 && r.left < viewportW && r.bottom > 0 && r.top < window.innerHeight;
  };

  const ignoredOverflowSelectors = [
    '.sy-offcanvas',
    '.shibuya-offcanvas',
    '.shibuya-drawer',
    '.shibuya-sidebar',
    '.sy-lside',
    '.sy-rside',
    '.sy-sidebar',
    '[aria-modal="true"]',
  ];
  const ignoredOverflow = (el) =>
    ignoredOverflowSelectors.some((sel) => el.closest(sel));

  const docW = document.documentElement.scrollWidth;
  if (docW > viewportW + 4) {
    const overflowCandidates = [...document.querySelectorAll('body *')];
    const overflowOffenders = [];
    for (const el of overflowCandidates) {
      if (ignoredOverflow(el) || collapsed(el)) continue;
      const r = el.getBoundingClientRect();
      if (r.right > viewportW + 4 || r.left < -4) {
        overflowOffenders.push({
          tag: el.tagName,
          cls: (el.className || '').toString().slice(0, 100),
          left: Math.round(r.left),
          right: Math.round(r.right),
          width: Math.round(r.width),
        });
        if (overflowOffenders.length >= 5) break;
      }
    }
    if (overflowOffenders.length > 0) {
      issues.push({
        type: 'h-overflow',
        scrollWidth: docW,
        offenders: overflowOffenders,
      });
    }
  }

  const toc = [...document.querySelectorAll('.sy-rside, .sy-right-toc')]
    .find((el) => visibleInViewport(el));
  if (toc) {
    const tocRect = toc.getBoundingClientRect();
    const overlapTargets = [
      ...document.querySelectorAll('article.yue, .dm-wide'),
    ].filter((el) => !collapsed(el));
    for (const target of overlapTargets) {
      const r = target.getBoundingClientRect();
      if (r.right > tocRect.left - 1) {
        issues.push({
          type: 'toc-overlap',
          selector: target.matches('.dm-wide') ? '.dm-wide' : 'article.yue',
          right: Math.round(r.right),
          tocLeft: Math.round(tocRect.left),
          gap: Math.round(tocRect.left - r.right),
        });
      }
    }
  }

  if (opts.gallery) {
    const cards = [...document.querySelectorAll('.sphx-glr-thumbcontainer')]
      .filter((card) => !collapsed(card))
      .slice(0, 12);
    if (cards.length === 0) {
      issues.push({type: 'gallery-missing-cards'});
    }
    for (const card of cards) {
      const img = card.querySelector('img');
      if (!img || collapsed(img)) {
        issues.push({type: 'gallery-missing-image'});
        continue;
      }
      const cardR = card.getBoundingClientRect();
      const imgR = img.getBoundingClientRect();
      const ratio = imgR.width / imgR.height;
      if (ratio < 1.45 || ratio > 1.9) {
        issues.push({
          type: 'gallery-image-ratio',
          ratio: Number(ratio.toFixed(3)),
          width: Math.round(imgR.width),
          height: Math.round(imgR.height),
        });
      }
      if (
        imgR.left < cardR.left - 1 ||
        imgR.right > cardR.right + 1 ||
        imgR.width < 80 ||
        imgR.height < 80
      ) {
        issues.push({
          type: 'gallery-image-slot',
          cardWidth: Math.round(cardR.width),
          imageWidth: Math.round(imgR.width),
          imageHeight: Math.round(imgR.height),
        });
      }
    }
  }

  if (opts.wide) {
    const article = document.querySelector('article.yue');
    const wide = document.querySelector('.dm-wide');
    if (!wide) {
      issues.push({type: 'wide-missing'});
    } else if (article) {
      const articleR = article.getBoundingClientRect();
      const wideR = wide.getBoundingClientRect();
      if (wideR.right > articleR.right + 1 || wideR.left < articleR.left - 1) {
        issues.push({
          type: 'wide-breakout',
          articleLeft: Math.round(articleR.left),
          articleRight: Math.round(articleR.right),
          wideLeft: Math.round(wideR.left),
          wideRight: Math.round(wideR.right),
        });
      }
    }
  }

  return {
    url: location.pathname,
    viewport: {w: viewportW, h: window.innerHeight},
    issues,
  };
}
"""


def run_check(
    browser: Any, base: str, check: dict[str, Any], viewport: dict[str, int]
) -> dict[str, Any]:
    page = browser.new_page(viewport=viewport)
    path = check["path"]
    result: dict[str, Any]
    try:
        page.goto(
            f"{base.rstrip('/')}/{path}",
            wait_until="networkidle",
            timeout=20_000,
        )
        page.wait_for_timeout(300)
        result = page.evaluate(
            LAYOUT_CHECK_JS,
            {
                "gallery": bool(check.get("gallery")),
                "wide": bool(check.get("wide")),
            },
        )
    except Exception as exc:  # noqa: BLE001
        result = {
            "url": path,
            "viewport": viewport,
            "issues": [{"type": "nav-or-eval-fail", "error": str(exc)[:240]}],
        }
    finally:
        page.close()

    result["path"] = path
    result["viewport"] = viewport
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://localhost:8320")
    parser.add_argument(
        "--out", type=Path, default=Path("docs_layout_check.json")
    )
    args = parser.parse_args()

    reports: list[dict[str, Any]] = []
    started = time.time()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for check in CHECKS:
            reports.extend(
                run_check(browser, args.base, check, viewport)
                for viewport in check["viewports"]
            )
        browser.close()

    by_type: dict[str, int] = {}
    total = 0
    for report in reports:
        for issue in report.get("issues", []):
            by_type[issue["type"]] = by_type.get(issue["type"], 0) + 1
            total += 1

    summary = {
        "checks": len(reports),
        "total_issues": total,
        "by_type": dict(sorted(by_type.items(), key=lambda item: item[0])),
        "elapsed_seconds": round(time.time() - started, 1),
    }
    args.out.write_text(
        json.dumps({"summary": summary, "pages": reports}, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
