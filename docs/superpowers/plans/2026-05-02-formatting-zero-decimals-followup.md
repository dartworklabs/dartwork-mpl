# `format_axis_millions/billions` zero-decimals follow-up

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the `format_axis_si` zero-tick-respects-`decimals` fix (PR #116, commit `964e6d6`) to its sister functions `format_axis_millions` and `format_axis_billions`, both of which still carry the identical `if x == 0: return "0"` short-circuit that ignores the caller-specified `decimals` argument.

**Architecture:** Pure additive change. Two single-line source edits in `src/dartwork_mpl/formatting.py` (lines 107-108 inside `format_axis_millions.millions_formatter` and lines 158-159 inside `format_axis_billions.billions_formatter`). Two new TDD test classes appended to `tests/test_formatting.py` (`TestFormatAxisMillionsZeroDecimals`, `TestFormatAxisBillionsZeroDecimals`) — each parametrizes magnitude/sign cases plus a dedicated zero-respects-decimals case that demonstrates the bug before the fix lands. No new files.

**Tech Stack:** Python ≥ 3.10, matplotlib ≥ 3.10, pytest 8, dartwork-mpl `main`@`7290354`. Branch `fix/formatting-zero-decimals-followup` cut from `main`.

---

## File Structure

| Path | Change |
|------|--------|
| `tests/test_formatting.py` | Append two new test classes after the existing `TestFormatAxisCurrencyMultibyte` (added in PR #116). |
| `src/dartwork_mpl/formatting.py:107-108` | Replace `return "0"` short-circuit in `format_axis_millions.millions_formatter`. |
| `src/dartwork_mpl/formatting.py:158-159` | Replace `return "0"` short-circuit in `format_axis_billions.billions_formatter`. |
| `CHANGELOG.md` | Append a new bullet under the existing `## [Unreleased] / ### Fixed` section noting the parity fix. |

Single-responsibility holds: one file (`formatting.py`) gets two surgical edits, both exact analogues of the `format_axis_si` patch already merged.

---

## Tasks

### Task 1: Cut feature branch + baseline regression

**Files:** None modified (preconditions only).

- [ ] **Step 1: Confirm clean main**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && git status -sb && git log --oneline -1`
Expected: clean tree on `main`, HEAD = `7290354 test(robustness): extras suite + format_axis_si zero-tick fix (#116)`.

- [ ] **Step 2: Cut the feature branch**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && git checkout -b fix/formatting-zero-decimals-followup`

- [ ] **Step 3: Baseline pytest count**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest -q --no-header`
Expected: `1029 passed, 2 skipped, 8 xfailed`. Capture exact summary line.

If `uv run pytest` hangs > 30s, fall back to `uv run python3 -m pytest -q --no-header`.

---

### Task 2: TDD `format_axis_millions` zero-decimals fix

**Files:**
- Test: `tests/test_formatting.py` (append a new class `TestFormatAxisMillionsZeroDecimals`).
- Modify: `src/dartwork_mpl/formatting.py` (line 107-108 inside `format_axis_millions.millions_formatter`).

- [ ] **Step 1: Write the failing tests**

Open `tests/test_formatting.py` and append at the bottom:

```python
class TestFormatAxisMillionsZeroDecimals:
    """Boundary-value tests for ``format_axis_millions``.

    The existing zero-tick short-circuit returns the literal ``"0"``
    regardless of ``decimals``. The patch in this task makes it honour
    ``decimals`` so the zero tick aligns visually with neighbouring
    millions-scale ticks.
    """

    @pytest.mark.parametrize(
        "value,decimals,suffix,expected",
        [
            (1_000_000, 1, "M", "1.0M"),
            (1_500_000, 1, "M", "1.5M"),
            (1_500_000, 0, "M", "2M"),
            (-1_500_000, 1, "M", "-1.5M"),
            (1_000_000, 2, " mn", "1.00 mn"),
        ],
    )
    def test_magnitude_sign_and_suffix(
        self,
        value: float,
        decimals: int,
        suffix: str,
        expected: str,
    ) -> None:
        fig, ax = _axes()
        dm.format_axis_millions(
            ax, axis="y", suffix=suffix, decimals=decimals
        )
        formatter = ax.yaxis.get_major_formatter()
        assert formatter(value, 0) == expected
        plt.close(fig)

    def test_zero_respects_decimals(self) -> None:
        """``format_axis_millions(ax, decimals=2)`` must format the
        zero tick as ``"0.00"`` so it visually aligns with neighbouring
        ticks like ``"1.50M"``. The pre-fix implementation returned
        the literal string ``"0"``."""
        fig, ax = _axes()
        dm.format_axis_millions(ax, axis="y", decimals=2)
        formatter = ax.yaxis.get_major_formatter()
        assert formatter(0, 0) == "0.00"
        plt.close(fig)
```

- [ ] **Step 2: Run new tests — `test_zero_respects_decimals` MUST FAIL**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest tests/test_formatting.py::TestFormatAxisMillionsZeroDecimals -q`
Expected: 5 magnitude cases PASS, `test_zero_respects_decimals` FAILS with `AssertionError: assert '0' == '0.00'`. This confirms the bug.

If a magnitude case fails, halt and report DONE_WITH_CONCERNS — that points to a separate suffix/sign bug not addressed by this task.

- [ ] **Step 3: Patch `format_axis_millions.millions_formatter`**

Open `src/dartwork_mpl/formatting.py`. Locate the inner `millions_formatter` function inside `format_axis_millions` (the `if x == 0: return "0"` short-circuit at lines 107-108). Replace:

```python
        if x == 0:
            return "0"
```

with:

```python
        if x == 0:
            return f"{0:.{decimals}f}"
```

Leave everything else in `millions_formatter` untouched.

- [ ] **Step 4: Re-run boundary tests — all must PASS**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest tests/test_formatting.py::TestFormatAxisMillionsZeroDecimals -q`
Expected: 6 PASSED.

- [ ] **Step 5: Run full formatting test module**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest tests/test_formatting.py -q`
Expected: previous count + 6 new passes; zero failures.

- [ ] **Step 6: Commit**

```bash
cd /Users/wonjun/Codes/company-analysis/dartwork-mpl
git add src/dartwork_mpl/formatting.py tests/test_formatting.py
git commit -m "fix(formatting): format_axis_millions zero tick now honours decimals"
```

---

### Task 3: TDD `format_axis_billions` zero-decimals fix

**Files:**
- Test: `tests/test_formatting.py` (append a new class `TestFormatAxisBillionsZeroDecimals`).
- Modify: `src/dartwork_mpl/formatting.py` (line 158-159 inside `format_axis_billions.billions_formatter`).

- [ ] **Step 1: Write the failing tests**

Open `tests/test_formatting.py` and append at the bottom (after `TestFormatAxisMillionsZeroDecimals` from Task 2):

```python
class TestFormatAxisBillionsZeroDecimals:
    """Boundary-value tests for ``format_axis_billions``.

    Same pattern as ``TestFormatAxisMillionsZeroDecimals`` but applied
    to the billions formatter. The pre-fix zero short-circuit ignores
    ``decimals`` and breaks visual tick alignment for charts that span
    billions-scale values.
    """

    @pytest.mark.parametrize(
        "value,decimals,suffix,expected",
        [
            (1_000_000_000, 1, "B", "1.0B"),
            (1_500_000_000, 1, "B", "1.5B"),
            (1_500_000_000, 0, "B", "2B"),
            (-1_500_000_000, 1, "B", "-1.5B"),
            (1_000_000_000, 2, " bn", "1.00 bn"),
        ],
    )
    def test_magnitude_sign_and_suffix(
        self,
        value: float,
        decimals: int,
        suffix: str,
        expected: str,
    ) -> None:
        fig, ax = _axes()
        dm.format_axis_billions(
            ax, axis="y", suffix=suffix, decimals=decimals
        )
        formatter = ax.yaxis.get_major_formatter()
        assert formatter(value, 0) == expected
        plt.close(fig)

    def test_zero_respects_decimals(self) -> None:
        """``format_axis_billions(ax, decimals=2)`` must format the
        zero tick as ``"0.00"`` so it visually aligns with neighbouring
        ticks like ``"1.50B"``. The pre-fix implementation returned
        the literal string ``"0"``."""
        fig, ax = _axes()
        dm.format_axis_billions(ax, axis="y", decimals=2)
        formatter = ax.yaxis.get_major_formatter()
        assert formatter(0, 0) == "0.00"
        plt.close(fig)
```

- [ ] **Step 2: Run new tests — `test_zero_respects_decimals` MUST FAIL**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest tests/test_formatting.py::TestFormatAxisBillionsZeroDecimals -q`
Expected: 5 magnitude cases PASS, `test_zero_respects_decimals` FAILS with `AssertionError: assert '0' == '0.00'`.

- [ ] **Step 3: Patch `format_axis_billions.billions_formatter`**

In `src/dartwork_mpl/formatting.py`, locate the `billions_formatter` short-circuit (now at lines 158-159 after Task 2's commit didn't shift this region). Replace:

```python
        if x == 0:
            return "0"
```

with:

```python
        if x == 0:
            return f"{0:.{decimals}f}"
```

- [ ] **Step 4: Re-run boundary tests — all must PASS**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest tests/test_formatting.py::TestFormatAxisBillionsZeroDecimals -q`
Expected: 6 PASSED.

- [ ] **Step 5: Run full formatting test module**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest tests/test_formatting.py -q`
Expected: Task 2 baseline + 6 new passes; zero failures.

- [ ] **Step 6: Commit**

```bash
cd /Users/wonjun/Codes/company-analysis/dartwork-mpl
git add src/dartwork_mpl/formatting.py tests/test_formatting.py
git commit -m "fix(formatting): format_axis_billions zero tick now honours decimals"
```

---

### Task 4: Final regression + CHANGELOG

**Files:**
- Modify: `CHANGELOG.md` (extend the existing `## [Unreleased] / ### Fixed` section).

- [ ] **Step 1: Final regression run**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest -q --no-header`
Expected: 1029 baseline + 12 new passes (Task 2: +6, Task 3: +6) = **1041 passed, 2 skipped, 8 xfailed**.

If the count diverges by more than ±1, report DONE_WITH_CONCERNS — investigate before committing CHANGELOG.

- [ ] **Step 2: Append the CHANGELOG bullet**

Open `CHANGELOG.md`. Find the existing `## [Unreleased]` section's `### Fixed` subsection (added by PR #116). Below the `format_axis_si` zero-tick bullet, add a new bullet at the same indentation:

```markdown
- `format_axis_millions` and `format_axis_billions` now honour
  `decimals` for the zero tick (mirroring the `format_axis_si` parity
  fix from PR #116). With `decimals=2` the zero tick formats as
  `"0.00"` instead of the literal `"0"`, restoring tick label width
  parity for charts that include both zero and non-zero values like
  `"1.50M"` / `"1.50B"`.
```

- [ ] **Step 3: Commit**

```bash
cd /Users/wonjun/Codes/company-analysis/dartwork-mpl
git add CHANGELOG.md
git commit -m "docs(changelog): millions/billions zero-tick decimals parity fix"
```

- [ ] **Step 4: Final pass-count audit**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && uv run pytest -q --no-header`
Expected: same `1041 passed, 2 skipped, 8 xfailed`.

- [ ] **Step 5: Sanity check the branch**

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && git log --oneline main..HEAD`
Expected: 3 commits (Task 2 + Task 3 + Task 4 docs).

Run: `cd /Users/wonjun/Codes/company-analysis/dartwork-mpl && git status`
Expected: clean working tree.

---

## Execution Notes

- **Branch hygiene.** Single feature branch `fix/formatting-zero-decimals-followup`. The plan file is committed as part of the same branch (Task 4 includes it via `git add docs/superpowers/plans/2026-05-02-formatting-zero-decimals-followup.md` if untracked).
- **Reuse Task 5 pattern from PR #116.** This plan deliberately mirrors the structure of Task 5 in `2026-05-02-dartwork-robustness-extras.md` so the per-task TDD ritual is identical: parametrized magnitude cases (must pass pre-fix), dedicated zero case (must fail pre-fix), source patch, re-run, commit.
- **No source changes outside the two `if x == 0` short-circuits.** Anything else flagged during implementation is out of scope; report DONE_WITH_CONCERNS rather than expanding the patch.
