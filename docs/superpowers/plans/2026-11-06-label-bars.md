# dm.label_bars and twin-axis series colours — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One call, `dm.label_bars(ax)`, labels every bar correctly (units, decimals, placement, contrast, headroom), twin pairs get series-coloured axes, and `dm.place_legend` stops losing legend details.

**Architecture:** `annotation/_bar_labels.py` creates the label `Text` artists and records a per-axes family; `settle_bar_labels(fig)` (same module) fits text, crowding and headroom and is called by `dm.simple_layout` next to `apply_default_tick_format`. Twin colours live in `formatting/_twin_colors.py` (`apply_twin_colors(fig) -> int`), also called by `simple_layout`. `place_legend` changes stay in `annotation/__init__.py`.

**Tech Stack:** Python ≥3.11, matplotlib ≥3.11 (public `BarContainer`, `ax.bar_label` geometry), numpy, pytest, pytest-mpl.

**Spec:** `docs/superpowers/specs/2026-11-06-label-bars-design.md` (incl. "Calls after the builder check" 1–8). Prototype for reference only: `~/scratch/dartwork-mpl-ideas-20261105/b3/scripts/proto.py`; approved renders `…/b3/img/`.

## Global Constraints

- Label look: `dm.fs(-1)`, `dm.fw(1)`, preset text colour, offset 3 pt.
- Defaults: `where="auto"`, `total="auto"`, `crowded="rotate"`, colour = text colour; twin colours `"series"` (option `dm.config.twin_colors = "neutral"`).
- Labels print like the ticks (spec call 1); decimals: 3 significant digits on the largest |value|, then fewest exact, one count per call, no meaningless `.0`; U+2212 minus.
- Explicit wins: user limits (autoscale off) never changed; explicit colours/`tick_params`/later `Text.set_*` survive repeated `simple_layout`.
- Twin text ≥4.5:1, spines/tick marks ≥3:1 (alpha composited), via `dm.ensure_contrast`.
- No private matplotlib API; MCP surface and colour tokens unchanged; boundaries pass (`scripts/check_boundaries.py`).
- Merge only after 0.7.0 is published (root's go-ahead); base is main 7ce2e7b4 or later.

## Review Focus

1. Zero-height and NaN bars: zero prints `0`, NaN gets no label and no error. (Task 2 `test_zero_and_nan_bars`.)
2. String categories and dates on the bar axis (`ax.bar(["A","B"], …)`, date positions). (Task 2 `test_categorical_and_date_positions`.)
3. `label_bars` without any `simple_layout` call still saves sensible labels (no headroom guarantee). (Task 2 `test_without_layout`.)
4. Log value axis: labels sit outside bar ends, no headroom math on log limits breaks. (Task 4 `test_log_value_axis`.)
5. Bars on the twin axes (`ax2.bar`) with a line on `ax`: labels still land on the top-most axes. (Task 2 `test_bars_on_the_twin`.)

---

### Task 1: Twin-axis series colours

**Files:** Create `src/dartwork_mpl/formatting/_twin_colors.py`; modify `config.py` (field), `formatting/__init__.py`, `layout/__init__.py` (call next to `apply_default_tick_format`); test `src/dartwork_mpl/formatting/tests/test_twin_colors.py`.

**Interfaces:** Produces `apply_twin_colors(fig: Figure) -> int` (number of sides coloured); `dm.config.twin_colors: Literal["series", "neutral"] = "series"` (readers raise `ValueError` naming the field for other values).

- [ ] **Step 1: Failing tests** — `test_bar_and_line_twin_get_series_colours` (left spine/ticks = bar colour composited, label/tick text darkened to ≥4.5:1; right likewise for the line), `test_single_axes_untouched`, `test_multi_hue_side_stays_neutral` (grouped bars on ax), `test_same_hue_both_neutral` (C0/C0), `test_light_alpha_series_spine_reaches_3_to_1` (alpha 0.3 `#c9e8ff` bars), `test_explicit_colours_win` (`tick_params(colors=…)`, `labelcolor=`, `spines[...].set_color`), `test_neutral_option`, `test_repeat_layout_idempotent`.
- [ ] **Step 2:** run, expect FAIL. **Step 3:** implement (a side qualifies when all its data artists share one hue; detect "explicit" by comparing against the rcParams defaults captured at axes creation). **Step 4:** PASS + `pytest src/dartwork_mpl/formatting src/dartwork_mpl/layout tests/architecture`. **Step 5:** commit `feat(formatting): series colours on twin axis pairs`.

### Task 2: `dm.label_bars` — creation, units, decimals, placement

**Files:** Create `src/dartwork_mpl/annotation/_bar_labels.py`; modify `annotation/__init__.py` (re-export), `src/dartwork_mpl/__init__.py` (`__all__`, `EXPERIMENTAL`); test `src/dartwork_mpl/annotation/tests/test_label_bars.py`.

**Interfaces:** Produces `label_bars(ax, bars=None, *, where="auto", total="auto", crowded="rotate", decimals=None, fmt=None, size=None, color=None) -> list[Text]`; per-axes family recorded on the axes for Task 4 (`_dm_bar_label_families: list[BarLabelFamily]`, a small dataclass in the same module with the texts, containers, options).

- [ ] **Step 1: Failing tests** — `test_quarterly_matches_approved` (texts equal `b3/img/report.json` `q/A`), `test_negative_bars_label_below_with_minus` (`−3.5`), `test_barh_left_for_negatives`, `test_axis_unit_max_and_whole` (`0.523…` under 조원; `5,234…` under 억원), `test_default_si_suffix_follows_ticks` (`33G`), `test_percent_formatter_follows_ticks`, `test_fmt_string_and_callable` (`"${}B"` → `$38.5B`; callable gets the scaled value), `test_decimals_rule` (`21.4`/`18.0` beside `21.5`; whole numbers no `.0`), `test_color_series_option`, `test_zero_and_nan_bars`, `test_categorical_and_date_positions`, `test_without_layout`, `test_bars_on_the_twin`, `test_returns_texts_and_later_edits_survive`.
- [ ] **Step 2:** FAIL. **Step 3:** implement on `BarContainer` geometry (`datavalues`, orientation); texts added to the top-most twin with the bar axes' `transData`. **Step 4:** PASS. **Step 5:** commit `feat(annotation): dm.label_bars places value labels on bars`.

### Task 3: Stacks, totals, inside ink

**Files:** Modify `annotation/_bar_labels.py`; test `test_label_bars.py`.

**Interfaces:** Consumes Task 2's family; produces stack detection used by Task 4.

- [ ] **Step 1: Failing tests** — `test_stack_segments_and_totals_match_approved` (`s/A` texts), `test_total_only_and_off`, `test_short_segment_label_hidden`, `test_mixed_sign_stack_net_total_side`, `test_waterfall_is_not_a_stack` (floating bars: no totals), `test_inside_ink_by_contrast` (`#1686e0` → black), `test_grouped_and_stacked_layout`.
- [ ] **Step 2:** FAIL. **Step 3:** implement spec call 3 (bottoms equal the running top). **Step 4:** PASS. **Step 5:** commit `feat(annotation): stacked bar segments and totals`.

### Task 4: Settle in `simple_layout` — crowding and headroom

**Files:** Modify `annotation/_bar_labels.py` (`settle_bar_labels(fig) -> int`), `layout/__init__.py` (call it before margins are measured), `scripts/check_boundaries.py` if a new edge is needed (with reason); test `test_label_bars.py`.

**Interfaces:** Produces `settle_bar_labels(fig: Figure) -> int` (families settled).

- [ ] **Step 1: Failing tests** — `test_dense_24_rotated_all_kept_no_overlap` (approved `d/A`; top label ≥ 0 px inside axes), `test_crowded_skip_and_inside`, `test_barh_thin_rows_skip_alternate`, `test_headroom_grows_only_autoscaled_limit` (no `*1.15`; ratio ≈ approved), `test_user_limits_respected_label_outside_margin_reserved`, `test_log_value_axis`, `test_repeat_simple_layout_idempotent`, `test_validate_figure_clean_on_six_charts`.
- [ ] **Step 2:** FAIL. **Step 3:** implement spec "Crowding"/"Headroom" and calls 4 and 8. **Step 4:** PASS + `pytest src/dartwork_mpl/layout src/dartwork_mpl/annotation tests/architecture`. **Step 5:** commit `feat(annotation): bar labels settle crowding and headroom in simple_layout`.

### Task 5: `place_legend` keeps legend details; lint rule

**Files:** Modify `annotation/__init__.py` (`place_legend`, `_merge_twin_legends`), lint catalog (`src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml` + `lint/` detector per existing pattern); tests `annotation/tests/test_place_legend_twin.py`, lint tests.

- [ ] **Step 1: Failing tests** — `test_rebuild_on_top_twin_keeps_title_and_handler_map`, `test_tuple_handles_legend_left_untouched`, `test_hand_merge_pattern_is_linted` (`h1, l1 = ax.get_legend_handles_labels(); … ax.legend(h1 + h2, l1 + l2)` → rule suggests `dm.place_legend(ax)`).
- [ ] **Step 2:** FAIL. **Step 3:** implement spec call 7. **Step 4:** PASS + lint tests. **Step 5:** commit `fix(annotation): place_legend keeps legend details on twin pairs`.

### Task 6: Docs, skill, changelog

**Files:** `docs/api/` (label_bars autodoc), `docs/usage_guide/` page section, `src/dartwork_mpl/asset/prompt/03-recipes.md`, skill `references/editing.md` (≤120-line `SKILL.md` one line if any), `CHANGELOG.md` [Unreleased], `llms-full.txt` via the repo hook.

- [ ] Rule text: "no request → `dm.label_bars(ax)` defaults; a request → that keyword"; replace hand-written label loops in examples the skill shows. Run `pytest tests/docs src/dartwork_mpl/skills` and the `-W` docs build. Commit `docs: dm.label_bars and twin colours in guides and skill`.

### Task 7: Baselines and PoC

- [ ] **Step 1:** `pytest tests/visual/test_visual_pixels.py --mpl` → list scenarios that change (expected: `dual_axis_timeseries` from twin colours; any template using twins).
- [ ] **Step 2:** render before/after for those scenarios and the six approved charts with the real implementation next to the approved prototype images (boxed, numbered, tick/label texts listed); publish on the review site; get the user's approval.
- [ ] **Step 3:** regenerate only the approved baselines; full suite, pre-commit, mypy (`--no-sync`), boundaries green; commit `test(visual): baselines for bar labels and twin colours`.
