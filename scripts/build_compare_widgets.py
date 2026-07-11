r"""Generate every before/after comparison widget used in the docs.

Each widget is a self-contained, id-scoped, **JavaScript-free** toggle
(see ``scripts/compare_widget.py`` for the rationale and markup). Sphinx
pages embed the output via:

```
\`\`\`{raw} html
:file: <relative path to the generated .html>
\`\`\`
```

This replaces the old drag-to-wipe sliders (the ``wipe_*.html`` generated
by the former ``build_wipe_snippets.py``, plus the hand-written
``compare_slider.html`` / ``*_slider.html`` files), all of which guessed
the ``_static/`` path at runtime and collapsed when an image failed to
load.

``image_src`` for each widget is the **exact static relative path from the
embedding page** (no runtime guessing): pages under ``usage_guide/`` use
``../_static/`` or ``../_images/``; the root ``index.md`` uses ``_static/``.

Run from the repo root:

    python scripts/build_compare_widgets.py
"""

from __future__ import annotations

from pathlib import Path

from compare_widget import render_compare

DOCS = Path(__file__).resolve().parent.parent / "docs"


# Each entry: (output html path, wid, after_src, before_src, alt, labels...)
# after = dartwork (shown first), before = vanilla.
WIDGETS = [
    # ── Landing-PoC wipe replacements (embedded from usage_guide pages) ──
    # tutorials.md, recipes.md, layout.md → page depth 1 → "../_static/".
    {
        "out": "_static/wipe_l2_bar.html",
        "wid": "dm-cmp-l2-bar",
        "after": "../_static/compare_assets/wipe_bar_after.svg",
        "before": "../_static/compare_assets/wipe_bar_before.svg",
        "alt": "Grouped bar with value labels",
    },
    {
        "out": "_static/wipe_l3_scatter.html",
        "wid": "dm-cmp-l3-scatter",
        "after": "../_static/compare_assets/wipe_scatter_after.svg",
        "before": "../_static/compare_assets/wipe_scatter_before.svg",
        "alt": "Scatter with OLS fit",
    },
    {
        "out": "_static/wipe_l4_dual.html",
        "wid": "dm-cmp-l4-dual",
        "after": "../_static/compare_assets/wipe_dual_after.svg",
        "before": "../_static/compare_assets/wipe_dual_before.svg",
        "alt": "Dual-axis revenue / margin dashboard",
    },
    {
        "out": "_static/wipe_l6_stacked.html",
        "wid": "dm-cmp-l6-stacked",
        "after": "../_static/compare_assets/wipe_stacked_after.svg",
        "before": "../_static/compare_assets/wipe_stacked_before.svg",
        "alt": "Stacked area composition",
    },
    {
        "out": "_static/wipe_l8_violin.html",
        "wid": "dm-cmp-l8-violin",
        "after": "../_static/compare_assets/wipe_violin_after.svg",
        "before": "../_static/compare_assets/wipe_violin_before.svg",
        "alt": "Distribution comparison (violin)",
    },
    # ── Landing hero (embedded from root index.md → depth 0 → "_static/") ──
    {
        "out": "_static/compare_slider.html",
        "wid": "dm-cmp-hero",
        "after": "_static/landing_hero_after.svg",
        "before": "_static/landing_hero_before.svg",
        "alt": "dartwork-mpl vs vanilla matplotlib",
    },
    # ── Quickstart compare (embedded from usage_guide/quickstart.md) ──
    {
        "out": "usage_guide/images/compare_slider.html",
        "wid": "dm-cmp-quickstart",
        "after": "../_static/compare_assets/quickstart_compare_after.svg",
        "before": "../_static/compare_assets/quickstart_compare_before.svg",
        "alt": "Quickstart figure — dartwork vs vanilla",
    },
    # ── layout.md helper demos (SVGs reach output via _images) ──
    {
        "out": "usage_guide/images/label_axes_slider.html",
        "wid": "dm-cmp-label-axes",
        "after": "../_images/label_axes_dm.svg",
        "before": "../_images/label_axes_vanilla.svg",
        "alt": "label_axes() panel labels",
    },
    {
        "out": "usage_guide/images/set_decimal_slider.html",
        "wid": "dm-cmp-set-decimal",
        "after": "../_images/set_decimal_dm.svg",
        "before": "../_images/set_decimal_vanilla.svg",
        "alt": "set_decimal() tick formatting",
    },
    # ── Interactive viewer (embedded from usage_guide/interactive.md) ──
    # A "default vs modified" pair, not vanilla/dartwork → custom labels.
    {
        "out": "_static/interactive_slider.html",
        "wid": "dm-cmp-interactive",
        "after": "../_static/interactive_viewer_modified.jpeg",
        "before": "../_static/interactive_viewer_default.jpeg",
        "alt": "Interactive parameter viewer",
        "after_label": "Modified",
        "before_label": "Default",
    },
]


def main() -> None:
    for w in WIDGETS:
        html = render_compare(
            w["wid"],
            after_src=w["after"],
            before_src=w["before"],
            after_label=w.get("after_label", "Dartwork"),
            before_label=w.get("before_label", "Vanilla"),
            alt=w["alt"],
        )
        path = DOCS / w["out"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html)
        print(f"  ✓ {w['out']}")


if __name__ == "__main__":
    main()
