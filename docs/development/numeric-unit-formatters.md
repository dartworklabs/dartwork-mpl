---
orphan: true
---

# Numeric-unit formatters: one engine and its contract map (D4)

Root decision D4: converge the numeric-unit implementations on one formatter
engine, prefer `axis_unit` / `axis_unit_of`, and promote a canonical API or
start dated deprecations only once an exact mapping of arguments, output,
label, precision, locator and scale exists. This page is that mapping, after
the internal merge. Nothing public was promoted, renamed or deprecated.

## One engine, two modes

`AxisUnitFormatter` (`formatting/_axis_wide.py`) is the only formatter class
behind `format_axis_millions`, `_billions`, `_currency`, `_si`, `_myriad`,
`axis_unit` (its subclass `LabelUnitFormatter`) and the library's default
numbers (`DefaultNumberFormatter`). It has two modes:

- **Axis-wide**: at every draw the visible ticks choose one unit and one
  decimal count for the axis. `tick_scale_of` reports that unit, so
  `dm.label_bars` prints like the ticks.
- **Per value** (`per_tick=TickText(...)`): no axis decision; each value is
  written alone with fixed decimals. `tick_scale_of` reports the plain
  scale. `TickText` holds the only rules that differ: thousands separators,
  the zero rule (`"bare"`, `"affixed"`, `"exact"`) and myriad's `compact`.

| Call | Mode | Ladder / unit | Text rules |
|---|---|---|---|
| `millions` / `billions`, `decimals=None` | axis-wide | one rung: `1e6` / `1e9`, label `suffix` | engine |
| `millions` / `billions`, `decimals=n` | per value | the same rung | `TickText(separators=False)` |
| `currency` (always) | per value | one rung `1`, symbol as currency or label | `TickText(zero="affixed")` |
| `si`, `decimals=None` or `unit` not `"max"` | axis-wide | none/k/M/G/T | engine |
| `si`, `decimals=n`, `unit="max"` | per value | its own prefix | `TickText(separators=False)` |
| `myriad`, `decimals=None` or `unit` not `"max"` | axis-wide | none/만/억/조/경 (zh, ja) | engine |
| `myriad`, `decimals=n`, `unit="max"` | per value | its own unit | `TickText(zero="exact", compact=True)` |
| `axis_unit` | axis-wide, unit in label | si, finance (k/M/B/T) or myriad (ko) | engine, no suffix |

Before this change the per-value rows of millions, billions, si and
currency were separate `FuncFormatter` closures (myriad moved in #601).

All five `format_axis_*` functions stay supported public API; none is
deprecated, and `axis_unit` / `axis_unit_of` remain EXPERIMENTAL with a
different purpose (the unit in the axis label). They are thin frontends
over the one engine, not duplicate implementations.

**Moving off the old attributes.** The installed formatter is no longer a
`FuncFormatter`, so its `.func` and `set_offset_string` are gone. A caller
that relied on them installs a native one itself, for example
`ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(f))`, after
(or instead of) the `format_axis_*` call. No shim is provided.

## Mapping

Evidence keys: `G:` a case id of `formatting/tests/number_formatters_golden.tsv`
(and the range key in it), `C:` a test in
`formatting/tests/test_number_formatter_contract.py`, `T:` a test in
`formatting/tests/test_tick_scale.py`. All of them pass on main `d952266b`
and after the merge.

### Arguments and defaults

| Function | Signature | Returns |
|---|---|---|
| `format_axis_millions` | `(ax, axis="y", suffix="M", decimals=None)` | `None` |
| `format_axis_billions` | `(ax, axis="y", suffix="B", decimals=None)` | `None` |
| `format_axis_currency` | `(ax, axis="y", symbol="$", position="prefix", decimals=0)` | `None` |
| `format_axis_si` | `(ax, axis="y", decimals=None, unit="max")` | `None` |
| `format_axis_myriad` | `(ax, axis="y", *, locale="ko", decimals=None, currency="", unit="max")` | `None` |
| `axis_unit` (experimental) | `(ax, axis="y", *, label=None, ladder="auto", scale="max", decimals=None)` | `LabelUnitFormatter` |

Returns: `C: test_return_label_locator_and_limits`.

### Tick text

| Rule | millions / billions | currency | si | myriad | axis_unit |
|---|---|---|---|---|---|
| precision, `None` | fewest exact, one count per axis: `0, 0.25M … 1.25M` (G: `millions\|y\|` 0..1.25e+06) | n/a (`decimals=0` default) | same: `−3.0M … 3.0M` (G: `si\|y\|`) | same: `0.5亿` (G: `myriad\|y\|locale='zh'`) | same, no suffix: `0, 0.25 … 1.25` under `(M)` (G: `axis_unit\|y\|ladder='si'`) |
| precision, `n` | `n` places per value; can repeat: `1.0M ×6` (G: `millions\|y\|decimals=1` 999000..) | `n` places | `unit="max"`: `n` places, own prefix: `800.0`, `1.0k` (G: `si\|y\|decimals=1`); other unit: `n` on every tick (G: `unit='M'`) | `unit="max"`: `n` places, zeros trimmed: `1.2만` (G: `myriad\|y\|decimals=1`) | `n` on every tick: `0.0, 0.7 … 3.4` (G: finance case) |
| zero | `None`: `0`; `n`: `0.0` bare, never `-0.0M` | `$0`, `0.00€`, never `-$0` (G: `currency\|y\|` -1..1) | `None`: `0`; `n`: `0.0` | `None`: `0`; `n`: exact zero `0`, else sign and currency kept: `-0`, `-$0` | `0` |
| negative | `None`: U+2212 (`-` when `axes.unicode_minus` is off); `n`: always `-` (G: `ascii minus`) | `-$1,500`, sign before symbol, always `-` | as millions | `None`: `−$300万`; `n`: `-125만` | U+2212 / rc |
| unit on tick | `suffix`, any text (`bn`, `백만`, `""`) | none | k/M/G/T by `unit` rule | 만/억/조/경; zh 万/亿/兆/京; ja 万/億/兆/京 | none (in label) |
| currency | none | `symbol` prefix or suffix (any `position` but `"prefix"` is suffix) | none | `currency=` after the sign | none (label template only) |
| separators | `None`: yes; `n`: no (`1360.0M`) | yes | `None`: yes; `n`: no (`1000.0k`) | yes | yes |
| boundary | fixed unit | none | `None`: `999.9999999` → `1k` (tolerance); `n`: `1000.0` (exact) | `n`: exact; `9,999.5` → `10,000` | as axis-wide |
| non-finite | `inf`; `n`: `infM`, `nanM` | `$inf`, `$nan` | `inf`; `n`: `infT`, `nan` | `inf`; `n`: `inf경`, NaN raises `ValueError` | `inf`, `nan` |
| locale | none | none | none | `ko` / `zh` / `ja`, else `ValueError` | `ladder="auto"`: myriad when the figure's text is Korean, else SI |

### Axis, label, locator, scale, draw

| Item | millions / billions / currency / si | myriad | axis_unit | Evidence |
|---|---|---|---|---|
| axis label | untouched | untouched | written at every draw: `Value (M)`; a `{unit}` template fills in (`인구 ({unit}명)` → `인구 (억명)`); shared axes too | C: `test_return_label_locator_and_limits`; G: axis_unit ranges `label=` |
| locator, limits | untouched; one someone set stays | same | same | C: same test |
| `axis` values | `x`, `y`, `both`; any other name: silently nothing | `x`, `y`, `both`; other: `ValueError` | `x`, `y`; `both`: `ValueError` | C: `test_helpers_take_both…`, `test_axis_unit_takes_x_or_y_only` |
| negative `decimals` | accepted; `ValueError` at the draw | `ValueError` at the call | `ValueError` at the call | C: `test_negative_decimals_fail…` |
| log scale | axis-wide: unit per tick (`1, 10 … 1k`); millions/billions keep their unit (`0.000001M`); per value and currency: as linear | axis-wide: unit per tick | whole values, label without unit | G: `y log` |
| zoom / redraw | axis-wide: decided again; per value: each value alone | same | decided again, label rewritten | G: ranges are `format_ticks` under set views |
| bar labels | axis-wide: tick suffix (`1.25M`); per value and currency: plain (`1,250,000`) | axis-wide: `125만`; per value: plain | scaled, no suffix (`1.25`) | T: `test_value_alone_formatters_give_the_plain_scale`, `test_suffix_formatters_give_unit_and_currency`, `test_axis_unit_scale_has_no_suffix` |
| installed class | `AxisUnitFormatter`, one per axis | same | `LabelUnitFormatter` | this change |

## Where `axis_unit` is the same

With the same ladder and rule the engine chooses the same unit and decimals,
so `axis_unit` prints the same numbers and moves the unit into the label:
`format_axis_millions()` = `axis_unit(ladder="si", scale="M")`,
`format_axis_billions()` = `axis_unit(ladder="finance", scale="B")`,
`format_axis_si(unit=u, decimals=d)` = `axis_unit(ladder="si", scale=u,
decimals=d)` (except `decimals=n` with `unit="max"`), Korean
`format_axis_myriad(unit=u)` = `axis_unit(ladder="myriad", scale=u)`, on
linear axes.

## Gaps: what `axis_unit` cannot do today

These decide whether `axis_unit` can be promoted as the replacement and what
a dated deprecation would change for callers.

1. **Unit on the ticks.** All five helpers print the unit (or symbol) on
   every tick and never touch the label. `axis_unit` always moves the unit
   into the label and rewrites the label at every draw.
2. **Currency on ticks.** `format_axis_currency` (prefix or suffix, symbol
   kept on zero) and `format_axis_myriad(currency=)` have no `axis_unit`
   form; the label template is the only place for a currency.
3. **Free suffix, one fixed unit.** `suffix="bn"`, `"백만"`, `""`: `scale`
   must be a symbol of a built-in ladder.
4. **zh / ja myriad ladders.** `ladder="myriad"` is Korean only.
5. **Per-value text.** `decimals=n` with `unit="max"` (si, myriad): a unit
   per tick; no separators and hyphen-minus (millions, billions, si);
   myriad's trimmed zeros, whole values under 만 and exact-zero rule. There
   is no per-value mode in `axis_unit`.
6. **`axis="both"`.** `axis_unit` takes one axis per call.
7. **Error contract.** Four helpers ignore an unknown `axis` and fail at the
   draw on a negative `decimals`; `axis_unit` raises at the call.
8. **Bar labels.** Under the helpers `dm.label_bars` shows the tick suffix or
   plain values; under `axis_unit`, scaled numbers without a unit.
9. **Log axes.** si and myriad print a unit per tick and millions/billions a
   fixed unit; `axis_unit` prints whole values and drops the unit.

## Changing these tests

`number_formatters_golden.tsv` was generated from main `d952266b` before the
merge (`python src/dartwork_mpl/formatting/tests/test_number_formatters_grid.py`).
Regenerate it only for an intended output change, decided by a person and
named in `CHANGELOG.md`; never to make a failing test pass. The same holds for
`myriad_decimals_golden.tsv` and the contract test.
