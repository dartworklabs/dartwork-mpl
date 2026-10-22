# Plan — #523 no meaningless decimals (formatters, validator, templates)

User instruction (2026-10-22): "의미없는 소수점은 항상 신경쓰도록해. 전부 정수인데 소수점 넣을
이유가 없어." Integer ticks and value labels never print decimals (`200.0` → `200`,
`1.0k` → `1k`); fractional steps keep one decimal count on every tick (`17.5, 20.0, 22.5`).
Add-on (same day): numeric value labels on bars and lines are one weight step heavier
(`fontweight=dm.fw(1)`). Nothing else about the visual style changes.

Base: `origin/main` 7d35b7af (already contains the #525–#534 slice refactor, so the
formatters live in `src/dartwork_mpl/formatting/`).

## Decisions

- **Axis-wide rule.** `decimals=None` (new default of `format_axis_si/_millions/_billions/_myriad`)
  installs a `ticker.Formatter` subclass (`formatting/_axis_wide.py`). `set_locs` — called by
  `format_ticks` on every draw — settles the unit and the decimal count from the ticks inside the
  view: the fewest decimals that render every scaled tick exactly and distinctly
  (`formatting/_decimals.py:fewest_exact_decimals`). `recommend_tick_decimals` (step rule) is
  not reused for the exact path because a 2.5 step needs one decimal, not zero; it is the
  fallback for irregular values. Called without a draw, a value decides for itself.
- **SI prefix.** One prefix per linear axis from the largest visible `|tick|` (no `800` next to
  `1.2k`). Log/non-linear axes: prefix and decimals per tick (`0.1, 1, 10, 1k`).
- **Myriad.** Each tick keeps its ladder unit (existing behaviour); ticks sharing a unit share
  decimals (`7,500만, 1.00억, 1.25억`). One unit per axis was not adopted (not requested).
- **Zero.** No prefix/suffix/sign; uses the axis decimal count, so `0` on integer axes and
  `0.0` beside `0.5M` (keeps `TICK_DECIMAL` uniformity and the line_signals zero glyph).
- **Explicit `decimals=<int>`** keeps the previous per-tick `FuncFormatter`, byte for byte.
- **Validator.** `TICK_DECIMAL` trailing zero → WARNING naming the formatter option; uniformity
  and precision judged per unit suffix on the rendered numbers. New `VALUE_LABEL_DECIMAL`
  (order 56): all short numeric `ax.texts` labels whole numbers but some print `.0` → WARNING.
- **annotate_value / set_decimal.** `annotate_value` takes a caller string (no number
  formatting); `set_decimal` honours explicit precision only. Neither adds decimals; the add-on
  makes `annotate_value` default to `fontweight=fw(1)` unless `fontweight`/`weight` is passed.

## Tasks

- [x] Formatters + tests (`formatting/tests/test_formatting_auto_decimals.py`).
- [x] Validator + tests (`validate/tests/test_decimal_checks.py`); registry order updated.
- [x] Templates: basic pie `%1.0f%%`; advanced contour levels to the next 0.1 step and one-decimal
      labels; gallery copies synced. A sweep of all 36 templates found no other case.
- [x] Add-on: `annotate_value` weight default + tests; `fw(1)` on advanced bar_grouped per-bar,
      waterfall deltas, tornado end values, line peak callout.
- [x] Docs: CHANGELOG, `docs/api/validate.rst`, `save_export.md`, `docs/api/formatting.rst`.
- [x] PoC before/after (same scale, plus pinned-layout diffs) outside the repo.

## Completion checks (all runnable here)

- `uv run ruff check . && uv run ruff format --check .`, `uv run mypy`.
- Full `uv run pytest` (MCP input tests need a checkout with umask 022).
- `uv run pytest tests/visual/test_visual_pixels.py --mpl --no-cov`: `line_signals` changes
  (`500.0k` → `0.5M`); baseline not regenerated — owner decision.
- `tests/test_shipped_colors_hash.py` unchanged and passing.
