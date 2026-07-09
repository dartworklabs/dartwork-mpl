# Color system "Model B" — one noun, one rule: *the name is a family, `n` picks the form*

Date: 2026-07-09 · Status: approved design (user-reviewed) · Scope: dartwork-mpl
color API + catalog + docs IA · Breaking changes: allowed (zero external users;
workspace grep confirms 0 usages of every removed symbol/name).

## 1. Problem

The color surface accumulated two parallel systems (discrete palettes vs
continuous colormaps) plus migration-era debt. Concrete findings:

1. **Four words for one concept** — cycle / palette / cycler / categorical,
   spread over four verbs (`set_cycle`, `get_palette`, `cycle`,
   `cycle_cycler`).
2. **Registry asymmetry** — `dc.blue` (continuous) and `dc.cycle` (discrete)
   are registered colormaps; `dc.vivid` (discrete) is not. No rule.
3. **Name collisions as a symptom** — `blue_orange` and `teal_amber` exist as
   *independently designed* discrete palettes AND continuous diverging maps.
4. **Legacy double surface** — 56 text-file colormaps beside the 46 v5 maps;
   `dm.list_colormaps()` returns 101 names. Plus the `dm.*` token alias,
   `set_palette_version()`, and three frozen legacy families.
5. **Docs drift** — docs claim a "24-palette system"; the code ships 20.
   `corona`/`halo` are documented as diverging but measurably wrap
   (ΔE00(ends) = 1.9 / 2.0 ≤ 2 → cyclic); `hue` wraps at 0.7.
6. **Naive discretization is not categorical** — measured on the shipped
   package (min pairwise ΔE00, CIELAB L\* range, grayscale ΔE, a\*b\*-plane
   separation, 8 colors):

   | set | minΔE00 | deutan | L\* range | gray | Δab |
   |---|--:|--:|--:|--:|--:|
   | curated `octave` cycle (7) | 18.6 | 10.3 | 43–78 | 2.0 | 28.1 |
   | curated `vivid` | 12.1 | 4.3 | 40–84 | 4.3 | 18.2 |
   | resampled `dc.aurora`@8 | 12.5 | 9.4 | **14–96** | 5.2 | 11.8 |
   | resampled `dc.blue`@8 | 8.9 | 9.1 | 24–96 | 5.3 | **1.6** |
   | resampled `dc.blue_red`@8 | 8.4 | 8.1 | 61–91 | **0.0** | 12.5 |

   Failure modes of naive resampling for unordered series: grayscale collapse
   (diverging arms mirror to ΔE 0.0), chromatic collapse (single-hue Δab 1.6),
   illegible extremes (L\* 14–96 on white), and implied order. Hence discrete
   forms must be **designed**, never resampled.

## 2. Decision — four axioms

```
A1 (namespace)  Only dc.* is the family system. Third-party design systems
                (oc./tw./md./ad./cu./pr.) are token-only registrations.
A2 (asset unit) Every color asset is a *family* with exactly one kind:
                sequential · multi-hue · diverging · cyclic · qualitative.
A3 (forms)      A family has a continuous form (Colormap) and a *designed*
                discrete-n form. n picks the form. Discrete forms are never
                naive resamples.
A4 (access)     color="dc.X#" (tokens) · cmap="dc.X" (families) ·
                dm.colors("X", n) · dm.set_colors("X"). Nothing else.
```

Kinds are decided by **measurable invariants**, enforced in CI (not by
narrative):

| kind | invariant (measured) | discrete-n source | name grammar |
|---|---|---|---|
| sequential | monotonic L\*, open ends | token-ladder subset (n ≤ 10, interior window for n ≤ 8) | hue noun (`blue`) |
| multi-hue | monotonic L\*, multi-hue path | L\*∈[35, 90] clamp + max–min-ΔE00 subset along the path (n ≤ 8), deterministic | natural-light scene (`aurora`) |
| diverging | interior anchor, two monotonic arms, L\*-mirrored ±tol | designed canonical 8 (absorbed curated set where one exists; else generated from pole-family ladders), subsets from it | `low_high` pair (`blue_red`) |
| cyclic | ΔE00(color(0), color(1)) ≤ 2.01 (measured seams: hue 0.7 / halo 1.9 / corona 2.0), no interior seam | equal-phase samples at i/n (wrap-aware), n ≤ 24 | circular-light phenomenon (`halo`) |
| qualitative | unordered point cloud, L\* legibility band | the curated set itself (prefix-optimized order; `n` = prefix), no continuous form | mood noun (`vivid`) or `<hue>_accent` |

After the ledger below, **name grammar ↔ kind is 1:1 with zero exceptions**,
so the kind of any family is guessable from its name (AI-native requirement).

## 3. Exceptions ledger — every non-conforming asset, dispositioned

| asset | violation | disposition |
|---|---|---|
| `coast` | scene name + datum anchor ("topographic" singleton) | **delete** (a terrain map may return later as a proper `low_high` diverging family) |
| `blue_red_deep`, `blue_red_soft` | only strength variants in the catalog | **delete** (strength axis only returns if generalized to all diverging) |
| `corona`, `halo` | docs classify diverging; ends measurably wrap | **reclassify cyclic** (invariant-based) |
| palette `cool_warm` | duplicates `blue_red` concept | **delete → absorbed as `blue_red`'s canonical discrete form** |
| palette `purple_green` | duplicates `green_purple` (flipped) | **delete → absorbed as `green_purple`'s discrete form (order flipped to match low_high)** |
| palettes `blue_orange`, `teal_amber` | name-collide with continuous maps | **absorbed** as those diverging families' discrete forms (collision dissolves) |
| palettes `warm_gray`, `cool_gray` | duplicate `gray` family; ordered ladders posing as qualitative | **delete** |
| palette `teal_coral` | ≈ `teal_rose` duplicate; pair-name grammar collision | **delete** |
| palette `teal_indigo` | analogous niche; pair-name grammar collision | **delete** (adjacent-hue jobs: take two sequential families' tokens) |
| palette `accessible` (Okabe-Ito) | external constant outside the generative system | **delete** (kept as a benchmark comparison in the design-rationale page only; `octave` passes the CVD gates) |
| `dc.cycle` = `octave` = `"default"` triple naming | alias debt | **single name `octave` / `octave_print`**; registry `dc.octave`, `dc.octave_print`; `dc.cycle*` and `"default"`/`"print"` aliases removed |
| legacy text-file maps (56) + `cmap.py` loader | double surface | **delete** (with `docs/api/cmap.rst`, `scripts/generate_cmaps.py`, the loader hooks in `style.py`/`explore.py`/`diagnostics`, and the loader-concurrency tests) |
| `dm.*` token alias, `set_palette_version()`, frozen legacy tokens (teal/indigo/gray) | migration remnants | **no action — already removed on main** (verified 2026-07-09; earlier sightings came from a stale working tree) |
| `teal_accent`, `coral_accent` | position-0-is-accent order semantics | **keep** — `<hue>_accent` promoted to official qualitative sub-grammar |
| docs "24 palettes", "42/46 maps", "101 names" | stale numbers | all counts rendered from code by doc builders |

**Final catalog (56 families, zero exceptions):**
sequential 20 (`red rose coral tangerine orange amber yellow lime green teal
cyan sky blue cobalt indigo violet purple fuchsia pink gray`) ·
multi-hue 9 (`afterglow aurora blaze canopy glacier haze iris lagoon lava`) ·
diverging 11 (`blue_red blue_orange cyan_red teal_amber teal_rose indigo_amber
green_purple purple_orange violet_lime gray_blue gray_red`) ·
cyclic 3 (`hue halo corona`) ·
qualitative 13 (`trustworthy vivid neon pastel dusty ember earth jewel forest
teal_accent coral_accent octave octave_print`).

## 4. Public API surface (complete)

```python
# strings (matplotlib-native channels)
color="dc.blue6"      # tokens: families with a canonical discrete form only
color="dc.vivid3"     #   sequential 0–9 · diverging 0–7 · qualitative 0–(size-1)
color="dc.pos"        # semantic tokens (pos/neg/ref/hl, locale-aware) — unchanged
cmap="dc.aurora"      # every family registers; qualitative as ListedColormap
cmap="dc.blue_r"      # continuous kinds also register _r (qualitative: no _r)

# verbs (2)
dm.colors(name, n=None, *, reverse=False)
#   n=None → Colormap (qualitative → ListedColormap; invariant: no n, no list)
#   n=int  → list[str] of designed discrete colors (never resampled)
#   errors: unknown name → ValueError listing nearest matches;
#           n > design max → ValueError stating the family's max and kind.
dm.set_colors(name_or_list=None, *, ax=None, n=None, styles=False)
#   sets prop_cycle globally or per-Axes; default family "octave";
#   styles=True expands colors × 3 linestyles (absorbs cycle_cycler).

# discovery (2)
dm.list_colors(kind=None)   # structured records: name, kind, forms, size,
                            # gate metrics (agents self-describe the catalog)
dm.show_colors(...)         # visual preview (absorbs plot_colors /
                            # plot_colormaps / show_palette)

# engine (unchanged)
dm.color() / dm.oklab() / dm.oklch() / Color / dm.cspace() /
mix_colors / pseudo_alpha  (+ helpers.make_palette — a user-palette
construction helper on the engine layer, kept as-is)
```

**Removed public API**: `get_palette`, `set_cycle`, `cycle`, `cycle_cycler`,
`list_palettes`, `list_colormaps`, `plot_colors`, `plot_colormaps`,
`show_palette`, `classify_colormap` (becomes an internal gate),
`set_palette_version`, `DartworkColor` / `DartworkColormap` (private),
`dm.cmap` module. `get_palette`'s `subset/order/shuffle/seed` kwargs are not
inherited — list manipulation is plain Python.

Known, accepted limits: (a) seaborn-side sampling of a *continuous* family
(`sns.color_palette("dc.blue", 6)`) is naive — `dm.colors` is the designed
path and docs say so; (b) choosing a sequential family for unordered series
is legal (ordinal use) — a lint hint + docs matrix mitigate.

## 5. Discrete-form recipes (deterministic, gated)

- **sequential**: index windows over the 0–9 ladder; n ≤ 8 uses the interior
  window [1, 8] evenly spaced (legibility gate L\*∈[30, 85]); n = 9 → 0–8;
  n = 10 → 0–9.
- **diverging**: canonical 8 = absorbed curated data (`blue_red`,
  `green_purple`, `blue_orange`, `teal_amber`) or generated
  `[B7,B5,B3,B1,A1,A3,A5,A7]` from pole-family ladders; subsets take outer
  pairs first; odd n inserts the map's center color.
- **multi-hue**: dynamic-programming subset of the 256-LUT restricted to
  L\*∈[35, 90] and chroma ≥ the family's vivid-cutoff, maximizing min pairwise
  ΔE00 while preserving path order. Deterministic; gated (min ΔE00 reported).
- **cyclic**: n equal-phase samples at i/n (endpoints not duplicated).
- **qualitative**: designed prefix order (first-n is the optimized subset);
  n > size raises.

Tokens exist exactly where a canonical ladder exists: sequential (0–9),
diverging (0–7, new), qualitative (0–size-1). Multi-hue and cyclic have no
tokens (n-dependent forms).

## 6. Delivery plan — PR ladder (each PR independently green)

| PR | scope | notes |
|---|---|---|
| **L0 — dead weight** | delete the legacy text-file colormap system end to end (loader, 56 txt assets, generator script, `style.py`/`explore.py`/`diagnostics` hooks, `api/cmap.rst`, loader-concurrency tests); re-pin doc count claims | zero catalog change; mostly deletions |
| **L1 — catalog truth** | ledger surgery (delete coast/_deep/_soft/7 palettes; absorb 4 into diverging; corona+halo → cyclic; octave rename incl. preset references); family metadata (kind, forms, sizes); CI invariant gates; colormap-explorer + categorical-explorer payload/tests/doc numbers regenerated (partition 20/9/11/3 = 43 maps + 13 qualitative) | old verbs still work on surviving names |
| **L2 — API swap** | `dm.colors` / `set_colors` / `list_colors` / `show_colors`; discrete generators per §5; qualitative ListedColormap + diverging-token registration; remove old verbs; preset prop_cycle audit (presets route through `octave` unless deliberately overridden); sync lint rules, MCP tools, llms.txt / llms-full.txt, prompt corpus, AGENTS/CLAUDE.md; explorer copy-code emits `dm.colors` | breaking swap, no users |
| **D1 — color docs IA** | restructure Design System pages to the family model (final page names + theory placement confirmed at kickoff — defaults: catalogs `Colors` / discrete / continuous split with explorers kept; `Design rationale` last, flat; `Color class` promoted); delete legacy widgets (`palette_picker`, `palette_explorer`) + stale POC files; all numbers builder-rendered | user decisions #2/#3 land here |
| **D2 — fonts explorer** | rebuild the fonts page widget on the explorer framework (rail + demos + controls + dark mode + replace-last), reconcile font counts | separate feature |
| **D3 — docs-wide sync** | usage_guide/colors rewrite on the new API, landing, troubleshooting, migration note for the removed API | final sweep |

Release: everything folds into the user-driven 0.6.0 release (existing
release branch is rebased then; tagging/publishing stays a user action).

## 7. Verification

- CI kind-invariant gates (monotone L\*, mirror tol, wrap ΔE ≤ 2, qualitative
  legibility band) over the whole catalog — the measurements in §1/§3 become
  pinned tests.
- Discrete generators: per-family min-ΔE00 / L\*-band assertions; goldens for
  canonical forms.
- Explorer builders regenerate + partition asserts; docs build clean
  (`-D plot_gallery=0`); ruff; node-parse of fragments.
- Workspace smoke: company-analysis + valuation grep for removed names
  (baseline 0 confirmed 2026-07-09); token/`cmap=` strings for surviving
  families unchanged.
- llms.txt / llms-full.txt regenerated; MCP `dartwork_mpl_info` /
  `get_color_value` / `list_color_families` exercised against the new API.

## 8. Open questions (defaults if not revisited)

1. **D1 page names & theory placement** — default: flat sidebar `Overview /
   Colors / <discrete page> / <continuous page> / Color class / Fonts /
   Design rationale`; exact titles decided at D1 kickoff (user decisions #2
   and #3, POC already served).
2. Multi-hue optimizer parameters (L\* band, chroma cutoff) are tunable
   constants — locked by gate outputs, not by narrative.
3. Preset audit may reveal presets that intentionally diverge from `octave`
   (e.g., `dmpl.mplstyle`'s hand-picked 8-token cycle) — keep deliberate
   overrides, document them, route the rest through `octave`.
