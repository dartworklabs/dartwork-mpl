# Color Model B — L1 "catalog truth" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. (In this session: codex CLI worker supervised by the planning agent.) This plan is gate-driven: where mechanics are obvious from the anchors, the worker has latitude; the pinned numbers and gates are non-negotiable.

**Goal:** Make the shipped catalog exactly match the spec's final catalog —
56 families, zero exceptions (sequential 20 · multi-hue 9 · diverging 11 ·
cyclic 3 · qualitative 13) — with kind metadata + measured invariant gates,
and both docs explorers regenerated to that truth.

**Architecture:** Colormaps are compiled from `colors/_cmaps.py` into the
checked-in `colors/_generated.py` by `python -m dartwork_mpl.colors._build`;
curated discrete sets live in `colors/_curated.py` (CURATED_ORDER / CURATED /
CURATED_META); typing literals regenerate via `scripts/generate_typing.py`;
both docs explorers read those modules directly. All surgery happens at those
SSOTs, then everything downstream is regenerated, never hand-patched.

**Spec:** `docs/superpowers/specs/2026-07-09-color-model-b-design.md` §2–§3, §6 (L1 row).

## Global Constraints

- Branch `feat/color-model-b-2026-07-09`, this worktree, `.venv` provisioned. No push; supervisor commits.
- Old verbs (`get_palette`, `set_cycle`, `cycle`, …) stay working on surviving names — the API swap is L2.
- No new discrete-form *generators* (ladder subsets, multi-hue optimizer) — L2. L1 only moves/renames existing designed data.
- Before commit-point: `git checkout HEAD -- docs/_static/*.svg docs/api/images docs/usage_guide/images 2>/dev/null || true`; docs builds with `-D plot_gallery=0`.

## Pinned numbers (the gates)

| quantity | before | after |
|---|--:|--:|
| v5 colormaps (non-reversed, excl. cycles) | 46 | **43** |
| `dm.list_colormaps()` non-reversed names | 48 | **45** |
| registered `dc.` cmap names incl. `_r` | 94 | **88** |
| curated sets in `_curated.py` rail (qualitative) | 20 | **13** |
| explorer taxonomy partition | 20/10/15/1 | **20/9/11/3** |
| cycle registry names | `dc.cycle`, `dc.cycle_print` | **`dc.octave`, `dc.octave_print`** |

---

### Task 1: Colormap catalog surgery

**Files:** `src/dartwork_mpl/colors/_cmaps.py` (delete the `coast`,
`blue_red_deep`, `blue_red_soft` constructions; ~:361, :378), then regenerate
`colors/_generated.py` (`python -m dartwork_mpl.colors._build`) and typing
(`scripts/generate_typing.py`).

- [ ] Delete the three map definitions (and any helper used only by them,
      e.g. `seq_topo` if coast was its only consumer).
- [ ] Regenerate `_generated.py` + `_typing.py`; smoke:

```bash
.venv/bin/python3 - <<'EOF'
import dartwork_mpl as dm
n = dm.list_colormaps()
assert len(n) == 45, len(n)
for gone in ("dc.coast", "dc.blue_red_deep", "dc.blue_red_soft"):
    assert gone not in n
print("OK 45")
EOF
```

### Task 2: Cyclic reclassification (corona, halo)

No registry change — kind metadata only (Task 4) plus every docs/test claim
that calls them diverging. Wrap invariant justification: measured
ΔE00(ends) = hue 0.7 / halo 1.9 / corona 2.0 (≤ 2 gate).

### Task 3: Curated surgery (`colors/_curated.py`)

- [ ] Delete sets: `warm_gray`, `cool_gray`, `teal_coral`, `teal_indigo`,
      `accessible` (Okabe-Ito benchmark numbers may move into a code comment
      or the design-rationale docs, not the catalog).
- [ ] Rename (data preserved): `cool_warm` → `blue_red`,
      `purple_green` → `green_purple` (flip color order so index 0 is the
      *low* pole per the `low_high` grammar — verify against the continuous
      map's pole hues). `blue_orange`, `teal_amber` keep their names.
- [ ] Mark the four renamed sets as **diverging canonical discrete forms**
      (CURATED_META kind or a separate structure — worker's choice) such that:
      (a) `dm.get_palette("blue_red")` returns the 8 colors,
      (b) tokens `dc.blue_red0…7` etc. register,
      (c) the categorical explorer rail shows **only the 13 qualitative sets**
      (11 curated + `octave` + `octave_print` if the rail includes cycles —
      match whatever the rail's current cycle handling is, but curated
      non-cycle count must be 11).
- [ ] Update `CURATED_ORDER`/`CURATED_META` intent groups accordingly
      (deleted intents like Analogous/Accessible disappear from meta).

### Task 4: Family metadata + invariant gates

**Files:** create `src/dartwork_mpl/colors/_families.py` + `tests/test_family_invariants.py`.

- [ ] `FAMILIES: dict[str, Family]` — every family name → kind
      (`sequential|multi-hue|diverging|cyclic|qualitative`), has_continuous,
      discrete_size (10 sequential ladders / 8 diverging canonical / set size
      qualitative / None otherwise). Derive membership programmatically where
      possible (from `_generated`/`_curated`), assert the partition
      20/9/11/3/13 = 56.
- [ ] Gate test measures with `colors._metrics` (the invariants, one test per kind):
      sequential/multi-hue → strictly monotonic L\* on the 256 LUT (tolerance
      for float noise); diverging → the two arms around the L\* extremum are
      monotonic and L\*-mirrored within tol (measure first, pin with margin);
      cyclic → ΔE00(color(0), color(1)) ≤ 2; qualitative → all member colors
      L\* within [35, 92] (octave_print's dark gray may need the lower bound
      checked — measure, then pin the observed band with ~2 L\* margin, and
      record the final band in the report).

### Task 5: `octave` rename (kill the triple name)

- [ ] `colors/_register.py`: register `dc.octave` / `dc.octave_print`
      (drop `dc.cycle*`); `colors/_cycle_api.py`: canonical names only —
      remove the `"default"`/`"print"` aliases (`dm.cycle("octave")`,
      `dm.cycle()` default stays octave).
- [ ] Sweep every reference: `grep -rn "dc\.cycle\|\"default\"\|'print'" src tests docs --include=...`
      — judgment applies (only cycle-related hits), including
      `docs/color_system/*.md`, `docs/usage_guide/colors.md`,
      `docs/_static/dartwork-discrete-palette-rationale.md`, explorer builders
      (categorical explorer already uses octave naming internally), typing regen.

### Task 6: Explorers + docs truth sync

- [ ] `docs/_static/scripts/build_colormap_explorer.py`: taxonomy partition →
      20/9/11/3 (= 43); corona/halo move to the Cyclic group; remove coast
      (and its "Segmented" chip special-casing if present); regenerate
      fragment; update its pinned tests.
- [ ] `docs/_static/scripts/build_categorical_explorer.py`: regenerates from
      the surviving 13; verify rail groups; update pinned tests
      (`tests/test_palette_family_taxonomy.py`,
      `tests/test_colormap_explorer_taxonomy.py`).
- [ ] Docs factual edits (IA rewrite is D1 — here only truth): catalog table +
      counts in `docs/color_system/colormaps.md` (43 maps, cyclic row `hue
      halo corona`, no coast/topographic row, no `_deep/_soft` mention),
      `docs/color_system/categorical-palettes.md` (13 sets, updated intent
      list, octave names), `design.md` / `usage_guide/colors.md` /
      `space.md` count or name mentions revealed by grep + count-claim tests.
- [ ] Node-parse both regenerated fragments.

### Task 7: Gates + report

- [ ] Full `.venv/bin/python3 -m pytest -q` green; `ruff check` + `format --check` clean.
- [ ] Sphinx targeted rebuild of the color pages exit 0 (`-D plot_gallery=0`).
- [ ] Report: partition assert output, invariant-gate measured values (esp.
      diverging mirror tol + qualitative L\* band), all count-pin updates
      (file: old → new), residual grep results, final `git status --porcelain`.
      No commit (supervisor commits).

## Self-review notes

- Spec coverage: §3 ledger rows coast/_deep/_soft (T1), corona+halo (T2/T4),
  curated 7 dispositions (T3), octave (T5), counts/docs (T6). Deferred to L2
  by design: discrete generators, `dm.colors`, qualitative cmap registration,
  diverging tokens beyond the four absorbed sets' existing token mechanism.
- Deviation from full-code granularity is deliberate: the repo is
  generator+gate driven; pinned numbers and measured gates carry correctness.
