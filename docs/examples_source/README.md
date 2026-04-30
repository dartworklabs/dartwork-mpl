---
orphan: true
---

# Gallery Examples

Sphinx-Gallery source for the dartwork-mpl docs site. Each `plot_*.py`
runs end-to-end and is rendered into a thumbnail page during the
docs build.

## 0.4 Migration In Progress

The gallery is mid-migration to the dartwork-mpl 0.4 API
(`dm.subplots(width="13cm", aspect="standard")`,
`dm.auto_layout(fig)`, `dm.col1` / `dm.col2`).

**Authoritative recipes:** `_LAYOUT_RECIPES.md` (lives next to this
file in the repo) is the canonical reference for new examples and
rewrites.

**Already migrated** (use the 0.4 API as a reference):

- `01_styling_and_themes/plot_preset_scientific.py`
- `01_styling_and_themes/plot_preset_presentation.py`
- `04_layout_and_annotations/plot_simple_layout.py`
- `04_layout_and_annotations/plot_panel_labels.py`
- `04_layout_and_annotations/plot_multi_panel_scientific.py`
- `04_layout_and_annotations/plot_auto_layout_dashboard.py`
- `07_real_world_dashboards/plot_sensor_trend_dual_axis.py`

**Pending migration:** the remaining ~60 examples still use the 0.3
patterns (`dm.SW/MW/TW/DW`, `figsize=` tuples, `dm.cm2in`). They
continue to render correctly because 0.4 keeps the legacy paths
behind a `DeprecationWarning`. They will be converted in follow-up
PRs ahead of the 0.5.0 release that removes the deprecated names.

If you are writing a **new** example, follow `_LAYOUT_RECIPES.md`
strictly — the lint catalog
(`dartwork_mpl.asset/prompt/02-anti-patterns.yaml`) blocks the
critical legacy patterns.
