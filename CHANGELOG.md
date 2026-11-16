# Changelog

Entries before 0.8.0 are in the git history of this file.

## [Unreleased] — 0.8.0

The package was rebuilt around one criterion: turn on the skill, say "draw
this", get a beautiful chart. Colour values and the rendered look are
unchanged; almost everything else is smaller. No compatibility layer is kept:
removed names simply no longer exist.

### Changed

- uv first. `dartwork-mpl install` is a console script: `uv run dartwork-mpl
  install` in a project, `uvx dartwork-mpl install` without one. It links the
  skill when the package is inside the project (after `uv add`) and copies it
  otherwise, so a skill installed from uvx's cache survives `uv cache clean`;
  running it again refreshes a copy. `--copy` replaces an existing link.
  `python -m dartwork_mpl.guide` still runs the same.
- The package is eleven slices: `style`, `size`, `color`, `font`, `layout`,
  `ticks`, `labels`, `legend`, `check`, `save`, `guide`.
- `dm.simple_layout` keeps 1 mm between the content and the canvas edge by
  default (was 0). Pass `margin=0` for the old flush layout.
- `dm.check(fig)` replaces `dm.validate_figure` and `dm.review`. It returns
  typed findings and never changes the figure. Saving no longer validates.

- Type checking uses basedpyright.

### Removed

- The MCP server (`dartwork-mpl-mcp`, the `mcp` extra). Agents use the
  bundled skill and run the code in their own shell.
- The local viewer (`dartwork-mpl-ui`, the `ui` and `notebook` extras),
  `dm.show`, `dm.save_and_show`.
- Colour build and verification tooling, `dm.show_colors`, colormap catalog
  renderers. Font families no preset uses, icon fonts, `dm.plot_fonts`.
- `dm.optimize_legend`, `dm.arrow_axis`, `dm.wrap_axis_label(s)`,
  `dm.make_offset`, `dm.tight_crop`, `dm.get_bounding_box`,
  `dm.adopt_axis_label_font`, `dm.avoid_tick_overlap`, `dm.figsize_grid`,
  `dm.length`, `dm.dpi`, `dm.Style`, `dm.tokens`, `dm.plot_diverging_bar`,
  `dm.suggest_chart_type`, `dm.migrate_legacy_code`, prompt helpers
  (`dm.get_prompt` and friends), `dm.validate_data`.
- Twin-axis automatic colours, the concise date style, year axes on y,
  SubFigure layout (a figure with SubFigures is left alone with a warning).
- The Sphinx documentation, examples and brand assets (moving to the site
  repository).
