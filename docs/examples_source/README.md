---
orphan: true
---

# Gallery Examples

Sphinx-Gallery source for the dartwork-mpl docs site. Each `plot_*.py`
runs end-to-end and is rendered into a thumbnail page during the
docs build.

## 0.4 Migration Complete

The entire gallery now uses the dartwork-mpl 0.4 API:
`plt.subplots(figsize=dm.figsize("13cm", "standard"))`,
`dm.simple_layout(fig)`, `dm.col1` / `dm.col2`. None of the legacy
0.3 tokens (`dm.SW/MW/TW/DW`, `dm.FS_*`, `dm.cm2in`,
`figsize=`/`dpi=` on `dm.subplots`) remain — they were purged from
the public API in PR #87 and would crash at import otherwise.

**Authoritative recipes:** `_LAYOUT_RECIPES.md` (lives next to this
file in the repo) is the canonical reference for new examples and
rewrites.

If you are writing a **new** example, follow `_LAYOUT_RECIPES.md`
strictly — the lint catalog
(`dartwork_mpl.asset/prompt/02-anti-patterns.yaml`) blocks the
critical legacy patterns.
