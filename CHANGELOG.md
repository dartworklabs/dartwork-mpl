# Changelog

All notable changes to dartwork-mpl will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

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
