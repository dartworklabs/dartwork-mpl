---
orphan: true
---

# PR 1 — Core: Width/Aspect API + Lint Module + Asset SSOT (M0–M4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pivot `dm.subplots()` to a `width=`/`aspect=` API with free width input, add deprecation aliases for `SW/MW/TW/DW`/`FS_*`, extract lint rules into a dedicated `dartwork_mpl/lint.py` module backed by `asset/prompt/02-anti-patterns.yaml`, and reorganize `asset/prompt/` into the new SSOT structure (00-index, 01-policy, 02-anti-patterns, 03-recipes, 05-templates).

**Architecture:** Single source of truth lives in `src/dartwork_mpl/asset/prompt/`. Runtime API gains a free-form width parser (cm/inch/mm) and aspect token lookup. Old `figsize=`/`dpi=` paths still work but emit `DeprecationWarning`. `lint.py` exposes `load_rules()` + `lint(code)` so MCP, CLI, and tests all share one engine. No MCP server, install_llm_txt rewrite, or docs sweep in this PR — those land in PR 2 / PR 3.

**Tech Stack:** Python 3.10+, matplotlib ≥ 3.10, pyyaml (new dep), pytest, fastmcp (untouched here). Branch: `feat/ai-readiness-0.4-core` (forked from `feat/ai-readiness-0.4-spec`).

**Out of scope (later PRs):**
- PR 2: MCP server refactor + `install_llm_txt` rewrite + `USAGE_GUIDE.md` deletion
- PR 3: docs/* sweep + drift CI gate + `examples_gallery` migration + `regen_api_reference.py` + 0.4.0 release

**Spec reference:** `docs/superpowers/specs/2026-04-29-dartwork-mpl-ai-readiness-design.md` §3, §4, §10 (M0–M4).

---

## File Map

### Created
- `src/dartwork_mpl/lint.py` — rule loader + `lint(code)` function (replaces inline rules in `mcp/tools.py`)
- `src/dartwork_mpl/units.py` — `cm()`, `inch()`, `mm()` helpers + `parse_width()`
- `src/dartwork_mpl/asset/prompt/00-index.md` — agent entry point with decision tree
- `src/dartwork_mpl/asset/prompt/01-policy.md` — width/aspect/layout/color/font/save policy
- `src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml` — machine-readable rule set
- `src/dartwork_mpl/asset/prompt/03-recipes.md` — intent → function-call cookbook
- `src/dartwork_mpl/asset/prompt/05-templates/{bar,line,scatter,heatmap,tornado,stacked_bar,violin,boxplot,pie,histogram,contour,twin_axis}.py` — 12 executable plot templates
- `src/dartwork_mpl/asset/prompt/_legacy/migration-from-0.3.md` — 0.3 → 0.4 migration cheatsheet
- `tests/test_units.py` — width/aspect parsing
- `tests/test_lint.py` — rule loading + detection
- `tests/test_subplots_width_aspect.py` — new subplots() API
- `tests/test_deprecation_aliases.py` — SW/MW/TW/DW/FS_* warnings

### Modified
- `src/dartwork_mpl/__init__.py` — add `cm`/`inch`/`mm`/`col1`/`col2`, add `__getattr__` for deprecation aliases, remove direct `SW/MW/TW/DW/FS_*/WIDTHS` imports from `__all__`
- `src/dartwork_mpl/figure.py` — add `width=`/`aspect=` params to `subplots()`; `figsize=`/`dpi=` deprecated paths
- `src/dartwork_mpl/mcp/tools.py` — replace inline `lint_dartwork_mpl_code` body with delegation to `dartwork_mpl.lint`
- `pyproject.toml` — add `pyyaml>=6.0` to base deps

### Deleted (after content migrated)
- `src/dartwork_mpl/asset/prompt/coding-rules.md`
- `src/dartwork_mpl/asset/prompt/general-guide.md`
- `src/dartwork_mpl/asset/prompt/layout-guide.md`

(NOT deleted in this PR: `src/dartwork_mpl/asset/USAGE_GUIDE.md`, `src/dartwork_mpl/install.py`, `src/dartwork_mpl/mcp/resources.py` template inlines — those belong to PR 2.)

---

## Task 0: Branch + dependency setup

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Verify clean state on spec branch**

```bash
git status --short docs/superpowers/specs/
git log --oneline -1
```

Expected: spec commit `c80b773` at HEAD on `feat/ai-readiness-0.4-spec`. Working tree may have unrelated user-in-progress changes in `docs/` — leave them alone.

- [ ] **Step 2: Create core branch off spec branch**

```bash
git checkout -b feat/ai-readiness-0.4-core
```

Expected: `Switched to a new branch 'feat/ai-readiness-0.4-core'`.

- [ ] **Step 3: Add pyyaml to dependencies**

Edit `pyproject.toml` line 13–20 (the `dependencies = [...]` array):

```toml
dependencies = [
    "colorspacious>=1.1.2",
    "ipython>=8.32.0",
    "matplotlib>=3.10.1",
    "numpy>=1.26",
    "palettable>=3.3.3",
    "pyyaml>=6.0",
    "scipy>=1.15.2",
]
```

- [ ] **Step 4: Sync env**

```bash
uv sync
```

Expected: pyyaml added to lockfile; no other diffs.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore(deps): add pyyaml for asset/prompt anti-patterns loader"
```

---

## Task 1: `dartwork_mpl/units.py` — width parsing helpers

**Files:**
- Create: `src/dartwork_mpl/units.py`
- Test: `tests/test_units.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_units.py`:

```python
"""Tests for dartwork_mpl.units (free-form width parsing)."""
from __future__ import annotations

import math

import pytest

from dartwork_mpl.units import (
    cm,
    inch,
    mm,
    parse_aspect,
    parse_width,
)


class TestUnitConverters:
    def test_cm_returns_inches(self):
        assert math.isclose(cm(2.54), 1.0, rel_tol=1e-6)

    def test_inch_is_identity(self):
        assert math.isclose(inch(3.5), 3.5, rel_tol=1e-12)

    def test_mm_returns_inches(self):
        assert math.isclose(mm(25.4), 1.0, rel_tol=1e-6)


class TestParseWidth:
    @pytest.mark.parametrize(
        "value,expected_in",
        [
            ("9cm", 9 / 2.54),
            ("9.5cm", 9.5 / 2.54),
            ("17 cm", 17 / 2.54),
            ("6.7in", 6.7),
            ('"6.7in"', 6.7),  # stripped quotes
            ("170mm", 170 / 25.4),
            (13, 13 / 2.54),  # raw int → cm
            (9.0, 9.0 / 2.54),  # raw float → cm
        ],
    )
    def test_accepts_string_and_numeric(self, value, expected_in):
        assert math.isclose(parse_width(value), expected_in, rel_tol=1e-9)

    def test_rejects_negative(self):
        with pytest.raises(ValueError, match="positive"):
            parse_width("-5cm")

    def test_rejects_zero(self):
        with pytest.raises(ValueError, match="positive"):
            parse_width(0)

    def test_rejects_unknown_unit(self):
        with pytest.raises(ValueError, match="unit"):
            parse_width("3foot")

    def test_rejects_non_numeric(self):
        with pytest.raises(ValueError):
            parse_width("abc")


class TestParseAspect:
    @pytest.mark.parametrize(
        "name,ratio",
        [
            ("square", 1.0),
            ("portrait", 5 / 4),  # h/w
            ("standard", 3 / 4),
            ("golden", 1 / 1.618),
            ("wide", 2 / 3),
            ("cinema", 1 / 2),
        ],
    )
    def test_known_tokens(self, name, ratio):
        assert math.isclose(parse_aspect(name), ratio, rel_tol=1e-6)

    def test_numeric_passthrough(self):
        assert parse_aspect(0.5) == 0.5
        assert parse_aspect(1) == 1.0

    def test_rejects_unknown_token(self):
        with pytest.raises(ValueError, match="aspect"):
            parse_aspect("ultra")

    def test_rejects_non_positive(self):
        with pytest.raises(ValueError, match="positive"):
            parse_aspect(-0.5)
        with pytest.raises(ValueError, match="positive"):
            parse_aspect(0)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run python3 -m pytest tests/test_units.py -v
```

Expected: ImportError / collection error (`dartwork_mpl.units` not yet defined).

- [ ] **Step 3: Implement `units.py`**

Create `src/dartwork_mpl/units.py`:

```python
"""Free-form width and aspect parsing helpers.

dartwork-mpl 0.4+ accepts user-supplied widths in physical units
(cm/in/mm) rather than fixed tokens. This module is the parser
that converts those inputs to inches for matplotlib.

It also resolves named aspect tokens (square/portrait/standard/
golden/wide/cinema) into a height/width ratio.
"""

from __future__ import annotations

__all__ = [
    "cm",
    "inch",
    "mm",
    "parse_width",
    "parse_aspect",
    "ASPECT_TOKENS",
    "DEFAULT_ASPECT",
]

import re

CM_PER_INCH: float = 2.54
MM_PER_INCH: float = 25.4

# Named aspect tokens: ratio = height / width.
ASPECT_TOKENS: dict[str, float] = {
    "square": 1.0,
    "portrait": 5.0 / 4.0,
    "standard": 3.0 / 4.0,
    "golden": 1.0 / 1.618,
    "wide": 2.0 / 3.0,
    "cinema": 1.0 / 2.0,
}

DEFAULT_ASPECT: str = "standard"

_WIDTH_RE = re.compile(
    r"""
    ^\s*
    (?P<value>[+-]?\d+(?:\.\d+)?)
    \s*
    (?P<unit>cm|in|mm)?
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)


def cm(value: float) -> float:
    """Convert centimeters to inches."""
    return float(value) / CM_PER_INCH


def inch(value: float) -> float:
    """Identity helper — kept for symmetry with cm/mm."""
    return float(value)


def mm(value: float) -> float:
    """Convert millimeters to inches."""
    return float(value) / MM_PER_INCH


def parse_width(value: str | int | float) -> float:
    """Parse a width specification into inches.

    Parameters
    ----------
    value : str | int | float
        A width like ``"9cm"``, ``"6.7in"``, ``"170mm"``, or a bare
        number (interpreted as cm). Surrounding whitespace and matched
        quote characters are stripped.

    Returns
    -------
    float
        Width in inches. Always strictly positive.

    Raises
    ------
    ValueError
        If the input cannot be parsed, has an unknown unit, or is
        non-positive.
    """
    if isinstance(value, (int, float)):
        if value <= 0:
            raise ValueError(
                f"width must be positive (got {value}); raw numbers "
                f"are interpreted as cm"
            )
        return cm(value)

    if not isinstance(value, str):
        raise ValueError(
            f"width must be str, int, or float (got {type(value).__name__})"
        )

    text = value.strip().strip('"').strip("'")
    match = _WIDTH_RE.match(text)
    if match is None:
        raise ValueError(f"could not parse width: {value!r}")

    number = float(match.group("value"))
    unit = (match.group("unit") or "cm").lower()
    if number <= 0:
        raise ValueError(f"width must be positive (got {number})")

    if unit == "cm":
        return cm(number)
    if unit == "in":
        return inch(number)
    if unit == "mm":
        return mm(number)
    raise ValueError(f"unknown width unit: {unit!r}")


def parse_aspect(value: str | int | float) -> float:
    """Resolve an aspect specification to a height/width ratio.

    Parameters
    ----------
    value : str | int | float
        Either a known aspect token (``"square"``, ``"portrait"``,
        ``"standard"``, ``"golden"``, ``"wide"``, ``"cinema"``) or a
        positive number interpreted directly as ``height / width``.

    Returns
    -------
    float
        The height/width ratio. Always strictly positive.
    """
    if isinstance(value, (int, float)):
        ratio = float(value)
        if ratio <= 0:
            raise ValueError(f"aspect must be positive (got {ratio})")
        return ratio

    if not isinstance(value, str):
        raise ValueError(
            f"aspect must be str, int, or float (got {type(value).__name__})"
        )

    key = value.strip().lower()
    if key not in ASPECT_TOKENS:
        raise ValueError(
            f"unknown aspect token {value!r}; known: "
            f"{sorted(ASPECT_TOKENS)}"
        )
    return ASPECT_TOKENS[key]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run python3 -m pytest tests/test_units.py -v
```

Expected: 18 passed (3 + 8 parametrize + 6 + 2 from numeric_passthrough/non_positive sub-asserts; pytest counts each parametrize case separately).

- [ ] **Step 5: Commit**

```bash
git add src/dartwork_mpl/units.py tests/test_units.py
git commit -m "feat(units): add free-form width/aspect parsers (cm/in/mm + 6 aspect tokens)"
```

---

## Task 2: Wire `cm`/`inch`/`mm`/`col1`/`col2` into top-level package

**Files:**
- Modify: `src/dartwork_mpl/__init__.py`
- Test: extend `tests/test_units.py`

- [ ] **Step 1: Add the failing test**

Append to `tests/test_units.py`:

```python
class TestPublicSurface:
    def test_cm_inch_mm_exposed_at_top_level(self):
        import dartwork_mpl as dm

        assert callable(dm.cm)
        assert callable(dm.inch)
        assert callable(dm.mm)
        assert math.isclose(dm.cm(2.54), 1.0, rel_tol=1e-6)

    def test_col1_and_col2_are_constants(self):
        import dartwork_mpl as dm

        # 9 cm and 17 cm in inches.
        assert math.isclose(dm.col1, 9 / 2.54, rel_tol=1e-9)
        assert math.isclose(dm.col2, 17 / 2.54, rel_tol=1e-9)
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run python3 -m pytest tests/test_units.py::TestPublicSurface -v
```

Expected: AttributeError on `dm.cm` (the existing `dm.cm2in` shadows nothing yet).

- [ ] **Step 3: Update `__init__.py` exports**

In `src/dartwork_mpl/__init__.py`, find the existing block around line 116–144 and replace the `Color utilities` import region. Specifically:

Replace lines 116–143 (currently imports `cm2in` from `util` and `validate*` from `validate*`) with:

```python
# --- Explicit imports from split modules (formerly in util.py) ---
# Scaling helpers
from .scale import fs, fw, lw

# Spine and grid utilities
from .spines import (
    add_frame,
    add_grid,
    hide_all_spines,
    hide_spines,
    minimal_axes,
    remove_grid,
    show_only_spines,
    style_spines,
)

# Import style module exports
from .style import Style, list_styles, load_style_dict, style, style_path

# Extended plot functions (from templates, formerly xplot)
from .templates import plot_diverging_bar

# Unit helpers (0.4+: free-form width input)
from .units import cm, inch, mm

# Color utilities
from .util import cm2in, make_offset, mix_colors, pseudo_alpha, set_decimal

# Validation entry points
from .validate import validate_figure
from .validate_enhanced import validate_with_fixes

# Academic column-width sugar (0.4+).
col1: float = cm(9)
col2: float = cm(17)
```

Then in the `__all__` list (around line 147–249), add new entries. Find the `# Units` section and add `cm`, `inch`, `mm`, `col1`, `col2`:

```python
    # Units (0.4+)
    "cm",
    "inch",
    "mm",
    "col1",
    "col2",
    # Units (legacy helpers, kept for compatibility)
    "cm2in",
    "make_offset",
```

The existing `"cm2in"` and `"make_offset"` lines (currently under `# Units`) move to the second block. Do not delete `cm2in` — it remains exported (no deprecation) since it is a pure conversion utility, not a tier alias.

- [ ] **Step 4: Run test**

```bash
uv run python3 -m pytest tests/test_units.py::TestPublicSurface -v
```

Expected: 2 passed.

- [ ] **Step 5: Smoke-import the package**

```bash
uv run python3 -c "import dartwork_mpl as dm; print(dm.cm(2.54), dm.col1, dm.col2)"
```

Expected: `1.0 3.5433070866141733 6.6929133858267715`.

- [ ] **Step 6: Commit**

```bash
git add src/dartwork_mpl/__init__.py tests/test_units.py
git commit -m "feat(api): expose dm.cm/inch/mm and dm.col1/col2 at top level"
```

---

## Task 3: Deprecation aliases for `SW/MW/TW/DW/WIDTHS/FS_*`

**Files:**
- Modify: `src/dartwork_mpl/__init__.py`
- Test: `tests/test_deprecation_aliases.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_deprecation_aliases.py`:

```python
"""Verify SW/MW/TW/DW/WIDTHS/FS_* emit DeprecationWarning in 0.4."""
from __future__ import annotations

import math
import warnings

import pytest

import dartwork_mpl as dm


DEPRECATED_WIDTH_TOKENS: dict[str, float] = {
    # token -> expected width in cm
    "SW": 9.0,
    "MW": 12.0,
    "TW": 14.5,
    "DW": 17.0,
}

DEPRECATED_FS_TOKENS: tuple[str, ...] = (
    "FS_SINGLE",
    "FS_DOUBLE",
    "FS_SQUARE",
    "FS_WIDE",
    "FS_TALL",
    "FS_GOLDEN",
    "FS_SLIDE",
    "FS_A4",
    "WIDTHS",
)


@pytest.mark.parametrize("name,cm_value", list(DEPRECATED_WIDTH_TOKENS.items()))
def test_width_tokens_warn_and_resolve(name, cm_value):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        value = getattr(dm, name)
    deprecation = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert deprecation, f"{name} should emit DeprecationWarning"
    assert name in str(deprecation[0].message)
    # Value must equal cm_value cm in inches.
    assert math.isclose(value, cm_value / 2.54, rel_tol=1e-9)


@pytest.mark.parametrize("name", DEPRECATED_FS_TOKENS)
def test_fs_and_widths_tokens_warn(name):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        value = getattr(dm, name)
    assert any(
        issubclass(w.category, DeprecationWarning) for w in caught
    ), f"{name} should emit DeprecationWarning"
    assert value is not None


def test_unknown_attribute_still_raises():
    with pytest.raises(AttributeError, match="completely_made_up"):
        _ = dm.completely_made_up


def test_warning_only_once_with_default_filter():
    """Default warnings filter dedupes; verify dm.SW still resolves twice."""
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        first = dm.SW
        second = dm.SW
    assert first == second
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run python3 -m pytest tests/test_deprecation_aliases.py -v
```

Expected: most pass (since `SW/MW/TW/DW/FS_*` are still imported eagerly), but the DeprecationWarning assertions fail — no warning is emitted today.

- [ ] **Step 3: Replace eager imports with `__getattr__` machinery**

In `src/dartwork_mpl/__init__.py`:

1. Remove the eager block that currently reads (lines ≈ 53–68):

```python
# Import constant module exports
from .constant import (
    DW,
    FS_A4,
    FS_DOUBLE,
    FS_GOLDEN,
    FS_SINGLE,
    FS_SLIDE,
    FS_SQUARE,
    FS_TALL,
    FS_WIDE,
    MW,
    SW,
    TW,
    WIDTHS,
)
```

Delete the entire `from .constant import ( ... )` block.

2. Remove the corresponding entries from `__all__` (lines ≈ 161–175). Specifically delete:

```python
    # Constant module
    "DW",
    "SW",
    "MW",
    "TW",
    "WIDTHS",
    "FS_SINGLE",
    "FS_DOUBLE",
    "FS_SQUARE",
    "FS_WIDE",
    "FS_TALL",
    "FS_GOLDEN",
    "FS_SLIDE",
    "FS_A4",
```

The `__all__` list now omits these — they are no longer part of the public API surface, only the deprecation shim.

3. Replace the existing `__getattr__` function (currently around lines 269–285) with this expanded version:

```python
# Deprecated 0.3.x width tokens. Mapping: name -> width in cm.
# These return inches at access time and emit DeprecationWarning.
_DEPRECATED_WIDTHS_CM: dict[str, float] = {
    "SW": 9.0,
    "MW": 12.0,
    "TW": 14.5,
    "DW": 17.0,
}

# Deprecated 0.3.x figure-size tuples and aggregate. Names map to
# attributes on the constant module which we still resolve via lazy
# import (without re-exporting in __all__).
_DEPRECATED_TUPLE_NAMES: frozenset[str] = frozenset({
    "FS_SINGLE",
    "FS_DOUBLE",
    "FS_SQUARE",
    "FS_WIDE",
    "FS_TALL",
    "FS_GOLDEN",
    "FS_SLIDE",
    "FS_A4",
    "WIDTHS",
})


def __getattr__(name):
    """Provide deprecated attribute access with warnings."""
    if name == "agent_utils":
        warnings.warn(
            "agent_utils is deprecated, use helpers instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return helpers
    if name == "xplot":
        warnings.warn(
            "xplot is deprecated, use templates instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return templates
    if name in _DEPRECATED_WIDTHS_CM:
        cm_value = _DEPRECATED_WIDTHS_CM[name]
        warnings.warn(
            f"dm.{name} is deprecated and will be removed in 0.5.0. "
            f"Use width=\"{cm_value:g}cm\" with dm.subplots(...), or "
            f"dm.cm({cm_value:g}) for a raw inches value. "
            f"For academic columns prefer dm.col1 / dm.col2.",
            DeprecationWarning,
            stacklevel=2,
        )
        from .units import cm as _cm
        return _cm(cm_value)
    if name in _DEPRECATED_TUPLE_NAMES:
        warnings.warn(
            f"dm.{name} is deprecated and will be removed in 0.5.0. "
            f"Use dm.subplots(width=..., aspect=...) instead of "
            f"figsize tuples.",
            DeprecationWarning,
            stacklevel=2,
        )
        from . import constant as _constant
        return getattr(_constant, name)
    raise AttributeError(f"module 'dartwork_mpl' has no attribute {name!r}")
```

- [ ] **Step 4: Run deprecation tests**

```bash
uv run python3 -m pytest tests/test_deprecation_aliases.py -v
```

Expected: all pass.

- [ ] **Step 5: Run the existing test suite to catch regressions**

```bash
uv run python3 -m pytest tests/ -v -x
```

Expected: any test that imports `dm.SW`/`dm.DW` etc. now emits warnings but still passes (numerical values unchanged). If something explicitly asserts `pytest.warns` is absent, those tests are fine because we removed the eager import path. If the existing suite uses `error` warning filter, you may see test failures; in that case wrap the offending tests with `warnings.catch_warnings()` or update them to use the new API in this PR's relevant scope only.

If the suite is green, continue. If a test fails with "DeprecationWarning treated as error", record the failure and proceed to Step 6 — the migration of those tests will be addressed in a follow-up commit later in this task.

- [ ] **Step 6: Smoke verify deprecation message text**

```bash
uv run python3 -W "default::DeprecationWarning" -c "import dartwork_mpl as dm; _ = dm.SW; _ = dm.FS_SINGLE"
```

Expected: two `DeprecationWarning` lines printed mentioning `dm.SW` and `dm.FS_SINGLE`, with replacement guidance.

- [ ] **Step 7: Commit**

```bash
git add src/dartwork_mpl/__init__.py tests/test_deprecation_aliases.py
git commit -m "feat(api)!: deprecate SW/MW/TW/DW/WIDTHS/FS_* via __getattr__ shim

Tokens still resolve to identical inch values for now, but emit
DeprecationWarning pointing users to width=\"...cm\"/dm.cm(...) and
dm.col1/dm.col2. Scheduled for removal in 0.5.0."
```

---

## Task 4: New `width=`/`aspect=` API on `dm.subplots`

**Files:**
- Modify: `src/dartwork_mpl/figure.py`
- Test: `tests/test_subplots_width_aspect.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_subplots_width_aspect.py`:

```python
"""Tests for dm.subplots() width=/aspect= API (0.4+)."""
from __future__ import annotations

import math
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm


def _close(fig):
    plt.close(fig)


class TestWidthAspect:
    def test_width_string_cm(self):
        fig, _ = dm.subplots(width="13cm", aspect="standard")
        try:
            w, h = fig.get_size_inches()
            assert math.isclose(w, 13 / 2.54, rel_tol=1e-6)
            assert math.isclose(h / w, 3 / 4, rel_tol=1e-6)
        finally:
            _close(fig)

    def test_width_string_inch(self):
        fig, _ = dm.subplots(width="6.7in", aspect="square")
        try:
            w, h = fig.get_size_inches()
            assert math.isclose(w, 6.7, rel_tol=1e-6)
            assert math.isclose(h, w, rel_tol=1e-6)
        finally:
            _close(fig)

    def test_width_with_dm_cm(self):
        fig, _ = dm.subplots(width=dm.cm(11.3), aspect="wide")
        try:
            w, h = fig.get_size_inches()
            assert math.isclose(w, 11.3 / 2.54, rel_tol=1e-6)
            assert math.isclose(h / w, 2 / 3, rel_tol=1e-6)
        finally:
            _close(fig)

    def test_width_raw_int_is_cm(self):
        fig, _ = dm.subplots(width=13)
        try:
            w, _h = fig.get_size_inches()
            assert math.isclose(w, 13 / 2.54, rel_tol=1e-6)
        finally:
            _close(fig)

    def test_aspect_default_is_standard(self):
        fig, _ = dm.subplots(width="9cm")
        try:
            w, h = fig.get_size_inches()
            assert math.isclose(h / w, 3 / 4, rel_tol=1e-6)
        finally:
            _close(fig)

    def test_aspect_numeric(self):
        fig, _ = dm.subplots(width="10cm", aspect=0.5)
        try:
            w, h = fig.get_size_inches()
            assert math.isclose(h / w, 0.5, rel_tol=1e-6)
        finally:
            _close(fig)


class TestFigsizeDeprecation:
    def test_figsize_emits_deprecation(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            fig, _ = dm.subplots(figsize=(5, 3))
            try:
                pass
            finally:
                _close(fig)
        msgs = [
            str(w.message)
            for w in caught
            if issubclass(w.category, DeprecationWarning)
        ]
        assert any("figsize" in m for m in msgs), msgs

    def test_dpi_emits_deprecation(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            fig, _ = dm.subplots(dpi=150)
            try:
                pass
            finally:
                _close(fig)
        msgs = [
            str(w.message)
            for w in caught
            if issubclass(w.category, DeprecationWarning)
        ]
        assert any("dpi" in m for m in msgs)

    def test_width_and_figsize_both_specified_warns_and_figsize_wins(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            fig, _ = dm.subplots(width="9cm", figsize=(7, 4))
            try:
                w, h = fig.get_size_inches()
            finally:
                _close(fig)
        # figsize wins for backward compat during 0.4.x.
        assert math.isclose(w, 7, rel_tol=1e-6)
        assert math.isclose(h, 4, rel_tol=1e-6)
        # And a warning is emitted.
        assert any(
            issubclass(w.category, DeprecationWarning) for w in caught
        )


class TestErrors:
    def test_invalid_width_unit(self):
        with pytest.raises(ValueError, match="unit"):
            dm.subplots(width="3foot")

    def test_invalid_aspect(self):
        with pytest.raises(ValueError, match="aspect"):
            dm.subplots(width="9cm", aspect="ultra")

    def test_negative_width(self):
        with pytest.raises(ValueError, match="positive"):
            dm.subplots(width="-1cm")
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run python3 -m pytest tests/test_subplots_width_aspect.py -v
```

Expected: many fail — `subplots()` doesn't accept `width=`/`aspect=` and doesn't emit deprecation warnings for `figsize=`/`dpi=`.

- [ ] **Step 3: Update `figure.py::subplots`**

In `src/dartwork_mpl/figure.py`, replace the `subplots` function (lines 17–188) with:

```python
def subplots(
    nrows: int = 1,
    ncols: int = 1,
    *,
    width: str | int | float | None = None,
    aspect: str | int | float = "standard",
    style: str | list[str] | None = None,
    figsize: tuple[float, float] | None = None,
    dpi: int | None = None,
    sharex: bool | Literal["none", "all", "row", "col"] = False,
    sharey: bool | Literal["none", "all", "row", "col"] = False,
    squeeze: bool = True,
    width_ratios: list[float] | None = None,
    height_ratios: list[float] | None = None,
    subplot_kw: dict[str, Any] | None = None,
    gridspec_kw: dict[str, Any] | None = None,
    **fig_kw: Any,
) -> tuple[Figure, Axes | np.ndarray]:
    """Create a figure and a set of subplots with optional style application.

    The 0.4 API takes ``width`` (free-form, e.g. ``"13cm"``,
    ``dm.cm(11.3)``, or a bare number interpreted as cm) plus a
    height/width ratio via ``aspect`` (named token or positive float).

    The legacy ``figsize=``/``dpi=`` parameters still work but emit
    ``DeprecationWarning`` and will be removed in 0.5.0.

    Parameters
    ----------
    nrows, ncols : int, optional
        Subplot grid dimensions.
    width : str | int | float | None, optional
        Figure width. Accepts ``"<num><unit>"`` strings (cm/in/mm),
        the helpers ``dm.cm(x)``/``dm.inch(x)``/``dm.mm(x)``, or a
        raw number (interpreted as cm). If ``None`` and a style is
        provided, the style's default figsize is used.
    aspect : str | int | float, optional
        Height/width ratio. Either a named token in
        ``{"square","portrait","standard","golden","wide","cinema"}``
        or a positive float. Default ``"standard"`` (3:4).
    style : str | list[str] | None, optional
        Style preset(s) to apply. See :func:`dartwork_mpl.style.use`.
    figsize : tuple[float, float] | None, optional
        DEPRECATED. Use ``width`` and ``aspect`` instead. Will be
        removed in 0.5.0.
    dpi : int | None, optional
        DEPRECATED. The active style controls dpi; remove this argument.
        Will be removed in 0.5.0.
    sharex, sharey : bool | str, optional
        Axis sharing flags forwarded to ``plt.subplots``.
    squeeze : bool, optional
        If True (default), single Axes object is returned when
        nrows=ncols=1; otherwise an ndarray of Axes is always returned.
    width_ratios, height_ratios : list[float] | None, optional
        GridSpec ratios.
    subplot_kw, gridspec_kw : dict | None, optional
        Forwarded to matplotlib.
    **fig_kw : Any
        Additional keyword arguments forwarded to ``plt.figure``.

    Returns
    -------
    tuple[Figure, Axes | np.ndarray]
        The created figure and axes.
    """
    from .units import DEFAULT_ASPECT, parse_aspect, parse_width

    # Apply style first so its rcParams are visible to the rest.
    original_rcParams = None
    if style is not None:
        original_rcParams = plt.rcParams.copy()
        from . import style as style_module
        if isinstance(style, str):
            style_module.use(style)
        elif isinstance(style, list):
            style_module.stack(style)
        else:
            raise ValueError(
                f"style must be str or list, got {type(style)}"
            )

    # Deprecation handling for figsize / dpi.
    if figsize is not None:
        import warnings as _warnings
        _warnings.warn(
            "figsize= on dm.subplots is deprecated and will be removed "
            "in 0.5.0. Use dm.subplots(width=..., aspect=...) instead "
            "(e.g. width=\"13cm\", aspect=\"wide\").",
            DeprecationWarning,
            stacklevel=2,
        )
    if dpi is not None:
        import warnings as _warnings
        _warnings.warn(
            "dpi= on dm.subplots is deprecated and will be removed in "
            "0.5.0. The active style controls dpi.",
            DeprecationWarning,
            stacklevel=2,
        )

    # Resolve width/aspect → final figsize, unless legacy figsize was
    # supplied (legacy wins for back-compat in 0.4.x).
    resolved_figsize: tuple[float, float] | None = None
    if figsize is not None:
        resolved_figsize = figsize
    elif width is not None:
        w_in = parse_width(width)
        ratio = parse_aspect(aspect if aspect is not None else DEFAULT_ASPECT)
        resolved_figsize = (w_in, w_in * ratio)
    else:
        # Fall back to style's figsize if a style was applied.
        if style is not None:
            style_figsize = plt.rcParams.get("figure.figsize")
            if (
                original_rcParams is not None
                and style_figsize is not None
                and style_figsize != original_rcParams.get("figure.figsize")
            ):
                resolved_figsize = cast(
                    tuple[float, float], tuple(style_figsize)
                )

    # Resolve dpi from style if not explicitly provided.
    resolved_dpi: int | None = dpi
    if resolved_dpi is None and style is not None:
        style_dpi = plt.rcParams.get("figure.dpi")
        if (
            original_rcParams is not None
            and style_dpi is not None
            and style_dpi != original_rcParams.get("figure.dpi")
        ):
            resolved_dpi = int(style_dpi)

    # Build kwargs.
    kwargs: dict[str, Any] = {}
    if resolved_figsize is not None:
        kwargs["figsize"] = resolved_figsize
    if resolved_dpi is not None:
        kwargs["dpi"] = resolved_dpi

    if gridspec_kw is None:
        gridspec_kw = {}
    if width_ratios is not None:
        gridspec_kw["width_ratios"] = width_ratios
    if height_ratios is not None:
        gridspec_kw["height_ratios"] = height_ratios
    if gridspec_kw:
        kwargs["gridspec_kw"] = gridspec_kw
    if subplot_kw is not None:
        kwargs["subplot_kw"] = subplot_kw
    kwargs.update(fig_kw)

    return plt.subplots(
        nrows=nrows,
        ncols=ncols,
        sharex=sharex,
        sharey=sharey,
        squeeze=squeeze,
        **kwargs,
    )
```

The "Zero-Resize Policy" Notes paragraph is replaced by docstring text describing the new API. Do not modify the `figure(...)` function in this PR — it stays on the legacy figsize/dpi signature; PR 3's docs sweep will rewrite its docstring. (`figure(...)` is rarely used by autonomous agents, who reach for `subplots`.)

- [ ] **Step 4: Run tests**

```bash
uv run python3 -m pytest tests/test_subplots_width_aspect.py -v
```

Expected: all pass.

- [ ] **Step 5: Run full suite to catch regressions**

```bash
uv run python3 -m pytest tests/ -v
```

Expected: all pass. If a test relies on the old `subplots()` signature accepting `figsize=` silently, it now emits warnings — those tests are still green numerically, but if `-W error` is set somewhere, wrap the affected calls in `warnings.catch_warnings()`. None expected at this point.

- [ ] **Step 6: Commit**

```bash
git add src/dartwork_mpl/figure.py tests/test_subplots_width_aspect.py
git commit -m "feat(figure)!: subplots() accepts width=/aspect=; figsize=/dpi= deprecated"
```

---

## Task 5: `dartwork_mpl/lint.py` — extract anti-pattern engine

**Files:**
- Create: `src/dartwork_mpl/lint.py`
- Test: `tests/test_lint.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_lint.py`:

```python
"""Tests for dartwork_mpl.lint — anti-pattern detection engine."""
from __future__ import annotations

import pytest

from dartwork_mpl.lint import Issue, Rule, lint, load_rules


GOOD_CODE = '''
import matplotlib.pyplot as plt
import dartwork_mpl as dm

fig, ax = dm.subplots(width="13cm", aspect="wide")
ax.bar(["A", "B"], [1, 2], color="dc.blue500")
dm.auto_layout(fig)
dm.save_and_show(fig, "out")
'''

BAD_FIGSIZE = '''
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(5, 3))
'''

BAD_TIGHT_LAYOUT = '''
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
plt.tight_layout()
'''

BAD_ZERO_RESIZE_MENTION = '''
# Zero-Resize Policy is great
import dartwork_mpl as dm
'''


class TestLoadRules:
    def test_returns_nonempty_rule_list(self):
        rules = load_rules()
        assert isinstance(rules, list)
        assert len(rules) >= 5
        for r in rules:
            assert isinstance(r, Rule)
            assert r.id
            assert r.severity in {"critical", "warning", "info"}
            assert r.message

    def test_includes_core_rule_ids(self):
        ids = {r.id for r in load_rules()}
        for required in {
            "figsize-direct",
            "tight-layout",
            "zero-resize-mention",
            "plt-style-use",
            "plt-show-only",
        }:
            assert required in ids


class TestLint:
    def test_good_code_has_no_critical_issues(self):
        issues = lint(GOOD_CODE)
        criticals = [i for i in issues if i.severity == "critical"]
        assert criticals == []

    def test_detects_figsize_direct(self):
        issues = lint(BAD_FIGSIZE)
        ids = {i.rule_id for i in issues}
        assert "figsize-direct" in ids
        figsize_issue = next(i for i in issues if i.rule_id == "figsize-direct")
        assert figsize_issue.severity == "critical"

    def test_detects_tight_layout(self):
        issues = lint(BAD_TIGHT_LAYOUT)
        assert any(i.rule_id == "tight-layout" for i in issues)

    def test_detects_zero_resize_mention(self):
        issues = lint(BAD_ZERO_RESIZE_MENTION)
        assert any(i.rule_id == "zero-resize-mention" for i in issues)

    def test_issue_has_message_and_line(self):
        issues = lint(BAD_FIGSIZE)
        first = next(i for i in issues if i.rule_id == "figsize-direct")
        assert first.message
        assert first.line is None or first.line >= 1


class TestRuleApplication:
    def test_custom_rules_subset(self):
        all_rules = load_rules()
        subset = [r for r in all_rules if r.id == "figsize-direct"]
        issues = lint(BAD_TIGHT_LAYOUT, rules=subset)
        assert all(i.rule_id == "figsize-direct" for i in issues)
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run python3 -m pytest tests/test_lint.py -v
```

Expected: import error (`dartwork_mpl.lint` doesn't exist).

- [ ] **Step 3: Create the YAML rule set**

Create `src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml`:

```yaml
# dartwork-mpl anti-pattern catalog (SSOT for lint engine).
#
# Each rule has:
#   id          unique kebab-case identifier
#   severity    critical | warning | info
#   detector
#     kind      regex | substring
#     pattern   regex pattern (Python re, MULTILINE) for kind=regex
#     literal   literal substring (case-sensitive) for kind=substring
#   message     short user-facing text shown in the lint report
#   why         (optional) longer rationale; shown only on demand
#   fix_suggestion  (optional) one-line replacement or pointer
#
# Rule IDs are part of the public API: tools, docs, and tests refer
# to them. Do not rename without bumping the dartwork-mpl version.

version: 1
rules:
  - id: figsize-direct
    severity: critical
    detector:
      kind: regex
      pattern: '\bfigsize\s*=\s*\('
    message: |
      `figsize=` is forbidden. Use `dm.subplots(width="13cm", aspect="wide")`
      with width as cm/in/mm string or `dm.cm(...)`.
    why: |
      Width and aspect are decided separately so report-wide width
      consistency can be enforced and so the height follows from the
      content's aspect intent.
    fix_suggestion: 'dm.subplots(width="13cm", aspect="standard")'

  - id: tight-layout
    severity: critical
    detector:
      kind: regex
      pattern: '\btight_layout\s*\('
    message: |
      `tight_layout()` collides with dartwork-mpl's spine and legend
      handling. Use `dm.auto_layout(fig)` (or `dm.simple_layout` for
      advanced GridSpec cases).
    fix_suggestion: 'dm.auto_layout(fig)'

  - id: zero-resize-mention
    severity: warning
    detector:
      kind: substring
      literal: 'Zero-Resize'
    message: |
      "Zero-Resize Policy" was retired in 0.4.0. dartwork-mpl now uses
      free-form width input plus a lint consistency guard.

  - id: plt-style-use
    severity: warning
    detector:
      kind: regex
      pattern: '\bplt\.style\.use\s*\('
    message: |
      Use `dm.style.use(...)` (or stack styles via dm.subplots(style=...))
      instead of `plt.style.use(...)`.
    fix_suggestion: 'dm.style.use("scientific")'

  - id: plt-show-only
    severity: info
    detector:
      kind: regex
      pattern: '\bplt\.show\s*\(\)'
    message: |
      Prefer `dm.save_and_show(fig, "name")` or `dm.save_formats(fig,
      "name")` so the figure ships with its rendered artifact.

  - id: plt-subplots
    severity: warning
    detector:
      kind: regex
      pattern: '\bplt\.subplots\s*\('
    message: |
      Use `dm.subplots(...)` so dartwork-mpl can apply style, width,
      and aspect handling.

  - id: cm2in-figsize
    severity: warning
    detector:
      kind: regex
      pattern: 'figsize\s*=\s*\([^)]*cm2in'
    message: |
      `figsize=(dm.cm2in(...), dm.cm2in(...))` is the legacy 0.3
      pattern. Use `width="<n>cm"` plus an aspect token instead.
    fix_suggestion: 'dm.subplots(width="9cm", aspect="standard")'

  - id: deprecated-width-token
    severity: warning
    detector:
      kind: regex
      pattern: '\bdm\.(SW|MW|TW|DW|FS_[A-Z_]+|WIDTHS)\b'
    message: |
      `dm.SW/MW/TW/DW/FS_*/WIDTHS` are deprecated and slated for
      removal in 0.5.0. Use `dm.subplots(width="...cm", aspect="...")`,
      or `dm.col1`/`dm.col2` for academic columns.

  - id: dpi-arg
    severity: warning
    detector:
      kind: regex
      pattern: '(subplots|figure)\s*\([^)]*\bdpi\s*='
    message: |
      `dpi=` should not be set per-figure. The active dartwork-mpl
      style controls dpi (display vs savefig).
```

- [ ] **Step 4: Implement `dartwork_mpl/lint.py`**

Create `src/dartwork_mpl/lint.py`:

```python
"""dartwork-mpl lint engine.

Loads the anti-pattern catalog from
``asset/prompt/02-anti-patterns.yaml`` and applies it to a Python
source string. Used by the MCP ``lint_dartwork_mpl_code`` tool, the
``dartwork-mpl lint`` CLI, and CI drift tests.

The catalog is the single source of truth: code never inlines rule
text. Add or change rules in the YAML file; this module loads them
verbatim.
"""

from __future__ import annotations

__all__ = [
    "Rule",
    "Issue",
    "load_rules",
    "lint",
    "format_report",
]

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml

_RULES_PATH: Path = (
    Path(__file__).parent / "asset" / "prompt" / "02-anti-patterns.yaml"
)


@dataclass(frozen=True)
class Rule:
    """A single anti-pattern definition."""

    id: str
    severity: str          # "critical" | "warning" | "info"
    detector_kind: str     # "regex" | "substring"
    detector_value: str    # pattern or literal
    message: str
    why: str | None = None
    fix_suggestion: str | None = None


@dataclass(frozen=True)
class Issue:
    """A detected violation."""

    rule_id: str
    severity: str
    message: str
    line: int | None = None
    snippet: str | None = None


def load_rules(path: Path | None = None) -> list[Rule]:
    """Load and parse the anti-pattern catalog.

    Parameters
    ----------
    path : Path | None, optional
        Override path for testing. Defaults to the bundled
        ``02-anti-patterns.yaml``.

    Returns
    -------
    list[Rule]
        Parsed rule objects in declaration order.
    """
    yaml_path = path or _RULES_PATH
    with yaml_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    rules: list[Rule] = []
    for entry in data.get("rules", []):
        detector = entry.get("detector", {})
        kind = detector.get("kind", "regex")
        if kind == "regex":
            value = detector["pattern"]
        elif kind == "substring":
            value = detector["literal"]
        else:
            raise ValueError(
                f"Unsupported detector kind {kind!r} in rule "
                f"{entry.get('id')!r}"
            )
        rules.append(
            Rule(
                id=entry["id"],
                severity=entry["severity"],
                detector_kind=kind,
                detector_value=value,
                message=entry["message"].rstrip(),
                why=(entry.get("why") or None),
                fix_suggestion=entry.get("fix_suggestion"),
            )
        )
    return rules


def _scan_one(code: str, rule: Rule) -> list[Issue]:
    matches: list[Issue] = []
    if rule.detector_kind == "regex":
        pattern = re.compile(rule.detector_value, re.MULTILINE)
        for m in pattern.finditer(code):
            line = code.count("\n", 0, m.start()) + 1
            snippet = code.splitlines()[line - 1].strip() if code else None
            matches.append(
                Issue(
                    rule_id=rule.id,
                    severity=rule.severity,
                    message=rule.message,
                    line=line,
                    snippet=snippet,
                )
            )
    elif rule.detector_kind == "substring":
        idx = 0
        while True:
            found = code.find(rule.detector_value, idx)
            if found < 0:
                break
            line = code.count("\n", 0, found) + 1
            matches.append(
                Issue(
                    rule_id=rule.id,
                    severity=rule.severity,
                    message=rule.message,
                    line=line,
                )
            )
            idx = found + len(rule.detector_value)
    return matches


def lint(code: str, *, rules: Iterable[Rule] | None = None) -> list[Issue]:
    """Apply anti-pattern rules to a Python source string.

    Parameters
    ----------
    code : str
        Python source to scan.
    rules : Iterable[Rule] | None, optional
        Override the rule set (e.g. for tests). Defaults to
        :func:`load_rules` output.

    Returns
    -------
    list[Issue]
        Issues in declaration order, deduplicated by (rule_id, line).
    """
    rule_list = list(rules) if rules is not None else load_rules()
    issues: list[Issue] = []
    seen: set[tuple[str, int | None]] = set()
    for rule in rule_list:
        for issue in _scan_one(code, rule):
            key = (issue.rule_id, issue.line)
            if key in seen:
                continue
            seen.add(key)
            issues.append(issue)
    return issues


def format_report(issues: list[Issue]) -> str:
    """Render issues as newline-separated `[SEV] rule-id: message` lines."""
    if not issues:
        return "✅ No issues found."
    lines: list[str] = []
    for issue in issues:
        line_part = f" (line {issue.line})" if issue.line else ""
        lines.append(
            f"[{issue.severity.upper()}] {issue.rule_id}{line_part}: "
            f"{issue.message.splitlines()[0]}"
        )
    return "\n".join(lines)
```

- [ ] **Step 5: Run tests**

```bash
uv run python3 -m pytest tests/test_lint.py -v
```

Expected: all pass.

- [ ] **Step 6: Smoke test with full suite**

```bash
uv run python3 -m pytest tests/ -v
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add src/dartwork_mpl/lint.py src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml tests/test_lint.py
git commit -m "feat(lint): extract anti-pattern engine + 9-rule YAML catalog (SSOT)"
```

---

## Task 6: Wire MCP `lint_dartwork_mpl_code` to the new engine

**Files:**
- Modify: `src/dartwork_mpl/mcp/tools.py`
- Test: `tests/test_lint.py` (add MCP smoke)

- [ ] **Step 1: Add a smoke test for the MCP tool**

Append to `tests/test_lint.py`:

```python
class TestMcpToolDelegation:
    """Verify the MCP tool delegates to dartwork_mpl.lint."""

    def test_tool_returns_clean_message_for_good_code(self):
        from fastmcp import FastMCP

        from dartwork_mpl.mcp.tools import register_tools

        srv = FastMCP("test")
        register_tools(srv)
        # The tool function is registered as a closure on `srv`. We
        # exercise the wrapped Python function directly via the
        # registry.
        tool = next(
            t for t in srv._tool_manager._tools.values()
            if t.name == "lint_dartwork_mpl_code"
        )
        result = tool.fn(GOOD_CODE)
        assert "No issues" in result or "✅" in result

    def test_tool_reports_figsize_direct(self):
        from fastmcp import FastMCP

        from dartwork_mpl.mcp.tools import register_tools

        srv = FastMCP("test")
        register_tools(srv)
        tool = next(
            t for t in srv._tool_manager._tools.values()
            if t.name == "lint_dartwork_mpl_code"
        )
        result = tool.fn(BAD_FIGSIZE)
        assert "figsize-direct" in result
```

If the FastMCP private attributes are not stable, fall back to invoking the closure directly: capture the function in a list inside the test by monkey-patching `srv.tool` before calling `register_tools`. Use this fallback only if the access path above breaks.

- [ ] **Step 2: Run to verify failure**

```bash
uv run python3 -m pytest tests/test_lint.py::TestMcpToolDelegation -v
```

Expected: failure — current MCP tool returns custom message format ("[CRITICAL] 'figsize=' detected ..." not "figsize-direct").

- [ ] **Step 3: Replace the MCP tool body**

In `src/dartwork_mpl/mcp/tools.py`, replace the entire body of `lint_dartwork_mpl_code` (lines 159–274) with a thin delegator. Keep the surrounding section comment and the surrounding tools intact.

Find this block:

```python
    @mcp.tool()
    def lint_dartwork_mpl_code(code: str) -> str:
        """Analyze Python code for dartwork-mpl best practices.

        Checks for common antipatterns:
        ...
        """
        issues = []

        # --- Critical: Zero-Resize Policy ---
        if "figsize=" in code:
            ...
        # ... many more inline checks ...
        if not issues:
            return (
                "✅ No issues found. Code follows dartwork-mpl best practices."
            )
        return "\n".join(issues)
```

Replace with:

```python
    @mcp.tool()
    def lint_dartwork_mpl_code(code: str) -> str:
        """Analyze Python code against the dartwork-mpl anti-pattern
        catalog (asset/prompt/02-anti-patterns.yaml).

        Returns a newline-separated list of ``[SEVERITY] rule-id
        (line N): message`` entries, or a success line.

        Parameters
        ----------
        code : str
            Python source to analyze.

        Returns
        -------
        str
            Lint report.
        """
        from dartwork_mpl.lint import format_report, lint as _lint
        return format_report(_lint(code))
```

- [ ] **Step 4: Run smoke tests**

```bash
uv run python3 -m pytest tests/test_lint.py -v
```

Expected: all pass, including new TestMcpToolDelegation.

- [ ] **Step 5: Run full suite**

```bash
uv run python3 -m pytest tests/ -v
```

Expected: all pass. There may be an existing test in `tests/test_mcp_*` that asserts old text strings; if so, update it to assert against rule IDs (`figsize-direct`, `tight-layout`) instead. Limit edits to the failing test only.

- [ ] **Step 6: Commit**

```bash
git add src/dartwork_mpl/mcp/tools.py tests/test_lint.py
git commit -m "refactor(mcp): delegate lint_dartwork_mpl_code to dartwork_mpl.lint"
```

---

## Task 7: Author `00-index.md`, `01-policy.md`, `03-recipes.md`

**Files:**
- Create: `src/dartwork_mpl/asset/prompt/00-index.md`
- Create: `src/dartwork_mpl/asset/prompt/01-policy.md`
- Create: `src/dartwork_mpl/asset/prompt/03-recipes.md`
- Create: `src/dartwork_mpl/asset/prompt/_legacy/migration-from-0.3.md`

These are content tasks, not behavior tasks; they ship as pure docs in this PR but become MCP-readable in PR 2. Each file has a documented purpose.

- [ ] **Step 1: Write `00-index.md`**

Create `src/dartwork_mpl/asset/prompt/00-index.md`:

```markdown
# dartwork-mpl Agent Entry Point

You are working with **dartwork-mpl**, a publication-quality matplotlib
design system. This file is the routing index — start here, then
fetch the specific guide you need.

## Decision tree

| If the user asked for… | Read this resource |
|---|---|
| A specific plot type (bar, line, heatmap, scatter, …) | `dartwork-mpl://templates/{plot}` |
| Width / aspect / layout / color / save policy | `dartwork-mpl://guide/policy` |
| "How do I do X with dartwork-mpl" cookbook | `dartwork-mpl://guide/recipes` |
| Anti-patterns to avoid | `dartwork-mpl://guide/anti-patterns` |
| A function signature you don't remember | `dartwork-mpl://api/{name}` |
| Color name → hex code | call `get_color_value(name)` |
| Sanity-check a generated script | call `lint_dartwork_mpl_code(code)` |

## Always-true facts

- `import dartwork_mpl as dm` is the only import path you need.
- Use `dm.subplots(width=..., aspect=...)` to create figures.
  `width` is free-form: `"13cm"`, `"6.7in"`, `dm.cm(11.3)`, or a raw
  number (interpreted as cm). `aspect` is one of `square`, `portrait`,
  `standard`, `golden`, `wide`, `cinema`, or a positive float.
- Use named colors: `oc.*`, `tw.*`, `dc.*`, `md.*`, `ad.*`, `cu.*`,
  `pr.*`. Raw hex is allowed but discouraged.
- After creating a figure, call `dm.auto_layout(fig)` and save with
  `dm.save_formats(fig, "name")` or `dm.save_and_show(fig, "name")`.
- Never call `tight_layout()`, `plt.style.use()`, or set `figsize=`
  / `dpi=` directly — those are lint criticals.

## Standard agent loop

1. Read this file.
2. Pick width and aspect from the user's intent.
3. Read the relevant template (`05-templates/{plot}.py`) and start
   from it.
4. Customize the template (data, colors, labels).
5. Pass the final code through `lint_dartwork_mpl_code` and fix any
   `[CRITICAL]` issue before rendering.
6. Render, then call `dm.validate_figure(fig)`.
7. Save with `dm.save_formats` or `dm.save_and_show`.
```

- [ ] **Step 2: Write `01-policy.md`**

Create `src/dartwork_mpl/asset/prompt/01-policy.md`:

```markdown
# dartwork-mpl 0.4 Policy

Every rule below has a matching entry in
`asset/prompt/02-anti-patterns.yaml`; the lint engine enforces them.

## Width

- `dm.subplots(width=...)` is the only legal way to set a figure
  width.
- `width=` accepts:
  - a unit-suffixed string: `"13cm"`, `"9.5cm"`, `"6.7in"`, `"170mm"`
  - a helper call: `dm.cm(11.3)`, `dm.inch(4.6)`, `dm.mm(170)`
  - a raw number: `13` (interpreted as cm — lint emits an info-level
    note suggesting an explicit unit)
  - the academic sugar constants `dm.col1` (= 9 cm) or `dm.col2`
    (= 17 cm).
- `figsize=` is **forbidden** (lint critical, removal in 0.5.0).
- The maximum width is 17 cm.
- Prefer the 0.5 cm grid (9.0, 9.5, 10.0…) for cross-figure
  consistency. Lint emits an info if you stray from it.
- Within one project, keep the number of distinct widths ≤ 5.

## Aspect (height / width)

- Default: `"standard"` (= 3 / 4).
- Tokens:
  - `"square"`  — 1.0
  - `"portrait"` — 5 / 4
  - `"standard"` — 3 / 4
  - `"golden"` — 1 / 1.618
  - `"wide"` — 2 / 3
  - `"cinema"` — 1 / 2
- Or pass a positive float directly. Extreme aspects (< 0.3 or > 4.0)
  trigger a `validate_figure` warning.

## Layout

- `dm.auto_layout(fig)` is the default. Call it after data is plotted.
- `dm.simple_layout(fig)` is reserved for advanced GridSpec cases
  where `auto_layout` cannot fit the bounding boxes.
- `tight_layout()` is **forbidden** (lint critical).

## Color

- Use named palettes: `oc.*` (Open Color), `tw.*` (Tailwind),
  `dc.*` (dartwork core), `md.*` (Material), `ad.*` (Ant),
  `cu.*` (Chakra), `pr.*` (Primer).
- Raw hex strings work but trigger a lint info (prefer named).
- For colormaps: `viridis`, `dc.spectral`, etc. — perceptually uniform
  recommended.

## Font and weight

- Do **not** pass `fontsize=` literals. Use `dm.fs(n)` for an offset
  from the active style's base size. Same for `dm.fw(n)` (weight)
  and `dm.lw(n)` (line width).

## Save and display

- Prefer `dm.save_and_show(fig, "name")` for notebooks (saves +
  inline preview).
- Prefer `dm.save_formats(fig, "name", formats=("png","svg"))` for
  scripts (multi-format, no preview).
- Never end a figure with just `plt.show()` — the rendered artifact
  must be persisted.

## Style presets

- Apply via `dm.style.use("scientific")` or pass a stack to
  `dm.subplots(style=[...])`.
- Korean text → `*-kr` variants (`scientific-kr`, `report-kr`,
  `presentation-kr`).
- Never call `plt.style.use(...)`.
```

- [ ] **Step 3: Write `03-recipes.md`**

Create `src/dartwork_mpl/asset/prompt/03-recipes.md`:

```markdown
# Recipes — Intent → Function Call

A short cookbook keyed by user intent. Each entry shows the canonical
0.4 invocation. For full templates see
`dartwork-mpl://templates/{plot}`.

## "Bar chart"

```python
fig, ax = dm.subplots(width="13cm", aspect="standard")
ax.bar(categories, values, color="dc.blue500", edgecolor="white",
       linewidth=0.3)
ax.set_ylabel("Value")
dm.auto_layout(fig)
```

## "Line chart, time series"

```python
fig, ax = dm.subplots(width="15cm", aspect="wide")
ax.plot(t, y, color="dc.ocean3", linewidth=0.8)
ax.set_xlabel("Time"); ax.set_ylabel("Signal")
dm.auto_layout(fig)
```

## "Scatter with trend"

```python
fig, ax = dm.subplots(width="11cm", aspect="square")
ax.scatter(x, y, color="dc.blue500", edgecolor="white", linewidth=0.3,
           s=20)
dm.auto_layout(fig)
```

## "Heatmap / correlation matrix"

```python
fig, ax = dm.subplots(width="11cm", aspect="square")
im = ax.imshow(matrix, cmap="viridis", aspect="auto")
plt.colorbar(im, ax=ax)
dm.auto_layout(fig)
```

## "Stacked bar"

```python
fig, ax = dm.subplots(width="13cm", aspect="standard")
ax.bar(x, a, color="dc.blue500", label="A")
ax.bar(x, b, bottom=a, color="dc.green500", label="B")
ax.legend()
dm.auto_layout(fig)
```

## "Twin axis"

```python
fig, ax1 = dm.subplots(width="15cm", aspect="wide")
ax2 = ax1.twinx()
ax1.bar(x, precip, color="dc.blue300", alpha=0.7)
ax2.plot(x, temp, color="dc.red500", marker="o", markersize=3)
dm.auto_layout(fig)
```

## "Korean labels"

Apply the language preset before creating the figure:

```python
dm.style.use("report-kr")
fig, ax = dm.subplots(width="13cm", aspect="standard")
ax.set_xlabel("월")
ax.set_ylabel("매출 (억원)")
dm.auto_layout(fig)
```

## "Multi-panel grid (a/b/c labels)"

```python
fig, axes = dm.subplots(2, 2, width="17cm", aspect="standard")
for ax, panel in zip(axes.flat, "abcd"):
    ax.text(0, 1, panel, transform=ax.transAxes + dm.make_offset(4, -4, fig),
            weight="bold", va="top")
dm.label_axes(axes)
dm.auto_layout(fig)
```

## "Save in multiple formats"

```python
dm.save_formats(fig, "output/figure", formats=("svg", "png", "pdf"),
                bbox_inches="tight", dpi=300)
```
```

- [ ] **Step 4: Write `_legacy/migration-from-0.3.md`**

Create `src/dartwork_mpl/asset/prompt/_legacy/migration-from-0.3.md`:

```markdown
# Migrating dartwork-mpl 0.3 → 0.4

## Width tokens

| 0.3 | 0.4 replacement |
|---|---|
| `dm.SW` | `width="9cm"` or `dm.col1` |
| `dm.MW` | `width="12cm"` |
| `dm.TW` | `width="14.5cm"` (or round to `"15cm"`) |
| `dm.DW` | `width="17cm"` or `dm.col2` |
| `dm.WIDTHS` | iterate explicit widths instead |
| `dm.FS_*` tuples | replace with `dm.subplots(width=..., aspect=...)` |

The 0.3 names still resolve at runtime (with a `DeprecationWarning`)
through 0.4.x and are removed in 0.5.0.

## subplots

```python
# 0.3
fig, ax = plt.subplots(figsize=(dm.cm2in(9), dm.cm2in(7)), dpi=200)

# 0.4
fig, ax = dm.subplots(width="9cm", aspect=7/9)
```

## Layout

| 0.3 | 0.4 |
|---|---|
| `plt.tight_layout()` | `dm.auto_layout(fig)` |
| `dm.simple_layout(fig)` (most cases) | `dm.auto_layout(fig)` (recommended); `dm.simple_layout` reserved for advanced GridSpec |

## Style application

| 0.3 | 0.4 |
|---|---|
| `plt.style.use("scientific")` | `dm.style.use("scientific")` |

## What was removed

- The phrase "Zero-Resize Policy" — replaced by free width input plus
  the lint consistency guard described in `01-policy.md`.
- `asset/USAGE_GUIDE.md` (PR 2 deletion) — split into
  `00-index.md` / `01-policy.md` / `03-recipes.md`.
```

- [ ] **Step 5: Verify files exist and parse cleanly**

```bash
ls src/dartwork_mpl/asset/prompt/
uv run python3 -c "
from dartwork_mpl.lint import load_rules
rules = load_rules()
print(f'{len(rules)} rules loaded; ids: {[r.id for r in rules]}')
"
```

Expected: 4 new files in the listing (00, 01, 03, _legacy/), and `9 rules loaded` (we authored 9 in 02-anti-patterns.yaml).

- [ ] **Step 6: Commit**

```bash
git add src/dartwork_mpl/asset/prompt/00-index.md \
        src/dartwork_mpl/asset/prompt/01-policy.md \
        src/dartwork_mpl/asset/prompt/03-recipes.md \
        src/dartwork_mpl/asset/prompt/_legacy/migration-from-0.3.md
git commit -m "docs(asset/prompt): author 00-index/01-policy/03-recipes + 0.3→0.4 migration"
```

---

## Task 8: Extract MCP inline templates → `05-templates/*.py`

**Files:**
- Create: `src/dartwork_mpl/asset/prompt/05-templates/{bar,line,scatter,heatmap,tornado,stacked_bar,violin,boxplot,pie,histogram,contour,twin_axis}.py`

These twelve files must be **executable** (subprocess smoke test in PR 3 will verify) and **lint-clean** under the new policy. They mirror — but do not yet replace — the inline templates in `mcp/resources.py:_TEMPLATES`. The MCP-side switch from inline-dict to file-read is a PR 2 task.

- [ ] **Step 1: Author all 12 templates**

Create the directory and files. Each template uses the new
`width=`/`aspect=` API. Sample template — repeat the pattern for the
other 11 (full bodies below).

```bash
mkdir -p src/dartwork_mpl/asset/prompt/05-templates
```

`05-templates/bar.py`:

```python
"""Vertical bar chart — basic template."""
import matplotlib.pyplot as plt
import dartwork_mpl as dm

categories = ["A", "B", "C", "D", "E"]
values = [23, 45, 56, 78, 33]

fig, ax = dm.subplots(width="13cm", aspect="standard")
ax.bar(categories, values, color="dc.blue500", edgecolor="white",
       linewidth=0.3)
ax.set_ylabel("Value")
dm.auto_layout(fig)
plt.show()
```

`05-templates/line.py`:

```python
"""Two-series line chart."""
import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

x = np.linspace(0, 10, 100)
y1, y2 = np.sin(x), np.cos(x)

fig, ax = dm.subplots(width="15cm", aspect="wide")
ax.plot(x, y1, color="dc.ocean3", linewidth=0.8, label="sin(x)")
ax.plot(x, y2, color="dc.vivid3", linewidth=0.8, label="cos(x)")
ax.set_xlabel("x"); ax.set_ylabel("y"); ax.legend()
dm.auto_layout(fig)
plt.show()
```

`05-templates/scatter.py`:

```python
"""Scatter with linear trend."""
import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

rng = np.random.default_rng(42)
x = rng.normal(size=50)
y = 2 * x + rng.normal(scale=0.5, size=50)

fig, ax = dm.subplots(width="11cm", aspect="square")
ax.scatter(x, y, color="dc.blue500", edgecolor="white", linewidth=0.3, s=20)
ax.set_xlabel("X axis"); ax.set_ylabel("Y axis")
dm.auto_layout(fig)
plt.show()
```

`05-templates/heatmap.py`:

```python
"""8x8 random heatmap with colorbar."""
import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

rng = np.random.default_rng(42)
data = rng.random(size=(8, 8))

fig, ax = dm.subplots(width="11cm", aspect="square")
im = ax.imshow(data, cmap="viridis", aspect="auto")
plt.colorbar(im, ax=ax)
ax.set_xlabel("Column"); ax.set_ylabel("Row")
dm.auto_layout(fig)
plt.show()
```

`05-templates/tornado.py`:

```python
"""Tornado chart — symmetric horizontal bars."""
import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

categories = ["Cat A", "Cat B", "Cat C", "Cat D"]
positive = [10, 25, 15, 30]
negative = [-8, -20, -12, -28]

fig, ax = dm.subplots(width="13cm", aspect="standard")
y_pos = np.arange(len(categories))
ax.barh(y_pos, positive, color="dc.blue500", label="Positive")
ax.barh(y_pos, negative, color="dc.red500", label="Negative")
ax.set_yticks(y_pos); ax.set_yticklabels(categories)
ax.axvline(0, color="black", linewidth=0.5)
ax.set_xlabel("Value"); ax.legend()
dm.auto_layout(fig)
plt.show()
```

`05-templates/stacked_bar.py`:

```python
"""Stacked bar chart with three series."""
import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

categories = ["Q1", "Q2", "Q3", "Q4"]
a = [20, 35, 30, 35]
b = [25, 32, 34, 20]
c = [15, 18, 22, 28]

fig, ax = dm.subplots(width="13cm", aspect="standard")
x = np.arange(len(categories))
ax.bar(x, a, label="A", color="dc.blue500")
ax.bar(x, b, bottom=a, label="B", color="dc.green500")
bottom_c = [ai + bi for ai, bi in zip(a, b, strict=False)]
ax.bar(x, c, bottom=bottom_c, label="C", color="dc.orange500")
ax.set_xticks(x); ax.set_xticklabels(categories)
ax.set_ylabel("Value"); ax.legend()
dm.auto_layout(fig)
plt.show()
```

`05-templates/violin.py`:

```python
"""Violin plot for three groups."""
import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

rng = np.random.default_rng(42)
data = [rng.normal(loc, 1, 100) for loc in (0, 2, 4)]

fig, ax = dm.subplots(width="13cm", aspect="standard")
ax.violinplot(data, showmeans=True, showmedians=True)
ax.set_xticks([1, 2, 3])
ax.set_xticklabels(["Group A", "Group B", "Group C"])
ax.set_ylabel("Value")
dm.auto_layout(fig)
plt.show()
```

`05-templates/boxplot.py`:

```python
"""Box plot across four spreads."""
import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

rng = np.random.default_rng(42)
data = [rng.normal(0, std, 100) for std in (1, 2, 3, 4)]
colors = ["dc.blue500", "dc.green500", "dc.orange500", "dc.red500"]

fig, ax = dm.subplots(width="13cm", aspect="standard")
bp = ax.boxplot(data, patch_artist=True)
for patch, color in zip(bp["boxes"], colors, strict=False):
    patch.set_facecolor(color)
ax.set_xticklabels(["std=1", "std=2", "std=3", "std=4"])
ax.set_ylabel("Value")
dm.auto_layout(fig)
plt.show()
```

`05-templates/pie.py`:

```python
"""Pie chart with four slices."""
import matplotlib.pyplot as plt
import dartwork_mpl as dm

labels = ["A", "B", "C", "D"]
sizes = [35, 25, 25, 15]
colors = ["dc.blue500", "dc.green500", "dc.orange500", "dc.red500"]

fig, ax = dm.subplots(width="11cm", aspect="square")
ax.pie(sizes, labels=labels, colors=colors, autopct="%1.1f%%",
       startangle=90)
ax.set_aspect("equal")
dm.auto_layout(fig)
plt.show()
```

`05-templates/histogram.py`:

```python
"""Histogram of standard normal samples."""
import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

rng = np.random.default_rng(42)
data = rng.standard_normal(1000)

fig, ax = dm.subplots(width="13cm", aspect="standard")
ax.hist(data, bins=30, color="dc.blue500", edgecolor="white", linewidth=0.3)
ax.set_xlabel("Value"); ax.set_ylabel("Frequency")
dm.auto_layout(fig)
plt.show()
```

`05-templates/contour.py`:

```python
"""Filled contour plot of sin(x) cos(y)."""
import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

x = np.linspace(-3, 3, 100)
y = np.linspace(-3, 3, 100)
X, Y = np.meshgrid(x, y)
Z = np.sin(X) * np.cos(Y)

fig, ax = dm.subplots(width="11cm", aspect="square")
cs = ax.contourf(X, Y, Z, levels=20, cmap="viridis")
plt.colorbar(cs, ax=ax)
ax.set_xlabel("x"); ax.set_ylabel("y")
dm.auto_layout(fig)
plt.show()
```

`05-templates/twin_axis.py`:

```python
"""Twin-axis chart: bars (precip) + line (temp)."""
import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

x = np.arange(1, 13)
temp = [5, 7, 12, 18, 23, 27, 30, 29, 24, 18, 11, 6]
precip = [50, 40, 45, 55, 70, 80, 90, 85, 65, 60, 55, 50]

fig, ax1 = dm.subplots(width="15cm", aspect="wide")
ax2 = ax1.twinx()
ax1.bar(x, precip, color="dc.blue300", alpha=0.7, label="Precipitation")
ax2.plot(x, temp, color="dc.red500", marker="o", markersize=3,
         label="Temperature")
ax1.set_xlabel("Month")
ax1.set_ylabel("Precipitation (mm)")
ax2.set_ylabel("Temperature (°C)")
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
dm.auto_layout(fig)
plt.show()
```

- [ ] **Step 2: Smoke-test each template by linting it**

```bash
uv run python3 -c "
from pathlib import Path
from dartwork_mpl.lint import lint, format_report

root = Path('src/dartwork_mpl/asset/prompt/05-templates')
fail = 0
for f in sorted(root.glob('*.py')):
    issues = lint(f.read_text())
    criticals = [i for i in issues if i.severity == 'critical']
    if criticals:
        fail += 1
        print(f'❌ {f.name}: {format_report(criticals)}')
    else:
        print(f'✅ {f.name}')
print('FAIL count =', fail)
"
```

Expected: every template prints `✅` and `FAIL count = 0`. (Warnings are tolerated; critical violations are not.)

- [ ] **Step 3: Smoke-execute one template under Agg backend**

```bash
MPLBACKEND=Agg uv run python3 src/dartwork_mpl/asset/prompt/05-templates/bar.py
```

Expected: no traceback. `plt.show()` is a no-op under Agg, so the script exits cleanly. (Full execution sweep happens in PR 3's CI gate.)

- [ ] **Step 4: Commit**

```bash
git add src/dartwork_mpl/asset/prompt/05-templates/
git commit -m "feat(asset/prompt): add 12 plot templates using width=/aspect= API"
```

---

## Task 9: Delete obsolete `coding-rules.md`/`general-guide.md`/`layout-guide.md`

**Files:**
- Delete: `src/dartwork_mpl/asset/prompt/coding-rules.md`
- Delete: `src/dartwork_mpl/asset/prompt/general-guide.md`
- Delete: `src/dartwork_mpl/asset/prompt/layout-guide.md`

The MCP server (PR 2) still resolves
`dartwork-mpl://guide/general-guide` and
`dartwork-mpl://guide/layout-guide` via `get_prompt`. Those resource
URIs would break if the underlying files vanished. To avoid a broken
state between PRs, this task **does not delete** the three files
yet. Instead, mark them as superseded with a banner so that any
human reader knows the canonical location.

- [ ] **Step 1: Add deprecation banner to each file**

At the very top of each of `coding-rules.md`, `general-guide.md`,
`layout-guide.md`, prepend:

```markdown
> **DEPRECATED in 0.4.0.** This file is retained only so MCP
> resource URIs from prior versions keep resolving. The canonical
> guides are now:
> - `00-index.md` — agent entry point
> - `01-policy.md` — policy / rules
> - `03-recipes.md` — cookbook
>
> This file will be removed in PR 2 once `mcp/resources.py` updates
> its URI mapping.

```

(Note: there are two spaces at the end of the URL line so markdown renders the line break.)

- [ ] **Step 2: Confirm files still parse**

```bash
uv run python3 -c "
import dartwork_mpl as dm
for name in ('coding-rules', 'general-guide', 'layout-guide',
             '00-index', '01-policy', '03-recipes'):
    print(name, len(dm.get_prompt(name)))
"
```

Expected: six lines, each printing the file name and a non-zero
length.

- [ ] **Step 3: Commit**

```bash
git add src/dartwork_mpl/asset/prompt/coding-rules.md \
        src/dartwork_mpl/asset/prompt/general-guide.md \
        src/dartwork_mpl/asset/prompt/layout-guide.md
git commit -m "docs(asset/prompt): mark legacy guides DEPRECATED (deletion in PR 2)"
```

---

## Task 10: Final verification + push

- [ ] **Step 1: Run full test suite**

```bash
uv run python3 -m pytest tests/ -v
```

Expected: every test passes.

- [ ] **Step 2: Run ruff (no new lint errors introduced)**

```bash
uv run ruff check src/dartwork_mpl tests
```

Expected: no new errors. Existing errors (if any) remain unchanged.

- [ ] **Step 3: Verify the lint engine on its own catalog and templates**

```bash
uv run python3 -c "
from pathlib import Path
from dartwork_mpl.lint import lint, format_report

# Confirm no critical issues across templates.
root = Path('src/dartwork_mpl/asset/prompt/05-templates')
total_criticals = 0
for f in sorted(root.glob('*.py')):
    issues = lint(f.read_text())
    crit = [i for i in issues if i.severity == 'critical']
    total_criticals += len(crit)
    if crit:
        print(f'{f.name}: {format_report(crit)}')
assert total_criticals == 0, 'templates must be critical-clean'
print('OK')
"
```

Expected: prints `OK`.

- [ ] **Step 4: Verify `dm.subplots` round-trip**

```bash
uv run python3 - <<'PY'
import matplotlib
matplotlib.use("Agg")
import dartwork_mpl as dm

cases = [
    {"width": "9cm", "aspect": "standard"},
    {"width": "17cm", "aspect": "wide"},
    {"width": dm.col1, "aspect": "square"},
    {"width": dm.cm(11.3), "aspect": 0.5},
]
for kw in cases:
    fig, ax = dm.subplots(**kw)
    w, h = fig.get_size_inches()
    print(kw, "->", round(w, 3), round(h, 3))
PY
```

Expected: four lines printing the resolved (w, h) inches; widths
match the inputs to within 1 mm.

- [ ] **Step 5: Push branch**

```bash
git push -u origin feat/ai-readiness-0.4-core
```

Expected: branch pushed. PR can now be opened against
`feat/ai-readiness-0.4-spec` (which is itself based on `main`).

- [ ] **Step 6: Open PR**

Use the GitHub CLI:

```bash
gh pr create \
  --base feat/ai-readiness-0.4-spec \
  --head feat/ai-readiness-0.4-core \
  --title "feat(0.4): core — width/aspect API + lint module + asset SSOT (M0–M4)" \
  --body "$(cat <<'EOF'
## Summary
- Adds `dm.subplots(width=..., aspect=...)` API; deprecates `figsize=`/`dpi=`/`SW`/`MW`/`TW`/`DW`/`FS_*`.
- Extracts lint engine to `dartwork_mpl/lint.py` backed by `asset/prompt/02-anti-patterns.yaml` (9 rules).
- Reorganizes `asset/prompt/` into the SSOT layout: `00-index`, `01-policy`, `03-recipes`, `05-templates/{12}.py`, `_legacy/`.
- Wires MCP `lint_dartwork_mpl_code` to the new engine (thin delegator).
- Old `coding-rules.md`/`general-guide.md`/`layout-guide.md` get DEPRECATED banners; deletion in PR 2.

## Out of scope (later PRs)
- PR 2: MCP `resources.py` switch from inline templates to file-read; `install_llm_txt` rewrite; `USAGE_GUIDE.md` deletion.
- PR 3: docs/* sweep; drift CI gate; examples migration; 0.4.0 release.

## Test plan
- [ ] `uv run python3 -m pytest tests/` passes
- [ ] `uv run ruff check src/dartwork_mpl tests` clean
- [ ] All 12 templates lint critical-clean
- [ ] `dm.SW`/`dm.FS_SINGLE` access prints DeprecationWarning with replacement guidance
- [ ] `dm.subplots(width="9cm", aspect="standard")` returns (3.54", 2.66")

Spec: `docs/superpowers/specs/2026-04-29-dartwork-mpl-ai-readiness-design.md`
EOF
)"
```

Expected: PR URL printed.

- [ ] **Step 7: Report PR URL to user**

Reply to the user with the PR URL and a one-paragraph summary of what
shipped and what is still owed in PR 2 / PR 3.

---

## Self-Review

**Spec coverage (against `2026-04-29-dartwork-mpl-ai-readiness-design.md`):**

- §3.1 Width: free input, helpers, `col1`/`col2`, lint hook → Tasks 1, 2, 5, 7 ✓
- §3.2 Aspect: 6 tokens → Task 1 (`ASPECT_TOKENS`), Task 7 (`01-policy.md`) ✓
- §3.3 `dm.subplots` signature → Task 4 ✓
- §3.1 deprecation aliases (`SW/MW/TW/DW`, `FS_*`, `WIDTHS`) → Task 3 ✓
- §4.1 SSOT layout `00`/`01`/`02`/`03`/`05`/`_legacy` → Tasks 5, 7, 8 ✓
- §4.2 `02-anti-patterns.yaml` schema (id/severity/detector/message/why/fix_suggestion) → Task 5 ✓
- §5.4 lint module split (`dartwork_mpl/lint.py`) → Tasks 5, 6 ✓
- §10 M0–M4 mapping: M0 (asset reorg) Task 7+8+9, M1 (lint+yaml) Task 5+6, M2 (subplots width/aspect) Task 4, M3 (cm/inch/mm + col1/col2) Tasks 1+2, M4 (deprecation aliases) Task 3 ✓

Items intentionally out of scope (deferred to PR 2 / PR 3 per plan header):
- §4.3 `04-api-reference.md` autogen (PR 3 with regen script)
- §5.1 MCP resource URI rename / new resources (PR 2)
- §5.2 new MCP tools (`search_api`, `agent_post_check`, etc.) (PR 2)
- §5.3 prompt rewrite (`create_plot`, `migrate_legacy_code`) (PR 2)
- §6 `validate_figure` width hardening (PR 3 alongside docs/CI)
- §7 `install_llm_txt` rewrite + `USAGE_GUIDE.md` deletion (PR 2)
- §8 docs/* sweep (PR 3)
- §9 drift CI gate (PR 3)

**Placeholder scan:** None. Every step has either complete code, an
exact command, or a precise edit instruction with line ranges /
anchor strings.

**Type / signature consistency:**
- `parse_width` / `parse_aspect` defined in Task 1, used in Task 4 ✓
- `Rule` / `Issue` defined in Task 5, used in Task 6's tests ✓
- `dm.cm` / `dm.col1` / `dm.col2` defined in Task 2, referenced in
  Task 7 (recipes) and Task 8 (templates) ✓
- Deprecation alias names in Task 3 match the constants in
  `src/dartwork_mpl/constant.py` and the lint rule
  `deprecated-width-token` (Task 5 YAML) ✓

**Behavioral consistency:**
- `figsize=` deprecated in Task 4 (subplots) and forbidden by lint
  rule in Task 5 (yaml) — same rule ID surfaces in the deprecation
  warning ✓
- `tight_layout` deprecated nowhere (it's not on dartwork's API), but
  lint rule `tight-layout` (Task 5) and recipes/templates avoid it ✓
- "Zero-Resize Policy" mentioned only in deprecation context: the
  literal phrase appears in `figure.py` legacy docstring (we replaced
  it in Task 4); CI `zero-resize-mention` rule guards future drift.

---

## Execution

Plan complete and saved to `docs/superpowers/plans/2026-04-29-pr1-core-width-aspect-lint.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
