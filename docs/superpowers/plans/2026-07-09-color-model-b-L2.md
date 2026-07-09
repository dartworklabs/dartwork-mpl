# Color Model B — L2 "API swap" Implementation Plan

> **For agentic workers:** gate-driven plan (codex CLI worker supervised by
> the planning agent). Pinned behaviors below are non-negotiable; mechanics
> are the worker's judgment. Regenerate, never hand-edit, generated artifacts.

**Goal:** Ship the Model B public surface — `dm.colors` / `dm.set_colors` /
`dm.list_colors` / `dm.show_colors` with *designed* discrete forms for every
family kind — and remove the old discrete vocabulary entirely.

**Spec:** `docs/superpowers/specs/2026-07-09-color-model-b-design.md` §4–§5, §6 (L2 row).

## Global Constraints

- Branch `feat/color-model-b-2026-07-09`, this worktree, `.venv`. No push; supervisor commits.
- L0+L1 already landed (43 maps / 45 listed / 88 registered / 56 families / octave).
- `helpers.make_palette` and the engine layer (`Color`, `cspace`, `mix_colors`,
  `pseudo_alpha`, `oklab/oklch/color`) are **kept unchanged**.
- Docs IA rewrite is D1 — here only mechanical snippet/verb truth updates.
- Sphinx noise restore before commit-point; builds with `-D plot_gallery=0`.

## Task A: package rename `colors` → `_colors`

The subpackage name collides with the new `dm.colors` verb. Rename
`src/dartwork_mpl/colors/` → `src/dartwork_mpl/_colors/` (git mv), update all
~40 referencing files (src, tests, docs builders, scripts). Nothing outside
spec/plan documents may still say `dartwork_mpl.colors` afterwards.

## Task B: discrete generators (`src/dartwork_mpl/_colors/_discrete.py`, new)

Deterministic, per spec §5. One public entry:
`discrete_colors(name, n, *, reverse=False) -> list[str]` (hex or registered
token names — document which; be consistent).

- sequential: ladder indices — n≤8 → evenly spaced over window [1, 8];
  n=9 → 0–8; n=10 → 0–9; n>10 → ValueError.
- diverging: canonical 8 (the curated data for the four absorbed families;
  **generate** canonical 8 for the other seven as `[B7,B5,B3,B1,A1,A3,A5,A7]`
  from the pole sequential ladders, where the name is `low_high` = `B_A`…
  verify pole order against the continuous map ends and keep index 0 = low
  pole). Subsets: even n → outer pairs first; odd n → + continuous map's
  center color. n>9 → ValueError. Register tokens `dc.<family>0…7` for the
  seven generated canonicals (the absorbed four already register via curated).
- multi-hue: DP subset of the 256 LUT restricted to L\*∈[35, 90] and chroma ≥
  60% of the family's peak chroma (walk from the peak toward the dark end —
  same rule the colormap explorer's vivid-cutoff uses), maximizing min
  pairwise ΔE00, order-preserving; n≤8, else ValueError.
- cyclic: n equal-phase LUT samples at i/n starting phase 0; n≤24.
- qualitative: designed prefix; n > size → ValueError naming the size.

Gate test (new `tests/test_discrete_forms.py`): for every family × a spread of
n, assert determinism (two calls identical), the kind-specific bounds
(L\* windows, ΔE00 min reported for multi-hue ≥ a measured-then-pinned floor),
diverging n=8 == canonical, qualitative prefix identity, ValueErrors.

## Task C: the four verbs (`src/dartwork_mpl/_colors/_api.py` or similar)

```python
dm.colors(name, n=None, *, reverse=False)
#  n=None → matplotlib Colormap (qualitative → its ListedColormap);
#  n=int  → discrete_colors(...); unknown name → ValueError with the
#  3 nearest names; bare names resolve like today (no "dc." prefix needed,
#  but "dc.aurora" also accepted).
dm.set_colors(name_or_list=None, *, ax=None, n=None, styles=False)
#  None → "octave". Family name → its discrete form (qualitative default =
#  full set; other kinds REQUIRE n, else ValueError with hint). Explicit
#  color list passes through. styles=True → colors × 3 linestyles
#  (absorbs cycle_cycler). ax=None → rcParams, else per-Axes.
dm.list_colors(kind=None)
#  → list of dicts {name, kind, continuous, discrete_size}; 56 records,
#  kind filter validates the kind string.
dm.show_colors(kind=None, names=None, n=None)
#  → Figure preview (continuous ramps + discrete swatches), replaces
#  plot_colors/plot_colormaps/show_palette. Keep it simple.
```

## Task D: qualitative registration

Register the 11 curated qualitative sets as `dc.<name>` ListedColormap
(octave/octave_print already registered) → registered `dc.` names
88 + 11 = **99**. No `_r` for qualitative. Regenerate `_typing.py`.

## Task E: remove the old vocabulary

Delete from the public surface: `get_palette`, `set_cycle`, `cycle`,
`cycle_cycler`, `list_palettes`, `list_colormaps`, `plot_colors`,
`plot_colormaps`, `show_palette`, `classify_colormap` (make internal),
`DartworkColor`/`DartworkColormap` exports (keep the Literal types internal
for signatures). Add a module-level `__getattr__` that raises
`AttributeError` with a one-line pointer (e.g. "removed in the Model B color
API — use dm.colors / dm.set_colors; see docs/color_system") for exactly
those names. Internal callers (style presets, explorers, diagnostics, docs
builders, examples gallery) migrate to the new verbs.

## Task F: integration sweep

- Docs snippets: `docs/color_system/categorical-palettes.md`,
  `docs/usage_guide/colors.md`, `colormaps.md`, examples gallery pages,
  `api/color.rst` — mechanical verb swaps (IA rewrite stays D1);
  `test_docs_snippets` must pass.
- Explorer builders: copy-code strings emit `dm.colors(...)` /
  `dm.set_colors(...)`; regenerate both fragments + update pinned tests;
  node-parse.
- Lint rules / prompt corpus (`asset/prompt/*.yaml|md`) / templates: no stale
  verb references; if an anti-pattern entry mentions old verbs, update the
  guidance to the new ones.
- MCP tools: exercise `dartwork_mpl_info`, `get_color_value`,
  `list_color_families` — fix anything importing removed names.
- `AGENTS.md` / `CLAUDE.md` / `llms.txt`: update color-API mentions;
  regenerate `llms-full.txt` via the docs build.
- Residual grep gate (0 hits outside docs/superpowers + CHANGELOG):
  `get_palette|set_cycle|cycle_cycler|list_palettes|list_colormaps|plot_colormaps|plot_colors|show_palette|dartwork_mpl\.colors`

## Task G: gates + report

Pinned behavior checks (put them in a test or run as smoke and report):

```python
import dartwork_mpl as dm, matplotlib.pyplot as plt
assert callable(dm.colors) and not hasattr(dm, "get_palette")
assert len([c for c in plt.colormaps() if c.startswith("dc.")]) == 99
assert dm.colors("aurora").N == 256 and len(dm.colors("aurora", n=6)) == 6
assert len(dm.colors("blue", n=5)) == 5
assert dm.colors("blue_red", n=8) == dm.colors("blue_red", n=8)  # determinism
assert len(dm.colors("hue", n=12)) == 12
assert len(dm.colors("vivid", n=6)) == 6
assert len(dm.list_colors()) == 56 and len(dm.list_colors(kind="qualitative")) == 13
dm.set_colors("vivid"); dm.set_colors("blue", n=5); dm.set_colors()
```

Full pytest green · ruff clean · sphinx exit 0 · node-parse both fragments.
Report: generator design values (multi-hue min-ΔE floors per family,
diverging pole-order verification), every doc/pin edit, MCP exercise output,
residual grep result, final `git status --porcelain`. No commit.

## Self-review notes

- Spec §4 covered: verbs (C), removals+`__getattr__` hints (E), registration
  (D), tokens for generated diverging (B), engine/helpers untouched
  (constraints). §5 fully in B. §6 L2 row integration list in F.
- Deferred to D1/D3: page IA, legacy widget deletion, migration.md long-form
  rewrite, explorer/lib vivid-cutoff dedup.
