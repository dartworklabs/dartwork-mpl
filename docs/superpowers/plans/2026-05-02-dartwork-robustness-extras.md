# dartwork-mpl Robustness Extras Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing robustness suite (44 scenarios merged in PR #108) with 7 robustness areas the original plan did not cover: matplotlib SubFigure containers, `constrained_layout=True` × `auto_layout` coexistence, full 14-preset parametrized matrix, `format_axis_si` numeric boundaries, multibyte currency symbols (₩/€), non-ASCII (Korean) `save_formats` filenames, and triple-`twinx` with offset right spine. Each addition either (a) appends to `tests/robustness/scenarios.py` via the existing registry, or (b) lives in a focused new test file under `tests/`.

**Architecture:** Reuse the existing harness — `RobustnessScenario(name, build, expect_warnings, forbid_warnings, pixel_checks, auto_layout_max_iter)` and `test_robustness_suite.test_robustness_scenario` already exercise build → pre-validate → auto_layout → save → post-validate → pixel-check on every registered scenario, so two of the seven areas (SubFigure, triple-twinx) are pure registry additions. The remaining five live in `tests/test_preset_matrix.py` (14-preset parametrize), `tests/test_formatting.py` (SI boundaries + multibyte currency), `tests/test_io.py` (Korean filename), and `tests/test_layout.py` (constrained_layout coexistence). Source-level fixes are limited: only `format_axis_si` ships a confirmed inconsistency (`x == 0` returns the literal `"0"` regardless of `decimals`) — Task 5 fixes it under TDD. No other source changes are anticipated; if Task 4 or Task 8 surface a real bug, the implementer pauses and reports DONE_WITH_CONCERNS so the controller can dispatch a follow-up fix task.

**Tech Stack:** Python ≥ 3.10, matplotlib ≥ 3.10, numpy, pytest 8, dartwork-mpl 0.4.0 (current `src/dartwork_mpl/` checkout at `main`@`41938a4`). All work happens on a feature branch `feat/robustness-extras` cut from `main`. The pre-existing `tests/conftest.py::_matplotlib_state_isolation` autouse fixture closes figures and resets rcParams between tests, so individual tasks do not need their own teardown logic.

---

## File Structure

Files created (new):

| Path | Responsibility |
|------|----------------|
| `tests/test_preset_matrix.py` | One parametrized test that walks every preset returned by `dm.style.list_styles()`, applies it via `dm.style.use(...)`, builds a trivial chart, saves PNG+PDF, and asserts (a) save succeeds with non-zero bytes, (b) `dm.validate_figure` reports zero warnings on the trivial chart. ~80 lines. |

Files modified (existing):

| Path | Change |
|------|--------|
| `tests/robustness/scenarios.py` | Three new builder functions and three new `RobustnessScenario` registry entries: `subfigures_2x1` (SubFigure container), `constrained_layout_then_auto_layout` (idempotency check), `triple_twinx_offset_spine` (third axis at axes-fraction 1.15). |
| `tests/test_formatting.py` | Two new test classes: `TestFormatAxisSiBoundaries` (parametrized SI boundary cases including the `x == 0` × `decimals` case) and `TestFormatAxisCurrencyMultibyte` (₩ and € symbols, both prefix and suffix positions). |
| `tests/test_layout.py` | Two new test methods on `TestAutoLayoutEdgeCases`: `test_constrained_layout_disables_auto_layout_warning` and `test_constrained_layout_off_then_auto_layout_runs_normally`. |
| `tests/test_io.py` | One new test class `TestSaveFormatsNonAscii` exercising `dm.save_formats` with a Korean filename stem. |
| `src/dartwork_mpl/formatting.py:226-281` | Inside `format_axis_si.si_formatter`, replace the `if x == 0: return "0"` short-circuit with a decimals-aware `f"{0:.{decimals}f}"` so callers get `"0.00"` when `decimals=2` instead of `"0"`. (Task 5.) |
| `CHANGELOG.md` | Append a new "Unreleased" entry summarizing the extension scenarios + the SI-zero fix. (Task 9.) |

Each new test file or registry entry has a single concern. The existing `tests/robustness/test_robustness_suite.py` harness is **not** modified — it iterates over `SCENARIOS` automatically, so growing the suite is purely additive.

---

## Tasks

### Task 1: Cut feature branch + baseline regression run

**Files:**
- No file changes; this task verifies preconditions only.

- [ ] **Step 1: Confirm dartwork-mpl is on `main` and clean**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && git status -sb && git log --oneline -1`
Expected: status reports `## main...origin/main` with no uncommitted changes; HEAD is `41938a4 feat: robustness test suite (44 scenarios, 5 source-level fixes) (#108)`.

- [ ] **Step 2: Cut the feature branch**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && git checkout -b feat/robustness-extras`
Expected: `Switched to a new branch 'feat/robustness-extras'`.

- [ ] **Step 3: Baseline test run**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest -q --no-header`
Expected: All non-xfail tests pass. Capture the pass count (e.g., `XXX passed, Y xfailed`) — the same numbers must hold (plus the new tests this plan adds) at the end of Task 9.

- [ ] **Step 4: Baseline robustness-only run for finer granularity**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest tests/robustness/ -q --no-header`
Expected: 44 scenarios reported (some `xfailed` per `KNOWN_LIMITATIONS`). Note this number for cross-check after Task 8.

---

### Task 2: SubFigure container scenario

**Files:**
- Modify: `tests/robustness/scenarios.py` (append builder + registry entry near the existing geometry scenarios around line 822-840).

- [ ] **Step 1: Add the failing scenario builder**

Open `tests/robustness/scenarios.py`. Locate the section that defines the geometry/inset/colorbar group of builders (the cluster ending in `_build_colorbar_attached_heatmap` followed by the `RobustnessScenario(name="colorbar_attached_heatmap", ...)` registry entry around line 838-841). Immediately **before** the registry list `SCENARIOS` is closed, add the new builder function:

```python
def _build_subfigures_2x1() -> Figure:
    """Two subfigures stacked vertically, each with its own axes,
    title-text, and ylabel.

    matplotlib's ``fig.subfigures()`` partitions a parent figure into
    independent SubFigure children, each with its own GridSpec. This
    scenario verifies that ``dm.validate_figure`` and
    ``dm.auto_layout`` do not crash or report spurious warnings on
    the SubFigure tree, which uses a different artist hierarchy from
    plain ``plt.subplots``.
    """
    fig = dm.figure(width="14cm", aspect="standard")
    sub_top, sub_bot = fig.subfigures(2, 1, hspace=0.05)

    ax_top = sub_top.subplots()
    ax_top.plot([1, 2, 3, 4], [1, 4, 9, 16])
    ax_top.set_ylabel("Top axis (units)")

    ax_bot = sub_bot.subplots()
    ax_bot.bar(["A", "B", "C"], [3, 7, 5])
    ax_bot.set_ylabel("Bottom axis (count)")

    return fig
```

Then add a new entry to the `SCENARIOS` list (place it adjacent to the other geometry scenarios — alphabetical order within the geometry group is fine):

```python
    RobustnessScenario(
        name="subfigures_2x1",
        build=_build_subfigures_2x1,
        # auto_layout uses fig.axes[0].get_gridspec(); SubFigures wrap
        # each child in its own GridSpec, so we accept either zero or
        # the existing INFO/WARN ids — but never any new OVERFLOW.
        forbid_warnings=("OVERFLOW",),
    ),
```

- [ ] **Step 2: Run the new scenario in isolation**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest tests/robustness/test_robustness_suite.py -k subfigures_2x1 -q`
Expected: PASS. If the harness raises (e.g., `auto_layout` crashes on SubFigure children), capture the traceback and report DONE_WITH_CONCERNS — a follow-up fix to `auto_layout` is required before the scenario can pass.

- [ ] **Step 3: Run the entire robustness suite to confirm no global regression**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest tests/robustness/ -q`
Expected: previous pass count + 1 new passing scenario.

- [ ] **Step 4: Commit**

```bash
cd /Users/wonjun/Codes/company-analysis/dartwork-mpl
git add tests/robustness/scenarios.py
git commit -m "test(robustness): add subfigures_2x1 SubFigure container scenario"
```

---

### Task 3: `constrained_layout` × `auto_layout` coexistence

**Files:**
- Modify: `tests/test_layout.py` (append two methods to `TestAutoLayoutEdgeCases`).
- Modify: `tests/robustness/scenarios.py` (append builder + registry entry).

- [ ] **Step 1: Write the failing layout-unit tests**

Open `tests/test_layout.py`. Inside `class TestAutoLayoutEdgeCases:` (currently ends after `test_colorbar_gridspec`), append:

```python
    def test_constrained_layout_off_then_auto_layout_runs_normally(self) -> None:
        """When ``constrained_layout`` is off (the dartwork default), a
        plain ``auto_layout`` call must run to convergence on a chart
        with reasonable labels."""
        fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=False)
        ax.plot([1, 2, 3])
        ax.set_ylabel("Value")
        ax.set_xlabel("Index")
        auto_layout(fig)
        overflow = _measure_overflow(fig)
        assert max(overflow.values()) <= 2.0

    def test_constrained_layout_on_then_auto_layout_no_crash(self) -> None:
        """``constrained_layout=True`` and ``auto_layout`` are normally
        mutually exclusive (constrained-layout owns the margins). The
        dartwork contract is: ``auto_layout`` may not crash when both
        are active, even if it has nothing to optimize. It must return
        cleanly and leave the figure in a renderable state."""
        fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
        ax.plot([1, 2, 3])
        ax.set_ylabel("Value")
        ax.set_xlabel("Index")
        # Must not raise.
        auto_layout(fig)
        # The figure must still render without error.
        fig.canvas.draw()
        plt.close(fig)
```

- [ ] **Step 2: Run the new tests to verify they pass**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest tests/test_layout.py::TestAutoLayoutEdgeCases -q`
Expected: PASS for both new methods. If `test_constrained_layout_on_then_auto_layout_no_crash` fails with an exception originating from `simple_layout`, that is a real bug — report DONE_WITH_CONCERNS with the traceback so the controller can dispatch a fix subtask. Do **not** patch `auto_layout` here without the controller's go-ahead.

- [ ] **Step 3: Add the matching robustness scenario**

Open `tests/robustness/scenarios.py`. Append builder near the geometry cluster:

```python
def _build_constrained_layout_then_auto_layout() -> Figure:
    """A figure constructed with ``constrained_layout=True`` that the
    suite then re-flows via ``auto_layout``. The expectation is that
    auto_layout is a no-op (constrained-layout already balanced the
    margins) and the figure saves cleanly. Verifies dartwork-mpl
    plays nicely with matplotlib's other layout engine."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(5.5, 3.5), constrained_layout=True)
    ax.plot([1, 2, 3, 4], [4, 1, 5, 2])
    ax.set_ylabel("Value (units)")
    ax.set_xlabel("Index")
    return fig
```

Append registry entry next to the other geometry scenarios:

```python
    RobustnessScenario(
        name="constrained_layout_then_auto_layout",
        build=_build_constrained_layout_then_auto_layout,
    ),
```

- [ ] **Step 4: Run the new robustness scenario**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest tests/robustness/test_robustness_suite.py -k constrained_layout_then_auto_layout -q`
Expected: PASS.

- [ ] **Step 5: Run the full layout test module + robustness suite**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest tests/test_layout.py tests/robustness/ -q`
Expected: All previously green tests still pass, plus the two new `test_layout.py` methods and the new `constrained_layout_then_auto_layout` scenario.

- [ ] **Step 6: Commit**

```bash
cd /Users/wonjun/Codes/company-analysis/dartwork-mpl
git add tests/test_layout.py tests/robustness/scenarios.py
git commit -m "test(layout): add constrained_layout × auto_layout coexistence tests + robustness scenario"
```

---

### Task 4: 14-preset parametrized matrix

**Files:**
- Create: `tests/test_preset_matrix.py`

- [ ] **Step 1: Create the new test file**

Write the entire file:

```python
"""Smoke matrix exercising every dartwork-mpl style preset.

For every preset listed in ``dm.style.presets_dict()`` we apply the
preset, build a trivially clean chart (single line plot + axis
labels), save PNG+PDF to a temporary directory, and assert that:

    1. ``dm.style.use(preset)`` does not raise.
    2. ``dm.save_formats`` writes both files with > 1 KB each.
    3. ``dm.validate_figure`` reports no WARNING-level findings on
       the trivially clean chart (INFO findings — e.g. EMPTY_AXES on
       a zero-data axes — are not emitted here because the chart has
       data).

Why a separate file: the existing ``tests/test_style.py`` covers
preset *loading* but not the round-trip through ``save_formats`` and
``validate_figure``. This matrix proves that every advertised preset
actually produces a savable, validation-clean figure end-to-end.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm
from dartwork_mpl.validate import Severity

_MIN_FILE_BYTES: int = 1024


def _all_preset_names() -> list[str]:
    """Return every preset name registered in presets.json."""
    return sorted(dm.style.presets_dict().keys())


@pytest.mark.parametrize("preset", _all_preset_names())
def test_preset_round_trip(preset: str, tmp_path: Path) -> None:
    """Apply ``preset``, build a trivial chart, save PNG+PDF, validate."""
    dm.style.use(preset)

    fig, ax = dm.subplots(width="9cm", aspect="standard")
    ax.plot([1, 2, 3, 4], [1, 4, 9, 16])
    ax.set_ylabel("Value")
    ax.set_xlabel("Index")

    dm.auto_layout(fig)

    out_stem = str(tmp_path / f"preset_{preset}")
    dm.save_formats(fig, out_stem, formats=("png", "pdf"), validate=False)

    png_path = Path(f"{out_stem}.png")
    pdf_path = Path(f"{out_stem}.pdf")
    assert png_path.exists(), f"{preset}: PNG not written"
    assert pdf_path.exists(), f"{preset}: PDF not written"
    assert png_path.stat().st_size > _MIN_FILE_BYTES, (
        f"{preset}: PNG suspiciously small ({png_path.stat().st_size} bytes)"
    )
    assert pdf_path.stat().st_size > _MIN_FILE_BYTES, (
        f"{preset}: PDF suspiciously small ({pdf_path.stat().st_size} bytes)"
    )

    warnings = dm.validate_figure(fig, quiet=True)
    severe = [w for w in warnings if w.severity == Severity.WARNING]
    assert severe == [], (
        f"{preset}: WARNING-level findings on a trivial chart — "
        f"{[(w.check_id, w.message) for w in severe]}"
    )

    plt.close(fig)
```

- [ ] **Step 2: Run the matrix**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest tests/test_preset_matrix.py -q`
Expected: 14 tests collected (one per preset in `presets.json`), all PASS. If a preset fails (e.g., `dark-kr` produces low contrast that triggers a WARNING, or the Korean font is missing on the runner), capture the failure and report DONE_WITH_CONCERNS — the dark-preset case may legitimately need an opt-out via a per-preset skip list, which is a controller decision.

- [ ] **Step 3: Run the entire test suite to confirm no global regression**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest -q`
Expected: previous total + 14 new passes; zero failures.

- [ ] **Step 4: Commit**

```bash
cd /Users/wonjun/Codes/company-analysis/dartwork-mpl
git add tests/test_preset_matrix.py
git commit -m "test(style): add 14-preset round-trip matrix (apply + save + validate)"
```

---

### Task 5: `format_axis_si` boundaries + zero-with-decimals fix (TDD)

**Files:**
- Test: `tests/test_formatting.py` (append a new class `TestFormatAxisSiBoundaries`).
- Modify: `src/dartwork_mpl/formatting.py:226-281` (inside `format_axis_si.si_formatter`).

- [ ] **Step 1: Write the failing tests**

Open `tests/test_formatting.py` and append:

```python
class TestFormatAxisSiBoundaries:
    """Boundary-value tests for ``format_axis_si``.

    The formatter is expected to:
    - Switch SI prefix at exactly 1e3, 1e6, 1e9, 1e12.
    - Honour ``decimals`` for both magnitude and the zero-tick label.
    - Carry the sign for negative values.
    """

    @pytest.mark.parametrize(
        "value,decimals,expected",
        [
            (999, 1, "999.0"),
            (1000, 1, "1.0k"),
            (999_999, 1, "1000.0k"),
            (1_000_000, 1, "1.0M"),
            (1_000_000_000, 1, "1.0G"),
            (1_000_000_000_000, 1, "1.0T"),
            (-1_500_000_000, 1, "-1.5G"),
            (-1500, 0, "-2k"),
        ],
    )
    def test_magnitude_and_sign(
        self, value: float, decimals: int, expected: str
    ) -> None:
        fig, ax = _axes()
        dm.format_axis_si(ax, axis="y", decimals=decimals)
        formatter = ax.yaxis.get_major_formatter()
        # FuncFormatter's call signature is (value, pos).
        assert formatter(value, 0) == expected
        plt.close(fig)

    def test_zero_respects_decimals(self) -> None:
        """``format_axis_si(ax, decimals=2)`` must format the zero
        tick as ``"0.00"`` so it visually aligns with neighbouring
        ticks like ``"1.50k"``. The pre-fix implementation returned
        the literal string ``"0"``."""
        fig, ax = _axes()
        dm.format_axis_si(ax, axis="y", decimals=2)
        formatter = ax.yaxis.get_major_formatter()
        assert formatter(0, 0) == "0.00"
        plt.close(fig)
```

- [ ] **Step 2: Run the new tests — `test_zero_respects_decimals` must FAIL, the parametrized magnitude cases must PASS**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest tests/test_formatting.py::TestFormatAxisSiBoundaries -q`
Expected: 8 magnitude cases PASS, `test_zero_respects_decimals` FAILS with `AssertionError: assert '0' == '0.00'`. This confirms the bug.

If a magnitude case also fails, halt and report DONE_WITH_CONCERNS — the SI prefix table itself has a bug, which is a separate issue that the controller will route to a different fix task.

- [ ] **Step 3: Patch `format_axis_si.si_formatter`**

Open `src/dartwork_mpl/formatting.py`. Locate the inner `si_formatter` function inside `format_axis_si` (around lines 245-274). Replace the current `if x == 0: return "0"` short-circuit:

```python
        if x == 0:
            return "0"
```

with a decimals-aware path:

```python
        if x == 0:
            return f"{0:.{decimals}f}"
```

Leave the rest of `si_formatter` (the `>= 1e12 / 1e9 / 1e6 / 1e3` ladder and the fallback `return f"{x:.{decimals}f}"`) untouched.

- [ ] **Step 4: Re-run the boundary tests — all must PASS now**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest tests/test_formatting.py::TestFormatAxisSiBoundaries -q`
Expected: 9 PASSED (8 parametrized + 1 zero-decimals).

- [ ] **Step 5: Run the full formatting test module to verify no regression**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest tests/test_formatting.py -q`
Expected: previous count + 9 new passes; zero failures.

- [ ] **Step 6: Commit**

```bash
cd /Users/wonjun/Codes/company-analysis/dartwork-mpl
git add src/dartwork_mpl/formatting.py tests/test_formatting.py
git commit -m "fix(formatting): format_axis_si zero tick now honours decimals (\"0.00\" not \"0\")"
```

---

### Task 6: Multibyte currency symbols (₩, €)

**Files:**
- Test: `tests/test_formatting.py` (append a new class `TestFormatAxisCurrencyMultibyte`).

- [ ] **Step 1: Write the new tests**

Open `tests/test_formatting.py` and append:

```python
class TestFormatAxisCurrencyMultibyte:
    """``format_axis_currency`` must accept multibyte Unicode currency
    symbols (₩, €, ¥) without UnicodeEncodeError on PNG save and the
    rendered tick label must literally contain the symbol."""

    @pytest.mark.parametrize(
        "symbol,position,expected_substring",
        [
            ("₩", "prefix", "₩1,000"),
            ("€", "suffix", "1,000€"),
            ("¥", "prefix", "¥1,000"),
        ],
    )
    def test_symbol_renders_in_tick_label(
        self,
        symbol: str,
        position: str,
        expected_substring: str,
        tmp_path,
    ) -> None:
        fig, ax = _axes()
        ax.plot([0, 1, 2], [500, 1000, 1500])
        dm.format_axis_currency(
            ax, axis="y", symbol=symbol, position=position
        )
        formatter = ax.yaxis.get_major_formatter()
        assert formatter(1000, 0) == expected_substring

        # PNG round-trip must not raise UnicodeEncodeError on the
        # backend's text rendering path.
        out_path = tmp_path / f"currency_{ord(symbol):x}.png"
        fig.savefig(out_path)
        assert out_path.exists()
        assert out_path.stat().st_size > 1024
        plt.close(fig)
```

- [ ] **Step 2: Run the new tests**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest tests/test_formatting.py::TestFormatAxisCurrencyMultibyte -q`
Expected: 3 PASSED. If a save fails with a font / Unicode error, the failure indicates a missing font on the runner — report DONE_WITH_CONCERNS so the controller can decide whether to add a font dependency or `pytest.mark.skipif` based on font availability.

- [ ] **Step 3: Run the full formatting test module**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest tests/test_formatting.py -q`
Expected: All passing.

- [ ] **Step 4: Commit**

```bash
cd /Users/wonjun/Codes/company-analysis/dartwork-mpl
git add tests/test_formatting.py
git commit -m "test(formatting): exercise multibyte currency symbols (₩, €, ¥) end-to-end"
```

---

### Task 7: `save_formats` with non-ASCII (Korean) filename

**Files:**
- Test: `tests/test_io.py` (append a new class `TestSaveFormatsNonAscii`).

- [ ] **Step 1: Write the new test**

Open `tests/test_io.py` and append:

```python
class TestSaveFormatsNonAscii:
    """Saving with a non-ASCII (Korean) filename stem must succeed on
    macOS / Linux filesystems with UTF-8 path encoding (the default
    on every CI runner this project supports)."""

    def test_korean_filename_round_trip(self, tmp_path) -> None:
        import dartwork_mpl as dm

        fig, ax = dm.subplots(width="9cm", aspect="standard")
        ax.plot([1, 2, 3], [1, 4, 9])
        ax.set_ylabel("값")
        ax.set_xlabel("순번")

        # The stem contains hangul + a wonsign → both bytes are >= 0x80
        # and exercise the same UTF-8 paths matplotlib uses for save.
        stem = str(tmp_path / "한글_차트_₩")
        dm.save_formats(fig, stem, formats=("png", "pdf"), validate=False)

        png_path = Path(f"{stem}.png")
        pdf_path = Path(f"{stem}.pdf")
        assert png_path.exists(), "PNG not written for non-ASCII stem"
        assert pdf_path.exists(), "PDF not written for non-ASCII stem"
        assert png_path.stat().st_size > 1024
        assert pdf_path.stat().st_size > 1024
        plt.close(fig)
```

If `pathlib.Path` and `plt` are not already imported at the top of `tests/test_io.py`, add `from pathlib import Path` and `import matplotlib.pyplot as plt` to the existing imports — do **not** duplicate them inside the test function.

- [ ] **Step 2: Run the new test**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest tests/test_io.py::TestSaveFormatsNonAscii -q`
Expected: PASS. If it fails on `OSError: [Errno 22]` or similar, the underlying filesystem cannot represent the path; report DONE_WITH_CONCERNS so the controller can add `pytest.mark.skipif(sys.getfilesystemencoding() != "utf-8")`.

- [ ] **Step 3: Run the full I/O test module**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest tests/test_io.py -q`
Expected: All passing.

- [ ] **Step 4: Commit**

```bash
cd /Users/wonjun/Codes/company-analysis/dartwork-mpl
git add tests/test_io.py
git commit -m "test(io): save_formats round-trip with Korean (non-ASCII) filename stem"
```

---

### Task 8: Triple-`twinx` with offset right spine

**Files:**
- Modify: `tests/robustness/scenarios.py` (append builder + registry entry alongside the existing twinx group).

- [ ] **Step 1: Add the failing scenario builder**

Open `tests/robustness/scenarios.py`. Locate the multi-axis cluster (`_build_twinx_basic_short_labels`, `_build_twinx_long_right_label`, `_build_twinx_unit_clash`, `_build_twiny_dual_xaxis`, `_build_triple_axis_parasite` around lines 696-712). After `_build_triple_axis_parasite` add:

```python
def _build_triple_twinx_offset_spine() -> Figure:
    """Three y-axes via two consecutive ``ax.twinx()`` calls plus
    spine offset at axes-fraction 1.15 for the third axis. Verifies
    that the dartwork ``twinx`` monkey-patch (which forces the right
    spine visible) still works on the *third* axis when its right
    spine is repositioned via ``set_position``.

    This guards against a regression where the patch only kicked in
    for the second axis (the immediate twin) and left the third
    axis's right spine invisible after the position change."""
    fig, ax1 = dm.subplots(width="14cm", aspect="standard")
    ax1.plot([1, 2, 3, 4], [1, 4, 9, 16], color="#1f77b4")
    ax1.set_ylabel("Series A")

    ax2 = ax1.twinx()
    ax2.plot([1, 2, 3, 4], [10, 20, 30, 40], color="#ff7f0e")
    ax2.set_ylabel("Series B")

    ax3 = ax1.twinx()
    ax3.spines["right"].set_position(("axes", 1.15))
    ax3.plot([1, 2, 3, 4], [100, 200, 150, 250], color="#2ca02c")
    ax3.set_ylabel("Series C")

    # All three right spines must end up visible (the monkey-patch
    # in dartwork_mpl/__init__.py runs on every twinx() call).
    assert ax2.spines["right"].get_visible(), (
        "ax2 right spine should be visible after twinx() monkey-patch"
    )
    assert ax3.spines["right"].get_visible(), (
        "ax3 right spine should be visible after twinx() monkey-patch"
    )
    return fig
```

Then append the registry entry adjacent to the other twinx scenarios:

```python
    RobustnessScenario(
        name="triple_twinx_offset_spine",
        build=_build_triple_twinx_offset_spine,
        # The offset spine pushes ax3's ylabel ~15% past the axes
        # right edge — auto_layout must absorb it without leaving
        # OVERFLOW behind.
        auto_layout_max_iter=8,
    ),
```

- [ ] **Step 2: Run the scenario in isolation**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest tests/robustness/test_robustness_suite.py -k triple_twinx_offset_spine -q`
Expected: PASS. If `auto_layout` cannot absorb the offset-spine overflow within `max_iter=8`, capture the residual overflow values and report DONE_WITH_CONCERNS — a follow-up tweak to the `auto_layout` BUFFER scaling for axes-fraction-positioned spines will be needed (out of scope for this task).

- [ ] **Step 3: Run the full robustness suite**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest tests/robustness/ -q`
Expected: previous count + 3 new passing scenarios (Tasks 2, 3, 8).

- [ ] **Step 4: Commit**

```bash
cd /Users/wonjun/Codes/company-analysis/dartwork-mpl
git add tests/robustness/scenarios.py
git commit -m "test(robustness): add triple_twinx_offset_spine scenario (3rd axis at axes-frac 1.15)"
```

---

### Task 9: Final regression run + CHANGELOG entry

**Files:**
- Modify: `CHANGELOG.md` (insert a new "Unreleased" section above the prior top entry).

- [ ] **Step 1: Run the entire test suite one last time**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest -q`
Expected: zero failures. Capture the final pass count (previous baseline + Tasks 2–8 additions).

- [ ] **Step 2: Add the changelog entry**

Open `CHANGELOG.md`. Find the current top-most heading. Insert immediately above it:

```markdown
## [Unreleased]

### Added
- **Robustness extras** — three new scenarios in
  `tests/robustness/scenarios.py`: `subfigures_2x1` (matplotlib
  SubFigure container), `constrained_layout_then_auto_layout`
  (constrained-layout × auto-layout coexistence), and
  `triple_twinx_offset_spine` (third y-axis at axes-fraction 1.15
  with offset spine).
- **14-preset round-trip matrix** — new `tests/test_preset_matrix.py`
  applies every preset registered in `presets.json`, builds a clean
  chart, saves PNG+PDF, and asserts validate-clean output for each.
- **`format_axis_si` boundary regression tests** — magnitude / sign
  / decimals coverage for the SI-prefix ladder (1e3, 1e6, 1e9, 1e12)
  in `tests/test_formatting.py`.
- **Multibyte currency symbol tests** — ₩ / € / ¥ exercised
  end-to-end through `format_axis_currency` and PNG save.
- **Non-ASCII filename test** — `dm.save_formats(fig, "한글_차트_₩")`
  round-trip in `tests/test_io.py`.
- **Constrained-layout coexistence tests** — two new methods on
  `tests/test_layout.py::TestAutoLayoutEdgeCases` confirming
  `auto_layout` does not crash when called on a figure built with
  `constrained_layout=True`.

### Fixed
- `format_axis_si` now honours `decimals` for the zero tick: with
  `decimals=2` the zero tick formats as `"0.00"` (previously the
  literal `"0"` regardless of `decimals`, which produced misaligned
  tick label widths next to non-zero values like `"1.50k"`).
```

- [ ] **Step 3: Commit**

```bash
cd /Users/wonjun/Codes/company-analysis/dartwork-mpl
git add CHANGELOG.md
git commit -m "docs(changelog): robustness extras + format_axis_si zero-tick fix"
```

- [ ] **Step 4: Final pass-count audit**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest -q`
Expected: total = (Task 1 baseline) + 14 (preset matrix) + 9 (SI boundaries) + 3 (currency) + 1 (Korean filename) + 2 (constrained-layout unit) + 3 (robustness scenarios) = baseline + 32 new passing tests; zero failures; xfail count unchanged from Task 1.

---

## Execution Notes

- **Branch hygiene.** All work lives on `feat/robustness-extras`. Push and open a PR at the end (out of scope for this plan; the controller decides when).
- **No source-level fixes outside Task 5.** Tasks 2 / 3 / 8 may surface auto_layout limitations on SubFigure / constrained_layout / offset spines. The implementer must report DONE_WITH_CONCERNS in that case rather than patching `auto_layout` ad-hoc — a layout fix needs its own dedicated TDD task that the controller can review independently.
- **No flaky scenarios.** Every new scenario is deterministic by construction (no `numpy.random` calls). If a future scenario adds randomness, seed it with `numpy.random.default_rng(42)` per the existing convention in `_build_datetime_x_5_years_daily`.
- **No `_PROBE_PX` / pixel-helper changes.** The pixel-assertion library (`tests/robustness/pixel_assertions.py`) ships unchanged in this plan. New scenarios that need a different probe (e.g., dark canvases) opt out via `pixel_checks=()`; they do not extend the helper library.
