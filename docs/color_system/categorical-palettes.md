# Categorical palettes

dartwork's discrete categorical palettes — a curated **24-palette system across
11 families**. Every palette is **8 colours**, CIELAB-generated and verified for
**black-&-white** and **colour-blindness (CVD)**, with the house teal `#12a594`
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
dm.set_cycle("focus", ax=ax)             # highlight one series on this Axes only
```

`dm.get_palette(name, n=None, subset="first"|"even"|"last")` returns colour names;
`dm.set_cycle(palette, ax=None, n=None)` applies a palette (or an explicit colour
list) to the global cycle or a single Axes. Bare names resolve under `dc.`
(`"trustworthy"` → `dc.trustworthy0…7`).

## Explore

Pick a palette, drag the colour count, toggle B&W / dark-canvas, and compare it
across nine chart shapes at once.

```{raw} html
<iframe src="../_static/palette_explorer.html" title="dartwork palette explorer"
        loading="lazy"
        style="width:100%;height:1500px;border:1px solid var(--dm-border-faint,#e6e6e6);border-radius:12px;">
</iframe>
```

> The design rationale (the eight criteria, the colour-count decision, and the
> spectral-width + intent-family organisation) lives in
> `docs/_static/dartwork-discrete-palette-rationale.md`; the colours are
> generated and verified by `docs/_static/scripts/gen_palettes.py`.
