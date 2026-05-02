# dartwork-mpl Robustness Test Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a comprehensive robustness test suite that exercises `dartwork-mpl` against ~30 known-painful figure scenarios (long tick labels, twinx, extreme margins, NaN/Inf, datetime axes, log/symlog scales, GridSpec colorbars, pie/donut labels, 한글 fonts, etc.), uses pixel-level assertions on the saved PNG to catch silent overflow that the existing artist-based checks miss, and drives concrete improvements in `validate.py` / `validate_fixes.py` / `layout.auto_layout` to make every scenario render correctly.

**Architecture:** Three layers: (1) a `tests/robustness/scenarios.py` registry where each scenario is a small `dataclass` describing how to build a figure + expected validation outcome + render-quality assertions, (2) parametrized pytest harness `tests/robustness/test_robustness_suite.py` that consumes the registry, draws each figure, runs `validate_figure`, runs `auto_layout`, saves to PNG via `save_formats`, and asserts pixel-level invariants (no fully-blank rows on the figure edges where tick labels live, no labels written into the bottom 1% strip of the canvas, etc.), and (3) a small set of source-level fixes in `src/dartwork_mpl/validate.py` + `src/dartwork_mpl/layout.py` + `src/dartwork_mpl/formatting.py` to handle the genuine bugs the suite uncovers (datetime axis blind-spot, symlog scale tick-label overflow, twinx right-spine offset, NaN-only data crash in `_check_overflow`, etc.).

**Tech Stack:** Python 3.11, matplotlib ≥ 3.10, numpy, scipy, pytest 8, dartwork-mpl 0.4.0 (current `src/dartwork_mpl/` checkout). All tests must pass under `uv run pytest tests/robustness/` and must not increase total suite runtime by more than ~25 seconds (45 scenarios × < 0.5 s each).

---

## File Structure

Files created (new):

| Path | Responsibility |
|------|----------------|
| `tests/robustness/__init__.py` | Empty package marker. |
| `tests/robustness/conftest.py` | Adds `Agg` backend, autouse `plt.close("all")` after each scenario, registers a `tmp_image_dir` fixture using pytest's `tmp_path_factory`. |
| `tests/robustness/scenarios.py` | The scenario registry: a `RobustnessScenario` dataclass + a module-level `SCENARIOS: list[RobustnessScenario]` populated by builder functions. ~700 lines. |
| `tests/robustness/pixel_assertions.py` | Tiny library of pixel-level helpers used by the harness (`assert_no_edge_overflow`, `assert_minimum_white_border`, `assert_no_clipped_text`). Uses only matplotlib + numpy; no Pillow dependency. |
| `tests/robustness/test_robustness_suite.py` | The parametrized pytest harness that runs every scenario and applies the assertions declared on it. |
| `tests/robustness/test_pixel_assertions.py` | Unit tests for the pixel helpers themselves (so the harness can trust them). |

Files modified (existing):

| Path | Change |
|------|--------|
| `src/dartwork_mpl/validate.py` | Add `_check_clipped_text` (pixel-coverage check), guard `_check_overflow` against NaN-only data, register `CLIPPED_TEXT` in `validate_figure`. |
| `src/dartwork_mpl/validate_fixes.py` | Add `CLIPPED_TEXT` branch in `get_fix_suggestions`. |
| `src/dartwork_mpl/layout.py` | In `auto_layout`, when `_measure_overflow` reports a side that is wholly populated by datetime/long-string ticks, increase the per-step `BUFFER` for that side (datetime tick labels grow non-linearly with rotation). |
| `src/dartwork_mpl/formatting.py` | `rotate_tick_labels` should set `ha="right"` automatically when rotation ∈ (0, 90); current code leaves alignment at default and produces overflow on dense x-axes. |
| `pyproject.toml` | Add a `robustness` pytest marker (so the suite can be opted out of CI when run on the slowest config: `addopts = ["-v", "--strict-markers", "--tb=short"]` already declares strict markers). |
| `CHANGELOG.md` | New "Unreleased" entry summarizing the suite + each source-level fix. |

The structure follows three rules:
- **One responsibility per file.** `scenarios.py` only declares scenarios; `pixel_assertions.py` only knows about NumPy arrays of pixels; `test_robustness_suite.py` only orchestrates.
- **Co-location.** Both pixel-helper unit tests and the harness live next to the scenarios they exercise (`tests/robustness/`).
- **Existing convention.** dartwork-mpl already groups one feature per `tests/test_*.py`; adding a `tests/robustness/` subfolder mirrors how `valuation` separates `audit/` from `unit/` and keeps the slow scenario suite collectable independently (`pytest tests/robustness/`).

---

## Scenario Catalog (informational)

The 45 scenarios that the harness exercises — covering every robustness corner the user named plus the ones the audit surfaced. Each entry becomes one builder function in `scenarios.py`.

**A. Tick label stress (8)**
1. `long_xtick_labels_no_rotation` — 8 categorical bars, each label 25 chars.
2. `long_xtick_labels_45_rotation` — same, with `rotation=45`.
3. `long_xtick_labels_90_rotation` — same, with `rotation=90`.
4. `long_ytick_labels_horizontal_bar` — 25-char y-tick labels on horizontal bars.
5. `dense_xticks_50_categories` — 50 categorical labels in a 13 cm figure.
6. `unicode_korean_xticks` — 한글 4-letter labels on x-axis (uses `lang-kr` style).
7. `mixed_kr_en_xticks` — alternating "한국전력" / "Apple" labels.
8. `scientific_notation_yticks` — values 1e-9 to 1e9 forcing matplotlib's exponent notation.

**B. Multiple-axis (twinx / twiny) (5)**
9. `twinx_basic_short_labels` — twinx, both sides ≤ 5 chars.
10. `twinx_long_right_label` — twinx with 30-char right ylabel.
11. `twinx_unit_clash` — left axis "온도 (℃)", right axis "Revenue (₩, 조원)".
12. `twiny_dual_xaxis` — `ax.twiny()` with both top & bottom xlabels.
13. `triple_axis_parasite` — `mpl_toolkits.axes_grid1.host_subplot` style (parasite axis).

**C. Margin / layout corner cases (6)**
14. `extreme_left_squeeze` — `subplots_adjust(left=0.05, right=0.30)`.
15. `extreme_right_squeeze` — `subplots_adjust(left=0.70, right=0.95)`.
16. `extreme_bottom_squeeze` — `subplots_adjust(bottom=0.60, top=0.95)`.
17. `outside_axes_annotation` — `xytext=(-0.4, 0.5)` axes-fraction annotation.
18. `axes_fraction_text_below_zero` — text at `y=-0.25` axes fraction.
19. `colorbar_below_axes` — `fig.colorbar(im, ax=ax, orientation='horizontal')`.

**D. Data degeneracies (5)**
20. `nan_only_y` — y vector all `np.nan`.
21. `inf_in_y` — y vector contains `np.inf` and `-np.inf`.
22. `single_point_data` — `ax.plot([5], [5], "o")` (zero-extent x and y).
23. `constant_y` — `ax.plot([1, 2, 3], [7, 7, 7])` (zero-range y, ylim auto-zooms).
24. `negative_log_data` — `ax.set_yscale("log")` with negative values mixed in (matplotlib clips silently, dartwork should warn).

**E. Scale & axis types (4)**
25. `log_y_with_minor_ticks` — `set_yscale("log")` with 5-decade range + minor ticks.
26. `symlog_y_centered_on_zero` — `set_yscale("symlog")` straddling zero.
27. `datetime_x_5_years_daily` — daily timestamps for 5 years on the x-axis.
28. `datetime_x_minutes` — 1-minute resolution for 4 hours.

**F. Saved-output integrity (3)**
29. `tiny_figure_2_5cm` — `width="2.5cm"` (smaller than typical font block).
30. `huge_figure_30cm` — `width="30cm"` (forces tick density to climb).
31. `square_aspect_with_long_legend` — `aspect="square"`, 12-entry legend at `loc="best"`.

**G. Multi-axes layout (4)**
32. `gridspec_2x3_mixed` — 2×3 GridSpec mixing line + bar + heatmap.
33. `inset_axes_overlapping_ticks` — `inset_axes` placed where it covers parent ticks.
34. `subplots_4_with_one_pie` — 2×2 subplot grid, one cell holds a donut chart.
35. `colorbar_attached_heatmap` — `fig.colorbar(im, ax=ax, shrink=0.8)` (already a regression case).

**H. Style / font (4)**
36. `lang_kr_style` — apply `dm.style.use("lang-kr")`.
37. `theme_dark_style` — apply `dm.style.use("theme-dark")` (dark background — dpi/save must remain readable).
38. `theme_minimal_style` — apply `dm.style.use("theme-minimal")` (no spines).
39. `font_minimal_style` — apply `dm.style.use("font-minimal")` (smallest font preset; dense layouts expose underflow).

**I. Annotation density (3)**
40. `bar_chart_value_labels` — value labels on every bar tip (`ax.text` per bar).
41. `crowded_legend_outside` — 20-series legend outside axes via `bbox_to_anchor`.
42. `arrow_annotations_diagonal` — three `ax.annotate(arrowprops=...)` crossing the plot.

**J. Pie/donut variants (3)**
43. `pie_full_default` — regular pie, 5 slices.
44. `donut_thin_correct_pctdistance` — `width=0.15`, `pctdistance=0.925`.
45. `donut_wide_wrong_pctdistance` — `width=0.7`, `pctdistance=0.4` (must trigger PIE_LABEL_OFFSET).

Each scenario carries metadata: builder function, expected validation outcome (`expect_warnings`: list of check_id substrings that **must** appear, `forbid_warnings`: list that **must not** appear after `auto_layout`), and pixel-level assertions to apply (`pixel_checks`: tuple of helper names).

---

## Tasks

### Task 1: Robustness package skeleton + harness conftest

**Files:**
- Create: `dartwork-mpl/tests/robustness/__init__.py`
- Create: `dartwork-mpl/tests/robustness/conftest.py`

- [ ] **Step 1: Create the empty package marker**

```python
# tests/robustness/__init__.py
"""Robustness suite: parametrized scenarios that exercise dartwork-mpl
against painful figure configurations (long ticks, twinx, NaN data,
datetime axes, log/symlog scales, etc.).

Each scenario is declared as a RobustnessScenario in scenarios.py and
consumed by test_robustness_suite.py.
"""
```

- [ ] **Step 2: Create the harness conftest**

```python
# tests/robustness/conftest.py
"""Shared fixtures and matplotlib hygiene for the robustness suite."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pytest

# Force the headless backend so the suite is safe under CI / SSH.
matplotlib.use("Agg")


@pytest.fixture(autouse=True)
def _close_all_figures_after_each_scenario() -> Iterator[None]:
    """Robustness scenarios deliberately stress matplotlib's state. We
    therefore close *every* open figure after each test (the parent
    conftest already resets rcParams)."""
    yield
    plt.close("all")


@pytest.fixture
def tmp_image_dir(tmp_path: Path) -> Path:
    """Per-test directory for saved PNG artefacts."""
    out = tmp_path / "robust_out"
    out.mkdir(parents=True, exist_ok=True)
    return out
```

- [ ] **Step 3: Verify pytest can collect the empty package**

Run: `cd dartwork-mpl && uv run pytest tests/robustness/ --collect-only -q`
Expected: zero errors, zero tests collected (no test files yet).

- [ ] **Step 4: Commit**

```bash
cd dartwork-mpl
git add tests/robustness/__init__.py tests/robustness/conftest.py
git commit -m "test(robustness): scaffold robustness package + conftest"
```

---

### Task 2: Pixel-level assertion helpers (TDD)

**Files:**
- Create: `dartwork-mpl/tests/robustness/pixel_assertions.py`
- Test: `dartwork-mpl/tests/robustness/test_pixel_assertions.py`

- [ ] **Step 1: Write the failing tests for the helpers**

```python
# tests/robustness/test_pixel_assertions.py
"""Unit tests for tests/robustness/pixel_assertions.py.

These helpers operate on the rendered RGBA buffer of a Figure so the
robustness suite can verify *what was actually drawn* rather than
trusting matplotlib's artist-tree bookkeeping.
"""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest

matplotlib.use("Agg")

from tests.robustness.pixel_assertions import (
    PixelAssertionError,
    assert_minimum_white_border,
    assert_no_clipped_text,
    assert_no_edge_overflow,
    figure_to_rgba,
)


class TestFigureToRgba:
    def test_returns_uint8_4channel(self) -> None:
        fig, ax = plt.subplots(figsize=(2, 2))
        ax.plot([1, 2, 3])
        arr = figure_to_rgba(fig)
        assert arr.dtype == np.uint8
        assert arr.ndim == 3
        assert arr.shape[2] == 4
        plt.close(fig)


class TestAssertNoEdgeOverflow:
    def test_clean_figure_passes(self) -> None:
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.plot([1, 2, 3])
        ax.set_ylabel("Y")
        ax.set_xlabel("X")
        fig.subplots_adjust(left=0.20, right=0.95, bottom=0.20, top=0.92)
        # Should not raise.
        assert_no_edge_overflow(fig, side="left", min_white_px=4)
        plt.close(fig)

    def test_text_pushed_against_left_edge_fails(self) -> None:
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.plot([1, 2, 3])
        # Force the plot to start at x=0 of the canvas.
        fig.subplots_adjust(left=0.0, right=0.95, bottom=0.20, top=0.92)
        ax.set_ylabel("very long left label that will be cut")
        with pytest.raises(PixelAssertionError, match="left"):
            assert_no_edge_overflow(fig, side="left", min_white_px=4)
        plt.close(fig)


class TestAssertMinimumWhiteBorder:
    def test_default_white_border_passes(self) -> None:
        fig, ax = plt.subplots(figsize=(3, 3))
        ax.plot([1, 2, 3])
        # Default subplots_adjust leaves > 8 px white border.
        assert_minimum_white_border(fig, min_px=8)
        plt.close(fig)


class TestAssertNoClippedText:
    def test_text_inside_axes_passes(self) -> None:
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.plot([1, 2, 3])
        ax.text(0.5, 0.5, "OK", transform=ax.transAxes)
        # Should not raise.
        assert_no_clipped_text(fig)
        plt.close(fig)

    def test_text_at_negative_axes_fraction_fails(self) -> None:
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.plot([1, 2, 3])
        # Place text at y = -0.4 axes-fraction; tight figure makes it spill.
        ax.text(0.5, -0.4, "spill", transform=ax.transAxes, fontsize=18)
        fig.subplots_adjust(bottom=0.05)
        with pytest.raises(PixelAssertionError):
            assert_no_clipped_text(fig)
        plt.close(fig)
```

- [ ] **Step 2: Run the tests to verify they fail with ImportError**

Run: `cd dartwork-mpl && uv run pytest tests/robustness/test_pixel_assertions.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'tests.robustness.pixel_assertions'` or all tests error during collection.

- [ ] **Step 3: Implement pixel_assertions.py**

```python
# tests/robustness/pixel_assertions.py
"""Pixel-level assertions for the robustness suite.

Why pixels and not artists? matplotlib's `Text.get_window_extent` reports
where matplotlib *thinks* a label sits, but a label can still be clipped
by the figure canvas at save time (e.g. when bbox_inches=None and the
label sits at x=-3 px). The robustness suite therefore inspects the
rendered RGBA buffer directly so we can prove the saved PNG actually
shows the labels.

All assertions are pure functions of a (Figure, parameters) pair and
raise PixelAssertionError on failure with a message identifying the
side and the deficient pixel count.
"""

from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure


class PixelAssertionError(AssertionError):
    """Raised when a rendered figure violates a pixel-level invariant."""


def figure_to_rgba(fig: Figure) -> np.ndarray:
    """Render the figure into an HxWx4 uint8 RGBA array.

    Always forces a draw first so the buffer is up-to-date.
    """
    fig.canvas.draw()
    buf = np.asarray(fig.canvas.buffer_rgba())
    return buf


def _is_blank_strip(strip: np.ndarray, *, tol: int = 6) -> bool:
    """Return True if `strip` is uniformly close to white.

    `strip` must be HxWx4 uint8. We treat a pixel as "blank" when its
    RGB channels are all >= 255 - tol *and* the alpha is the strip's
    maximum (so faint anti-aliased edges still count as blank)."""
    rgb = strip[..., :3]
    return bool(np.all(rgb >= (255 - tol)))


def assert_no_edge_overflow(
    fig: Figure,
    *,
    side: str,
    min_white_px: int = 4,
) -> None:
    """Assert that the saved RGBA buffer has at least `min_white_px`
    blank rows/columns on the named edge.

    `side` ∈ {"left", "right", "top", "bottom"}.
    """
    arr = figure_to_rgba(fig)
    h, w, _ = arr.shape

    if side == "left":
        strip = arr[:, :min_white_px, :]
    elif side == "right":
        strip = arr[:, w - min_white_px :, :]
    elif side == "top":
        strip = arr[:min_white_px, :, :]
    elif side == "bottom":
        strip = arr[h - min_white_px :, :, :]
    else:
        raise ValueError(
            f"side must be left/right/top/bottom, got {side!r}"
        )

    if not _is_blank_strip(strip):
        raise PixelAssertionError(
            f"Figure has non-blank pixels in the {min_white_px}-px "
            f"{side} edge strip — content is clipped or touches the canvas."
        )


def assert_minimum_white_border(fig: Figure, *, min_px: int = 4) -> None:
    """Assert all four edges have at least `min_px` blank pixels."""
    for side in ("left", "right", "top", "bottom"):
        assert_no_edge_overflow(fig, side=side, min_white_px=min_px)


def assert_no_clipped_text(fig: Figure) -> None:
    """Assert that every visible Text artist's window extent lies fully
    inside the figure canvas (with 1-px tolerance).

    This complements `assert_minimum_white_border` by catching cases
    where text spills *partway* off-canvas: the edge strip is no longer
    blank but the text isn't fully blacked out either."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    fig_bbox = fig.bbox
    for ax in fig.axes:
        for txt in (
            *ax.texts,
            ax.title,
            ax.xaxis.label,
            ax.yaxis.label,
            *ax.xaxis.get_ticklabels(),
            *ax.yaxis.get_ticklabels(),
        ):
            if txt is None or not txt.get_visible():
                continue
            if not txt.get_text().strip():
                continue
            try:
                ext = txt.get_window_extent(renderer)
            except (RuntimeError, ValueError, AttributeError):
                continue
            overflow = max(
                fig_bbox.x0 - ext.x0,
                ext.x1 - fig_bbox.x1,
                fig_bbox.y0 - ext.y0,
                ext.y1 - fig_bbox.y1,
            )
            if overflow > 1.0:
                raise PixelAssertionError(
                    f"Text {txt.get_text()[:30]!r} clipped by "
                    f"{overflow:.1f}px"
                )
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `cd dartwork-mpl && uv run pytest tests/robustness/test_pixel_assertions.py -q`
Expected: PASS — all 5 tests pass.

- [ ] **Step 5: Commit**

```bash
cd dartwork-mpl
git add tests/robustness/pixel_assertions.py tests/robustness/test_pixel_assertions.py
git commit -m "test(robustness): pixel-level assertion helpers"
```

---

### Task 3: Scenario registry + minimal harness (TDD with one scenario)

**Files:**
- Create: `dartwork-mpl/tests/robustness/scenarios.py` (minimal — one scenario only)
- Create: `dartwork-mpl/tests/robustness/test_robustness_suite.py`

- [ ] **Step 1: Write the failing harness test**

```python
# tests/robustness/test_robustness_suite.py
"""Parametrized robustness harness.

Each entry in scenarios.SCENARIOS is run through the same pipeline:

    1. Build the figure via the scenario's builder function.
    2. Run dm.validate_figure to collect warnings (quiet mode).
    3. Apply dm.auto_layout to give the layout a chance to converge.
    4. Save to PNG via dm.save_formats(validate=False) so we know the
       saved bytes are well-formed.
    5. Re-run dm.validate_figure on the post-layout figure and check
       that scenario.expect_warnings is satisfied and
       scenario.forbid_warnings is empty.
    6. Apply each scenario.pixel_checks against the post-save figure.

The scenario list is imported, so growing the suite means adding
entries to scenarios.SCENARIOS (no harness changes required).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")

import dartwork_mpl as dm
from tests.robustness import pixel_assertions
from tests.robustness.scenarios import SCENARIOS, RobustnessScenario


def _scenario_id(s: object) -> str:
    """Return the pytest test id for either a bare RobustnessScenario
    or a pytest.param-wrapped one (used in Task 4+ to mark
    expected-to-fail scenarios via pytest.mark.xfail)."""
    if hasattr(s, "values"):  # pytest.param ParameterSet
        return s.values[0].name  # type: ignore[attr-defined,no-any-return]
    return s.name  # type: ignore[attr-defined,no-any-return]


@pytest.mark.parametrize(
    "scenario", SCENARIOS, ids=[_scenario_id(s) for s in SCENARIOS]
)
def test_robustness_scenario(
    scenario: RobustnessScenario, tmp_image_dir: Path
) -> None:
    fig = scenario.build()

    # Stage 1: pre-layout validation.
    pre_warnings = dm.validate_figure(fig, quiet=True)
    pre_ids = {w.check_id for w in pre_warnings}
    for must_have in scenario.expect_warnings:
        assert any(must_have in cid for cid in pre_ids), (
            f"{scenario.name}: expected pre-layout check "
            f"{must_have!r} in {pre_ids!r}"
        )

    # Stage 2: layout convergence.
    dm.auto_layout(fig, max_iter=scenario.auto_layout_max_iter)

    # Stage 3: save round-trip — must not crash, and the file must be
    # non-empty (matplotlib silently writes 0-byte files on certain
    # backend errors).
    out_stem = str(tmp_image_dir / scenario.name)
    dm.save_formats(fig, out_stem, formats=("png",), validate=False)
    out_path = Path(f"{out_stem}.png")
    assert out_path.exists(), f"PNG not written for {scenario.name}"
    assert out_path.stat().st_size > 1024, (
        f"{scenario.name}: PNG suspiciously small "
        f"({out_path.stat().st_size} bytes)"
    )

    # Stage 4: post-layout validation — forbidden warnings must not appear.
    post_warnings = dm.validate_figure(fig, quiet=True)
    post_ids = {w.check_id for w in post_warnings}
    for forbidden in scenario.forbid_warnings:
        assert all(forbidden not in cid for cid in post_ids), (
            f"{scenario.name}: post-layout still has forbidden "
            f"{forbidden!r} in {post_ids!r}"
        )

    # Stage 5: pixel-level assertions registered on the scenario.
    for check_name in scenario.pixel_checks:
        check_fn = getattr(pixel_assertions, check_name)
        check_fn(fig)
```

- [ ] **Step 2: Write the failing scenarios.py with exactly one scenario**

```python
# tests/robustness/scenarios.py
"""Scenario registry for the robustness suite.

Adding a scenario:
    1. Write a builder function returning a fully-configured Figure.
    2. Append a RobustnessScenario instance to SCENARIOS.

Builder functions own their figure size and styling. The harness in
test_robustness_suite.py never modifies the figure between build() and
the first validate_figure call.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import matplotlib.pyplot as plt
import pytest  # noqa: F401  used in xfail markers added in Task 4+
from matplotlib.figure import Figure

import dartwork_mpl as dm


@dataclass(frozen=True)
class RobustnessScenario:
    """One scenario in the robustness suite.

    Parameters
    ----------
    name
        Snake-case identifier used as the pytest test id.
    build
        Callable returning a fully-built Figure.
    expect_warnings
        Substrings of validate_figure check_ids that **must** appear
        before auto_layout runs (i.e. validate is supposed to catch
        the issue this scenario plants).
    forbid_warnings
        Substrings that **must not** appear after auto_layout. Empty
        by default (i.e. layout should clean up cleanly).
    pixel_checks
        Names of callables in pixel_assertions to invoke against the
        post-layout figure (e.g. ("assert_minimum_white_border",)).
    auto_layout_max_iter
        Iteration cap for auto_layout. Most scenarios accept the
        default (5); pathological annotations may need more.
    """

    name: str
    build: Callable[[], Figure]
    expect_warnings: tuple[str, ...] = ()
    forbid_warnings: tuple[str, ...] = ("OVERFLOW",)
    pixel_checks: tuple[str, ...] = ("assert_minimum_white_border",)
    auto_layout_max_iter: int = 5


# ───────────────────────────────────────────────────────
# A. Tick label stress
# ───────────────────────────────────────────────────────


def _build_long_xtick_labels_no_rotation() -> Figure:
    """8 categorical bars, each with a 25-character label, no rotation."""
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    labels = [f"category_label_no_{i:02d}" for i in range(8)]
    ax.bar(labels, [3, 5, 7, 4, 6, 2, 8, 5])
    ax.set_ylabel("Value")
    return fig


SCENARIOS: list[RobustnessScenario] = [
    RobustnessScenario(
        name="long_xtick_labels_no_rotation",
        build=_build_long_xtick_labels_no_rotation,
        expect_warnings=(),  # auto_layout should handle it without warning
        forbid_warnings=("OVERFLOW",),
        pixel_checks=("assert_minimum_white_border",),
    ),
]
```

- [ ] **Step 3: Run the harness against the single scenario**

Run: `cd dartwork-mpl && uv run pytest tests/robustness/test_robustness_suite.py -q`
Expected: PASS — one test passes (the harness wires up correctly and the long-label scenario clears `OVERFLOW` after `auto_layout`).

If it fails because `assert_minimum_white_border` reports < 4 px on the bottom edge, that is a *real* layout bug to be fixed in Task 9 — for now confirm `dm.auto_layout` is being called and the failure points to the bottom edge.

- [ ] **Step 4: Commit**

```bash
cd dartwork-mpl
git add tests/robustness/scenarios.py tests/robustness/test_robustness_suite.py
git commit -m "test(robustness): scenario harness + first long-tick scenario"
```

---

### Task 4: Tick label stress scenarios (A1–A8)

**Files:**
- Modify: `dartwork-mpl/tests/robustness/scenarios.py`

- [ ] **Step 1: Append seven additional builder functions and entries**

Add immediately after `_build_long_xtick_labels_no_rotation` (and *before* the existing `SCENARIOS = [...]` literal — replace the literal at the end):

```python
def _build_long_xtick_labels_45_rotation() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    labels = [f"category_label_45_{i:02d}" for i in range(8)]
    ax.bar(labels, [3, 5, 7, 4, 6, 2, 8, 5])
    ax.set_ylabel("Value")
    dm.rotate_tick_labels(ax, axis="x", rotation=45)
    return fig


def _build_long_xtick_labels_90_rotation() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    labels = [f"category_label_90_{i:02d}" for i in range(8)]
    ax.bar(labels, [3, 5, 7, 4, 6, 2, 8, 5])
    ax.set_ylabel("Value")
    dm.rotate_tick_labels(ax, axis="x", rotation=90)
    return fig


def _build_long_ytick_labels_horizontal_bar() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="wide")
    labels = [f"horizontal_bar_label_{i:02d}" for i in range(6)]
    ax.barh(labels, [3, 5, 7, 4, 6, 2])
    ax.set_xlabel("Value")
    return fig


def _build_dense_xticks_50_categories() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    labels = [f"c{i:02d}" for i in range(50)]
    ax.bar(labels, list(range(50)))
    ax.set_ylabel("Value")
    return fig


def _build_unicode_korean_xticks() -> Figure:
    dm.style.use("lang-kr")
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    labels = ["삼성전자", "한국전력", "포스코", "현대차", "엘지화학"]
    ax.bar(labels, [3, 5, 7, 4, 6])
    ax.set_ylabel("매출 (억원)")
    return fig


def _build_mixed_kr_en_xticks() -> Figure:
    dm.style.use("lang-kr")
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    labels = ["Samsung", "한국전력", "Apple", "현대차", "NVIDIA"]
    ax.bar(labels, [3, 5, 7, 4, 6])
    ax.set_ylabel("Value")
    return fig


def _build_scientific_notation_yticks() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    ax.plot([0, 1, 2], [1e-9, 1e0, 1e9])
    ax.set_yscale("log")
    ax.set_ylabel("Value")
    return fig
```

- [ ] **Step 2: Replace the SCENARIOS literal at the bottom of the file**

```python
SCENARIOS: list[RobustnessScenario] = [
    # A. Tick label stress
    RobustnessScenario(
        name="long_xtick_labels_no_rotation",
        build=_build_long_xtick_labels_no_rotation,
    ),
    RobustnessScenario(
        name="long_xtick_labels_45_rotation",
        build=_build_long_xtick_labels_45_rotation,
    ),
    RobustnessScenario(
        name="long_xtick_labels_90_rotation",
        build=_build_long_xtick_labels_90_rotation,
    ),
    RobustnessScenario(
        name="long_ytick_labels_horizontal_bar",
        build=_build_long_ytick_labels_horizontal_bar,
    ),
    RobustnessScenario(
        name="dense_xticks_50_categories",
        build=_build_dense_xticks_50_categories,
        # 50 ticks in 13 cm guarantees a TICK_CROWD info. After
        # auto_layout we still have 50 ticks; the info is informational
        # and OVERFLOW must remain absent.
        expect_warnings=("TICK_CROWD",),
    ),
    RobustnessScenario(
        name="unicode_korean_xticks",
        build=_build_unicode_korean_xticks,
    ),
    RobustnessScenario(
        name="mixed_kr_en_xticks",
        build=_build_mixed_kr_en_xticks,
    ),
    RobustnessScenario(
        name="scientific_notation_yticks",
        build=_build_scientific_notation_yticks,
    ),
]
```

- [ ] **Step 3: Run the eight scenarios and review failures**

Run: `cd dartwork-mpl && uv run pytest tests/robustness/test_robustness_suite.py -q`
Expected: At least 5 of 8 pass; the rotated-label and dense-tick scenarios likely fail with `assert_minimum_white_border` on the bottom edge — this is the **bug surface** that Task 9 will fix. Record which scenarios fail (the failure list will be referenced in Task 9 verification).

- [ ] **Step 4: Mark currently-failing scenarios with xfail-strict**

For each scenario that failed in Step 3, wrap its `RobustnessScenario` instance in `pytest.param(..., marks=pytest.mark.xfail(strict=True, reason="..."))`. The harness's `_scenario_id` helper from Task 3 already handles both bare and wrapped entries.

Add `import pytest` near the top of `tests/robustness/scenarios.py` (alongside the existing `from dataclasses` import) and edit each failing entry like this:

```python
    pytest.param(
        RobustnessScenario(
            name="long_xtick_labels_45_rotation",
            build=_build_long_xtick_labels_45_rotation,
        ),
        marks=pytest.mark.xfail(
            strict=True, reason="rotated-tick layout bug — fixed in Task 11"
        ),
    ),
```

Use `strict=True` so the marker is removed automatically when the underlying fix lands and the scenario starts passing (XPASS-strict turns red).

- [ ] **Step 5: Run again to confirm xfail behaviour**

Run: `cd dartwork-mpl && uv run pytest tests/robustness/test_robustness_suite.py -q`
Expected: All 8 scenarios show as PASSED (with `xfail` for the marked ones reported as xfailed). No actual failures.

- [ ] **Step 6: Commit**

```bash
cd dartwork-mpl
git add tests/robustness/scenarios.py tests/robustness/test_robustness_suite.py
git commit -m "test(robustness): tick label stress scenarios (A1-A8)"
```

---

### Task 5: Multiple-axis scenarios (B9–B13)

**Files:**
- Modify: `dartwork-mpl/tests/robustness/scenarios.py`

- [ ] **Step 1: Add five builder functions before the SCENARIOS list**

```python
def _build_twinx_basic_short_labels() -> Figure:
    fig, ax1 = dm.subplots(width="13cm", aspect="standard")
    ax1.plot([1, 2, 3], [1, 2, 3], label="L")
    ax1.set_ylabel("L")
    ax2 = ax1.twinx()
    ax2.plot([1, 2, 3], [10, 20, 30], color="red", label="R")
    ax2.set_ylabel("R")
    return fig


def _build_twinx_long_right_label() -> Figure:
    fig, ax1 = dm.subplots(width="13cm", aspect="standard")
    ax1.plot([1, 2, 3], [1, 2, 3])
    ax1.set_ylabel("Left axis")
    ax2 = ax1.twinx()
    ax2.plot([1, 2, 3], [1e6, 2e6, 3e6], color="red")
    ax2.set_ylabel("Right axis with very long label (units in USD millions)")
    return fig


def _build_twinx_unit_clash() -> Figure:
    dm.style.use("lang-kr")
    fig, ax1 = dm.subplots(width="13cm", aspect="standard")
    ax1.plot([1, 2, 3], [-10, 0, 25])
    ax1.set_ylabel("온도 (℃)")
    ax2 = ax1.twinx()
    ax2.plot([1, 2, 3], [1.2e12, 1.5e12, 1.8e12], color="red")
    ax2.set_ylabel("Revenue (₩, 조원)")
    return fig


def _build_twiny_dual_xaxis() -> Figure:
    fig, ax1 = dm.subplots(width="13cm", aspect="standard")
    ax1.plot([1, 2, 3], [1, 2, 3])
    ax1.set_xlabel("Bottom axis: index")
    ax2 = ax1.twiny()
    ax2.set_xlim(2020, 2025)
    ax2.set_xlabel("Top axis: year")
    return fig


def _build_triple_axis_parasite() -> Figure:
    # mpl_toolkits.axes_grid1 is part of matplotlib core, available
    # in 3.10+. The parasite-axes test exercises a three-y-axis layout.
    from mpl_toolkits.axes_grid1 import host_subplot

    fig = plt.figure(figsize=(13 / 2.54, 13 / 2.54 * 0.75))
    host = host_subplot(111)
    par1 = host.twinx()
    par2 = host.twinx()
    # Offset the third axis 60 px to the right.
    par2.spines["right"].set_position(("outward", 60))
    host.plot([1, 2, 3], [1, 2, 3], label="A")
    par1.plot([1, 2, 3], [10, 20, 30], color="red", label="B")
    par2.plot([1, 2, 3], [1e6, 2e6, 3e6], color="green", label="C")
    host.set_ylabel("A")
    par1.set_ylabel("B")
    par2.set_ylabel("C (millions)")
    return fig
```

- [ ] **Step 2: Append the five entries to SCENARIOS**

Insert these immediately after the section A entries:

```python
    # B. Multiple-axis (twinx / twiny)
    RobustnessScenario(
        name="twinx_basic_short_labels",
        build=_build_twinx_basic_short_labels,
    ),
    RobustnessScenario(
        name="twinx_long_right_label",
        build=_build_twinx_long_right_label,
    ),
    RobustnessScenario(
        name="twinx_unit_clash",
        build=_build_twinx_unit_clash,
    ),
    RobustnessScenario(
        name="twiny_dual_xaxis",
        build=_build_twiny_dual_xaxis,
    ),
    RobustnessScenario(
        name="triple_axis_parasite",
        build=_build_triple_axis_parasite,
        # Parasite axes use absolute pixel offsets that auto_layout can't
        # negotiate; the test only verifies "no crash + saveable", so we
        # tolerate residual OVERFLOW.
        forbid_warnings=(),
    ),
```

- [ ] **Step 3: Run section B in isolation**

Run: `cd dartwork-mpl && uv run pytest tests/robustness/test_robustness_suite.py -k "twinx or twiny or triple" -q`
Expected: 4 of 5 PASS; `triple_axis_parasite` likely passes (we set `forbid_warnings=()`). If `twinx_unit_clash` fails on `assert_minimum_white_border` for the right edge, that is the right-spine-label bug to be fixed in Task 9.

- [ ] **Step 4: Wrap any failing entries with `pytest.param(..., marks=pytest.mark.xfail(strict=True, reason="..."))`**

Same pattern as Task 4 Step 4.

- [ ] **Step 5: Commit**

```bash
cd dartwork-mpl
git add tests/robustness/scenarios.py
git commit -m "test(robustness): multiple-axis scenarios (B9-B13)"
```

---

### Task 6: Margin/layout corner cases (C14–C19)

**Files:**
- Modify: `dartwork-mpl/tests/robustness/scenarios.py`

- [ ] **Step 1: Add six builder functions**

```python
def _build_extreme_left_squeeze() -> Figure:
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.barh([0, 1, 2], [1, 2, 3])
    fig.subplots_adjust(left=0.05, right=0.30)
    return fig


def _build_extreme_right_squeeze() -> Figure:
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.barh([0, 1, 2], [1, 2, 3])
    fig.subplots_adjust(left=0.70, right=0.95)
    return fig


def _build_extreme_bottom_squeeze() -> Figure:
    fig, ax = plt.subplots(figsize=(6, 8))
    ax.bar([0, 1, 2], [1, 2, 3])
    fig.subplots_adjust(bottom=0.60, top=0.95)
    return fig


def _build_outside_axes_annotation() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    ax.plot([1, 2, 3])
    ax.annotate(
        "Far left annotation",
        xy=(1, 1),
        xytext=(-0.4, 0.5),
        textcoords="axes fraction",
        fontsize=12,
    )
    return fig


def _build_axes_fraction_text_below_zero() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    ax.plot([1, 2, 3])
    ax.text(0.5, -0.25, "below the axis", transform=ax.transAxes)
    return fig


def _build_colorbar_below_axes() -> Figure:
    import numpy as np

    fig, ax = dm.subplots(width="13cm", aspect="standard")
    im = ax.imshow(np.random.rand(10, 10))
    fig.colorbar(im, ax=ax, orientation="horizontal", shrink=0.8)
    return fig
```

- [ ] **Step 2: Append SCENARIOS entries**

```python
    # C. Margin / layout corner cases
    RobustnessScenario(
        name="extreme_left_squeeze",
        build=_build_extreme_left_squeeze,
        # MARGIN_ASYMMETRY is the whole point — must be flagged before
        # auto_layout. After auto_layout we expect it to be cleaned up.
        expect_warnings=("MARGIN_ASYMMETRY",),
    ),
    RobustnessScenario(
        name="extreme_right_squeeze",
        build=_build_extreme_right_squeeze,
        expect_warnings=("MARGIN_ASYMMETRY",),
    ),
    RobustnessScenario(
        name="extreme_bottom_squeeze",
        build=_build_extreme_bottom_squeeze,
        expect_warnings=("MARGIN_ASYMMETRY",),
    ),
    RobustnessScenario(
        name="outside_axes_annotation",
        build=_build_outside_axes_annotation,
        # Axes-fraction annotations move *with* the subplot; auto_layout
        # may need extra iterations.
        auto_layout_max_iter=15,
    ),
    RobustnessScenario(
        name="axes_fraction_text_below_zero",
        build=_build_axes_fraction_text_below_zero,
        auto_layout_max_iter=15,
    ),
    RobustnessScenario(
        name="colorbar_below_axes",
        build=_build_colorbar_below_axes,
    ),
```

- [ ] **Step 3: Run section C**

Run: `cd dartwork-mpl && uv run pytest tests/robustness/test_robustness_suite.py -k "squeeze or annotation or colorbar_below or below_zero" -q`
Expected: All squeeze scenarios should clear OVERFLOW after auto_layout. If `MARGIN_ASYMMETRY` *also* persists after auto_layout, treat as a bug to be fixed in Task 9 (auto_layout currently re-derives margins from overflow only, not from existing whitespace asymmetry).

- [ ] **Step 4: xfail any persistent failures**

Same pattern.

- [ ] **Step 5: Commit**

```bash
cd dartwork-mpl
git add tests/robustness/scenarios.py
git commit -m "test(robustness): margin/layout corner-case scenarios (C14-C19)"
```

---

### Task 7: Data degeneracies & scale-axis scenarios (D20–E28)

**Files:**
- Modify: `dartwork-mpl/tests/robustness/scenarios.py`

- [ ] **Step 1: Add nine builder functions**

```python
def _build_nan_only_y() -> Figure:
    import numpy as np

    fig, ax = dm.subplots(width="13cm", aspect="standard")
    ax.plot([1, 2, 3], [np.nan, np.nan, np.nan])
    ax.set_ylabel("Value")
    return fig


def _build_inf_in_y() -> Figure:
    import numpy as np

    fig, ax = dm.subplots(width="13cm", aspect="standard")
    ax.plot([1, 2, 3, 4, 5], [1.0, 2.0, np.inf, -np.inf, 5.0])
    ax.set_ylabel("Value")
    return fig


def _build_single_point_data() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    ax.plot([5], [5], "o")
    ax.set_ylabel("Value")
    return fig


def _build_constant_y() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    ax.plot([1, 2, 3, 4, 5], [7, 7, 7, 7, 7])
    ax.set_ylabel("Value")
    return fig


def _build_negative_log_data() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    ax.plot([1, 2, 3, 4, 5], [-2, 1, 10, 100, -50])
    ax.set_yscale("log")
    ax.set_ylabel("Value")
    return fig


def _build_log_y_with_minor_ticks() -> Figure:
    import numpy as np

    fig, ax = dm.subplots(width="13cm", aspect="standard")
    x = np.linspace(1, 5, 100)
    ax.plot(x, 10 ** x)
    ax.set_yscale("log")
    ax.minorticks_on()
    ax.set_ylabel("Value")
    return fig


def _build_symlog_y_centered_on_zero() -> Figure:
    import numpy as np

    fig, ax = dm.subplots(width="13cm", aspect="standard")
    x = np.linspace(-10, 10, 200)
    ax.plot(x, x**3)
    ax.set_yscale("symlog", linthresh=10)
    ax.set_ylabel("Value")
    return fig


def _build_datetime_x_5_years_daily() -> Figure:
    import numpy as np
    import pandas as pd

    fig, ax = dm.subplots(width="13cm", aspect="standard")
    dates = pd.date_range("2021-01-01", "2025-12-31", freq="D")
    ax.plot(dates, np.cumsum(np.random.randn(len(dates))))
    ax.set_ylabel("Value")
    fig.autofmt_xdate()
    return fig


def _build_datetime_x_minutes() -> Figure:
    import numpy as np
    import pandas as pd

    fig, ax = dm.subplots(width="13cm", aspect="standard")
    times = pd.date_range("2026-05-02 09:00", "2026-05-02 13:00", freq="1min")
    ax.plot(times, np.cumsum(np.random.randn(len(times))))
    ax.set_ylabel("Value")
    fig.autofmt_xdate()
    return fig
```

- [ ] **Step 2: Append SCENARIOS entries**

```python
    # D. Data degeneracies
    RobustnessScenario(
        name="nan_only_y",
        build=_build_nan_only_y,
        # No data to plot but axes still has a Line2D artist → not empty.
        # Must not crash anywhere in validate or auto_layout.
        forbid_warnings=("OVERFLOW",),
    ),
    RobustnessScenario(
        name="inf_in_y",
        build=_build_inf_in_y,
    ),
    RobustnessScenario(
        name="single_point_data",
        build=_build_single_point_data,
    ),
    RobustnessScenario(
        name="constant_y",
        build=_build_constant_y,
    ),
    RobustnessScenario(
        name="negative_log_data",
        build=_build_negative_log_data,
        # Negative-on-log is a real warning in matplotlib; the figure
        # still renders (negative samples are dropped). Test only that
        # we don't crash and the saved PNG isn't empty.
    ),
    # E. Scale & axis types
    RobustnessScenario(
        name="log_y_with_minor_ticks",
        build=_build_log_y_with_minor_ticks,
    ),
    RobustnessScenario(
        name="symlog_y_centered_on_zero",
        build=_build_symlog_y_centered_on_zero,
    ),
    RobustnessScenario(
        name="datetime_x_5_years_daily",
        build=_build_datetime_x_5_years_daily,
    ),
    RobustnessScenario(
        name="datetime_x_minutes",
        build=_build_datetime_x_minutes,
    ),
```

- [ ] **Step 3: Run sections D + E**

Run: `cd dartwork-mpl && uv run pytest tests/robustness/test_robustness_suite.py -k "nan_only or inf_in_y or single_point or constant_y or negative_log or log_y or symlog or datetime" -q`
Expected: most pass; `nan_only_y` is the most likely crash site — if `_check_overflow` calls `get_window_extent` on a Line2D backed by all-NaN data, matplotlib raises `RuntimeError` (the existing `with contextlib.suppress(...)` *should* swallow it, but the renderer state may still be corrupt). If it crashes, document the traceback; that is the bug to be fixed in Task 9.

- [ ] **Step 4: xfail crashes / failures**

Same pattern as Task 4 Step 4.

- [ ] **Step 5: Commit**

```bash
cd dartwork-mpl
git add tests/robustness/scenarios.py
git commit -m "test(robustness): data-degeneracy + scale-axis scenarios (D20-E28)"
```

---

### Task 8: Saved-output / multi-axes / style / annotation / pie (F29–J45)

**Files:**
- Modify: `dartwork-mpl/tests/robustness/scenarios.py`

- [ ] **Step 1: Add the remaining 17 builder functions**

```python
# F. Saved-output integrity ─────────────────────────────


def _build_tiny_figure_2_5cm() -> Figure:
    fig, ax = dm.subplots(width="2.5cm", aspect="standard")
    ax.plot([1, 2, 3])
    ax.set_ylabel("Y")
    return fig


def _build_huge_figure_30cm() -> Figure:
    fig, ax = dm.subplots(width="30cm", aspect="standard")
    ax.plot(list(range(50)), list(range(50)))
    ax.set_ylabel("Value")
    return fig


def _build_square_aspect_with_long_legend() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="square")
    for i in range(12):
        ax.plot([0, 1], [i, i + 1], label=f"Series {i:02d} long label")
    ax.legend(loc="best")
    ax.set_ylabel("Y")
    return fig


# G. Multi-axes layout ─────────────────────────────────


def _build_gridspec_2x3_mixed() -> Figure:
    import numpy as np

    fig, axes = dm.subplots(2, 3, width="17cm", aspect="standard")
    axes[0, 0].plot([1, 2, 3])
    axes[0, 1].bar(["a", "b", "c"], [3, 5, 7])
    axes[0, 2].imshow(np.random.rand(10, 10))
    axes[1, 0].scatter(np.random.randn(20), np.random.randn(20))
    axes[1, 1].hist(np.random.randn(100), bins=20)
    axes[1, 2].plot([1, 2, 3], [3, 2, 1])
    for ax in axes.flat:
        ax.set_ylabel("Y")
    return fig


def _build_inset_axes_overlapping_ticks() -> Figure:
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes

    fig, ax = dm.subplots(width="13cm", aspect="standard")
    ax.plot([1, 2, 3, 4, 5], [10, 30, 20, 50, 40])
    ax.set_ylabel("Y")
    inset = inset_axes(ax, width="40%", height="40%", loc="lower left")
    inset.plot([1, 2, 3], [3, 2, 1])
    return fig


def _build_subplots_4_with_one_pie() -> Figure:
    fig, axes = dm.subplots(2, 2, width="13cm", aspect="square")
    axes[0, 0].plot([1, 2, 3])
    axes[0, 0].set_ylabel("Y")
    axes[0, 1].bar(["a", "b"], [3, 5])
    axes[0, 1].set_ylabel("Y")
    axes[1, 0].plot([3, 2, 1])
    axes[1, 0].set_ylabel("Y")
    width = 0.4
    axes[1, 1].pie(
        [40, 30, 20, 10],
        labels=["A", "B", "C", "D"],
        autopct="%.0f%%",
        pctdistance=1.0 - width / 2.0,
        wedgeprops={"width": width},
    )
    return fig


def _build_colorbar_attached_heatmap() -> Figure:
    import numpy as np

    fig, ax = dm.subplots(width="13cm", aspect="standard")
    im = ax.imshow(np.random.rand(10, 10))
    fig.colorbar(im, ax=ax, shrink=0.8)
    return fig


# H. Style / font ──────────────────────────────────────


def _build_lang_kr_style() -> Figure:
    dm.style.use("lang-kr")
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    ax.plot([1, 2, 3], [10, 20, 15])
    ax.set_ylabel("매출 (억원)")
    ax.set_xlabel("연도")
    return fig


def _build_theme_dark_style() -> Figure:
    dm.style.use("theme-dark")
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    ax.plot([1, 2, 3], [10, 20, 15])
    ax.set_ylabel("Y")
    ax.set_xlabel("X")
    return fig


def _build_theme_minimal_style() -> Figure:
    dm.style.use("theme-minimal")
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    ax.plot([1, 2, 3], [10, 20, 15])
    ax.set_ylabel("Y")
    ax.set_xlabel("X")
    return fig


def _build_font_minimal_style() -> Figure:
    dm.style.use("font-minimal")
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    ax.plot([1, 2, 3], [10, 20, 15])
    ax.set_ylabel("Y")
    ax.set_xlabel("X")
    return fig


# I. Annotation density ────────────────────────────────


def _build_bar_chart_value_labels() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    values = [3, 5, 7, 4, 6]
    bars = ax.bar(["a", "b", "c", "d", "e"], values)
    for bar, v in zip(bars, values, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{v}",
            ha="center",
            va="bottom",
        )
    ax.set_ylabel("Value")
    return fig


def _build_crowded_legend_outside() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    for i in range(20):
        ax.plot([0, 1], [i, i + 1], label=f"Series {i:02d}")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
    ax.set_ylabel("Y")
    return fig


def _build_arrow_annotations_diagonal() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    ax.plot([1, 2, 3, 4, 5], [10, 30, 20, 50, 40])
    for x_to, x_from, label in [(2, 1, "first"), (4, 2, "mid"), (5, 4, "end")]:
        ax.annotate(
            label,
            xy=(x_to, 30),
            xytext=(x_from, 50),
            arrowprops={"arrowstyle": "->"},
        )
    ax.set_ylabel("Y")
    return fig


# J. Pie / donut variants ──────────────────────────────


def _build_pie_full_default() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="square")
    ax.pie([40, 30, 20, 7, 3], labels=["A", "B", "C", "D", "E"])
    return fig


def _build_donut_thin_correct_pctdistance() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="square")
    width = 0.15
    ax.pie(
        [50, 30, 20],
        autopct="%.0f%%",
        pctdistance=1.0 - width / 2.0,
        wedgeprops={"width": width},
    )
    return fig


def _build_donut_wide_wrong_pctdistance() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="square")
    ax.pie(
        [50, 30, 20],
        autopct="%.0f%%",
        pctdistance=0.4,
        wedgeprops={"width": 0.7},
    )
    return fig
```

- [ ] **Step 2: Append SCENARIOS entries**

```python
    # F. Saved-output integrity
    RobustnessScenario(
        name="tiny_figure_2_5cm",
        build=_build_tiny_figure_2_5cm,
        # 2.5 cm canvas can't fit ylabel + 4 ticks; expect TICK_CROWD
        # but we still want save_formats to succeed.
        forbid_warnings=(),  # Tolerate any post-layout warnings.
    ),
    RobustnessScenario(
        name="huge_figure_30cm",
        build=_build_huge_figure_30cm,
    ),
    RobustnessScenario(
        name="square_aspect_with_long_legend",
        build=_build_square_aspect_with_long_legend,
        expect_warnings=("LEGEND_OVERFLOW",),
    ),
    # G. Multi-axes layout
    RobustnessScenario(
        name="gridspec_2x3_mixed",
        build=_build_gridspec_2x3_mixed,
    ),
    RobustnessScenario(
        name="inset_axes_overlapping_ticks",
        build=_build_inset_axes_overlapping_ticks,
    ),
    RobustnessScenario(
        name="subplots_4_with_one_pie",
        build=_build_subplots_4_with_one_pie,
    ),
    RobustnessScenario(
        name="colorbar_attached_heatmap",
        build=_build_colorbar_attached_heatmap,
    ),
    # H. Style / font
    RobustnessScenario(
        name="lang_kr_style",
        build=_build_lang_kr_style,
    ),
    RobustnessScenario(
        name="theme_dark_style",
        build=_build_theme_dark_style,
        # Dark theme paints the canvas dark; the white-border helper is
        # designed for a white canvas, so swap the pixel check out.
        pixel_checks=(),
    ),
    RobustnessScenario(
        name="theme_minimal_style",
        build=_build_theme_minimal_style,
    ),
    RobustnessScenario(
        name="font_minimal_style",
        build=_build_font_minimal_style,
    ),
    # I. Annotation density
    RobustnessScenario(
        name="bar_chart_value_labels",
        build=_build_bar_chart_value_labels,
    ),
    RobustnessScenario(
        name="crowded_legend_outside",
        build=_build_crowded_legend_outside,
    ),
    RobustnessScenario(
        name="arrow_annotations_diagonal",
        build=_build_arrow_annotations_diagonal,
    ),
    # J. Pie / donut variants
    RobustnessScenario(
        name="pie_full_default",
        build=_build_pie_full_default,
    ),
    RobustnessScenario(
        name="donut_thin_correct_pctdistance",
        build=_build_donut_thin_correct_pctdistance,
    ),
    RobustnessScenario(
        name="donut_wide_wrong_pctdistance",
        build=_build_donut_wide_wrong_pctdistance,
        expect_warnings=("PIE_LABEL_OFFSET",),
    ),
```

- [ ] **Step 3: Run the entire suite**

Run: `cd dartwork-mpl && uv run pytest tests/robustness/test_robustness_suite.py -q`
Expected: 45 scenarios total, of which a subset is xfailed (those expected to fail until Task 9 source-level fixes land). No actual failures.

- [ ] **Step 4: Commit**

```bash
cd dartwork-mpl
git add tests/robustness/scenarios.py
git commit -m "test(robustness): saved-output, multi-axes, style, annotation, pie scenarios (F29-J45)"
```

---

### Task 9: Fix `_check_overflow` against NaN-only / empty-extent text (TDD)

**Files:**
- Modify: `dartwork-mpl/src/dartwork_mpl/validate.py:67-168` (the `_check_overflow` function)
- Test: `dartwork-mpl/tests/test_validate.py` (add new test class `TestCheckOverflowDegenerateData`)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_validate.py`:

```python
class TestCheckOverflowDegenerateData:
    """Regressions for degenerate input that used to crash _check_overflow."""

    def test_nan_only_y_does_not_crash(self) -> None:
        """A line whose y-values are all NaN must not crash validate.

        matplotlib still creates a Line2D artist, but its bbox is
        degenerate. _check_overflow must skip such artists silently."""
        import numpy as np
        import dartwork_mpl as dm

        fig, ax = dm.subplots(width="13cm", aspect="standard")
        ax.plot([1, 2, 3], [np.nan, np.nan, np.nan])
        ax.set_ylabel("Value")
        # Must return without raising even when the artist tree contains
        # NaN-backed lines whose tightbbox is undefined.
        warnings = validate_figure(fig, checks=("OVERFLOW",), quiet=True)
        # We don't care which warnings fired, only that we didn't crash.
        assert isinstance(warnings, list)
        plt.close(fig)

    def test_empty_extent_text_skipped(self) -> None:
        """A Text artist whose get_window_extent returns a zero-area
        bbox (e.g. text="" but visible) must not produce a spurious
        overflow."""
        import dartwork_mpl as dm

        fig, ax = dm.subplots(width="13cm", aspect="standard")
        ax.plot([1, 2, 3])
        # ax.text with whitespace-only string is filtered already; this
        # test pins behaviour for a degenerate fontsize=0 label.
        ax.set_xlabel("", fontsize=0)
        warnings = validate_figure(fig, checks=("OVERFLOW",), quiet=True)
        assert all(w.check_id != "OVERFLOW" for w in warnings)
        plt.close(fig)
```

- [ ] **Step 2: Run the new tests**

Run: `cd dartwork-mpl && uv run pytest tests/test_validate.py::TestCheckOverflowDegenerateData -q`
Expected: At least one of the two FAILS (most likely `test_nan_only_y_does_not_crash`) with either `RuntimeError` from `get_window_extent` propagating up, or a spurious `OVERFLOW` warning. If both already pass, immediately move to Step 4 — the matplotlib version on this checkout already handles the case and we only needed to pin the contract.

- [ ] **Step 3: Patch `_check_overflow` to defensively skip zero-area extents**

In `src/dartwork_mpl/validate.py`, locate the inner loop in `_check_overflow` (around line 81-100):

```python
            try:
                ext = txt.get_window_extent(renderer)
            except (RuntimeError, ValueError, AttributeError):
                continue
```

Replace with:

```python
            try:
                ext = txt.get_window_extent(renderer)
            except (RuntimeError, ValueError, AttributeError):
                continue
            # Skip zero-area extents — they appear when matplotlib
            # builds a Text for an artist with NaN/Inf-only data or a
            # fontsize=0 label. Such extents are uninformative and the
            # subsequent overflow comparison would compare against
            # garbage coordinates.
            if ext.width <= 0 or ext.height <= 0:
                continue
```

Apply the same `if ext.width <= 0 or ext.height <= 0: continue` guard inside the tick-label loop (around line 132-140) immediately after the `try/except` block.

- [ ] **Step 4: Re-run the new tests**

Run: `cd dartwork-mpl && uv run pytest tests/test_validate.py::TestCheckOverflowDegenerateData -q`
Expected: PASS — both tests pass.

- [ ] **Step 5: Run the full validate test class to confirm no regression**

Run: `cd dartwork-mpl && uv run pytest tests/test_validate.py -q`
Expected: PASS — original 32 plus 2 new = 34 passed.

- [ ] **Step 6: Re-run the robustness suite, lift xfail on `nan_only_y`**

Run: `cd dartwork-mpl && uv run pytest tests/robustness/test_robustness_suite.py::test_robustness_scenario[nan_only_y] -q`
Expected: PASS without xfail. Edit `scenarios.py` to remove the `pytest.mark.xfail` wrapper from the `nan_only_y` entry. Re-run; confirm the scenario remains green.

- [ ] **Step 7: Commit**

```bash
cd dartwork-mpl
git add src/dartwork_mpl/validate.py tests/test_validate.py tests/robustness/scenarios.py
git commit -m "fix(validate): skip zero-area text extents in OVERFLOW (NaN-only data, empty labels)"
```

---

### Task 10: Fix `auto_layout` datetime-tick blow-up (TDD)

**Files:**
- Modify: `dartwork-mpl/src/dartwork_mpl/layout.py:338-441` (the `auto_layout` function — specifically the BUFFER constant and the per-side increment loop)
- Test: `dartwork-mpl/tests/test_layout.py` (add `test_datetime_xaxis_converges_under_max_iter`)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_layout.py`:

```python
class TestAutoLayoutDatetime:
    """Regressions for datetime-tick figures."""

    def test_datetime_xaxis_converges_under_max_iter(self) -> None:
        """A 5-year daily-resolution datetime x-axis must converge in
        ≤ 5 iterations to ≤ 2 px overflow on every side."""
        import numpy as np
        import pandas as pd

        import dartwork_mpl as dm

        fig, ax = dm.subplots(width="13cm", aspect="standard")
        dates = pd.date_range("2021-01-01", "2025-12-31", freq="D")
        rng = np.random.default_rng(42)
        ax.plot(dates, np.cumsum(rng.standard_normal(len(dates))))
        ax.set_ylabel("Value")
        fig.autofmt_xdate()

        auto_layout(fig, max_iter=5)

        overflow = _measure_overflow(fig)
        assert max(overflow.values()) <= 2.0, (
            f"datetime auto_layout did not converge: {overflow}"
        )
        plt.close(fig)
```

- [ ] **Step 2: Run the test**

Run: `cd dartwork-mpl && uv run pytest tests/test_layout.py::TestAutoLayoutDatetime -q`
Expected: FAIL with overflow on the bottom side (datetime ticks are tall when rotated; the existing increment loop adds only `(overflow + tolerance) / dpi + 0.02` inches per round, which under-counts the 45° tick footprint).

- [ ] **Step 3: Patch the increment formula in `auto_layout`**

In `src/dartwork_mpl/layout.py`, locate the increment block (around line 422-436):

```python
        for side, idx in SIDE_MAP.items():
            if overflow[side] > tolerance:
                consec[side] += 1
                # Escalation: multiply increment for persistent overflow
                # (handles axes-relative content that moves with subplot)
                scale = 1.0 + 1.0 * (consec[side] - 1)
                increment = (
                    (overflow[side] + tolerance) / dpi + BUFFER
                ) * scale
                margins[idx] += increment
            else:
                consec[side] = 0
```

Replace with:

```python
        for side, idx in SIDE_MAP.items():
            if overflow[side] > tolerance:
                consec[side] += 1
                # Escalation: multiply increment for persistent overflow
                # (handles axes-relative content that moves with subplot).
                scale = 1.0 + 1.0 * (consec[side] - 1)
                # Datetime / rotated ticks have a tall footprint that
                # the previous formula under-counted because we only
                # add ``overflow + tolerance``. Multiply by 1.5 so we
                # converge in ≤ 3 iterations on the worst observed
                # case (5-year daily timestamps with autofmt_xdate).
                increment = (
                    (overflow[side] * 1.5 + tolerance) / dpi + BUFFER
                ) * scale
                margins[idx] += increment
            else:
                consec[side] = 0
```

- [ ] **Step 4: Re-run the test**

Run: `cd dartwork-mpl && uv run pytest tests/test_layout.py::TestAutoLayoutDatetime -q`
Expected: PASS.

- [ ] **Step 5: Run the full layout test file to confirm no regression**

Run: `cd dartwork-mpl && uv run pytest tests/test_layout.py -q`
Expected: PASS — all original tests + 1 new = unchanged plus 1 passed.

- [ ] **Step 6: Lift xfail from datetime + rotated-label scenarios**

Edit `tests/robustness/scenarios.py`: remove the `pytest.mark.xfail` wrapper from `datetime_x_5_years_daily`, `datetime_x_minutes`, `long_xtick_labels_45_rotation`, `long_xtick_labels_90_rotation`. Run:

`cd dartwork-mpl && uv run pytest tests/robustness/test_robustness_suite.py -k "datetime or 45_rotation or 90_rotation" -q`
Expected: All 4 pass without xfail.

- [ ] **Step 7: Commit**

```bash
cd dartwork-mpl
git add src/dartwork_mpl/layout.py tests/test_layout.py tests/robustness/scenarios.py
git commit -m "fix(layout): scale auto_layout increment for tall rotated/datetime ticks"
```

---

### Task 11: Fix `rotate_tick_labels` default alignment (TDD)

**Files:**
- Modify: `dartwork-mpl/src/dartwork_mpl/formatting.py:284-320` (the `rotate_tick_labels` function)
- Test: `dartwork-mpl/tests/test_formatting.py` (add `TestRotateTickLabelsAlignment`)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_formatting.py`:

```python
class TestRotateTickLabelsAlignment:
    """rotate_tick_labels must set ha='right' for non-trivial rotations
    on the x-axis so labels anchor at their tick — leaving ha='center'
    causes labels to drift left of their tick and overflow the figure."""

    @pytest.mark.parametrize("rotation", [30, 45, 60, 90])
    def test_x_axis_rotation_sets_right_alignment(
        self, rotation: int
    ) -> None:
        fig, ax = _axes()
        ax.set_xticks(np.arange(5))
        ax.set_xticklabels(["A_long", "B_long", "C_long", "D_long", "E_long"])
        dm.rotate_tick_labels(ax, axis="x", rotation=rotation)
        for label in ax.get_xticklabels():
            assert label.get_horizontalalignment() == "right", (
                f"rotation={rotation} should anchor at right, "
                f"got {label.get_horizontalalignment()!r}"
            )
        plt.close(fig)

    def test_x_axis_zero_rotation_leaves_alignment_center(self) -> None:
        fig, ax = _axes()
        ax.set_xticks(np.arange(3))
        ax.set_xticklabels(["a", "b", "c"])
        dm.rotate_tick_labels(ax, axis="x", rotation=0)
        for label in ax.get_xticklabels():
            assert label.get_horizontalalignment() == "center"
        plt.close(fig)
```

- [ ] **Step 2: Run the test**

Run: `cd dartwork-mpl && uv run pytest tests/test_formatting.py::TestRotateTickLabelsAlignment -q`
Expected: FAIL — current `rotate_tick_labels` does not adjust `ha`.

- [ ] **Step 3: Patch `rotate_tick_labels`**

Read `src/dartwork_mpl/formatting.py:284-320` first to confirm the current signature. Then add an `ha=None` parameter and a default-resolution rule:

Locate the function (around line 284 onward) and replace its body to look like this (structure based on the existing signature; preserve any `axis` validation logic that's already there):

```python
def rotate_tick_labels(
    ax: Axes,
    *,
    axis: str = "x",
    rotation: float = 0.0,
    ha: str | None = None,
) -> None:
    """Rotate tick labels on the named axis.

    Parameters
    ----------
    ax : Axes
        Target Axes.
    axis : {"x", "y", "both"}
        Which axis to rotate. Default ``"x"``.
    rotation : float
        Rotation angle in degrees. Default ``0``.
    ha : str | None
        Horizontal alignment override. When ``None`` (default), x-axis
        rotations in ``(0, 90]`` are anchored at ``"right"`` so labels
        sit under their tick rather than drifting left of it; all other
        cases keep ``"center"``.
    """
    if ha is None:
        if axis in ("x", "both") and 0.0 < rotation <= 90.0:
            resolved_ha = "right"
        else:
            resolved_ha = "center"
    else:
        resolved_ha = ha

    if axis in ("x", "both"):
        for label in ax.get_xticklabels():
            label.set_rotation(rotation)
            label.set_horizontalalignment(resolved_ha)
    if axis in ("y", "both"):
        for label in ax.get_yticklabels():
            label.set_rotation(rotation)
            # Y-axis alignment is left untouched — vertical tick labels
            # already anchor sensibly via va.
```

- [ ] **Step 4: Re-run the test**

Run: `cd dartwork-mpl && uv run pytest tests/test_formatting.py -q`
Expected: PASS — original tests + 5 new = all pass.

- [ ] **Step 5: Lift any remaining xfails on rotated tick scenarios that depended on this**

Run: `cd dartwork-mpl && uv run pytest tests/robustness/test_robustness_suite.py -q`
Expected: any rotated-label scenarios that were still flaky now go green; remove their `pytest.mark.xfail` markers.

- [ ] **Step 6: Commit**

```bash
cd dartwork-mpl
git add src/dartwork_mpl/formatting.py tests/test_formatting.py tests/robustness/scenarios.py
git commit -m "fix(formatting): rotate_tick_labels anchors at ha='right' for non-zero x-axis rotation"
```

---

### Task 12: Add `CLIPPED_TEXT` validate check (TDD)

**Files:**
- Modify: `dartwork-mpl/src/dartwork_mpl/validate.py` (add `_check_clipped_text` and register it)
- Modify: `dartwork-mpl/src/dartwork_mpl/validate_fixes.py` (add `CLIPPED_TEXT` branch in `get_fix_suggestions`)
- Test: `dartwork-mpl/tests/test_validate.py` (new `TestCheckClippedText` class)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_validate.py`:

```python
class TestCheckClippedText:
    """CLIPPED_TEXT fires when a Text artist's drawn pixels overlap the
    edge strip of the figure canvas (≤ 1 px from any side)."""

    def test_clipped_xtick_label(self) -> None:
        """Long x-tick labels with a tight figure should be flagged."""
        fig, ax = plt.subplots(figsize=(3, 2))
        ax.bar([0, 1, 2], [1, 2, 3])
        ax.set_xticks([0, 1, 2])
        ax.set_xticklabels(["LongLabel" * 4, "B" * 30, "C" * 30])
        warnings = validate_figure(fig, checks=("CLIPPED_TEXT",), quiet=True)
        clipped = [w for w in warnings if w.check_id == "CLIPPED_TEXT"]
        assert len(clipped) > 0
        plt.close(fig)

    def test_clean_figure_no_clipped(self) -> None:
        """A normally-laid-out figure should not flag CLIPPED_TEXT."""
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot([1, 2, 3])
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        fig.subplots_adjust(left=0.20, right=0.95, bottom=0.18, top=0.92)
        warnings = validate_figure(fig, checks=("CLIPPED_TEXT",), quiet=True)
        clipped = [w for w in warnings if w.check_id == "CLIPPED_TEXT"]
        assert len(clipped) == 0
        plt.close(fig)

    def test_clipped_text_in_default_check_set(self) -> None:
        """CLIPPED_TEXT is registered in the default check set."""
        fig, ax = plt.subplots(figsize=(3, 2))
        ax.bar([0, 1, 2], [1, 2, 3])
        ax.set_xticklabels(["A" * 30, "B" * 30, "C" * 30])
        warnings = validate_figure(fig, quiet=True)  # default checks
        ids = {w.check_id for w in warnings}
        assert "CLIPPED_TEXT" in ids
        plt.close(fig)
```

- [ ] **Step 2: Run — should fail because `CLIPPED_TEXT` is not a registered check_id yet**

Run: `cd dartwork-mpl && uv run pytest tests/test_validate.py::TestCheckClippedText -q`
Expected: FAIL — `validate_figure(checks=("CLIPPED_TEXT",))` returns `[]` since the check id isn't registered.

- [ ] **Step 3: Implement `_check_clipped_text` in `validate.py`**

Add immediately before the `# Public API` divider (around line 522, before `def validate_figure(...)`):

```python
def _check_clipped_text(
    fig: Figure, renderer: RendererBase
) -> list[VisualWarning]:
    """Detect text artists clipped (or about to be clipped) by the canvas.

    Complementary to OVERFLOW: OVERFLOW fires when a label's bounding
    box exits the canvas, but it has a 2 px tolerance and skips ticks
    outside the data range. CLIPPED_TEXT is stricter — it fires when
    *any* visible Text artist's bbox approaches the edge by less than
    1 px, which is what causes saved PNGs to chop labels."""
    warnings: list[VisualWarning] = []
    fig_bbox = fig.bbox
    TIGHT_TOL_PX = 1.0

    seen: set[tuple[str, str]] = set()
    for ax in fig.axes:
        candidates: list[Any] = [
            *ax.texts,
            ax.title,
            ax.xaxis.label,
            ax.yaxis.label,
            *ax.xaxis.get_ticklabels(),
            *ax.yaxis.get_ticklabels(),
        ]
        for txt in candidates:
            if (
                txt is None
                or not txt.get_visible()
                or not txt.get_text().strip()
            ):
                continue
            try:
                ext = txt.get_window_extent(renderer)
            except (RuntimeError, ValueError, AttributeError):
                continue
            if ext.width <= 0 or ext.height <= 0:
                continue
            margin = min(
                ext.x0 - fig_bbox.x0,
                fig_bbox.x1 - ext.x1,
                ext.y0 - fig_bbox.y0,
                fig_bbox.y1 - ext.y1,
            )
            if margin >= TIGHT_TOL_PX:
                continue
            label = txt.get_text()[:30]
            key = (label, str(round(margin, 1)))
            if key in seen:
                continue
            seen.add(key)
            warnings.append(
                VisualWarning(
                    severity=Severity.WARNING,
                    check_id="CLIPPED_TEXT",
                    message=(
                        f"Text {label!r} sits within "
                        f"{TIGHT_TOL_PX:.0f}px of the canvas edge "
                        f"(margin: {margin:.1f}px)"
                    ),
                    detail={
                        "text": txt.get_text(),
                        "margin_px": round(margin, 1),
                    },
                )
            )
    return warnings
```

Then register it in the `all_checks` dict in `validate_figure` (line 553-562):

```python
    all_checks: dict[str, Any] = {
        "OVERFLOW": lambda: _check_overflow(fig, renderer),
        "OVERLAP": lambda: _check_overlap(fig, renderer),
        "LEGEND_OVERFLOW": lambda: _check_legend_overflow(fig, renderer),
        "TICK_CROWD": lambda: _check_tick_crowding(fig, renderer),
        "EMPTY_AXES": lambda: _check_empty_axes(fig),
        "MARGIN_ASYMMETRY": lambda: _check_margin_asymmetry(fig, renderer),
        "PIE_LABEL_OFFSET": lambda: _check_pie_label_offset(fig, renderer),
        "CLIPPED_TEXT": lambda: _check_clipped_text(fig, renderer),
    }
```

Update the `validate_figure` docstring "Supported IDs" line to include `CLIPPED_TEXT`.

- [ ] **Step 4: Add `CLIPPED_TEXT` branch in validate_fixes.py**

In `src/dartwork_mpl/validate_fixes.py`, in `get_fix_suggestions`, add (immediately before the `return suggestions` line):

```python
    elif warning.check_id == "CLIPPED_TEXT":
        suggestions.append("# Run the auto-layout pass\ndm.auto_layout(fig)")
        suggestions.append(
            "# Or rotate the offending label\n"
            "dm.rotate_tick_labels(ax, axis='x', rotation=45)"
        )
        suggestions.append(
            "# Or shrink the font\n"
            "ax.tick_params(axis='both', labelsize=dm.fs(-2))"
        )
```

- [ ] **Step 5: Re-run the new tests**

Run: `cd dartwork-mpl && uv run pytest tests/test_validate.py::TestCheckClippedText -q`
Expected: PASS — all 3 tests pass.

- [ ] **Step 6: Run the full validate test file to confirm no regression**

Run: `cd dartwork-mpl && uv run pytest tests/test_validate.py tests/test_validate_fixes.py -q`
Expected: PASS — original validate tests (now 34 from Task 9) + 3 = 37 passed plus all `test_validate_fixes.py` tests.

- [ ] **Step 7: Commit**

```bash
cd dartwork-mpl
git add src/dartwork_mpl/validate.py src/dartwork_mpl/validate_fixes.py tests/test_validate.py
git commit -m "feat(validate): add CLIPPED_TEXT check + fix suggestions"
```

---

### Task 13: Fix `MARGIN_ASYMMETRY` not cleaned up by `auto_layout`

**Files:**
- Modify: `dartwork-mpl/src/dartwork_mpl/layout.py:338-441` (the `auto_layout` function — add a final symmetry pass)
- Test: `dartwork-mpl/tests/test_layout.py` (add `TestAutoLayoutSymmetry`)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_layout.py`:

```python
class TestAutoLayoutSymmetry:
    """auto_layout should leave both horizontal and vertical margins
    balanced (within MARGIN_ASYMMETRY's 3x ratio threshold)."""

    def test_extreme_left_squeeze_recovers(self) -> None:
        """A figure squeezed into the left 25% of the canvas should be
        re-centred by auto_layout."""
        from dartwork_mpl.validate import validate_figure

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.barh([0, 1, 2], [1, 2, 3])
        ax.set_ylabel("Y")
        ax.set_xlabel("X")
        fig.subplots_adjust(left=0.05, right=0.30)

        auto_layout(fig)

        warnings = validate_figure(
            fig, checks=("MARGIN_ASYMMETRY",), quiet=True
        )
        asym = [w for w in warnings if w.check_id == "MARGIN_ASYMMETRY"]
        assert len(asym) == 0, f"Asymmetry remains: {[w.message for w in asym]}"
        plt.close(fig)
```

- [ ] **Step 2: Run — should fail because `auto_layout` only inflates overflowing sides, never deflates over-padded ones**

Run: `cd dartwork-mpl && uv run pytest tests/test_layout.py::TestAutoLayoutSymmetry -q`
Expected: FAIL — `MARGIN_ASYMMETRY` warning persists.

- [ ] **Step 3: Patch `auto_layout` to call `simple_layout` with balanced margins as a final pass**

In `src/dartwork_mpl/layout.py`, at the end of the `auto_layout` function (immediately before the `if verbose:` block in the `for` loop's `else` branch — actually after the entire `for iteration` loop ends, around line 441), append:

```python
    # Final symmetry pass: if no overflow is left but the layout has
    # asymmetric whitespace (e.g. user passed subplots_adjust before
    # calling us), normalize horizontal and vertical margins by
    # setting them to the *max* of the two sides on each axis. This
    # leaves the figure centred.
    fig.canvas.draw()
    overflow = _measure_overflow(fig)
    if max(overflow.values()) <= tolerance:
        avg_h = (margins[0] + margins[1]) / 2
        avg_v = (margins[2] + margins[3]) / 2
        margins[0] = avg_h
        margins[1] = avg_h
        margins[2] = avg_v
        margins[3] = avg_v
        simple_layout(fig, margins=tuple(margins))  # type: ignore[arg-type]
```

- [ ] **Step 4: Re-run the new test**

Run: `cd dartwork-mpl && uv run pytest tests/test_layout.py::TestAutoLayoutSymmetry -q`
Expected: PASS.

- [ ] **Step 5: Run all layout tests + the squeeze scenarios**

Run: `cd dartwork-mpl && uv run pytest tests/test_layout.py tests/robustness/test_robustness_suite.py -k "layout or squeeze" -q`
Expected: PASS for all. If a squeeze scenario was xfailed in Task 6, remove the marker.

- [ ] **Step 6: Commit**

```bash
cd dartwork-mpl
git add src/dartwork_mpl/layout.py tests/test_layout.py tests/robustness/scenarios.py
git commit -m "fix(layout): final symmetry pass in auto_layout to balance horizontal/vertical margins"
```

---

### Task 14: Lift remaining xfails + tighten the suite

**Files:**
- Modify: `dartwork-mpl/tests/robustness/scenarios.py`

- [ ] **Step 1: List remaining xfails**

Run: `cd dartwork-mpl && uv run pytest tests/robustness/test_robustness_suite.py -q --co | grep -i xfail || true`

Then run the full suite verbosely and capture which scenarios still report xfail:

`cd dartwork-mpl && uv run pytest tests/robustness/test_robustness_suite.py -v 2>&1 | grep -E "(XFAIL|XPASS)"`

For each XPASS (xfail-marked but actually passing now), remove the marker.
For each remaining XFAIL, investigate by running the scenario in isolation: `uv run pytest tests/robustness/test_robustness_suite.py::test_robustness_scenario[<name>] -v --no-header`. Determine whether the failure is a genuine library bug (open a follow-up task) or an over-aggressive assertion (relax `pixel_checks` or `forbid_warnings`).

- [ ] **Step 2: For each remaining genuine bug, document it**

Append to the top of `tests/robustness/scenarios.py` a `KNOWN_LIMITATIONS` constant listing scenario names + a one-line reason:

```python
# Scenarios still wrapped with pytest.mark.xfail because the underlying
# library limitation hasn't been resolved yet. Each entry is a (name,
# reason, owner) tuple. Lift the xfail when the reason is fixed.
KNOWN_LIMITATIONS: tuple[tuple[str, str, str], ...] = (
    # ("scenario_name", "reason", "tracking issue or owner"),
)
```

- [ ] **Step 3: Run the full suite once more and confirm zero unexpected failures**

Run: `cd dartwork-mpl && uv run pytest tests/robustness/test_robustness_suite.py -q`
Expected: 45 collected, all PASSED or XFAILED — zero FAILED, zero ERROR.

- [ ] **Step 4: Run the entire dartwork-mpl test suite to make sure no global regression slipped in**

Run: `cd dartwork-mpl && uv run pytest -q`
Expected: full pass count = previous baseline + new tests; zero new failures. Capture the count for the changelog entry.

- [ ] **Step 5: Commit**

```bash
cd dartwork-mpl
git add tests/robustness/scenarios.py
git commit -m "test(robustness): lift xfails + document any KNOWN_LIMITATIONS"
```

---

### Task 15: Document the new robustness suite

**Files:**
- Modify: `dartwork-mpl/CHANGELOG.md`
- Create: `dartwork-mpl/docs/robustness_suite.md` (only if `docs/` already has Sphinx markdown sources — otherwise skip)

- [ ] **Step 1: Add the changelog entry**

Locate the top of `dartwork-mpl/CHANGELOG.md`. The first non-comment heading is currently the most recent release. Insert immediately above the previous top section:

```markdown
## [Unreleased]

### Added
- **Robustness test suite** under `tests/robustness/` exercising 45
  scenarios (long tick labels, twinx/twiny, NaN/Inf data, datetime
  axes, log/symlog scales, GridSpec colorbars, pie/donut labels, 한글
  fonts, etc.). Each scenario asserts (a) `validate_figure` outcome,
  (b) `auto_layout` convergence, (c) saved-PNG pixel-level invariants.
- **`CLIPPED_TEXT` validation check** that fires when any visible Text
  artist sits within 1 px of the figure canvas edge. Complements
  `OVERFLOW`'s 2 px artist-tree check with a tighter pixel-coverage
  rule, plus fix suggestions in `validate_fixes.get_fix_suggestions`.

### Fixed
- `_check_overflow` no longer crashes (or produces spurious warnings)
  when a `Line2D` is backed by NaN-only data or a `Text` artist has a
  zero-area window extent.
- `auto_layout` now converges in ≤ 5 iterations on figures with
  rotated tick labels and datetime axes (incremental margin step is
  scaled by 1.5 to match the actual tall-tick footprint).
- `auto_layout` runs a final symmetry pass that re-balances horizontal
  and vertical margins so `MARGIN_ASYMMETRY` no longer survives a
  successful overflow-cleanup round.
- `rotate_tick_labels(axis="x", rotation>0)` defaults to `ha="right"`
  so rotated labels anchor at their tick instead of drifting left and
  overflowing the canvas.
```

- [ ] **Step 2: Run the entire suite one final time**

Run: `cd dartwork-mpl && uv run pytest -q`
Expected: Zero failures. Capture the final pass count.

- [ ] **Step 3: Commit**

```bash
cd dartwork-mpl
git add CHANGELOG.md
git commit -m "docs(changelog): robustness suite + validate/layout/formatting fixes"
```

---

## Execution Notes

- **Branch hygiene.** This work belongs in a single feature branch — recommend `feat/robustness-test-suite`.
- **xfail discipline.** Every scenario that gets wrapped in `pytest.mark.xfail(strict=True, ...)` MUST be revisited in Task 14. `strict=True` is non-negotiable: it forces the marker to be lifted as soon as the underlying bug is fixed.
- **No 0-byte PNG.** The harness asserts `out_path.stat().st_size > 1024`; this guards against silent matplotlib backend errors that otherwise produce a 0-byte PNG and an exit code of 0.
- **Theme-dark exception.** `theme_dark_style` paints the canvas dark, so `assert_minimum_white_border` would always fail. The scenario sets `pixel_checks=()` to opt out cleanly. If a future task wants to assert dark-canvas equivalents, add `assert_minimum_dark_border` to `pixel_assertions.py` and route it via the registry — do not special-case the harness.
- **Non-determinism.** `_build_datetime_x_5_years_daily` and friends use `numpy.random.randn`. Always seed with `numpy.random.default_rng(42)` (already done in the layout test, do the same in the scenario builder) so the suite is reproducible.
