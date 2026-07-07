# Categorical palettes

```{raw} html
<style>
article:has(#dm-cat-exp) .dm-lead {
  margin: .7em 0 1.25em;
  color: var(--dm-text-muted, var(--dm-gray-10, #667085));
  font-size: 1.09em; line-height: 1.72;
}
article:has(#dm-cat-exp) section > h2 { margin-top: 2.6em; padding-top: .72em; border-top: 1px solid var(--dm-gray-a4, rgba(0, 0, 0, 0.12)); }
article:has(#dm-cat-exp) section > h3 { margin-top: 1.9em; }
article:has(#dm-cat-exp) table {
  width: 100%; border-collapse: separate; border-spacing: 0; overflow: hidden; font-variant-numeric: tabular-nums;
  border: 1px solid var(--dm-gray-a4, rgba(0, 0, 0, 0.12)); border-radius: var(--dm-radius-md, 8px);
}
article:has(#dm-cat-exp) thead th { background: var(--dm-bg-subtle, var(--dm-gray-2, #f7f9f9)); }
article:has(#dm-cat-exp) th, article:has(#dm-cat-exp) td {
  padding: .68rem .82rem; vertical-align: top; border-bottom: 1px solid var(--dm-gray-a4, rgba(0, 0, 0, 0.12));
}
article:has(#dm-cat-exp) th + th, article:has(#dm-cat-exp) td + td { border-left: 1px solid var(--dm-gray-a4, rgba(0, 0, 0, 0.12)); }
article:has(#dm-cat-exp) tbody tr:last-child td { border-bottom: 0; }
article:has(#dm-cat-exp) tbody tr:hover { background: var(--dm-accent-2, #e6f7f4); }
article:has(#dm-cat-exp) p code, article:has(#dm-cat-exp) li code,
article:has(#dm-cat-exp) td code, article:has(#dm-cat-exp) th code,
article:has(#dm-cat-exp) blockquote code {
  padding: .08em .35em; border: 1px solid var(--dm-gray-a4, rgba(0, 0, 0, 0.12));
  border-radius: var(--dm-radius-sm, 5px); font-size: .91em; background: var(--dm-i-code-surface, var(--dm-gray-2, #f2f4f5));
  font-family: var(--dm-f-mono, ui-monospace, SFMono-Regular, Menlo, monospace);
}
html[data-theme="dark"] article:has(#dm-cat-exp) tbody tr:hover { background: var(--dm-accent-3, rgba(18, 165, 148, 0.16)); }
</style>
```

```{raw} html
<p class="dm-lead">Pick a palette visually, preview it across nine chart shapes, and apply it with one line. Start with the explorer, then copy the matching Python call or a swatch hex when you need exact colors.</p>
```

:::{note}
**This page** picks a categorical palette by intent and applies it. For a
static swatch reference of *every* color — all `dc.*` shades plus the bundled
third-party systems — see **[Palettes](colors.md)**.
:::

## Pick a palette

Use the left rail to choose a palette, drag the color-count control, and toggle
black-and-white preview. Click any swatch to copy its hex, or copy the matching
Python call from the explorer.

```{raw} html
:file: ../_static/categorical_explorer.html
```

## Apply it

```python
import dartwork_mpl as dm

dm.set_cycle(dm.cycle("octave"))   # Octave — the searched 8-color default
dm.set_cycle("trustworthy")                  # any curated set, by name
dm.set_cycle("green", n=5)                   # 5 steps of one hue family
dm.set_cycle(["dc.hl", "dc.gray3", "dc.gray5"], ax=ax)   # one Axes only
cols = dm.get_palette("blue", n=4, subset="even")        # colors, not cycle
ax.set_prop_cycle(dm.cycle_cycler())         # >8 series: 8 colors x 3 styles
```

Every name resolves under `dc.*`: `"blue"` expands to `dc.blue0` … `dc.blue9`,
and `"trustworthy"` expands to `dc.trustworthy0` … `dc.trustworthy7`. The cycles
are also registered as colormaps (`dc.cycle`, `dc.cycle_print`) for
`scatter(c=...)` and seaborn `palette=`.

## Which palette for which data?

| Your data | Reach for | Explorer group |
| --- | --- | --- |
| Everyday 4-8 categories | `dm.cycle("octave")` or `trustworthy` | Qualitative |
| Many unrelated categories, max distinctness | `vivid` or `neon` | Qualitative |
| A few related series, one mood | a hue family sampled evenly, or `forest` / `teal_indigo` | Sequential / Analogous |
| Ordered amount (rank) | one family ramp; `gray` if hue means nothing | Sequential / Neutral |
| Ordered around a midpoint (+/- / change / correlation) | `cool_warm`, `teal_amber`, or `purple_green` | Diverging |
| Two opposed groups (A/B, before-after) | `blue_orange` or `teal_coral` | Duo |
| Soft, editorial, dense dashboards | `pastel` or `dusty` | Muted |
| A specific mood (warm / earthy / luxury) | `ember`, `earth`, or `jewel` | Tone |
| Highlight one series, mute the rest | `teal_accent`, `coral_accent`, or `dc.hl` + grays | Emphasis |
| Colorblind-mandatory | `accessible` (Okabe-Ito) | Accessible |

## How the system is organized

Everything lives in one `dc.*` namespace and uses one API: `dm.cycle(...)` for
matplotlib cycles, `dm.get_palette(...)` for color lists, and
`dm.set_cycle(...)` to apply colors globally or to one Axes.

There are three layers: Octave, the searched default cycle for everyday charts; 20
generative single-hue families (19 chromatic plus gray, ten perceptually
equalized steps on CIELAB L\* + OKLCH) for ordered and sequential work; and the
curated 20-palette system of hand-tuned qualitative, duo, diverging, tonal,
neutral, emphasis, and accessible sets, all grayscale- and CVD-screened.

The count rule is simple: families have 10 steps; curated sets have 8 colors;
Octave has 8 chromatic colors, with rose in the eighth slot; and Octave Print
has 7 chromatic colors plus dark gray. Single-hue curated ramps are not
duplicated; the families serve that job.

## Reference

### Octave — the default cycle

Octave is the default coherent data-series cycle when you do not want to choose
a palette by hand; use `dm.cycle("octave")` or the stable `dc.cycle` colormap
token. Its eight chromatic colors were selected by exhaustive search to stay
distinct under color-vision-deficiency simulation. The common red-green
deficiencies clear min ΔE00 10.3 (vs the Okabe-Ito benchmark's 11.5), and on
the rare tritan the default cycle's 8.3 actually beats Okabe-Ito's 7.9 — both
under the accurate Brettel-1997 model (see [Color system design](design.md));
matplotlib's `tab10` scores 1.4 and effectively collapses under protanopia.

Gray is reserved for grids and reference lines, not spent as a data color in
Octave; its eighth series color is chromatic rose. Octave Print uses a dark
gray as its eighth color for black-and-white lightness spread. The trade-off is
screen versus print: Octave keeps every color in the line-safe L* 43-78 band
for thin lines on white, while Octave Print guarantees every pair is at least
about 7 L* apart (min ΔL* 7.7) for grayscale printing and photocopies. It
keeps the same hue per slot as Octave, and the violet slot matches Octave. Need
more than eight line series? Opt in to `dm.cycle_cycler()`, which expands the
cycle to 8 × 3 = 24 color/style combinations. Line styles are opt-in because a
plot with `lw=0` would otherwise inherit dashes and break.

### Hue families

The chromatic families follow the hue spectrum: `red` · `rose` · `coral` ·
`tangerine` · `orange` · `amber` · `yellow` · `lime` · `green` · `teal` ·
`cyan` · `sky` · `blue` · `cobalt` · `indigo` · `violet` · `purple` ·
`fuchsia` · `pink`, plus `gray`. Use a whole ramp for an ordered scale, or
sample evenly spaced steps for related series.

```python
cols = dm.get_palette("blue", n=4, subset="even")
cols = dm.get_palette("teal", order="lightness")
```

### Curated sets

The curated 20-palette system is the hand-tuned set collection preserved
verbatim through the v5 clean break. Curated sets use the same API as families,
and all are grayscale- and CVD-screened.

| Group | Members |
| --- | --- |
| Analogous | `forest`, `teal_indigo` |
| Muted | `pastel`, `dusty` |
| Tone | `ember`, `earth`, `jewel` |
| Duo | `blue_orange`, `teal_coral` |
| Diverging | `cool_warm`, `teal_amber`, `purple_green` |
| Neutral | `warm_gray`, `cool_gray` (+ the generative `gray`) |
| Emphasis | `teal_accent`, `coral_accent` |
| Accessible | `accessible` (Okabe-Ito) |
| Qualitative | `trustworthy`, `vivid`, `neon` |

### `get_palette` and `set_cycle` options

| Option | What it does |
| --- | --- |
| `n` / `subset` (`"first"` \| `"even"` \| `"last"`) | Choose how many colors and which steps to sample. |
| `order` (`"default"` \| `"lightness"` \| `"shuffle"`) | Keep palette order, sort by lightness, or shuffle. |
| `reverse` | Flip the resulting order. |
| `seed` | Make shuffled order reproducible. |
| `set_cycle(palette, ax=None, n=None)` | Apply a palette globally, or to one Axes with `ax=`. |

Names resolve under `dc.*`, so `"blue"` and `"trustworthy"` are enough.

> The v5 clean break trimmed the throwaway ad-hoc aliases; the curated `dc.*`
> categorical sets are deliberately preserved. See the
> [migration guide](../migration.md) for the manual rename table.
