# Categorical palettes

dartwork's categorical color system is one `dc.*` surface for choosing discrete
series colors and ordered ramps. The explorer groups palettes by intent:
**Qualitative**, **Sequential**, **Analogous**, **Muted**, **Tone**, **Duo**,
**Diverging**, **Neutral**, **Emphasis**, and **Accessible**.

The **Qualitative** group is the everyday categorical family: the searched
default cycle, the print cycle, and the curated `trustworthy`, `vivid`, and
`neon` sets all pick unrelated categories and mainly differ by chroma and print
behavior. The **Sequential** group is the 20 generative single-hue families
(19 chromatic ramps plus gray), each with ten perceptually equalized steps
generated on CIELAB L\* + OKLCH. The curated 20-palette system covers
analogous, muted, tonal, duo, diverging, neutral-cast, emphasis, and accessible
categorical sets, each hand-tuned and screened for grayscale and
color-vision-deficiency (CVD) legibility.

Count rule: sequential family ramps have **10 steps**; curated categorical sets
have **8 colors**; the default cycle is a searched CVD-optimal **8-color** set,
and the print cycle has **8 colors**. Every palette applies the same way through
`dm.cycle(...)`, `dm.get_palette(...)`, or `dm.set_cycle(...)`.

:::{note}
**This page** picks a categorical palette by intent and applies it. For a
static swatch reference of *every* color — all `dc.*` shades plus the bundled
third-party systems — see **[Palettes](colors.md)**.
:::

## The default cycle

For a coherent data-series cycle without choosing a palette, use the default
`dc.cycle` — eight chromatic colors selected by exhaustive search to stay
distinct under color-vision-deficiency simulation: the common red-green
deficiencies clear min ΔE00 10.3 (vs the Okabe-Ito benchmark's 11.5), and on
the rare tritan the default cycle's 8.3 actually beats Okabe-Ito's 7.9 — both under
the accurate Brettel-1997 model (see [Color system design](design.md));
matplotlib's `tab10` scores 1.4 and effectively collapses under protanopia.
Gray is reserved for grids and reference lines, not spent as a data color in
the default `dc.cycle`; its 8th series color is chromatic rose. The print cycle
uses a dark gray as its 8th color for B&W lightness spread.

```python
import dartwork_mpl as dm

dm.set_cycle(dm.cycle("default"))   # 8-color screen/PDF cycle (the default)
dm.set_cycle(dm.cycle("print"))     # 8-color cycle, spread darker for B&W print
```

Need more than eight line series? Opt in to line-style variation with
`dm.cycle_cycler()` — it expands the eight colors × three line styles (24
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

## Generative families

The families are 19 chromatic single-hue ramps plus gray — `dc.blue0` …
`dc.blue9` — of ten perceptually equalized steps, generated on CIELAB L\* +
OKLCH. Use a whole ramp as an ordered / sequential scale, or sample a few
evenly-spaced steps for a set of related series. A bare family name resolves
under `dc.`.

```python
cols = dm.get_palette("blue", n=6)                 # first 6 family steps
cols = dm.get_palette("blue", n=4, subset="even")  # 4 spread across the range
cols = dm.get_palette("teal", order="lightness")   # light → dark ordered scale
dm.set_cycle("green", n=5)                          # apply 5 green steps globally
```

The chromatic families follow the hue spectrum: `red` · `rose` · `coral` ·
`tangerine` · `orange` · `amber` · `yellow` · `lime` · `green` · `teal` ·
`cyan` · `sky` · `blue` · `cobalt` · `indigo` · `violet` · `purple` ·
`fuchsia` · `pink`, plus `gray`.

## Curated categorical sets

Alongside the generative families, dartwork ships **20 curated categorical
sets** — hand-tuned qualitative, analogous, muted, tonal, duo, diverging,
neutral-cast, emphasis, and accessible schemes that have no generative
equivalent. They are the scientifically curated palettes carried over from the
0.5.5 categorical overhaul and preserved verbatim through the v5 clean break.
Each resolves through exactly the same API as a family —
`dm.get_palette("trustworthy", n=6)`, `dm.set_cycle("vivid")` — and every set is
grayscale- and CVD-screened.

| Explorer group | Members |
| --- | --- |
| Qualitative (unrelated categories, low→high chroma) | `dm.cycle("default")` · `dm.cycle("print")` · `trustworthy` · `vivid` · `neon` |
| Sequential (ordered amount) | the 20 generative families, ten steps each |
| Analogous (one-mood arcs) | `forest` · `teal_indigo` |
| Muted (soft editorial) | `pastel` · `dusty` |
| Tone (specific mood) | `ember` · `earth` · `jewel` |
| Duo (two opposed groups) | `blue_orange` · `teal_coral` |
| Diverging (± around a midpoint) | `cool_warm` · `teal_amber` · `purple_green` |
| Neutral (hue-free, warm/cool cast) | `gray` · `warm_gray` · `cool_gray` |
| Emphasis (highlight one series) | `teal_accent` · `coral_accent` |
| Accessible (CVD-mandatory) | `accessible` (Okabe-Ito) |

```python
dm.set_cycle("trustworthy")                    # everyday 8-category default
cols = dm.get_palette("cool_warm")             # diverging ± scale (dark→pale→dark)
dm.set_cycle(dm.get_palette("vivid", n=6))     # 6 maximally-distinct categories
dm.set_cycle(dm.get_palette("teal_accent", n=5))  # one teal series, rest gray
```

Single-hue sequential ramps are served by the generative families above (10
recipe-generated steps), so they are not duplicated as curated sets.

## Pick a palette by intent

Pick by the *shape and job* of your data:

- **Everyday 4–8 categories** → Qualitative `dc.cycle` /
  `dm.cycle("default")`, or curated `trustworthy`
- **Many unrelated categories** (up to 8) → high-chroma Qualitative `vivid` /
  `neon`
- **A few related series** → one hue family sampled evenly, or analogous
  `forest` / `teal_indigo`
- **Ordered** (rank / amount) → a single family ramp, or `gray` if hue carries
  no meaning
- **Ordered around a midpoint** (±, change, correlation) → curated diverging
  `cool_warm` / `teal_amber` / `purple_green`
- **Two opposed groups** (A/B, before/after) → curated `blue_orange` /
  `teal_coral`
- **Highlight one series**, mute the rest → curated `teal_accent` /
  `coral_accent`, or `dc.hl` plus gray tones
- **Colorblind-mandatory** → curated `accessible` (Okabe-Ito)

```python
import dartwork_mpl as dm

dm.set_cycle(dm.cycle("default"))        # everyday default cycle (global)
dm.set_cycle(["dc.hl", "dc.gray3", "dc.gray5"], ax=ax)  # one Axes only
dm.set_cycle(dm.get_palette("cool_warm", order="lightness", reverse=True))
```

`dm.get_palette(name, n=None, subset="first"|"even"|"last", *,
order="default"|"lightness"|"shuffle", reverse=False, seed=None)` returns color
names — choose how many (`n` / `subset`), then optionally re-arrange them: `order`
sorts light→dark by lightness or shuffles; `reverse` flips the cycle; `seed` makes a
shuffle reproducible. `dm.set_cycle(palette, ax=None, n=None)` applies a palette (or
an explicit color list) to the global cycle or a single Axes. Family and curated
names both resolve under `dc.` (`"blue"` → `dc.blue0` …; `"trustworthy"` →
`dc.trustworthy0` …).

> The v5 clean break trimmed the throwaway ad-hoc aliases; the curated `dc.*`
> categorical sets are deliberately preserved. See the
> [migration guide](../migration.md) for the manual rename table.

## Explore

Pick a **Qualitative** palette, a **Sequential** family, or another intent group
and read it across nine chart shapes in a single view. Drag the color count,
sort by lightness, shuffle or reverse, preview black-and-white behavior, and
read the CVD metrics in the reference footer. Click a swatch to copy its hex, or
copy the matching `dm.get_palette(...)` / `dm.cycle(...)` call.

```{raw} html
:file: ../_static/categorical_explorer.html
```
