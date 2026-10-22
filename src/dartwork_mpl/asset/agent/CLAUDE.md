# dartwork-mpl for coding agents

dartwork-mpl is installed here: a design system on top of matplotlib
(style presets, physical sizes, content-aware margins, figure checks).
`Figure` and `Axes` stay native matplotlib objects.

## Load the skill once per project

```bash
python -m dartwork_mpl.skills install
```

This links `.claude/skills/dartwork-mpl` (Claude Code) and
`.agents/skills/dartwork-mpl` (Codex) to the skill inside the installed
package, so it follows upgrades (recreating the environment needs a rerun).
`--claude` or `--codex` picks one agent, `--dest ~` installs for your user,
`--copy` copies (no symlinks, or to check it in), `--force` replaces a
folder you made or edited yourself. Without installing,
`python -m dartwork_mpl.skills path` prints the folder; read its `SKILL.md`
and `references/`.

## The rules on one screen

```python
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use("scientific")  # paper; "report" documents, "presentation" slides
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
ax.plot([0, 1, 2], [1, 3, 2])
dm.simple_layout(fig)       # after drawing; never plt.tight_layout()
dm.save_formats(fig, "output/figure-v1", formats=("png", "pdf"))
```

- Sizes are physical: width `"13cm"` or `dm.cm(13)`; the second argument is
  an aspect token (`"standard"`, `"wide"`, `"slide"`, ...), `"16:9"`, a
  number (height / width) or a height (`"8cm"`). Never `figsize=(w, h)`.
- `-kr` presets (`report-kr`) only when the plot text is Korean.
- Leave `color=` out so the preset cycle applies; named colours
  (`"dc.blue6"`) when asked or to emphasise; explicit user values win.
- Plot values as given: never silently drop, fill or sort rows; keep NaN
  gaps visible (`dm.validate_data(..., allow_nan=True)`).
- Edit only what was asked; keep data, preset, size and everything else.
- Open the saved PNG and read `dm.validate_figure(fig, quiet=True)` before
  calling it done (`CHECK_FAILED` = incomplete validation, say so); save
  each revision under a new stem (`figure-v2`).

## More

- `dm.get_prompt("03-recipes")` cookbook, `dm.get_prompt("01-policy")`
  policy, `dm.get_prompt("02-anti-patterns")` lint catalog.
- `dm.lint_code(code)` checks a script; `help(dm.figsize)` and friends
  document every function.
- MCP server (extra `dartwork-mpl[mcp]`): the `dartwork-mpl-mcp` command.
