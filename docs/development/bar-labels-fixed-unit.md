---
orphan: true
---

# Bar labels under fixed-unit tick formatters

Status: decided, 2026-11-07: the user chose B (the label decimal rule) on
the before/after PoC review (item 10). Sources: root decision D4 ("D4
decision after PR604's exact mapping", API-DECISIONS-20261106) and call 1 of
the label-bars design (`docs/superpowers/specs/2026-11-06-label-bars-design.md`:
"labels print like the ticks").

## Problem

`format_axis_millions(ax, decimals=1)`, `format_axis_billions(ax,
decimals=2)` and `format_axis_currency(ax)` print ticks such as `1.0M`,
`0.50B`, `$1,000`, but `dm.label_bars` printed the bare value beside them:
`1,250,000`, `12,400,000,000`, `1,250`. These paths write each tick alone
(`AxisUnitFormatter(per_tick=...)`), and `AxisUnitFormatter.scale_for`
returned the plain `TickScale()` for every such formatter (D4 review,
Minor 2). Main (`bd2b61f8`) prints the same.

## Scope

In scope: per-value formatters with **one fixed unit**.

- `format_axis_millions(decimals=n)`, `format_axis_billions(decimals=n)`,
  any `suffix` (`M`, `B`, `bn`, ` 백만`, `""`).
- `format_axis_currency(...)` (always per value), symbol before or after.

Unchanged:

- Per-value formatters whose values each take **their own unit**:
  `format_axis_si(decimals=n)` and `format_axis_myriad(decimals=n)` with
  `unit="max"` (`800.0` beside `1.2M`). No unit is the axis's, and D4 forbids
  inventing one; their labels stay plain values.
- Axis-wide formatters (they already report their unit), `dm.axis_unit`,
  `PercentFormatter`, any other formatter.
- Tick text: no formatter output changes (the golden TSVs stay as they are).

## Tick text, executed

`b9e028ab`, report preset, the installed formatter called on each value:

| Call | negative | rounds to 0 | 0 | positive | ≥ 1000 units |
|---|---|---|---|---|---|
| `format_axis_millions(decimals=1)` | `-1.2M` | `0.0` | `0.0` | `1.2M` | `1360.0M` |
| `format_axis_billions(decimals=2)` | `-0.45B` | `0.00` | `0.00` | `1.23B` | `1500.00B` |
| `format_axis_billions(suffix="bn", decimals=0)` | `-2bn` | `0` | `0` | `12bn` | `1500bn` |
| `format_axis_currency()` | `-$800` | `$0` | `$0` | `$1,250` | `$2,050` |
| `format_axis_currency("€", "suffix", decimals=2)` | `-8.00€` | `0.00€` | `0.00€` | `20.55€` | `1,234.50€` |
| `format_axis_si(decimals=1)` (out) | `-1.2M` | `-40.0k` | `0.0` | `800.0` | `1.2M` |
| `format_axis_myriad(decimals=1)` (out) | `-1.2억` | `-0` | `0` | `7,500` | `1.2억` |

Values: millions −1.25e6, −4e4, 0, 1.25e6, 1.36e9; billions −0.45e9,
−4e6, 0, 1.234e9, 1.5e12; `bn` −2e9, −4e8, 0, 1.2e10, 1.5e12; `$` −800,
−0.4, 0, 1250, 2050.5; `€` −8, −0.004, 0, 20.55, 1234.5; si −1.25e6, −4e4,
0, 800, 1.25e6; myriad −1.25e8, −0.2, 0, 7500, 1.25e8.

Read off the table: the sign goes before the currency (`-$800`, never
`$-800`); the symbol sits where `position` puts it; millions and billions
drop sign and unit on zero (`bare`: `0.0`), currency keeps the symbol and
drops the sign (`affixed`: `$0`, `0.00€`); the minus is the hyphen-minus
and millions/billions print no thousands separators (both kept from the
pre-engine `FuncFormatter` output for parity).

## Rules

`tick_scale_of` reports the fixed unit as a `TickScale`: factor, currency
prefix, unit label (or a suffix symbol) and the zero rule. Labels take from
the ticks:

1. **Unit.** The value divided by the unit's factor, the unit label after
   it: `1.25M`, `12.4B`, `12bn`, `1.2 백만`.
2. **Currency.** The symbol on the ticks' side: `$1,250`, `1,250€`.
3. **Sign.** Before currency and number, as on the ticks: `−$800`,
   `−800€`, `−0.80M`.
4. **Zero.** The ticks' rule. Millions/billions (`bare`): no sign, no unit
   (`0`, or `0.0` when the count is fixed). Currency (`affixed`): the symbol
   stays, the sign goes (`$0`, `0€`). A non-zero value that rounds to zero
   under the count in force prints as zero (0.03M beside 12.5M: `0`).

Labels keep their own rules where the ticks only keep legacy parity:

5. **Minus glyph.** Matplotlib's minus (U+2212 unless `axes.unicode_minus`
   is off), as every other label, the axis-wide ticks and the label-bars
   design. The per-value ticks keep their hyphen-minus (D4: tick output
   unchanged).
6. **Separators.** Always (`1,360M`), as every other label.
7. **Text the caller writes.** `fmt="{} mn"` gets the number in the tick
   unit and adds no suffix or currency; a `fmt` callable gets the scaled
   value and returns the whole text.
8. **Follows.** The scale is re-read at each draw: a formatter installed
   after `label_bars` moves the labels at the next draw.

## Precision priority

The precision the caller gives the labels always wins; the formatter's
`decimals=n` sizes tick text and never the labels:

1. A `fmt` format spec (`"{:.3f} mn"`) or a `fmt` callable writes the number.
2. `label_bars(decimals=k)`: `k` places in the tick unit, fewer or more than
   the ticks' (`1M` or `1.250M` under `decimals=1` ticks; zero `0.000`,
   `$0.00`, `0€`).
3. Nothing asked: the label rule below.

## Decision: B, the label rule (user, 2026-11-07)

With nothing asked, the labels take the label rule in the tick unit: three
significant digits on the largest `|value|`, cut to the fewest decimals that
print every value exactly, one count per call, zero `0`. It is the rule
every other formatter's labels use: `format_axis_millions(decimals=1)` now
labels exactly as `format_axis_millions()` and `format_axis_si(unit="M",
decimals=1)` do (ticks `1.0M`, labels `1.25M`).

Not chosen: A, labels in the formatter's fixed `decimals` (`1.2M`, `0.0`,
`$4` for $4.25; cents kept as `20.55€`).

Labels of the PoC data (before = main; `−` is U+2212):

| Formatter (values) | before | after |
|---|---|---|
| millions `d=1` (1.25e6, 2.05e6, −0.8e6, 0, 3.4e6) | `1,250,000` `2,050,000` `−800,000` `0` `3,400,000` | `1.25M` `2.05M` `−0.80M` `0` `3.40M` |
| billions `d=2` (12.4e9, 8e9, −3.5e9, 0, 15e9) | `12,400,000,000` … `0` | `12.4B` `8.0B` `−3.5B` `0` `15.0B` |
| currency `$` (1250, 2050, −800, 0, 3400) | `1,250` `2,050` `−800` `0` `3,400` | `$1,250` `$2,050` `−$800` `$0` `$3,400` |
| currency `€` suffix `d=2` (12.5, 20.55, −8, 0, 34) | `12.5` `20.6` `−8.0` `0` `34.0` | `12.5€` `20.6€` `−8.0€` `0€` `34.0€` |
| currency `$`, small (4.25, 3.8, −1.5, 0, 6.1) | `4.25` `3.80` `−1.50` `0` `6.10` | `$4.25` `$3.80` `−$1.50` `$0` `$6.10` |

**Boundaries** (six bars: a value, a small positive and a small negative
that round to zero at the ticks' count, 0, a negative, a value):

| Formatter (small values) | nothing asked | `decimals=2` |
|---|---|---|
| millions `d=1`, max 3.4M (0.03M, −0.04M) | `0.03M` `−0.04M` | `0.03M` `−0.04M` |
| millions `d=1`, max 12.5M (same) | `0` `0` | `0.03M` `−0.04M` |
| billions `suffix="bn"`, `d=1` (0.02e9, −0.03e9) | `0` `0` | `0.02bn` `−0.03bn` |
| millions `suffix="백만"`, `d=1`, max 5.6M | `0.03백만` `−0.04백만` | same |
| millions `suffix=""`, `d=1`, max 3.4M | `0.03` `−0.04` | same |
| currency `$`, `d=0` (0.4, −0.3) | `$0.40` `−$0.30` | same |
| currency `€` suffix, `d=2` (0.03, −0.04) | `0€` `0€` | `0.03€` `−0.04€` |

A small value reads zero when the largest value leaves too few places
(three significant digits on 12.5M or €34); `decimals=` shows it, as it does
for cents.

**Log axes, changed from main.** Millions `d=1` on a log y axis, bars
1e4, 2e5, 3.4e6, 4.5e7: main labelled the first bar `10,000`; B labels it
`0` (three significant digits on 45M), though a log axis has no zero.
`decimals=` shows it. Whether labels on a log axis should keep every
non-zero value is a separate decision, to be made on a before/after PoC;
this change keeps B and the asked-precision priority as they are.

## Tests

- `formatting/tests/test_tick_scale.py`: fixed-unit formatters report
  their unit, currency and zero rule; si/myriad per value report the plain
  scale (labels `1,250,000`); `number_text(zero="affixed")`.
- `annotation/tests/test_label_bars.py`: the five PoC charts' label texts,
  sign/currency position against the tick text, the same labels as the
  axis-wide millions, a formatter set after the call is followed; the seven
  boundary charts with nothing asked and with `decimals=2`; asked precision
  (`decimals=0`, `3`, a `fmt` spec) beating the ticks' count under
  millions, `bn`, `$` and `€`.
- Every other label and tick test unchanged.
