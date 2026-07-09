#!/usr/bin/env python3
"""Build the v5 dartwork color-family showcase.

The output is a standalone static HTML file used by the API diagnostics page.
It reads the generated v5 palette table directly instead of importing
dartwork_mpl, so regeneration does not depend on matplotlib font caches.
"""

from __future__ import annotations

import html
import runpy
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[2]
OUT = SCRIPT_DIR.parent / "palette_showcase.html"
GENERATED = ROOT / "src" / "dartwork_mpl" / "_colors" / "_generated.py"

ORDER = [
    "red",
    "rose",
    "coral",
    "tangerine",
    "orange",
    "amber",
    "yellow",
    "lime",
    "green",
    "teal",
    "cyan",
    "sky",
    "blue",
    "cobalt",
    "indigo",
    "violet",
    "purple",
    "fuchsia",
    "pink",
    "gray",
]


def _text_color(hex_color: str) -> str:
    raw = hex_color.lstrip("#")
    r, g, b = (int(raw[i : i + 2], 16) / 255 for i in (0, 2, 4))
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#ffffff" if lum < 0.48 else "#1f2933"


def main() -> None:
    palette: dict[str, tuple[str, ...]] = runpy.run_path(str(GENERATED))[
        "PALETTE"
    ]
    rows: list[str] = []
    for family in ORDER:
        colors = palette[family]
        swatches = []
        for i, hex_color in enumerate(colors):
            token = f"dc.{family}{i}"
            swatches.append(
                '<button class="sw" '
                f'style="--c:{hex_color};--tc:{_text_color(hex_color)}" '
                f'data-token="{html.escape(token)}" '
                f'data-hex="{hex_color.upper()}" '
                f'aria-label="{html.escape(token)} {hex_color.upper()}">'
                f"<span>{i}</span><code>{html.escape(token)}</code></button>"
            )
        rows.append(
            '<section class="family">'
            f"<h2>dc.{html.escape(family)}</h2>"
            '<div class="swatches">' + "\n".join(swatches) + "</div></section>"
        )

    OUT.write_text(
        """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>dartwork color v5 families</title>
<style>
:root{color-scheme:light;--bg:#fff;--fg:#20242a;--muted:#667085;--line:#e5e7eb}
body{margin:0;background:var(--bg);color:var(--fg);font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{max-width:1120px;margin:0 auto;padding:24px 22px 40px}
header{display:flex;align-items:end;justify-content:space-between;gap:16px;margin-bottom:22px;border-bottom:1px solid var(--line);padding-bottom:16px}
h1{font-size:20px;line-height:1.2;margin:0;font-weight:720}
p{margin:6px 0 0;color:var(--muted);font-size:13px;line-height:1.45}
.count{font-size:12px;color:var(--muted);white-space:nowrap}
.family{padding:13px 0 16px;border-bottom:1px solid var(--line)}
h2{margin:0 0 8px;font-size:13px;font-weight:680;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.swatches{display:grid;grid-template-columns:repeat(10,minmax(0,1fr));gap:4px}
.sw{appearance:none;border:0;border-radius:6px;min-height:58px;padding:7px 5px;background:var(--c);color:var(--tc);cursor:pointer;text-align:left;display:flex;flex-direction:column;justify-content:space-between}
.sw:hover{outline:2px solid #111827;outline-offset:1px}
.sw span{font-weight:760;font-size:13px}
.sw code{font-size:9.5px;color:inherit;opacity:.86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
@media (max-width:720px){main{padding:18px 14px 30px}.swatches{grid-template-columns:repeat(5,minmax(0,1fr))}.sw{min-height:54px}header{display:block}.count{display:block;margin-top:8px}}
</style>
</head>
<body>
<main>
<header>
<div>
<h1>dartwork color v5 families</h1>
<p>20 generated families, 10 perceptually equalized steps each. Click a swatch to copy its token.</p>
</div>
<div class="count">200 named colors</div>
</header>
"""
        + "\n".join(rows)
        + """
</main>
<script>
document.querySelectorAll('.sw').forEach((button) => {
  button.addEventListener('click', async () => {
    const token = button.dataset.token;
    try { await navigator.clipboard.writeText(token); } catch (_) {}
    button.animate([{transform:'translateY(0)'},{transform:'translateY(-2px)'},{transform:'translateY(0)'}], {duration:160});
  });
});
</script>
</body>
</html>
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
