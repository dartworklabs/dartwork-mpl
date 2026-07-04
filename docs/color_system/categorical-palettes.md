# Categorical palettes

dartwork's discrete categorical palettes — a curated 24-palette system across
11 families. Every palette is 8 colors, generated on an even-L* CIELAB
ladder and screened for grayscale and color-blindness (CVD) legibility;
the loudest high-chroma sets deliberately trade some CVD margin for
vibrancy (the generation pipeline reports both scores per palette).

:::{note}
**This page** picks a categorical palette by intent and applies it with
`set_cycle` / `get_palette`. For a static swatch reference of *every* color —
all `dc.*` shades plus the six third-party systems — see **[Palettes](colors.md)**.
:::

## The default cycle

For a coherent data-series cycle without choosing a palette, use the v5
`dc.cycle` — seven chromatic colors selected by exhaustive search to stay
distinct under color-vision-deficiency simulation: the common red-green
deficiencies clear min ΔE00 10.3 (on par with the Okabe-Ito benchmark of
11.1), and the rare tritan clears 9.0 under the accurate Brettel-1997 model
(see [Color system design](design.md));
matplotlib's `tab10` scores 1.4 and effectively collapses under deuteranopia.
Gray is reserved for grids and reference lines, not spent as a data color.

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

> Three families (`teal`, `indigo`, `gray`) share names with legacy tokens
> and stay frozen to their pre-v5 hex by default; opt in to the v5 values with
> `dm.set_palette_version(5)`. See the [migration guide](../migration.md).

## Pick a palette by intent

Pick by the *shape and job* of your data:

- **Ordered** (rank / amount) → Sequential, or Neutral if hue carries no meaning
- **Ordered around a midpoint** (±, change, correlation) → Diverging
- **Highlight one series**, mute the rest → Emphasis
- **A few related series** → Analogous · **Two opposed groups** → Duo
- **Everyday 4–8 categories** → Balanced · **Many unrelated** → Spectrum
- **A specific tone** → Muted, Earth, or Jewel · **Mandatory CVD** → Accessible (Okabe-Ito)

```python
import dartwork_mpl as dm

dm.set_cycle("trustworthy")              # everyday default cycle (global)
dm.set_cycle("teal_accent", ax=ax)       # highlight one series, this Axes only

cols = dm.get_palette("vivid", n=6)                # first 6 — best-separated subset
cols = dm.get_palette("vivid", n=4, subset="even")             # or: 4 spread across the range
cols = dm.get_palette("vivid", order="lightness", reverse=True)  # or: re-sorted dark → light
dm.set_cycle(cols)                       # apply a palette result (or any color list)
```

`dm.get_palette(name, n=None, subset="first"|"even"|"last", *,
order="default"|"lightness"|"shuffle", reverse=False, seed=None)` returns color
names — choose how many (`n` / `subset`), then optionally re-arrange them: `order`
sorts light→dark by lightness or shuffles; `reverse` flips the cycle; `seed` makes a
shuffle reproducible. `dm.set_cycle(palette, ax=None, n=None)` applies a palette (or
an explicit color list) to the global cycle or a single Axes. Bare names resolve
under `dc.` (`"trustworthy"` → `dc.trustworthy0…7`).

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
