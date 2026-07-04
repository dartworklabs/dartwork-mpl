# Math & special characters

Scientific and report figures lean on symbols that a body typeface never
ships — arrows, operators, Greek, units, and the occasional ⚠ or ★.
dartwork-mpl covers these two ways: a **mathtext** stack for `$…$`
expressions, and a **plain-text fallback chain** so bare symbols in labels
and annotations render instead of turning into tofu (□). Both work out of
the box under every preset; no configuration and no TeX install.

## Mathtext (the `$…$` stack)

Every preset sets `mathtext.fontset: custom` with all math roles mapped to
**Noto Sans Math**, so inline math matches the sans body rather than
switching to Computer Modern:

```python
import dartwork_mpl as dm
import matplotlib.pyplot as plt

dm.style.use("scientific")
fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
ax.set_title(r"$x^2 + \alpha_i \geq \sqrt{\beta} \cdot \sum_n \frac{1}{n^2}$")
```

Any glyph outside Noto Sans Math's coverage falls back to matplotlib's
built-in **STIX** fonts (`mathtext.fallback: stix`) — bundled with
matplotlib itself, so it costs zero extra bytes and no math glyph
hard-fails to a dummy box.

## Plain-text symbols (labels, annotations, ticks)

You do **not** need `$…$` for a single symbol in a label. dartwork-mpl's
`font.family` is an explicit fallback chain, so matplotlib resolves each
character against it per glyph:

```python
ax.set_ylabel("Δσ (‰)")
ax.annotate("≈ ±1.5 σ  →  ✓", xy=(0.5, 0.5))
ax.text(0.1, 0.9, "T ≥ 25 ℃  ⚠")
```

The guaranteed plain-text set — covered by the bundled chain under both the
Latin and Korean presets — includes:

| Group | Glyphs |
| ----- | ------ |
| Arrows | → ← ↑ ↓ ⇒ |
| Relations / operators | ± × ÷ ≈ ≠ ≤ ≥ ∑ ∏ √ ∞ ∂ ∫ |
| Units / misc | ℃ ‰ µ Ω |
| Greek | α β γ σ |
| Mathematical alphanumeric | 𝜎 𝑥 |
| Dingbats | ⚠ ✓ ★ |

### How the fallback chain resolves them

matplotlib builds its per-glyph fallback list from `font.family` (an
**explicit** family list — not the generic `sans-serif` alias, which would
collapse to a single face). The bundled order is:

1. **Roboto / Inter** — Latin body, most arrows and operators;
2. **Paperlogy / Noto Sans CJK KR / Pretendard** — Korean, plus `℃` and
   broad symbol coverage;
3. **Noto Sans Math** — Greek, mathematical-alphanumeric (𝜎, 𝑥), and the
   full operator set;
4. **Noto Sans Symbols / Noto Sans Symbols 2** — dingbats and technical
   symbols (⚠ ✓ ★).

Korean presets lead with Paperlogy but append the same math/symbol faces,
so the symbol set is identical in `report-kr` and friends.

## Full LaTeX is not bundled

Setting `text.usetex: True` routes typesetting through a **local TeX
installation** (TeX Live / MacTeX and `dvipng`). dartwork-mpl does **not**
bundle TeX — it is far too large to ship in a wheel — so `usetex` only
works if you have TeX installed system-wide. For the vast majority of
figures the mathtext stack above is enough and needs no external tools; reach
for `usetex` only when you need a construct mathtext cannot express.
