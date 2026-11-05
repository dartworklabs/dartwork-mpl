# Two-digit tick years and units in the axis label

Date: 2026-11-05. Status: decisions taken by the user on the review site
(`2026-11-05-b1-year-default`, `-b1-year-look`, `-b2-unit-rule`, `-b2-kr-default`);
this note records the shape for the builder. Ships after 0.6.0 (a look change: 0.7.0).

## Why

The largest downstream user (company-analysis + valuation) rebuilt two things on top
of dm because dm's defaults disagree with how the user wants figures to read:

- **Years.** The user's rule (2026-10-06): tick years are always two digits
  (`25`, `25.Q2`, `25.07`). An audit of 1,586 committed SVGs found 6,519 four-digit
  year ticks, 5,498 of them from dm's default date formatter. Downstream keeps an
  831-line `year_ticks.py` that rewrites dm's formats after the fact. That rewrite
  also makes dm treat the formats as user-chosen, so Korean date words are skipped
  (`23, May, Sep` instead of `23년, 5월`).
- **Units.** The downstream rule puts the unit in the axis label (`매출 (억원)`) and
  plain numbers on the ticks. dm's default puts SI suffixes on ticks (`0.2T` on a
  Korean money axis) and its own `UNIT_DUP` check then flags the label. dm's
  `format_axis_*` helpers are called 0 times downstream; instead there are 647 manual
  `/1e8`·`/1e12` divisions and 66 calls to a local `resolve_axis_unit`.

## The principle (user, 2026-11-05)

"근사하게 제공하는 기본값은 있지만 사용자 프롬프트에 따라서 유연하게 대응하는 게 이
리포의 핵심이야." Every decision below sets only what appears when nobody asks.
Every alternative is one argument or one config line away, and nothing in the library
pushes an explicit request back toward the default (no check flags a requested format).

## Decisions

| id | decision | default after this change | alternatives kept |
|---|---|---|---|
| B1-1 | two-digit years are the default | on | four digits, one line |
| B1-2 | notation when on: "period" (L2) | `23.01 · 23.05`, `23.Q1 · 23.Q3`, `16 … 24` | concise words with short years (`23, May`; `23년, Q2`), today's look |
| B2-1 | unit-in-label rule: largest tick's unit ("max") | `0, 0.2 … 1.0` + `매출 (조원)` | "whole" (`0, 2,000 … 10,000` + `(억원)`), a fixed unit (`"억"`, `"M"`) |
| B2-2 | Korean figures' default tick unit ladder: 만/억/조 | `0.2조 … 1.0조` | SI (`0.2T`), label mode |

Not changed: English figures keep SI on untouched axes (`35G`): on an axis that may
not be money, G is the correct SI prefix. Money ladders (`B`) come from `dm.axis_unit`.

## API

### Years (B1)

New `dm.config` fields (the existing slotted `Config`, so typos raise, and
`dm.config.override(...)` scopes them):

- `tick_years: Literal[2, 4] = 2`
- `date_style: Literal["period", "concise"] = "period"`

`dm.config.override(tick_years=4, date_style="concise")` reproduces 0.6.0 exactly
(test: pixel-identical to the 0.6.0 render of every date baseline).

Where they apply (all through `apply_default_tick_format`, which `simple_layout`
already calls, and the explicit helpers):

1. Concise date axes (`date.converter: concise`, untouched). "period": monthly
   `23.01`, daily `23.01.15`, yearly `23`. "concise": matplotlib's concise words with
   `%y` years (`23, May, Sep`), Korean words in Korean figures (`23년, 5월`).
   Quarter labels (`23.Q1`) on a real date axis come from the **data**, not the
   tick step: when every plotted x value of the axis's artists sits on a quarter
   start (or quarter end) the axis reads quarters; otherwise months. Thinning
   changes how many labels show, never the notation (no `23.Q1` ↔ `23.05` flips).
2. Integer-year x axes, today left as `2024`: `24` when `tick_years=2`, only when
   every visible tick is an integer in **1900–2099** with an integer step (the
   approved prototype's rule). Axes outside that (a wavelength axis `1000 … 2500`)
   keep today's behaviour. Label text is not used as evidence.
3. `dm.format_axis_dates` (category dates under bars): same styles; quarterly data
   thins in steps 1/2/4/8 so Q1 stays labelled.
4. `dm.format_axis_year`: unchanged signature and defaults (`digits=2`,
   `locale="ko"` → `25년`). It is an explicit call, so it is not tied to
   `dm.config`; the 0.6.0-reproduction promise covers untouched axes only.

Repeated two-digit labels are never drawn: when an axis spans a century (two
different years would print the same two digits, e.g. 1880–2024) it falls back to
four digits on its own. In "period" style a Korean figure's integer-year axis reads
`24` (no `년`), matching the user's table; "concise" keeps `24년`.

Per-axis overrides: `years=` and `style=` keywords on `format_axis_dates` and
`format_axis_year`; any explicit `ax.xaxis.set_major_formatter(...)` is left alone
(the existing `_untouched`/`_stock` rules). Korean detection stays the existing rule
(`_korean_labels`: Hangul in labels, titles or legend), the same one that picks
Korean date words today.

The downstream `%Y→%y` rewrite becomes unnecessary; the bug it causes (Korean words
skipped) disappears because dm itself writes the short year.

### Units in the label (B2-1)

```python
dm.axis_unit(ax, "y", label="매출 ({unit}원)")            # 0, 0.2 … 1.0 + 매출 (조원)
dm.axis_unit(ax, "y", label="Revenue (USD {unit})", ladder="finance")  # M, B, T
dm.axis_unit(ax, "y", label="매출 ({unit}원)", scale="whole")          # (억원), integer ticks
dm.axis_unit(ax, "y", label="매출 ({unit}원)", scale="억")             # fixed
dm.axis_unit_of(ax, "y")   # -> Unit chosen at the last draw (for value labels)
```

- `ladder`: `"auto"` (myriad 만/억/조 in Korean figures, SI otherwise), `"myriad"`,
  `"finance"` (k, M, B, T), `"si"`.
- `scale`: `"max"` (default), `"whole"`, or a unit symbol on the ladder.
- `label`: a template with `{unit}`; without the placeholder the unit is appended in
  parentheses; `None` keeps the current label text and appends ` ({unit})`.
- Ticks: plain numbers; fewest decimals that show every tick exactly, the same count
  on every tick, `0` for zero, thousands separators. One unit per axis, chosen at
  draw time so zoom and limit changes keep label and ticks consistent.
- Built on the existing `AxisUnitFormatter`; the formatter rewrites the label text
  in its draw-time hook. `UNIT_DUP` must report 0 findings on the result.

### Korean default ladder (B2-2)

`apply_default_tick_format` installs `DefaultNumberFormatter` with the myriad ladder
(만, 억, 조) instead of SI when `_korean_labels(fig)` is true. Same thresholds as
today: separators from 1,000 and a unit only from **1,000,000** (`_UNIT_FROM`), so a
Korean stock-price axis `50,000 … 80,000` is unchanged and `3,000,000` reads `300만`.
New field
`dm.config.number_ladder: Literal["auto", "si", "myriad"] = "auto"` restores SI in
one line.

## Non-goals

- A check that flags four-digit years. With two digits as the default, a four-digit
  axis is either a request or an explicit formatter; flagging it would fight the user.
- Guessing the unit from label text (`매출 (원)` → `(조원)`) on untouched axes, and an
  "off" mode with full digits: both rejected on the review page (guessing, unreadable).
- English money B instead of G by default; MCP tool surface (frozen); value-label
  helpers (separate work, they will read `axis_unit_of`).

## Anti-goals

- Units switching from tick to tick; meaningless decimals (`200.0`); a default that
  cannot be turned off in one line; any change to colours or fonts.

## Compatibility and evidence

- Look change on every figure with a date or year axis, and on Korean figures with
  axes ≥ 1M. Pixel baselines that contain such axes are regenerated in the same PR,
  shown before/after on the review site and approved first (repo rule: visual
  changes ship with PoC). `dm.config.override(tick_years=4, date_style="concise",
  number_ladder="si")` is tested to be pixel-identical to 0.6.0.
- CHANGELOG `Changed` entry with the one-line opt-out; migration note.
- Skill and prompt corpus: one rule — "no request → library default; a request →
  that format" — with the opt-out lines next to it (`references/editing.md`,
  `03-recipes.md`), so agents do not hand-roll `/1e8` or `%Y` rewrites.

## Tests (executable here)

- Formatter units: monthly / daily / yearly / quarterly period labels; quarter
  thinning keeps Q1; Korean concise words with short years; four-digit override.
- `axis_unit`: max / whole / fixed on myriad, finance, si; decimals rules (no `.0` on
  integer axes, equal decimals, `0`), label templates, draw-time relabel after
  `set_ylim`, `UNIT_DUP` = 0, `axis_unit_of`.
- Defaults: Korean figure ≥1M → 만/억/조; English unchanged; config override restores
  0.6.0 pixels.
- Prototype renders already exist (`~/scratch/dartwork-mpl-ideas-20261105/b12/`):
  the implementation must reproduce the approved captures' tick texts.

## Calls made after the builder check (not asked of the user)

Year-axis detection range 1900–2099 with integer steps; quarters decided by the data;
four-digit fallback when two-digit labels would repeat; Korean ladder only from
1,000,000; `format_axis_year` keeps its explicit defaults. Each can be revisited from
the PoC renders before merge.

## Left to the builder

Module placement inside `formatting` (respect `scripts/check_boundaries.py`), the
period formatter's tick thinning at narrow widths (keep labels ≥1 em apart as
`thin_crowded_date_ticks` does), and whether `format_axis_myriad/si` gain a
`unit_in="label"` shortcut over `axis_unit` (optional sugar, not required).
