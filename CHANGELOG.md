# Changelog

All notable changes to dartwork-mpl will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Removed (breaking)
- **`install_llm_txt` / `uninstall_llm_txt` (and `INSTALL_TARGETS`) are
  removed.** They copied the bundled prompt corpus into IDE-specific
  folders — a job now better served by the MCP server (runtime
  `dartwork-mpl://guide/*` resources) and the repo-root onboarding files
  (`AGENTS.md`, `CLAUDE.md`, `llms.txt`, `llms-full.txt`). **Migration:**
  non-MCP users resolve the corpus with `dm.agent_doc_path(name)` /
  `dm.get_agent_doc(name)` (accepts `"AGENTS"`, `"CLAUDE"`, `"llms"`,
  `"llms-full"`) and copy it into their tool's context location. (#170)
- **`ipython` is no longer a core dependency.** Only `dm.show()` (inline
  SVG display in Jupyter) needs it, so it moved to a `notebook` optional
  extra — `pip install "dartwork-mpl[notebook]"`. This drops ~30 MB of
  IPython transitive dependencies (`prompt_toolkit`, `jedi`, `traitlets`,
  `stack_data`, …) from every non-notebook install of this matplotlib
  styling library. `dm.show()` now raises a clear `ImportError` naming
  the extra when IPython is absent; every other entry point is
  unaffected. **Migration:** notebook users add the `[notebook]` extra
  (or install `ipython` directly). (#248)

### Changed
- **Color assets load via `importlib.resources`** instead of an
  `__file__`-relative filesystem path, so palette loading works even when
  the package is imported from a zip / non-extracted wheel. No change to
  the colors registered. (#236)
- **`cspace` accepts every string form `dm.color` does.** String
  endpoints now route through the unified `Color(...)` parser, so
  `cspace("oklch(0.7, 0.15, 30)", ...)` and `rgb(...)` work — previously
  only hex and palette names were accepted (oklch/rgb strings raised). (#236)
- **Agent-facing validation heuristics hardened (`check_agent_requirements`,
  `TICK_CROWD`).** `style_applied` is now figure-local — it inspects the
  figure's own text artists instead of the process-global `plt.rcParams`
  (which any later `style.use` / `rcdefaults` mutates independently of the
  figure under test). `proper_colors` now flags full color names
  (`"red"`, `"green"`, …) and patch (bar/area) facecolors, not just
  single-letter codes on lines. The `TICK_CROWD` visual check measures
  each label's real rendered extent — so it scales with font size, weight,
  rotation, and text length — instead of a fixed 4 ticks/inch density that
  ignored font size (it falls back to the density only when extents are
  unmeasurable). (#236)
- **`diagnostics` is now a package** (`_colormaps` / `_colors` / `_fonts`
  submodules) instead of a single 1309-line module (#235). Purely
  internal — the public API (`classify_colormap`, `plot_colormaps`,
  `plot_colors`, `plot_fonts`) and every existing import path
  (`dartwork_mpl.diagnostics.*`, the top-level namespace, the deprecated
  `asset_viz` alias) are unchanged.
- **UI viewer pins the Lucide icon CDN** to `lucide@1.17.0` (explicit
  UMD path) instead of `@latest`, for reproducible builds and
  supply-chain safety. (#236)
- **Docs build caches the sphinx-gallery output in CI.** The generated
  gallery tree (`docs/examples_gallery/`, including each example's
  `.py.md5` stamp) is now cached and restored, so a build whose example
  sources and library code are unchanged skips the 70+ example
  executions that dominated the build (~9 min → ~1 min). The cache key
  folds in the example sources, package source, `conf.py`, the build
  hooks, and the lockfile, so any change forces a fresh, full rebuild —
  no stale images. A new `PLOT_GALLERY=0` env var skips gallery
  execution entirely for fast local prose/layout previews. (#249)
- **`dartwork_mpl_info` now derives its advertised MCP catalog
  dynamically** instead of from hand-maintained literals. The `tools`
  and `resources` (and `prompts`) lists are scanned from the
  decorator source of `tools.py` / `resources.py` / `prompts.py`, and
  the `plot_templates` / primitive `style_presets` lists are globbed
  from the bundled `asset/` directories. Adding a tool, resource, or
  template can no longer silently drift the `dartwork_mpl_info`
  catalog out of sync with the live registry. This also fixes a latent
  omission — `dartwork-mpl://guide/anti-patterns` was missing from the
  previously hardcoded `resources` list and is now advertised. (#236)

### Fixed
- **`Color.from_rgb` validates its input** instead of silently producing
  an out-of-gamut color. Non-finite (`NaN`/`inf`) and negative channels
  are rejected, and once the auto-detect heuristic reads values as 0-255
  (any channel > 1.0) a channel > 255 now errors rather than normalizing
  to > 1.0. (#236)
- **`dm.fw(n)` honours its `-> int` contract for fractional `n`.** A float
  step (e.g. `fw(0.5)`) used to return a float; the result is now rounded
  to an int (matplotlib font weights are integers). (#236)
- **`icon.ensure_loaded` is thread-safe** — it gained the same
  double-checked `threading.Lock` as `font.ensure_loaded` /
  `cmap.ensure_loaded`, so concurrent first use can't register the icon
  fonts twice. (#236)
- **`check_figure_quality` DPI threshold matches its advice.** The check
  flagged DPI `< 150` while the message said "at least 200"; both now use
  a single `_MIN_RECOMMENDED_DPI = 200` constant (aligned with
  `check_agent_requirements`' `high_dpi` bar). (#236)
- **Lint anti-pattern catalog + auto-fix table corrected (`lint.py`,
  `02-anti-patterns.yaml`).** Removed a dead, semantically wrong
  `apply_lint_fixes` entry that referenced the non-existent rule_id
  `cm2in-call` and rewrote `dm.cm2in` → `dm.cm` (the two are not
  interchangeable — `cm2in` returns inches, `cm` a `Length`); the legacy
  token is now left for `migrate_legacy_code`. A new test asserts every
  auto-fix rule_id exists in the SSOT catalog. The
  `multirow-subplots-no-gridspec-kw` detector now catches line-wrapped
  `plt.subplots(` calls (a bounded look-ahead for `gridspec_kw` /
  `sharex` / `sharey`) instead of only single-line ones. Corrected two
  catalog messages that said `style_spines` / `auto_select_colors` were
  removed/renamed "in 0.5.0" — they shipped in 0.4.1 (#156). (#236)
- **`validate_with_fixes(auto_apply=True)` applies `simple_layout` once.**
  It previously called the whole-figure layout solver once *per*
  OVERFLOW / MARGIN_ASYMMETRY warning, re-running it redundantly and
  listing N identical "Applied simple_layout" entries for a single
  mutation. (#236)
- **Docs `viz_example` asset now renders** (long-standing intermittent
  docs-build failure). `_save_viz_example` passed `dm.cm(15)` / `dm.cm(10)`
  — `Length` objects, not float subclasses since 0.4.x — straight to
  `fig.set_size_inches`, so matplotlib built an object-dtype size array
  and raised `ufunc 'isfinite' not supported`; the SVG was never written
  and the `-W` build aborted on the missing figure. It now sizes via
  `dm.figsize("15cm", "10cm")` (inch floats). As defense-in-depth, the
  API asset builder retries each generator once and drops a visible
  placeholder SVG on final failure so a single bad asset can never abort
  the whole docs build. (#235)
- **UI export endpoints fail cleanly on bad input.** `/api/export/{fmt}`
  and `/api/save-server/image/{fmt}` validate `fmt` against matplotlib's
  supported filetypes and return **400** for an unknown format instead of
  a 500 from `savefig`. The export / script / save-server endpoints build
  the param model through a checked helper that returns **422** for
  invalid params (parity with `/api/render`, which already did). UI
  presets and config are written atomically (temp file + `os.replace`) so
  a racing reader/writer can't observe a half-written JSON file. (#236)
- **Out-of-gamut OKLCH colors are now gamut-mapped preserving L and h**
  (behavior change for out-of-gamut colors). `Color.to_rgb` previously
  clamped each linear-sRGB channel independently, which shifted the
  requested lightness *and* hue — e.g. `from_oklch(0.7, 0.4, 30).to_hex()`
  returned `#ff0000` (OKLCH ≈ 0.628 / 29.2). It now reduces chroma while
  holding L and h fixed (binary search to the sRGB gamut boundary, CSS
  Color 4 style): the same color maps to `#ff6551` (OKLCH 0.700 / 30.0,
  chroma 0.40 → 0.19). In-gamut colors are unchanged; only colors for
  which `in_gamut()` is `False` render differently. (#240)
- **`fetch_github_document` now surfaces the underlying error detail**
  (`<ExcType>: <message>`) instead of only the exception type name, so
  an agent can tell a `404` apart from a timeout or DNS failure and
  self-correct rather than retrying blind. (#236)
- **`mix_colors` validates `ratio` before blending.** A non-finite
  (`NaN`/`inf`) or out-of-`[0, 1]` ratio extrapolated past the two
  endpoints, producing RGB outside `[0, 1]` and a malformed hex (or a
  leaked matplotlib "RGBA values should be within 0-1 range" error).
  The ratio is now rejected up front with an actionable message. (#236)
- **`style.use` now preserves a caller-set `svg.hashsalt`** across its
  internal `rcParams`-default reset. Previously every preset switch restored
  matplotlib's default (`None` → uuid4 element ids), so any SVG saved after a
  `style.use` call had non-deterministic element ids even when the salt was
  pinned for reproducible output. Setting `svg.hashsalt` now yields
  byte-identical SVGs across rebuilds. (The docs build pins the salt +
  `SOURCE_DATE_EPOCH` so its generated SVG assets stop dirtying the tree.)

## [0.4.2] - 2026-06-03

### Added
- **`dm.adopt_axis_label_font(fig)`** — when an axis carries tick labels
  but no axis label, its tick labels (major and minor) and scientific
  offset text adopt that axis's label font (size, weight, family,
  style; color is preserved). The x and y axes are judged
  independently, so an axes with a y-label but no x-label restyles only
  the x tick labels. Reads the font from the (possibly empty) axis-label
  Text object, so repeated application is idempotent.

### Changed
- **`simple_layout` (and therefore the deprecated `auto_layout`) now
  applies `adopt_axis_label_font` by default** via the new
  `adopt_orphan_tick_font=True` parameter. Tick labels on an axis with
  no label render in the (heavier) axis-label style for correct visual
  hierarchy. The adoption runs before each iteration's margin
  measurement so the layout still fits the restyled ticks. Pass
  `adopt_orphan_tick_font=False` to opt out.
- **`save_formats` and `save_and_show` also apply `adopt_axis_label_font`
  by default** (same `adopt_orphan_tick_font=True` parameter, keyword-only)
  so the saved/displayed output always reflects the adoption even when
  `simple_layout` was never called. Together with `simple_layout`, this
  makes orphan-tick adoption automatic across every dartwork finalization
  path — no explicit `adopt_axis_label_font` call is required. Note that
  with the default on, these save helpers now **mutate the figure's tick
  fonts** (idempotent; they do not re-fit margins — call `simple_layout`
  for that). Pass `adopt_orphan_tick_font=False` to opt out.
- **Coverage now includes the `mcp/` package and enforces a
  `fail_under=80` gate.** The agentic core (`mcp/tools.py`,
  `resources.py`) was previously omitted, inflating the reported figure
  (~89% → honest ~86% with `mcp/` counted). The gate fails the build when
  a large chunk of new code ships untested instead of letting coverage
  silently regress. `ui/` stays omitted (optional viewer, not
  unit-tested). (#234, #242)

### Fixed
- **`plot_colors(sort_colors=False)` no longer raises `UnboundLocalError`.**
  `color_groups` was bound only inside the `sort_colors` branch — whose
  final reassignment also clobbered the sorted result, leaving the sort
  path dead. The single-group fallback now lives in an `else` branch, so
  sorting actually applies and the unsorted path is defined. (#225, #237)
- **MCP `validate_plot_data` returns a structured error instead of leaking
  a raw `TypeError`.** Several legacy validators indexed or called `len()`
  on a field without a type check, so a present-but-wrong-type field (a
  scalar where a list was expected) or a non-dict payload surfaced an
  uninformative `TypeError` to the client. The dispatch is now guarded and
  returns an actionable message. (#224, #237)
- **Color hex conversion no longer corrupts silently.** `_rgb_to_hex`
  clamped channels with `max(0, min(1, x))`, which collapsed `NaN` to
  `1.0` and emitted a bogus `#ffffff` (e.g. `from_oklab(nan).to_hex()`)
  instead of surfacing the upstream error; it now raises `ValueError` on
  non-finite channels. `_parse_hex` used `lstrip('#')` and fed the result
  straight to `int(.., 16)`, so `##ff0000` parsed as a color and
  `#-10000` produced negative RGB; it now strips exactly one `#` and
  whitelists the hex alphabet before parsing. (#229, #239)
- **`label_axes` font size is now preset-relative.** It defaulted to a
  hardcoded `fontsize=10` that did not scale across presets — the exact
  `fontsize-literal` anti-pattern the library's own lint flags. The
  default is now `None`, resolved to `fs(1)` so panel labels track the
  active preset's base size. `fontweight='bold'` is kept deliberately (a
  semantic weight, not a numeric scaling literal). (#232, #243)
- **Unitless numeric width strings are rejected instead of assumed to be
  cm.** `figsize("13", ...)` / `parse_width("13")` / `Length("13")`
  silently meant `13cm` — the same cm/inch ambiguity for which bare
  `int`/`float` widths are already rejected. A missing unit now raises
  `ValueError` naming the unit suffixes and the `dm.cm()` / `dm.inch()`
  escape hatches. (#226, #244)
- **`__version__` is derived from package metadata.** It was a
  hand-maintained literal that drifted (`0.4.0` while the shipped package
  was `0.4.1`) whenever a release bumped `pyproject.toml` but not the
  literal; it now reads from `importlib.metadata` for a single source of
  truth. Removed 0.3/0.4 names (`dm.SW`, `dm.cm2in`, `dm.FS_*`, …) now
  raise an `AttributeError` that names the replacement API and links
  `docs/migration.md` via a package-level `__getattr__`, instead of
  Python's bare "no attribute" message. (#230, #231, #241)
- **Prompt corpus self-contradiction fixed.** `00-index.md` told agents to
  express sub-1 hairlines as `dm.lw(-1)`, which `01-policy.md` and the lint
  engine both warn collapses to `0.0` and hides the edge; literal
  `0.3`/`0.5` hairlines are restored to match the authoritative policy. The
  raw-hex anti-pattern message recommended non-existent `dm.oc.blue6` /
  `dm.dc.blue500` attribute access (an `AttributeError`); it now points to
  the real string-token form (`color="oc.blue6"`). `llms-full.txt`
  regenerated to match. (#227, #238)

## [0.4.1] - 2026-05-30

### Added
- **`dm.Length`** — opaque Color-pattern length wrapper that
  replaces the in-flight `Inches(float)` marker introduced earlier
  in this release. Multi-unit views as properties (`length.cm`,
  `length.mm`, `length.inch`, `length.pt`).
  `dm.length("13cm")` parses unit strings (mirrors
  `dm.hex("#abc")`); `dm.pt(24)` joins the existing `dm.cm` /
  `dm.inch` / `dm.mm` constructor family. Deliberately **not** a
  `float` subclass — passing a `Length` to a matplotlib API that
  expects a non-inch unit (`fontsize=` / `linewidth=` are pt;
  transform offsets are px) would silently misinterpret the value;
  forcing every boundary to pick a unit explicitly via the property
  views keeps each one type-safe. `dm.Inches` is no longer
  importable. (#152)
- **`dm.figsize(width, aspect)`** — single sizing helper that returns
  the inch tuple matplotlib's `figsize=` expects. Pairs natively with
  `plt.subplots` / `plt.figure` so dartwork-mpl no longer wraps the
  figure constructors. Width must be a unit string (`"13cm"`, `"5in"`,
  `"170mm"`, `"24pt"`) or a `Length` value (`dm.cm(13)`, `dm.col1`,
  `dm.col2`); bare `int`/`float` are rejected (`raw-width-number`
  lint rule). The second argument accepts four equivalent forms —
  aspect token (`"wide"`), numeric ratio (`0.6`), unit-string height
  (`"12cm"`), or `Length` height (`dm.cm(12)`) — so callers can write
  `dm.figsize("15cm", "12cm")` directly instead of hand-computing
  `12 / 15`. (#147, #152)

### Changed
- `dm.mix_colors` now blends in OKLab space (perceptually uniform) instead of
  naïve gamma-sRGB linear interpolation. Result colors will subtly differ for
  non-grayscale blends — gradients now look smoother and less desaturated
  through saturated midpoints (e.g. red + blue gives a vivid purple rather than
  a muddy dark grey). `dm.pseudo_alpha` (which delegates to `mix_colors`)
  inherits the change. (#141)
- `parse_width` now rejects bare `int`/`float`/`bool` with `TypeError`.
  Earlier dartwork-mpl silently treated raw numbers as cm — that
  silently bridged matplotlib's inches contract and caused
  hard-to-spot 2.54× sizing bugs. (#147)
- **`dm.auto_select_colors` → `dm.make_palette`** with argument
  cleanup: `n_series` → `n`, `color_type` → `kind`,
  `highlight_index` → `highlight`. The function body is unchanged
  (same four curated palette lists, same highlight-index swap); the
  rename aligns the name with `make_offset` (prefix) and
  `list_palettes` / `show_palette` (vocabulary). The
  `dm-auto-select-colors-renamed` lint rule flags the old name. (#156)

### Removed
- **`dm.style_spines`, `dm.add_grid`, `dm.minimal_axes`** — round 4 of
  the public API audit (#141 / #156). All three were 1–3 line
  matplotlib calls with curated default kwargs; the curation was the
  only contribution and now lives in `docs/usage_guide/recipes.md`
  (publication grid, minimal axes, thin gray spines snippets). The
  `dm-spines-removed` lint rule flags the old call sites and points
  at the recipes page. The `src/dartwork_mpl/spines.py` module,
  `tests/test_spines.py`, and the `docs/api/spines.rst` page were
  deleted along with the functions; seven `examples_source` files
  that demonstrated the wrappers (`plot_spine_*.py`,
  `plot_grid_customization.py`) were removed because their
  pedagogical purpose was specifically the now-removed functions.
  (#156)
- **`dm.subplots`, `dm.figure`** — both raise `AttributeError` now. The
  package no longer wraps the matplotlib figure constructors. Use
  `plt.subplots(figsize=dm.figsize("<n>cm", "<aspect>"))` and call
  `dm.style.use(...)` separately. The `style=` kwarg is gone with
  them. The `migrate_legacy_code` codemod inserts a
  `# TODO(dm-migrate):` comment above each call site so an agent can
  rewrite them in one sweep. (#147)
- 5 wrapper functions per round-3 of the public API audit (#141):
  `format_axis_percent`, `format_axis_labels`, `add_frame`,
  `add_value_labels`, `set_xmargin`/`set_ymargin`.
  See `docs/migration.md` for inline replacements.
- 8 thin-wrapper utility functions per round-2 of the public API audit (#141):
  `hide_spines`, `hide_all_spines`, `show_only_spines`, `remove_grid`,
  `format_axis_thousands`, `save_figure`, `create_figure_with_style`,
  `templates.diverging_bar.get_source_code`.
  Each can be inlined as a single matplotlib call — see `docs/migration.md`.

## [0.4.0] - 2026-05-05

### Added
- **Robustness test suite** under `tests/robustness/` exercising 44
  scenarios (long tick labels, twinx/twiny, NaN/Inf data, datetime
  axes, log/symlog scales, GridSpec colorbars, pie/donut labels, 한글
  fonts, etc.). Each scenario asserts (a) `validate_figure` outcome,
  (b) `auto_layout` convergence, (c) saved-PNG pixel-level invariants
  via a new `tests/robustness/pixel_assertions.py` helper module.
- **`CLIPPED_TEXT` validation check** that fires when any visible Text
  artist sits within 1 px of the figure canvas edge. Complements
  `OVERFLOW`'s 2 px artist-tree check with a tighter pixel-coverage
  rule, plus fix suggestions in `validate_fixes.get_fix_suggestions`.
- **Robustness extras** — three new scenarios in
  `tests/robustness/scenarios.py`: `subfigures_2x1` (matplotlib
  SubFigure container), `constrained_layout_then_auto_layout`
  (constrained-layout × auto-layout coexistence), and
  `triple_twinx_offset_spine` (third y-axis at axes-fraction 1.15
  with offset spine, currently `xfail(strict=True)` and tracked in
  `KNOWN_LIMITATIONS` until the BUFFER scaling for axes-fraction
  spines is improved).
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
- `RobustnessScenario.auto_layout_padding` field (default 0.08
  inches) lets per-scenario builders request extra initial padding
  for figures whose right-edge content (e.g. axes-fraction-
  positioned spines) tightly fills the `auto_layout` tolerance band.

### Fixed
- `_check_overflow` no longer produces spurious warnings when a
  `Line2D` is backed by NaN-only data or a `Text` artist has a
  zero-area window extent (e.g. `fontsize=0` label).
- `auto_layout`'s per-iteration margin increment is now scaled by 1.5x
  on the overflowing side, accelerating convergence for tall rotated
  and datetime tick footprints.
- `auto_layout` runs a final symmetry pass that averages horizontal
  and vertical margin pairs so asymmetrically-squeezed figures
  (e.g. user called `subplots_adjust` before `auto_layout`) are
  centred without expanding the canvas.
- `rotate_tick_labels` now mutates existing Text artists in place via
  per-label `.set_rotation` / `.set_horizontalalignment`, eliminating
  the matplotlib `set_ticklabels()` UserWarning that previously fired
  on non-FixedLocator axes (e.g. CategoricalLocator from `ax.bar`).
- `format_axis_si` now honours `decimals` for the zero tick: with
  `decimals=2` the zero tick formats as `"0.00"` (previously the
  literal `"0"` regardless of `decimals`, which produced misaligned
  tick label widths next to non-zero values like `"1.50k"`).
- `format_axis_millions` and `format_axis_billions` now honour
  `decimals` for the zero tick (mirroring the `format_axis_si` parity
  fix from PR #116). With `decimals=2` the zero tick formats as
  `"0.00"` instead of the literal `"0"`, restoring tick label width
  parity for charts that include both zero and non-zero values like
  `"1.50M"` / `"1.50B"`.
- `auto_layout` post-convergence symmetry pass now reverts itself
  when re-measurement detects that the averaging would re-introduce
  overflow on any side. Figures with structurally-needed asymmetric
  margins (e.g. axes-fraction-positioned right spines via
  `ax.spines["right"].set_position(("axes", 1.15))`) keep their
  iteration-converged margins; balanced figures (e.g. user called
  `subplots_adjust(left=0.05, right=0.30)`) still get re-centred.
- The `triple_twinx_offset_spine` robustness scenario is no longer
  `xfail` — combined with the symmetry-pass guard above and the new
  `auto_layout_padding` field on `RobustnessScenario`, the scenario
  now converges with a 4 px white-border invariant on the offset
  ylabel and is removed from `KNOWN_LIMITATIONS`.
- `format_axis_currency(position="prefix")` now places the minus sign
  OUTSIDE the currency symbol for negative values (`-$1,000` instead
  of `$-1,000`), matching standard financial-report convention. The
  formatter additionally suppresses the sign when the magnitude
  rounds to exactly zero at the requested decimals (so `x=-0.0` and
  `x=-0.4` with `decimals=0` both render as `"$0"`, not `"$-0"`).

  Note: these source-level fixes are defensive hardening. Scenarios
  still wrapped in `pytest.mark.xfail(strict=True)` represent separate
  library limitations (mostly `auto_layout` failing to absorb the
  footprint of long rotated tick labels, axes-fraction annotations
  that escape the canvas, axes-fraction-positioned right spines, and
  colorbar overshoot) — see `tests/robustness/scenarios.KNOWN_LIMITATIONS`
  for the per-scenario tracking notes.

### Changed (CI strictness)

- **`mypy --strict` is now the default mypy mode** in `pyproject.toml`
  (replaces the looser `warn_return_any` / `check_untyped_defs` config).
  Every module under `src/dartwork_mpl/` passes strict type checking,
  including matplotlib-facing code where `np.ndarray[Any, Any]` /
  `cast(...)` / minimal `# type: ignore[…]` are used at the few
  unavoidable boundaries.
- **Ruff `select` extended** with `BLE`/`RET`/`SIM`/`PERF`/`RUF` rule
  sets (was: `E,W,F,I,B,C4,UP`). All findings in `src/` are fixed; a
  small per-file ignore list shields tests from low-value noise (unused
  unpacked tuples, nested context managers, blind-except in cleanup
  paths, etc.).

### Changed

- **`dartwork_mpl.validate_enhanced` renamed to
  `dartwork_mpl.validate_fixes`.** The module split between
  `validate.py` (visual checks) and the auto-fix companion was clear in
  intent but the "enhanced" name was vague — `validate_fixes` makes it
  obvious that this submodule is the auto-fix layer (`get_fix_suggestions`,
  `validate_with_fixes`, `check_agent_requirements`,
  `generate_validation_report`). The public function
  `dm.validate_with_fixes` is unchanged. Direct submodule access
  (`dm.validate_enhanced` / `from dartwork_mpl.validate_enhanced
  import ...`) now raises `AttributeError` /
  `ModuleNotFoundError` — use `dm.validate_fixes` instead. No
  backward-compat alias is provided, in line with the 0.4.x deprecated-
  surface purge.

### Changed (gallery migration)

- **`docs/examples_source/` gallery (~60 scripts) migrated to the
  0.4 width/aspect API.** PR #74 had only converted 7 signal-flare
  scripts (preset showcases + a handful of layout examples); the
  remaining ~60 still relied on `dm.SW/MW/TW/DW`, `dm.FS_*`,
  `dm.cm2in`, and bare `figsize=`/`dpi=` kwargs and crashed under
  PR #87's deprecation removals (`AttributeError`/`TypeError` at
  import). Every gallery `plot_*.py` now calls
  `dm.subplots(width="...cm", aspect="...")` (or `dm.figure(...)`),
  finalises with `dm.auto_layout(fig)` / `dm.simple_layout(fig)`,
  and reads `dm.cm(...)` instead of `dm.cm2in(...)`. Lint passes
  cleanly for the entire gallery and all 60+ scripts execute
  successfully end-to-end against current main.

### Changed (font asset slimming)

- **`NotoSansCJK-Regular.ttc` (19 MB) → `NotoSansCJK-Regular.otf`
  (1.5 MB Korean subset).** The bundled CJK font is now a Hangul
  subset of the original Noto Sans CJK KR instance: 11,172 Hangul
  syllables + Latin/symbols common in Korean reports. The font's
  family name remains `Noto Sans CJK KR`, so `lang-kr.mplstyle`'s
  fallback chain works unchanged. Users who need Japanese / Chinese
  / Hong Kong glyphs must install Noto Sans CJK system-wide;
  matplotlib's font fallback chain will discover them via system
  paths. Wheel drops from ~41.5 MB to ~27 MB.

### Removed (BREAKING — 0.5.0 candidates pulled forward into 0.4.0)

- **0.3 width tokens** (`dm.SW`, `dm.MW`, `dm.TW`, `dm.DW`, `dm.WIDTHS`)
  removed. Use `dm.subplots(width="9cm" | "12cm" | "14.5cm" | "17cm",
  aspect=...)` or `dm.col1` / `dm.col2`.
- **0.3 figure-size tuples** (`dm.FS_SINGLE`, `FS_DOUBLE`, `FS_SQUARE`,
  `FS_WIDE`, `FS_TALL`, `FS_GOLDEN`, `FS_SLIDE`, `FS_A4`) removed. Use
  `dm.subplots(width=..., aspect=...)` with one of the six aspect
  tokens or a positive float.
- **`dm.cm2in()` removed.** Use `dm.cm(value)` (returns an
  `Inches`-tagged float that `dm.subplots(width=...)` recognises
  directly).
- **`dartwork_mpl.constant` module deleted.** It only held the
  removed width tokens and figure-size tuples.
- **`dartwork_mpl.agent_utils` and `dartwork_mpl.xplot` submodule
  aliases removed.** Use `dartwork_mpl.helpers` and
  `dartwork_mpl.templates` directly. `import dartwork_mpl.agent_utils`
  / `import dartwork_mpl.xplot` now raise `ModuleNotFoundError`.
- **`figsize=` and `dpi=` arguments to `dm.subplots()` /
  `dm.figure()` removed.** Passing them now raises `TypeError` with a
  message naming the new `width=` / `aspect=` API.

All of the above were deprecated in the initial `0.4.0-rc1` cut (see
the release notes below) and emitted `DeprecationWarning` until this
final 0.4.0 release. Migration paths are documented in
`docs/migration.md`.

## [0.4.0-rc1] - 2026-04-30

> Initial 0.4.0 cut. Folded into the final `0.4.0` release on 2026-05-05
> (entries above), which additionally pulled the deprecated 0.3 width
> tokens / `FS_*` / `cm2in` / `figsize=`/`dpi=` arguments forward into
> a hard removal so 0.4.x ships a single, consistent surface.

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

### Post-release polish (rolled into 0.4.0 prior to publish)

The following fixes landed between the 0.4.0 cut commit and the PyPI publish.

#### Added

- **`dartwork-mpl://guide/migration` MCP resource** so 0.3 → 0.4 migration is reachable from the agent entry point and from `dartwork_mpl_info()`.
- **`dm.lint` output now surfaces `→ fix: <suggestion>` lines** when the rule's YAML entry includes a `fix_suggestion`. `Issue.column` and `Issue.fix_suggestion` fields added; the dedupe key inside `lint(...)` switched from `(rule_id, line)` to `(rule_id, column)` so multiple violations on the same line are reported separately.
- **Thread-safe `ensure_loaded` for fonts and colormaps** — `cmap.ensure_loaded()`, `font.ensure_loaded()`, and `style.Style.stack(...)` now use a module-level `threading.Lock` with double-checked locking, eliminating a `ValueError` race when two threads first import the package concurrently.
- **`tests/conftest.py` autouse fixture** closes every figure and restores rcParams defaults between tests, preventing style/figure leak across the suite.
- **Smoke tests for `dartwork_mpl.helpers.*`** (quality, formatting, colors, labels, data) and branch coverage for `validate_enhanced.get_fix_suggestions` and `style.Style` (kwargs, list-of-presets, `presets_dict()` isolation, `context(...)`).
- **`__dir__()` exposes deprecated 0.3 names** so IDE autocomplete can suggest `SW`/`MW`/`TW`/`DW`, `FS_*`, `WIDTHS`, `agent_utils`, and `xplot` during migration. Each access still emits a `DeprecationWarning` via `__getattr__`.
- **PyPI classifiers** — Development Status, Intended Audience, License (OSI MIT), Python 3.10/11/12/13, Topic :: Scientific/Engineering :: Visualization, Framework :: Matplotlib, Typing :: Typed.

#### Changed

- **`dpi-arg` lint severity raised to `critical`** to align with `figsize-direct` and `00-index.md`. `savefig(dpi=...)` remains owned by `savefig-direct` (warning).
- **Deprecated 0.3 prompt files reduced to redirect stubs** — `coding-rules.md`, `general-guide.md`, `layout-guide.md` no longer carry stale 0.3 content.
- **Heatmap recipes / templates use `fig.colorbar(...)`** instead of `plt.colorbar(...)` so copy-pasted snippets don't depend on an unimported `plt`.
- **`validate_plot_data` covers all 12 advertised templates** — added validators for `violin`, `boxplot`, `histogram`, `contour`, and `twin_axis`.
- **`fastmcp` capped below 4** (`>=2.13.3,<4`) in the `[mcp]` extra. 3.x is the latest tested major.
- **`dartwork_mpl_info()` registered-prompt list is now static** instead of poking at the private `mcp._prompt_manager._prompts` attribute that shifted between fastmcp 2.x and 3.x.
- **MCP prompt input cap (8192 chars)** — `create_plot` and `style_review` now truncate `description`, `data_sample`, and `code` with a clear `... [truncated]` marker.
- **Narrowed `except Exception` blocks in `layout.py` and `validate.py`** to `(RuntimeError, ValueError, AttributeError)` so unexpected matplotlib regressions surface instead of being swallowed.
- **Console script renamed `ui` → `dartwork-mpl-ui`** to avoid colliding with whatever `ui` command might already be on a user's PATH.
- **`anti-patterns.yaml` MCP resource ships `application/yaml`** mime type so clients that key off mime auto-detect the format.
- **`oversize-width` lint rule covers fractional widths** (`width="17.5cm"`, `"17.1cm"`, etc.). Previously only integer widths above 17 cm were caught.
- **Clearer `parse_aspect(True)` / `parse_width(True)` errors** — both parsers reject `bool` upfront with "bool is not accepted".
- **`lint(code)` docstring clarifies "Python source only"** to prevent agents from feeding YAML/Markdown into the regex-based lint engine.
- **README "Project Structure" tree refreshed** to reflect the actual 0.4 layout (adds `figure.py`, `lint.py`, `units.py`, `spines.py`, `formatting.py`, `helpers/`, `diagnostics.py`, `explore.py`, `validate_enhanced.py`; marks `constant.py` as deprecated).
- **README MCP resource counts corrected** to `12 resources + 3 resource templates / 7 tools / 2 prompts` (was 11+3).
- **README MCP docs link** points at the actual page (`/integrations/mcp_server.html`, was a broken `/api/mcp.html`).

#### Fixed

- **`Axes.twinx` reentrance guard** — the monkey-patch tags itself with `__dm_patched__` and skips re-patching, so `importlib.reload(dartwork_mpl)` no longer self-wraps into a `RecursionError`.
- **`auto_layout(fig)` / `simple_layout(fig)` no-op on empty figures** instead of `IndexError` on `fig.axes[0]`.
- **`Inches` survives numpy ufunc dispatch** — `__array_ufunc__ = None` on the `Inches` class so `np.float64(2) * dm.cm(9)` keeps the inches tag instead of decaying to a bare `np.float64` that `parse_width` would re-interpret as cm.
- **`_check_pie_label_offset` no longer crashes on regular pies** — coerces `wedge.width=None` (matplotlib's default for non-donut pies) to `1.0` at the source.
- **sdist whitelist now authoritative** — `[tool.hatch.build.targets.sdist]` switched from `include` (additive) to `only-include` (replaces hatch's default file discovery), so the published tarball no longer ships `.claude/`, `docs/`, `tests/`, `examples/`, or `uv.lock`.
- **`dpi-arg` lint regex sees through `figsize=(...)`** — the prior `[^)]*` pattern stopped at the first `)` and silently missed `plt.figure(figsize=(8,6), dpi=200)`.
- **`linewidth-literal` lint relaxed for sub-1 hairlines** — only fires on literals whose integer part is `>= 1`. Sub-1 widths (`0.3`, `0.5`, `0.8`) are common, intentional decoration in the bundled templates.
- **`dartwork-mpl-mcp` console script** prints a friendly install hint and exits `1` when the `[mcp]` extra is missing.
- **`dm.subplots(width=, figsize=)` and `dm.figure(...)`** emit an explicit `UserWarning` saying the new `width=` was ignored and the legacy `figsize=` won.
- **`fetch_github_document` URL allowlist** — only `https://raw.githubusercontent.com/` URLs accepted; other schemes/hosts rejected with a clear `ValueError`. Error messages trimmed to exception type, not full traceback.
- **`dm.cm2in` now actually emits the `DeprecationWarning`** the rest of this changelog promised. (It was supposed to warn since 0.4 but the body of the function was a plain return.)

#### Removed (font asset slimming, no API impact)

- **`NotoSans_ExtraCondensed` family** (18 files, ~10 MB) — never referenced by any mplstyle preset, helper, example, or test.
- **Roboto Thin/Black weights and all italic variants** (8 files, ~0.7 MB) — not exercised by any bundled preset (presets only call weights 300/400/500/700, no italic).
- **Paperlogy 1Thin / 2ExtraLight / 6SemiBold / 8ExtraBold / 9Black** weights (5 files, ~6.3 MB) — bundled presets only reference the four weights kept.
- **Wheel size**: ~50 MB → ~41.5 MB (≈17%, ~17 MB freed uncompressed). sdist now ~5 MB once the worktree-cache leak is fixed by `only-include`.

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
