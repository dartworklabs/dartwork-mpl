# `dm.color` Parser & `color → colors` Module Rename — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce `dm.color(value)` as a single string-parser entry point for color creation (mirrors `dm.length`), rename the `color` submodule to `colors` with a backward-compatibility shim, and deprecate `dm.named` (kept working with `DeprecationWarning`).

**Architecture:**
- New `Color.parse(value: str) → Color` classmethod dispatches by leading `#`, functional `rgb(...)`/`oklch(...)`/`oklab(...)`, or palette-name fallback.
- Module-level `color(value: str | Color) → Color` is a thin wrapper handling pass-through, mirroring `length(value: str | Length) → Length`.
- Submodule rename: `src/dartwork_mpl/color/` is moved to `colors/`; old `color/` becomes a stub package re-exporting from `colors/` and emitting `DeprecationWarning` once on import.
- Specialized constructors (`dm.hex`, `dm.rgb`, `dm.oklch`, `dm.oklab`) are unchanged.

**Tech Stack:** Python 3.10+, matplotlib, pytest, YAML lint catalog (`asset/prompt/02-anti-patterns.yaml`).

**Tracking issue:** dartworklabs/dartwork-mpl#164

---

## ⚠️ Scope reduction (decided after plan was written)

User constraint: *internal-only project, near-zero external users — keep code clean rather than maintain legacy entry points*. Concretely:

- **Drop Task 2 (backward-compat shim)**. `dartwork_mpl.color` becomes a hard rename to `dartwork_mpl.colors`; no shim package, no deprecation warning at module level. All internal callers updated in Task 1.
- **Drop the deprecation cycle for `dm.named`** — replace it with hard removal. The old `named()` function is deleted from `_color.py`, removed from all `__all__` / re-export blocks, and the `TestNamed` test class is deleted. Every call site is rewritten to `dm.color`.
- **Drop Tasks 7 and 8 (lint rule and `migrate_legacy_code` rewrite)** — they were dual-use safety nets for external users. Internal-only means we just edit the call sites.
- **Final guarantee**: full pytest suite green at the end. Nothing else.

Effective task list after reduction:

1. **Task 0** — Branch + baseline tests *(unchanged)*
2. **Task 1** — Rename `color/` → `colors/` and update every internal import in src, tests, scripts, docs *(unchanged)*
3. **Task 3** — `Color.parse()` classmethod *(unchanged)*
4. **Task 4** — Module-level `color()` *(unchanged)*
5. **Task 5** — Top-level `dm.color` export *(unchanged)*
6. **Task 6′** — **Remove `dm.named`**: delete the function from `colors/_color.py`, drop from every `__all__`/import block, delete the `TestNamed` test class, sweep all `dm.named(` → `dm.color(` in `docs/examples_source/`, `docs/color_system/`, and any `asset/prompt/05-templates/` hits.
7. **Task 10′** — Update `docs/migration.md`: short note that `dm.named` was removed and `color` submodule was renamed to `colors`. No shim mention.
8. **Task 11′** — Final verification + PR *(unchanged in spirit, condensed)*.

Sections "Task 2", "Task 6", "Task 7", "Task 8", "Task 9" below are obsolete under the reduced scope; they remain in the document only as a historical record. Follow the reduced list above.

---

## Source-of-Truth References

(Cited directly from a recon sweep — DO NOT trust these line numbers blindly when editing; re-grep before each edit, since other tasks may shift them.)

- Module entry: `src/dartwork_mpl/color/__init__.py` (38 lines)
- `Color` class + module-level helpers: `src/dartwork_mpl/color/_color.py` (639 lines)
  - `from_rgb`: lines 179–220 (auto-detects 0–1 vs 0–255)
  - `from_hex`: lines 223–241 (delegates to `from_rgb`)
  - `from_name`: lines 244–277
  - `from_oklab`: lines 140–154
  - `from_oklch`: lines 157–176 (h in degrees)
  - `cspace`: lines 397–537
  - module helpers: `oklab` (545–559), `oklch` (562–578), `rgb` (581–595), `hex` (598–612), `named` (615–639)
- Top-level re-export: `src/dartwork_mpl/__init__.py:31-41` (block `from .color import (...)`)
- Length parser pattern: `src/dartwork_mpl/units.py:364-370`
- Internal direct imports of `.color`:
  - `src/dartwork_mpl/util.py` (`from .color import Color`)
  - `src/dartwork_mpl/explore.py` (`from .color._loader import ensure_loaded`)
- External direct imports of `dartwork_mpl.color.*` (must keep working via shim):
  - `tests/test_loader.py`
  - `tests/test_color_view.py`
  - `tests/test_color_api.py`
  - `tests/test_color_conversion.py`
  - `docs/color_system/generate_assets.py`
  - `scripts/generate_cmaps.py`
- Lint catalog: `src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml`
- Migration engine: `src/dartwork_mpl/lint.py` (`_MIGRATE_SAFE_REWRITES` ~lines 248–251, `_MIGRATE_HINTS` ~253–291, `migrate_legacy_code` ~294–354)
- `dm.named(` call sites (~25, all in `docs/`):
  - `docs/examples_source/**/*.py` (primary edit target)
  - `docs/examples_gallery/**/*.py` (verify whether generated or sourced)
  - `docs/color_system/generate_assets.py`

---

## File Structure

**New files (created by this plan):**

| Path | Responsibility |
|---|---|
| `src/dartwork_mpl/colors/__init__.py` | Public color package entry (was `color/__init__.py`) |
| `src/dartwork_mpl/colors/_color.py` | `Color` class, `parse`, module helpers (was `color/_color.py`) |
| `src/dartwork_mpl/colors/_conversion.py` | Color-space conversions (was `color/_conversion.py`) |
| `src/dartwork_mpl/colors/_loader.py` | Palette JSON loader + matplotlib registration (was `color/_loader.py`) |
| `src/dartwork_mpl/colors/_views.py` | View classes (was `color/_views.py`) |
| `src/dartwork_mpl/colors/_typing.py` | `DartworkColor` / `DartworkColormap` literals (was `color/_typing.py`) |
| `src/dartwork_mpl/color/__init__.py` | **Backward-compat shim** — re-exports `colors`, emits `DeprecationWarning` |
| `src/dartwork_mpl/color/_color.py` | Shim — re-exports `colors._color` |
| `src/dartwork_mpl/color/_conversion.py` | Shim — re-exports `colors._conversion` |
| `src/dartwork_mpl/color/_loader.py` | Shim — re-exports `colors._loader` |
| `src/dartwork_mpl/color/_views.py` | Shim — re-exports `colors._views` |
| `src/dartwork_mpl/color/_typing.py` | Shim — re-exports `colors._typing` |
| `tests/test_color_parser.py` | Tests for `Color.parse` and module-level `color()` |
| `tests/test_color_module_shim.py` | Tests for `color/` shim (deprecation + re-export) |

**Modified files:**

| Path | Change |
|---|---|
| `src/dartwork_mpl/__init__.py` | Import block from `.colors` (was `.color`); export `color`; update `__all__` |
| `src/dartwork_mpl/util.py` | `from .color import Color` → `from .colors import Color` |
| `src/dartwork_mpl/explore.py` | `from .color._loader import ensure_loaded` → `from .colors._loader import ensure_loaded` |
| `src/dartwork_mpl/lint.py` | Append `("dm.named(", "dm.color(")` to `_MIGRATE_SAFE_REWRITES` |
| `src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml` | Add `named-deprecated` rule |
| `tests/test_color_api.py` | Add `TestNamedDeprecation` |
| `tests/test_loader.py`, `tests/test_color_view.py`, `tests/test_color_api.py`, `tests/test_color_conversion.py` | Update imports `dartwork_mpl.color` → `dartwork_mpl.colors` to avoid leaking warnings into other tests |
| `docs/color_system/generate_assets.py` | Update imports + sweep `dm.named(` → `dm.color(` |
| `scripts/generate_cmaps.py` | Update imports `dartwork_mpl.color._*` → `dartwork_mpl.colors._*` |
| `docs/examples_source/**/*.py` | Sweep `dm.named(` → `dm.color(` |
| `docs/migration.md` | Add section on `dm.named` deprecation and `color → colors` rename |

---

## Tasks

### Task 0: Set up feature branch

**Files:** none

- [ ] **Step 1: Confirm clean working tree**

Run: `git status`
Expected: `nothing to commit, working tree clean` (we are on `main`).

- [ ] **Step 2: Create and switch to feature branch**

Run: `git checkout -b feat/color-parser-api`

- [ ] **Step 3: Confirm tests currently pass on main as a baseline**

Run: `pytest tests/ -x -q`
Expected: all tests pass. Capture the count for comparison after the rename. If any tests are already broken on `main`, STOP and surface to the user — do not proceed.

---

### Task 1: Move `color/` → `colors/` and update all internal + test imports atomically

This task is one atomic commit. After this commit the package must work end-to-end as before, just under the new submodule name. The legacy `color/` shim is added in Task 2.

**Files:**
- Move (git): `src/dartwork_mpl/color/` → `src/dartwork_mpl/colors/`
- Modify: `src/dartwork_mpl/__init__.py`
- Modify: `src/dartwork_mpl/util.py`
- Modify: `src/dartwork_mpl/explore.py`
- Modify: `tests/test_loader.py`
- Modify: `tests/test_color_view.py`
- Modify: `tests/test_color_api.py`
- Modify: `tests/test_color_conversion.py`
- Modify: `docs/color_system/generate_assets.py`
- Modify: `scripts/generate_cmaps.py`

- [ ] **Step 1: Move the directory with `git mv`**

Run: `git mv src/dartwork_mpl/color src/dartwork_mpl/colors`

Verify:
```bash
ls src/dartwork_mpl/colors
# Expected: __init__.py  _color.py  _conversion.py  _loader.py  _typing.py  _views.py
ls src/dartwork_mpl/color 2>/dev/null
# Expected: directory does not exist (will be re-created in Task 2)
```

- [ ] **Step 2: Update top-level package re-export**

In `src/dartwork_mpl/__init__.py`, find the block:

```python
from .color import (
    Color,
    DartworkColor,
    DartworkColormap,
    cspace,
    hex,
    named,
    oklab,
    oklch,
    rgb,
)
```

Replace with:

```python
from .colors import (
    Color,
    DartworkColor,
    DartworkColormap,
    cspace,
    hex,
    named,
    oklab,
    oklch,
    rgb,
)
```

(Do NOT add `color` here yet — that lands in Task 5 with the new function.)

- [ ] **Step 3: Update `util.py` internal import**

In `src/dartwork_mpl/util.py`, replace:
```python
from .color import Color
```
with:
```python
from .colors import Color
```

- [ ] **Step 4: Update `explore.py` internal import**

In `src/dartwork_mpl/explore.py`, replace:
```python
from .color._loader import ensure_loaded
```
with:
```python
from .colors._loader import ensure_loaded
```

- [ ] **Step 5: Update tests' direct imports**

For each of these files, replace every occurrence of `dartwork_mpl.color` with `dartwork_mpl.colors` (whole substring, including submodule paths like `dartwork_mpl.color._loader`):

- `tests/test_loader.py`
- `tests/test_color_view.py`
- `tests/test_color_api.py`
- `tests/test_color_conversion.py`

Use Edit with `replace_all: true` per file, or run:
```bash
grep -rln "dartwork_mpl\.color\b\|dartwork_mpl\.color\." tests/
```
and edit each file shown.

- [ ] **Step 6: Update scripts and docs generators**

- `docs/color_system/generate_assets.py`: `from dartwork_mpl.color._loader import ensure_loaded` → `from dartwork_mpl.colors._loader import ensure_loaded`
- `scripts/generate_cmaps.py`: `from dartwork_mpl.color._loader import _load_colors` → `from dartwork_mpl.colors._loader import _load_colors`; `from dartwork_mpl.color._color import cspace` → `from dartwork_mpl.colors._color import cspace`

- [ ] **Step 7: Verify no remaining `dartwork_mpl.color` import paths inside source / tests / scripts**

Run:
```bash
grep -rn "dartwork_mpl\.color\b\|dartwork_mpl\.color\." src/ tests/ scripts/ docs/color_system/
```
Expected: no matches. (Matches under `docs/_build/` are build artifacts — ignore them. Matches in `docs/superpowers/plans/` are this plan itself — ignore.)

If any remain, edit them to `dartwork_mpl.colors`.

- [ ] **Step 8: Run the full test suite**

Run: `pytest tests/ -x -q`
Expected: same pass count as the Task 0 baseline.

If anything fails, fix the import or stub before continuing — do NOT proceed to Task 2 with a broken tree.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "refactor(color): rename color submodule to colors

Move src/dartwork_mpl/color/ to src/dartwork_mpl/colors/ and update
all internal and test imports. Backward-compat shim follows in a
later commit. Refs #164."
```

---

### Task 2: Add backward-compat shim package `dartwork_mpl.color`

After Task 1 commits cleanly, the old `color` import path is gone. This task brings it back as a deprecation shim so external users (and any forgotten import paths) keep working with a single warning.

**Files:**
- Create: `src/dartwork_mpl/color/__init__.py`
- Create: `src/dartwork_mpl/color/_color.py`
- Create: `src/dartwork_mpl/color/_conversion.py`
- Create: `src/dartwork_mpl/color/_loader.py`
- Create: `src/dartwork_mpl/color/_views.py`
- Create: `src/dartwork_mpl/color/_typing.py`
- Create: `tests/test_color_module_shim.py`

- [ ] **Step 1: Write failing shim tests**

Create `tests/test_color_module_shim.py`:

```python
"""Backward-compat shim tests for the deprecated `dartwork_mpl.color` module.

These tests force a fresh import of `dartwork_mpl.color` (popping it from
``sys.modules`` first) so the one-shot DeprecationWarning is observable.
"""
from __future__ import annotations

import importlib
import sys
import warnings


def _fresh_import(name: str):
    """Re-import a module after evicting it (and submodules) from sys.modules."""
    for mod_name in list(sys.modules.keys()):
        if mod_name == name or mod_name.startswith(name + "."):
            del sys.modules[mod_name]
    return importlib.import_module(name)


def test_shim_emits_deprecation_warning():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _fresh_import("dartwork_mpl.color")
        msgs = [
            str(w.message)
            for w in caught
            if issubclass(w.category, DeprecationWarning)
        ]
    assert any("dartwork_mpl.color" in m for m in msgs), (
        f"Expected DeprecationWarning mentioning 'dartwork_mpl.color', got: {msgs}"
    )


def test_shim_top_level_reexports():
    mod = _fresh_import("dartwork_mpl.color")
    assert hasattr(mod, "Color")
    assert callable(mod.named)
    assert callable(mod.hex)
    assert callable(mod.rgb)
    assert callable(mod.oklab)
    assert callable(mod.oklch)
    assert callable(mod.cspace)


def test_shim_loader_submodule_reexport():
    loader = _fresh_import("dartwork_mpl.color._loader")
    assert callable(loader.ensure_loaded)
    # Private name used by tests/test_loader.py historically
    assert callable(loader._load_json_palette)


def test_shim_color_submodule_reexport():
    sub = _fresh_import("dartwork_mpl.color._color")
    assert callable(sub.cspace)
    assert hasattr(sub, "Color")


def test_shim_conversion_submodule_reexport():
    sub = _fresh_import("dartwork_mpl.color._conversion")
    # _conversion exposes private helpers; just check it imports cleanly
    assert sub is not None


def test_shim_proxies_same_class_object():
    """`Color` from shim must be the same class as `Color` from `colors`."""
    from dartwork_mpl.colors import Color as _ColorNew  # canonical
    shim = _fresh_import("dartwork_mpl.color")
    assert shim.Color is _ColorNew
```

- [ ] **Step 2: Run failing tests**

Run: `pytest tests/test_color_module_shim.py -v`
Expected: all tests fail with `ModuleNotFoundError: No module named 'dartwork_mpl.color'` (the directory was deleted in Task 1).

- [ ] **Step 3: Create the shim package**

Create `src/dartwork_mpl/color/__init__.py`:

```python
"""Deprecated import path. Use ``dartwork_mpl.colors`` instead.

This module is a thin re-export shim retained for backward compatibility
with code that imports ``dartwork_mpl.color`` (or its submodules) directly.
A single :class:`DeprecationWarning` is emitted at import time. The shim
will be removed in a future major release.
"""
from __future__ import annotations

import warnings as _warnings

_warnings.warn(
    "dartwork_mpl.color is deprecated; import from dartwork_mpl.colors instead.",
    category=DeprecationWarning,
    stacklevel=2,
)

from ..colors import (  # noqa: F401  (re-export)
    Color,
    DartworkColor,
    DartworkColormap,
    OklabView,
    OklabViewIterator,
    OklchView,
    OklchViewIterator,
    RgbView,
    RgbViewIterator,
    cspace,
    hex,
    named,
    oklab,
    oklch,
    rgb,
)

__all__ = [
    "Color",
    "DartworkColor",
    "DartworkColormap",
    "OklabView",
    "OklabViewIterator",
    "OklchView",
    "OklchViewIterator",
    "RgbView",
    "RgbViewIterator",
    "cspace",
    "hex",
    "named",
    "oklab",
    "oklch",
    "rgb",
]
```

Create `src/dartwork_mpl/color/_color.py`:

```python
"""Deprecated re-export of :mod:`dartwork_mpl.colors._color`."""
from __future__ import annotations

from ..colors._color import *  # noqa: F401, F403
from ..colors._color import (  # noqa: F401  (explicit private re-exports for legacy callers)
    Color,
    cspace,
    hex,
    named,
    oklab,
    oklch,
    rgb,
)
```

Create `src/dartwork_mpl/color/_conversion.py`:

```python
"""Deprecated re-export of :mod:`dartwork_mpl.colors._conversion`."""
from __future__ import annotations

from ..colors._conversion import *  # noqa: F401, F403
```

Create `src/dartwork_mpl/color/_loader.py`:

```python
"""Deprecated re-export of :mod:`dartwork_mpl.colors._loader`."""
from __future__ import annotations

from ..colors._loader import *  # noqa: F401, F403
from ..colors._loader import (  # noqa: F401  (private names used by historical callers)
    _load_colors,
    _load_json_palette,
    ensure_loaded,
)
```

Create `src/dartwork_mpl/color/_views.py`:

```python
"""Deprecated re-export of :mod:`dartwork_mpl.colors._views`."""
from __future__ import annotations

from ..colors._views import *  # noqa: F401, F403
```

Create `src/dartwork_mpl/color/_typing.py`:

```python
"""Deprecated re-export of :mod:`dartwork_mpl.colors._typing`."""
from __future__ import annotations

from ..colors._typing import *  # noqa: F401, F403
from ..colors._typing import (  # noqa: F401
    DartworkColor,
    DartworkColormap,
)
```

- [ ] **Step 4: Run shim tests**

Run: `pytest tests/test_color_module_shim.py -v`
Expected: all 6 tests pass.

If `_load_json_palette` or `_load_colors` does not actually exist in `colors._loader`, edit `color/_loader.py` to import only the names that exist (cross-check by `grep -n '^def \|^_load' src/dartwork_mpl/colors/_loader.py`). Update the test accordingly so it asserts only available names.

- [ ] **Step 5: Run the whole suite to verify the shim does not introduce warnings into unrelated tests**

Run: `pytest tests/ -W error::DeprecationWarning -q`

Expected: any test that imports `dartwork_mpl.color` directly is the only place a `DeprecationWarning` could fire. Internal code already uses `dartwork_mpl.colors` (Task 1), so no internal warning should leak. If an unrelated test trips the warning-as-error, find the offending import and either (a) update it to `dartwork_mpl.colors`, or (b) add a `pytestmark` filter narrowly to that test file with a comment justifying it.

- [ ] **Step 6: Commit**

```bash
git add src/dartwork_mpl/color tests/test_color_module_shim.py
git commit -m "feat(colors): add backward-compat shim for legacy color/ module

dartwork_mpl.color and its submodules now re-export from
dartwork_mpl.colors and emit a one-shot DeprecationWarning on
import. Refs #164."
```

---

### Task 3: Add `Color.parse()` classmethod (TDD, multi-form)

The classmethod is the core dispatcher; the module-level `color()` wrapper in Task 4 is a thin shell.

**Files:**
- Modify: `src/dartwork_mpl/colors/_color.py`
- Create: `tests/test_color_parser.py`

- [ ] **Step 1: Write the failing test file with all input forms**

Create `tests/test_color_parser.py`:

```python
"""Tests for ``Color.parse`` and the module-level ``dm.color`` parser."""
from __future__ import annotations

import math

import pytest

from dartwork_mpl.colors import Color


# --- Pass-through ----------------------------------------------------------- #


def test_parse_rejects_color_instance():
    """Color.parse handles strings only; pass-through belongs to dm.color()."""
    c = Color.from_hex("#ff0000")
    with pytest.raises(TypeError):
        Color.parse(c)  # type: ignore[arg-type]


# --- Hex ------------------------------------------------------------------- #


def test_parse_hex_long():
    assert Color.parse("#ff0000").to_hex() == "#ff0000"


def test_parse_hex_short():
    assert Color.parse("#f00").to_hex() == "#ff0000"


def test_parse_hex_with_surrounding_whitespace():
    assert Color.parse("  #00ff00  ").to_hex() == "#00ff00"


# --- Functional rgb(...) --------------------------------------------------- #


def test_parse_rgb_unit_floats():
    expected = Color.from_rgb(1.0, 0.0, 0.0)
    assert Color.parse("rgb(1.0, 0.0, 0.0)").to_hex() == expected.to_hex()


def test_parse_rgb_byte_ints():
    """rgb(255, 0, 0) — Color.from_rgb auto-detects 0-255 range."""
    expected = Color.from_rgb(255, 0, 0)
    assert Color.parse("rgb(255, 0, 0)").to_hex() == expected.to_hex()


def test_parse_rgb_internal_whitespace():
    assert Color.parse("rgb( 1.0 , 0 , 0 )").to_hex() == "#ff0000"


def test_parse_rgb_case_insensitive():
    assert Color.parse("RGB(1, 0, 0)").to_hex() == "#ff0000"


def test_parse_rgb_wrong_argc():
    with pytest.raises(ValueError, match="rgb"):
        Color.parse("rgb(1, 0)")


# --- Functional oklch(...) ------------------------------------------------- #


def test_parse_oklch_matches_factory():
    expected = Color.from_oklch(0.5, 0.1, 30.0)
    got = Color.parse("oklch(0.5, 0.1, 30)")
    assert math.isclose(got.oklab.L, expected.oklab.L, abs_tol=1e-9)
    assert math.isclose(got.oklab.a, expected.oklab.a, abs_tol=1e-9)
    assert math.isclose(got.oklab.b, expected.oklab.b, abs_tol=1e-9)


def test_parse_oklch_case_insensitive():
    expected = Color.from_oklch(0.7, 0.15, 120.0)
    got = Color.parse("OkLch(0.7, 0.15, 120)")
    assert math.isclose(got.oklab.L, expected.oklab.L, abs_tol=1e-9)


# --- Functional oklab(...) ------------------------------------------------- #


def test_parse_oklab_matches_factory():
    expected = Color.from_oklab(0.5, 0.05, 0.05)
    got = Color.parse("oklab(0.5, 0.05, 0.05)")
    assert math.isclose(got.oklab.L, expected.oklab.L, abs_tol=1e-9)
    assert math.isclose(got.oklab.a, expected.oklab.a, abs_tol=1e-9)
    assert math.isclose(got.oklab.b, expected.oklab.b, abs_tol=1e-9)


# --- Palette name fallback ------------------------------------------------- #


def test_parse_palette_name_oc():
    expected = Color.from_name("oc.red5")
    assert Color.parse("oc.red5").to_hex() == expected.to_hex()


def test_parse_palette_name_tw():
    expected = Color.from_name("tw.blue500")
    assert Color.parse("tw.blue500").to_hex() == expected.to_hex()


def test_parse_palette_name_matplotlib_basic():
    expected = Color.from_name("red")
    assert Color.parse("red").to_hex() == expected.to_hex()


# --- Errors ---------------------------------------------------------------- #


def test_parse_rejects_non_string():
    with pytest.raises(TypeError):
        Color.parse(0xff0000)  # type: ignore[arg-type]


def test_parse_unknown_palette_name_bubbles():
    with pytest.raises((ValueError, KeyError)):
        Color.parse("definitely-not-a-color-name-xyz")


def test_parse_unknown_function_bubbles():
    """Unknown leading function name falls through to from_name and fails."""
    with pytest.raises((ValueError, KeyError)):
        Color.parse("hsv(0, 1, 1)")
```

- [ ] **Step 2: Run failing tests**

Run: `pytest tests/test_color_parser.py -v`
Expected: every test fails with `AttributeError: type object 'Color' has no attribute 'parse'`.

- [ ] **Step 3: Implement `Color.parse()`**

In `src/dartwork_mpl/colors/_color.py`, locate the `Color` class. Add the following classmethod after `from_name` (the last existing factory). Also add `import re` to the module-level imports if it is not already imported.

```python
    _FUNCTIONAL_RE = re.compile(
        r"^(?P<func>rgb|oklch|oklab)\s*\(\s*(?P<args>.+?)\s*\)$",
        re.IGNORECASE,
    )

    @classmethod
    def parse(cls, value: str) -> "Color":
        """Parse a string in any supported form into a :class:`Color`.

        Supported forms:

        * Hex string — ``"#rgb"`` or ``"#rrggbb"`` → :meth:`from_hex`.
        * Functional — ``"rgb(r, g, b)"`` (auto 0-1/0-255 detection),
          ``"oklch(L, C, h)"`` (h in degrees), ``"oklab(L, a, b)"``.
          The function name is case-insensitive; arguments are
          comma-separated and tolerant of internal whitespace.
        * Palette name — anything else falls through to :meth:`from_name`
          (matplotlib named colors, ``oc.``, ``tw.``, ``md.``, …).

        Parameters
        ----------
        value : str
            The color string to parse. Surrounding whitespace is stripped.

        Returns
        -------
        Color

        Raises
        ------
        TypeError
            If ``value`` is not a :class:`str`.
        ValueError
            If a functional form has the wrong number of arguments, or
            the underlying factory rejects the value.
        """
        if not isinstance(value, str):
            raise TypeError(
                f"Color.parse expects a str, got {type(value).__name__}"
            )
        text = value.strip()
        if text.startswith("#"):
            return cls.from_hex(text)
        match = cls._FUNCTIONAL_RE.match(text)
        if match is not None:
            func = match.group("func").lower()
            raw_args = match.group("args")
            try:
                nums = [float(part.strip()) for part in raw_args.split(",")]
            except ValueError as exc:
                raise ValueError(
                    f"{func}(...) arguments must be numeric: {raw_args!r}"
                ) from exc
            if len(nums) != 3:
                raise ValueError(
                    f"{func}(...) expects 3 arguments, got {len(nums)}: "
                    f"{raw_args!r}"
                )
            if func == "rgb":
                return cls.from_rgb(*nums)
            if func == "oklch":
                return cls.from_oklch(*nums)
            if func == "oklab":
                return cls.from_oklab(*nums)
            # Defensive — _FUNCTIONAL_RE already constrains func.
            raise ValueError(f"unsupported color function: {func!r}")
        return cls.from_name(text)
```

If `import re` is not already at the top of `_color.py`, add it (check first with `grep -n "^import re\|^import " src/dartwork_mpl/colors/_color.py`).

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_color_parser.py -v`
Expected: all tests pass.

If `from_rgb` rejects `(255, 0, 0)` because the auto-detect threshold differs from what we assumed, adjust the test (`test_parse_rgb_byte_ints`) to use values the existing `from_rgb` accepts. Do NOT change `from_rgb` semantics in this task — keep scope tight.

- [ ] **Step 5: Commit**

```bash
git add src/dartwork_mpl/colors/_color.py tests/test_color_parser.py
git commit -m "feat(colors): add Color.parse() multi-form string parser

Routes by leading '#', functional rgb/oklch/oklab(...), or palette
name fallback. Mirrors the dm.length/Length(value) string-parser
pattern. Refs #164."
```

---

### Task 4: Add module-level `color()` function

Mirrors `length(value: str | Length) -> Length`: handles `Color` pass-through, delegates strings to `Color.parse`.

**Files:**
- Modify: `src/dartwork_mpl/colors/_color.py`
- Modify: `src/dartwork_mpl/colors/__init__.py`
- Modify: `tests/test_color_parser.py`

- [ ] **Step 1: Append failing tests for `color()`**

Append to `tests/test_color_parser.py`:

```python
# --------------------------------------------------------------------------- #
# Module-level color() — thin wrapper over Color.parse                         #
# --------------------------------------------------------------------------- #

from dartwork_mpl.colors import color  # noqa: E402  (intentional late import)


def test_color_passthrough_returns_same_object():
    c = Color.from_hex("#ff0000")
    assert color(c) is c


def test_color_string_delegates_to_parse():
    expected = Color.parse("oc.red5")
    assert color("oc.red5").to_hex() == expected.to_hex()


def test_color_hex_via_module_function():
    assert color("#00ff00").to_hex() == "#00ff00"


def test_color_rejects_non_str_non_color():
    with pytest.raises(TypeError):
        color(123)  # type: ignore[arg-type]


def test_color_rejects_none():
    with pytest.raises(TypeError):
        color(None)  # type: ignore[arg-type]
```

- [ ] **Step 2: Run failing tests**

Run: `pytest tests/test_color_parser.py -v -k "color and not parse"`
Expected: import fails with `ImportError: cannot import name 'color' from 'dartwork_mpl.colors'`.

- [ ] **Step 3: Implement `color()` and export it**

In `src/dartwork_mpl/colors/_color.py`, add a module-level function near the other helpers (after `named`):

```python
def color(value: "Color | str") -> "Color":
    """Parse a string or pass through a :class:`Color` instance.

    String-parser counterpart to :func:`hex`, :func:`rgb`,
    :func:`oklch`, :func:`oklab`, and palette-name lookup. Mirrors
    :func:`dartwork_mpl.length` for unit strings.

    Examples
    --------
    >>> color("#ff0000")           # hex
    >>> color("rgb(1, 0, 0)")      # functional
    >>> color("oklch(0.7, 0.15, 30)")
    >>> color("oc.red5")           # palette name

    Parameters
    ----------
    value : Color or str
        A :class:`Color` instance is returned unchanged. A string is
        dispatched through :meth:`Color.parse`.

    Returns
    -------
    Color
    """
    if isinstance(value, Color):
        return value
    if isinstance(value, str):
        return Color.parse(value)
    raise TypeError(
        f"color() expects str or Color, got {type(value).__name__}"
    )
```

In `src/dartwork_mpl/colors/__init__.py`, find the line:
```python
from ._color import Color, cspace, hex, named, oklab, oklch, rgb
```
Replace with:
```python
from ._color import Color, color, cspace, hex, named, oklab, oklch, rgb
```

Also add `"color"` to the `__all__` list (alphabetically between `Color` and `cspace`):
```python
__all__ = [
    "Color",
    "DartworkColor",
    "DartworkColormap",
    "OklabView",
    "OklabViewIterator",
    "OklchView",
    "OklchViewIterator",
    "RgbView",
    "RgbViewIterator",
    "color",
    "cspace",
    "hex",
    "named",
    "oklab",
    "oklch",
    "rgb",
]
```

Update the shim `src/dartwork_mpl/color/__init__.py` accordingly: add `color` to its re-export block AND its `__all__` list. Do the same in `src/dartwork_mpl/color/_color.py` (add `color` to the explicit re-export tuple).

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_color_parser.py -v`
Expected: all tests pass (both `Color.parse` and `color()` suites).

- [ ] **Step 5: Commit**

```bash
git add src/dartwork_mpl/colors src/dartwork_mpl/color tests/test_color_parser.py
git commit -m "feat(colors): add module-level color() string parser

Mirrors dm.length: pass-through for Color, dispatch to Color.parse
for strings. Refs #164."
```

---

### Task 5: Re-export `color` from the top-level package

**Files:**
- Modify: `src/dartwork_mpl/__init__.py`

- [ ] **Step 1: Add a regression test that `dm.color` resolves**

Append to `tests/test_color_parser.py`:

```python
def test_color_is_exported_at_top_level():
    import dartwork_mpl as dm

    assert dm.color is color
    assert dm.color("#ff0000").to_hex() == "#ff0000"
```

- [ ] **Step 2: Run failing test**

Run: `pytest tests/test_color_parser.py::test_color_is_exported_at_top_level -v`
Expected: `AttributeError: module 'dartwork_mpl' has no attribute 'color'`.

- [ ] **Step 3: Update top-level imports**

In `src/dartwork_mpl/__init__.py`, locate the existing block:

```python
from .colors import (
    Color,
    DartworkColor,
    DartworkColormap,
    cspace,
    hex,
    named,
    oklab,
    oklch,
    rgb,
)
```

Replace with:

```python
from .colors import (
    Color,
    DartworkColor,
    DartworkColormap,
    color,
    cspace,
    hex,
    named,
    oklab,
    oklch,
    rgb,
)
```

Then locate the package-level `__all__` list and add `"color"` (insert after `"Color"`).

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_color_parser.py -v`
Expected: all pass, including the new `test_color_is_exported_at_top_level`.

- [ ] **Step 5: Commit**

```bash
git add src/dartwork_mpl/__init__.py tests/test_color_parser.py
git commit -m "feat(colors): export dm.color at top level

Refs #164."
```

---

### Task 6: Deprecate `dm.named` (warn, but keep working)

`named()` already emits a deprecation warning specifically for the legacy `dm.` palette prefix. We add an additional warning that points users to `dm.color()`, and the function continues to work.

**Files:**
- Modify: `src/dartwork_mpl/colors/_color.py`
- Modify: `tests/test_color_api.py`

- [ ] **Step 1: Add failing deprecation test**

Append to `tests/test_color_api.py` (at the end, after `TestCspace`):

```python
class TestNamedDeprecation:
    """``dm.named`` keeps working but emits DeprecationWarning."""

    def test_named_emits_deprecation_pointing_to_color(self):
        import warnings

        from dartwork_mpl.colors import named

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            named("oc.red5")
            msgs = [
                str(w.message)
                for w in caught
                if issubclass(w.category, DeprecationWarning)
            ]
        assert any("dm.color" in m for m in msgs), (
            f"Expected DeprecationWarning mentioning dm.color, got: {msgs}"
        )

    def test_named_still_returns_correct_color(self):
        import warnings

        from dartwork_mpl.colors import Color, named

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            got = named("oc.red5")
            expected = Color.from_name("oc.red5")
        assert got.to_hex() == expected.to_hex()
```

- [ ] **Step 2: Run failing tests**

Run: `pytest tests/test_color_api.py::TestNamedDeprecation -v`
Expected: `test_named_emits_deprecation_pointing_to_color` fails (no warning mentions `dm.color`).

- [ ] **Step 3: Add the deprecation warning**

In `src/dartwork_mpl/colors/_color.py`, locate the existing `named` function (around line 615 originally; re-grep to find current line number after Task 3 edits):

```bash
grep -n "^def named\b" src/dartwork_mpl/colors/_color.py
```

At the very top of the function body — BEFORE the existing `if color_name.startswith("dm."):` block — insert:

```python
    warnings.warn(
        "dm.named() is deprecated; use dm.color() instead. "
        "dm.color() also accepts hex (#rrggbb), rgb(...), oklch(...), "
        "and oklab(...) functional strings.",
        category=DeprecationWarning,
        stacklevel=2,
    )
```

The `import warnings` at the top of the file already exists (the legacy `dm.` prefix block uses it); confirm with:
```bash
grep -n "^import warnings\|^    import warnings" src/dartwork_mpl/colors/_color.py
```
If `warnings` is currently imported lazily inside `named()`, hoist it to the module top — the new warning needs it before the `if` block.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_color_api.py -v`
Expected: all `TestNamed`, `TestNamedDeprecation`, and pre-existing tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/dartwork_mpl/colors/_color.py tests/test_color_api.py
git commit -m "feat(colors): emit DeprecationWarning from dm.named

dm.named() now points users to dm.color() while continuing to work.
Refs #164."
```

---

### Task 7: Add `named-deprecated` rule to anti-pattern catalog

**Files:**
- Modify: `src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml`

- [ ] **Step 1: Add failing lint-rule test**

Append to a new test file `tests/test_lint_named_rule.py`:

```python
"""Lint rule coverage for dm.named() → dm.color() guidance."""
from __future__ import annotations

from dartwork_mpl.lint import lint as lint_code


def test_named_call_is_flagged():
    code = 'import dartwork_mpl as dm\nc = dm.named("oc.red5")\n'
    diagnostics = lint_code(code)
    rule_ids = {d.rule_id for d in diagnostics}
    assert "named-deprecated" in rule_ids, (
        f"Expected named-deprecated diagnostic, got rule ids: {rule_ids}"
    )


def test_color_call_is_not_flagged():
    code = 'import dartwork_mpl as dm\nc = dm.color("oc.red5")\n'
    diagnostics = lint_code(code)
    rule_ids = {d.rule_id for d in diagnostics}
    assert "named-deprecated" not in rule_ids
```

(The exact attribute name on the diagnostic — `rule_id` vs `id` — depends on the existing `Rule` dataclass in `src/dartwork_mpl/lint.py`. Before running, grep for it: `grep -n "class Rule\|class Diagnostic\|rule_id\|@dataclass" src/dartwork_mpl/lint.py | head` and adjust the assertion accordingly. Use whatever attribute the other tests use — see `tests/test_lint*.py` if present, e.g. `grep -rn "from dartwork_mpl.lint" tests/`.)

- [ ] **Step 2: Run failing test**

Run: `pytest tests/test_lint_named_rule.py -v`
Expected: `test_named_call_is_flagged` fails because no rule with id `named-deprecated` exists yet.

- [ ] **Step 3: Add the YAML rule**

In `src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml`, append a new entry under `rules:` (match the indentation of existing rules — see e.g. the `tight-layout` rule for the exact YAML shape):

```yaml
  - id: named-deprecated
    severity: warning
    detector:
      kind: regex
      pattern: '\bdm\.named\s*\('
    message: dm.named() is deprecated; use dm.color() instead.
    why: |
      dm.color() is the canonical string-parser entry point — it accepts
      palette names ("oc.red5"), hex ("#ff0000"), and functional strings
      ("rgb(...)", "oklch(...)", "oklab(...)"). dm.named() is retained
      only for backward compatibility and emits a DeprecationWarning at
      runtime.
    fix_suggestion: |
      Replace dm.named("oc.red5") with dm.color("oc.red5"). The new
      dm.color() handles every input form previously split across
      dm.named, dm.hex, etc. — though dm.hex/dm.rgb/dm.oklch/dm.oklab
      remain available as specialized constructors.
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_lint_named_rule.py tests/ -k lint -v`
Expected: all lint-related tests pass, including the two new ones.

- [ ] **Step 5: Commit**

```bash
git add src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml tests/test_lint_named_rule.py
git commit -m "feat(lint): flag dm.named() with named-deprecated rule

Refs #164."
```

---

### Task 8: Add `dm.named(` → `dm.color(` to migration safe-rewrites

**Files:**
- Modify: `src/dartwork_mpl/lint.py`

- [ ] **Step 1: Add failing migration test**

Append to a test file (`tests/test_migrate_named.py`):

```python
"""migrate_legacy_code() rewrites dm.named( to dm.color(."""
from __future__ import annotations

from dartwork_mpl.lint import migrate_legacy_code


def test_migrate_named_call_to_color():
    src = 'import dartwork_mpl as dm\nc = dm.named("oc.red5")\n'
    out = migrate_legacy_code(src)
    assert "dm.named(" not in out
    assert 'dm.color("oc.red5")' in out


def test_migrate_named_with_kwarg_or_var():
    src = "x = dm.named(name)\n"
    out = migrate_legacy_code(src)
    assert "dm.named(" not in out
    assert "dm.color(name)" in out
```

- [ ] **Step 2: Run failing test**

Run: `pytest tests/test_migrate_named.py -v`
Expected: both tests fail (`dm.named(` still present in output).

- [ ] **Step 3: Add the rewrite tuple**

In `src/dartwork_mpl/lint.py`, locate `_MIGRATE_SAFE_REWRITES`:

```bash
grep -n "_MIGRATE_SAFE_REWRITES\b" src/dartwork_mpl/lint.py
```

Append a tuple entry:

```python
_MIGRATE_SAFE_REWRITES = (
    ("dm.cm2in", "dm.cm"),
    ("plt.style.use", "dm.style.use"),
    ("dm.named(", "dm.color("),  # see issue #164
)
```

(Use the exact existing literal style — single vs double quotes, trailing-comma convention — match what is already there.)

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_migrate_named.py -v`
Expected: both tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/dartwork_mpl/lint.py tests/test_migrate_named.py
git commit -m "feat(lint): migrate dm.named( -> dm.color( automatically

Refs #164."
```

---

### Task 9: Sweep `dm.named(` → `dm.color(` across docs, examples, and asset corpus

This is a mechanical rewrite using the new `migrate_legacy_code` rule from Task 8. We commit the migrated files separately so the diff is auditable.

**Files (write-targets):**
- All `docs/examples_source/**/*.py` containing `dm.named(`
- `docs/color_system/generate_assets.py`
- `src/dartwork_mpl/asset/prompt/05-templates/**/*.py` (verify whether any template uses `dm.named(`; sweep if so)
- DO NOT touch `docs/_build/` — it is a build artifact
- DO NOT touch `docs/examples_gallery/` if it is auto-generated (see Step 1)

- [ ] **Step 1: Determine whether `docs/examples_gallery/` is generated or hand-edited**

Run:
```bash
git log --oneline -- docs/examples_gallery/ | head -5
git log --oneline -- docs/examples_source/ | head -5
ls docs/examples_gallery/ docs/examples_source/ 2>&1 | head
grep -n "examples_gallery\|examples_source\|sphinx_gallery" docs/conf.py 2>/dev/null
```

- If `docs/conf.py` references `sphinx_gallery` and lists `examples_source` as the source dir with `examples_gallery` as the generated target, treat `examples_gallery/` as build output — DO NOT edit it; it will regenerate.
- If both are tracked by git as hand-edited (commits modify both directly), sweep both.

Record the determination here in the commit message.

- [ ] **Step 2: List every file that needs editing**

Run:
```bash
grep -rln "\bdm\.named\s*(" docs/examples_source/ docs/color_system/ src/dartwork_mpl/asset/prompt/05-templates/ 2>/dev/null
```

Expected output: ~10–13 files.

- [ ] **Step 3: Do the sweep**

For each file in the list from Step 2, replace every `dm.named(` with `dm.color(` (use Edit with `replace_all: true` per file, or run them through `migrate_legacy_code` programmatically).

To run via the new migrator (preferred — exercises the lint code path):

```bash
python - <<'PY'
import pathlib
from dartwork_mpl.lint import migrate_legacy_code

paths = [
    # paste the list from Step 2 here
]
for p in paths:
    path = pathlib.Path(p)
    src = path.read_text()
    new = migrate_legacy_code(src)
    if new != src:
        path.write_text(new)
        print(f"rewrote {p}")
PY
```

- [ ] **Step 4: Verify no `dm.named(` remains in non-build, non-test paths**

Run:
```bash
grep -rn "\bdm\.named\s*(" docs/ src/ scripts/ 2>/dev/null | grep -v "docs/_build/" | grep -v "docs/superpowers/plans/"
```
Expected: no matches outside test files. (Tests legitimately call `dm.named` to verify the deprecation warning — those are fine.)

- [ ] **Step 5: Spot-check one rewritten example by running it**

Pick the smallest example file (e.g. `docs/examples_source/04_layout_and_annotations/plot_bivariate_kde_marginals.py`) and run:
```bash
python <picked-file>
```
Expected: it executes without error and without `DeprecationWarning` from `dm.named` (because it now uses `dm.color`).

If the example fails for an unrelated reason (e.g. requires a display, missing test data), at least confirm the import + the `dm.color(...)` call resolves by running:
```bash
python -c "import ast, sys; ast.parse(open('<picked-file>').read()); print('parse ok')"
```

- [ ] **Step 6: Commit**

```bash
git add docs/ src/dartwork_mpl/asset/prompt/
git commit -m "docs(colors): sweep dm.named( -> dm.color( across examples

Mechanical rewrite via migrate_legacy_code. Refs #164."
```

---

### Task 10: Update `docs/migration.md`

**Files:**
- Modify: `docs/migration.md`

- [ ] **Step 1: Read the current migration guide to find the right insertion point**

Run:
```bash
head -80 docs/migration.md
```

Identify where existing deprecations are documented (e.g. an `## Removed in 0.X` or `## Renamed APIs` section). If no comparable section exists, add a new one near the top labeled `## dm.named → dm.color (deprecated, kept)`.

- [ ] **Step 2: Add the migration entry**

Add a new section (adapt heading style to match the file):

```markdown
## `dm.named` → `dm.color` (deprecated, kept)

`dm.named` continues to work but now emits a `DeprecationWarning` and
will be removed in a future major release. The replacement is `dm.color`,
the new single string-parser entry point, mirroring `dm.length`.

| Old | New |
|---|---|
| `dm.named("oc.red5")` | `dm.color("oc.red5")` |
| `dm.named("red")` | `dm.color("red")` |

In addition to palette names, `dm.color` accepts:

- Hex strings: `dm.color("#ff0000")`, `dm.color("#f00")`
- Functional strings: `dm.color("rgb(1, 0, 0)")`,
  `dm.color("oklch(0.7, 0.15, 30)")`, `dm.color("oklab(0.5, 0.05, 0.05)")`
- Pass-through: `dm.color(some_color_instance)` returns the instance unchanged.

The specialized constructors `dm.hex`, `dm.rgb`, `dm.oklch`, `dm.oklab`
are unchanged — use them when you already have the components, just as
`dm.cm(13)` coexists with `dm.length("13cm")`.

The migration tool rewrites `dm.named(` → `dm.color(` automatically:

```python
from dartwork_mpl.lint import migrate_legacy_code
new_source = migrate_legacy_code(old_source)
```

## `dartwork_mpl.color` → `dartwork_mpl.colors` (module rename)

The submodule was renamed to free the `color` name for the new
`dm.color` function. The old import path keeps working through a
shim that emits a single `DeprecationWarning`:

```python
# Old
from dartwork_mpl.color import Color  # DeprecationWarning

# New
from dartwork_mpl.colors import Color
```

Most users never touch the submodule directly (`dm.Color`, `dm.color`,
etc. all continue to work via the top-level package). Update direct
imports at your leisure.
```

- [ ] **Step 3: Commit**

```bash
git add docs/migration.md
git commit -m "docs(migration): document dm.named -> dm.color and color/ -> colors/

Refs #164."
```

---

### Task 11: Final verification, CHANGELOG/CLAUDE sweep, and PR

- [ ] **Step 1: Run the entire test suite cleanly**

Run: `pytest tests/ -q`
Expected: all tests pass. Compare the count to the Task 0 baseline plus the new tests added in Tasks 2, 3, 4, 5, 6, 7, 8.

- [ ] **Step 2: Run with `DeprecationWarning` upgraded to error to surface unintended internal use**

Run: `pytest tests/ -W error::DeprecationWarning -q`
Expected: only the deprecation tests themselves fail (they assert the warning is raised, but with `error` they raise instead — they will need `pytest.warns(DeprecationWarning)` rather than `warnings.catch_warnings`). Adjust any tests that legitimately need the warning to use `pytest.warns(DeprecationWarning)` if they fail under this stricter mode.

If the suite passes under `-W error::DeprecationWarning`, no internal code path is leaking the legacy `dm.named` or `dartwork_mpl.color` import anywhere.

- [ ] **Step 3: Skim CLAUDE.md and `llms.txt` / `llms-full.txt` for stale `dm.named` mentions**

Run:
```bash
grep -n "dm\.named\|dartwork_mpl\.color\b" CLAUDE.md AGENTS.md llms.txt llms-full.txt 2>/dev/null
```

If matches are agent-facing prose (e.g. "use `dm.named` to look up palette colors"), update them to mention `dm.color` and note that `dm.named` is deprecated. If no matches, skip.

If `llms.txt` / `llms-full.txt` are generated artifacts (check git history), regenerate via the project's existing tool rather than hand-editing.

- [ ] **Step 4: Update CLAUDE.md anti-pattern bullets if relevant**

The CLAUDE.md "Anti-patterns (top 3)" list references the lint engine. The full SSOT is `02-anti-patterns.yaml`, which we already updated in Task 7 — no edit needed unless the user wants `dm.named` promoted to a top-3 bullet.

- [ ] **Step 5: Commit any doc fixups from Step 3 (if any)**

```bash
git add CLAUDE.md llms.txt llms-full.txt 2>/dev/null
git commit -m "docs: sweep agent-facing prose for dm.named → dm.color (#164)" || true
```

- [ ] **Step 6: Push and open a PR**

```bash
git push -u origin feat/color-parser-api
gh pr create --title "feat(colors): dm.color string parser + color → colors module rename" --body "$(cat <<'EOF'
Closes #164.

## Summary

- Adds `dm.color(value)` — a single string-parser entry point that
  routes by leading `#` (hex), functional `rgb(...)`/`oklch(...)`/`oklab(...)`,
  or palette-name fallback. Mirrors `dm.length`.
- Adds `Color.parse(value: str)` classmethod containing the dispatch logic.
- Renames `src/dartwork_mpl/color/` → `src/dartwork_mpl/colors/` and ships
  a backward-compat shim under `dartwork_mpl.color` that re-exports from
  `dartwork_mpl.colors` and emits a single `DeprecationWarning` on import.
- Deprecates `dm.named` (kept working, now emits `DeprecationWarning`
  pointing to `dm.color`).
- Adds the `named-deprecated` lint rule and an automatic migration
  rewrite (`dm.named(` → `dm.color(`) to `migrate_legacy_code`.
- Sweeps all examples and the doc-asset generator to use `dm.color`.

`dm.hex`, `dm.rgb`, `dm.oklch`, `dm.oklab` are unchanged.

## Test plan

- [ ] `pytest tests/ -q` passes
- [ ] `pytest tests/ -W error::DeprecationWarning -q` passes (with the
      one expected exception — the `TestNamedDeprecation` and shim tests
      use `warnings.catch_warnings`, not `pytest.warns`)
- [ ] One swept example renders without error
- [ ] `from dartwork_mpl.color import Color` still works and emits one
      `DeprecationWarning`
EOF
)"
```

---

## Self-review

**1. Spec coverage (against issue #164):**

- ✅ `dm.named` → `dm.color` rename (issue's primary ask) — Tasks 4 (color), 6 (deprecate named)
- ✅ `dm.color` accepts multiple string forms (oc./tw./hex/rgb/oklch/oklab) — Task 3
- ✅ `dm.hex`, `dm.rgb`, etc. preserved — explicitly *not modified* (mentioned in plan summary, no task touches them)
- ✅ Module rename `color` → `colors` — Tasks 1, 2
- ✅ Backward-compat shim — Task 2
- ✅ Lint rule + migration rule — Tasks 7, 8
- ✅ Examples + asset corpus sweep — Task 9
- ✅ `docs/migration.md` entry — Task 10

**2. Placeholder scan:** No `TBD`, no "implement appropriately", no "similar to Task N". Code blocks are concrete.

**3. Type/identifier consistency:**

- `Color.parse` (classmethod) used consistently in Tasks 3, 4, 5 — same name, same signature.
- `color` (module function) used consistently in Tasks 4, 5, 9 — same signature.
- `_MIGRATE_SAFE_REWRITES` matches the recon report (Task 8).
- `named-deprecated` rule id used in Tasks 7, and matches the YAML schema observed.

**4. Risks the plan acknowledges (read carefully before executing):**

- Line numbers from the recon report will shift mid-plan. Tasks consistently re-grep before editing rather than trusting offsets.
- The exact attribute name on lint diagnostics (`rule_id` vs `id`) was not directly observed; Task 7 Step 1 explicitly grep-checks before relying on it.
- `from_rgb`'s 0–1 vs 0–255 auto-detect threshold is assumed but not verified in the recon; Task 3 Step 4 has a fallback note.
- The `examples_gallery/` vs `examples_source/` distinction is left to runtime check in Task 9 Step 1, not assumed.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-08-dm-color-parser.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using `executing-plans`, batch execution with checkpoints

**Which approach?**
