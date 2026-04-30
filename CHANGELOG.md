# Changelog

All notable changes to dartwork-mpl will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Removed (font asset slimming, no API impact)

- **`NotoSans_ExtraCondensed` family (18 files, ~10 MB)** — the family
  was bundled but never referenced by any mplstyle preset, helper,
  example, or test. Removed wholesale.
- **Roboto Thin/Black weights and all italic variants (8 files,
  ~0.7 MB)** — `Roboto-Thin`, `Roboto-ThinItalic`, `Roboto-Black`,
  `Roboto-BlackItalic`, `Roboto-Italic`, `Roboto-LightItalic`,
  `Roboto-MediumItalic`, `Roboto-BoldItalic` are not exercised by any
  bundled preset (presets only call weights 300/400/500/700 and never
  italic).
- **Paperlogy 1Thin / 2ExtraLight / 6SemiBold / 8ExtraBold / 9Black
  weights (5 files, ~6.3 MB)** — bundled presets only reference
  `Paperlogy-3Light`, `Paperlogy-4Regular`, `Paperlogy-5Medium`,
  `Paperlogy-7Bold`. Other Paperlogy weights are not loaded by any
  shipped style.
- **Wheel size reduction**: ~50 MB → ~41.5 MB (≈17%, ~17 MB freed
  uncompressed). sdist drops from ~50 MB to ~41.4 MB. No public API
  changes; users targeting the removed weights can fall back to
  nearby weights via matplotlib's weight-resolution heuristics, or
  install the originals as system fonts.

### Added

- **`dartwork-mpl://guide/migration` MCP resource** — the 0.3 → 0.4
  migration guide is now exposed at a stable URI (sourced from
  `asset/prompt/_legacy/migration-from-0.3.md`) so 0.3 clients
  landing on the deprecated guides have a clear next step. Listed in
  `dartwork_mpl_info()` and the `00-index.md` decision tree.
- **Lint output now surfaces fix suggestions** —
  `format_report(...)` emits `→ fix: <suggestion>` directly under
  each issue when the rule's YAML entry includes a `fix_suggestion`.
  Lets MCP/CLI consumers (and AI agents) apply replacements without
  a second round-trip.
- **`Issue.column` and `Issue.fix_suggestion` fields** — the lint
  `Issue` dataclass now carries the absolute match offset and the
  rule's fix suggestion. The dedupe key inside `lint(...)` switched
  from `(rule_id, line)` to `(rule_id, column)` so multiple
  violations on the same line are reported separately.
- **Thread-safe `ensure_loaded` for fonts and colormaps** —
  `dartwork_mpl.cmap.ensure_loaded()` and
  `dartwork_mpl.font.ensure_loaded()` now use a module-level
  `threading.Lock` with double-checked locking, eliminating a
  `ValueError` race when two threads first import the package
  concurrently. `dartwork_mpl.style.Style.stack(...)` is likewise
  guarded so concurrent `dm.style.use(...)` calls cannot interleave
  `rcParams` mutations.
- **Test isolation conftest** — `tests/conftest.py` now ships an
  autouse fixture that closes every figure and restores rcParams
  defaults between tests, preventing style/figure leak across the
  834-test suite.
- **Smoke tests for `dartwork_mpl.helpers.*`** — `test_helpers_*.py`
  files cover `quality`, `formatting` (deprecated alias),
  `colors`, `labels`, and `data`, raising the previously
  near-zero coverage on those modules.
- **Branch coverage for `validate_enhanced.get_fix_suggestions`** —
  added cases for OVERFLOW (right/bottom/top), OVERLAP,
  LEGEND_OVERFLOW, TICK_CROWD (x/y), EMPTY_AXES, MARGIN_ASYMMETRY,
  and PIE_LABEL_OFFSET so every public branch of the suggestion
  table is exercised.
- **Branch coverage for `style.Style`** — kwargs override
  (`font_size=14` and dot-notation), list-of-presets `use(...)`,
  `presets_dict()` mutation isolation, and the `context(...)`
  context manager.

### Changed

- **`dpi-arg` lint severity raised to `critical`** — `dpi=` on
  `plt.figure` / `dm.figure` / `dm.subplots` now matches
  `figsize-direct` in severity, aligning the rule with the
  always-true facts in `00-index.md`. `savefig(dpi=...)` remains
  owned by `savefig-direct` (warning).
- **Deprecated 0.3 prompt files reduced to redirect stubs** —
  `coding-rules.md`, `general-guide.md`, and `layout-guide.md` no
  longer carry stale 0.3 content (which contradicted the 0.4
  width/aspect API). They now point at `00-index.md`,
  `01-policy.md`, `03-recipes.md`, and the migration guide. MCP
  URIs are unchanged.
- **`03-recipes.md` heatmap and bundled `heatmap.py` / `contour.py`
  templates** — switched from `plt.colorbar(...)` to
  `fig.colorbar(...)` so the figure-first idiom is consistent and
  copy-pasted recipes don't depend on an unimported `plt`.

### Fixed

- **`Axes.twinx` reentrance guard** — the monkey-patch in
  `dartwork_mpl/__init__.py` now tags the wrapper with
  `__dm_patched__` and skips re-patching when that marker is
  present, so `importlib.reload(dartwork_mpl)` no longer self-wraps
  into a `RecursionError` on the next `ax.twinx()` call.
- **`auto_layout(fig)` / `simple_layout(fig)` no-op on empty figures**
  — both functions used to `IndexError` on `fig.axes[0]` when given a
  figure with no axes; they now return cleanly.
- **`Inches` survives numpy ufunc dispatch** — the `Inches` `float`
  subclass returned by `dm.cm` / `dm.inch` / `dm.mm` now sets
  `__array_ufunc__ = None`, so `np.float64(2) * dm.cm(9)` falls back
  to `Inches.__rmul__` and keeps the inches tag instead of silently
  becoming a bare `np.float64` that `parse_width` would re-interpret
  as cm.
- **sdist whitelist** — `[tool.hatch.build.targets.sdist]` now
  enumerates `src/dartwork_mpl`, `LICENSE`, `README.md`,
  `CHANGELOG.md`, `pyproject.toml`. Previous default-everything
  behaviour swept in worktree caches and `docs/_build`, pushing the
  tarball over PyPI's 100 MB per-file ceiling. The 0.4.0 sdist now
  builds at ~50 MB.
- **`dpi-arg` lint regex now sees through `figsize=(...)`** — the
  prior `[^)]*` pattern stopped at the first `)` and silently missed
  `plt.figure(figsize=(8,6), dpi=200)`. Updated to allow one level
  of nested parens. `savefig(dpi=...)` remains owned by
  `savefig-direct`.
- **`linewidth-literal` lint relaxed for sub-1 hairlines** — the
  rule now only fires on literals whose integer part is `>= 1`.
  Sub-1 widths (`0.3`, `0.5`, `0.8`) are common, intentional
  decoration in the bundled templates, which now lint clean against
  the rules they teach. `linewidth=0` (no-border idiom) and
  `linewidth=2.5` (true bypass) keep their previous behaviour.
- **`dartwork-mpl-mcp` console script** prints a friendly install
  hint and exits `1` when the `[mcp]` extra is missing, instead of
  raising `ModuleNotFoundError` from a top-of-module import.
- **`dm.subplots(width=..., figsize=...)` and `dm.figure(...)`** now
  emit an explicit `UserWarning` saying the new `width=` argument
  was ignored and the legacy `figsize=` won, on top of the existing
  `DeprecationWarning` on `figsize=`.

### Changed

- **`validate_plot_data` now covers all 12 advertised templates** —
  added validators for `violin`, `boxplot`, `histogram`, `contour`,
  and `twin_axis` to match the catalog returned by
  `dartwork_mpl_info()`.
- **`fastmcp` capped below 4** in the `[mcp]` extra
  (`fastmcp>=2.13.3,<4`). 3.x is the latest tested major; 4.x has
  not been vetted and may rename the introspection APIs we relied
  on.
- **`dartwork_mpl_info()` registered-prompt list is now static** —
  previously poked at `mcp._prompt_manager._prompts`, a private
  fastmcp attribute that shifted between 2.x and 3.x. The static
  list is kept in sync with `register_prompts` in `prompts.py`.
- **README** — updated MCP server line to "11 resources +
  3 resource templates / 7 tools / 2 prompts", swapped the
  layout-helper example to lead with `dm.auto_layout(fig)` (the 0.4
  default) with `dm.simple_layout(fig, gs=gs)` shown as the advanced
  fall-through, and changed the `dm.get_prompt(...)` example to
  reference shipped 0.4 prompt names (`00-index`, `01-policy`).

## [0.4.0] - 2026-04-30

Highlights:

- **Width × aspect API** — `dm.subplots(width=, aspect=)` and `dm.figure(width=, aspect=)` accept free-form widths (`"13cm"`, `dm.cm(11.3)`, `dm.col1` / `dm.col2`) and six named aspect tokens (`square` / `portrait` / `standard` / `golden` / `wide` / `cinema`). New `dm.cm` / `dm.inch` / `dm.mm` helpers return `Inches`, a `float` subclass that survives arithmetic so unit-conversion can't be silently doubled.
- **`dm.lint` module + 15-rule anti-pattern catalog** — single source of truth at `asset/prompt/02-anti-patterns.yaml`, served identically by the MCP `lint_dartwork_mpl_code` tool, the `dartwork-mpl lint` CLI, and CI.
- **MCP server (FastMCP)** with the same SSOT prompt assets the bundled install ships.
- **12 ai-ready templates** under `asset/prompt/05-templates/` for common report idioms.
- **Twinx auto-spine monkey-patch** keeps the right spine visible on all `ax.twinx()` axes.
- **0.3 width tokens deprecated** — `dm.SW`, `dm.MW`, `dm.TW`, `dm.DW`, `dm.WIDTHS`, `dm.FS_*`, `dm.cm2in`, `dm.agent_utils`, `dm.xplot` all emit `DeprecationWarning` (removal in 0.5.0 for the width / FS / cm2in family; v1.0 for the older module renames).
- **Retired the "Zero-Resize Policy" wording** in user-facing surfaces. The new policy is free width input plus the `oversize-width` lint guard.

### Added

- **0.4 width × aspect API** — `dm.subplots(width=, aspect=)` and `dm.figure(width=, aspect=)`. `width` accepts unit-suffixed strings (`"13cm"`, `"6.7in"`, `"170mm"`), helper calls (`dm.cm`, `dm.inch`, `dm.mm`), bare numbers (interpreted as cm), and the academic-column sugar `dm.col1` / `dm.col2`. `aspect` is height / width and accepts six named tokens (`square`, `portrait`, `standard`, `golden`, `wide`, `cinema`) or any positive float. A new `dartwork_mpl.units` module exposes the parser (`parse_width`, `parse_aspect`), the `Inches` `float` subclass, and the unit helpers.
- **`dartwork_mpl.lint`** — single-shot static checker that runs the 15-rule anti-pattern catalog over a Python source string. Returns `Issue` objects (`rule_id`, `severity`, `message`, `line`, `snippet`) and a `format_report` helper. The catalog lives in `asset/prompt/02-anti-patterns.yaml` (the SSOT), so the lint engine, the MCP `lint_dartwork_mpl_code` tool, and the `dartwork-mpl lint` CLI never drift.
- **MCP server (FastMCP)** wired to the SSOT prompt directory: serves `00-index`, `01-policy`, `02-anti-patterns`, `03-recipes`, plus the 12 templates under `05-templates/`. The `dartwork-mpl-mcp` console script launches the server.
- **12 ai-ready templates** under `asset/prompt/05-templates/` covering common report idioms (bar chart, line chart, dual-axis, twinx with band, multi-panel grid, diverging bar with legend, etc.). Each template renders with `dm.subplots(width=..., aspect=...)`, lint-pass clean.
- **`dm.col1` / `dm.col2`** — academic single- and double-column constants (`cm(9)` and `cm(17)`), for callers who don't want to type the unit-suffixed string.
- **Domain-neutrality guardrail test** (`tests/test_domain_neutrality.py`): a parametrised pytest scanner that fails CI if any shipped `.py` / `.md` / `.mplstyle` file under `src/dartwork_mpl/` contains unambiguous finance-domain vocabulary (English: revenue, profit, ebitda, earnings, fiscal, valuation, dcf; Korean: 매출, 매출액, 영업이익, 억원, 조원). Prevents regression of the de-domain work below.
- **Guardrail scope expanded to `docs/` and `examples/`**: `tests/test_domain_neutrality.py` now runs a second parametrised test `test_no_finance_terms_in_docs_and_examples` that scans every `.py` / `.md` / `.rst` / `.mplstyle` file under `docs/` and the top-level `examples/` tree. Build artefacts (`_build`, `examples_gallery`, `_static`, `_templates`, `__pycache__`) are excluded. `tests/` itself is deliberately skipped because the term list would match recursively. The full guardrail now scans 184+ files per run.
- **`dm.helpers.labels`** — new submodule name for what used to be `dm.helpers.formatting`. Houses `format_axis_labels`, `optimize_legend`, and `add_value_labels`. Renamed to avoid the naming clash with the top-level `dartwork_mpl.formatting` module (which houses the `format_axis_*` tick formatters). The old `dm.helpers.formatting` import path still works but emits a `DeprecationWarning` pointing at the new name.
- **`tests/test_templates.py`** — renamed from `tests/test_xplot.py` to match the canonical module name. Migrated the three existing tests to use `from dartwork_mpl.templates import plot_diverging_bar` (canonical) instead of the deprecated `from dartwork_mpl.xplot import plot_diverging_bar`, and added two regression tests that exercise the `dm.xplot` deprecation shim: one asserts the legacy import still resolves to the same callable, and the other asserts `dm.xplot` attribute access emits a `DeprecationWarning`.
- **Dedicated tests for four previously-uncovered public modules**: `tests/test_figure.py` (9 tests covering `dm.subplots` and `dm.figure`, including style/figsize/dpi forwarding and invalid-style handling), `tests/test_formatting.py` (15 tests, one per axis formatter plus parametrised decimals and rotation), `tests/test_spines.py` (9 tests, one per spine/grid helper with concrete spine-visibility assertions), and `tests/test_validate_enhanced.py` (7 tests covering `validate_with_fixes`, `get_fix_suggestions`, `check_agent_requirements`, `generate_validation_report`, and the new `dm.validate_with_fixes` top-level alias). Suite goes from 534 to 574 passing tests.
- **Gallery: six new single-plot spine / grid examples** under `docs/examples_source/01_styling_and_themes/` — `plot_spine_minimal.py`, `plot_spine_visibility.py`, `plot_spine_styling.py`, `plot_grid_customization.py`, `plot_spine_publication_styles.py`, `plot_spine_dark_theme.py`, `plot_spine_dashboard.py`. Each renders exactly one figure, per the repo's one-plot-per-file convention.
- **Gallery: six new single-plot helpers examples** under `docs/examples_source/05_advanced_components/` — `plot_helpers_data_validation.py`, `plot_helpers_color_selection.py`, `plot_helpers_labels.py` (renamed from `plot_helpers_formatting.py` for consistency with the new `dm.helpers.labels` submodule), `plot_helpers_quality.py`, `plot_helpers_io.py`, `plot_helpers_workflow.py`. Each renders exactly one figure and covers one `dm.helpers` submodule (plus an end-to-end workflow demo), replacing the monolithic six-figure `plot_helpers_usage.py`.
- **`dartwork_mpl.diagnostics`** — new canonical home for the four asset-inspection helpers (`classify_colormap`, `plot_colormaps`, `plot_colors`, `plot_fonts`). Closes out the final v0.2.0 folder-restructuring follow-up tracked as issue #57. The functions themselves are unchanged; only their physical module path moved. All four names remain reachable via `dartwork_mpl.<name>` (top-level), `dartwork_mpl.explore.<name>` (re-export), and — with a `DeprecationWarning` — via the legacy `dartwork_mpl.asset_viz.<name>` path.
- **`tests/test_diagnostics.py`** — 14 tests covering the canonical `dartwork_mpl.diagnostics` import path (functional behaviour of the four helpers plus a `TestTopLevelReexport` class pinning that `dm.<name>` and `dm.explore.<name>` resolve to the same objects as `dm.diagnostics.<name>`). Migrated and expanded from the legacy `tests/test_asset_viz.py`.

### Changed

- **Retired the "Zero-Resize Policy" wording** across user-facing surfaces (README, `docs/api/figure.rst`, MCP prompt assets). The replacement framing is "free width input plus the `oversize-width` lint consistency guard", documented in `asset/prompt/01-policy.md` and the 0.3 → 0.4 section of `docs/migration.md`.
- **`plot_diverging_bar()`** (templates): Default `neg_label` / `pos_label` are now the neutral `"Negative"` / `"Positive"` (previously domain-branded strings). The default `title`, default sample `labels`, and docstring Examples were likewise rewritten to neutral placeholders (`"Category A"`–`"Category H"`, `"Diverging bar chart"`). Calling `plot_diverging_bar()` with no arguments now produces a generic, domain-neutral diagram. The function signature is unchanged, so existing callers that pass explicit labels/title continue to work.
- **MCP prompt asset `coding-rules.md` §12**: Renamed section from "Chart Type Templates" to "Reusable Snippet Patterns" and rewrote the two code blocks as inline snippets rather than `def create_dual_axis_chart(...)` / `def create_categorical_bars(...)` wrapper functions. The wrappers were phantom — no such helpers exist in the shipped package, and the `def` framing could mislead MCP clients into hallucinating `dm.create_dual_axis_chart(...)` calls. A short subsection now points at the one real shipped template, `dm.plot_diverging_bar()`, with a runnable example.
- **MCP prompt asset `coding-rules.md` finance examples removed** (first pass, before the §12 rewrite): previous edits to this shipped AI prompt still carried revenue/margin sample code. Replaced with domain-neutral equivalents so MCP clients stop learning a finance-specific idiom by default.
- **MCP prompt asset `general-guide.md` "Agent Best Practices" de-domained**: the earlier version included finance examples and a phantom `agent_utils` import path. Rewrote to use real exports (`dm.helpers.*`) and neutral sample content.
- **Source-code docstrings** under `src/dartwork_mpl/` rewritten to remove finance vocabulary from every public docstring and inline example. Signatures unchanged. The guardrail test above pins this.
- **`docs/examples_source/` rewritten to one-plot-per-file convention** (first pass): earlier bundle files (`single_plot_example.py`, `single_plot_korean.py`, monolithic gallery entries) were split so each file renders exactly one `Figure`. Also de-domained example captions and data labels.
- **Gallery: `plot_waterfall_bridge.py` generalised to an energy-balance walk** instead of Year-over-Year profit change, so the gallery entry leads with a neutral domain while the narrative text still mentions other valid domains (mass balance, population flow, etc.).
- **Gallery: financial dashboard replaced by a set of single-chart sensor examples** (`docs/examples_source/06_real_world_dashboards/plot_sensor_*.py`), removing the last standalone finance-branded gallery entry and keeping the "real-world dashboard" theme with a neutral subject.
- **Canonical import path for asset diagnostics is now `dartwork_mpl.diagnostics`.** The top-level `__init__.py` and `dartwork_mpl.explore` both re-export `classify_colormap`, `plot_colormaps`, `plot_colors`, and `plot_fonts` from the new `diagnostics` module (previously they came from `asset_viz`). Public API contract (`dm.classify_colormap(...)`, `dm.plot_colormaps(...)`, etc.) is unchanged — only the physical module path moved. `__init__.py`'s internal import block comment was updated to reflect the new source module.
- **`docs/migration.md` rewritten** with a new "v0.3.x → v0.4.0" section at the top covering the width / aspect API, `figsize` → `width=` + `aspect=` rewrite, `tight_layout` → `auto_layout`, `cm2in` → `cm`, and the `dm.lint` quick start. The legacy `asset/prompt/_legacy/migration-from-0.3.md` is now a stub that points at the docs version.
- **`docs/api/index.rst`** wired up new pages: `units`, `lint`, `cmap`, `diagnostics`, `install`, plus the `templates` page (renamed from `xplot.rst`). `constant.rst` carries an explicit `.. deprecated:: 0.4.0` notice. `layout.rst` example replaced its `dm.DW` reference with `dm.col2`.

### Deprecated

- **0.3 width tokens (`dm.SW`, `dm.MW`, `dm.TW`, `dm.DW`)** and the aggregate `dm.WIDTHS`. Resolve via the module-level `__getattr__` with a `DeprecationWarning` pointing at the unit-string / `dm.col1` / `dm.col2` replacements. Removal: 0.5.0.
- **`FS_*` figsize tuples** (`FS_SINGLE`, `FS_DOUBLE`, `FS_SQUARE`, `FS_WIDE`, `FS_TALL`, `FS_GOLDEN`, `FS_SLIDE`, `FS_A4`). Same `__getattr__` shim, same removal in 0.5.0. Replacement is `dm.subplots(width=..., aspect=...)`.
- **`dm.cm2in`** — kept for back-compat but now emits a `DeprecationWarning` pointing at `dm.cm` (which returns the safer `Inches` subclass). Removal: 0.5.0.
- **`dartwork_mpl.helpers.formatting`** — deprecated alias for `dartwork_mpl.helpers.labels`. Importing from the old path still works but emits a `DeprecationWarning` pointing at the new submodule. Renamed to resolve the long-standing name clash with the top-level `dartwork_mpl.formatting` module (which houses the `format_axis_*` tick formatters). Plan to remove the deprecated shim in v1.0.
- **`dartwork_mpl.asset_viz`** — deprecated alias for `dartwork_mpl.diagnostics`. The subpackage is now a thin shim: `asset_viz/__init__.py` re-exports the four helpers from `dartwork_mpl.diagnostics` and emits a `DeprecationWarning` on import. `asset_viz/_cmap.py`, `asset_viz/_color.py`, and `asset_viz/_font.py` were removed (their contents are now in `src/dartwork_mpl/diagnostics.py`). Plan to remove the deprecated shim in v1.0 alongside `dm.agent_utils`, `dm.xplot`, and `dm.helpers.formatting`.

### Fixed

- **CI green on `main` restored**: an incidental pre-existing ruff-format issue in `src/dartwork_mpl/constant.py` and a mypy `attr-defined` complaint on `src/dartwork_mpl/layout.py` were blocking every subsequent PR. Fixed so CI passes cleanly.
- **`docs/api/xplot.rst`**: The "Example" code block called `plot_diverging_bar()` with `categories=` / `negatives=` / `positives=` kwargs that do not exist in the real signature (`labels=` / `neg_values=` / `pos_values=`). Copy-pasting the snippet raised `TypeError`. Corrected the kwargs and added the required `numpy` import so the snippet is strictly runnable as shown.
- **`dm.agent_utils` / `dm.xplot` deprecation warnings are live again.** The package previously set `agent_utils = helpers` / `xplot = templates` as module-level attributes and also defined a module-level `__getattr__` that wanted to emit `DeprecationWarning` on those names. Because Python only calls `__getattr__` when an attribute is *missing*, the attribute shim silently shadowed the warning and users saw no migration signal. Removed the attribute shim so `__getattr__` now fires. The legacy import path (`import dartwork_mpl.agent_utils`) remains supported via the `sys.modules` entry. Also cleaned up an unused `_import_with_warning` helper and tightened the import block so `cmap` / `font` / `helpers` / `icon` / `templates` are imported together.
- **`plot_colormaps` / `plot_colors` / `plot_fonts` / `classify_colormap` now appear in `dartwork_mpl.__all__`.** These four visualization-diagnostic helpers are documented as public API in `docs/api/visualization.rst` and have been reachable as `dm.<name>` for some time, but the top-level `__all__` omitted them, so `from dartwork_mpl import *` skipped them and anything introspecting `__all__` (completion tools, stubs) under-reported the public surface. Replaced the star-import from `asset_viz` with an explicit 4-name import so ruff's F405 is satisfied and the names are statically known.
- **`validate_enhanced` is a first-class public surface now.** `src/dartwork_mpl/__init__.py` now imports the `validate_enhanced` submodule explicitly and re-exports `validate_with_fixes` at the top level, so `dm.validate_enhanced.get_fix_suggestions` / `check_agent_requirements` / `generate_validation_report` and `dm.validate_with_fixes` all work without depending on import side effects. Both `validate_enhanced` and `validate_with_fixes` are now in `__all__`, matching what `docs/api/validate.rst` already promises. `get_fix_suggestions` / `check_agent_requirements` / `generate_validation_report` remain reachable via `dm.validate_enhanced.<name>` only — top-level surface stays narrow.
- **`docs/usage_guide/tutorials.md` "Business Report" tutorial** is now "Korean Operations Report". The `report-kr` preset showcase previously branded its example as a quarterly revenue / margin report (`매출액 (억원)`, `영업이익률 (%)`, `quarters = ["1Q24", ...]`). Rewritten to a weekly operations report (`처리량 (건)`, `가동률 (%)`, `weeks = ["1주차", ...]`) so the pedagogical payload — Korean font + dual-axis bar+line + `PercentFormatter` + `auto_layout` — stays identical but the surrounding narrative is domain-neutral. Grid-card title, in-page anchor (`korean-operations-report`), and save filename updated accordingly.
- **`docs/api/formatting.rst` example and section framing** re-themed to remove the implicit "formatters are a finance tool" branding. The "Financial Data Formatting" section becomes "Large Number Formatting" (sample counts / dataset rows / population instead of revenue / market cap / GDP). The "Complete Example: Financial Dashboard" becomes "Complete Example: Multi-format Dashboard" — a 2×2 grid exercising all four numeric formatters on neutral metrics (sample count, efficiency, unit price, cumulative energy). The "Financial Reports" common-patterns subsection, the "Financial formats" feature bullet, the `data_type == 'financial'` branch, and the "technical/financial" Best Practice line are all neutralised. API signatures are unchanged.

### Removed

- **`FOLDER_RESTRUCTURING.md`** moved from the repo root to `docs/development/folder-restructuring.md`. Kept as a historical reference for the v0.2.0 rename (documented migration contract + deprecation timeline) but trimmed its stale "Next Steps (Optional)" list: the `asset_viz → explore` merge is now tracked as a dedicated issue, and the rest of the bullets were already complete.
- **`AGENT_IMPROVEMENTS.md`**: Removed root-level planning document that described phantom modules (`agent_utils.py`, `templates/financial.py`, `templates/scientific.py`, `templates/business.py`) and phantom functions (`create_dual_axis_chart`, `create_waterfall_chart`, `create_multiple_comparison`, `create_band_chart`, etc.) as if they were implemented. The document also framed the library as finance-domain oriented, contradicting dartwork-mpl's identity as a general-purpose matplotlib design utility. Real features (MCP tools, `validate_enhanced`, prompt guides) are tracked in this changelog and their own source files.
- **`docs/examples_source/01_styling_and_themes/plot_spine_styles.py`**: Removed the monolithic seven-figure gallery script and replaced it with the seven single-plot files listed under "Added" above. Each new file preserves the original narrative of its section (minimal / visibility / styling / grid / publication / dark / dashboard) but renders exactly one `Figure`.
- **`docs/examples_source/05_advanced_components/plot_helpers_usage.py`**: Removed the monolithic six-figure gallery script and replaced it with the six single-plot files listed under "Added" above (one per `dm.helpers` submodule, plus a workflow demo). Each new file renders exactly one `Figure`.
- **`docs/api/xplot.rst`** removed in favor of the canonically-named `docs/api/templates.rst`. The new page covers the same surface (`dm.plot_diverging_bar`) and links back to the migration guide for the rename history.

## [0.3.1] - 2026-03-20

### Fixed

- **Documentation**: Extensive updates to MCP Server documentation (8 resources, 7 tools, 2 prompts) and README.
- **Tests**: Expanded MCP test suite from 9 to 28 tests for full coverage.

## [0.3.0] - 2026-03-20

### Added

- **MCP Tools**: 6 new tools — `get_color_value`, `mix_colors`, `list_color_families`, `lint_dartwork_mpl_code`, `validate_plot_data`, `dartwork_mpl_info`.
- **MCP Resources**: 6 new resources — `palette/colors`, `palette/fonts`, `styles/list`, `styles/{preset}`, `templates/list`, `templates/{plot_type}`.
- **MCP Prompts**: 2 interactive prompts — `create_plot` (guided plot generation), `style_review` (code compliance review).
- **Korean font fallback**: `Pretendard` → `NanumBarunGothic` fallback chain in mplstyles.
- **`twinx()` auto-spine**: Monkey-patch ensures right spine is always visible on twin axes.
- **Validation checks**: `MARGIN_ASYMMETRY` and `PIE_LABEL_OFFSET` in `validate_figure()`.
- **Heatmap default**: `image.aspect=equal` set as default rcParam.
- **Gallery examples**: Advanced ML and Bayesian visualization examples.
- **Colormaps**: 9+ new vibrant colormaps across all categories; cyclical cmaps.

### Changed

- **Colormap curation**: Reduced from 232 → 16 core colormaps with descriptive names.
- **Default tick labelsize**: Changed to 8.0pt.
- **Plot readability**: Thicker lines, bold titles, and adjusted margins.
- **Docstrings**: All docstrings translated from Korean to English.
- **Monochrome toggle**: Replaced toggle switch with explicit segmented control in UI.

### Fixed

- **`dc.ocean` colormap**: Replaced removed `dc.ocean` with `dc.deep_sea` throughout docs.

## [0.2.0] - 2026-03-07

### Added

- **MCP Server**: Built-in Model Context Protocol server (`dartwork-mpl-mcp`) for AI coding assistants (Claude Code, Cursor, Windsurf, Antigravity). Exposes library guides as resources and `fetch_github_document` as a tool.
- **MCP documentation**: Comprehensive `docs/api/mcp.rst` covering capabilities, client configuration, verification, architecture, and troubleshooting.
- **PEP 561 compliance**: `py.typed` marker for downstream mypy support.
- **CI pipeline**: GitHub Actions with lint (ruff + mypy), test (pytest + coverage), and docs (sphinx) jobs.
- **Pre-commit hooks**: Ruff lint/format and mypy via `.pre-commit-config.yaml`.
- **`__all__` exports**: Explicit public API for 15 modules.
- **`auto_layout()` function**: Content-aware layout that automatically detects and fixes text overflow.
- **`set_xmargin()` and `set_ymargin()` functions**: Set responsive axis margins based on data range.
- **`dm.subplots()` and `dm.figure()` wrappers**: Enhanced figure creation with integrated styling.
- **Helper utilities**: AI-focused utilities for data validation, color selection, formatting, and quality checks.

### Changed

- **Module renames for clarity**:
  - `agent_utils` → `helpers`: Better reflects general-purpose utility nature
  - `xplot` → `templates`: More descriptive of ready-to-use visualization templates

### Deprecated

- **`agent_utils` module**: Renamed to `helpers`. Import `dartwork_mpl.helpers` instead. Backward-compatible alias provided with deprecation warning.
- **`xplot` module**: Renamed to `templates`. Import `dartwork_mpl.templates` instead. Old name available as alias with deprecation warning.
- **`xplot` re-export**: `plot_diverging_bar` accessible via `dm.plot_diverging_bar()`.
- **`USAGE_GUIDE.md` asset**: Bundled guide for LLM install command.
- **Test coverage**: 228 tests, 91% line coverage.
- **CHANGELOG.md**: This file.

### Changed

- **`asset_viz`**: Split from single 1,387-line file into `asset_viz/` subpackage (`_cmap.py`, `_color.py`, `_font.py`).
- **`color/_loader.py`**: Removed eager module-level `ensure_loaded()` call; registration now triggered explicitly in `color/__init__.py`.
- **`util.py`**: Split God Module into `layout.py`, `annotation.py`, `io.py`, `scale.py`, `prompt.py` + residual `util.py`.
- **`color/`**: Extracted `_BaseColorView`, unified iterator classes, added `_load_json_palette` helper.
- **`__init__.py`**: Lazy initialization for side effects (font, cmap, icon registration).
- **README**: Updated project structure to reflect new subpackages.

### Removed

- **`cmap-backup/`**: 114 unused backup files.
- **Tracked notebooks**: 11 `.ipynb` files untracked and added to `.gitignore`.

### Fixed

- **MCP script name collision**: Renamed `mcp` → `dartwork-mpl-mcp` to avoid conflict with the `mcp` Python package CLI.
- **`__version__`**: Synced with `pyproject.toml` (`0.1.0` → `0.2.0`).
- **Ruff lint**: Applied auto-fixes for unused imports and loop variables.
- **`ui` module**: Lazy-import `run` to avoid requiring `uvicorn` at import time.

## [0.1.1] - 2026-03-07

### Changed

- Version sync between `__init__.py` and `pyproject.toml`.

## [0.1.0] - 2025-12-01

- Initial public release with style management, color system, font registration, colormap support, and visual validation.
