# `Length` Class — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `Inches(float)` phantom-type with `Length`, an
opaque Color-pattern wrapper exposing multi-unit views (`.cm`,
`.mm`, `.inch`, `.pt`) as properties. See spec
[`2026-05-06-length-class-design.md`](../specs/2026-05-06-length-class-design.md)
for the rationale and full API contract; see issue
[#152](https://github.com/dartworklabs/dartwork-mpl/issues/152).

**Architecture:** Single-file rewrite of
`src/dartwork_mpl/units.py` (replace `class Inches(float)` with
`class Length`, add `Length.from_pt`, `dm.length(...)` parser,
`dm.pt(...)` wrapper). One-line type changes elsewhere
(`__init__.py` exports, `col1` / `col2` annotations). String swap
across user-facing docs (`Inches` → `Length`). No new files outside
the spec/plan pair already on this branch.

**Tech stack:** Python ≥ 3.10, matplotlib ≥ 3.10, pytest 8,
dartwork-mpl 0.4 (unreleased). Branch `length-class-152` cut from
`main@7ae4b228`.

---

## File Structure

| Path | Change |
|------|--------|
| `src/dartwork_mpl/units.py` | Rewrite. Replace `Inches(float)` with `Length` opaque wrapper (slots, properties, classmethods, arithmetic). Add `_parse_unit_string` shared helper, `pt()` wrapper, `length()` parser wrapper. Update `parse_width` signature to `str \| Length`. Add `pt` to `_KNOWN_WIDTH_UNITS` and `_WIDTH_RE`. |
| `src/dartwork_mpl/__init__.py` | Imports: `Inches` → `Length`, add `length`, `pt`. `__all__`: same swap. `col1: float = cm(9)` → `col1: Length = cm(9)` (same value, new annotation). |
| `tests/test_units.py` | Rewrite. Replace `Inches`-shaped tests with `Length`-shaped tests covering: str init, classmethods, multi-unit views, arithmetic contract (incl. `Length+scalar` rejection, `Length×Length` rejection, `Length/Length` ratio), comparison/hash, `repr`, public surface. |
| `src/dartwork_mpl/mcp/prompts.py:81,153` | `Inches` value → `Length` value (two strings). Add `"24pt"` to listed unit-string examples. |
| `src/dartwork_mpl/mcp/tools.py:417` | `Inches values` → `Length values` (one string). Add `pt` to listed unit examples. |
| `CLAUDE.md:36` | `Inches` value → `Length` value. Add `"24pt"`. |
| `AGENTS.md:36` | Same change as CLAUDE.md (mirrored doc). |
| `README.md:80,156` | Two paragraphs reworked: (a) `Inches` → `Length` + `"24pt"` in figsize description; (b) "Width Helpers" section retitled "Length Helpers", adds `dm.pt(24)` and `dm.length("13cm")` rows, adds Color-style multi-unit view example. |
| `docs/migration.md:26,65,229–242` | Three updates: (a) cm2in row's "returns Inches" → "returns Length"; (b) figsize policy paragraph swap; (c) §"`dm.cm2in` → `dm.cm`" body rewritten — drops `Inches(float)` framing, shows multi-unit views and `dm.pt`/`dm.length`, appends a short note that `Inches` was renamed in-flight before any 0.4 release shipped. |
| `CHANGELOG.md` | Insert a new `### Added` bullet under `## [Unreleased]` describing `dm.Length`. Update the existing `dm.figsize` bullet to say "Length value" + `"24pt"`. |

Single-responsibility holds: `units.py` is the only behavioural
edit; everything else is import-table or string updates.

---

## Tasks

### Task 1: Baseline + working-tree sanity

**Files:** None modified.

- [ ] **Step 1: Confirm clean branch**

  Run: `git status -sb && git log --oneline main..HEAD`
  Expected: clean tree on `length-class-152`, two ahead of main
  (the spec + plan commits). If the tree is dirty, halt — there
  should be no premature implementation changes.

- [ ] **Step 2: Baseline pytest**

  Run: `uv run pytest -q --no-header`
  Capture the exact summary line (`N passed, M skipped, ...`) for
  comparison after each task. Record the baseline here:

  ```
  Baseline: ____ passed, ____ skipped, ____ xfailed
  ```

  If `uv run pytest` hangs > 30 s, fall back to
  `uv run python3 -m pytest -q --no-header`.

---

### Task 2: TDD — `Length` core surface (init, classmethods, views)

**Files:**
- Rewrite: `tests/test_units.py` (replace the file).
- Modify: `src/dartwork_mpl/units.py` (rewrite the class section
  only — keep `parse_aspect`, `figsize`, error-message helpers
  for now).

- [ ] **Step 1: Write the new test module against the not-yet-existing
  surface**

  Replace `tests/test_units.py` wholesale with the test set
  enumerated in §"Test inventory" below (classes
  `TestUnitConstructors`, `TestLengthInit`, `TestLengthViews`,
  `TestLengthRepr`, `TestParseWidth*`, `TestParseAspect*`,
  `TestFigsize`, `TestPublicSurface`).

  Do **not** add `TestLengthArithmetic` or `TestLengthComparison`
  yet — those are wired up in Task 3 so the failure surface stays
  small in this task.

- [ ] **Step 2: Run the new tests — they MUST FAIL**

  Run: `uv run pytest tests/test_units.py -q`
  Expected: most tests fail with `ImportError: cannot import name
  'Length' from 'dartwork_mpl.units'` or similar. This is the
  failure that proves the tests bind to the new surface.

- [ ] **Step 3: Implement `Length` core in `src/dartwork_mpl/units.py`**

  Replace the `class Inches(float):` block (and the `cm` / `inch`
  / `mm` wrapper functions immediately below it) with:

  - A new `class Length:` per spec §2 — `__slots__ = ("_inch",)`,
    `__init__(self, value: str | Length)`, classmethods
    `from_cm` / `from_mm` / `from_inch` / `from_pt`, properties
    `cm` / `mm` / `inch` / `pt`, `__repr__`. Leave arithmetic and
    comparison dunders out for Task 3.
  - A shared `_parse_unit_string(value: str) -> float` helper
    that both `Length.__init__` and `parse_width` call into.
  - A `_validate_positive(value)` guard for the classmethods
    (positive, finite, non-bool numeric).
  - Public wrappers `cm`, `inch`, `mm`, `pt`, `length`.

  Add `pt` to `_KNOWN_WIDTH_UNITS` and to the regex named group
  in `_WIDTH_RE`. Extend `_WIDTH_UNIT_SYNONYMS` with
  `"point"/"points"/"pts" -> "pt"`.

  Update `parse_width`:
  - Signature: `value: str | Length`.
  - First branch: `isinstance(value, Length)` — return `value._inch`
    after the existing finite/positive guard.
  - Reuse `_parse_unit_string` for the str branch.
  - Bare-number `TypeError` message text: replace the `"or an Inches
    value"` phrase with `"or a Length value"`.

  Update `__all__`: drop `"Inches"`, add `"Length"`, `"length"`,
  `"pt"`.

  Update the module docstring header line: `(cm/in/mm)` →
  `(cm/in/mm/pt)`.

- [ ] **Step 4: Run the new test module — Task-2 classes must PASS**

  Run: `uv run pytest tests/test_units.py -q`
  Expected: every class except `TestLengthArithmetic` /
  `TestLengthComparison` (which we have not added yet) passes.
  If the failure shape is anything else, halt and triage before
  adding the deferred test classes in Task 3.

- [ ] **Step 5: Commit (no top-level export changes yet)**

  ```
  git add src/dartwork_mpl/units.py tests/test_units.py
  git commit -m "refactor(units): introduce Length class (Color-pattern wrapper)"
  ```

---

### Task 3: Arithmetic, comparison, hashing — TDD

**Files:**
- Modify: `tests/test_units.py` (append `TestLengthArithmetic`,
  `TestLengthComparison`).
- Modify: `src/dartwork_mpl/units.py` (add the arithmetic +
  comparison dunders to `Length`).

- [ ] **Step 1: Append the deferred test classes**

  Append the `TestLengthArithmetic` and `TestLengthComparison`
  bodies from §"Test inventory" to `tests/test_units.py`.

- [ ] **Step 2: Run — arithmetic tests MUST FAIL**

  Run: `uv run pytest tests/test_units.py::TestLengthArithmetic
  tests/test_units.py::TestLengthComparison -q`
  Expected: every case fails (TypeError on `Length * 2`,
  unsupported operand on `cm(9) - cm(2)`, etc.) since the dunders
  do not yet exist.

- [ ] **Step 3: Implement the dunders per spec §2.5**

  Add to `Length` (after the property block):

  - `__add__` / `__radd__` / `__sub__` / `__rsub__` — operate on
    two `Length` operands; return `NotImplemented` against scalars
    so Python raises `TypeError` from the caller side rather than
    silently producing a unit-less number.
  - `__mul__` / `__rmul__` — accept `int` / `float` (not `bool`),
    return `Length`; reject `Length * Length` with
    `NotImplemented` (becomes `TypeError`).
  - `__truediv__` — accept scalar (returns `Length`) and `Length`
    (returns dimensionless `float`).
  - `__neg__` / `__abs__` — return `Length`.
  - `__eq__`, `__lt__`, `__le__`, `__gt__`, `__ge__` — compare on
    `_inch`; return `NotImplemented` for non-`Length` operands.
  - `__hash__` — `hash((Length, self._inch))` so `cm(2.54)` and
    `inch(1)` collide as expected.

- [ ] **Step 4: Re-run — all PASS**

  Run: `uv run pytest tests/test_units.py -q`
  Expected: full module green, including the new arithmetic and
  comparison classes.

- [ ] **Step 5: Commit**

  ```
  git add src/dartwork_mpl/units.py tests/test_units.py
  git commit -m "refactor(units): Length arithmetic, comparison, hashing"
  ```

---

### Task 4: Top-level exports + `col1` / `col2` retype

**Files:**
- Modify: `src/dartwork_mpl/__init__.py`.

- [ ] **Step 1: Update the import line**

  Replace:
  ```python
  from .units import Inches, cm, figsize, inch, mm
  ```
  with:
  ```python
  from .units import Length, cm, figsize, inch, length, mm, pt
  ```

- [ ] **Step 2: Retype `col1` / `col2`**

  Replace:
  ```python
  col1: float = cm(9)
  col2: float = cm(17)
  ```
  with:
  ```python
  col1: Length = cm(9)
  col2: Length = cm(17)
  ```

- [ ] **Step 3: Update `__all__`**

  In the `# Units (0.4+)` group, drop `"Inches"`, add `"Length"`,
  `"length"`, `"pt"`. Keep the existing ordering style.

- [ ] **Step 4: Verify import surface**

  Run: `uv run python -c "import dartwork_mpl as dm; print(type(dm.col1).__name__, dm.col1.cm, dm.col2.cm)"`
  Expected: `Length 9.0 17.0`. Then:
  Run: `uv run python -c "import dartwork_mpl as dm; dm.Inches"`
  Expected: `AttributeError: module 'dartwork_mpl' has no attribute 'Inches'`.

- [ ] **Step 5: Run targeted regression**

  Run: `uv run pytest tests/test_units.py tests/test_lint.py
  tests/test_migrate_legacy.py tests/test_deprecation_aliases.py -q`
  Expected: all green.

- [ ] **Step 6: Commit**

  ```
  git add src/dartwork_mpl/__init__.py
  git commit -m "refactor(api): swap Inches for Length in dm exports; col1/col2 retyped"
  ```

---

### Task 5: User-facing prose sweep (lint/MCP/CLAUDE/AGENTS/README/migration)

**Files:**
- `src/dartwork_mpl/mcp/prompts.py` (lines 81, 153)
- `src/dartwork_mpl/mcp/tools.py` (line 417)
- `CLAUDE.md` (line 36)
- `AGENTS.md` (line 36)
- `README.md` (lines 80, 153–161)
- `docs/migration.md` (lines 26, 65, 229–242)

- [ ] **Step 1: MCP prompts**

  In `src/dartwork_mpl/mcp/prompts.py`:
  - Line 81 (mandatory rule 2 of the generation prompt): change
    `or an `Inches` value` → `or a `Length` value`. Append
    `, `"24pt"`` to the unit-string list.
  - Line 153 (Critical checklist item): same wording swap.

- [ ] **Step 2: MCP tools info string**

  In `src/dartwork_mpl/mcp/tools.py:417`: change
  `"width accepts unit strings (cm/in/mm) or Inches values
  (dm.cm/inch/mm, dm.col1, dm.col2);"` to
  `"width accepts unit strings (cm/in/mm/pt) or Length values
  (dm.cm/inch/mm/pt, dm.col1, dm.col2);"`.

- [ ] **Step 3: CLAUDE.md / AGENTS.md**

  In both files, in the bullet beginning `**`dm.figsize(width,
  aspect)`**:`, replace `or an `Inches` value` with `or a
  `Length` value` and append `, `"24pt"`` to the unit-string list.

- [ ] **Step 4: README.md**

  - Line ~80 (paragraph after the example block): replace the
    `Inches` value clause with `Length` value, append `, `"24pt"``
    to the unit-string list, and append `, dm.pt(24)` to the helper
    list.
  - The "### Width Helpers" section (~line 153): retitle to
    `### Length Helpers`. Append rows for `dm.pt(24)` and
    `dm.length("13cm")`. Add a short multi-unit view example
    showing `dm.cm(13).inch / .mm / .pt`.

- [ ] **Step 5: docs/migration.md**

  - Line 26 (table row for `dm.cm2in`): `(returns Inches)` →
    `(returns Length)`.
  - Line 65 (`dm.figsize` paragraph): `or an Inches value` → `or a
    Length value`. Append `, "24pt"` to the unit-string list.
  - The §`dm.cm2in → dm.cm` body (lines ~226–242): rewrite — drop
    the `Inches(float)` framing, show the new `Length` constructors
    + multi-unit views, add a one-paragraph note that the in-flight
    `Inches` marker was renamed to `Length` before any 0.4 release
    shipped, with `dm.Inches` no longer importable.

- [ ] **Step 6: Spot-grep for stragglers**

  Run: `git grep -n '\bInches\b' -- 'docs/' '*.md' 'src/'`
  Expected: zero hits outside the historical
  `docs/superpowers/specs/` and `docs/superpowers/plans/` archive
  (those are immutable history; do not edit). If any production
  doc still mentions `Inches`, fix it before committing.

- [ ] **Step 7: Commit**

  ```
  git add CLAUDE.md AGENTS.md README.md docs/migration.md \
          src/dartwork_mpl/mcp/prompts.py src/dartwork_mpl/mcp/tools.py
  git commit -m "docs: update Inches → Length wording across user-facing prose"
  ```

---

### Task 6: CHANGELOG + final regression

**Files:**
- Modify: `CHANGELOG.md`.

- [ ] **Step 1: Update the `[Unreleased]` section**

  In `CHANGELOG.md`'s `## [Unreleased] / ### Added` block:

  - Insert a new bullet **above** the existing `dm.figsize` bullet:

    ```markdown
    - **`dm.Length`** — Color-style physical-length wrapper that
      replaces the in-flight `Inches(float)` marker introduced
      earlier in this release. Multi-unit views as properties
      (`length.cm`, `length.mm`, `length.inch`, `length.pt`).
      `dm.length("13cm")` parses unit strings (mirrors
      `dm.hex("#abc")`); `dm.pt(24)` joins the existing
      `dm.cm` / `dm.inch` / `dm.mm` constructor family.
      `dm.Inches` is no longer importable.
    ```

  - Update the existing `dm.figsize` bullet: `or an `Inches`
    value` → `or a `Length` value`. Append `, `"24pt"`` to the
    listed unit-string examples.

- [ ] **Step 2: Final regression**

  Run: `uv run pytest -q --no-header`
  Expected: at least Task 1's baseline passing-count, ± the
  delta from new `Length` test cases (Task 2 + Task 3). No
  regressions.

  Record the final count:

  ```
  After: ____ passed, ____ skipped, ____ xfailed
  ```

- [ ] **Step 3: Commit**

  ```
  git add CHANGELOG.md
  git commit -m "docs(changelog): note Length class replacing Inches marker"
  ```

- [ ] **Step 4: Branch sanity**

  Run: `git log --oneline main..HEAD`
  Expected: 6 commits — spec, plan, units-core, arithmetic,
  exports, prose-sweep, changelog (one per task body, plus the
  spec+plan pre-commits if they were two separate commits).

  Run: `git status`
  Expected: clean working tree.

---

## Test inventory (for Task 2 / Task 3)

The replacement `tests/test_units.py` covers these classes. Inline
the bodies during execution; this list is the spec for what must be
present before Task 2 / Task 3 closes.

| Class | Purpose | Task |
|---|---|---|
| `TestUnitConstructors` | `cm()`, `inch()`, `mm()`, `pt()` return `Length`; classmethods (`Length.from_cm` etc.) match wrappers. | 2 |
| `TestLengthInit` | `Length("13cm" / "5in" / "170mm" / "72pt")` parses; default-cm fallback for bare numeric strings; pass-through for `Length` input; bare `int` / `float` / `bool` raise `TypeError`; negative / zero strings raise `ValueError`; non-str / non-`Length` inputs raise `TypeError`. | 2 |
| `TestLengthViews` | `length.cm` / `.mm` / `.inch` / `.pt` round-trip; properties stay in sync via `Length.from_<unit>(view).inch ≈ length.inch`. | 2 |
| `TestLengthRepr` | `repr(length)` shows cm for sub-inch values, inch otherwise. | 2 |
| `TestParseWidth*` (existing classes, edited) | `parse_width` accepts `str | Length`; rejects bare numeric / bool with the new "or a Length value" message; preserves the existing self-correction suggestions; new `("72pt", 1.0)` parametrize case for the pt suffix. | 2 |
| `TestParseAspect*` (existing classes, unchanged) | Aspect-token parsing untouched. | 2 |
| `TestFigsize` (existing class, edited) | `figsize` accepts `Length`; the `Inches(...)` import in `test_accepts_inches_value` is replaced with `cm(9)`-style construction asserting `not isinstance(w, Length)` for the returned floats. | 2 |
| `TestPublicSurface` (existing class, edited) | `dm.cm` / `inch` / `mm` / `pt` / `length` exposed; `dm.col1.cm == 9`, `dm.col2.cm == 17`, both `isinstance(_, Length)`; `dm.Length is units.Length`; **new** assertion that `dm.Inches` raises `AttributeError`. | 2 |
| `TestLengthArithmetic` | `Length + Length → Length`; `Length + scalar → TypeError`; `Length × scalar → Length`; `Length × Length → TypeError`; `Length / scalar → Length`; `Length / Length → float (ratio)`; `-Length` and `abs(-Length)` return `Length`; `parse_width(cm(9)*2)` round-trips. | 3 |
| `TestLengthComparison` | `cm(2.54) == inch(1)`; ordering; hashable as dict key. | 3 |

---

## Execution Notes

- **Branch hygiene.** Single feature branch `length-class-152`,
  cut from `main` at the start of this session. Spec + plan ship
  on the same branch as the implementation.
- **Hard removal, not deprecation.** `Inches` was added on
  unreleased `[Unreleased]`; spec §3 confirms zero external
  usage. Do not add a `DeprecationWarning` shim — match PR
  #147's hard-removal precedent for `dm.subplots` / `dm.figure`.
- **No scope creep.** Anything unrelated to the `Inches → Length`
  migration is out of scope. Surfacing a separate issue is
  preferable to expanding this PR.
- **Spec history files are read-only.** When sweeping prose for
  `Inches`, exclude `docs/superpowers/specs/` and
  `docs/superpowers/plans/` — those are dated archives.
