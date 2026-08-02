# Palettes

Use this page when separate series or categories need distinct colors.

A **palette** is a finite list of colors. The palette types on this page use
these terms:

- **Qualitative:** separate colors for labels that have no numeric order.
- **Sequential:** low to high along one ordered path.
- **Diverging:** two sides meet at a meaningful center such as zero.

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

Color-vision deficiency (CVD) simulations are named models used to diagnose
potential color collisions, not observer guarantees.

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
| Qualitative categories where distinction under the named CVD simulations matters | `dm.colors("octave", n=8)` or `trustworthy` | Qualitative |

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

:::{dropdown} Technical terms
OKLab and OKLCH are used to construct and adjust colors. ΔEOK is a
color-distance ruler: larger means more different.

Modeled relative CIE Y (`relative_y`) is calculated from nominal D65 sRGB; it
is not a measurement of a particular display, perceived brightness, or OKLab
`L`. It records nominal output ordering under the catalog's pinned
calculation.

CIELAB supplies coordinates for CIEDE2000 distance. CIEDE2000 and the named
CVD simulations are model-specific collision/regression diagnostics on
finished output; they do not construct colors or define modeled output.
CIEDE2000 distance is reported as ΔE00.
Web Content Accessibility Guidelines (WCAG) check pair-specific text contrast
for a named foreground/background pair; this is not palette certification.
:::

The 19 chromatic family ladders use ΔEOK arc-length equalization. The gray
ladder directly samples ten evenly spaced neutral-tone positions; its resulting
neighbor ΔEOK near-evenness is measured and protected by frozen non-regression
gates, not produced by the chromatic equalizer. Both forms use OKLab/OKLCH
construction and preserve the normalized modeled-relative-Y output contract.
The curated sets are manual, preserved rows rather than extra recipe inputs.
CIEDE2000 and CVD results remain model-specific diagnostics, and WCAG text
contrast is checked separately for a specified foreground/background pair.

The count rule is simple: families have 10 steps; curated qualitative and
diverging sets have 8 colors; Octave has 8 chromatic colors, with rose in the
eighth slot; and Octave Print has 7 chromatic colors plus dark gray. Single-hue
curated ramps are not duplicated; the families serve that job.

## Reference

### Octave — the default cycle

Octave is the default for unrelated series; Octave Print trades one chromatic
slot for dark gray to increase nominal neutral-coordinate separation in the
historical diagnostic.

:::{dropdown} Technical detail
Octave is the default coherent data-series cycle when you do not want to choose
a palette by hand; use `dm.set_colors()` or the stable `dc.octave` colormap
token. Its eight published chromatic colors originated in an exhaustive
model-specific collision search; the v6 compiler replays the frozen selection
rather than using CVD as a construction objective. Under the named
full-severity simulation diagnostics, `dc.octave` records min ΔE00 10.3 (vs
the Okabe-Ito benchmark's 11.5), and in the named tritan diagnostic the default
cycle's 8.3 actually beats Okabe-Ito's 7.9.
Protan/deutan use Machado et al. (2009), while tritan uses
Brettel–Viénot–Mollon (BVM, 1997); see
[Design rationale](design-rationale.md). Matplotlib's `tab10` scores 1.4 under
the same named simulated-protanopia validation protocol.

Gray is reserved for grids and reference lines, not spent as a data color in
Octave; its eighth series color is chromatic rose. Octave Print uses a dark
gray as its eighth color to change its nominal neutral-coordinate diagnostic.
The trade-off is a catalog design choice, not a print guarantee. The
historical, validation-only CIELAB report records Octave's L* 43-78 range for
thin-line candidates on white; in the same diagnostic, Octave Print records a
minimum pairwise ΔL* of 7.7. That bounded source-color statistic does not model
a particular printer, paper, conversion workflow, background, overlap, or
observer. The live nominal output ordering is checked with modeled relative Y.
Octave Print keeps
the same hue per slot as Octave, and the violet slot matches Octave. Need more
than eight line series? Opt in to `dm.set_colors(styles=True)`, which expands
the cycle to 8 × 3 = 24 color/style combinations. Line styles are opt-in
because a plot with `lw=0` would otherwise inherit dashes and break.
:::

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

The curated qualitative rail is the hand-tuned set collection preserved from
the v5 migration. Curated sets use the same API as families, and their
grayscale and CVD metrics are validation metadata, not generation inputs.

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

> The v5 migration trimmed the throwaway ad-hoc aliases; the curated `dc.*`
> categorical sets are deliberately preserved. See the
> [migration guide](../migration.md) for the manual rename table.
