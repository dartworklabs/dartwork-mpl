# i18n: East-Asian myriad axis formatter — Design (P7)

> Program umbrella #411, pillar EO7. Advisory/design by orchestrator; implementation by codex.

## Problem

dartwork-mpl is KR-first (report-kr / scientific-kr presets, bundled Korean fonts), yet
`formatting.py` ships only **Western** axis number formatters — `format_axis_millions` (M),
`format_axis_billions` (B), `format_axis_si` (k/M/G), `format_axis_currency`. East-Asian number
systems group by **myriads (10⁴)**, not thousands (10³): 만/억/조 (ko), 万/亿/兆 (zh),
万/億/兆 (ja). A KR chart of "1.5억" today has to be hand-labeled. This is a concrete i18n gap for a
"global" utility.

## Design

Add one new public formatter to `formatting.py`, mirroring the existing `format_axis_millions`
structure (a `matplotlib.ticker.FuncFormatter` applied to the chosen axis):

```python
def format_axis_myriad(
    ax: Axes,
    axis: Literal["x", "y", "both"] = "y",
    locale: Literal["ko", "zh", "ja"] = "ko",
    decimals: int = 1,
    currency: str | None = None,
) -> None:
```

Myriad unit ladders (value threshold → unit char):
| locale | 10⁴ | 10⁸ | 10¹² | 10¹⁶ |
|---|---|---|---|---|
| ko | 만 | 억 | 조 | 경 |
| zh | 万 | 亿 | 兆 | 京 |
| ja | 万 | 億 | 兆 | 京 |

Formatter algorithm for a tick value `x`:
- sign = "-" if x < 0 else ""; work with `abs(x)`.
- if `abs(x) < 10⁴`: return `sign + currency? + f"{abs(x):,.0f}"` (thousands-grouped integer, no unit).
- else: pick the largest ladder threshold `t` with `abs(x) >= t`; `scaled = abs(x)/t`; format `scaled`
  with `decimals` places but strip a trailing `.0…` (so 1.0억 → "1억", 1.5억 → "1.5억");
  return `sign + currency? + scaled_str + unit`.
- `0` → `"0"`.
- `currency` (e.g. "₩", "¥") is an optional prefix placed after the sign.

Follow the module's existing idioms exactly: same param names/order shape as `format_axis_millions`
(`ax`, `axis`, …), same `axis` handling ("x"/"y"/"both"), a nested `FuncFormatter` closure, full
type hints, and a docstring in the same style as the neighbours (so `test_docstring_catalogs` /
`test_typing_parity` stay green).

## Scope (P7 PR)
- `src/dartwork_mpl/formatting.py`: add `format_axis_myriad`.
- `src/dartwork_mpl/__init__.py`: import it in the `from .formatting import (...)` block and add
  `"format_axis_myriad"` to `__all__`, adjacent to the other `format_axis_*` entries.
- If a type stub (`formatting.pyi` / `__init__.pyi`) or a docstring/typing **parity** test enumerates
  the formatting exports, update it so the new name is covered.
- Tests: `tests/test_formatting.py` (extend) or `tests/test_formatting_myriad.py` (new) — assert the
  produced tick strings for representative values across all three locales (e.g. ko: 12_300_000 →
  "1,230만", 150_000_000 → "1.5억", 1_200_000_000_000 → "1.2조", 8_000 → "8,000", 0 → "0",
  −150_000_000 → "-1.5억"; zh 억→亿, ja 억→億). Build via
  `dm.style.use("scientific")` + `plt.subplots(figsize=dm.figsize("9cm","standard"))`, apply the
  formatter, and read `ax.yaxis.get_major_formatter()(value)` directly (deterministic; no pixels).

## Non-goals (P7)
- **Locale-aware dates** (month/day names, era calendars) — a larger lift (needs the `locale`
  module / CLDR data and has platform-locale caveats). Documented as a future extension; not in this PR.
- **Broadening bundled CJK / RTL / Cyrillic font coverage** — a separate, license-sensitive effort
  (new font assets + license files + glyph-coverage tests). Out of scope here; the myriad formatter
  works with the already-bundled Korean/CJK fonts.

## Acceptance
- `format_axis_myriad` public + exported; new tests green (all three locales, sign, sub-myriad,
  zero, currency); ruff + mypy clean; existing formatting / typing / docstring tests unaffected;
  full suite green.
