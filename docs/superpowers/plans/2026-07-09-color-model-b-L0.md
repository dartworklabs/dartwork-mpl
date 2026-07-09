# Color Model B — L0 "dead weight" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. (In this session the executor is the codex CLI worker supervised by the planning agent.)

**Goal:** Remove the legacy text-file colormap system end to end so the v5
catalog is the only colormap surface (`dm.list_colormaps()`: 101 → 48
non-reversed names).

**Architecture:** Pure deletion + hook unwiring. The v5 maps register eagerly
on `import dartwork_mpl` (via `dartwork_mpl.colors`); the legacy loader
(`dartwork_mpl.cmap`) was a lazy secondary registry read from
`asset/cmap/*.txt`. Deleting the loader chain leaves behavior identical for
every `dc.*` v5 name. Zero catalog change (that is PR L1).

**Tech Stack:** Python 3.10+, matplotlib, uv, pytest, ruff, sphinx (docs).

**Spec:** `docs/superpowers/specs/2026-07-09-color-model-b-design.md` §3/§6 (L0 row).

## Global Constraints

- Branch: `feat/color-model-b-2026-07-09` (this worktree). NO pushes; commits only.
- Do not touch `src/dartwork_mpl/colors/` internals (v5 system) — L0 is loader removal only. (`colors/_cmaps.py` is v5, NOT legacy — leave it.)
- `icon.py` / `font.py` have their own unrelated `ensure_loaded` — keep those.
- Before any commit: `git checkout HEAD -- docs/_static/*.svg docs/api/images docs/usage_guide/images 2>/dev/null || true` (mpl-3.11 sphinx regen noise).
- Docs builds use `-D plot_gallery=0` (known upstream gallery PDF failures, issue #429).

---

### Task 1: Environment bootstrap + baseline

**Files:** none (env only)

- [ ] **Step 1:** `cd` into the worktree and create the env:

```bash
uv sync --all-extras
```

- [ ] **Step 2:** Baseline test run (must be green before any change):

```bash
.venv/bin/python3 -m pytest -x -q 2>&1 | tail -5
```

Expected: all pass (record the count, e.g. `N passed`).

### Task 2: Remove the loader chain (src)

**Files:**
- Delete: `src/dartwork_mpl/cmap.py`
- Delete: `src/dartwork_mpl/asset/cmap/` (56 `.txt` files)
- Delete: `scripts/generate_cmaps.py` (legacy txt generator)
- Modify: `src/dartwork_mpl/__init__.py:35` (import block) and `:326-327` (comment)
- Modify: `src/dartwork_mpl/style.py:343-348` (stack() hook)
- Modify: `src/dartwork_mpl/explore.py:100-102` (list_colormaps hook)
- Modify: `src/dartwork_mpl/diagnostics/_colormaps.py:41` (comment) and `:~350` (plot_colormaps hook)
- Modify: `src/dartwork_mpl/icon.py:149-150` (docstring cross-ref)

**Interfaces:**
- Produces: `dm.list_colormaps()` / `dm.plot_colormaps()` keep signatures; they
  now enumerate only what is registered at import (46 v5 + 2 cycles, + `_r`).
  `dm.cmap` module attribute no longer exists.

- [ ] **Step 1:** Delete files:

```bash
git rm src/dartwork_mpl/cmap.py scripts/generate_cmaps.py
git rm -r src/dartwork_mpl/asset/cmap
```

- [ ] **Step 2:** `__init__.py` — remove `cmap,` from the submodule import
  block (line 35) and fix the eager/lazy comment (lines 326-327):

```python
from . import (  # noqa: F401
    font,
    helpers,
    icon,
    lint,
    templates,
    tokens,
    validate_fixes,
)
```

and replace the two comment lines mentioning "legacy ``asset/cmap`` text maps
stay on-demand behind ``dm.cmap.ensure_loaded()``" with a single line stating
that all `dc.*` colormaps register eagerly via the ``dartwork_mpl.colors``
import above.

- [ ] **Step 3:** `style.py` `stack()` — drop the cmap hook, keep fonts:

```python
        from .font import ensure_loaded as ensure_fonts_loaded

        # Ensure fonts are registered before Matplotlib tries to resolve
        # them (v5 colormaps register eagerly at import time).
        ensure_fonts_loaded()
```

- [ ] **Step 4:** `explore.py` `list_colormaps()` — remove the two hook lines
  (`from .cmap import ensure_loaded` / `ensure_loaded()`); the body keeps
  filtering `plt.colormaps()` for `dc.` names.

- [ ] **Step 5:** `diagnostics/_colormaps.py` — remove the
  `from ..cmap import ensure_loaded as ensure_cmaps_loaded` import and its
  call inside `plot_colormaps`; update the module comment at line 41 so it no
  longer mentions "the asset/cmap maps exposed by dartwork_mpl.cmap".

- [ ] **Step 6:** `icon.py` docstring — reword the cross-reference so it only
  cites `dartwork_mpl.font.ensure_loaded` (drop the `dartwork_mpl.cmap` one).

- [ ] **Step 7:** Import smoke + count check:

```bash
.venv/bin/python3 - <<'EOF'
import dartwork_mpl as dm
names = dm.list_colormaps()
assert not hasattr(dm, "cmap"), "dm.cmap must be gone"
assert len(names) == 48, f"expected 48 non-reversed dc.* names, got {len(names)}"
print("OK", len(names))
EOF
```

Expected: `OK 48`.

### Task 3: Prune tests + re-pin counts

**Files:**
- Modify: `tests/test_concurrency.py` (delete `TestCmapEnsureLoadedConcurrency`
  class at :169-213, the `_reset_cmap_loaded` fixture at :75, the imports at
  :42/:45, and the module-docstring mention at :4)
- Modify: any failing count-pin tests (`tests/test_docs_count_claims.py`,
  `tests/test_docs_asset_inventory.py`, `tests/test_explore.py`,
  `tests/test_docs_snippets.py`, `tests/test_docs_color_tokens.py`) — update
  pins to the post-deletion truth (48 names, no `asset/cmap`), never by
  weakening an assertion to `>=`.

- [ ] **Step 1:** Delete the cmap-loader concurrency tests + fixture + imports.
- [ ] **Step 2:** Run the suite; fix every failure by re-pinning to the new
  truth (list each in the report):

```bash
.venv/bin/python3 -m pytest -q 2>&1 | tail -8
```

Expected: green, total count = baseline minus the deleted loader tests.

### Task 4: Docs prune

**Files:**
- Delete: `docs/api/cmap.rst`
- Modify: `docs/api/index.rst:44` (drop `Colormap Registry <cmap>` toctree line)
- Modify: `docs/color_system/colormaps.md:1-15` (rewrite head)
- Sweep: any other docs page matching the residual grep in Step 3

- [ ] **Step 1:** `git rm docs/api/cmap.rst` and remove the toctree entry.
- [ ] **Step 2:** Replace the first two paragraphs of `colormaps.md` with:

```markdown
# Colormaps

The colormap surface is the v5 catalog: **46 colormaps**, their `_r`
reverses, and **2 qualitative cycle maps** (`dc.cycle`, `dc.cycle_print`)
registered for `cmap=` interfaces — `dm.list_colormaps()` returns the 48
non-reversed names. Every map is generated by the same perceptual recipe as
the `dc.*` palette — designed on CIELAB L\* and OKLCH, equalized in OKLab ΔE,
and checked against hard gates before it ships.
```

- [ ] **Step 3:** Residual sweep (must end at zero hits):

```bash
grep -rnE "dartwork_mpl\.cmap|from \.cmap|from \.\.cmap|asset/cmap|dm\.cmap|legacy text-file" \
  src tests docs/api docs/color_system docs/usage_guide scripts llms.txt llms-full.txt \
  --include="*.py" --include="*.rst" --include="*.md" --include="*.txt" | grep -v superpowers || echo CLEAN
```

Expected: `CLEAN` (spec/plan files under docs/superpowers are exempt).

- [ ] **Step 4:** Targeted docs rebuild:

```bash
.venv/bin/python3 -m sphinx -b html docs docs/_build/html -D plot_gallery=0 -q 2>&1 | tail -3
```

Expected: exit 0, `build succeeded` (font-fallback warnings are pre-existing noise).

### Task 5: Verify + commit

- [ ] **Step 1:** Full gates:

```bash
.venv/bin/python3 -m pytest -q 2>&1 | tail -3
.venv/bin/ruff check . && .venv/bin/ruff format --check . 2>&1 | tail -2
```

- [ ] **Step 2:** Restore sphinx regen noise, then single atomic commit
  (code+tests+docs are one green unit — count-pin tests couple them):

```bash
git checkout HEAD -- docs/_static/*.svg docs/api/images docs/usage_guide/images 2>/dev/null || true
git status --porcelain   # review: only intended paths
git add -A -- src tests docs/api docs/color_system scripts
git commit -m "refactor(colors)!: remove legacy text-file colormap system (L0)

46 v5 maps + 2 cycles are the only colormap surface; list_colormaps
101 -> 48 non-reversed names. Deletes the lazy loader (dartwork_mpl.cmap),
asset/cmap txt assets, generator script, loader hooks in style/explore/
diagnostics, api/cmap.rst, and the loader-concurrency tests.

Spec: docs/superpowers/specs/2026-07-09-color-model-b-design.md (L0)"
```

If the pre-commit hook aborts with a stash-conflict warning, rerun the same
`git add` + `git commit` once (known hook behavior).

---

## Self-review notes

- Spec coverage: L0 row fully mapped (loader, assets, generator, hooks ×4
  files, rst, tests, count re-pins). `dm.*` alias / `set_palette_version` /
  frozen tokens verified already absent on main → no tasks.
- No placeholders; every edit has exact code or exact deletion targets.
- Deliberately NOT touched: `colors/` package, explorers, presets, llms
  regeneration (0 legacy mentions verified) — those belong to L1/L2.
