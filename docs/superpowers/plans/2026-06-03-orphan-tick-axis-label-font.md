# Orphan tick-label axis-label font adoption — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When an axis has no axis label, make its tick labels and offset text adopt the axis label's font (size, weight, family, style), judged independently for x and y.

**Architecture:** A pure core function `_adopt_axis_label_font_core(fig)` in `layout.py` copies the `axis.label` font onto unlabeled axes' visible tick labels + offset text. A public `adopt_axis_label_font(fig)` draws once then calls the core. `simple_layout` calls the core after each convergence-iteration draw (gated by `adopt_orphan_tick_font=True`) so margins reflect the restyled ticks.

**Tech Stack:** matplotlib, pytest, Agg backend.

---

### Task 1: Core + public adoption functions in `layout.py`

**Files:**
- Modify: `src/dartwork_mpl/layout.py` (add functions after `_resolve_gridspec`, ~line 235; update `__all__` at line 16)
- Test: `tests/test_orphan_tick_font.py` (create)

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for orphan tick-label axis-label font adoption."""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl.layout import (
    _adopt_axis_label_font_core,
    adopt_axis_label_font,
    simple_layout,
)


def _x_tick(ax):
    return next(
        t for t in ax.xaxis.get_ticklabels()
        if t.get_visible() and t.get_text().strip()
    )


def _y_tick(ax):
    return next(
        t for t in ax.yaxis.get_ticklabels()
        if t.get_visible() and t.get_text().strip()
    )


class TestAdoptCore:
    def test_unlabeled_x_adopts_axis_label_font(self) -> None:
        """x has no label -> x ticks take xaxis.label size+weight+family+style."""
        dm.style.use("scientific")
        fig, ax = plt.subplots()
        ax.plot(range(10), range(10))
        ax.set_ylabel("y label")  # y labeled, x unlabeled
        fig.canvas.draw()
        _adopt_axis_label_font_core(fig)

        xt, lbl = _x_tick(ax), ax.xaxis.label
        assert xt.get_fontsize() == lbl.get_fontsize()
        assert xt.get_fontweight() == lbl.get_fontweight()
        assert list(xt.get_fontfamily()) == list(lbl.get_fontfamily())
        assert xt.get_fontstyle() == lbl.get_fontstyle()
        plt.close(fig)

    def test_labeled_axis_ticks_untouched(self) -> None:
        """y has a label -> y ticks keep their default (lighter) style."""
        dm.style.use("scientific")
        fig, ax = plt.subplots()
        ax.plot(range(10), range(10))
        ax.set_ylabel("y label")
        fig.canvas.draw()
        before = _y_tick(ax).get_fontweight()
        _adopt_axis_label_font_core(fig)

        yt, lbl = _y_tick(ax), ax.yaxis.label
        assert yt.get_fontweight() == before
        # default tick weight differs from axis-label weight in this preset
        assert lbl.get_fontweight() != before
        plt.close(fig)

    def test_x_and_y_independent(self) -> None:
        """y labeled, x not -> x adopts, y does not."""
        dm.style.use("scientific")
        fig, ax = plt.subplots()
        ax.plot(range(10), range(10))
        ax.set_ylabel("y label")
        fig.canvas.draw()
        y_before = _y_tick(ax).get_fontweight()
        _adopt_axis_label_font_core(fig)

        assert _x_tick(ax).get_fontweight() == ax.xaxis.label.get_fontweight()
        assert _y_tick(ax).get_fontweight() == y_before
        plt.close(fig)

    def test_offset_text_adopts(self) -> None:
        """Unlabeled axis -> ScalarFormatter offset text adopts label font."""
        dm.style.use("scientific")
        fig, ax = plt.subplots()
        ax.plot(range(10), [v * 1e9 for v in range(10)])  # forces 1e9 offset
        fig.canvas.draw()
        _adopt_axis_label_font_core(fig)

        ot = ax.yaxis.get_offset_text()
        assert ot.get_text().strip()  # offset present
        assert ot.get_fontweight() == ax.yaxis.label.get_fontweight()
        plt.close(fig)

    def test_idempotent(self) -> None:
        """Two applications produce identical font."""
        dm.style.use("scientific")
        fig, ax = plt.subplots()
        ax.plot(range(10), range(10))
        fig.canvas.draw()
        _adopt_axis_label_font_core(fig)
        size1, w1 = _x_tick(ax).get_fontsize(), _x_tick(ax).get_fontweight()
        _adopt_axis_label_font_core(fig)
        assert _x_tick(ax).get_fontsize() == size1
        assert _x_tick(ax).get_fontweight() == w1
        plt.close(fig)

    def test_no_ticklabels_no_error(self) -> None:
        """Unlabeled axis with no tick labels -> no error, no-op."""
        dm.style.use("scientific")
        fig, ax = plt.subplots()
        ax.plot(range(10), range(10))
        ax.set_xticks([])
        fig.canvas.draw()
        _adopt_axis_label_font_core(fig)  # must not raise
        plt.close(fig)


class TestAdoptPublic:
    def test_public_draws_and_applies(self) -> None:
        """adopt_axis_label_font draws then applies (no manual draw needed)."""
        dm.style.use("scientific")
        fig, ax = plt.subplots()
        ax.plot(range(10), range(10))
        adopt_axis_label_font(fig)
        assert _x_tick(ax).get_fontweight() == ax.xaxis.label.get_fontweight()
        plt.close(fig)

    def test_empty_figure_no_error(self) -> None:
        fig = plt.figure()
        adopt_axis_label_font(fig)  # no axes -> no-op
        plt.close(fig)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_orphan_tick_font.py -q`
Expected: FAIL — `ImportError: cannot import name '_adopt_axis_label_font_core'`.

- [ ] **Step 3: Implement core + public functions**

In `src/dartwork_mpl/layout.py`, update `__all__` (line 16):

```python
__all__ = [
    "adopt_axis_label_font",
    "auto_layout",
    "get_bounding_box",
    "simple_layout",
    "tight_crop",
]
```

Add after `_resolve_gridspec` (~line 235), before the "main entry point" banner:

```python
# ─────────────────────────────────────────────────────────────────────
# orphan tick-label font adoption
# ─────────────────────────────────────────────────────────────────────

# Font properties copied from an axis label onto its tick labels when
# the axis carries no label of its own. Color is intentionally excluded
# so user-set tick label colors are preserved.


def _copy_label_font(src: Any, dst: Any) -> None:
    """Copy fontsize/weight/family/style from ``src`` Text onto ``dst``."""
    dst.set_fontsize(src.get_fontsize())
    dst.set_fontweight(src.get_fontweight())
    dst.set_fontfamily(src.get_fontfamily())
    dst.set_fontstyle(src.get_fontstyle())


def _adopt_axis_label_font_core(fig: Figure) -> None:
    """Make unlabeled axes' tick labels adopt that axis's label font.

    For each axes and each axis direction (x, y) **independently**: if the
    axis has no axis label, copy the axis-label font (size, weight,
    family, style — *not* color) onto that axis's visible, non-empty tick
    labels (major and minor) and its offset text. Axes that *do* carry a
    label are left untouched, preserving any user tick-font customization.

    Assumes the figure has already been drawn so tick label Text objects
    exist. The change persists across redraws and locator regeneration
    because matplotlib copies the prototype tick's font to new ticks.
    """
    for ax in fig.axes:
        for axis, get_label in (
            (getattr(ax, "xaxis", None), getattr(ax, "get_xlabel", None)),
            (getattr(ax, "yaxis", None), getattr(ax, "get_ylabel", None)),
        ):
            if axis is None or get_label is None:
                continue
            try:
                if get_label().strip():
                    continue  # labeled axis — leave ticks as-is
                label = axis.label
                targets: list[Any] = []
                for minor in (False, True):
                    for tick in axis.get_ticklabels(minor=minor):
                        if tick.get_visible() and tick.get_text().strip():
                            targets.append(tick)
                offset = axis.get_offset_text()
                if offset.get_visible() and offset.get_text().strip():
                    targets.append(offset)
                for tick in targets:
                    _copy_label_font(label, tick)
            except (AttributeError, ValueError):
                # Non-standard axes (polar/3D) — skip defensively.
                continue


def adopt_axis_label_font(fig: Figure) -> None:
    """Draw ``fig`` then apply :func:`_adopt_axis_label_font_core`.

    Use when you are not calling :func:`simple_layout` (which already
    applies this by default via ``adopt_orphan_tick_font=True``) but still
    want unlabeled axes' tick labels to take the axis-label font. A no-op
    on figures without axes.

    Examples
    --------
    >>> import matplotlib.pyplot as plt
    >>> import dartwork_mpl as dm
    >>> dm.style.use("report-kr")
    >>> fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    >>> ax.bar(["1월", "2월"], [3, 5])
    >>> ax.set_ylabel("매출")          # x has no label
    >>> dm.adopt_axis_label_font(fig)  # x tick labels now use the label font
    """
    if not fig.axes:
        return
    fig.canvas.draw()
    _adopt_axis_label_font_core(fig)
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_orphan_tick_font.py -q`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add src/dartwork_mpl/layout.py tests/test_orphan_tick_font.py
git commit -m "feat(layout): orphan tick labels adopt axis-label font

Add _adopt_axis_label_font_core + public adopt_axis_label_font: when an
axis has no label, its tick labels and offset text take the axis-label
font (size/weight/family/style, not color). x and y judged independently."
```

---

### Task 2: Integrate into `simple_layout`

**Files:**
- Modify: `src/dartwork_mpl/layout.py` (`simple_layout` signature ~line 242 + loop ~line 339)
- Test: `tests/test_orphan_tick_font.py` (append class)

- [ ] **Step 1: Append failing tests**

```python
class TestSimpleLayoutIntegration:
    def test_simple_layout_applies_by_default(self) -> None:
        dm.style.use("scientific")
        fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
        ax.plot(range(10), range(10))
        ax.set_ylabel("y label")  # x unlabeled
        simple_layout(fig)
        assert _x_tick(ax).get_fontweight() == ax.xaxis.label.get_fontweight()
        plt.close(fig)

    def test_simple_layout_toggle_off(self) -> None:
        dm.style.use("scientific")
        fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
        ax.plot(range(10), range(10))
        default_weight = _x_tick(ax).get_fontweight()
        simple_layout(fig, adopt_orphan_tick_font=False)
        assert _x_tick(ax).get_fontweight() == default_weight
        plt.close(fig)

    def test_margin_reflects_enlarged_orphan_ticks(self) -> None:
        """A larger axis-label font on an unlabeled axis grows the bottom
        margin because simple_layout measures the restyled ticks."""
        dm.style.use("scientific")

        def build():
            fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
            ax.plot(range(10), range(10))
            ax.xaxis.label.set_fontsize(24)  # empty label, large font
            return fig, ax

        fig_on, ax_on = build()
        simple_layout(fig_on, adopt_orphan_tick_font=True)
        bottom_on = ax_on.get_gridspec().bottom

        fig_off, ax_off = build()
        simple_layout(fig_off, adopt_orphan_tick_font=False)
        bottom_off = ax_off.get_gridspec().bottom

        assert _x_tick(ax_on).get_fontsize() == 24
        # bigger ticks push the axes up -> larger bottom edge fraction
        assert bottom_on > bottom_off + 0.01
        plt.close(fig_on)
        plt.close(fig_off)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_orphan_tick_font.py::TestSimpleLayoutIntegration -q`
Expected: FAIL — `simple_layout() got an unexpected keyword argument 'adopt_orphan_tick_font'`.

- [ ] **Step 3: Add parameter + loop call**

In `simple_layout` signature, add after `use_all_axes: bool = True,`:

```python
    adopt_orphan_tick_font: bool = True,
```

Add to the docstring Parameters section (after `use_all_axes`):

```
    adopt_orphan_tick_font : bool, optional
        If ``True`` (default), tick labels (and offset text) on any axis
        that has no axis label adopt that axis's label font (size,
        weight, family, style; not color). Applied each iteration before
        measurement so margins reflect the restyled ticks. See
        :func:`adopt_axis_label_font`.
```

In the convergence loop, immediately after `fig.canvas.draw()` (line 340) and before `renderer = ...`:

```python
        fig.canvas.draw()
        if adopt_orphan_tick_font:
            _adopt_axis_label_font_core(fig)
        renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_orphan_tick_font.py -q`
Expected: PASS (11 tests).

- [ ] **Step 5: Commit**

```bash
git add src/dartwork_mpl/layout.py tests/test_orphan_tick_font.py
git commit -m "feat(layout): simple_layout applies orphan tick font by default

New adopt_orphan_tick_font=True param. Applied after each iteration's
draw and before extent measurement so margins reflect restyled ticks.
auto_layout inherits via simple_layout."
```

---

### Task 3: Export from package root

**Files:**
- Modify: `src/dartwork_mpl/__init__.py` (line 84 import; `__all__` ~line 180)
- Test: `tests/test_orphan_tick_font.py` (append)

- [ ] **Step 1: Append failing test**

```python
def test_exported_at_package_root() -> None:
    assert hasattr(dm, "adopt_axis_label_font")
    assert "adopt_axis_label_font" in dm.__all__
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_orphan_tick_font.py::test_exported_at_package_root -q`
Expected: FAIL — `AttributeError: module 'dartwork_mpl' has no attribute 'adopt_axis_label_font'`.

- [ ] **Step 3: Add export**

`__init__.py` line 84 — change:

```python
from .layout import auto_layout, get_bounding_box, simple_layout, tight_crop
```
to:
```python
from .layout import (
    adopt_axis_label_font,
    auto_layout,
    get_bounding_box,
    simple_layout,
    tight_crop,
)
```

In `__all__`, add next to the other layout names (after `"auto_layout",`):

```python
    "adopt_axis_label_font",
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_orphan_tick_font.py -q`
Expected: PASS (12 tests).

- [ ] **Step 5: Commit**

```bash
git add src/dartwork_mpl/__init__.py
git commit -m "feat: export dm.adopt_axis_label_font"
```

---

### Task 4: CHANGELOG + version bump

**Files:**
- Modify: `CHANGELOG.md` (add section after `## [Unreleased]`)
- Modify: `pyproject.toml` (`version = "0.4.1"` → `"0.4.2"`)

- [ ] **Step 1: Add CHANGELOG section**

Insert after the `## [Unreleased]` line:

```markdown

## [0.4.2] - 2026-06-03

### Added
- **`dm.adopt_axis_label_font(fig)`** — when an axis carries tick labels
  but no axis label, its tick labels and scientific offset text adopt
  that axis's label font (size, weight, family, style; color preserved).
  x and y are judged independently.

### Changed
- **`simple_layout` (and therefore `auto_layout`) now applies
  `adopt_axis_label_font` by default** via the new
  `adopt_orphan_tick_font=True` parameter. Unlabeled axes' tick labels
  render in the (heavier) axis-label style for correct visual hierarchy.
  Pass `adopt_orphan_tick_font=False` to opt out. The adoption runs
  before margin measurement so layout still fits the restyled ticks.
```

- [ ] **Step 2: Bump version**

`pyproject.toml`: `version = "0.4.1"` → `version = "0.4.2"`.

- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md pyproject.toml
git commit -m "chore(release): 0.4.2 — orphan tick axis-label font adoption"
```

---

### Task 5: Full verification

- [ ] **Step 1: Full suite**

Run: `uv run pytest -q`
Expected: all pass (no regressions in test_layout, test_font, test_validate, test_formatting).

- [ ] **Step 2: Lint + format + types**

Run: `uv run ruff check src/dartwork_mpl/layout.py src/dartwork_mpl/__init__.py tests/test_orphan_tick_font.py`
Run: `uv run ruff format --check src/dartwork_mpl/layout.py tests/test_orphan_tick_font.py`
Run: `uv run mypy src/dartwork_mpl/layout.py`
Expected: clean.

- [ ] **Step 3: Visual smoke (optional)**

Render a report-kr bar chart with a y-label and no x-label; confirm x tick labels are visibly heavier than before.

## Self-Review notes

- Spec coverage: behavior (Task 1), timing/integration (Task 2), API export (Task 3), rollout (Task 4), verification (Task 5). All spec sections mapped.
- Type consistency: `_adopt_axis_label_font_core`, `adopt_axis_label_font`, `_copy_label_font`, `adopt_orphan_tick_font` used consistently across tasks.
- `Any` is already imported in `layout.py` (`from typing import TYPE_CHECKING, Any`).
