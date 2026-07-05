# Categorical palettes

dartwork's discrete categorical palettes — a curated 16-palette system across
the v5 color families. Every family has 10 perceptually equalized steps,
generated on CIELAB L* + OKLCH and screened for grayscale and
color-vision-deficiency (CVD) legibility. For ordinary data series, start with
the searched `dc.cycle`; for tone-specific series, sample a family with
`get_palette`.

:::{note}
**This page** picks a categorical palette by intent and applies it with
`set_cycle` / `get_palette`. For a static swatch reference of *every* color —
all `dc.*` shades plus the six third-party systems — see **[Palettes](colors.md)**.
:::

## The default cycle

For a coherent data-series cycle without choosing a palette, use the v5
`dc.cycle` — seven chromatic colors selected by exhaustive search to stay
distinct under color-vision-deficiency simulation: the common red-green
deficiencies clear min ΔE00 10.3 (vs the Okabe-Ito benchmark's 11.5), and on
the rare tritan the v5 cycle's 9.0 actually beats Okabe-Ito's 7.9 — both under
the accurate Brettel-1997 model (see [Color system design](design.md));
matplotlib's `tab10` scores 1.4 and effectively collapses under protanopia.
Gray is reserved for grids and reference lines, not spent as a data color in
the default `dc.cycle`; the print cycle adds a dark gray as its 8th color for
B&W lightness spread.

```python
import dartwork_mpl as dm

dm.set_cycle(dm.cycle("default"))   # 7-color screen/PDF cycle (the default)
dm.set_cycle(dm.cycle("print"))     # 8-color cycle, spread darker for B&W print
```

Need more than eight line series? Opt in to line-style variation with
`dm.cycle_cycler()` — it expands the seven colors × three line styles (21
combinations) so a repeated color never reads as the same series. Line styles
are opt-in rather than baked into the default cycle, because an `ax.plot` with
`lw=0` would otherwise inherit a dashed style and break.

```python
ax.set_prop_cycle(dm.cycle_cycler())
```

The cycles are also registered as colormaps (`dc.cycle`, `dc.cycle_print`) for
`scatter(c=...)` and seaborn `palette=` interfaces.

## Semantic tokens

Role-based aliases keep meaning separate from color: `dc.pos` (up / positive),
`dc.neg` (down / negative), `dc.ref` (reference), `dc.hl` (highlight). The
mapping is **locale-aware** — under a `*-kr` style, up = red and down = blue
(the Korean finance convention); otherwise up = green, down = red — so report
prose and charts share one semantic.

```python
ax.plot(gains, color="dc.pos")        # green — or red under a *-kr style
ax.axhline(baseline, color="dc.ref")  # neutral reference line
```

> v5 is a clean break: legacy v4-only categorical names were removed from the
> live registry. See the [migration guide](../migration.md) for the manual
> rename table.

## Pick a palette by intent

Pick by the *shape and job* of your data:

- **Ordered** (rank / amount) → Sequential, or Neutral if hue carries no meaning
- **Ordered around a midpoint** (±, change, correlation) → Diverging
- **Highlight one series**, mute the rest → `dc.hl` plus gray/reference tones
- **A few related series** → one hue family, sampled evenly
- **Everyday 4–8 categories** → `dc.cycle` / `dm.cycle("default")`
- **A specific tone** → pick the named v5 family (`green`, `amber`, `violet`, ...)

```python
import dartwork_mpl as dm

dm.set_cycle(dm.cycle("default"))        # everyday default cycle (global)
dm.set_cycle(["dc.hl", "dc.gray3", "dc.gray5"], ax=ax)  # one Axes only

cols = dm.get_palette("blue", n=6)                 # first 6 family steps
cols = dm.get_palette("blue", n=4, subset="even")  # or: 4 spread across the range
cols = dm.get_palette("blue", order="lightness", reverse=True)  # or: dark → light
dm.set_cycle(cols)                       # apply a palette result (or any color list)
```

`dm.get_palette(name, n=None, subset="first"|"even"|"last", *,
order="default"|"lightness"|"shuffle", reverse=False, seed=None)` returns color
names — choose how many (`n` / `subset`), then optionally re-arrange them: `order`
sorts light→dark by lightness or shuffles; `reverse` flips the cycle; `seed` makes a
shuffle reproducible. `dm.set_cycle(palette, ax=None, n=None)` applies a palette (or
an explicit color list) to the global cycle or a single Axes. Bare v5 family
names resolve under `dc.` (`"blue"` → `dc.blue0` … `dc.blue9`).

## Explore

Pick any palette and read it across nine chart shapes — with its grayscale and
color-vision checks — in a single view. Drag the color counts, sort by lightness,
shuffle or reverse the cycle, and toggle black & white; click a swatch to copy its
hex, or copy the matching `dm.get_palette(...)` call.

```{raw} html
:file: ../_static/categorical_explorer.html
```

> The design rationale (the eight criteria, the color-count decision, and the
> spectral-width + intent-family organization) lives in
> `docs/_static/dartwork-discrete-palette-rationale.md`; the colors are
> generated and verified by `docs/_static/scripts/gen_palettes.py`.
