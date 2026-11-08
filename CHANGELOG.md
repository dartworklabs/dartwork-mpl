# Changelog

All notable changes to dartwork-mpl will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- **Experimental `dm.label_bars(ax)`: each bar's value on it.** No request,
  its defaults; a request, one keyword. The defaults: `dm.fs(-1)` at
  `dm.fw(1)` in the text colour, 3 pt beyond the bar end; the number printed
  like the axis ticks (plain scaled numbers under `dm.axis_unit`, the ticks'
  suffix under `dm.format_axis_si` or a `PercentFormatter`, the ticks'
  unit, currency and zero under `dm.format_axis_currency` and
  `decimals=n` of `dm.format_axis_millions` / `_billions`: `1.25M`,
  `−$800`, `$0`; plain values under a formatter it cannot read and under
  `decimals=n` of `dm.format_axis_si` / `_myriad`, whose ticks each take
  their own unit); three significant digits on the largest value, then the
  fewest exact decimals, one count per call, no meaningless `.0`; stacked
  bars' segments centred with a total beyond the stack. `dm.simple_layout` turns crowded labels on vertical bars vertical
  (`barh` hides every other one instead) and grows autoscaled limits just
  enough for the labels; limits you set stay, and a bar running past one
  shows its true value at that limit: just inside it, on the bar, in white
  or the text colour (whichever reads on it) when the bar holds the
  number, otherwise just beyond it in the text colour (the series colour
  under `color="series"`); a value there that would cover tick labels, an
  axis label or a title is hidden instead, with a warning (no label also
  for bars wholly outside the view, and for stack segments and totals past
  the limit). A label asked inside its bar (`where="inside"`,
  `crowded="inside"`) likewise stays there only while the bar holds it
  along and across; otherwise it sits beyond the bar's end in the text
  colour, so a narrow dark bar never leaves part of a white number on the
  background. Labels that would still overlap are hidden; grouped series
  take turns where their labels meet (two series alternate by bar index),
  in one call or one call per series, when that keeps as many labels as
  the plain rule. When labels are lost for room (thin `barh` rows, dense
  groups), `dm.simple_layout` warns once with the count and the cure (a
  taller or wider figure); `crowded="skip"`, which asks for hiding, stays
  silent. A label a legend covers is hidden too, with its own warning
  that names the cure for that legend (`dm.place_legend(ax)` keeps the
  legend clear of the labels; a legend it puts on a side, `loc="above"`
  say, is anchored past the values beyond that limit). On a twin pair the
  labels go on the top axes. The keywords:
  `where`, `total`, `crowded`, `decimals`, `fmt` (a `{}` template, a
  format-spec field such as `"{:.2f}"`, or a callable), `size`, `color`
  (`"series"` colours labels off their bar).
- `dm.config.twin_colors` (`"series"`, the default, or `"neutral"`): the
  axis colours of `twinx` / `twiny` pairs.
- Lint rule `twin-legend-hand-merge` (info): a twin pair's legends merged
  by hand (`ax.legend(h1 + h2, l1 + l2)`, or `lns = l1 + l2` then
  `ax.legend(lns, labs)`) points to `dm.place_legend(ax)`.
- Lint rule `ticklabel-format-default-before-layout` (info): an
  `ax.ticklabel_format(...)` / `plt.ticklabel_format(...)` call that asks
  only for matplotlib's defaults (`style="sci"`, `useOffset=True`,
  `scilimits=(-5, 6)`) in the source before `dm.simple_layout`. matplotlib
  records nothing for such a request, so the library's ticks stay
  (`0.5M`; a year axis under a narrowed rc keeps `14 … 24`). The message
  names the paths that work in either order (`ScalarFormatter()` first,
  `dm.format_axis_year(ax)` first, a non-default value such as
  `scilimits=(0, 0)`) and asks for the layout again after a late request.
  Source order only, up to the first `dm.simple_layout` in the source;
  `**kwargs` and requested values given as names are not read.
- `dm.label_bars(..., sign="+")`: a positive value that does not print as
  zero carries `+` where a negative one carries the minus (`+30`, `−15`,
  `+$800`, `+1.2k`, `+33.0 GWh` through `fmt="{} GWh"`); zero prints `0`.
  The default `sign="-"` labels as before; any other value raises
  `ValueError`. A `fmt` field with a format spec and a callable write their
  own sign.

### Changed

- **The waterfall templates draw each step with its signed change.** A step
  is a bar from the level before it with its signed delta as the height
  (`ax.bar(x, delta, bottom=level_before)`), the totals a second `ax.bar`
  call, so `dm.label_bars(ax, steps, sign="+")` prints `+30` and `−15`
  (a fall's label below its bar). The basic template draws no values (its
  comments give the two calls) and renders the same pixels as before. The
  advanced template labels its steps and totals with `dm.label_bars`
  instead of hand-placed text (`−280`, not `-280`; `1,200`, not
  `1,200 MWh`), drops `dm.format_axis_si` so ticks and labels share one
  unit (`1,200`, not `1.2k`), and draws its connectors level at each bar's
  closing value. The docs recipe `plot_waterfall_bridge` follows (no
  `fontweight="bold"`, no `dm.set_decimal`).

- **Importing dartwork-mpl no longer rebinds any matplotlib class or
  function.** `ax.twinx()` is matplotlib's own again (0.7 replaced it at
  import); import still registers the bundled colours, colormaps and fonts.
  `dm.simple_layout` shows the right spine, which the presets hide, of an
  Axes drawing its own y scale on the right of a shared plot area: y ticks
  and y label on the right, or one of them when its x axis is hidden as a
  twin's is (the Axes `twinx()` returns, of an inset too). Figures laid out
  with `dm.simple_layout` look as in 0.7, except: a `sharex` overlay whose
  y ticks and label you moved to the right gets that line, and so does an
  overlay you made like a twin (x axis hidden, y ticks or label on the
  right); when a twin and its parent swap sides, the line moves to the
  parent; a twin whose y axis is hidden, or whose y ticks and label you both
  moved to the left, gets none.
  Without the layout a twin keeps the hidden spine; show it with
  `ax2.spines["right"].set_visible(True)`. A right spine you hide before the
  first `dm.simple_layout` now shows; hide it after the layout, or give it
  `linewidth=0`. `dm.validate_figure` reports the line on such an overlay
  or a swapped parent as `PRESET_OVERRIDE` (INFO); it is the layout's. The
  rule: [docs/development/twin-spine-at-layout.md](docs/development/twin-spine-at-layout.md).
- **Colour catalogue labels pick their ink by WCAG contrast.** The swatch
  labels in `dm.diagnostics.render_color_catalog` and the docs colour
  tables choose white or
  `#333333` with `dm.readable_text_color` instead of a gamma-encoded
  brightness rule, so the catalogue, the docs tables and the public helper
  share one luminance. 68 of the 1,408 shipped colours change ink, each to
  the higher-contrast one; the lowest label contrast rises from 2.67:1
  (`tw.neutral500`) to 3.56:1. The colour values do not change.
- The Matplotlib floor is now `>=3.11.2`, the patch release the declared
  floor environment (Python 3.11, NumPy 1.26) is verified on. Matplotlib
  3.11.0 logs font-weight misses without naming the family, so the quiet
  math-font handling cannot tell them from a caller's own font notices.
- **Twin pairs get series colours.** `dm.simple_layout` colours each side
  of a `twinx` / `twiny` pair like the one series read on it: the spine
  and tick marks in the series colour raised to 3:1 against the
  background, the tick labels and axis label in the same hue at 4.5:1. A
  side whose series draw several colours, or a hue close to the other
  side's, stays neutral; single Axes are never touched; a colour you set
  (`tick_params(colors=...)`, `labelcolor=`, `set_color`) wins and makes
  that whole side yours (on a `twinx` pair the left spine you see is
  `ax2.spines["left"]`): its other parts keep the preset's colours while
  the other side keeps its series colour. The exception is a colour set
  before the first `dm.simple_layout` that equals the preset's default
  (`"black"` under the light presets), which cannot be told from the
  default and is painted with the rest of the side.
  `with dm.config.override(twin_colors="neutral"):` (or
  `dm.config.twin_colors = "neutral"`) keeps the preset's colours, for
  black or neutral twin axes.
- **`dm.place_legend` keeps legend details.** A twin pair's legends merge
  onto the top twin, now chosen by Axes zorder, then figure order (it was
  figure order alone), so the `ax.set_zorder(ax2.get_zorder() + 1)` idiom
  puts the legend on `ax`. The merged legend keeps the existing legend's
  title, `handler_map`, frame, alignment, fonts, label colour,
  `markerscale` and `draggable` (a single Axes' rebuilt legend too);
  `ncols` cannot be read back, so pass it again. A legend it built is
  rebuilt from the artists on its next call, so series added or removed
  since appear or go.
  A legend it cannot rebuild faithfully (tuple or custom handles, labels
  other than the artists') is left as it is: an explicit `loc=` or
  `bbox_to_anchor=` still moves it, and a side (`loc="above"` …) warns
  and leaves it.
- `dm.format_axis_myriad(ax, decimals=n)` now sets an `AxisUnitFormatter`
  instead of a `FuncFormatter`. The tick text is the same.
- `dm.format_axis_currency` and `decimals=n` of `dm.format_axis_millions`,
  `_billions` and `_si` now set an `AxisUnitFormatter` too, one per axis
  (`axis="both"` no longer shares one `FuncFormatter`). The tick text is
  the same; a figure with these formatters can now be pickled. The old
  formatter's `.func` and `set_offset_string` are gone with it.
- **A Figure without a live renderer is always measured with Agg.** A
  plain `Figure()`, a Figure on a PDF, SVG or PS canvas, or one that
  `plt.close` detached is measured for layout, tick formatting and checks
  by a temporary Agg canvas at the Figure DPI, now through public
  matplotlib API only. Where another canvas is registered for PNG
  (`matplotlib.backend_bases.register_backend("png", ...)`, cairo say),
  such a Figure used to be measured with that canvas and is now measured
  with Agg; margins can move by a few pixels (about 7 px at 200 dpi in one
  cairo case). Figures on a live canvas, of any backend, are measured with
  their own renderer as before.

### Deprecated

- **`dartwork_mpl.util`** is deprecated in 0.8 (a `DeprecationWarning`
  on every access to a name, pointing at your line) and may be removed in
  0.10 or later. Until then every name in it is the owner's own object. Import
  each name from its owner; the table is in
  [docs/migration.md](docs/migration.md#deprecated-in-08-dartwork_mpl-util).
- **`FontFamily.tnum`, `FontMeasurement.tnum`, `FontFaceMeasurement.tnum`**
  are deprecated in 0.8 (a `DeprecationWarning` on each access) and may be
  removed in 0.10 or later; they return the same value as
  `.tnum_available` (whether a bundled font declares the OpenType `tnum`
  feature for browsers; matplotlib does not apply it, see `numeric_axes` for
  real plot digits). The font browser data no longer carries a separate
  `tnum` key.

### Removed

- `dartwork_mpl.style.install_twinx_patch` and its root alias
  `dm.install_twinx_patch` (internal, never in `__all__`): the import-time
  `twinx` wrapper. See *Changed*.
- `dartwork_mpl.ui._config` (private): the legacy preset-file helpers.
  Nothing in the package used them; the viewer keeps its state in
  `dartwork_mpl.ui.state`.

### Fixed

- **The layout guide no longer loses the `1e6` multiplier.**
  `docs/usage_guide/layout.md` advised calling `ax.ticklabel_format(...)`
  after the layout; that applies the request, but its offset text (`1e6`)
  has no room and is drawn above the figure, so `0.0 … 3.0` reads without
  its multiplier. The guide now gives the paths that work in either order
  (`ScalarFormatter()` first, `dm.format_axis_year(ax)` first, a
  non-default value) and, for a late request, `dm.simple_layout(fig)`
  again, with an example whose multiplier stays on the canvas.
- **`TEXT_CONTRAST` reads a shape only where it is drawn.** A bar past the
  axes limit is drawn up to the axes edge, but `dm.validate_figure` read
  text beyond the limit (a bar's value there) against the whole bar and
  reported a contrast fault that was not drawn (black on `#1f4e79`,
  2.42:1). A shape that clips now counts only inside its clip box; real
  faults on a bar, or white text off it, are still found.
- **Labels fixed by `set_xticklabels` print the right years.**
  `ax.set_xticklabels(ax.get_xticklabels(), rotation=45)` on annual data
  read `2007.5` at 2010 after `dm.simple_layout`: the whole-year locator
  went in under labels matplotlib gives to ticks by order, and the refit
  could change matplotlib's own tick count too (a 6 cm axis over 0–5,000
  read `2000` at 1,000). Such an axis now keeps the ticks its labels were
  made for, pinned before the refit, and is not thinned. Pinned ticks stay
  when you zoom later with `set_xlim` (no new ticks appear). To rotate
  without fixing the text, use `ax.tick_params(axis="x", rotation=45)`.
- **Secondary axes read the library's numbers.** A `secondary_yaxis` over a
  price line printed `1600 … 2400` beside the parent's `1,600 … 2,400`,
  and over millions `0.0 … 3.0` under `1e6` beside `0.5M`. A
  `secondary_xaxis` / `secondary_yaxis` whose functions are affine (the
  same values, `×1.3`, °C as °F) now follows the parent's rules; a curved
  one (`1 / x`) keeps matplotlib's. `dm.format_axis_si` on such a
  secondary takes one unit for the axis (`0.5M … 3.0M`, not `500k, 1M,
  1.5M`).
- **A year axis zoomed under two years is labelled.** `2023.2–2023.8` had
  no tick label at all, `2023.5–2024.5` one of five. Every tick now prints
  its value (`2023.2 … 2023.7`), as under a locator you set: never a
  rounded year, never an empty label.
- **`dm.format_axis_year` never rounds.** A zoom to `2019.2–2019.8` read
  `19 19 19 20 20 20`, and matplotlib's 2.5-year steps `05 08 10 12`
  before a layout. It now ticks whole years unless you set a locator
  (monthly data read `05년, 06년`; `ax.locator_params(nbins=...)` asked
  before is kept) and uses the library's year formatter: whole years with
  the suffix (`19년`; four digits when two would repeat), every value
  between years (`2019.2 …`), and `ax.ticklabel_format` works on it.
  The formatter class is now `YearTickFormatter` (was `FuncFormatter`): the
  cursor reads the value (`2007.53`, was `08년`), and calling it directly
  before a draw on a fraction (`f(2025.5)`) gives `""` (was `26년`).
- **The whole-canvas recipes' presentation margin note says what a render
  actually does.** It claimed that raising the local left margin from
  1.15 cm to 1.70 cm "cleared that overflow in both examples". Measured on
  a 20 × 16 cm `presentation` render of the shipped recipes, 1.15 cm puts
  content outside the canvas on three sides (left 1.40 cm, bottom 1.05 cm,
  top 0.34 cm) and 1.70 cm only narrows the left one to 0.85 cm. The note
  now reports all three, prints margins measured to keep every artist
  inside (L 2.60 / R 0.50 / B 2.15 / T 1.19 cm), and names what margins
  cannot fix: `TICK_CROWD` on the 30 % row and `LEGEND_OVERLAP` in the
  4.9 cm and 2.9 cm panels for an inside legend at 19.5 pt. For that last
  one it now gives two measured ways out, each leaving `dm.validate_figure`
  with no findings — the same page under `report` at the recipe's own
  1.15 cm margins, or `presentation` with the four panel legends replaced
  by one shared `fig.legend` below and a 3.40 cm bottom margin (adding the
  figure legend without deleting the panel ones leaves five legends and
  every overlap back) — and records that `dm.place_legend(ax)` does not
  rescue it (it lifts each legend onto all four titles and 55 px past the
  canvas). Same text in `dm.get_prompt("03-recipes")` and
  `docs/usage_guide/layout.md`.

## [0.7.0] - 2026-11-06

The rule behind these defaults: with no request the library's look applies;
a request for another format gets that format.

### Security

- Raise the development-only Mistune floor to 3.3.3 and virtualenv floor
  to 21.14.13, fixing the captured Markdown recursion, seed-link and Bash
  prompt-expansion advisories. These tools are not consumer dependencies.

### Breaking / Changed defaults

- **Two-digit years on untouched axes.** An x axis whose data are integer
  years (1900–2099: annual lines, bars, grouped bars, scatter, `stackplot`
  and `fill_between` areas; a `secondary_xaxis` showing them too), and a
  y axis whose data *positions* are such years (horizontal bars such as
  `ax.barh(range(2014, 2025), …)`, grouped too, `fill_betweenx` spans; a
  `secondary_yaxis` following them), ticks whole years only and reads
  `16, 18, 20 … 24` (no more `2005.0, 2007.5`, nor a rounded `08`, nor
  `2,014` beside horizontal bars). Line, scatter and bar values on y are
  quantities and keep their numbers (a price of `1,985 … 2,045`); monthly dates read `23.01, 23.07, 24.01`, quarterly
  dates `23.Q1, 23.Q3` (`stackplot` and `fill_between` areas included;
  `dm.format_axis_dates` and dated categories too). Korean figures print
  the same text, without the `년` suffix. Other
  formats on request: `tick_years=4` (`2016`), `date_style="concise"`
  (`23, May, Sep`).
- **Korean figures count in 만/억/조 from 1,000,000** on axes you did not
  format (`50만 … 250만`, `0.2조`). English figures keep `k/M/G/T`;
  `number_ladder="si"` gives `k/M/G/T` in Korean figures too.
- **A formatter or locator you set is never replaced**, of any class. The
  defaults go only where matplotlib's own `axis.isDefault_majfmt` /
  `isDefault_majloc` flags still hold, so matplotlib's idiom
  `ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(loc))` keeps its
  words (in Korean figures too, which 0.6.0 turned Korean) and its locator
  (no quarter locator, no thinning), and an explicit `ScalarFormatter()`
  keeps `1000`. A tick count asked with `ax.locator_params(axis="x",
  nbins=3)` is kept, on whole years for year data (`00, 10, 20`); under a
  locator you set (`MaxNLocator`) year data read `05, 10` while every tick
  is a whole year and plain numbers (`2005.0, 2007.5`) when one is not,
  decided at each draw (also for a locator set after `dm.simple_layout`),
  so no tick is left unlabelled or rounded.
- **Requires Matplotlib ≥3.11; 3.10 is no longer supported.** Matplotlib
  3.11 differs from 3.10 in text metrics, pixel rounding and FreeType
  rasterization. The apparent legend-marker size change was a stale
  historical baseline, not a Matplotlib 3.11 change. Rather
  than patch Matplotlib internals to imitate 3.10, dartwork-mpl follows
  3.11 as it is: the 14 pixel baselines and the colour-theory docs figures are regenerated
  on 3.11 (3.11.0 and 3.11.2 render them byte-identically), and supporting
  both series would mean two baseline sets. The `numpy<2.5` cap is lifted
  with it: only Matplotlib 3.10's own `dates.py` tripped NumPy 2.5's
  generic-unit deprecation.
- The `fastapi<0.137` upper cap is lifted.

### Added

- **Experimental axis units:**
  `dm.axis_unit(ax, axis, label="… ({unit}명)", ladder=..., scale=...)` puts
  the unit in the axis label and keeps the ticks plain (`0, 0.2 … 1.0` under
  `인구 (억명)`); the experimental `dm.axis_unit_of(ax)` returns the unit
  for value labels.
  The default rule is the largest unit (`scale="max"`).
- `dm.config.tick_years` (2 or 4), `date_style` (`"period"` or `"concise"`)
  and `number_ladder` (`"auto"`, `"si"` or `"myriad"`): the tick formats a
  prompt can ask for, as `with dm.config.override(...):` around the code from
  figure creation to the last `dm.simple_layout`, or set on `dm.config`.

### Fixed

- Symmetric axes no longer print floating-point noise (`-0.4 … 0.4`).
- **FastAPI >=0.137 UI.** The UI policy matches against the routers it builds,
  so the included-router wrapper no longer makes every request 403.
- **NumPy 2.5.** Date formatting no longer creates generic-unit NumPy values.
- **Matplotlib 3.11 fonts.** `dm.font.list_registered()` lists only the
  bundled primary families, and the per-render "Failed to find font weight"
  notice for one-weight fallback families is muted.
- **Matplotlib 3.11 math text.** The first `$...$` render under a preset no
  longer prints ten "Failed to find font weight light for STIXGeneral / ... /
  cmex10" lines. Matplotlib's math fonts (picked from `mathtext.fontset` and
  `mathtext.fallback`) have no light weight; only that notice at the preset's
  `font.weight` is dropped, so a family you choose still warns.
- **Matplotlib 3.11 formatter warning.** dartwork-mpl's default number tick
  labels and `dm.format_axis_si` / `_millions` / `_billions` / `_myriad` no
  longer emit a `MatplotlibDeprecationWarning` about `Formatter.locs` on
  every draw.
- **Docs build from `docs/`.** The 18 tier-2 gallery examples shared their
  file names with the basic tier, so sphinx-gallery warned "Duplicate
  example file name(s)" and `sphinx-build -W` failed when started in
  `docs/`. They are now `plot_<id>_advanced.py`; template ids, MCP
  resources and the bundled sources are unchanged, and
  `find_template(..., tier="advanced")` reports the new `source_path`.
- **Secondary axes stay on the canvas.** `dm.simple_layout` now fits the
  tick labels, offset text and label of `ax.secondary_xaxis(...)` /
  `ax.secondary_yaxis(...)` like the parent's own; they used to sit past
  the figure edge. `dm.validate_figure`'s `OVERFLOW` and `CLIPPED_TEXT`
  checks look at them too (matplotlib keeps them out of `fig.axes`).
- **Layout checks judge drawn tick labels only.** `OVERFLOW`,
  `CLIPPED_TEXT` and `CROSS_AXES_OVERLAP` no longer report tick labels
  matplotlib never draws: those of an Axes with `ax.axis("off")`, and a
  tick a hair past the view (a colorbar's `1.00` above a 0.9997 limit).
- **`ax.ticklabel_format` on a year axis.** After `dm.simple_layout` it
  raised `AttributeError: This method only works with the ScalarFormatter`,
  and before it the request was dropped. The year formatter is now
  matplotlib's `ScalarFormatter`, and what was asked of matplotlib's own
  formatter before the layout carries over, so both orders draw the same
  ticks: `useOffset=False` and `style="plain"` keep `14 … 24`; an exponent
  or offset you ask for (`scilimits=(0, 0)`, `useOffset=2000`) reads as
  matplotlib writes it, on whole-year ticks. The same holds on an axis with
  the library's default numbers (`1,750`; `0.5M`): `ax.ticklabel_format()`
  no longer raises there, `useOffset=False` keeps `1,750`, `style="plain"`
  on a `0.5M … 3.0M` axis prints full numbers, and a request for
  matplotlib's notation gets matplotlib's `ScalarFormatter`, with the
  settings asked before it (`style="plain"`) kept.

## [0.6.0] - 2026-11-05

### Breaking / Removed

- The 0.5.6 root exports `get_palette`, `set_cycle`, `cycle`,
  `cycle_cycler`, `list_palettes`, `list_colormaps`, `plot_colors`,
  `plot_colormaps`, `show_palette`, `classify_colormap`, `DartworkColor`,
  `DartworkColormap`, and `set_palette_version` have been removed, as has
  `dartwork_mpl.cmap` (`dm.cmap`). Use the current `dm.colors`,
  `dm.set_colors`, `dm.list_colors`, and `dm.show_colors` APIs as appropriate;
  their behavior and arguments differ from the old helpers. See the
  [migration guide](docs/migration.md#v5--generative-color-system-060)
  for each name and type guidance.
- The v4-only numeric cycle aliases `0`–`7` and ad-hoc color families were
  removed; curated categorical sets remain available. The 0.5.6 deprecation
  notice promised v4-only tokens at least two minor releases before removal;
  that promise was not met for these removed legacy tokens. Some surviving
  names also refer to different v5 colors; see the migration guide before
  substituting tokens.

### Changed

- **Matplotlib 3.10.x support.** The supported range is >=3.10.1,<3.11;
  3.11 is excluded because rendered appearance differs from the frozen output.
  NumPy is restricted to >=1.26,<2.5 because its 2.5 date-unit deprecation
  breaks the supported Matplotlib date tests.
- **UI FastAPI compatibility.** The UI extra requires FastAPI >=0.110.0,<0.137.
  Newer included-router wrappers prevent the current policy matcher from
  finding routes, causing every request to be rejected with 403.
- **Python 3.11 minimum.** Python 3.11–3.13 remain tested; Python 3.10 is
  no longer supported from 0.6.0 because the security patch set requires
  Pillow 13 and other dependencies whose minimum is 3.11.

### Security

- Raise Pillow's published core requirement to >=13.0.0 and publish affected
  MCP/UI transitive security floors so fresh wheel installs receive the
  repair. Update the 25 advisory candidates and forced collateral packages;
  keep Jupyter/docs patches in the dev group. FastMCP 3.4.10 and its matching
  slim package replace 3.4.2. The secure 2.x minimum becomes 2.14.7 because
  2.13.3 pins a vulnerable MCP SDK <1.23; its legacy source/API test remains.
  Vulnerable 3.0–3.4.9 is excluded and the <4 cap remains. PyJWT >=2.15.1 uses the exact-tested
  wheel; GHSA-gvp8-978c-rx2q still has no upstream patched-version field.
  This addresses the captured dependency ranges, not all possible security
  issues or unassessed product paths.

### Added

- **`dm.review(fig, stem)`: one call for the review loop (experimental, #574).**
  It saves with `dm.save_formats` (the same files), runs every
  `dm.validate_figure` check on the saved figure and keeps the findings as
  they are, and returns a `Review` with a summary of what the figure shows:
  per Axes (insets nested) the titles, axis labels, ranges, tick labels,
  series (kind, label, count, colour, line style, a digest of the values) and
  legends, the figure's and SubFigures' own titles and text, plus every text
  outside the canvas. `complete` is `False` when a check could not run
  (`CHECK_FAILED`); it is not a pass. `<stem>.review.json` records it all.
  With `baseline=` (an earlier `Review`, its stem or its json) the review
  lists every summary entry that differs by path (`axes[0].ylabel.text`);
  `allow=` patterns (`*` the only wildcard) mark the expected ones and
  `Review.unexpected` is the rest. Nothing is fixed or judged. The bundled
  skill's review loop and editing reference use it (masterplan stages 3–4).

- **Explicit native data policies.** `dm.validate_data(..., policy="strict" | "preserve" | "clean")`
  rejects, retains or removes nonfinite values in one-dimensional signed/unsigned
  integer and real floating vectors. Opt-in calls require `allow_nan=False`;
  `dm.DataPolicyError` and `dm.DataPolicyWarning` carry immutable original-index
  records. Omitted policy and `policy=None` preserve exact legacy behavior;
  MCP shape checks and report contracts are unchanged.
- **`dm.format_axis_dates(ax, dates)`.** Bars and other category charts that
  stand for dates (`"2024-01" … "2024-12"` under twelve bars) get the
  library's concise date words (`2024, Feb, Mar …`; `2024년, 2월 …` on a
  Korean figure), and `dm.simple_layout` thins a crowded axis to every 2nd,
  3rd, 4th, 6th or 12th month until the labels are one em apart, instead of
  the labels being rotated. ISO strings, datetimes and `datetime64` are read;
  anything else is a `ValueError`.
- **`dm.figsize_for("full_slide")`.** A chart that is a whole 16:9 slide
  ("a full-slide chart") is 25.4 x 14.29 cm under any preset: the 10 in slide
  the presentation sizes assume, so its text reads at the same size as a
  chart under a slide title.

- **The preset's default canvas (provisional).** `dm.figsize_for(kind,
  n_points=, n_series=, dual_axis=, nrows=, ncols=)` returns the active
  preset's figure size when a request names none: report widths 9 / 12 /
  14.5 / 17 cm picked by chart kind and data density (4:3 like `dm.figsize`),
  journal columns under `scientific` (one panel in one 9 cm column, grids
  and full-width kinds 17 cm), 10.5 cm tall under a 16:9 slide's title
  under `presentation` (11.4 / 15.4 / 23.4 cm wide for up to 4, up to 6
  or more x positions, half for `"compact"`), widths scaled by font size
  under `poster`, and `"slide"` for that slide body under any preset.
  `dm.grid_shape(n)` lays out `n` small multiples. The same request gets the
  same canvas from any agent. The bundled skill uses both and states that
  spines, grid, ticks, fonts, background and margins stay the preset's, with
  no figure title or extra panel unless asked. Both are in `dm.EXPERIMENTAL`.
- **`PRESET_OVERRIDE` validation check (INFO).** `validate_figure()` reports
  major gridlines, spine visibility and Axes or figure backgrounds that differ
  from the active dartwork preset, one finding per Axes and property with the
  preset and figure values in `detail`. The check cannot see the request, so
  the finding is advisory: keep the change only if the user asked for it.
  Axis-off, polar, 3-D, colorbar, pie and twin Axes are not inspected, and
  nothing is reported without an active preset.
  `dartwork_mpl.style.active_preset_rcparams()` returns the values compared.
- **Outside legends from one call.** `dm.place_legend(ax, loc="above")` (also
  `"below"`, `"right"`, `"left"`) puts the legend outside the axes, centred on
  that side and past its tick labels and axis label (a twin's included) by the
  preset's `legend.borderaxespad`. Above and below it takes one row when that
  fits the axes width, else the fewest rows that fit; right and left it is one
  column. `ncols=` still wins; `bbox_to_anchor=` with a side raises
  `ValueError`. Other explicit `loc` values behave as before.
- **`dm.label_line_ends(ax)` (provisional).** Line names instead of a legend
  in one style for every caller: each named line's label
  `axes.labelpad` right of its last finite point, vertically centred, in the
  preset text size and weight and the line's colour made readable on the
  axes background (`dm.ensure_contrast`, 4.5:1); labels that would overlap
  move apart vertically in order. The legend is removed and the axis limits
  stay; `dm.simple_layout` makes room. Agents asked for end labels had drawn
  them in the line colour, a darker shade or black, at 6 to 8 pt, and some
  widened the x axis to fit them.
- **`dm.add_note(fig, text)` (provisional).** A source or note line in one
  style for every caller: the figure's lower-left corner, one point under the
  preset font, the preset text colour; `dm.simple_layout` keeps the axis
  labels one `axes.labelpad` above it. Named `fontsize=`/`color=` win. In the
  customization eval the same request gave 7 pt from one agent and 8 pt from
  the other. The skill also keeps an existing legend on "highlight one series"
  and keeps canvas, title and legend on "make it look better".
- **`dm.place_legend(ax)` gives a twin pair one legend.** The entries of every
  `twinx`/`twiny` partner go into one legend on the twin drawn last, and the
  partners' own legends are removed, whichever twin is passed.
- **`dm.place_legend(ax)` goes above the plot when nothing inside is free.**
  With no `loc`, a legend that would cover data in every in-axes spot now takes
  the `loc="above"` placement (`legend._dm_outside_fallback`), so a request
  that names no side gets one legend from every agent; a caller
  `bbox_to_anchor=` keeps it inside as before.
- **`LEGEND_OVERLAP` validation check (WARNING).** `validate_figure()` reports
  a legend box that covers a title, an axis label, tick labels or a
  figure-level text (suptitle, `fig.text`), one finding per legend and covered
  role, naming both. `OVERLAP` compares text with text only and missed a
  legend drawn on the title.
- Font corpus expanded to 20 families (262 files): Noto Serif and IBM Plex Serif
  added, Roboto/Roboto Mono completed with instanced weights + italics;
  registry-backed interactive font browser on the fonts page (faceted filters,
  specimen drawer, badge system, pin/compare tray, and a custom preview
  sentence).
- **Visual tick consistency checks.** `validate_figure()` now includes
  `UNIT_DUP`, `TICK_ROTATION`, and `TICK_DECIMAL` to catch duplicated
  axis/tick unit affixes, avoidable or missing x-tick rotation, and
  ambiguous or over-precise numeric tick labels. `dm.recommend_tick_decimals()`
  exposes the decimal-step rule as a small public helper for formatter code.
- **Annotation and legend primitives.** `dm.annotate_value()` adds compact
  point-offset value labels with automatic vertical or horizontal placement,
  `dm.annotate_corner()` adds spine-tight narrative corner notes,
  `dm.label_hline()` keeps reference-line labels attached to visible line
  endpoints, `dm.place_legend()` scores data/text obstacles across locations
  and one to three columns, and `dm.wrap_axis_label()` /
  `dm.wrap_axis_labels()` wrap overlong axis labels to two lines.

- **Shipped colours are now frozen by a machine check.**
  `tests/test_shipped_colors_hash.py` pins five surfaces by sha256 — 1,272
  named colours, 99 colormaps at 256 stops, 14 style presets, the full
  `dm.colors(name, n)` grid, and the curated palettes. Any change to a shipped
  colour fails the test and names the surface that moved, with no colour-theory
  knowledge required to read the result.

- **Agent skill in the wheel.** `src/dartwork_mpl/skills/dartwork-mpl/`
  (`SKILL.md` plus references on sizing, editing, colours, Korean text, the
  review loop and templates) ships with the package.
  `python -m dartwork_mpl.skills install [--dest DIR] [--copy] [--force]`
  links it into `.claude/skills` and `.agents/skills`, the project skill
  folders agents read, so it follows upgrades; every agent gets the same
  skill. `... skills path` prints the folder. `--copy` copies record an inventory of their entries and are
  never overwritten after local edits without `--force`, nor when they change
  during the install. A link is replaced in one atomic rename; an
  interrupted copy replacement is recovered on the next `install` or `path`
  run. Linked `.claude`/`.agents` folders may not lead outside `--dest`. The
  skill also says how to use it alongside a generic chart skill.
- `dm.figsize` accepts `"W:H"` ratio strings as its second argument
  (`dm.figsize("13cm", "16:9")`); so do `dm.figsize_grid` and
  `parse_aspect`.

### Changed

- **`dm.label_axes` names itself when a keyword cannot be honoured.** An
  argument it does not support (`fmt`, `loc`, `xy`, a typo) still raises
  `AttributeError` and a property it sets itself still raises `TypeError`, but
  the message now names `label_axes`, the argument, the supported
  `labels`/`x`/`y`/`fontsize`/`fontweight` and the native
  `ax.text(x, y, label, transform=ax.transAxes)` route, instead of a bare
  `'Text' object has no property 'fmt'` or a `matplotlib...Axes.text()` clash.
  `horizontalalignment`/`verticalalignment` were accepted and then dropped by
  the helper's own `ha`/`va`, so an explicit alignment request silently did
  nothing; they now raise that same named `TypeError`, matching the bundled
  guidance that the helper supplies alignment. Every keyword that reached the
  label before — `color`, `rotation`, `fontstyle`, the rest of the `Text`
  surface and `ax.text`'s own `fontdict` — is untouched, as are label placement
  and the default output. `fontdict` still reaches `ax.text` but not
  `ax.annotate`, so it still fails on a panel whose label moves onto a title's
  line; passing the properties directly works on both paths.

- **`dm.make_palette` rejects a fractional `highlight` inside the series
  range.** `highlight=1.5` passed the range check but matched no series, so
  every series receded to `oc.*3` and none was emphasised — a plausible-looking
  palette that answered a different question. It is now a `ValueError` naming
  the valid range. Whole-number indices of any numeric spelling (`1`, `1.0`,
  `True`, numpy integers and integral floats) keep their exact results, and an
  out-of-range `highlight` is still ignored.

- **Bundled templates size with `dm.figsize_for` and draw no title.** All 36
  templates (18 basic, 18 advanced) and their gallery pages take the canvas
  from `dm.figsize_for(...)` with counts read from their own data
  (`dm.grid_shape` + `nrows=`/`ncols=` for small multiples) instead of
  hand-picked 9-17 cm sizes, and no longer draw a chart title; the advanced
  tier also drops its subtitle and source footnote. Panel names in small
  multiples stay. Agents copy templates, so a size or title now appears only
  when the user asks for it.
- **`TICK_ROTATION` advises dates and fewer ticks before rotation.**
  Overlapping x labels now read "날짜면 dm.format_axis_dates(ax, dates),
  아니면 눈금 수 축소, 45° 회전은 마지막 수단", and the fix suggestions list
  `dm.format_axis_dates`, then a tick locator, then `dm.rotate_tick_labels`.
- **Agent skill and policy: details nobody named.** No value labels unless
  asked; axis limits stay the library's (bars from 0, lines with their data
  margins); bars are vertical unless the category names would overlap; axis
  labels are column names, else the request's noun, word for word and in its
  order, with no unit nothing states; a bare year stays a number; a figure
  moved to slides takes `dm.figsize_for` and multiplies pt values written in
  its code by 2.6, unrounded; a broad "make it look better" keeps axis labels
  as written and an "only X" edit keeps the legend as it is.
- **Agent skill and policy after eval v16–v18.** Column names win over the
  request's wording for axis labels; a legend added, moved or merged (a twin
  pair's two into one) goes through `dm.place_legend`, never `ax.legend` with
  `bbox_to_anchor`, and others stay; an "only X" edit that makes a legend
  overlap other text (`LEGEND_OVERLAP`) moves that legend with
  `dm.place_legend` and lists it (decision L-B); a "make it look better"
  pass that shrinks touching value labels to `dm.fs(-1)` gives them
  `dm.fw(1)` too when no weight is written (decision W-A) and keeps the axis
  limits even when a line crosses the labels.

- **`presentation` is `scientific` with every point size × 2.6.** Text,
  lines, markers, tick lengths and widths, pads, grid, spines and boxplot
  lines are 2.6 times the scientific values (23.4 cm slide body over a 9 cm
  column): 19.5 pt text, 18.2 pt ticks, 15.6 pt legend, 2.6 pt lines, 7.8 pt
  markers. A slide chart now looks like a column figure enlarged as a vector;
  before, only text grew (10.5 pt) and lines, markers and ticks stayed at
  paper size. `presentation-kr` follows. Slide titles stay regular weight.
- **One `dm.fs` / `dm.lw` step is 2.6 pt under `presentation`.** So
  `dm.fs(-1)` is 16.9 pt on a 19.5 pt slide, the same share as 6.5 of 7.5 pt
  in a column, and `dm.lw(1)` doubles the line as it does on paper. Every
  other preset keeps 1 pt steps; `dartwork_mpl.style.step_pt()` returns the
  active step. Code that passed `dm.fs(n)` under `presentation` gets larger
  offsets than before.
- **Tick numbers and dates nobody formatted are the library's.**
  `dm.simple_layout(fig)` gives every axis still on matplotlib's default
  number formatter whose visible ticks reach 1,000 thousands separators
  (`1,750`, `34,000`) and, from one million, the largest tick's SI unit
  (`0.5M … 2.5M`) instead of a `1e6` corner label; decimals are the fewest
  exact ones. Smaller axes, x axes of years (every tick in 1000-2999), log,
  date and category axes, colorbars and axes with a formatter you set keep
  theirs; `format_ticks=False` keeps matplotlib's numbers. Every preset sets
  `date.converter: concise`, so an unformatted date axis reads `2024, Mar,
  May … 2025` instead of `2024-01, 2024-03 …`, whose labels collided at
  column widths. When the figure's axis labels, titles or legend are Korean,
  `dm.simple_layout` writes the dates as `2024년, 3월, 5월 … 2025년`. Agents had each picked their own formatter, so the same
  0-1,750 axis came out as `1750`, `1,750` or `1.75k`.
- **Date ticks fit the axis length.** matplotlib picks date ticks from the
  date range alone, so 36 months got ten labels on a 23.4 cm slide and on a
  9 cm column alike, where `2021 May Sep 2022` ran together. After fitting,
  `dm.simple_layout` gives a date axis matplotlib set up fewer ticks until
  neighbouring labels are one em apart (`2021, Jul, 2022 …`) and fits the
  margins again. Axes with a locator you set, rotated labels and
  `format_ticks=False` keep matplotlib's ticks.
- **Negative ticks from the axis-wide formatters use the axis minus.**
  `dm.format_axis_si`, `_millions`, `_billions` and `_myriad` print U+2212
  (`−1.0M`) like matplotlib's own ticks unless `axes.unicode_minus` is off,
  instead of a hyphen beside the minus of the other axis.
- **No meaningless decimals and no mixed units on scaled axes (#523).**
  `format_axis_si`, `format_axis_myriad`, `format_axis_millions` and
  `format_axis_billions` default to `decimals=None`: one decimal count per
  axis, the fewest that render every visible tick exactly. Integer ticks
  print `200`, `0`, `1M` instead of `200.0`, `0.0`, `1.0M`; half steps stay
  exact (1250 no longer rounds to `1.2k`, `1.75억` to `1.8억`); fractional
  steps keep the count on every tick (`0.5M, 1.0M`). Zero prints as `0`;
  scaled values of 1000 and more get thousands separators.
- **`format_axis_si` and `format_axis_myriad` take `unit=`.** The whole axis
  shares one unit, so an axis no longer mixes `800` with `1.2k` or
  `7,500만` with `1.25억`. `unit="max"` (default) uses the unit of the
  largest visible tick (`0, 0.2k … 1.2k`; `0, 0.25억 … 1.75억`);
  `unit="whole"` picks a unit in which every tick is whole (`0, 200 …
  1,200`); a prefix such as `"k"` or `"억"` fixes the unit. Log axes keep a
  unit per tick (decades cannot share one). An explicit integer `decimals=`
  with the default `unit` keeps the previous per-tick output.
- **`TICK_DECIMAL` trailing zeros are now a WARNING**, and decimal
  consistency is judged per unit suffix on the rendered numbers; a bare `0`
  needs no decimals (`-1.0M, -0.5M, 0, 0.5M, 1.0M` is clean). The new
  **`VALUE_LABEL_DECIMAL`** check warns when every numeric value label in an
  axes is a whole number but some print trailing zeros.
- **Value labels on bars and lines are one weight step heavier.**
  `dm.annotate_value()` defaults to `fontweight=fw(1)` unless `fontweight` or
  `weight` is passed; the advanced bar_grouped, waterfall, tornado and line
  templates now match the templates that already did this.
- `format_axis_year` prints two-digit tick years by default (`2025` -> `25년`,
  `25年`, `25`). Four-digit tick years double the tick width and crowd
  neighbouring labels; the company-analysis harness now rejects them
  (user instruction 2026-10-06). Pass `digits=4` for axes spanning a century
  or more.
- **Orphan tick-font adoption is now opt-in.**
  `dm.config.adopt_orphan_tick_font` now defaults to `False`, so
  `simple_layout`, `save_formats`, and `save_and_show` preserve tick fonts on
  unlabeled axes unless callers pass `adopt_orphan_tick_font=True` or enable
  the config field. This intentionally changes every existing figure with an
  unlabeled axis: tick labels return to the smaller tick font. Set the config
  field to `True` to retain the previous rendered output project-wide.
- **Colour construction is unified on OKLab/OKLCH.** The compiler previously
  authored OKLCH hue and chroma while solving rendered output against CIELAB
  `L*`. CIELAB and CIEDE2000 remain as isolated validation diagnostics.
  **Every shipped colour value is byte-identical** — verified by the freeze
  above on both `main` and the refactor branch.
- **Colour documentation now separates design choices from evidence.** Claims
  are identifiable as design choice, implementation fact, reproducible
  measurement, or stated limit, so a house style no longer reads as a law of
  vision. `relative_y` is described as modeled relative CIE Y from nominal D65
  sRGB rather than a measurement of any display.
- `dm.get_agent_doc("AGENTS")` and `("CLAUDE")` return a one-screen consumer
  entry that points to the skill instead of the repository's contributor
  `AGENTS.md` (ADR and colour-freeze rules no longer reach installed users).
  The repo-root `AGENTS.md` / `CLAUDE.md` are contributor docs and leave the
  wheel. The four stale `.cursor/rules/*.mdc` files became one pointer.

### Fixed

- **Retained figures relayout after `plt.close(fig)` (#579).**
  `dm.simple_layout(fig)` updates subplot positions on the retained Figure
  even after it leaves pyplot's figure registry.
- **Retained figures work with Matplotlib 3.11's rendererless canvas (#582).**
  Layout, formatting and geometry checks can obtain a renderer when the
  canvas has no `get_renderer` method.
- **MCP guidance respects requested title and source scope (#580).**
  Returned instructions and examples add titles and source notes only when
  asked, keep unnamed preset defaults and explicit user values, and preserve
  existing text outside an edit's scope.
- **MCP HTTPS trust uses updated certificate roots (#576).** The MCP extra
  now requires `certifi>=2026.10.19`, excluding compromised emSign roots
  from the certificate bundle used for Raw GitHub fetches.
- **Line-end labels stay apart after the layout.** `dm.label_line_ends`
  spaced its labels at the Axes size of the call, so a later
  `dm.simple_layout` that shrank the Axes (for a note, say) let them overlap
  again (-12 px at 300 dpi in a four-line slide chart). The layout now
  spaces them again at the size it settles on.
- **`dm.add_note` is `dm.fs(-1)` under `presentation` too.** It used one
  point under the body text, which is the same step everywhere but
  `presentation`, where a step is 2.6 pt: slide notes are 16.9 pt, not
  18.5 pt.
- **A refused `simple_layout` call leaves tick formats alone.** The library
  tick numbers and dates (#554) were installed before the GridSpec and
  margin checks, so `simple_layout(fig, margin=float("nan"))` raised but had
  already swapped the formatters, and a figure without a GridSpec got them
  although its layout stays unchanged. They are installed only once the call
  goes ahead.
- **Korean concise dates keep the axis's offset and TeX choice.** Replacing a
  stock `ConciseDateFormatter` on a Korean figure carries over `show_offset`
  and `usetex` with the time zone.
- **The MCP template descriptions match the templates.** `suggest_chart_type`,
  `render_template_advanced`, the advanced-template resource and the MCP
  guide no longer promise a narrative title or source footnote, which the
  templates dropped; `03-recipes` describes `label_axes` stepping before a
  title.

- **Korean concise dates leave edited formats alone.** `dm.simple_layout`
  turned any stock-type `ConciseDateFormatter` on a Korean figure into
  `2024년, 3월 …`, also when the caller had already rewritten its format
  strings (company-analysis turns `%Y` into a two-digit `%y` and then failed
  its year-tick guard on `2026년 5월`). Only matplotlib's own format strings
  are replaced now.
- **`save_formats` no longer prints `PRESET_OVERRIDE`.** The check cannot
  see the request, so a deliberate grid or spine printed advice on every
  save and failed callers that allow no `[VISUAL]` hints. `validate_figure()`
  still reports it, and takes `exclude=` to drop check IDs the same way
  `checks=` selects them.

- `dm.format_axis_dates` reads `datetime64` arrays and Series of any unit
  (a `datetime64[ns]` array came out in the year 53999741868), refuses
  numbers such as a bare year instead of reading them as seconds since 1970,
  and words and thins only the dates in view, so a view cut to Feb–Dec still
  shows the year; a step that shows one label in a cut view no longer ends
  the search for a step that fits.
- After `dm.style.use("presentation")`, a bare `dm.style.stack([...])` no
  longer keeps the 2.6 pt `dm.fs` / `dm.lw` step.
- `dm.simple_layout()` no longer leaves an axes title on top of a legend above
  the axes. Whether the legend came from `dm.place_legend(ax, loc="above")` or
  a raw `ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0))`, the title
  offset is raised so the title sits `axes.titlepad` above the legend (all
  three title slots, one baseline); text, size and weight are unchanged. A
  `place_legend` outside legend is re-anchored to the labels present when the
  layout runs, so setting the x label after the legend no longer collides.
- `dm.label_axes()` no longer puts the panel letter on a left-aligned panel
  title (the advanced small_multiples template drew "a" over "Line A"). With
  `x="auto"`, a left title takes the letter onto its line, half a letter size
  before the title start, and the letter follows the title (layout, a legend
  above); a centre or right title moves it only when they would touch. `y`
  now defaults to `None` (1.05 as before when no title is in the way); an
  explicit `x` or `y` is kept. Title text, size and weight are unchanged.
- `simple_layout()` rejects nonfinite effective margins after complete parsing
  and resolution, before layout effects. Finite margins and existing parse,
  no-op and GridSpec error precedence are preserved.
- Selected basic/advanced templates reject invalid `return_format` values before
  execution, render temporary-file creation or publication, using the existing
  `render_error` reply. Valid renders and unknown-template precedence are preserved.

- `validate_data(..., require_same_length=False)` keeps originally unequal
  inputs independent even when cleaning temporarily makes their lengths equal,
  preventing finite-value loss and spurious minimum-point errors.

- `make_palette` rejects negative series counts instead of treating them as
  end-relative slices; zero still returns an empty palette and positive counts repeat.

- Colormap registration reuses exact package-owned maps on reload/retry and
  preflights static external collisions before adding missing maps.
- Preset switches preserve detectable caller edits on incoming-silent keys;
  temporary contexts restore preset ownership with native rcParams and semantics.
  Same-value native writes remain indistinguishable from preset residue.
- `set_decimal()` follows new ticks after data/view changes while retaining
  locators and Python fixed-point rounding. Proven non-string style/family name
  errors now raise descriptive `TypeError` before state changes.

- **`TICK_DECIMAL` now enforces axis-wide decimal consistency.** Mixed
  numeric tick labels such as `17.5, 20, 22.5` now warn as non-uniform,
  while fractional-step labels such as `17.5, 20.0, 22.5` remain valid.
  Trailing-zero advice now applies only to integer-valued tick sequences.
- A pixel size such as `dm.figsize("1920px", ...)` was answered with "Did you
  mean 'pt'"; the error now explains that pixels need a DPI and shows the
  `dm.inch(px / dpi)` conversion.
- Agent guidance matched the runtime again: the prompt corpus lists all ten
  aspect tokens (`slide` 16:9 was missing) and all seven presets, the a/b/c
  panel-label recipe draws each label once, the MCP prompts no longer say
  "dartwork-mpl 0.4", and the AI hub shows Codex's MCP support, drops the
  nonexistent `GEMINI.md` and states the real `llms*.txt` sizes. The
  "Be Specific" guide now treats vague requests ("make it look better") as
  normal ones.

## [0.5.6] - 2026-07-05

### Added

- **Color system v5**: a generative 91-parameter palette (16 families ×
  10 perceptually-equalized steps, `dc.{family}{step}`), 42 perceptually
  gated colormaps registered natively in matplotlib's colormap registry
  (`cmap="dc.aurora"` — no separate accessor), 2 CVD-verified categorical
  cycles (`dm.cycle()` — default 7-color screen/PDF cycle plus an 8-color
  print variant), and locale-aware semantic tokens (`dc.pos` / `dc.neg` /
  `dc.ref` / `dc.hl`) that resolve to the correct color regardless of
  red/green-for-gain-or-loss convention. An opt-in
  `dm.set_palette_version(5)` remaps the small set of v4/v5 name
  collisions (`dc.teal*` / `dc.indigo*` / `dc.gray*` 0-7) to their v5
  hex values; the default (`4`) keeps every existing script visually
  unchanged. Design spec:
  `docs/superpowers/specs/2026-07-03-color-system-v5-design.md`.
- **Math & special-character coverage.** The default mathtext stack now
  uses Noto Sans Math with STIX fallback, and the explicit plain-text
  fallback chain bundles Noto Sans Math plus Noto Sans Symbols 1/2 so
  labels render symbols such as `→`, `±`, `℃`, `∑`, `σ`, `⚠`, and `✓`
  without tofu. New guide: `docs/fonts/math_and_symbols.md`.
- **Deterministic SVG/PDF/SVGZ output by default.** `dm.save_formats`
  pins SVG ids with a stable `svg.hashsalt`, drops churning SVG/PDF
  timestamp metadata unless the caller supplies it, and writes SVGZ with
  gzip `mtime=0`, so unchanged figures re-render byte-identically.
- **Prompt and diagnostic convenience surfaces.** `dm.cycle_cycler` is
  exported at the package root, `dm.get_prompt("02-anti-patterns")` and
  `dm.list_prompts()` now include the YAML anti-pattern catalog, and
  `dm.font.list_registered()` / `dm.font.get_font_dir()` expose bundled
  font diagnostics for troubleshooting.

### Changed

- **Internal style presets now use the v5 categorical cycle.** Every
  named preset except `dark` / `dark-kr` (deferred to v5.1 — see the
  design spec §12) now cycles `dc.blue6 · dc.orange9 · dc.green5 ·
  dc.pink3 · dc.amber7 · dc.violet8 · dc.cyan8`, with the style layer
  automatically extending into `linestyle` (dash / dot) once a plot
  exceeds 7 series so reused colors stay distinguishable. The default
  `image.cmap` rcParam is now `dc.aurora` (the v5 colormap of that
  name — see "Changed (breaking)" below).
- **Bundled fonts win `findfont` ties.** Registered bundled faces are
  promoted ahead of identically-named system copies, so figures resolve
  to the shipped font files consistently across machines.
- **Palette migration codemod hardened.** `python -m
  dartwork_mpl._colors._migrate` rewrites prefixed removed-token names as
  visible diffs, preserves `dc.` / `dm.` namespace intent, reports
  bare-name palette calls for manual review, documents its exit codes,
  and offers `--no-advisory` for CI logs that do not need the ΔE table.

### Deprecated

- **All v4-only `dc.*` tokens** (`dc.vivid*`, `dc.pastel*`, `dc.0`
  through `dc.7`, and the rest of the 24-palette legacy catalog) are
  frozen at their existing hex values and now emit a one-time
  `DeprecationWarning` on first access; removal is planned no sooner
  than two minor releases out.

### Changed (breaking)

- **`dc.aurora` and `dc.teal_rose` renamed to `dc.legacy_aurora` and
  `dc.legacy_teal_rose`.** Both names are ceded to the new v5 colormap
  catalog, which ships a differently-tuned `dc.aurora`. Scripts that
  pass `cmap="dc.aurora"` or `cmap="dc.teal_rose"` will silently start
  rendering the v5 colormap after upgrading; use the `dc.legacy_*` name
  to keep the pre-v5 rendering.

### Security

- **MCP: closed a path-traversal hole in the template tools.** An
  unsanitized ``plot_type`` let ``render_template`` /
  ``render_template_advanced`` / ``compose_layered_plot`` escape the
  bundled template directory (``"../../.../x"``), turning them into
  arbitrary ``.py`` exec / read primitives. ``plot_type`` is now
  validated to a bare stem inside the template dir.
- **UI viewer: DNS-rebinding defense + stored-XSS fix.** The interactive
  viewer (``dartwork-mpl[ui]``) now enforces a ``Host`` allowlist, so a
  rebound ``evil.com -> 127.0.0.1`` page can no longer drive its
  side-effecting endpoints (``/api/reload`` execs, file writes) by
  matching Origin and Host. Color / range / number control widgets now
  HTML-escape the stored parameter value, closing a stored-XSS vector
  via crafted config / preset JSON.

### Fixed

- **UI viewer: matplotlib figures no longer leak on failed render /
  export.** ``/api/render``, ``/api/export`` and ``/api/save-server/image``
  close the figure in a ``finally`` so a ``savefig`` failure on these
  hot paths can't accumulate figures in pyplot's global registry.

### Changed

- **Visual: 24 of the 56 bundled colormaps regenerated** so the shipped
  assets match the gamut-safe OKLCH conversion introduced by the #240
  chroma-reduction fix (the committed txt files pre-dated it; channel
  deltas up to 0.41 on the most saturated anchors). The generator ↔
  asset reproducibility is now pinned by
  ``tests/test_cmap_sources_consistency.py``.
- **Visual: ``day_night`` and ``synthwave`` colormaps regenerated** to
  reflect the ``cspace`` achromatic-hue fix below (they interpolate
  through a near-black/near-white endpoint whose hue was previously
  floating-point noise).

### Fixed

- **``cspace`` OKLCH ramps from achromatic endpoints.** White / black /
  grey endpoints carry a meaningless atan2-noise hue; ramps like
  ``cspace("white", "oc.blue9")`` returned green/teal midpoints. Per CSS
  Color 4, a near-zero-chroma hue is now treated as missing and the
  other endpoint's hue is carried.
- **``simple_layout`` geometry.** Inverted axes no longer drop their tick
  labels (the view interval is sorted); figure-level artists
  (``suptitle`` / ``fig.legend`` / ``fig.text``) are measured so axes
  content is not laid on top of them; a figure with no GridSpec
  (``fig.add_axes``) now warns instead of silently doing nothing.
- **Style preset switching.** Switching presets no longer leaks the prior
  preset's rcParams (franken-theme); a preset that declares a key to
  matplotlib's default value now wins over a pre-existing user value; the
  underscore kwarg form works for rcParams whose canonical name contains
  an underscore (e.g. ``legend_title_fontsize``); ``load_style_dict``
  unwraps quoted values (``"#1e1e1e"`` → ``#1e1e1e``).
- **Validation / lint engine.** ``apply_lint_fixes`` no longer rewrites
  inside string literals / comments, preserves the receiver of
  ``<fig>.tight_layout()``, and no longer double-counts issues; the
  geometric checks stop firing false positives on the library's own
  flush ``simple_layout`` output (``CLIPPED_TEXT``), on off-view phantom
  ticks (``CROSS_AXES_OVERLAP`` / ``TICK_CROWD``), and on legend-only
  panels (``EMPTY_AXES``); ``OVERFLOW`` / ``LEGEND_OVERFLOW`` now see
  figure-level text and off-canvas legends; a check that errors no longer
  lets the figure be reported "clean".
- **Color gate integrity.** CVD and contrast gate checks now compare
  unrounded threshold values, avoiding false passes/failures caused by
  display-rounded numbers in reports and docs.
- **Misc correctness.** ``import dartwork_mpl`` no longer deletes
  matplotlib's global ``xkcd:*`` colours; ``mix_colors`` rejects
  out-of-range ``alpha``; ``check_figure_quality`` recognises
  bar/histogram/pie/imshow as data; ``validate_data`` accepts categorical
  x instead of crashing; the millions/billions formatters never render
  ``-0.0M``; ``arrow_axis`` validates ``direction``; ``label_axes`` labels
  grids larger than 26 panels; ``dm.config`` rejects typo'd attributes;
  ``save_and_show`` handles PNG/PDF paths (and the quickstart's
  extensionless one) instead of raising a raw XML error;
  ``classify_colormap`` no longer mislabels ``Spectral`` as categorical.
- **Docs asset normalization.** Generated documentation figures and
  static SVG/PDF/SVGZ assets are normalized through the reproducible
  export path, reducing meaningless artifact churn in docs-only changes.

### Added

- **Bundled font corpus expanded to 16 families** (204 files), including
  four monospace families (IBM Plex Mono, JetBrains Mono, Source Code
  Pro, Roboto Mono), with eager registration on import so every family
  resolves by bare rcParam name immediately (#370).

## [0.5.5] - 2026-07-01

> **Never released.** No `v0.5.5` tag and no PyPI distribution exist; these
> changes shipped as part of 0.5.6. `pip install dartwork-mpl==0.5.5` fails.

### Changed

- **BREAKING — categorical palette system overhaul.** A judge-panel redesign
  (rigor / naming / editorial / accessibility lenses) reworked the 24 curated
  palettes for a more coherent, intuitive, better-covered set. Every palette is
  still CIELAB-generated on an even-L* ladder and CVD + B&W verified.
  - **Renames**: `spectrum` → **`vivid`** (the palette you reach for by that
    name), `coolwarm` → **`cool_warm`** (uniform diverging underscore).
  - **Merges** (redundancy cut): `bold` folded into `vivid`; `corporate` folded
    into `trustworthy`.
  - **Removed**: `warm_cool` (weakest under CVD, redundant with the stronger
    `blue_orange` / `teal_coral` duos).
  - **Re-designed**: `pastel` / `dusty` are now an intentional high-key /
    low-key pair (shared hue plan, different L* band) instead of near-duplicates.

### Added

- **`neon`** — max-chroma electric categorical (the loudest legal set); CVD-safe
  because confusable hues are thrown far apart on the L* ladder.
- **`ember`** — warm-vibrant categorical; fills the warm gap (`earth` was the
  only warm palette but muted).
- **`purple_green`** — tritan-robust diverging (the axis `cool_warm` /
  `teal_amber` lack, both of which drift warm under tritanopia).

Migration: `dc.spectrum*` → `dc.vivid*`, `dc.bold*` → `dc.vivid*`,
`dc.coolwarm*` → `dc.cool_warm*`, `dc.corporate*` → `dc.trustworthy*`,
`dc.warm_cool*` → `dc.blue_orange*`.

## [0.5.4] - 2026-07-01

> **Never released.** No `v0.5.4` tag and no PyPI distribution exist; these
> changes shipped as part of 0.5.6. `pip install dartwork-mpl==0.5.4` fails.

### Removed

- **BREAKING — the 7 legacy `dc.*` palettes are gone.** `Vivid`, `Sunset`,
  `Ocean`, `Pop`, `Cyber`, `Autumn`, and `Nordic` were deprecated back-compat
  aliases; they no longer resolve (`dc.ocean2`, `dc.nordic1`, … now raise the
  usual "not a valid color" error). All docs examples, prompt templates, and
  build scripts were migrated to curated palettes with the shade index
  preserved: `vivid→bold`, `sunset→earth`, `ocean→teal`, `pop→spectrum`,
  `cyber→jewel`, `autumn→dusty`, `nordic→teal_indigo`. `dc_palettes.json`
  drops from 32 to 25 keys (24 curated + the `dc.0-7` default). (#367)
- **BREAKING — deprecated aliases removed (no debt carried forward).**
  - `dm.auto_layout` → use `dm.simple_layout(fig, margin=...)` (the legacy
    `padding` inches arg maps to `margin`; `max_iter`/`tolerance` were
    obsolete). Now raises a migration-hint `AttributeError`.
  - `dartwork_mpl.helpers.formatting` module → `dartwork_mpl.helpers.labels`.
  - `dartwork_mpl.asset_viz` module → `dartwork_mpl.diagnostics`.
    Both removed modules now raise `ModuleNotFoundError`.
  - MCP resource aliases `dartwork-mpl://guide/general-guide` and
    `…/guide/layout-guide` → use `…/guide/agent-entry` and `…/guide/policy`.
  - `ui._config.append_history` / `load_history` → `save_preset` /
    `load_presets`. (#368)

### Added

- **`get_palette` gains `order` / `reverse` / `seed`.** Re-arrange a picked
  palette by lightness or a reproducible shuffle, or reverse it — the same
  controls the docs palette explorer exposes, so its snippets run verbatim.
- **In-repo categorical palette explorer** — an inline, de-nested generator
  builds the interactive explorer widget from the palette SSOT so it can
  never drift from what the package registers.
- **Integrity gates**: a release test-gate (tests must pass before build), a
  richer no-extras smoke test that exercises the core render path, positive
  validation of `dm.figsize` heights, and render coverage for every bundled
  plot template. A regression test also guards that `gen_palettes.py`
  reproduces the committed CIELAB SSOT byte-for-byte.

### Changed

- **The 24 categorical palettes now use consistent snake_case names**
  (`teal_seq→teal`, `focus→teal_accent`, `focus_warm→coral_accent`,
  `muted→pastel`, `teal_amber_div→teal_amber`, …).
- **Single source of truth for the 7 colour libraries.** A `COLOR_LIBRARIES`
  registry drives the prefix / label / order lists that the loader, the MCP
  server, diagnostics, and the docs asset generator used to hard-code
  separately.
- Docs build pinned to Python 3.12; asset *data* now folded into the
  gallery / doctree cache keys so a palette change busts stale renders.

### Fixed

- Six correctness/consistency bugs from a codebase audit: `list_palettes`
  now shows multi-word palettes, `make_palette(highlight=…)` emphasises the
  right series for sequential/diverging kinds, and several stale doc/asset
  references were corrected.
- `set_cycle(..., ax=None)` now writes the global colour cycle under the same
  lock `style.use` uses; `optimize_legend` loads the dartwork colours itself
  instead of relying on an import side effect.
- MCP: the advanced-tier template resource is registered and the emitted
  template URIs line up with what resolves.
- CI docs build: a legacy alias (`dc.nordic1`) failed colour resolution on the
  Linux runner during gallery execution — removing the deprecated palettes
  eliminates the failing surface.

## [0.5.3] - 2026-06-20

### Added
- **18 tier-2 advanced plot templates** under
  `asset/prompt/05-templates/advanced/` — one per existing basic template
  (bar, line, scatter, histogram, heatmap, …). Each ships with synthetic
  but realistic data, an OKLCH gradient (`dm.cspace`) sequence, value
  labels, reference lines / annotation overlays, a narrative title with
  takeaway subtitle, a source footnote, and an end-of-script
  `dm.validate_with_fixes` + `dm.check_figure_quality` chain. The tier-1
  basic templates remain the minimal "what does the API look like"
  examples; tier-2 demonstrate the full publication-ready layered
  composition pattern. Rendered into the Sphinx gallery as a new
  section. (PR #349)
- **3 new MCP tools** on the `dartwork-mpl-mcp` server:
  - `suggest_chart_type(x_type, y_type, n_points, n_series)` — returns a
    `{recommended, basic_template_uri, advanced_template_uri, rationale}`
    record so an agent can pick a chart type from data shape before
    writing any code.
  - `compose_layered_plot(plot_type, layers, tier)` — returns the chosen
    template plus an `{applied, missing}` checklist of layered
    composition elements (gradient sequence, value labels, reference
    lines, narrative title, …), nudging agents toward the full pattern
    rather than the minimal basic.
  - `render_template_advanced(plot_type, return_format, timeout)` —
    tier-2 sibling of `render_template`, with automatic basic-tier
    fallback when an advanced template is missing
    (`status: "ok" | "fell_back" | …`).
- **`chart_type_hint` argument on `validate_generated_plot`** —
  surfaces semantic warnings (pie with >7 slices, scatter with <5
  points, bar without value labels, line that produced no `Line2D`,
  histogram with <10 bins) in addition to the existing lint + execution
  + visual-validation chain. (PR #349)
- **`tier` argument on `find_template`** (Python API + MCP wrapper) —
  `"basic"` / `"advanced"` / `"all"` scope the metadata index search to
  the tier-1, tier-2, or both buckets. Default is unchanged
  (basic-only, no `tier` field on results) so existing callers see no
  difference. (PR #349)

### Changed
- **`create_plot` MCP prompt overhauled.** Now opens with a
  pre-flight tool-call sequence (`suggest_chart_type` →
  `render_template_advanced` → `find_template(tier="advanced")`),
  documents the advanced-tier APIs an agent should reach for
  (`dm.cspace`, `format_axis_si` / `_millions` / `_currency`,
  `label_axes`, `simple_layout` margin guidance,
  `validate_with_fixes`, `check_figure_quality`,
  `axhline` / `axvline` / `axvspan` / `annotate`), an explicit hairline
  policy (`dm.lw(-1)` collapses to 0.0 — use 0.3 / 0.5 literals when a
  hairline is intentional), and ships a tier-2 skeleton that follows
  the full layered pattern. The skeleton still passes the existing
  validation chain — `chart_type_hint` is wired through. (PR #349)

### Fixed
- **`dartwork_mpl_info()` no longer hardcodes `"version_surface": "0.4"`.**
  Reads the installed package version via `importlib.metadata.version`
  and reports the `major.minor` (e.g. `"0.5"`). Same registry-derivation
  principle used elsewhere — the advertised surface tracks the actual
  release instead of a hand-maintained literal that silently drifts.
  (PR #344)

### Docs / Design
- **`docs/` design system overhaul (Tiers 1 → 6).** Eight design
  refresh PRs (#332–#339) landed without touching any runtime Python:
  - Tier 1: heading + strong weight ladder one step lighter
    (bold → semibold → medium), neutral fills removed from inline
    code / kbd / cards / quotes.
  - Tier 2 + 3: widget chrome flattened, designer chrome separated
    from content, hero made solid.
  - Tier 4: flat underline tabs, before/after order reversed, less
    personal phrasing across narrative blocks.
  - Tier 5 + 6: universal widget unification, body column widen,
    mermaid renderer rebuilt, validator harness overhauled.
  - **Diagram PoC** (#338 → #339): five-library shootout, system
    architecture diagram, auto-extracted module graph; mermaid
    upscaling fixed, Excalidraw dropped, PoC examples made real.
  - **Colormap explorer redesign** (#335 → #336): hybrid explorer,
    Design System page flattened to four siblings.

## [0.5.2] - 2026-06-09

### Added — internal audit notes (issues #310 / #311 / #313)
- **`docs/development/config-roadmap.md`** — `dm.config` expansion
  roadmap: walked every `dm.__all__` bool / `Literal` kwarg, classified
  into "Add to config now" (6 fields surfaced for issue #304), "Add
  later" (5), "Per-call only" (8 patterns), and "Should be a preset
  attribute" (0). Output of issue #311 (B19), input to issue #304
  (M1). Excluded from the public docs build via
  `conf.py:exclude_patterns`.
- **`docs/development/naming-audit.md`** — naming convention audit of
  all 78 `dm.__all__` entries grouped by prefix family (`list_`,
  `plot_`, `validate_`, `format_axis_`, etc.), sibling-set
  completeness checks, verb consistency for action helpers,
  abbreviation collision review. Conclusion: no renames in 0.x → 1.0
  transition; track `arrow_axis` rename alongside the eventual
  `dm.add_grid` (#302). Output of issue #310 (C9).
- **`docs/development/path-handling-audit.md`** — investigation of the
  suspected sub-path-deployment issue with sphinx-gallery thumbnail
  paths (issue #313, D23). Verified `.. image:: /...` directives are
  *srcdir-absolute*, not URL-absolute; sphinx emits HTML-relative
  URLs (`../_images/sphx_glr_*.png`) that resolve correctly under
  every base URL. False alarm; no code change required. Documents
  the watch-points that would re-open the question.

### Changed
- **Preset `savefig.dpi` default lowered from `500` → `300`.** Print-grade
  300 DPI is a sensible export resolution for nearly every use case and
  matches the existing `figure.dpi: 300` so screen and saved output now
  agree. Applies to `base`, `dmpl`, and `dmpl_light` mplstyle (all
  preset stacks inherit from one of these). The 500-DPI default was
  inherited from an early hardcopy-print bias and produced gratuitously
  large PNG files for everyday work. Callers who genuinely want 500 DPI
  pass it explicitly (`dm.save_formats(fig, "out", dpi=500)`) or use
  `dm.dpi(4)` (300 + 4 × 50). The `dm.dpi(n=0)` ladder docstring is
  refreshed accordingly.

### Added
- **`docs/usage_guide/config.md`** — a hands-on cookbook for the
  `dm.config` singleton: when to set a project-wide default, when to
  scope with `dm.config.override(...)`, when to override per-call, how
  the resolution chain works (per-call kwarg → `dm.config` → library
  default), and the typo-fails-loud `AttributeError` guarantee. Wired
  into the `usage_guide` toctree between Save and Validation and
  Extended Plots & Diagnostics.
- **`dm.dpi(n=0)`** — preset-relative save-resolution helper, completing
  the `fs` / `fw` / `lw` quartet. Reads `rcParams['savefig.dpi']` and
  applies a 50-DPI ladder step per `n` so writing
  `dm.save_formats(fig, "out", dpi=dm.dpi(1))` upgrades cleanly when the
  preset changes. Handles matplotlib's `"figure"` sentinel and quoted-
  string DPI values transparently; clamps to 1 DPI on large negative
  steps. (audit-F7)
- **`dm.config.warn_on_orphan_tick_adoption`** — `False` by default.
  Set to `True` to emit a `UserWarning` whenever orphan-tick font
  adoption actually mutates a figure during `simple_layout` /
  `save_formats` / `save_and_show`. Useful when debugging unexpected
  tick changes after a save, or running under
  `constrained_layout` where the font change can trigger a re-layout
  on the next draw. (audit-M7)

### Refactor
- **`dartwork_mpl.validate` is now a package, not an 870-line god-file.**
  The nine visual checks (`OVERFLOW`, `OVERLAP`, `LEGEND_OVERFLOW`,
  `TICK_CROWD`, `EMPTY_AXES`, `MARGIN_ASYMMETRY`, `PIE_LABEL_OFFSET`,
  `CLIPPED_TEXT`, `CROSS_AXES_OVERLAP`) each live in their own file
  under `validate/_checks/`; shared types (`Severity`, `VisualWarning`,
  `BBOX_ERRORS`) live in `validate/_types.py`; the orchestrator lives
  in `validate/_orchestrator.py`. Public API is unchanged — every name
  re-exported by the old module is re-exported by the new
  package's `__init__.py`. Each module is now ≤200 lines instead of
  one ≥870-line wall. (audit-H4)
- **`simple_layout` extracted `_solve_layout_step()`.** The per-iteration
  solver logic (canvas draw → orphan-tick adoption → axes-content
  measurement → edge arithmetic → clamp → delta-px) is now a single
  function. `simple_layout`'s body reads as the high-level "iterate
  until converged" pattern and the step can be exercised in isolation
  from the convergence loop. Byte-identical behaviour. (audit-H5)
- **`validate_fixes`: per-check fix-handler registry.** The 8-branch
  `if/elif` in `get_fix_suggestions` (one branch per `check_id` string)
  is now a `dict[check_id, handler]` populated by a `@register_fix(...)`
  decorator. Adding a new check needs one decorator instead of editing
  the dispatcher. Duplicate registrations raise so the table stays
  deterministic. Pattern mirrors `lint.py`'s `Rule` objects.
  (audit-M5)
- **`validate_fixes.auto_apply`: narrow the catch around `dm.simple_layout`.**
  Replaced `except Exception` (with a `BLE001` noqa) with
  `(RuntimeError, ValueError, AttributeError, TypeError)` — the actual
  failure modes documented in `simple_layout`. `KeyboardInterrupt`,
  `MemoryError`, and silent regressions in `simple_layout` now escape
  the helper instead of being swallowed as "fix failed, carry on."
  (audit-C14)
- **`layout.py`: type the `Any` escape hatches.** `_resolve_gridspec`
  walker is now typed `GridSpecBase | SubplotSpec | None` (matplotlib's
  stubs widen `SubplotSpec.get_gridspec()` to the base class) with a
  final `isinstance(GridSpec)` narrowing at the return. `_copy_label_font`
  now declares both arguments as `matplotlib.text.Text`. The `Text`
  import lives in the `TYPE_CHECKING` block alongside the existing
  `Axes` / `RendererBase` lazy imports. (audit-M6)

### Fixed

- **Actionable error messages for missing styles, presets, and icon
  fonts.** Previously `style_path("scien")` raised
  ``ValueError: Not found style: scien``, `dm.style.use("reort")`
  raised ``KeyError: "Preset 'reort' not found"``, and `icon_font_path
  ("fasolid")` raised ``ValueError: Unknown icon font 'fasolid'.
  Available: fa-brands, fa-regular, fa-solid, mdi`` — none enumerated
  the styles list and no site offered a "did you mean" hint. All
  three now (a) list the available names and (b) when the input is
  close to an existing entry, append ``Did you mean 'X'?``. Format
  matches across the three sites for consistency. (audit-Q6)
- **`dm.style.use` / `dm.style.stack` now preserve user-set rcParams**
  that the chosen preset does not itself touch. Prior to this, every
  preset switch ran `rcParams.update(rcParamsDefault)` which silently
  dropped any caller configuration except `svg.hashsalt` (the one
  key that had a hand-crafted preserve path). User settings like
  `pdf.compression`, `axes.unicode_minus`, `webagg.port`, …
  disappeared. The new logic snapshots every rcParam whose value
  differs from the matplotlib default, applies the preset, and then
  restores each snapshot entry that the preset is silent on. Where
  the preset and the user disagree (e.g. `font.size`), the preset
  still wins. (audit-B1)

### Added

- **Four new aspect tokens** — `tall` (2:3 portrait), `a4` (1:√2 ISO
  216), `slide` (16:9 widescreen), and `panoramic` (3:1 long banner) —
  join the existing six, so `dm.figsize(width, aspect)` reaches
  presentation slides, ISO paper, mobile-first portrait, and banner
  sparklines without forcing the user to hand-pick a numeric ratio.
- **`dm.list_aspect_tokens()`** — discovery view returning a copy of
  the registry sorted from tallest (`tall`) to widest (`panoramic`).
  Mutating the returned dict does not leak into the singleton. Useful
  for notebooks and AI agents that want to enumerate valid aspect
  strings without scraping source. (audit-Q9)

- **`dm.config` — process-wide defaults for dartwork-mpl behaviour
  toggles.** A singleton (`dataclass`-backed) whose attributes are
  read by every public-API call site that exposes a matching keyword.
  Today it carries one attribute, `adopt_orphan_tick_font` (default
  `True`, matching prior behaviour). Set `dm.config.adopt_orphan_tick_font
  = False` once near the top of your program to flip the default of the
  matching keyword on `dm.simple_layout`, `dm.save_formats`, and
  `dm.save_and_show` everywhere — no need to thread the keyword through
  each call site. Per-call overrides still win (pass the keyword
  explicitly). A `with dm.config.override(...)` context manager scopes a
  change to a block and always restores prior state, including on
  exception. Unknown field names raise `AttributeError` so a typo can't
  silently shadow the singleton.
- **`save_and_show(close_figure=True)` opt-out keyword.** The function
  unconditionally called `plt.close(fig)` before — surprising notebook
  users who wanted to keep editing the figure. Pass `close_figure=False`
  to keep the figure registered in `plt.get_fignums()`. Default
  unchanged. (audit-Q1)
- **`save_formats(validate_quiet=False)` opt-out keyword.** When
  `validate=True`, the visual check still runs but `[VISUAL]` stdout
  output is suppressed. Threads through to `validate_figure(quiet=...)`.
  Default unchanged. (audit-Q2)
- **README "Common pitfalls" section** mirrors the anti-pattern top 3
  from CLAUDE.md / quickstart (raw `figsize=(w, h)` tuple,
  `plt.tight_layout()`, raw `fontsize=` / `linewidth=` literals).
  (audit-Q5)
- **"Next →" navigation on `styles.md` and `colors.md`** matching the
  existing pattern on `layout.md` and `save_export.md`. Threads the
  prose reading sequence quickstart → styles → colors → layout →
  save_export → extras. (audit-Q8)

### Changed
- **Default of `adopt_orphan_tick_font` on `dm.simple_layout`,
  `dm.save_formats`, `dm.save_and_show` is now `None` (sentinel)** —
  when `None`, the value is read from `dm.config.adopt_orphan_tick_font`
  (default `True`, same as before). Passing `True` / `False` explicitly
  behaves exactly as before, so every existing call site is unaffected.
- **`dm.auto_layout`, `dartwork_mpl.asset_viz`, and
  `dartwork_mpl.helpers.formatting`** name **v0.6.0** as the removal
  target in their `DeprecationWarning` messages instead of "a future
  release". No code is removed in this release; the alias layer still
  works. (audit-Q7)

### Refactor
- **`_helpers.get_renderer(fig)`** centralises five repeated
  `fig.canvas.get_renderer()  # type: ignore[attr-defined]` sites across
  `annotation.py`, `layout.py` (×3), and `validate.py`. Future
  matplotlib stub / mypy changes touch one place instead of five.
  Behaviour unchanged. (audit-Q3)

### Fixed
- **`validate_fixes.py` LEGEND_OVERFLOW branch** removed a dead
  `warning.detail.get("ratio", 0)` lookup that discarded the result.
  Behaviour unchanged. (audit-Q4)

## [0.5.1] - 2026-06-08

### Fixed
- **`Color.from_rgb` rejects a 0-1 value mixed into 0-255 channels.** When
  any channel is `> 1.0` the call is read as 0-255; a fractional channel
  (`0 < v < 1`) passed alongside it — e.g. `from_rgb(255, 0.5, 0.1)` — now
  raises `ValueError` instead of silently dividing the fractional channels
  by 255 into a near-black, distorted color. Completes the existing
  "don't mix ranges" guard, which previously only caught values `> 255`. (#236)

## [0.5.0] - 2026-06-08

### Removed (breaking)
- **`install_llm_txt` / `uninstall_llm_txt` (and `INSTALL_TARGETS`) are
  removed.** They copied the bundled prompt corpus into IDE-specific
  folders — a job now better served by the MCP server (runtime
  `dartwork-mpl://guide/*` resources) and the repo-root onboarding files
  (`AGENTS.md`, `CLAUDE.md`, `llms.txt`, `llms-full.txt`). **Migration:**
  non-MCP users resolve the corpus with `dm.agent_doc_path(name)` /
  `dm.get_agent_doc(name)` (accepts `"AGENTS"`, `"CLAUDE"`, `"llms"`,
  `"llms-full"`) and copy it into their tool's context location. (#170)
- **`ipython` is no longer a core dependency.** Only `dm.show()` (inline
  SVG display in Jupyter) needs it, so it moved to a `notebook` optional
  extra — `pip install "dartwork-mpl[notebook]"`. This drops ~30 MB of
  IPython transitive dependencies (`prompt_toolkit`, `jedi`, `traitlets`,
  `stack_data`, …) from every non-notebook install of this matplotlib
  styling library. `dm.show()` now raises a clear `ImportError` naming
  the extra when IPython is absent; every other entry point is
  unaffected. **Migration:** notebook users add the `[notebook]` extra
  (or install `ipython` directly). (#248)

### Changed
- **Color assets load via `importlib.resources`** instead of an
  `__file__`-relative filesystem path, so palette loading works even when
  the package is imported from a zip / non-extracted wheel. No change to
  the colors registered. (#236)
- **`cspace` accepts every string form `dm.color` does.** String
  endpoints now route through the unified `Color(...)` parser, so
  `cspace("oklch(0.7, 0.15, 30)", ...)` and `rgb(...)` work — previously
  only hex and palette names were accepted (oklch/rgb strings raised). (#236)
- **Agent-facing validation heuristics hardened (`check_agent_requirements`,
  `TICK_CROWD`).** `style_applied` is now figure-local — it inspects the
  figure's own text artists instead of the process-global `plt.rcParams`
  (which any later `style.use` / `rcdefaults` mutates independently of the
  figure under test). `proper_colors` now flags full color names
  (`"red"`, `"green"`, …) and patch (bar/area) facecolors, not just
  single-letter codes on lines. The `TICK_CROWD` visual check measures
  each label's real rendered extent — so it scales with font size, weight,
  rotation, and text length — instead of a fixed 4 ticks/inch density that
  ignored font size (it falls back to the density only when extents are
  unmeasurable). (#236)
- **`diagnostics` is now a package** (`_colormaps` / `_colors` / `_fonts`
  submodules) instead of a single 1309-line module (#235). Purely
  internal — the public API (`classify_colormap`, `plot_colormaps`,
  `plot_colors`, `plot_fonts`) and every existing import path
  (`dartwork_mpl.diagnostics.*`, the top-level namespace, the deprecated
  `asset_viz` alias) are unchanged.
- **UI viewer pins the Lucide icon CDN** to `lucide@1.17.0` (explicit
  UMD path) instead of `@latest`, for reproducible builds and
  supply-chain safety. (#236)
- **Examples gallery curated.** Trimmed three redundant/weak creative
  pieces (`flow_radial_burst`, `geometric_penrose_tiling` — which wasn't
  actually a Penrose tiling — and `particles_flow_dynamics`, a near-dup of
  `flow_quantum_dynamics`); renamed the three `plot_auto_layout_*` layout
  examples to `plot_simple_layout_*` (their code already used the current
  `simple_layout`, not the deprecated `auto_layout`); and fixed several
  example issues — the `plot_simple_layout` docstring claimed a
  non-existent "L-BFGS-B optimizer" (it is a direct measure→place calc),
  the margin-buffer example now renders two figures so it actually shows
  default-vs-`margin="2%"`, oversize (>17 cm) creative figures were
  brought to ≤17 cm, an invisible `dm.lw(-1)` baseline became a `0.5`
  hairline, and `plot_named_palettes` now uses the `oc.*` token its prose
  advertises. (#236)
- **Docs build caches the sphinx-gallery output in CI.** The generated
  gallery tree (`docs/examples_gallery/`, including each example's
  `.py.md5` stamp) is now cached and restored, so a build whose example
  sources and library code are unchanged skips the 70+ example
  executions that dominated the build (~9 min → ~1 min). The cache key
  folds in the example sources, package source, `conf.py`, the build
  hooks, and the lockfile, so any change forces a fresh, full rebuild —
  no stale images. A new `PLOT_GALLERY=0` env var skips gallery
  execution entirely for fast local prose/layout previews. (#249)
- **Docs gallery executes examples in parallel** (sphinx-gallery
  `parallel=True`, backed by a new `joblib` dev dependency). This speeds
  up the *cache-miss* builds the output cache can't help — a full cold
  build dropped from ~9 min to ~3.5 min locally. Each example runs in its
  own worker process, so the global rcParams a `dm.style.use(...)` mutates
  can't leak between examples (stricter isolation than the serial path);
  the generated gallery is gitignored, so worker-order differences never
  dirty the repo. Falls back to serial if joblib is unavailable. (#249)
- **UI viewer template split out of the 1.5k-line god-file.** The CSS and
  client-side JS that `_template.get_html` inlined now live in sibling
  `_styles.py` (`CSS_BLOCK`) and `_scripts.py` (`JS_BLOCK`) modules as
  *plain* strings — real CSS `{ }` and JS `${...}` template literals
  instead of the f-string's doubled `{{ }}` / `${{ }}` "escape hell".
  `_template.py` drops from 1548 to 214 lines and just assembles the two
  blocks, interpolating only the (HTML-escaped) `title`. Purely internal:
  `get_html(...)` output is byte-for-byte identical (verified across
  default / XSS / plain titles) and no public API changes. (#236)
- **`dartwork_mpl_info` now derives its advertised MCP catalog
  dynamically** instead of from hand-maintained literals. The `tools`
  and `resources` (and `prompts`) lists are scanned from the
  decorator source of `tools.py` / `resources.py` / `prompts.py`, and
  the `plot_templates` / primitive `style_presets` lists are globbed
  from the bundled `asset/` directories. Adding a tool, resource, or
  template can no longer silently drift the `dartwork_mpl_info`
  catalog out of sync with the live registry. This also fixes a latent
  omission — `dartwork-mpl://guide/anti-patterns` was missing from the
  previously hardcoded `resources` list and is now advertised. (#236)

### Fixed
- **`Color.from_rgb` validates its input** instead of silently producing
  an out-of-gamut color. Non-finite (`NaN`/`inf`) and negative channels
  are rejected, and once the auto-detect heuristic reads values as 0-255
  (any channel > 1.0) a channel > 255 now errors rather than normalizing
  to > 1.0. (#236)
- **`dm.fw(n)` honours its `-> int` contract for fractional `n`.** A float
  step (e.g. `fw(0.5)`) used to return a float; the result is now rounded
  to an int (matplotlib font weights are integers). (#236)
- **`icon.ensure_loaded` is thread-safe** — it gained the same
  double-checked `threading.Lock` as `font.ensure_loaded` /
  `cmap.ensure_loaded`, so concurrent first use can't register the icon
  fonts twice. (#236)
- **`check_figure_quality` DPI threshold matches its advice.** The check
  flagged DPI `< 150` while the message said "at least 200"; both now use
  a single `_MIN_RECOMMENDED_DPI = 200` constant (aligned with
  `check_agent_requirements`' `high_dpi` bar). (#236)
- **Lint anti-pattern catalog + auto-fix table corrected (`lint.py`,
  `02-anti-patterns.yaml`).** Removed a dead, semantically wrong
  `apply_lint_fixes` entry that referenced the non-existent rule_id
  `cm2in-call` and rewrote `dm.cm2in` → `dm.cm` (the two are not
  interchangeable — `cm2in` returns inches, `cm` a `Length`); the legacy
  token is now left for `migrate_legacy_code`. A new test asserts every
  auto-fix rule_id exists in the SSOT catalog. The
  `multirow-subplots-no-gridspec-kw` detector now catches line-wrapped
  `plt.subplots(` calls (a bounded look-ahead for `gridspec_kw` /
  `sharex` / `sharey`) instead of only single-line ones. Corrected two
  catalog messages that said `style_spines` / `auto_select_colors` were
  removed/renamed "in 0.5.0" — they shipped in 0.4.1 (#156). (#236)
- **`validate_with_fixes(auto_apply=True)` applies `simple_layout` once.**
  It previously called the whole-figure layout solver once *per*
  OVERFLOW / MARGIN_ASYMMETRY warning, re-running it redundantly and
  listing N identical "Applied simple_layout" entries for a single
  mutation. (#236)
- **Docs `viz_example` asset now renders** (long-standing intermittent
  docs-build failure). `_save_viz_example` passed `dm.cm(15)` / `dm.cm(10)`
  — `Length` objects, not float subclasses since 0.4.x — straight to
  `fig.set_size_inches`, so matplotlib built an object-dtype size array
  and raised `ufunc 'isfinite' not supported`; the SVG was never written
  and the `-W` build aborted on the missing figure. It now sizes via
  `dm.figsize("15cm", "10cm")` (inch floats). As defense-in-depth, the
  API asset builder retries each generator once and drops a visible
  placeholder SVG on final failure so a single bad asset can never abort
  the whole docs build. (#235)
- **UI export endpoints fail cleanly on bad input.** `/api/export/{fmt}`
  and `/api/save-server/image/{fmt}` validate `fmt` against matplotlib's
  supported filetypes and return **400** for an unknown format instead of
  a 500 from `savefig`. The export / script / save-server endpoints build
  the param model through a checked helper that returns **422** for
  invalid params (parity with `/api/render`, which already did). UI
  presets and config are written atomically (temp file + `os.replace`) so
  a racing reader/writer can't observe a half-written JSON file. (#236)
- **Out-of-gamut OKLCH colors are now gamut-mapped preserving L and h**
  (behavior change for out-of-gamut colors). `Color.to_rgb` previously
  clamped each linear-sRGB channel independently, which shifted the
  requested lightness *and* hue — e.g. `from_oklch(0.7, 0.4, 30).to_hex()`
  returned `#ff0000` (OKLCH ≈ 0.628 / 29.2). It now reduces chroma while
  holding L and h fixed (binary search to the sRGB gamut boundary, CSS
  Color 4 style): the same color maps to `#ff6551` (OKLCH 0.700 / 30.0,
  chroma 0.40 → 0.19). In-gamut colors are unchanged; only colors for
  which `in_gamut()` is `False` render differently. (#240)
- **`fetch_github_document` now surfaces the underlying error detail**
  (`<ExcType>: <message>`) instead of only the exception type name, so
  an agent can tell a `404` apart from a timeout or DNS failure and
  self-correct rather than retrying blind. (#236)
- **`mix_colors` validates `ratio` before blending.** A non-finite
  (`NaN`/`inf`) or out-of-`[0, 1]` ratio extrapolated past the two
  endpoints, producing RGB outside `[0, 1]` and a malformed hex (or a
  leaked matplotlib "RGBA values should be within 0-1 range" error).
  The ratio is now rejected up front with an actionable message. (#236)
- **`style.use` now preserves a caller-set `svg.hashsalt`** across its
  internal `rcParams`-default reset. Previously every preset switch restored
  matplotlib's default (`None` → uuid4 element ids), so any SVG saved after a
  `style.use` call had non-deterministic element ids even when the salt was
  pinned for reproducible output. Setting `svg.hashsalt` now yields
  byte-identical SVGs across rebuilds. (The docs build pins the salt +
  `SOURCE_DATE_EPOCH` so its generated SVG assets stop dirtying the tree.)
- **Removed names raise a migration hint, not a bare `AttributeError`.**
  `dm.subplots`, `dm.figure`, `dm.agent_utils`, `dm.xplot` (removed in
  0.4) and `dm.install_llm_txt` / `dm.uninstall_llm_txt` /
  `dm.INSTALL_TARGETS` (removed in 0.5) fell through `__getattr__` to
  Python's generic "module has no attribute" string. Each now raises an
  `AttributeError` naming the version it was removed in and the
  replacement API — the contract `CLAUDE.md` / `AGENTS.md` advertise,
  previously honoured only by the 0.3 width / `FS_*` / `cm2in` tokens. (#236)

## [0.4.2] - 2026-06-03

### Added
- **`dm.adopt_axis_label_font(fig)`** — when an axis carries tick labels
  but no axis label, its tick labels (major and minor) and scientific
  offset text adopt that axis's label font (size, weight, family,
  style; color is preserved). The x and y axes are judged
  independently, so an axes with a y-label but no x-label restyles only
  the x tick labels. Reads the font from the (possibly empty) axis-label
  Text object, so repeated application is idempotent.

### Changed
- **`simple_layout` (and therefore the deprecated `auto_layout`) now
  applies `adopt_axis_label_font` by default** via the new
  `adopt_orphan_tick_font=True` parameter. Tick labels on an axis with
  no label render in the (heavier) axis-label style for correct visual
  hierarchy. The adoption runs before each iteration's margin
  measurement so the layout still fits the restyled ticks. Pass
  `adopt_orphan_tick_font=False` to opt out.
- **`save_formats` and `save_and_show` also apply `adopt_axis_label_font`
  by default** (same `adopt_orphan_tick_font=True` parameter, keyword-only)
  so the saved/displayed output always reflects the adoption even when
  `simple_layout` was never called. Together with `simple_layout`, this
  makes orphan-tick adoption automatic across every dartwork finalization
  path — no explicit `adopt_axis_label_font` call is required. Note that
  with the default on, these save helpers now **mutate the figure's tick
  fonts** (idempotent; they do not re-fit margins — call `simple_layout`
  for that). Pass `adopt_orphan_tick_font=False` to opt out.
- **Coverage now includes the `mcp/` package and enforces a
  `fail_under=80` gate.** The agentic core (`mcp/tools.py`,
  `resources.py`) was previously omitted, inflating the reported figure
  (~89% → honest ~86% with `mcp/` counted). The gate fails the build when
  a large chunk of new code ships untested instead of letting coverage
  silently regress. `ui/` stays omitted (optional viewer, not
  unit-tested). (#234, #242)

### Fixed
- **`plot_colors(sort_colors=False)` no longer raises `UnboundLocalError`.**
  `color_groups` was bound only inside the `sort_colors` branch — whose
  final reassignment also clobbered the sorted result, leaving the sort
  path dead. The single-group fallback now lives in an `else` branch, so
  sorting actually applies and the unsorted path is defined. (#225, #237)
- **MCP `validate_plot_data` returns a structured error instead of leaking
  a raw `TypeError`.** Several legacy validators indexed or called `len()`
  on a field without a type check, so a present-but-wrong-type field (a
  scalar where a list was expected) or a non-dict payload surfaced an
  uninformative `TypeError` to the client. The dispatch is now guarded and
  returns an actionable message. (#224, #237)
- **Color hex conversion no longer corrupts silently.** `_rgb_to_hex`
  clamped channels with `max(0, min(1, x))`, which collapsed `NaN` to
  `1.0` and emitted a bogus `#ffffff` (e.g. `from_oklab(nan).to_hex()`)
  instead of surfacing the upstream error; it now raises `ValueError` on
  non-finite channels. `_parse_hex` used `lstrip('#')` and fed the result
  straight to `int(.., 16)`, so `##ff0000` parsed as a color and
  `#-10000` produced negative RGB; it now strips exactly one `#` and
  whitelists the hex alphabet before parsing. (#229, #239)
- **`label_axes` font size is now preset-relative.** It defaulted to a
  hardcoded `fontsize=10` that did not scale across presets — the exact
  `fontsize-literal` anti-pattern the library's own lint flags. The
  default is now `None`, resolved to `fs(1)` so panel labels track the
  active preset's base size. `fontweight='bold'` is kept deliberately (a
  semantic weight, not a numeric scaling literal). (#232, #243)
- **Unitless numeric width strings are rejected instead of assumed to be
  cm.** `figsize("13", ...)` / `parse_width("13")` / `Length("13")`
  silently meant `13cm` — the same cm/inch ambiguity for which bare
  `int`/`float` widths are already rejected. A missing unit now raises
  `ValueError` naming the unit suffixes and the `dm.cm()` / `dm.inch()`
  escape hatches. (#226, #244)
- **`__version__` is derived from package metadata.** It was a
  hand-maintained literal that drifted (`0.4.0` while the shipped package
  was `0.4.1`) whenever a release bumped `pyproject.toml` but not the
  literal; it now reads from `importlib.metadata` for a single source of
  truth. Removed 0.3/0.4 names (`dm.SW`, `dm.cm2in`, `dm.FS_*`, …) now
  raise an `AttributeError` that names the replacement API and links
  `docs/migration.md` via a package-level `__getattr__`, instead of
  Python's bare "no attribute" message. (#230, #231, #241)
- **Prompt corpus self-contradiction fixed.** `00-index.md` told agents to
  express sub-1 hairlines as `dm.lw(-1)`, which `01-policy.md` and the lint
  engine both warn collapses to `0.0` and hides the edge; literal
  `0.3`/`0.5` hairlines are restored to match the authoritative policy. The
  raw-hex anti-pattern message recommended non-existent `dm.oc.blue6` /
  `dm.dc.blue500` attribute access (an `AttributeError`); it now points to
  the real string-token form (`color="oc.blue6"`). `llms-full.txt`
  regenerated to match. (#227, #238)

## [0.4.1] - 2026-05-30

### Added
- **`dm.Length`** — opaque Color-pattern length wrapper that
  replaces the in-flight `Inches(float)` marker introduced earlier
  in this release. Multi-unit views as properties (`length.cm`,
  `length.mm`, `length.inch`, `length.pt`).
  `dm.length("13cm")` parses unit strings (mirrors
  `dm.hex("#abc")`); `dm.pt(24)` joins the existing `dm.cm` /
  `dm.inch` / `dm.mm` constructor family. Deliberately **not** a
  `float` subclass — passing a `Length` to a matplotlib API that
  expects a non-inch unit (`fontsize=` / `linewidth=` are pt;
  transform offsets are px) would silently misinterpret the value;
  forcing every boundary to pick a unit explicitly via the property
  views keeps each one type-safe. `dm.Inches` is no longer
  importable. (#152)
- **`dm.figsize(width, aspect)`** — single sizing helper that returns
  the inch tuple matplotlib's `figsize=` expects. Pairs natively with
  `plt.subplots` / `plt.figure` so dartwork-mpl no longer wraps the
  figure constructors. Width must be a unit string (`"13cm"`, `"5in"`,
  `"170mm"`, `"24pt"`) or a `Length` value (`dm.cm(13)`, `dm.col1`,
  `dm.col2`); bare `int`/`float` are rejected (`raw-width-number`
  lint rule). The second argument accepts four equivalent forms —
  aspect token (`"wide"`), numeric ratio (`0.6`), unit-string height
  (`"12cm"`), or `Length` height (`dm.cm(12)`) — so callers can write
  `dm.figsize("15cm", "12cm")` directly instead of hand-computing
  `12 / 15`. (#147, #152)

### Changed
- `dm.mix_colors` now blends in OKLab space (perceptually uniform) instead of
  naïve gamma-sRGB linear interpolation. Result colors will subtly differ for
  non-grayscale blends — gradients now look smoother and less desaturated
  through saturated midpoints (e.g. red + blue gives a vivid purple rather than
  a muddy dark grey). `dm.pseudo_alpha` (which delegates to `mix_colors`)
  inherits the change. (#141)
- `parse_width` now rejects bare `int`/`float`/`bool` with `TypeError`.
  Earlier dartwork-mpl silently treated raw numbers as cm — that
  silently bridged matplotlib's inches contract and caused
  hard-to-spot 2.54× sizing bugs. (#147)
- **`dm.auto_select_colors` → `dm.make_palette`** with argument
  cleanup: `n_series` → `n`, `color_type` → `kind`,
  `highlight_index` → `highlight`. The function body is unchanged
  (same four curated palette lists, same highlight-index swap); the
  rename aligns the name with `make_offset` (prefix) and
  `list_palettes` / `show_palette` (vocabulary). The
  `dm-auto-select-colors-renamed` lint rule flags the old name. (#156)

### Removed
- **`dm.style_spines`, `dm.add_grid`, `dm.minimal_axes`** — round 4 of
  the public API audit (#141 / #156). All three were 1–3 line
  matplotlib calls with curated default kwargs; the curation was the
  only contribution and now lives in `docs/usage_guide/recipes.md`
  (publication grid, minimal axes, thin gray spines snippets). The
  `dm-spines-removed` lint rule flags the old call sites and points
  at the recipes page. The `src/dartwork_mpl/spines.py` module,
  `tests/test_spines.py`, and the `docs/api/spines.rst` page were
  deleted along with the functions; seven `examples_source` files
  that demonstrated the wrappers (`plot_spine_*.py`,
  `plot_grid_customization.py`) were removed because their
  pedagogical purpose was specifically the now-removed functions.
  (#156)
- **`dm.subplots`, `dm.figure`** — both raise `AttributeError` now. The
  package no longer wraps the matplotlib figure constructors. Use
  `plt.subplots(figsize=dm.figsize("<n>cm", "<aspect>"))` and call
  `dm.style.use(...)` separately. The `style=` kwarg is gone with
  them. The `migrate_legacy_code` codemod inserts a
  `# TODO(dm-migrate):` comment above each call site so an agent can
  rewrite them in one sweep. (#147)
- 5 wrapper functions per round-3 of the public API audit (#141):
  `format_axis_percent`, `format_axis_labels`, `add_frame`,
  `add_value_labels`, `set_xmargin`/`set_ymargin`.
  See `docs/migration.md` for inline replacements.
- 8 thin-wrapper utility functions per round-2 of the public API audit (#141):
  `hide_spines`, `hide_all_spines`, `show_only_spines`, `remove_grid`,
  `format_axis_thousands`, `save_figure`, `create_figure_with_style`,
  `templates.diverging_bar.get_source_code`.
  Each can be inlined as a single matplotlib call — see `docs/migration.md`.

## [0.4.0] - 2026-05-05

### Added
- **Robustness test suite** under `tests/robustness/` exercising 44
  scenarios (long tick labels, twinx/twiny, NaN/Inf data, datetime
  axes, log/symlog scales, GridSpec colorbars, pie/donut labels, 한글
  fonts, etc.). Each scenario asserts (a) `validate_figure` outcome,
  (b) `auto_layout` convergence, (c) saved-PNG pixel-level invariants
  via a new `tests/robustness/pixel_assertions.py` helper module.
- **`CLIPPED_TEXT` validation check** that fires when any visible Text
  artist sits within 1 px of the figure canvas edge. Complements
  `OVERFLOW`'s 2 px artist-tree check with a tighter pixel-coverage
  rule, plus fix suggestions in `validate_fixes.get_fix_suggestions`.
- **Robustness extras** — three new scenarios in
  `tests/robustness/scenarios.py`: `subfigures_2x1` (matplotlib
  SubFigure container), `constrained_layout_then_auto_layout`
  (constrained-layout × auto-layout coexistence), and
  `triple_twinx_offset_spine` (third y-axis at axes-fraction 1.15
  with offset spine, currently `xfail(strict=True)` and tracked in
  `KNOWN_LIMITATIONS` until the BUFFER scaling for axes-fraction
  spines is improved).
- **14-preset round-trip matrix** — new `tests/test_preset_matrix.py`
  applies every preset registered in `presets.json`, builds a clean
  chart, saves PNG+PDF, and asserts validate-clean output for each.
- **`format_axis_si` boundary regression tests** — magnitude / sign
  / decimals coverage for the SI-prefix ladder (1e3, 1e6, 1e9, 1e12)
  in `tests/test_formatting.py`.
- **Multibyte currency symbol tests** — ₩ / € / ¥ exercised
  end-to-end through `format_axis_currency` and PNG save.
- **Non-ASCII filename test** — `dm.save_formats(fig, "한글_차트_₩")`
  round-trip in `tests/test_io.py`.
- **Constrained-layout coexistence tests** — two new methods on
  `tests/test_layout.py::TestAutoLayoutEdgeCases` confirming
  `auto_layout` does not crash when called on a figure built with
  `constrained_layout=True`.
- `RobustnessScenario.auto_layout_padding` field (default 0.08
  inches) lets per-scenario builders request extra initial padding
  for figures whose right-edge content (e.g. axes-fraction-
  positioned spines) tightly fills the `auto_layout` tolerance band.

### Fixed
- `_check_overflow` no longer produces spurious warnings when a
  `Line2D` is backed by NaN-only data or a `Text` artist has a
  zero-area window extent (e.g. `fontsize=0` label).
- `auto_layout`'s per-iteration margin increment is now scaled by 1.5x
  on the overflowing side, accelerating convergence for tall rotated
  and datetime tick footprints.
- `auto_layout` runs a final symmetry pass that averages horizontal
  and vertical margin pairs so asymmetrically-squeezed figures
  (e.g. user called `subplots_adjust` before `auto_layout`) are
  centred without expanding the canvas.
- `rotate_tick_labels` now mutates existing Text artists in place via
  per-label `.set_rotation` / `.set_horizontalalignment`, eliminating
  the matplotlib `set_ticklabels()` UserWarning that previously fired
  on non-FixedLocator axes (e.g. CategoricalLocator from `ax.bar`).
- `format_axis_si` now honours `decimals` for the zero tick: with
  `decimals=2` the zero tick formats as `"0.00"` (previously the
  literal `"0"` regardless of `decimals`, which produced misaligned
  tick label widths next to non-zero values like `"1.50k"`).
- `format_axis_millions` and `format_axis_billions` now honour
  `decimals` for the zero tick (mirroring the `format_axis_si` parity
  fix from PR #116). With `decimals=2` the zero tick formats as
  `"0.00"` instead of the literal `"0"`, restoring tick label width
  parity for charts that include both zero and non-zero values like
  `"1.50M"` / `"1.50B"`.
- `auto_layout` post-convergence symmetry pass now reverts itself
  when re-measurement detects that the averaging would re-introduce
  overflow on any side. Figures with structurally-needed asymmetric
  margins (e.g. axes-fraction-positioned right spines via
  `ax.spines["right"].set_position(("axes", 1.15))`) keep their
  iteration-converged margins; balanced figures (e.g. user called
  `subplots_adjust(left=0.05, right=0.30)`) still get re-centred.
- The `triple_twinx_offset_spine` robustness scenario is no longer
  `xfail` — combined with the symmetry-pass guard above and the new
  `auto_layout_padding` field on `RobustnessScenario`, the scenario
  now converges with a 4 px white-border invariant on the offset
  ylabel and is removed from `KNOWN_LIMITATIONS`.
- `format_axis_currency(position="prefix")` now places the minus sign
  OUTSIDE the currency symbol for negative values (`-$1,000` instead
  of `$-1,000`), matching standard financial-report convention. The
  formatter additionally suppresses the sign when the magnitude
  rounds to exactly zero at the requested decimals (so `x=-0.0` and
  `x=-0.4` with `decimals=0` both render as `"$0"`, not `"$-0"`).

  Note: these source-level fixes are defensive hardening. Scenarios
  still wrapped in `pytest.mark.xfail(strict=True)` represent separate
  library limitations (mostly `auto_layout` failing to absorb the
  footprint of long rotated tick labels, axes-fraction annotations
  that escape the canvas, axes-fraction-positioned right spines, and
  colorbar overshoot) — see `tests/robustness/scenarios.KNOWN_LIMITATIONS`
  for the per-scenario tracking notes.

### Changed (CI strictness)

- **`mypy --strict` is now the default mypy mode** in `pyproject.toml`
  (replaces the looser `warn_return_any` / `check_untyped_defs` config).
  Every module under `src/dartwork_mpl/` passes strict type checking,
  including matplotlib-facing code where `np.ndarray[Any, Any]` /
  `cast(...)` / minimal `# type: ignore[…]` are used at the few
  unavoidable boundaries.
- **Ruff `select` extended** with `BLE`/`RET`/`SIM`/`PERF`/`RUF` rule
  sets (was: `E,W,F,I,B,C4,UP`). All findings in `src/` are fixed; a
  small per-file ignore list shields tests from low-value noise (unused
  unpacked tuples, nested context managers, blind-except in cleanup
  paths, etc.).

### Changed

- **`dartwork_mpl.validate_enhanced` renamed to
  `dartwork_mpl.validate_fixes`.** The module split between
  `validate.py` (visual checks) and the auto-fix companion was clear in
  intent but the "enhanced" name was vague — `validate_fixes` makes it
  obvious that this submodule is the auto-fix layer (`get_fix_suggestions`,
  `validate_with_fixes`, `check_agent_requirements`,
  `generate_validation_report`). The public function
  `dm.validate_with_fixes` is unchanged. Direct submodule access
  (`dm.validate_enhanced` / `from dartwork_mpl.validate_enhanced
  import ...`) now raises `AttributeError` /
  `ModuleNotFoundError` — use `dm.validate_fixes` instead. No
  backward-compat alias is provided, in line with the 0.4.x deprecated-
  surface purge.

### Changed (gallery migration)

- **`docs/examples_source/` gallery (~60 scripts) migrated to the
  0.4 width/aspect API.** PR #74 had only converted 7 signal-flare
  scripts (preset showcases + a handful of layout examples); the
  remaining ~60 still relied on `dm.SW/MW/TW/DW`, `dm.FS_*`,
  `dm.cm2in`, and bare `figsize=`/`dpi=` kwargs and crashed under
  PR #87's deprecation removals (`AttributeError`/`TypeError` at
  import). Every gallery `plot_*.py` now calls
  `dm.subplots(width="...cm", aspect="...")` (or `dm.figure(...)`),
  finalises with `dm.auto_layout(fig)` / `dm.simple_layout(fig)`,
  and reads `dm.cm(...)` instead of `dm.cm2in(...)`. Lint passes
  cleanly for the entire gallery and all 60+ scripts execute
  successfully end-to-end against current main.

### Changed (font asset slimming)

- **`NotoSansCJK-Regular.ttc` (19 MB) → `NotoSansCJK-Regular.otf`
  (1.5 MB Korean subset).** The bundled CJK font is now a Hangul
  subset of the original Noto Sans CJK KR instance: 11,172 Hangul
  syllables + Latin/symbols common in Korean reports. The font's
  family name remains `Noto Sans CJK KR`, so `lang-kr.mplstyle`'s
  fallback chain works unchanged. Users who need Japanese / Chinese
  / Hong Kong glyphs must install Noto Sans CJK system-wide;
  matplotlib's font fallback chain will discover them via system
  paths. Wheel drops from ~41.5 MB to ~27 MB.

### Removed (BREAKING — 0.5.0 candidates pulled forward into 0.4.0)

- **0.3 width tokens** (`dm.SW`, `dm.MW`, `dm.TW`, `dm.DW`, `dm.WIDTHS`)
  removed. Use `dm.subplots(width="9cm" | "12cm" | "14.5cm" | "17cm",
  aspect=...)` or `dm.col1` / `dm.col2`.
- **0.3 figure-size tuples** (`dm.FS_SINGLE`, `FS_DOUBLE`, `FS_SQUARE`,
  `FS_WIDE`, `FS_TALL`, `FS_GOLDEN`, `FS_SLIDE`, `FS_A4`) removed. Use
  `dm.subplots(width=..., aspect=...)` with one of the six aspect
  tokens or a positive float.
- **`dm.cm2in()` removed.** Use `dm.cm(value)` (returns an
  `Inches`-tagged float that `dm.subplots(width=...)` recognises
  directly).
- **`dartwork_mpl.constant` module deleted.** It only held the
  removed width tokens and figure-size tuples.
- **`dartwork_mpl.agent_utils` and `dartwork_mpl.xplot` submodule
  aliases removed.** Use `dartwork_mpl.helpers` and
  `dartwork_mpl.templates` directly. `import dartwork_mpl.agent_utils`
  / `import dartwork_mpl.xplot` now raise `ModuleNotFoundError`.
- **`figsize=` and `dpi=` arguments to `dm.subplots()` /
  `dm.figure()` removed.** Passing them now raises `TypeError` with a
  message naming the new `width=` / `aspect=` API.

All of the above were deprecated in the initial `0.4.0-rc1` cut (see
the release notes below) and emitted `DeprecationWarning` until this
final 0.4.0 release. Migration paths are documented in
`docs/migration.md`.

## [0.4.0-rc1] - 2026-04-30

> Initial 0.4.0 cut. Folded into the final `0.4.0` release on 2026-05-05
> (entries above), which additionally pulled the deprecated 0.3 width
> tokens / `FS_*` / `cm2in` / `figsize=`/`dpi=` arguments forward into
> a hard removal so 0.4.x ships a single, consistent surface.

Highlights:

- **Width × aspect API** — `dm.subplots(width=, aspect=)` and `dm.figure(width=, aspect=)` accept free-form widths (`"13cm"`, `dm.cm(11.3)`, `dm.col1` / `dm.col2`) and six named aspect tokens (`square` / `portrait` / `standard` / `golden` / `wide` / `cinema`). New `dm.cm` / `dm.inch` / `dm.mm` helpers return `Inches`, a `float` subclass that survives arithmetic so unit-conversion can't be silently doubled.
- **`dm.lint` module + 15-rule anti-pattern catalog** — single source of truth at `asset/prompt/02-anti-patterns.yaml`, served identically by the MCP `lint_dartwork_mpl_code` tool, the `dartwork-mpl lint` CLI, and CI.
- **MCP server (FastMCP)** with the same SSOT prompt assets the bundled install ships.
- **12 ai-ready templates** under `asset/prompt/05-templates/` for common report idioms.
- **Twinx auto-spine monkey-patch** keeps the right spine visible on all `ax.twinx()` axes.
- **0.3 width tokens deprecated** — `dm.SW`, `dm.MW`, `dm.TW`, `dm.DW`, `dm.WIDTHS`, `dm.FS_*`, `dm.cm2in`, `dm.agent_utils`, `dm.xplot` all emit `DeprecationWarning` (removal in 0.5.0 for the width / FS / cm2in family; v1.0 for the older module renames).
- **Retired the "Zero-Resize Policy" wording** in user-facing surfaces. The new policy is free width input plus the `oversize-width` lint guard.

### Added

- **0.4 width × aspect API** — `dm.subplots(width=, aspect=)` and `dm.figure(width=, aspect=)`. `width` accepts unit-suffixed strings (`"13cm"`, `"6.7in"`, `"170mm"`), helper calls (`dm.cm`, `dm.inch`, `dm.mm`), bare numbers (interpreted as cm), and the academic-column sugar `dm.col1` / `dm.col2`. `aspect` is height / width and accepts six named tokens (`square`, `portrait`, `standard`, `golden`, `wide`, `cinema`) or any positive float. A new `dartwork_mpl.units` module exposes the parser (`parse_width`, `parse_aspect`), the `Inches` `float` subclass, and the unit helpers.
- **`dartwork_mpl.lint`** — single-shot static checker that runs the 15-rule anti-pattern catalog over a Python source string. Returns `Issue` objects (`rule_id`, `severity`, `message`, `line`, `snippet`) and a `format_report` helper. The catalog lives in `asset/prompt/02-anti-patterns.yaml` (the SSOT), so the lint engine, the MCP `lint_dartwork_mpl_code` tool, and the `dartwork-mpl lint` CLI never drift.
- **MCP server (FastMCP)** wired to the SSOT prompt directory: serves `00-index`, `01-policy`, `02-anti-patterns`, `03-recipes`, plus the 12 templates under `05-templates/`. The `dartwork-mpl-mcp` console script launches the server.
- **12 ai-ready templates** under `asset/prompt/05-templates/` covering common report idioms (bar chart, line chart, dual-axis, twinx with band, multi-panel grid, diverging bar with legend, etc.). Each template renders with `dm.subplots(width=..., aspect=...)`, lint-pass clean.
- **`dm.col1` / `dm.col2`** — academic single- and double-column constants (`cm(9)` and `cm(17)`), for callers who don't want to type the unit-suffixed string.
- **Domain-neutrality guardrail test** (`tests/test_domain_neutrality.py`): a parametrised pytest scanner that fails CI if any shipped `.py` / `.md` / `.mplstyle` file under `src/dartwork_mpl/` contains unambiguous finance-domain vocabulary (English: revenue, profit, ebitda, earnings, fiscal, valuation, dcf; Korean: 매출, 매출액, 영업이익, 억원, 조원). Prevents regression of the de-domain work below.
- **Guardrail scope expanded to `docs/` and `examples/`**: `tests/test_domain_neutrality.py` now runs a second parametrised test `test_no_finance_terms_in_docs_and_examples` that scans every `.py` / `.md` / `.rst` / `.mplstyle` file under `docs/` and the top-level `examples/` tree. Build artefacts (`_build`, `examples_gallery`, `_static`, `_templates`, `__pycache__`) are excluded. `tests/` itself is deliberately skipped because the term list would match recursively. The full guardrail now scans 184+ files per run.
- **`dm.helpers.labels`** — new submodule name for what used to be `dm.helpers.formatting`. Houses `format_axis_labels`, `optimize_legend`, and `add_value_labels`. Renamed to avoid the naming clash with the top-level `dartwork_mpl.formatting` module (which houses the `format_axis_*` tick formatters). The old `dm.helpers.formatting` import path still works but emits a `DeprecationWarning` pointing at the new name.
- **`tests/test_templates.py`** — renamed from `tests/test_xplot.py` to match the canonical module name. Migrated the three existing tests to use `from dartwork_mpl.templates import plot_diverging_bar` (canonical) instead of the deprecated `from dartwork_mpl.xplot import plot_diverging_bar`, and added two regression tests that exercise the `dm.xplot` deprecation shim: one asserts the legacy import still resolves to the same callable, and the other asserts `dm.xplot` attribute access emits a `DeprecationWarning`.
- **Dedicated tests for four previously-uncovered public modules**: `tests/test_figure.py` (9 tests covering `dm.subplots` and `dm.figure`, including style/figsize/dpi forwarding and invalid-style handling), `tests/test_formatting.py` (15 tests, one per axis formatter plus parametrised decimals and rotation), `tests/test_spines.py` (9 tests, one per spine/grid helper with concrete spine-visibility assertions), and `tests/test_validate_enhanced.py` (7 tests covering `validate_with_fixes`, `get_fix_suggestions`, `check_agent_requirements`, `generate_validation_report`, and the new `dm.validate_with_fixes` top-level alias). Suite goes from 534 to 574 passing tests.
- **Gallery: six new single-plot spine / grid examples** under `docs/examples_source/01_styling_and_themes/` — `plot_spine_minimal.py`, `plot_spine_visibility.py`, `plot_spine_styling.py`, `plot_grid_customization.py`, `plot_spine_publication_styles.py`, `plot_spine_dark_theme.py`, `plot_spine_dashboard.py`. Each renders exactly one figure, per the repo's one-plot-per-file convention.
- **Gallery: six new single-plot helpers examples** under `docs/examples_source/05_advanced_components/` — `plot_helpers_data_validation.py`, `plot_helpers_color_selection.py`, `plot_helpers_labels.py` (renamed from `plot_helpers_formatting.py` for consistency with the new `dm.helpers.labels` submodule), `plot_helpers_quality.py`, `plot_helpers_io.py`, `plot_helpers_workflow.py`. Each renders exactly one figure and covers one `dm.helpers` submodule (plus an end-to-end workflow demo), replacing the monolithic six-figure `plot_helpers_usage.py`.
- **`dartwork_mpl.diagnostics`** — new canonical home for the four asset-inspection helpers (`classify_colormap`, `plot_colormaps`, `plot_colors`, `plot_fonts`). Closes out the final v0.2.0 folder-restructuring follow-up tracked as issue #57. The functions themselves are unchanged; only their physical module path moved. All four names remain reachable via `dartwork_mpl.<name>` (top-level), `dartwork_mpl.explore.<name>` (re-export), and — with a `DeprecationWarning` — via the legacy `dartwork_mpl.asset_viz.<name>` path.
- **`tests/test_diagnostics.py`** — 14 tests covering the canonical `dartwork_mpl.diagnostics` import path (functional behaviour of the four helpers plus a `TestTopLevelReexport` class pinning that `dm.<name>` and `dm.explore.<name>` resolve to the same objects as `dm.diagnostics.<name>`). Migrated and expanded from the legacy `tests/test_asset_viz.py`.

### Changed

- **Retired the "Zero-Resize Policy" wording** across user-facing surfaces (README, `docs/api/figure.rst`, MCP prompt assets). The replacement framing is "free width input plus the `oversize-width` lint consistency guard", documented in `asset/prompt/01-policy.md` and the 0.3 → 0.4 section of `docs/migration.md`.
- **`plot_diverging_bar()`** (templates): Default `neg_label` / `pos_label` are now the neutral `"Negative"` / `"Positive"` (previously domain-branded strings). The default `title`, default sample `labels`, and docstring Examples were likewise rewritten to neutral placeholders (`"Category A"`–`"Category H"`, `"Diverging bar chart"`). Calling `plot_diverging_bar()` with no arguments now produces a generic, domain-neutral diagram. The function signature is unchanged, so existing callers that pass explicit labels/title continue to work.
- **MCP prompt asset `coding-rules.md` §12**: Renamed section from "Chart Type Templates" to "Reusable Snippet Patterns" and rewrote the two code blocks as inline snippets rather than `def create_dual_axis_chart(...)` / `def create_categorical_bars(...)` wrapper functions. The wrappers were phantom — no such helpers exist in the shipped package, and the `def` framing could mislead MCP clients into hallucinating `dm.create_dual_axis_chart(...)` calls. A short subsection now points at the one real shipped template, `dm.plot_diverging_bar()`, with a runnable example.
- **MCP prompt asset `coding-rules.md` finance examples removed** (first pass, before the §12 rewrite): previous edits to this shipped AI prompt still carried revenue/margin sample code. Replaced with domain-neutral equivalents so MCP clients stop learning a finance-specific idiom by default.
- **MCP prompt asset `general-guide.md` "Agent Best Practices" de-domained**: the earlier version included finance examples and a phantom `agent_utils` import path. Rewrote to use real exports (`dm.helpers.*`) and neutral sample content.
- **Source-code docstrings** under `src/dartwork_mpl/` rewritten to remove finance vocabulary from every public docstring and inline example. Signatures unchanged. The guardrail test above pins this.
- **`docs/examples_source/` rewritten to one-plot-per-file convention** (first pass): earlier bundle files (`single_plot_example.py`, `single_plot_korean.py`, monolithic gallery entries) were split so each file renders exactly one `Figure`. Also de-domained example captions and data labels.
- **Gallery: `plot_waterfall_bridge.py` generalised to an energy-balance walk** instead of Year-over-Year profit change, so the gallery entry leads with a neutral domain while the narrative text still mentions other valid domains (mass balance, population flow, etc.).
- **Gallery: financial dashboard replaced by a set of single-chart sensor examples** (`docs/examples_source/06_real_world_dashboards/plot_sensor_*.py`), removing the last standalone finance-branded gallery entry and keeping the "real-world dashboard" theme with a neutral subject.
- **Canonical import path for asset diagnostics is now `dartwork_mpl.diagnostics`.** The top-level `__init__.py` and `dartwork_mpl.explore` both re-export `classify_colormap`, `plot_colormaps`, `plot_colors`, and `plot_fonts` from the new `diagnostics` module (previously they came from `asset_viz`). Public API contract (`dm.classify_colormap(...)`, `dm.plot_colormaps(...)`, etc.) is unchanged — only the physical module path moved. `__init__.py`'s internal import block comment was updated to reflect the new source module.
- **`docs/migration.md` rewritten** with a new "v0.3.x → v0.4.0" section at the top covering the width / aspect API, `figsize` → `width=` + `aspect=` rewrite, `tight_layout` → `auto_layout`, `cm2in` → `cm`, and the `dm.lint` quick start. The legacy `asset/prompt/_legacy/migration-from-0.3.md` is now a stub that points at the docs version.
- **`docs/api/index.rst`** wired up new pages: `units`, `lint`, `cmap`, `diagnostics`, `install`, plus the `templates` page (renamed from `xplot.rst`). `constant.rst` carries an explicit `.. deprecated:: 0.4.0` notice. `layout.rst` example replaced its `dm.DW` reference with `dm.col2`.

### Deprecated

- **0.3 width tokens (`dm.SW`, `dm.MW`, `dm.TW`, `dm.DW`)** and the aggregate `dm.WIDTHS`. Resolve via the module-level `__getattr__` with a `DeprecationWarning` pointing at the unit-string / `dm.col1` / `dm.col2` replacements. Removal: 0.5.0.
- **`FS_*` figsize tuples** (`FS_SINGLE`, `FS_DOUBLE`, `FS_SQUARE`, `FS_WIDE`, `FS_TALL`, `FS_GOLDEN`, `FS_SLIDE`, `FS_A4`). Same `__getattr__` shim, same removal in 0.5.0. Replacement is `dm.subplots(width=..., aspect=...)`.
- **`dm.cm2in`** — kept for back-compat but now emits a `DeprecationWarning` pointing at `dm.cm` (which returns the safer `Inches` subclass). Removal: 0.5.0.
- **`dartwork_mpl.helpers.formatting`** — deprecated alias for `dartwork_mpl.helpers.labels`. Importing from the old path still works but emits a `DeprecationWarning` pointing at the new submodule. Renamed to resolve the long-standing name clash with the top-level `dartwork_mpl.formatting` module (which houses the `format_axis_*` tick formatters). Plan to remove the deprecated shim in v1.0.
- **`dartwork_mpl.asset_viz`** — deprecated alias for `dartwork_mpl.diagnostics`. The subpackage is now a thin shim: `asset_viz/__init__.py` re-exports the four helpers from `dartwork_mpl.diagnostics` and emits a `DeprecationWarning` on import. `asset_viz/_cmap.py`, `asset_viz/_color.py`, and `asset_viz/_font.py` were removed (their contents are now in `src/dartwork_mpl/diagnostics.py`). Plan to remove the deprecated shim in v1.0 alongside `dm.agent_utils`, `dm.xplot`, and `dm.helpers.formatting`.

### Fixed

- **CI green on `main` restored**: an incidental pre-existing ruff-format issue in `src/dartwork_mpl/constant.py` and a mypy `attr-defined` complaint on `src/dartwork_mpl/layout.py` were blocking every subsequent PR. Fixed so CI passes cleanly.
- **`docs/api/xplot.rst`**: The "Example" code block called `plot_diverging_bar()` with `categories=` / `negatives=` / `positives=` kwargs that do not exist in the real signature (`labels=` / `neg_values=` / `pos_values=`). Copy-pasting the snippet raised `TypeError`. Corrected the kwargs and added the required `numpy` import so the snippet is strictly runnable as shown.
- **`dm.agent_utils` / `dm.xplot` deprecation warnings are live again.** The package previously set `agent_utils = helpers` / `xplot = templates` as module-level attributes and also defined a module-level `__getattr__` that wanted to emit `DeprecationWarning` on those names. Because Python only calls `__getattr__` when an attribute is *missing*, the attribute shim silently shadowed the warning and users saw no migration signal. Removed the attribute shim so `__getattr__` now fires. The legacy import path (`import dartwork_mpl.agent_utils`) remains supported via the `sys.modules` entry. Also cleaned up an unused `_import_with_warning` helper and tightened the import block so `cmap` / `font` / `helpers` / `icon` / `templates` are imported together.
- **`plot_colormaps` / `plot_colors` / `plot_fonts` / `classify_colormap` now appear in `dartwork_mpl.__all__`.** These four visualization-diagnostic helpers are documented as public API in `docs/api/visualization.rst` and have been reachable as `dm.<name>` for some time, but the top-level `__all__` omitted them, so `from dartwork_mpl import *` skipped them and anything introspecting `__all__` (completion tools, stubs) under-reported the public surface. Replaced the star-import from `asset_viz` with an explicit 4-name import so ruff's F405 is satisfied and the names are statically known.
- **`validate_enhanced` is a first-class public surface now.** `src/dartwork_mpl/__init__.py` now imports the `validate_enhanced` submodule explicitly and re-exports `validate_with_fixes` at the top level, so `dm.validate_enhanced.get_fix_suggestions` / `check_agent_requirements` / `generate_validation_report` and `dm.validate_with_fixes` all work without depending on import side effects. Both `validate_enhanced` and `validate_with_fixes` are now in `__all__`, matching what `docs/api/validate.rst` already promises. `get_fix_suggestions` / `check_agent_requirements` / `generate_validation_report` remain reachable via `dm.validate_enhanced.<name>` only — top-level surface stays narrow.
- **`docs/usage_guide/tutorials.md` "Business Report" tutorial** is now "Korean Operations Report". The `report-kr` preset showcase previously branded its example as a quarterly revenue / margin report (`매출액 (억원)`, `영업이익률 (%)`, `quarters = ["1Q24", ...]`). Rewritten to a weekly operations report (`처리량 (건)`, `가동률 (%)`, `weeks = ["1주차", ...]`) so the pedagogical payload — Korean font + dual-axis bar+line + `PercentFormatter` + `auto_layout` — stays identical but the surrounding narrative is domain-neutral. Grid-card title, in-page anchor (`korean-operations-report`), and save filename updated accordingly.
- **`docs/api/formatting.rst` example and section framing** re-themed to remove the implicit "formatters are a finance tool" branding. The "Financial Data Formatting" section becomes "Large Number Formatting" (sample counts / dataset rows / population instead of revenue / market cap / GDP). The "Complete Example: Financial Dashboard" becomes "Complete Example: Multi-format Dashboard" — a 2×2 grid exercising all four numeric formatters on neutral metrics (sample count, efficiency, unit price, cumulative energy). The "Financial Reports" common-patterns subsection, the "Financial formats" feature bullet, the `data_type == 'financial'` branch, and the "technical/financial" Best Practice line are all neutralised. API signatures are unchanged.

### Removed

- **`FOLDER_RESTRUCTURING.md`** moved from the repo root to `docs/development/folder-restructuring.md`. Kept as a historical reference for the v0.2.0 rename (documented migration contract + deprecation timeline) but trimmed its stale "Next Steps (Optional)" list: the `asset_viz → explore` merge is now tracked as a dedicated issue, and the rest of the bullets were already complete.
- **`AGENT_IMPROVEMENTS.md`**: Removed root-level planning document that described phantom modules (`agent_utils.py`, `templates/financial.py`, `templates/scientific.py`, `templates/business.py`) and phantom functions (`create_dual_axis_chart`, `create_waterfall_chart`, `create_multiple_comparison`, `create_band_chart`, etc.) as if they were implemented. The document also framed the library as finance-domain oriented, contradicting dartwork-mpl's identity as a general-purpose matplotlib design utility. Real features (MCP tools, `validate_enhanced`, prompt guides) are tracked in this changelog and their own source files.
- **`docs/examples_source/01_styling_and_themes/plot_spine_styles.py`**: Removed the monolithic seven-figure gallery script and replaced it with the seven single-plot files listed under "Added" above. Each new file preserves the original narrative of its section (minimal / visibility / styling / grid / publication / dark / dashboard) but renders exactly one `Figure`.
- **`docs/examples_source/05_advanced_components/plot_helpers_usage.py`**: Removed the monolithic six-figure gallery script and replaced it with the six single-plot files listed under "Added" above (one per `dm.helpers` submodule, plus a workflow demo). Each new file renders exactly one `Figure`.
- **`docs/api/xplot.rst`** removed in favor of the canonically-named `docs/api/templates.rst`. The new page covers the same surface (`dm.plot_diverging_bar`) and links back to the migration guide for the rename history.

### Post-release polish (rolled into 0.4.0 prior to publish)

The following fixes landed between the 0.4.0 cut commit and the PyPI publish.

#### Added

- **`dartwork-mpl://guide/migration` MCP resource** so 0.3 → 0.4 migration is reachable from the agent entry point and from `dartwork_mpl_info()`.
- **`dm.lint` output now surfaces `→ fix: <suggestion>` lines** when the rule's YAML entry includes a `fix_suggestion`. `Issue.column` and `Issue.fix_suggestion` fields added; the dedupe key inside `lint(...)` switched from `(rule_id, line)` to `(rule_id, column)` so multiple violations on the same line are reported separately.
- **Thread-safe `ensure_loaded` for fonts and colormaps** — `cmap.ensure_loaded()`, `font.ensure_loaded()`, and `style.Style.stack(...)` now use a module-level `threading.Lock` with double-checked locking, eliminating a `ValueError` race when two threads first import the package concurrently.
- **`tests/conftest.py` autouse fixture** closes every figure and restores rcParams defaults between tests, preventing style/figure leak across the suite.
- **Smoke tests for `dartwork_mpl.helpers.*`** (quality, formatting, colors, labels, data) and branch coverage for `validate_enhanced.get_fix_suggestions` and `style.Style` (kwargs, list-of-presets, `presets_dict()` isolation, `context(...)`).
- **`__dir__()` exposes deprecated 0.3 names** so IDE autocomplete can suggest `SW`/`MW`/`TW`/`DW`, `FS_*`, `WIDTHS`, `agent_utils`, and `xplot` during migration. Each access still emits a `DeprecationWarning` via `__getattr__`.
- **PyPI classifiers** — Development Status, Intended Audience, License (OSI MIT), Python 3.10/11/12/13, Topic :: Scientific/Engineering :: Visualization, Framework :: Matplotlib, Typing :: Typed.

#### Changed

- **`dpi-arg` lint severity raised to `critical`** to align with `figsize-direct` and `00-index.md`. `savefig(dpi=...)` remains owned by `savefig-direct` (warning).
- **Deprecated 0.3 prompt files reduced to redirect stubs** — `coding-rules.md`, `general-guide.md`, `layout-guide.md` no longer carry stale 0.3 content.
- **Heatmap recipes / templates use `fig.colorbar(...)`** instead of `plt.colorbar(...)` so copy-pasted snippets don't depend on an unimported `plt`.
- **`validate_plot_data` covers all 12 advertised templates** — added validators for `violin`, `boxplot`, `histogram`, `contour`, and `twin_axis`.
- **`fastmcp` capped below 4** (`>=2.13.3,<4`) in the `[mcp]` extra. 3.x is the latest tested major.
- **`dartwork_mpl_info()` registered-prompt list is now static** instead of poking at the private `mcp._prompt_manager._prompts` attribute that shifted between fastmcp 2.x and 3.x.
- **MCP prompt input cap (8192 chars)** — `create_plot` and `style_review` now truncate `description`, `data_sample`, and `code` with a clear `... [truncated]` marker.
- **Narrowed `except Exception` blocks in `layout.py` and `validate.py`** to `(RuntimeError, ValueError, AttributeError)` so unexpected matplotlib regressions surface instead of being swallowed.
- **Console script renamed `ui` → `dartwork-mpl-ui`** to avoid colliding with whatever `ui` command might already be on a user's PATH.
- **`anti-patterns.yaml` MCP resource ships `application/yaml`** mime type so clients that key off mime auto-detect the format.
- **`oversize-width` lint rule covers fractional widths** (`width="17.5cm"`, `"17.1cm"`, etc.). Previously only integer widths above 17 cm were caught.
- **Clearer `parse_aspect(True)` / `parse_width(True)` errors** — both parsers reject `bool` upfront with "bool is not accepted".
- **`lint(code)` docstring clarifies "Python source only"** to prevent agents from feeding YAML/Markdown into the regex-based lint engine.
- **README "Project Structure" tree refreshed** to reflect the actual 0.4 layout (adds `figure.py`, `lint.py`, `units.py`, `spines.py`, `formatting.py`, `helpers/`, `diagnostics.py`, `explore.py`, `validate_enhanced.py`; marks `constant.py` as deprecated).
- **README MCP resource counts corrected** to `12 resources + 3 resource templates / 7 tools / 2 prompts` (was 11+3).
- **README MCP docs link** points at the actual page (`/integrations/mcp_server.html`, was a broken `/api/mcp.html`).

#### Fixed

- **`Axes.twinx` reentrance guard** — the monkey-patch tags itself with `__dm_patched__` and skips re-patching, so `importlib.reload(dartwork_mpl)` no longer self-wraps into a `RecursionError`.
- **`auto_layout(fig)` / `simple_layout(fig)` no-op on empty figures** instead of `IndexError` on `fig.axes[0]`.
- **`Inches` survives numpy ufunc dispatch** — `__array_ufunc__ = None` on the `Inches` class so `np.float64(2) * dm.cm(9)` keeps the inches tag instead of decaying to a bare `np.float64` that `parse_width` would re-interpret as cm.
- **`_check_pie_label_offset` no longer crashes on regular pies** — coerces `wedge.width=None` (matplotlib's default for non-donut pies) to `1.0` at the source.
- **sdist whitelist now authoritative** — `[tool.hatch.build.targets.sdist]` switched from `include` (additive) to `only-include` (replaces hatch's default file discovery), so the published tarball no longer ships `.claude/`, `docs/`, `tests/`, `examples/`, or `uv.lock`.
- **`dpi-arg` lint regex sees through `figsize=(...)`** — the prior `[^)]*` pattern stopped at the first `)` and silently missed `plt.figure(figsize=(8,6), dpi=200)`.
- **`linewidth-literal` lint relaxed for sub-1 hairlines** — only fires on literals whose integer part is `>= 1`. Sub-1 widths (`0.3`, `0.5`, `0.8`) are common, intentional decoration in the bundled templates.
- **`dartwork-mpl-mcp` console script** prints a friendly install hint and exits `1` when the `[mcp]` extra is missing.
- **`dm.subplots(width=, figsize=)` and `dm.figure(...)`** emit an explicit `UserWarning` saying the new `width=` was ignored and the legacy `figsize=` won.
- **`fetch_github_document` URL allowlist** — only `https://raw.githubusercontent.com/` URLs accepted; other schemes/hosts rejected with a clear `ValueError`. Error messages trimmed to exception type, not full traceback.
- **`dm.cm2in` now actually emits the `DeprecationWarning`** the rest of this changelog promised. (It was supposed to warn since 0.4 but the body of the function was a plain return.)

#### Removed (font asset slimming, no API impact)

- **`NotoSans_ExtraCondensed` family** (18 files, ~10 MB) — never referenced by any mplstyle preset, helper, example, or test.
- **Roboto Thin/Black weights and all italic variants** (8 files, ~0.7 MB) — not exercised by any bundled preset (presets only call weights 300/400/500/700, no italic).
- **Paperlogy 1Thin / 2ExtraLight / 6SemiBold / 8ExtraBold / 9Black** weights (5 files, ~6.3 MB) — bundled presets only reference the four weights kept.
- **Wheel size**: ~50 MB → ~41.5 MB (≈17%, ~17 MB freed uncompressed). sdist now ~5 MB once the worktree-cache leak is fixed by `only-include`.

## [0.3.1] - 2026-03-20

### Fixed

- **Documentation**: Extensive updates to MCP Server documentation (8 resources, 7 tools, 2 prompts) and README.
- **Tests**: Expanded MCP test suite from 9 to 28 tests for full coverage.

## [0.3.0] - 2026-03-20

### Added

- **MCP Tools**: 6 new tools — `get_color_value`, `mix_colors`, `list_color_families`, `lint_dartwork_mpl_code`, `validate_plot_data`, `dartwork_mpl_info`.
- **MCP Resources**: 6 new resources — `palette/colors`, `palette/fonts`, `styles/list`, `styles/{preset}`, `templates/list`, `templates/{plot_type}`.
- **MCP Prompts**: 2 interactive prompts — `create_plot` (guided plot generation), `style_review` (code compliance review).
- **Korean font fallback**: `Pretendard` → `NanumBarunGothic` fallback chain in mplstyles.
- **`twinx()` auto-spine**: Monkey-patch ensures right spine is always visible on twin axes.
- **Validation checks**: `MARGIN_ASYMMETRY` and `PIE_LABEL_OFFSET` in `validate_figure()`.
- **Heatmap default**: `image.aspect=equal` set as default rcParam.
- **Gallery examples**: Advanced ML and Bayesian visualization examples.
- **Colormaps**: 9+ new vibrant colormaps across all categories; cyclical cmaps.

### Changed

- **Colormap curation**: Reduced from 232 → 16 core colormaps with descriptive names.
- **Default tick labelsize**: Changed to 8.0pt.
- **Plot readability**: Thicker lines, bold titles, and adjusted margins.
- **Docstrings**: All docstrings translated from Korean to English.
- **Monochrome toggle**: Replaced toggle switch with explicit segmented control in UI.

### Fixed

- **`dc.ocean` colormap**: Replaced removed `dc.ocean` with `dc.deep_sea` throughout docs.

## [0.2.0] - 2026-03-07

### Added

- **MCP Server**: Built-in Model Context Protocol server (`dartwork-mpl-mcp`) for AI coding assistants (Claude Code, Cursor, Windsurf, Antigravity). Exposes library guides as resources and `fetch_github_document` as a tool.
- **MCP documentation**: Comprehensive `docs/api/mcp.rst` covering capabilities, client configuration, verification, architecture, and troubleshooting.
- **PEP 561 compliance**: `py.typed` marker for downstream mypy support.
- **CI pipeline**: GitHub Actions with lint (ruff + mypy), test (pytest + coverage), and docs (sphinx) jobs.
- **Pre-commit hooks**: Ruff lint/format and mypy via `.pre-commit-config.yaml`.
- **`__all__` exports**: Explicit public API for 15 modules.
- **`auto_layout()` function**: Content-aware layout that automatically detects and fixes text overflow.
- **`set_xmargin()` and `set_ymargin()` functions**: Set responsive axis margins based on data range.
- **`dm.subplots()` and `dm.figure()` wrappers**: Enhanced figure creation with integrated styling.
- **Helper utilities**: AI-focused utilities for data validation, color selection, formatting, and quality checks.

### Changed

- **Module renames for clarity**:
  - `agent_utils` → `helpers`: Better reflects general-purpose utility nature
  - `xplot` → `templates`: More descriptive of ready-to-use visualization templates

### Deprecated

- **`agent_utils` module**: Renamed to `helpers`. Import `dartwork_mpl.helpers` instead. Backward-compatible alias provided with deprecation warning.
- **`xplot` module**: Renamed to `templates`. Import `dartwork_mpl.templates` instead. Old name available as alias with deprecation warning.
- **`xplot` re-export**: `plot_diverging_bar` accessible via `dm.plot_diverging_bar()`.
- **`USAGE_GUIDE.md` asset**: Bundled guide for LLM install command.
- **Test coverage**: 228 tests, 91% line coverage.
- **CHANGELOG.md**: This file.

### Changed

- **`asset_viz`**: Split from single 1,387-line file into `asset_viz/` subpackage (`_cmap.py`, `_color.py`, `_font.py`).
- **`color/_loader.py`**: Removed eager module-level `ensure_loaded()` call; registration now triggered explicitly in `color/__init__.py`.
- **`util.py`**: Split God Module into `layout.py`, `annotation.py`, `io.py`, `scale.py`, `prompt.py` + residual `util.py`.
- **`color/`**: Extracted `_BaseColorView`, unified iterator classes, added `_load_json_palette` helper.
- **`__init__.py`**: Lazy initialization for side effects (font, cmap, icon registration).
- **README**: Updated project structure to reflect new subpackages.

### Removed

- **`cmap-backup/`**: 114 unused backup files.
- **Tracked notebooks**: 11 `.ipynb` files untracked and added to `.gitignore`.

### Fixed

- **MCP script name collision**: Renamed `mcp` → `dartwork-mpl-mcp` to avoid conflict with the `mcp` Python package CLI.
- **`__version__`**: Synced with `pyproject.toml` (`0.1.0` → `0.2.0`).
- **Ruff lint**: Applied auto-fixes for unused imports and loop variables.
- **`ui` module**: Lazy-import `run` to avoid requiring `uvicorn` at import time.

## [0.1.1] - 2026-03-07

### Changed

- Version sync between `__init__.py` and `pyproject.toml`.

## [0.1.0] - 2025-12-01

- Initial public release with style management, color system, font registration, colormap support, and visual validation.

[Unreleased]: https://github.com/dartworklabs/dartwork-mpl/compare/v0.7.0...HEAD
[0.7.0]: https://github.com/dartworklabs/dartwork-mpl/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/dartworklabs/dartwork-mpl/compare/v0.5.6...v0.6.0
