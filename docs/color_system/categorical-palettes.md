# Categorical palettes

dartwork's discrete categorical palettes — a curated **24-palette system across
11 families**. Every palette is **8 colors**, CIELAB-generated and verified for
**black-&-white** and **color-blindness (CVD)**, with the house teal `#12a594`
anchoring the general-purpose sets.

Pick by the *shape and job* of your data:

- **Ordered** (rank / amount) → Sequential, or **Neutral** if hue carries no meaning
- **Ordered around a midpoint** (±, change, correlation) → **Diverging**
- **Highlight one series**, mute the rest → **Focus**
- **A few related series** → Analogous · **Two opposed groups** → Duo
- **Everyday 4–8 categories** → Balanced · **Many unrelated** → Spectrum
- **A specific tone** → Muted, Earth, or Jewel · **Mandatory CVD** → Accessible (Okabe-Ito)

```python
import dartwork_mpl as dm

dm.set_cycle("trustworthy")              # the everyday default cycle (global)
cols = dm.get_palette("spectrum", n=6)   # first 6 — the best-separated subset
dm.set_cycle("teal_accent", ax=ax)             # highlight one series on this Axes only
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
