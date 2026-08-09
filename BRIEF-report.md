# Orphan tick-font default flip

## Status

Complete on `fix/orphan-tick-font-default`; ready to commit as one coherent
change. No push was requested or performed.

## Change

- Changed `Config.adopt_orphan_tick_font` from `True` to `False`.
- Kept the feature and every opt-in surface unchanged:
  `adopt_orphan_tick_font=True` on `simple_layout`, `save_formats`, and
  `save_and_show`; `dm.config.adopt_orphan_tick_font = True`;
  `dm.config.override(...)`; `dm.adopt_axis_label_font`; and
  `warn_on_orphan_tick_adoption`.
- Updated source docstrings, live configuration/troubleshooting docs, the
  changelog, and supersession notes on the historical default-on design and
  implementation plan.
- Searched tracked source, docs, `llms.txt`, `llms-full.txt`, and the prompt
  corpus. The llms files and prompt corpus did not state this default and
  needed no edit.

## Compatibility impact

This intentionally changes the rendered output of every existing figure with
an unlabeled axis: its tick labels now retain the smaller/lighter tick font
instead of silently adopting the axis-label font. Projects that require the
old output must set `dm.config.adopt_orphan_tick_font = True` or pass the
per-call keyword.

Tests outside `tests/test_orphan_tick_font.py` did observe the behavior change:
the two freshness checks in `tests/test_docs_theory_figures.py` detected
intentional output drift. No test source outside the orphan-tick test file was
edited; regenerating the repository-owned assets updated exactly
`theory_2_floor.svg`, `theory_3_drift.svg`, and `theory_6_metric.svg`, after
which both checks passed. The separate 14-case pixel baseline comparison still
passed without baseline edits.

Bundled examples and doc figures do depend on the old implicit default. For
example, `examples/plot_bar_with_value_labels.py` and the bundled `bar`
template set a y-label but no x-label, so their categorical x ticks now render
with the tick font. The three regenerated theory SVGs are the tracked doc
figures whose exact output changed. This is the requested visual regression;
the examples remain default-usage examples and were not opted back into the
old behavior.

## Verification

- TDD RED: the four default-off expectations failed against the old field with
  `(7.5, 400) != (5.5, light)`.
- Focused: `35 passed` in `tests/test_orphan_tick_font.py`.
- Full suite: `4929 passed, 2 skipped, 19 warnings` in 850.27 seconds.
- Theory-figure freshness: `18 passed`; generator `--check` reports fresh.
- Pixel baseline comparison: `14 passed` with `--mpl`.
- Ruff lint: all checks passed.
- Ruff format: 268 files already formatted.
- mypy: no issues in 98 source files.
- `git diff --check`: clean.

## Files changed

- `src/dartwork_mpl/config.py`
- `src/dartwork_mpl/layout.py`
- `src/dartwork_mpl/io.py`
- `tests/test_orphan_tick_font.py`
- `docs/api/config.rst`
- `docs/usage_guide/config.md`
- `docs/troubleshooting.md`
- `docs/superpowers/specs/2026-06-03-orphan-tick-axis-label-font-design.md`
- `docs/superpowers/plans/2026-06-03-orphan-tick-axis-label-font.md`
- `docs/color_system/theory_figures/theory_2_floor.svg`
- `docs/color_system/theory_figures/theory_3_drift.svg`
- `docs/color_system/theory_figures/theory_6_metric.svg`
- `CHANGELOG.md`
- `BRIEF-report.md`

## Concerns

The visual change is broad by design. Historical changelog entries and the
archived 2026-06-03 plan/spec retain their original default-on narrative; both
archived documents now carry an explicit current-default supersession note.
The user-owned untracked `BRIEF.md` and `BRIEF.out` were left untouched and
will not be staged.
