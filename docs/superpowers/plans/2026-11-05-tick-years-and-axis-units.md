# Two-digit tick years and units in the axis label — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make two-digit "period" years (`23.01`, `23.Q1`, `16`), `dm.axis_unit` (unit in the label, plain ticks) and a 만/억/조 default for Korean figures the library defaults, each one line away from the 0.6.0 look.

**Architecture:** Three new `dm.config` fields drive `apply_default_tick_format` (already called by `simple_layout`). Year/period formatters live in a new `formatting/_years.py`; the label-unit formatter and `axis_unit` live in `formatting/_label_unit.py`, built on the existing `AxisUnitFormatter`. Nothing outside `formatting`, `config`, the root exports, docs and skill text changes.

**Tech Stack:** Python ≥3.11, matplotlib ≥3.11 (after PR "matplotlib 3.11 floor"), numpy, pytest, pytest-mpl.

**Spec:** `docs/superpowers/specs/2026-11-05-tick-years-and-axis-units-design.md` (read it first; this plan does not repeat its reasons).

## Global Constraints

- Defaults: `dm.config.tick_years = 2`, `dm.config.date_style = "period"`, `dm.config.number_ladder = "auto"`.
- `dm.config.override(tick_years=4, date_style="concise", number_ladder="si")` restores 0.6.0 tick text on untouched axes (oracle: Task 6 test).
- Year detection for untouched integer x axes: every visible tick an integer in 1900–2099, integer step, ≥2 ticks. Label text is never evidence.
- Two-digit labels that would repeat on one axis → that axis prints four digits.
- Korean ladder only from 1,000,000 (`_UNIT_FROM`); separators from 1,000 as today.
- `format_axis_year` keeps `digits=2`, `locale="ko"` defaults and is not tied to `dm.config`.
- Never override an explicitly chosen formatter (existing `_untouched` / `_stock` rules).
- No meaningless decimals; equal decimals across an axis; one unit per axis; `0` prints `0`.
- Colours, fonts, MCP tool surface unchanged. Boundary checker (`scripts/check_boundaries.py`) must pass.
- Merge only after 0.6.0 is released and the matplotlib 3.11 floor PR is merged (rebase onto it before Task 7).

## Review Focus

1. An untouched x axis of non-year integers inside 1900–2099 (e.g. elevation `1950, 2000, 2050 m`) is indistinguishable from years; the repeat rule keeps it at four digits only when two labels would collide (`50`/`50`). Document the limitation and the opt-out (`dm.config.tick_years = 4` or any explicit formatter) in the `apply_default_tick_format` docstring. (Task 2 test `test_year_axis_rejects_non_integer_and_out_of_range` pins the out-of-range and non-integer cases; `test_century_span_keeps_four_digits` pins the collision case.)
2. A century-spanning axis (1880–2024) must not print repeated `80 … 20`. (Task 2 `test_century_span_keeps_four_digits`.)
3. An axis whose formatter the user set (`DateFormatter("%Y")`, an edited `ConciseDateFormatter`, `FuncFormatter`) must keep it. (Task 3 `test_explicit_date_formatters_survive`.)
4. `axis_unit` on repeated draws / `simple_layout` passes must not stack units (`(조원) (조원)`), and must follow `set_ylim` changes. (Task 4 `test_label_is_idempotent_and_follows_limits`.)
5. `axis_unit` on an all-zero, negative or inverted axis must not crash and must print `0` and U+2212 minus. (Task 4 `test_degenerate_axes`.)

---

### Task 1: Config fields

**Files:**
- Modify: `src/dartwork_mpl/config.py` (class `Config`, docstring Attributes)
- Test: `tests/…` existing config test file if present, else `src/dartwork_mpl/tests/test_config_fields.py`

**Interfaces:**
- Produces: `dm.config.tick_years: Literal[2, 4]`, `dm.config.date_style: Literal["period", "concise"]`, `dm.config.number_ladder: Literal["auto", "si", "myriad"]`; `formatting` reads them at draw/apply time via `from ..config import config`.

- [ ] **Step 1: Failing test** — `test_new_fields_defaults_and_override`: defaults are `2`, `"period"`, `"auto"`; inside `with dm.config.override(tick_years=4, date_style="concise", number_ladder="si")` they change and are restored after; `dm.config.override(tick_year=4)` raises `AttributeError`.
- [ ] **Step 2:** run, expect FAIL (`AttributeError`).
- [ ] **Step 3:** add the three slotted fields with docstrings (one paragraph each: what it changes, the one-line opt-out).
- [ ] **Step 4:** run, expect PASS. **Step 5:** commit `feat(config): tick_years, date_style and number_ladder defaults`.

### Task 2: Year helpers and integer-year axes

**Files:**
- Create: `src/dartwork_mpl/formatting/_years.py`
- Modify: `src/dartwork_mpl/formatting/_defaults.py` (`apply_default_tick_format`, the `_YEARS` branch)
- Test: `src/dartwork_mpl/formatting/tests/test_tick_years.py`

**Interfaces:**
- Produces in `_years.py`:
  - `is_year_axis(ticks: Sequence[float]) -> bool` (Global Constraints rule).
  - `two_digits_repeat(years: Sequence[int]) -> bool` — True when two distinct years share `year % 100`.
  - `class YearTickFormatter(ticker.Formatter)`: `__init__(self, digits: Literal[2, 4], suffix: str = "")`; formats `round(x)` as `f"{y % 100:02d}{suffix}"` or `f"{y}{suffix}"`; in `format_ticks`, falls back to four digits when `two_digits_repeat` of the visible ticks.

- [ ] **Step 1: Failing tests:**
  - `test_untouched_year_axis_two_digits`: line over x=2016…2024 (report preset), `dm.simple_layout(fig)`, x tick texts == `["16", "18", "20", "22", "24"]`.
  - `test_korean_period_year_axis_has_no_suffix`: same with a Korean ylabel → `["16", …, "24"]`; with `date_style="concise"` → `["16년", …]`.
  - `test_year_axis_rejects_non_integer_and_out_of_range`: x 1000…2500 keeps today's text (`1,000 … 2,500` or matplotlib's), x 1900.5…1950.5 untouched.
  - `test_century_span_keeps_four_digits`: x 1880…2024 → four-digit labels, no duplicates.
  - `test_override_four_digits`: `override(tick_years=4)` → `["2016", …]`.
- [ ] **Step 2:** run, expect FAIL.
- [ ] **Step 3:** implement `_years.py`; in `apply_default_tick_format` replace the `_YEARS` skip: when `config.tick_years == 2 and is_year_axis(ticks)` install `YearTickFormatter(2, "년" if korean and config.date_style == "concise" else "")`, else keep current behaviour.
- [ ] **Step 4:** run, expect PASS; also `pytest src/dartwork_mpl/formatting` green. **Step 5:** commit `feat(formatting): two-digit years on untouched year axes`.

### Task 3: Date axes — period and short concise styles, quarters from data

**Files:**
- Modify: `src/dartwork_mpl/formatting/_years.py`, `_defaults.py` (date branch of `apply_default_tick_format`, `KoreanConciseDateFormatter` reuse, `thin_crowded_date_ticks` if quarter locator needs it)
- Test: `src/dartwork_mpl/formatting/tests/test_tick_years.py`

**Interfaces:**
- Produces in `_years.py`:
  - `class PeriodDateFormatter(mdates.ConciseDateFormatter)` with formats `["%y", "%y.%m", "%y.%m.%d", "%H:%M", "%H:%M", "%S.%f"]`, zero_formats `["", "%y.%m", "%y.%m.%d", "%y.%m.%d", "%H:%M", "%H:%M"]`, offset_formats `["", "", "", "%y.%m.%d", "%y.%m.%d", "%y.%m.%d %H:%M"]` (prototype `PeriodYY`, b12/scripts/proto.py:92).
  - `class ShortConciseDateFormatter` (English concise words with `%y`) and Korean variant (`%y년`, months `5월`), both stripping zero padding like `KoreanConciseDateFormatter`.
  - `quarterly(nums: Sequence[float]) -> bool`: ≥2 distinct values, consecutive gaps 89–92 days (prototype `_is_quarterly`).
  - `plotted_dates(ax: Axes, which: Literal["x", "y"]) -> np.ndarray` — x (or y) data of `ax.lines`, collection offsets and bar centres, as date numbers.
  - Quarter labels `23.Q1` in period style; `Q2` (concise, English) / `23년, Q2` (concise, Korean) words; a 3-month locator aligned to Jan/Apr/Jul/Oct, thinned in steps 1/2/4/8 quarters.
  - Century fallback: if `two_digits_repeat` over visible tick years → `%Y` formats.

- [ ] **Step 1: Failing tests** (all through `dm.simple_layout`):
  - `test_monthly_line_period`: monthly line 2023-01…2026-01 (14.5 cm, report) → labels match `^\d\d\.\d\d$` and the first is `23.01`.
  - `test_monthly_line_concise_override`: `date_style="concise"` → contains `"May"` and `"23"`, no `"2023"`; Korean labels → contains `"5월"` and `"23년"`.
  - `test_quarterly_line_period`: 12 quarter-start points 2023Q1…2025Q4 → labels like `23.Q1`; never `23.04`.
  - `test_thinning_never_switches_notation`: same data at 9 cm → every label matches `^\d\d\.Q[1-4]$`.
  - `test_explicit_date_formatters_survive`: `DateFormatter("%Y")`, a ConciseDateFormatter with edited formats, and a `FuncFormatter` are unchanged after `simple_layout`.
  - `test_override_reproduces_concise`: `override(tick_years=4, date_style="concise")` → labels equal matplotlib's stock concise (English) / `KoreanConciseDateFormatter` (Korean) output for the same figure.
  - `test_category_dates_period`: `ax.bar(range(12), …)` + `dm.format_axis_dates(ax, ["2024-01", …, "2024-12"])` → labels start `24.01`; 12 quarter categories 2023Q1…2025Q4 → `23.Q1 …`, thinned in steps 1/2/4/8 at 9 cm keeping Q1 labelled; `format_axis_dates(..., years=4, style="concise")` → today's words.
- [ ] **Step 2:** run, expect FAIL.
- [ ] **Step 3:** implement; in `apply_default_tick_format` replace any stock concise formatter (English or Korean, `_stock`) by the style chosen from `config`; quarter detection reads `plotted_dates`. Extend `format_axis_dates(ax, dates, axis="x", *, years: Literal[2, 4] | None = None, style: Literal["period", "concise"] | None = None)` (`None` → `dm.config`) and `CategoryDateFormatter` to honour them, with quarter steps `(1, 2, 4, 8)` for quarterly categories (prototype `_steps_for`/`_quarter_words`).
- [ ] **Step 4:** PASS + `pytest src/dartwork_mpl/formatting src/dartwork_mpl/layout` green. **Step 5:** commit `feat(formatting): period date ticks with two-digit years`.

### Task 4: `dm.axis_unit` and `dm.axis_unit_of`

**Files:**
- Create: `src/dartwork_mpl/formatting/_label_unit.py`
- Modify: `src/dartwork_mpl/formatting/__init__.py` (`__all__`, re-export), `src/dartwork_mpl/__init__.py` (`__all__`, `EXPERIMENTAL`), `docs/api/formatting.rst`
- Test: `src/dartwork_mpl/formatting/tests/test_axis_unit.py`

**Interfaces:**
- Produces:
  - `MYRIAD_LADDER = (Unit(1, ""), Unit(1e4, "만"), Unit(1e8, "억"), Unit(1e12, "조"), Unit(1e16, "경"))`, `FINANCE_LADDER = (Unit(1, ""), Unit(1e3, "k"), Unit(1e6, "M"), Unit(1e9, "B"), Unit(1e12, "T"))`; SI is the existing `_SI_LADDER`.
  - `class LabelUnitFormatter(AxisUnitFormatter)`: `__init__(self, ladder, unit="max", *, template: str, decimals: int | None = None)`; ticks plain (unit label stripped); on `set_locs` writes `fill(template, unit.label)` to `self.axis.label`; property `unit: Unit | None` (last plan).
  - `fill(template: str, unit: str) -> str` — prototype `_fill` (b12/scripts/proto.py:193): substitute, collapse `( ` / ` )`, drop empty `()`.
  - `axis_unit(ax: Axes, axis: Literal["x", "y"] = "y", *, label: str | None = None, ladder: Literal["auto", "myriad", "finance", "si"] = "auto", scale: str = "max", decimals: int | None = None) -> LabelUnitFormatter`. `label=None` → template `current_label_text + " ({unit})"` captured once at install; a label without `{unit}` → `label + " ({unit})"`. `ladder="auto"` → myriad when `_korean_labels(fig)` at install time, else SI.
  - `axis_unit_of(ax: Axes, axis: Literal["x", "y"] = "y") -> Unit | None` — the installed `LabelUnitFormatter`'s last unit, else `None`.
- [ ] **Step 1: Failing tests** (values from the approved captures, review site `2026-11-05-b2-unit-rule`):
  - `test_max_korean`: bars 5.2e11…9.6e11, `axis_unit(ax, "y", label="매출 ({unit}원)")`, `simple_layout` → y ticks `["0", "0.2", "0.4", "0.6", "0.8", "1.0"]`, ylabel `"매출 (조원)"`.
  - `test_whole_korean`: same with `scale="whole"` → `["0", "2,000", "4,000", "6,000", "8,000", "10,000"]`, `"매출 (억원)"`.
  - `test_fixed_and_finance`: `scale="억"` → label `(억원)`; `ladder="finance", label="Revenue (USD {unit})"` on 3.5e10…7.5e10 → `"Revenue (USD B)"`, ticks `35 … 75`.
  - `test_label_without_placeholder_and_none`.
  - `test_label_is_idempotent_and_follows_limits`: three `simple_layout` calls → label unchanged; `set_ylim(0, 2e9)` then draw → unit `억`.
  - `test_degenerate_axes`: all-zero, negative-only (U+2212), inverted limits.
  - `test_unit_dup_clean`: `dm.validate_figure(fig, checks=("UNIT_DUP",))` → `[]`.
  - `test_axis_unit_of`.
- [ ] **Step 2:** FAIL. **Step 3:** implement. **Step 4:** PASS + `pytest src/dartwork_mpl/formatting tests/architecture` (exports/EXPERIMENTAL/boundaries). **Step 5:** commit `feat(formatting): dm.axis_unit puts the axis unit in its label`.

### Task 5: Korean default ladder

**Files:**
- Modify: `src/dartwork_mpl/formatting/_defaults.py` (`apply_default_tick_format` number branch)
- Test: `src/dartwork_mpl/formatting/tests/test_default_tick_format.py` (add cases)

**Interfaces:**
- Consumes: `MYRIAD_LADDER` (Task 4), `config.number_ladder` (Task 1).

- [ ] **Step 1: Failing tests:** `test_korean_figure_uses_myriad_from_one_million` (5.2e11…9.6e11 → `0.2조 … 1.0조` per capture 4-A; `50,000 … 80,000` unchanged; `3,000,000` → `300만`); `test_english_figure_keeps_si` (`35G`); `test_number_ladder_override_si` (Korean + `number_ladder="si"` → `0.2T`).
- [ ] **Step 2:** FAIL. **Step 3:** choose ladder: `"myriad"` or (`"auto"` and `_korean_labels(fig)`) → `MYRIAD_LADDER`, else `_SI_LADDER`. **Step 4:** PASS. **Step 5:** commit `feat(formatting): Korean figures use 만/억/조 on untouched axes`.

### Task 6: 0.6.0 reproduction oracle, docs and skill

**Files:**
- Test: `src/dartwork_mpl/formatting/tests/test_060_look.py`
- Modify: `CHANGELOG.md` ([Unreleased] → Changed + Added), `docs/migration.md`, the formatting usage page under `docs/usage_guide/`, `src/dartwork_mpl/asset/prompt/03-recipes.md`, `src/dartwork_mpl/skills/dartwork-mpl/references/editing.md`; regenerate `llms-full.txt` with the repo's build hook.

- [ ] **Step 1: Test** `test_override_restores_060_tick_text`: for four figures (monthly English, monthly Korean, integer years, Korean ≥1M bars) under `override(tick_years=4, date_style="concise", number_ladder="si")`, tick texts equal these 0.6.0 strings: `["2023", "May", "Sep", "2024", …]` prefix, `["2023년", "5월", "9월", …]` prefix, `["2016", …, "2024"]`, `["0", "0.2T", …, "1.0T"]`.
- [ ] **Step 2:** PASS (no code change expected; fix code if not).
- [ ] **Step 3:** docs/skill text: one rule — no request → library default; a request → that format — with the three opt-out lines and `dm.axis_unit` examples; `SKILL.md` stays ≤120 lines; run `pytest tests/docs src/dartwork_mpl/skills`.
- [ ] **Step 4:** commit `docs: two-digit years and dm.axis_unit in guides and skill`.

### Task 7: Baselines and PoC (after rebasing onto the matplotlib 3.11 floor PR)

- [ ] **Step 1:** `git rebase t3/mpl311-floor-20261105` (or main after it merges); `pytest tests/visual/test_visual_pixels.py --mpl` → list which scenarios fail (expected: date / year / Korean ≥1M axes only).
- [ ] **Step 2:** render before/after for exactly those scenarios plus the three approved review captures (q, m, y); mark changed tick/label regions (orange 2px box + number) and write per-capture tick-text diffs; publish to the review site and get the user's approval before Step 3.
- [ ] **Step 3:** regenerate only the failing scenarios' baselines; full suite, pre-commit, mypy green; commit `test(visual): baselines for two-digit years and Korean units`.
