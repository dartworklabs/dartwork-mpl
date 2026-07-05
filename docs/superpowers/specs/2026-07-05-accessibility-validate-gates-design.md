# Accessibility validation gates — Design (P5)

> Program umbrella #411, pillar EO5. Advisory/design by orchestrator; implementation by codex.

## Problem

`dm.validate_figure(fig)` runs self-registering visual checks (overflow, overlap, cross-axes,
tick-crowd, margin, legend, empty-axes, clipped-text, pie-label) — all *layout* concerns. A
professional design-plot utility should also gate **accessibility**: is the text legible and
high-contrast, and does the figure survive grayscale/print? Colour-vision-deficiency (CVD) is
already covered at the *palette* level (`colors/_gates.py`, `tests/test_palette_cvd.py`); P5 adds
the missing *figure-level* checks.

## Design

Three new self-registering checks in `src/dartwork_mpl/validate/_checks/`, following the exact
module pattern of the existing checks (mirror `margin.py`): a `check_<name>(fig, renderer) ->
list[VisualWarning]` decorated with `@register_check("<ID>", order=<N>)`, module-level threshold
constants with rationale comments, `__all__`, re-exported + registered in `_checks/__init__.py`.

They fit the existing advisory model — `Severity.WARNING` / `Severity.INFO`, printed by the
orchestrator, never raising. No new Severity level.

### Check 1 — `TEXT_CONTRAST`
WCAG 2.x relative-luminance contrast for every *visible, non-empty* `Text` artist against its
background. Background = the artist's axes `get_facecolor()` if opaque (alpha > 0), else the
figure `get_facecolor()` (fall back to white if transparent). Algorithm (implement exactly):
```
def _rel_lum(rgb):           # rgb components in 0..1 (sRGB)
    def lin(c): return c/12.92 if c <= 0.03928 else ((c+0.055)/1.055)**2.4
    r, g, b = (lin(c) for c in rgb[:3])
    return 0.2126*r + 0.7152*g + 0.0722*b
def _contrast(c1, c2):
    hi, lo = sorted((_rel_lum(c1), _rel_lum(c2)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)
```
"Large text" = effective size ≥ 18pt, OR ≥ 14pt and bold. Applicable AA threshold = 3.0 (large)
else 4.5 (normal). Emit **WARNING** if ratio < 3.0 (fails even large-text AA); **INFO** if
3.0 ≤ ratio < applicable-AA (borderline: passes large-text AA but not normal AA). Include the
offending text (truncated), the ratio, and the threshold in `detail`.

### Check 2 — `MIN_FONT_SIZE`
For every visible, non-empty `Text`, **WARNING** if its effective point size < `5.0` (a print
legibility floor — below this, text is unreadable at figure scale). `detail` carries the text and
its size. (dartwork presets floor at 6.5pt, so clean figures never trip this — it catches
hand-set tiny literals.)

### Check 3 — `GRAYSCALE_SAFETY`
Gather the distinct colors of *data-bearing* artists (line colors, patch facecolors, collection
facecolors). If two or more **distinct** colors have near-identical relative luminance
(|ΔL| < `0.10` on the 0..1 scale), they would be indistinguishable in grayscale / B&W print —
emit **INFO** naming the colliding pair(s). Only fires with ≥ 2 distinct series colors (never on
a single-series plot). INFO, not WARNING (advisory — colour is often enough on screen).

## Integration risk (codex MUST handle)

Registering new default checks can break tests that (a) assert an exact registered-check count /
set, (b) call `validate_figure` on a fixture and assert **no** warnings, or (c) enumerate checks
via the MCP validator tool. Before finishing, codex must:
- grep the test suite for `registered_checks`, check-count assertions, and any explicit list of
  check ids (e.g. `tests/test_validate.py`, `tests/test_mcp_validators_complete.py`,
  `tests/test_mcp*.py`) and update them to include the three new ids.
- Ensure the new checks do **not** fire on default-preset figures: with dartwork presets, text is
  dark-on-light (high contrast) and ≥ 6.5pt, so `TEXT_CONTRAST` and `MIN_FONT_SIZE` stay silent;
  `GRAYSCALE_SAFETY` is INFO-only. If any existing "no warnings" assertion would newly trip,
  report it (do not weaken a check to force a pass without saying so).

## Tests (`tests/test_validate_accessibility.py`)

For each check, a PASS fixture (compliant figure → no warning of that id) and a FAIL fixture
(deliberately non-compliant → the expected WARNING/INFO present). Drive via `validate_figure(fig,
checks=["<ID>"])` (inspect the returned `list[VisualWarning]`; confirm the return type by reading
`_orchestrator.py`) or by calling the check fn directly with a drawn renderer
(`fig.canvas.draw(); renderer = fig.canvas.get_renderer()`). Example fixtures:
- contrast FAIL: `ax.set_title("x", color="#cccccc")` on a white figure → WARNING.
- contrast PASS: default preset title (dark on light) → none.
- min-font FAIL: a `Text` at `fontsize=3` → WARNING; PASS: `fontsize=8`.
- grayscale FAIL: two lines whose colors share luminance but differ in hue → INFO; PASS: two
  lines with clearly different luminance.

## Acceptance

- 3 checks registered + returned by `validate_figure`; `_checks/__init__.py` updated.
- New + dependent tests green; ruff/mypy clean; full suite green (no regression).
- No files touched outside `validate/`, its tests, and dependent test files. No docs/_static,
  design_system, philosophy, prompt-corpus edits.

## Non-goals

- No new `Severity` level (stays WARNING/INFO to fit the model).
- No CVD *simulation* here — palette-level CVD gating already exists; duplicating it is out of scope.
- No auto-fix — these are advisory gates (an auto-fixer could come later via `validate_fixes`).
