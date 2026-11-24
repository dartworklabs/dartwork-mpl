# Changelog

Entries before 0.8.0 are in the git history of this file.

## [Unreleased]

### Changed

- The skill's reference-library steps describe the user's data on the Hub
  search's five data axes, read the hits in order (the search now returns
  more, later ones may fit loosely), and point a user without the library to
  its connection guide, https://mpl.dartwork.io/docs/mcp.
- `dm.lint_code` notes `matplotlib-cmap` (info): a literal colormap that
  matplotlib ships (`viridis`, `RdBu`, ...) where dartwork-mpl has a `dc.`
  map for every kind of data. The skill's colormap guidance named `viridis`,
  `cividis` and `magma` for ordered values; it now routes by kind to
  `dm.list_colors(kind)`, and `jet-cmap`'s fix is `cmap="dc.aurora"`.

## 0.10.0 — 2026-11-23

### Added

- `dm.check` reports `UNDERUSED_CANVAS` when a vertical colorbar's
  subplot slot leaves a large blank strip on one side of a plot. It
  suggests a smaller colorbar `fraction` or an explicit column (#858).
- `UNDERUSED_CANVAS` also measures the columns and descriptions in a single
  plot with no x scale and points out a large one-sided blank band (#860).
- `dm.place_columns(ax, *columns)` sets columns of existing texts (a net,
  a share, a table that stands in for a legend) beside a plot: the nearest
  one text size from the plot's edge, each next a text size and a half
  after the text before it (tick labels on that side count). A column
  moves as one block, heading included, and then follows the plot's edge,
  so `dm.simple_layout` makes room for it. Nothing is created or restyled
  (#869).
- `dm.check` reports `TEXT_COLUMN_GAP`: a column of names or numbers set
  beside a plot that sits more than 1.6 em from the marks or the plot's
  edge, or more than 2.5 em from the column between them, a wide heading
  counted. The hint names `dm.place_columns` and the distance to move it
  by hand. The skill's column guidance places columns with the function
  instead of at an axes fraction, and says where a side table and a
  heading go (#869, #870).
- `dm.check`'s `TEXT_CONTRAST` leaves a text of shapes alone (a `■` in a
  series colour as the key of a legend table) to its colour: it is a mark,
  not words to read (#869).
- `dm.align_texts` aligns existing text edges or decimal positions without
  changing the chart's rows or tick labels. `dm.check` flags ragged columns
  beside a plot and suggests how to align them (#812).
- `dm.legible(texts)` makes the texts `dm.check` reports as `TEXT_CONTRAST`
  read on what is drawn behind them: a note that runs over bars, contour
  numbers on pale and dark bands. Called after `dm.simple_layout`, it reads
  the drawn figure and gives each text the least that makes it read:
  nothing to one that reads, the one colour among its own, the preset's
  text colour and the Axes' face colour that reads on everything behind
  it, or an outline in the colour of the background it reads best on. It
  reads the figure again afterwards: a text nothing can mend (it is
  translucent, or something is drawn over it) is left as it was and named,
  and calling it twice is the same as calling it once (#810).
- `dm.check` reports `TEXT_ON_LINE`: a name or note with a line drawn
  through it, as when a fitted trend line strikes out the names of the points
  beside it. A text on a box of its own, a leader that ends at its label and
  a name turned to run along its line are left alone (#852).
- `dm.check`'s `TEXT_AT_EDGE` also reports a plot title that ends at one
  canvas edge with room past its other end: `ax.set_title` centres it on the
  plot, and long category names or a colorbar push the plot off the canvas
  centre. The hint names `fig.suptitle` and a line break (#855).
- `dm.check`'s `TEXT_ON_LINE` also reports an inset's tick or axis labels
  with a zoom connector (`ax.indicate_inset_zoom`) drawn through them: with
  the inset above its zoom region every connector leaves on the side the
  tick numbers are on (#854).
- `dm.check` reports `VALUE_LABEL_ADRIFT`: a value label that stands
  between the bar whose length it prints and another bar of the same row or
  column, nearer the other, as when the values of a bar matrix are set as a
  column at the far end of each cell (#863).
- `dm.check` reports `UNEVEN_OUTLINE`: bars that touch a bar with a
  narrower outline or none. An outline is drawn half outside its bar, so an
  outlined middle segment stood past the segments beside it (#864).
- `dm.check` reports `BAND_OFF_CENTRE`: a band drawn behind one row or
  column of marks whose middle is not that row's (#866).
- `dm.check` reports `TEXT_BOX_ON_DATA`: a text on an opaque box of its
  own that covers bars or filled areas, as when the node labels of a flow
  diagram stood on white boxes though they read without them. The hint
  names the order: without the box first, then `dm.legible` (#867).
- `dm.check` reports `CONNECTOR_SHORT`: a straight line or
  `ConnectionPatch` that ends on the corner of a bar or wedge outlined in
  the colour of the paper. The outline covers the mark's rim, so the line
  stopped half the outline's width from the visible corner (#865).

### Changed

- The skill names four joins to get exact ("Edges and ends" in
  `references/craft.md`): a label at its own mark, the same outline on
  touching marks and none on pieces a connector must meet, a band centred
  on its row, and an axis that ends on a tick when the data leaves room
  (#868). It no longer prints a white-box call for text over data.
- `dm.check`'s `TEXT_CONTRAST` reads every pixel of a text's ink against
  what is drawn behind it, where it compared the text with the one colour
  behind the centre of its box. A note that runs from the canvas onto a dark
  bar, a label over two contour bands, a word a thin dark band cuts through
  and a text in a polar plot are found, and the finding says how much of
  the ink is under 3:1 (#810). A number inside a scatter point or a marker
  is read against the point, not the page behind it (#830). The check
  still draws the figure once.
- Y tick labels sit 3 pt from their tick marks (7.8 pt on `presentation`),
  up from 1 pt, so a category name no longer reads as ending in a hyphen and
  no longer touches the cells of a heatmap drawn without tick marks (#818).
- `dm.simple_layout` aligns the angle labels of a polar plot away from its
  circle when one of them runs into it: a radar's long category names and a
  wind rose's directions then stand at one distance outside the plot. Short
  labels that already clear the circle, and labels aligned or turned by
  hand, stay as they are (#842).

### Fixed

- `dm.check`'s `VALUE_LABEL_ON_DATA` leaves a number centred in a dot that
  holds it (a rank circle, a dot matrix): it is in its mark on purpose, as
  a label inside its bar is. The lines that run under such a dot are not
  counted either (#871, #830).
- `dm.place_columns` keeps the distance to the plot by the rows of a
  column, the texts at the heights of the plot's marks. A heading wider
  than its numbers runs on over the plot instead of pushing them away, and
  `TEXT_COLUMN_GAP` measures the rows the same way, so a wide heading no
  longer hides a floating column (#874).
- `TEXT_COLUMN_GAP` leaves a column that continues a grid of numbered cells
  at the cells' own spacing (the totals beside a heatmap, within a tenth of
  that spacing). A column that is neither close nor in step gets both
  places in the hint (#875).
- `UNDERUSED_CANVAS` beside columns and their descriptions names
  `dm.place_columns`, which spends no x range on the text, instead of a
  new x limit to guess (#876).
- The skill's look-at-it step says where things set in open space go: in
  the middle of that space, not against the frame, and a band's label
  inside the band or wholly beside it (#877).
- The skill's rendered-figure review compares the margins of the visible
  group, looks for clearance around insets and annotations, and aligns a
  custom key as a block with the marks it describes (#859, #860, #861).
- Removed the Korean role-colour notice because it describes a preset convention (#806).
- The skill says when a single plot's title belongs on the canvas: where long
  category names push the plot well off the figure's centre, `fig.suptitle`
  sits better than `ax.set_title`, which stays the default (#819).
- The skill names the width each preset's text is sized for (17 cm for
  `report` and `scientific`, 25 cm for `poster` and `presentation`), lets
  the height follow the content, and says a bigger medium takes its preset,
  not more centimetres; a deck is slides. Agents had drawn posters at 40 cm
  and a board deck at 24 cm in `report` text, which then read small (#844).
- The skill says what to do where things overlap: shapes are filled so the
  one in front covers the one behind (a ridgeline's ridges take the
  background colour) and the smaller goes on top, and a label moved away
  from its mark keeps a thin line to it. Ridgelines had been drawn as lines
  crossing each other and slope-chart labels left floating (#846).
- The skill says text size encodes nothing: text of one kind (the values
  in cells, the names of rows) has one size across the figure, and what does
  not fit its mark goes beside it or is left out. A Marimekko had its
  narrowest column's values in smaller type than the rest (#849).

## 0.9.0 — 2026-11-22

Fixes found while drawing with 0.8.0, plus three public catalogs. A minor
bump, not a patch: it adds public names and changes the legend text size and
grid canvas sizes.

### Added

- `dm.lint_rules()` lists the rules `dm.lint_code` checks: `id`, `severity`,
  `message` and `fix`, read from the same catalog.
- `dm.list_aspects()` lists the aspect tokens `dm.figsize` reads, each with
  its height-over-width `ratio`, and `dm.list_color_libraries()` the colour
  libraries registered with matplotlib (`prefix`, `label`) (#777).
- `dm.check` reports `SMALL_PANEL`, a plot too small for its text (#782).
- Panel letters run into their titles, or all sit inside the plots when one
  does not fit (#798).

### Changed

- Legend text is 6.5 pt on `scientific` and `report`, 6 pt on `minimal`
  (#795).
- Default grids leave their plots room for their text (#796).

### Fixed

- Every `dm.lw`, `dm.fs` and `dm.fw` step is drawable: in 0.8.0 `dm.lw(-1)`
  returned 0 and `dm.lw(-2)` a negative width, so lines drawn with them
  vanished (#789).
- A figure title, a `dm.figure_legend` above the panels and the panel titles
  stack in that order; in 0.8.0 the legend covered the figure title (#785,
  #792, #805).
- `MISSING_AXIS_LABEL` leaves an x axis of years alone and names the right
  axis (#763, #781, #804).
- An x axis of years ticks at whole years, an axis of whole numbers at whole
  numbers (#791, #802).
- A title wider than the canvas keeps its plot; grid rows part for their tick
  labels (#783, #787).
- `CROSS_AXES_OVERLAP` reports a title running into a colorbar (#771, #781).
- `place_legend` and `figure_legend` show the handles and labels the caller
  gives; `label_bars` takes some of the bars (#778, #789).
- A `dm.add_note` line sits the layout margin from the canvas corner (#779).
- The layout leaves what the user set (rotation, moved legends, own title
  transforms) and figures with parasite axes as they were (#794, #797).
- The bundled skill and the repository skill match again: this release ships
  the skill text that had changed on `develop` since 0.8.0 (#804).

### Known

- A `-kr` preset prints the `dc.pos`/`dc.neg` locale note on every run
  (#806).

## 0.8.0 — 2026-11-16

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
- The skill's one source is `skills/dartwork-mpl/` at the repository root, so
  `npx skills add dartworklabs/dartwork-mpl` finds it; the package carries the
  same folder. `SKILL.md` names the version it was written for, and an agent
  checks it against `dm.__version__`.
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
