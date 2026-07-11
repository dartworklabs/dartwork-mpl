#!/usr/bin/env python3
"""Build the measured typography matrix include."""

from __future__ import annotations

import html
from pathlib import Path

from dartwork_mpl import font

SCRIPT_DIR = Path(__file__).resolve().parent
OUT = SCRIPT_DIR.parent / "typography_matrix.html"


def _weights_text(weights: tuple[int, ...]) -> str:
    return ", ".join(str(weight) for weight in weights)


def _numeric_axes_text(measurement: font.FontMeasurement) -> str:
    if measurement.fixed_pitch:
        return "mono"
    if measurement.default_digit_widths_uniform:
        return "digits"
    return "-"


def _yes_no(value: bool) -> str:
    return "yes" if value else "-"


def _chart_glyph_text(measurement: font.FontMeasurement) -> str:
    glyphs = "".join(measurement.chart_glyphs)
    return f"{len(measurement.chart_glyphs)}/8 {glyphs}"


def _row(family: font.FontFamily) -> str:
    measurement = font._measure(family.name)
    cells = (
        family.name,
        family.role,
        _weights_text(measurement.weights),
        _numeric_axes_text(measurement),
        _yes_no(measurement.tnum_available),
        _chart_glyph_text(measurement),
        _yes_no(measurement.hangul),
        " / ".join(measurement.licenses),
    )
    tds = "".join(f"<td>{html.escape(cell)}</td>" for cell in cells)
    return f"<tr>{tds}</tr>"


def build() -> str:
    rows = "\n".join(_row(family) for family in font.font_families().values())
    return f"""<!-- GENERATED FILE - do not edit by hand.
     Source: docs/_static/scripts/build_typography_matrix.py
     Data:   dartwork_mpl.font.font_families() + dartwork_mpl.font._measure()
     Regenerate: python3 docs/_static/scripts/build_typography_matrix.py -->
<div id="dm-typography-matrix" class="yue">
<table>
<thead>
<tr><th>Family</th><th>Role</th><th>Weights</th><th>Aligned digits</th><th>tnum available</th><th>Chart glyphs</th><th>Hangul</th><th>License</th></tr>
</thead>
<tbody>
{rows}
</tbody>
</table>
</div>
"""


def main() -> None:
    html_text = build()
    OUT.write_text(html_text, encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
