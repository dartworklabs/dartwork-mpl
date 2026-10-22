# Plan — #523 no meaningless decimals (formatters, validator, templates)

User instruction (2026-10-22): "의미없는 소수점은 항상 신경쓰도록해. 전부 정수인데 소수점 넣을
이유가 없어." Integer ticks and value labels never print decimals (`200.0` → `200`,
`1.0k` → `1k`); fractional steps keep one decimal count on every tick (`17.5, 20.0, 22.5`).
Add-on (same day): numeric value labels on bars and lines are one weight step heavier
(`fontweight=dm.fw(1)`). Nothing else about the visual style changes.

Base: `origin/main` 2fa337c4 (contains the #525–#538 slice and typing refactor, so the
formatters live in `src/dartwork_mpl/formatting/`).

## Decisions

- **Axis-wide rule.** `decimals=None` (new default of `format_axis_si/_millions/_billions/_myriad`)
  installs a `ticker.Formatter` subclass (`formatting/_axis_wide.py`). `set_locs` — called by
  `format_ticks` on every draw — settles the unit and the decimal count from the ticks inside the
  view: the fewest decimals that render every scaled tick exactly and distinctly
  (`formatting/_decimals.py:fewest_exact_decimals`). `recommend_tick_decimals` (step rule) is
  not reused for the exact path because a 2.5 step needs one decimal, not zero; it is the
  fallback for irregular values. Called without a draw, a value decides for itself.
- **Unit (user decision 2026-10-22: "최대 단위를 기준으로 잡거나, 일관된 단위를 잡는 거 …
  그래야 자리수가 직관적임").** An axis never mixes units. `format_axis_si` / `_myriad` take
  `unit=`: `"max"` (default) is the unit of the largest visible tick (`0, 0.2k … 1.2k`;
  `0, 0.25억 … 1.75억`); `"whole"` is the integers-first rule tried in round 2 (`0, 200 …
  1,200`); a ladder label fixes the unit. One `AxisUnitFormatter` serves all four helpers
  (millions/billions are a one-rung ladder). Log axes: unit and decimals per tick.
- **Zero.** Always a bare `0`; TICK_DECIMAL treats a bare `0` as unit-less, so
  `-1.0M, -0.5M, 0, 0.5M, 1.0M` validates clean.
- **Explicit `decimals=<int>`** keeps the previous per-tick `FuncFormatter`, byte for byte.
- **Validator.** `TICK_DECIMAL` trailing zero → WARNING naming the formatter option; uniformity
  and precision judged per unit suffix on the rendered numbers. New `VALUE_LABEL_DECIMAL`
  (order 56): all short numeric `ax.texts` labels whole numbers but some print `.0` → WARNING.
  Details are one `TypedDict` per variant (TICK_DECIMAL carries a `reason` literal) built with
  `_detail.wire`; the fix handlers read them back with `_detail.choice` / `number` (#537).
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
- `uv run pytest tests/visual/test_visual_pixels.py --mpl --no-cov`: only `line_signals`
  changes; its regeneration is a separate last commit, kept or dropped on PoC approval.
- `tests/test_shipped_colors_hash.py` unchanged and passing.
