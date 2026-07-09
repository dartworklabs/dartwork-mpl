#!/usr/bin/env python3
"""Targeted docs layout regression checks.

This complements ``visual_check_docs.py`` with page-specific geometry checks for
the docs width contract:

- gallery thumbnail media slots keep a stable visual ratio
- API prose uses the selected 86ch readable measure, not the old narrow 72ch
  cap and not the full component canvas
- API article canvas uses the large-display shell instead of staying pinned
  to the old narrow frame
- representative docs intro/body paragraphs use the readable measure while
  components keep the article canvas
- article-local wide blocks do not break out into the right page TOC
- no horizontal overflow, excluding Shibuya offcanvas/sidebar surfaces
- static CSS/JS cache-busting versions are consistent across audited pages
- gallery/color search empty states use tokenized classes, not inline colors
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
        "path": "usage_guide/index.html",
        "viewports": [
            {"width": 390, "height": 844},
            {"width": 1440, "height": 1000},
        ],
        "themes": ["light", "dark"],
        "article_text": True,
        "evolution_widget": True,
    },
    {
        "path": "usage_guide/styles.html",
        "viewports": [
            {"width": 390, "height": 844},
            {"width": 1440, "height": 1000},
        ],
        "themes": ["light", "dark"],
        "article_text": True,
        "preset_compare": True,
    },
    {
        "path": "fonts/index.html",
        "viewports": [
            {"width": 390, "height": 844},
            {"width": 1440, "height": 1000},
        ],
        "themes": ["light", "dark"],
        "article_text": True,
        "font_picker": True,
    },
    {
        "path": "examples_gallery/index.html",
        "viewports": [
            {"width": 320, "height": 844},
            {"width": 390, "height": 844},
            {"width": 700, "height": 900},
            {"width": 900, "height": 900},
            {"width": 1024, "height": 900},
            {"width": 1440, "height": 1000},
            {"width": 1680, "height": 1050},
        ],
        "themes": ["light", "dark"],
        "article_text": True,
        "gallery": True,
    },
    {
        "path": "examples_gallery/01_styling_and_themes/plot_dark_mode.html",
        "viewports": [
            {"width": 390, "height": 844},
            {"width": 1440, "height": 1000},
        ],
        "themes": ["light", "dark"],
        "article_text": True,
        "example_controls": True,
    },
    {
        "path": "color_system/colors.html",
        "viewports": [
            {"width": 320, "height": 844},
            {"width": 390, "height": 844},
            {"width": 700, "height": 900},
            {"width": 760, "height": 900},
            {"width": 900, "height": 900},
            {"width": 1024, "height": 900},
            {"width": 1200, "height": 900},
            {"width": 1440, "height": 1000},
        ],
        "themes": ["light", "dark"],
        "article_text": True,
        "color_search": True,
    },
    {
        "path": "color_system/space.html",
        "viewports": [
            {"width": 390, "height": 844},
            {"width": 1024, "height": 900},
            {"width": 1440, "height": 1000},
        ],
        "themes": ["light", "dark"],
        "article_text": True,
        "colormap_builder": True,
    },
    {
        "path": "colormap_poc.html",
        "viewports": [
            {"width": 390, "height": 844},
            {"width": 1440, "height": 1000},
        ],
        "themes": ["light", "dark"],
        "colormap_poc": True,
    },
    {
        "path": "usage_guide/colors.html",
        "viewports": [
            {"width": 390, "height": 844},
            {"width": 1024, "height": 900},
            {"width": 1440, "height": 1000},
        ],
        "themes": ["light", "dark"],
        "article_text": True,
        "compare_controls": True,
        "palette_tabs": True,
        "palette_picker": True,
    },
    {
        "path": "landing_pocs.html",
        "viewports": [
            {"width": 390, "height": 844},
            {"width": 1440, "height": 1000},
        ],
        "themes": ["light", "dark"],
        "landing_pocs": True,
    },
    {
        "path": "_static/dm-interactive-styleguide.html",
        "viewports": [
            {"width": 390, "height": 844},
            {"width": 1440, "height": 1000},
        ],
        "themes": ["light", "dark"],
        "styleguide_harness": True,
    },
    {
        "path": "_static/_overhaul_review.html",
        "viewports": [
            {"width": 390, "height": 844},
            {"width": 1440, "height": 1000},
        ],
        "themes": ["light", "dark"],
        "overhaul_harness": True,
    },
    {
        "path": "_static/layout_width_pocs.html",
        "viewports": [{"width": 1440, "height": 1000}],
        "themes": ["light"],
        "layout_width_poc": True,
    },
    {
        "path": (
            "_static/layout_width_pocs.html?"
            "mode=single&variant=typed&page=api&viewport=1680&theme=dark"
        ),
        "viewports": [{"width": 1680, "height": 1100}],
        "themes": ["dark"],
        "layout_width_poc_deeplink": True,
    },
    {
        "path": "usage_guide/quickstart.html",
        "viewports": [
            {"width": 390, "height": 844},
            {"width": 1440, "height": 1000},
        ],
        "themes": ["light", "dark"],
        "article_text": True,
        "compare_widget": True,
    },
    {
        "path": "troubleshooting.html",
        "viewports": [
            {"width": 390, "height": 844},
            {"width": 1024, "height": 900},
            {"width": 1440, "height": 1000},
        ],
        "themes": ["light", "dark"],
        "article_text": True,
        "faq_controls": True,
    },
    {
        "path": "color_system/categorical-palettes.html",
        "viewports": [
            {"width": 320, "height": 844},
            {"width": 390, "height": 844},
            {"width": 900, "height": 900},
            {"width": 1440, "height": 1000},
            {"width": 1680, "height": 1050},
        ],
        "themes": ["light", "dark"],
        "article_text": True,
        "wide": True,
    },
    {
        "path": "api/helpers.html",
        "viewports": [
            {"width": 320, "height": 844},
            {"width": 390, "height": 844},
            {"width": 900, "height": 900},
            {"width": 1024, "height": 900},
            {"width": 1440, "height": 1000},
            {"width": 1680, "height": 1050},
            {"width": 2048, "height": 1200},
        ],
        "themes": ["light", "dark"],
        "article_text": True,
        "api_prose": True,
    },
    {
        "path": "color_system/colormaps.html",
        "viewports": [
            {"width": 320, "height": 844},
            {"width": 390, "height": 844},
            {"width": 900, "height": 900},
            {"width": 1440, "height": 1000},
            {"width": 1680, "height": 1050},
        ],
        "themes": ["light", "dark"],
        "article_text": True,
        "wide": True,
    },
]

LAYOUT_CHECK_JS = r"""
(opts) => {
  const issues = [];
  const viewportW = window.innerWidth;
  const trackedAssets = [
    'custom.css',
    'custom.js',
    'dartwork-design.css',
  ];
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
  const verifyEmptySearchState = (inputSelector, countSelector) => {
    const input = document.querySelector(inputSelector);
    const count = document.querySelector(countSelector);
    if (!input || !count) {
      issues.push({
        type: 'search-empty-state-missing',
        inputSelector,
        countSelector,
      });
      return;
    }
    input.value = 'zzzz-no-layout-match';
    input.dispatchEvent(new Event('input', {bubbles: true}));
    if (!count.classList.contains('is-empty')) {
      issues.push({
        type: 'search-empty-state',
        inputSelector,
        countSelector,
        text: count.textContent,
        cls: count.className,
        inlineColor: count.style.color || '',
      });
    }
    if (count.style.color) {
      issues.push({
        type: 'search-empty-inline-color',
        inputSelector,
        countSelector,
        text: count.textContent,
        cls: count.className,
        inlineColor: count.style.color,
      });
    }
  };
  const verifyFieldInputPrimitive = (wrapSelector, inputSelector) => {
    const wrap = document.querySelector(wrapSelector);
    const input = document.querySelector(inputSelector);
    if (!wrap || !input) {
      issues.push({
        type: 'field-input-primitive-missing',
        wrapSelector,
        inputSelector,
      });
      return;
    }
    if (!wrap.classList.contains('dm-field') || !input.classList.contains('dm-input')) {
      issues.push({
        type: 'field-input-primitive',
        wrapSelector,
        inputSelector,
        wrapClass: wrap.className,
        inputClass: input.className,
      });
    }
  };
  const verifyPressedGroupPrimitive = (groupSelector, optionSelector) => {
    const group = document.querySelector(groupSelector);
    if (!group) {
      issues.push({
        type: 'pressed-group-primitive-missing',
        groupSelector,
        optionSelector,
      });
      return;
    }
    const options = [...group.querySelectorAll(optionSelector)];
    const pressed = options.filter((opt) => opt.getAttribute('aria-pressed') === 'true');
    if (
      group.getAttribute('role') !== 'group' ||
      options.length === 0 ||
      pressed.length !== 1 ||
      !options.every((opt) => opt.hasAttribute('aria-pressed'))
    ) {
      issues.push({
        type: 'pressed-group-primitive',
        groupSelector,
        optionSelector,
        groupRole: group.getAttribute('role') || '',
        groupClass: group.className,
        optionCount: options.length,
        pressedCount: pressed.length,
        missingPressedCount: options.filter((opt) => !opt.hasAttribute('aria-pressed')).length,
      });
    }
  };
  const verifySelectedTabPrimitive = (groupSelector, tabSelector) => {
    const group = document.querySelector(groupSelector);
    if (!group) {
      issues.push({
        type: 'selected-tab-primitive-missing',
        groupSelector,
        tabSelector,
      });
      return;
    }
    const tabs = [...group.querySelectorAll(tabSelector)];
    const selected = tabs.filter((tab) => tab.getAttribute('aria-selected') === 'true');
    if (
      group.getAttribute('role') !== 'tablist' ||
      tabs.length === 0 ||
      selected.length !== 1 ||
      !tabs.every((tab) => tab.getAttribute('role') === 'tab') ||
      !tabs.every((tab) => tab.hasAttribute('aria-selected'))
    ) {
      issues.push({
        type: 'selected-tab-primitive',
        groupSelector,
        tabSelector,
        groupRole: group.getAttribute('role') || '',
        groupClass: group.className,
        tabCount: tabs.length,
        selectedCount: selected.length,
        missingSelectedCount: tabs.filter((tab) => !tab.hasAttribute('aria-selected')).length,
        missingRoleCount: tabs.filter((tab) => tab.getAttribute('role') !== 'tab').length,
      });
    }
  };
  const verifyCompareWidgetAlias = () => {
    const group = document.querySelector('.dmc-tabs');
    if (!group) {
      issues.push({type: 'compare-widget-missing'});
      return;
    }
    const tabs = [...group.querySelectorAll('.dmc-tab')];
    if (
      !group.classList.contains('dm-tabs') ||
      tabs.length === 0 ||
      !tabs.every((tab) => tab.classList.contains('dm-tab'))
    ) {
      issues.push({
        type: 'compare-widget-tab-primitive',
        groupClass: group.className,
        tabCount: tabs.length,
        missingAliasCount: tabs.filter((tab) => !tab.classList.contains('dm-tab')).length,
      });
    }
  };
  const verifyArticleTextMeasure = () => {
    const article = document.querySelector('article.yue');
    if (!article) {
      issues.push({type: 'article-text-missing-article'});
      return;
    }
    const articleR = article.getBoundingClientRect();
    if (articleR.width < 760) return;

    const excludedContainers = [
      '.dm-prose',
      '.dm-readable',
      '.admonition',
      '.sd-card',
      '.sd-tab-content',
      '.sphx-glr-thumbcontainer',
      '.dm-wide',
      '.dm-pe-widget',
      '.dm-ce',
      '.dm-pp',
      '.dm-fp',
      '.dm-pc',
      '.dm-compare-slider',
      '.dm-gallery-toolbar',
      '.dm-faq',
      '.dm-fav-tray',
      '#dm-cat-exp',
      'table',
    ];
    const paragraphs = [...document.querySelectorAll('article.yue section > p')]
      .filter((el) => {
        if (collapsed(el)) return false;
        if (el.textContent.trim().length < 60) return false;
        return !excludedContainers.some((sel) => el.closest(sel));
      });
    if (paragraphs.length === 0) return;

    for (const p of paragraphs.slice(0, 12)) {
      const r = p.getBoundingClientRect();
      const ratio = r.width / articleR.width;
      if (articleR.width >= 1000 && r.width < 820) {
        issues.push({
          type: 'article-text-too-narrow',
          text: p.textContent.trim().slice(0, 90),
          articleWidth: Math.round(articleR.width),
          paragraphWidth: Math.round(r.width),
          ratio: Number(ratio.toFixed(3)),
        });
      }
      if (articleR.width >= 1000 && r.width > 980) {
        issues.push({
          type: 'article-text-too-wide',
          text: p.textContent.trim().slice(0, 90),
          articleWidth: Math.round(articleR.width),
          paragraphWidth: Math.round(r.width),
          ratio: Number(ratio.toFixed(3)),
        });
      }
    }
  };
  const verifyScrollTargetClearance = (targetSelector, visibleSelector, minTop) => {
    const target = document.querySelector(targetSelector);
    const visible = document.querySelector(visibleSelector);
    if (!target || !visible) {
      issues.push({
        type: 'scroll-target-missing',
        targetSelector,
        visibleSelector,
      });
      return;
    }
    target.scrollIntoView({block: 'start', inline: 'nearest'});
    const r = visible.getBoundingClientRect();
    if (r.top < minTop) {
      issues.push({
        type: 'scroll-target-covered',
        targetSelector,
        visibleSelector,
        top: Math.round(r.top),
        minTop,
      });
    }
  };
  const verifyStickyOverlayClearance = (
    targetSelector,
    visibleSelector,
    overlaySelector,
    gap,
  ) => {
    const target = document.querySelector(targetSelector);
    const visible = document.querySelector(visibleSelector);
    const overlay = document.querySelector(overlaySelector);
    if (!target || !visible || !overlay) {
      issues.push({
        type: 'sticky-clearance-missing',
        targetSelector,
        visibleSelector,
        overlaySelector,
      });
      return;
    }
    target.scrollIntoView({block: 'start', inline: 'nearest'});
    const visibleR = visible.getBoundingClientRect();
    const overlayR = overlay.getBoundingClientRect();
    if (visibleR.top < overlayR.bottom + gap) {
      issues.push({
        type: 'sticky-overlay-covered',
        targetSelector,
        visibleSelector,
        overlaySelector,
        visibleTop: Math.round(visibleR.top),
        overlayBottom: Math.round(overlayR.bottom),
        gap,
      });
    }
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

  const headerSearch = [...document.querySelectorAll('.sy-head-extra .searchbox')]
    .find((el) => visibleInViewport(el));
  const headerLinks = [...document.querySelectorAll('.sy-head-links a')]
    .filter((el) => visibleInViewport(el));
  if (headerSearch && headerLinks.length > 0) {
    const searchR = headerSearch.getBoundingClientRect();
    const overlappingLink = headerLinks.find((link) => {
      const linkR = link.getBoundingClientRect();
      return linkR.right > searchR.left - 8;
    });
    if (overlappingLink) {
      const linkR = overlappingLink.getBoundingClientRect();
      issues.push({
        type: 'header-nav-search-overlap',
        text: overlappingLink.textContent.trim(),
        linkRight: Math.round(linkR.right),
        searchLeft: Math.round(searchR.left),
        viewportWidth: viewportW,
      });
    }
  }

  const toc = [...document.querySelectorAll('.sy-rside, .sy-rside .localtoc, .sy-right-toc')]
    .find((el) => visibleInViewport(el));
  if (toc && viewportW < 1600) {
    issues.push({
      type: 'toc-visible-too-early',
      viewportWidth: viewportW,
    });
  }
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

  const favTray = document.querySelector('.dm-fav-tray');
  const articleForFavTray = document.querySelector('article.yue');
  if (favTray && articleForFavTray && visibleInViewport(favTray)) {
    const trayR = favTray.getBoundingClientRect();
    const articleR = articleForFavTray.getBoundingClientRect();
    const overlapsArticle =
      trayR.left < articleR.right &&
      trayR.right > articleR.left &&
      trayR.top < articleR.bottom &&
      trayR.bottom > articleR.top;
    if (overlapsArticle) {
      issues.push({
        type: 'favorites-tray-article-overlap',
        viewportWidth: viewportW,
        trayLeft: Math.round(trayR.left),
        trayRight: Math.round(trayR.right),
        articleLeft: Math.round(articleR.left),
        articleRight: Math.round(articleR.right),
        cls: favTray.className,
      });
    }
    if (viewportW < 1600) {
      issues.push({
        type: 'favorites-tray-visible-too-early',
        viewportWidth: viewportW,
        cls: favTray.className,
      });
    }
  }

  if (opts.gallery) {
    verifyFieldInputPrimitive('.dm-gallery-search-wrap', '.dm-gallery-search');
    verifyPressedGroupPrimitive('.dm-gallery-pills', '.dm-gallery-pill.dm-chip');
    const toolbar = document.querySelector('.dm-gallery-toolbar');
    if (toolbar && viewportW <= 1100) {
      const toolbarR = toolbar.getBoundingClientRect();
      if (toolbarR.height > 180) {
        issues.push({
          type: 'gallery-toolbar-too-tall',
          height: Math.round(toolbarR.height),
          viewportWidth: viewportW,
        });
      }
      const rail = document.querySelector('.dm-gallery-pills');
      const chips = rail ? [...rail.querySelectorAll('button')] : [];
      const lastChip = chips[chips.length - 1];
      if (rail && lastChip) {
        lastChip.focus();
        const railR = rail.getBoundingClientRect();
        const chipR = lastChip.getBoundingClientRect();
        if (chipR.left < railR.left - 1 || chipR.right > railR.right + 1) {
          issues.push({
            type: 'gallery-focused-chip-hidden',
            chipText: lastChip.textContent,
            chipLeft: Math.round(chipR.left),
            chipRight: Math.round(chipR.right),
            railLeft: Math.round(railR.left),
            railRight: Math.round(railR.right),
          });
        }
      }
    }
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
    verifyStickyOverlayClearance(
      '.sphx-glr-thumbnails',
      '.sphx-glr-thumbcontainer img',
      '.dm-gallery-toolbar',
      8,
    );
    verifyEmptySearchState('.dm-gallery-search', '.dm-gallery-search-count');
  }

  if (opts.color_search) {
    verifyFieldInputPrimitive('.dm-color-search-wrap', '.dm-color-search');
    verifyPressedGroupPrimitive('.dm-cvd-buttons.dm-seg', '.dm-cvd-btn.dm-opt');
    verifyEmptySearchState('.dm-color-search', '.dm-color-search-count');
    if (favTray && viewportW <= 1100 && !collapsed(favTray)) {
      const isCollapsed = favTray.classList.contains('collapsed');
      if (!isCollapsed) {
        issues.push({
          type: 'favorites-tray-not-collapsed',
          viewportWidth: viewportW,
          cls: favTray.className,
        });
      } else {
        const trayR = favTray.getBoundingClientRect();
        const visibleHeight = Math.max(
          0,
          Math.min(trayR.bottom, window.innerHeight) - Math.max(trayR.top, 0),
        );
        if (visibleHeight > 48) {
          issues.push({
            type: 'favorites-tray-collapsed-too-tall',
            viewportWidth: viewportW,
            visibleHeight: Math.round(visibleHeight),
            cls: favTray.className,
          });
        }
      }
    }
  }

  if (opts.colormap_builder) {
    verifyPressedGroupPrimitive('.dm-cb-tabs.dm-seg', '.dm-cb-tab.dm-opt');
    const midGroup = document.querySelector('.dm-cb-mid-group');
    const diverging = document.querySelector('.dm-cb-tab[data-type="diverging"]');
    const sequential = document.querySelector('.dm-cb-tab[data-type="sequential"]');
    if (!midGroup || !diverging || !sequential) {
      issues.push({type: 'colormap-builder-midpoint-missing'});
    } else {
      if (!midGroup.hidden || midGroup.getAttribute('aria-hidden') !== 'true') {
        issues.push({
          type: 'colormap-builder-midpoint-initial-state',
          hidden: midGroup.hidden,
          ariaHidden: midGroup.getAttribute('aria-hidden') || '',
        });
      }
      if (midGroup.getAttribute('style') || midGroup.style.display) {
        issues.push({
          type: 'colormap-builder-inline-display-state',
          style: midGroup.getAttribute('style') || '',
        });
      }
      diverging.click();
      if (midGroup.hidden || midGroup.getAttribute('aria-hidden') !== 'false') {
        issues.push({
          type: 'colormap-builder-midpoint-diverging-state',
          hidden: midGroup.hidden,
          ariaHidden: midGroup.getAttribute('aria-hidden') || '',
        });
      }
      sequential.click();
      if (!midGroup.hidden || midGroup.getAttribute('aria-hidden') !== 'true') {
        issues.push({
          type: 'colormap-builder-midpoint-return-state',
          hidden: midGroup.hidden,
          ariaHidden: midGroup.getAttribute('aria-hidden') || '',
        });
      }
    }
  }

  if (opts.colormap_explorer) {
    verifySelectedTabPrimitive('.dm-ce-tabs.dm-tabs', '.dm-ce-tab.dm-tab');
    verifyPressedGroupPrimitive('.dm-ce-tone.dm-seg', '.dm-ce-tone-btn.dm-opt');
    verifyScrollTargetClearance('.dm-ce', '.dm-ce-tabs', 64);
  }

  if (opts.colormap_poc) {
    verifySelectedTabPrimitive(
      '.cm-poc-a-tabs.dm-tabs',
      '.cm-poc-a-tab.dm-tab',
    );
    verifyPressedGroupPrimitive(
      '.cm-poc-a-tone.dm-seg',
      '.cm-poc-a-tone-btn.dm-opt',
    );
    verifyPressedGroupPrimitive(
      '.cm-poc-b-tone.dm-seg',
      '.cm-poc-b-tone-btn.dm-opt',
    );
  }

  if (opts.palette_tabs) {
    verifySelectedTabPrimitive('.dm-pc-tabs.dm-tabs', '.dm-pe-tab.dm-tab');
    verifyScrollTargetClearance('.dm-pe-widget', '.dm-pc-tabs', 64);
  }

  if (opts.palette_picker) {
    verifySelectedTabPrimitive('.dm-pp-tabs.dm-tabs', '.dm-pp-tab.dm-tab');
    verifyPressedGroupPrimitive('.dm-pp-buttons', '.dm-pp-btn.dm-chip');
  }

  if (opts.landing_pocs) {
    verifyPressedGroupPrimitive('.lpoc-palettes', '.lpoc-palette-btn');
  }

  if (opts.styleguide_harness) {
    verifyPressedGroupPrimitive(
      '[data-seg][aria-label="Tool selector"]',
      '.dm-opt',
    );
    verifyPressedGroupPrimitive(
      '[data-seg][aria-label="Operating system selector"]',
      '.dm-opt',
    );
    verifySelectedTabPrimitive('[data-tabs].dm-tabs', '.dm-tab');
    verifyPressedGroupPrimitive('[data-chips]', '.dm-chip');
    verifyPressedGroupPrimitive('[data-swatches]', '.dm-swatch');
    verifyPressedGroupPrimitive('[data-steps]', '.dm-chip');
    if (!document.querySelector('.dm-slider[data-slider]')) {
      issues.push({type: 'styleguide-slider-missing'});
    }
    const wrap = document.querySelector('.wrap');
    if (wrap && viewportW >= 1440) {
      const wrapR = wrap.getBoundingClientRect();
      if (wrapR.width < 1000) {
        issues.push({
          type: 'styleguide-canvas-too-narrow',
          width: Math.round(wrapR.width),
          viewportWidth: viewportW,
        });
      }
    }
  }

  if (opts.overhaul_harness) {
    const requiredLinks = [
      'custom.css',
      'dynamic_ux.css',
      'dartwork-design.css',
      'dm-interactive.css',
    ];
    const linked = [...document.querySelectorAll('link[href]')]
      .map((link) => link.href);
    const missingLinks = requiredLinks.filter(
      (asset) => !linked.some((href) => href.includes(asset)),
    );
    if (missingLinks.length > 0 || !document.querySelector('.rv-tt')) {
      issues.push({
        type: 'overhaul-harness-assets',
        missingLinks,
        hasThemeToggle: Boolean(document.querySelector('.rv-tt')),
      });
    }
    if (!document.querySelector('.dm-install-picker')) {
      issues.push({type: 'overhaul-install-picker-missing'});
    } else {
      verifyPressedGroupPrimitive(
        '.dm-install-picker .dm-seg[aria-label="Package manager"]',
        '.dm-opt',
      );
      verifyPressedGroupPrimitive(
        '.dm-install-picker .dm-seg[aria-label="Operating system"]',
        '.dm-opt',
      );
      if (!document.querySelector('.dm-install-picker .dm-code .dm-icon-btn')) {
        issues.push({type: 'overhaul-install-code-surface'});
      }
    }
  }

  if (opts.layout_width_poc || opts.layout_width_poc_deeplink) {
    const statusText = document.querySelector('.status-strip')?.textContent || '';
    if (
      !statusText.includes('Current shipping CSS') ||
      !statusText.includes('C split prose/component') ||
      !statusText.includes('POC variants')
    ) {
      issues.push({type: 'layout-poc-status-missing', statusText});
    }
    if (!document.querySelector('#copyViewLink')) {
      issues.push({type: 'layout-poc-copy-link-missing'});
    }

    const currentSummary = document.querySelector('.summary-card[data-id="split"]');
    const currentCompare = document.querySelector(
      '.compare-card[data-variant-id="split"]',
    );
    if (
      !currentSummary?.classList.contains('is-current') ||
      !currentSummary?.textContent.includes('current shipping') ||
      !currentCompare?.classList.contains('is-current') ||
      !currentCompare?.textContent.includes('current shipping')
    ) {
      issues.push({type: 'layout-poc-current-badge-missing'});
    }
    for (const variantId of ['typed']) {
      const card = document.querySelector(`.summary-card[data-id="${variantId}"]`);
      if (!card?.textContent.includes('candidate')) {
        issues.push({type: 'layout-poc-candidate-badge-missing', variantId});
      }
    }

    if (opts.layout_width_poc) {
      if (!document.querySelector('#modeControls [data-id="compare"][aria-pressed="true"]')) {
        issues.push({type: 'layout-poc-default-mode'});
      }
      if (!document.querySelector('#variantControls [data-id="split"][aria-pressed="true"]')) {
        issues.push({type: 'layout-poc-default-variant'});
      }
      const cards = [...document.querySelectorAll('.compare-card')];
      if (cards.length !== 4) {
        issues.push({type: 'layout-poc-card-count', count: cards.length});
      }
      const currentMetrics =
        currentCompare?.querySelector('.compare-card__metrics')?.textContent || '';
      if (!currentMetrics.includes('article') || !currentMetrics.includes('text')) {
        issues.push({type: 'layout-poc-default-metrics', currentMetrics});
      }
      const match = currentMetrics.match(/text\s+(\d+)px/);
      if (!match || Number(match[1]) < 820 || Number(match[1]) > 980) {
        issues.push({type: 'layout-poc-current-text-width', currentMetrics});
      }
    }

    if (opts.layout_width_poc_deeplink) {
      const expected = {
        mode: 'single',
        variant: 'typed',
        page: 'api',
        viewport: '1680',
        theme: 'dark',
      };
      const params = new URLSearchParams(location.search);
      for (const [key, value] of Object.entries(expected)) {
        if (params.get(key) !== value) {
          issues.push({
            type: 'layout-poc-deeplink-param',
            key,
            expected: value,
            actual: params.get(key),
          });
        }
      }
      if (!document.querySelector('#modeControls [data-id="single"][aria-pressed="true"]')) {
        issues.push({type: 'layout-poc-deeplink-mode'});
      }
      if (!document.querySelector('#variantControls [data-id="typed"][aria-pressed="true"]')) {
        issues.push({type: 'layout-poc-deeplink-variant'});
      }
      const metricText = document.querySelector('#metrics')?.textContent || '';
      const match = metricText.match(/text\s+(\d+)px/);
      if (!match || Number(match[1]) > 900) {
        issues.push({type: 'layout-poc-deeplink-text-width', metricText});
      }
    }
  }

  if (opts.font_picker) {
    verifySelectedTabPrimitive('.dm-fp-tabs.dm-tabs', '.dm-fp-tab.dm-tab');
  }

  if (opts.preset_compare) {
    verifyPressedGroupPrimitive('.dm-pc-dots', '.dm-pc-dot');
    const activePanels = [...document.querySelectorAll('.dm-pc-panel')]
      .filter((panel) => panel.classList.contains('is-active'));
    const arrows = [...document.querySelectorAll('.dm-pc-arrow')];
    const params = document.querySelector('.dm-pc-params');
    const paramItems = params
      ? [...params.querySelectorAll('.dm-pc-param-item')]
      : [];
    const clippedParam = params
      ? paramItems.find((item) => {
          const itemR = item.getBoundingClientRect();
          const paramsR = params.getBoundingClientRect();
          return itemR.right > paramsR.right + 1 || itemR.left < paramsR.left - 1;
        })
      : null;
    if (
      activePanels.length !== 1 ||
      arrows.length !== 2 ||
      !arrows.every((arrow) => arrow.classList.contains('dm-icon-btn')) ||
      Boolean(clippedParam)
    ) {
      issues.push({
        type: 'preset-compare-primitive',
        activePanelCount: activePanels.length,
        arrowCount: arrows.length,
        arrowsMissingIconBtn: arrows.filter((arrow) => !arrow.classList.contains('dm-icon-btn')).length,
        clippedParam: clippedParam ? clippedParam.textContent.trim() : '',
      });
    }
  }

  if (opts.evolution_widget) {
    verifyPressedGroupPrimitive('.evo-labels', '.evo-label.dm-chip');
    const slider = document.querySelector('#evo-slider.dm-slider');
    const activeImages = [...document.querySelectorAll('.evo-img')]
      .filter((img) => img.classList.contains('is-active'));
    if (!slider || activeImages.length !== 1) {
      issues.push({
        type: 'evolution-widget-primitive',
        hasSlider: Boolean(slider),
        activeImageCount: activeImages.length,
      });
    }
  }

  if (opts.compare_controls) {
    verifyPressedGroupPrimitive(
      '.dm-compare-toggle.dm-seg',
      '.dm-compare-toggle-btn.dm-opt',
    );
  }

  if (opts.compare_widget) {
    verifyCompareWidgetAlias();
  }

  if (opts.faq_controls) {
    verifyFieldInputPrimitive('.dm-faq-search-wrap', '.dm-faq-search');
    verifyPressedGroupPrimitive('.dm-faq-pills', '.dm-faq-pill.dm-chip');
    verifyEmptySearchState('.dm-faq-search', '.dm-faq-search-count');
  }

  if (opts.example_controls) {
    verifyPressedGroupPrimitive(
      '.dm-example-controls.dm-seg',
      '.dm-example-mode-btn.dm-opt',
    );
  }

  if (opts.article_text) {
    verifyArticleTextMeasure();
  }

  if (opts.wide) {
    if (document.querySelector('#dm-cat-exp style')) {
      issues.push({type: 'categorical-inline-style'});
    }
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

  if (opts.api_prose) {
    const article = document.querySelector('article.yue');
    const prose = [...document.querySelectorAll('article section > p')]
      .find((el) => !collapsed(el) && !el.closest('.dm-prose, .dm-readable'));
    if (!article) {
      issues.push({type: 'api-prose-missing-article'});
    } else if (!prose) {
      issues.push({type: 'api-prose-missing'});
    } else {
      const articleR = article.getBoundingClientRect();
      const proseR = prose.getBoundingClientRect();
      const ratio = proseR.width / articleR.width;
      if (articleR.width >= 1000 && proseR.width < 820) {
        issues.push({
          type: 'api-prose-too-narrow',
          articleWidth: Math.round(articleR.width),
          proseWidth: Math.round(proseR.width),
          ratio: Number(ratio.toFixed(3)),
        });
      }
      if (articleR.width >= 1000 && proseR.width > 980) {
        issues.push({
          type: 'api-prose-too-wide',
          articleWidth: Math.round(articleR.width),
          proseWidth: Math.round(proseR.width),
          ratio: Number(ratio.toFixed(3)),
        });
      }
      if (viewportW >= 1680 && articleR.width < 1040) {
        issues.push({
          type: 'api-article-canvas-too-narrow',
          articleWidth: Math.round(articleR.width),
          viewportWidth: viewportW,
        });
      }
      if (viewportW >= 1440 && viewportW < 1600 && articleR.width < 1000) {
        issues.push({
          type: 'api-article-canvas-too-narrow',
          articleWidth: Math.round(articleR.width),
          viewportWidth: viewportW,
        });
      }
      if (viewportW >= 1920 && articleR.width < 1280) {
        issues.push({
          type: 'api-article-canvas-too-narrow',
          articleWidth: Math.round(articleR.width),
          viewportWidth: viewportW,
        });
      }
    }
  }

  return {
    url: location.pathname,
    viewport: {w: viewportW, h: window.innerHeight},
    assetVersions: Object.fromEntries(trackedAssets.map((asset) => {
      const isStaticHarness = location.pathname.includes('/_static/');
      const versions = [...document.querySelectorAll('link[href], script[src]')]
        .map((el) => el.href || el.src || '')
        .filter((url) => url.includes('/_static/') && url.includes(asset))
        .map((url) => new URL(url, location.href).searchParams.get('v') || '')
        .filter((version) => version || !isStaticHarness);
      return [asset, [...new Set(versions)].sort()];
    })),
    issues,
  };
}
"""


def apply_theme(page: Any, theme: str) -> None:
    page.evaluate(
        """(theme) => {
          const dark = theme === 'dark';
          document.documentElement.classList.toggle('dark', dark);
          document.body.toggleAttribute('data-theme', dark);
          if (dark) document.body.setAttribute('data-theme', 'dark');
        }""",
        theme,
    )


def run_check(
    browser: Any,
    base: str,
    check: dict[str, Any],
    viewport: dict[str, int],
    theme: str,
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
        apply_theme(page, theme)
        if check.get("palette_picker"):
            page.wait_for_selector(".dm-pp-tab", timeout=5_000)
        if check.get("font_picker"):
            page.wait_for_selector(".dm-fp-tab", timeout=5_000)
        if check.get("preset_compare"):
            page.wait_for_selector(".dm-pc-dot", timeout=5_000)
        if check.get("evolution_widget"):
            page.wait_for_selector(".evo-label", timeout=5_000)
        if check.get("colormap_poc"):
            page.wait_for_selector(".cm-poc-a-tab", timeout=5_000)
            page.wait_for_selector(".cm-poc-b-tone-btn", timeout=5_000)
        if check.get("landing_pocs"):
            page.wait_for_selector(".lpoc-palette-btn", timeout=5_000)
        if check.get("styleguide_harness"):
            page.wait_for_selector(".dm-seg .dm-opt", timeout=5_000)
            page.wait_for_selector(".dm-tabs .dm-tab", timeout=5_000)
        if check.get("overhaul_harness"):
            page.wait_for_selector(".dm-install-picker", timeout=5_000)
        if check.get("layout_width_poc"):
            page.wait_for_selector(
                '.compare-card[data-variant-id="split"] .compare-card__metrics .metric',
                timeout=8_000,
            )
        if check.get("layout_width_poc_deeplink"):
            page.wait_for_selector("#metrics .metric", timeout=8_000)
        page.wait_for_timeout(300)
        result = page.evaluate(
            LAYOUT_CHECK_JS,
            {
                "gallery": bool(check.get("gallery")),
                "color_search": bool(check.get("color_search")),
                "article_text": bool(check.get("article_text")),
                "example_controls": bool(check.get("example_controls")),
                "colormap_builder": bool(check.get("colormap_builder")),
                "colormap_explorer": bool(check.get("colormap_explorer")),
                "colormap_poc": bool(check.get("colormap_poc")),
                "compare_controls": bool(check.get("compare_controls")),
                "compare_widget": bool(check.get("compare_widget")),
                "palette_tabs": bool(check.get("palette_tabs")),
                "palette_picker": bool(check.get("palette_picker")),
                "landing_pocs": bool(check.get("landing_pocs")),
                "styleguide_harness": bool(check.get("styleguide_harness")),
                "overhaul_harness": bool(check.get("overhaul_harness")),
                "layout_width_poc": bool(check.get("layout_width_poc")),
                "layout_width_poc_deeplink": bool(
                    check.get("layout_width_poc_deeplink")
                ),
                "font_picker": bool(check.get("font_picker")),
                "preset_compare": bool(check.get("preset_compare")),
                "evolution_widget": bool(check.get("evolution_widget")),
                "faq_controls": bool(check.get("faq_controls")),
                "wide": bool(check.get("wide")),
                "api_prose": bool(check.get("api_prose")),
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
    result["theme"] = theme
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
            themes = check.get("themes", ["light"])
            reports.extend(
                run_check(browser, args.base, check, viewport, theme)
                for viewport in check["viewports"]
                for theme in themes
            )
        browser.close()

    by_type: dict[str, int] = {}
    total = 0
    versions_by_asset: dict[str, set[str]] = {}
    for report in reports:
        for asset, versions in report.get("assetVersions", {}).items():
            versions_by_asset.setdefault(asset, set()).update(versions)

    static_mismatches = {
        asset: sorted(versions)
        for asset, versions in versions_by_asset.items()
        if len(versions) > 1
    }
    if static_mismatches:
        reports.append(
            {
                "path": "__static_assets__",
                "viewport": None,
                "theme": None,
                "issues": [
                    {
                        "type": "static-version-mismatch",
                        "assets": static_mismatches,
                    }
                ],
            }
        )

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
