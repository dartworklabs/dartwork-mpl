# Palettes

```{raw} html
<p class="dm-lead">Discrete color forms for series: the Octave default cycle, curated qualitative sets, and designed sequential or diverging samples from <code>dm.colors(name, n=...)</code>.</p>
```

For a static token sheet of every single-color string, use [Colors](colors.md).

## Pick a palette

Use the left rail to choose a palette, drag the color-count control, and toggle
black-and-white preview. Click any swatch to copy its hex, or copy the matching
Python call from the explorer. The rail has 13 qualitative choices: Octave,
Octave Print, and 11 curated qualitative sets.

```{raw} html
:file: ../_static/categorical_explorer.html
```

## Apply it

```python
import dartwork_mpl as dm

dm.set_colors()                              # octave — the searched default cycle
dm.set_colors("trustworthy")                 # any curated set, by name
dm.set_colors("green", n=5)                  # 5 steps of one hue family
dm.set_colors(["dc.hl", "dc.gray3", "dc.gray5"], ax=ax)  # one Axes only
cols = dm.colors("blue", n=4)                # designed color list
dm.set_colors(ax=ax, styles=True)            # >8 series: 8 colors x 3 styles
```

Every name resolves under `dc.*`: `"blue"` can return designed samples from the
single-hue family, `"blue_red"` can return a diverging list, and
`"trustworthy"` returns the curated qualitative set. The qualitative families
are also registered as colormaps (`dc.octave`, `dc.octave_print`,
`dc.trustworthy`, …) for `scatter(c=...)` and seaborn `palette=`.

## Which palette for which data?

| Your data | Reach for | Explorer group |
| --- | --- | --- |
| Everyday 4-8 categories | `dm.colors("octave", n=8)` or `trustworthy` | Qualitative |
| Many unrelated categories, max distinctness | `vivid` or `neon` | Qualitative |
| A few related series, one mood | a hue family sampled evenly, or `forest` | Sequential / Qualitative |
| Ordered amount (rank) | one family ramp; `gray` if hue means nothing | Sequential / Neutral |
| Ordered around a midpoint (+/- / change / correlation) | `blue_red`, `blue_orange`, `teal_amber`, or `green_purple` | Diverging API |
| Soft, editorial, dense dashboards | `pastel` or `dusty` | Muted |
| A specific mood (warm / earthy / luxury) | `ember`, `earth`, or `jewel` | Tone |
| Highlight one series, mute the rest | `teal_accent`, `coral_accent`, or `dc.hl` + grays | Emphasis |
| Colorblind-mandatory | `dm.colors("octave", n=8)` or `trustworthy` | Qualitative |

## How the system is organized

Everything lives in one `dc.*` namespace and uses one API: `dm.colors(...)` for
colormaps or designed color lists, `dm.set_colors(...)` to apply colors globally
or to one Axes, `dm.list_colors(...)` for family metadata, and
`dm.show_colors(...)` for previews.

There are four discrete forms: Octave, the searched default cycle for everyday
charts; 11 hand-tuned curated qualitative sets for muted, tonal, forest, and
emphasis use cases; 20 generative single-hue families sampled for ordered and
sequential work; and canonical diverging lists such as `blue_red`,
`blue_orange`, `teal_amber`, and `green_purple` for centered data.

The count rule is simple: families have 10 steps; curated qualitative and
diverging sets have 8 colors; Octave has 8 chromatic colors, with rose in the
eighth slot; and Octave Print has 7 chromatic colors plus dark gray. Single-hue
curated ramps are not duplicated; the families serve that job.

## Reference

### Octave — the default cycle

Octave is the default coherent data-series cycle when you do not want to choose
a palette by hand; use `dm.set_colors()` or the stable `dc.octave` colormap
token. Its eight chromatic colors were selected by exhaustive search to stay
distinct under color-vision-deficiency simulation. The common red-green
deficiencies clear min ΔE00 10.3 (vs the Okabe-Ito benchmark's 11.5), and on
the rare tritan the default cycle's 8.3 actually beats Okabe-Ito's 7.9 — both
under the accurate Brettel-1997 model (see
[Design rationale](design-rationale.md));
matplotlib's `tab10` scores 1.4 and effectively collapses under protanopia.

Gray is reserved for grids and reference lines, not spent as a data color in
Octave; its eighth series color is chromatic rose. Octave Print uses a dark
gray as its eighth color for black-and-white lightness spread. The trade-off is
screen versus print: Octave keeps every color in the line-safe L* 43-78 band
for thin lines on white, while Octave Print guarantees every pair is at least
about 7 L* apart (min ΔL* 7.7) for grayscale printing and photocopies. It
keeps the same hue per slot as Octave, and the violet slot matches Octave. Need
more than eight line series? Opt in to `dm.set_colors(styles=True)`, which
expands the cycle to 8 × 3 = 24 color/style combinations. Line styles are opt-in
because a plot with `lw=0` would otherwise inherit dashes and break.

### Hue families

The chromatic families follow the hue spectrum: `red` · `rose` · `coral` ·
`tangerine` · `orange` · `amber` · `yellow` · `lime` · `green` · `teal` ·
`cyan` · `sky` · `blue` · `cobalt` · `indigo` · `violet` · `purple` ·
`fuchsia` · `pink`, plus `gray`. Use a whole ramp for an ordered scale, or
sample evenly spaced steps for related series.

```python
cols = dm.colors("blue", n=4)
cols = dm.colors("teal", n=6, reverse=True)
```

### Curated sets

The curated qualitative rail is the hand-tuned set collection preserved through
the v5 clean break. Curated sets use the same API as families, and all are
grayscale- and CVD-screened.

| Group | Members |
| --- | --- |
| Qualitative | `trustworthy`, `vivid`, `neon`, `forest` |
| Muted | `pastel`, `dusty` |
| Tone | `ember`, `earth`, `jewel` |
| Emphasis | `teal_accent`, `coral_accent` |

The four canonical discrete diverging forms are `blue_red`, `blue_orange`,
`teal_amber`, and `green_purple`. They are ordered encodings for centered data,
not unordered categorical sets, so the explorer keeps them out of the
qualitative rail.

### `colors` and `set_colors` options

| Option | What it does |
| --- | --- |
| `colors(name, n=None)` | Return the registered colormap when `n` is omitted, or a designed list when `n` is set. |
| `n` | Choose how many colors from the designed discrete form. Continuous families require it when used with `set_colors`. |
| `reverse` | Flip the resulting list or colormap. |
| `set_colors(name_or_list=None, ax=None, n=None, styles=False)` | Apply a palette globally, to one Axes with `ax=`, or expand it with line styles. |

Names resolve under `dc.*`, so `"blue"` and `"trustworthy"` are enough.

> The v5 clean break trimmed the throwaway ad-hoc aliases; the curated `dc.*`
> categorical sets are deliberately preserved. See the
> [migration guide](../migration.md) for the manual rename table.
