# dartwork-mpl

A thin layer on top of matplotlib for publication-quality figures. `Figure`
and `Axes` stay native: you keep writing matplotlib, and dartwork-mpl adds a
style preset, physical sizes, deterministic margins and a figure checker.

It is built for one thing: turn on the bundled skill and the MCP server in
your coding agent, say "draw this", and get a beautiful chart.

## Install

```bash
pip install dartwork-mpl            # the library
pip install "dartwork-mpl[mcp]"     # plus the MCP server
```

Python 3.11 or later, matplotlib 3.11.2 or later.

## First figure

```python
import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("scientific")                                      # preset by purpose
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))  # physical width + aspect
ax.plot([0, 1, 2, 3], [1, 3, 2, 4], label="signal")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Level")
dm.simple_layout(fig)                                           # content-aware margins
print(dm.check(fig))                                            # defects, if any
dm.save_formats(fig, "out", formats=("png", "pdf"))
```

Sizes take unit strings (`"13cm"`, `"5in"`) or `dm.cm(13)`; text and line
sizes are relative to the preset (`dm.fs(1)`, `dm.lw(0)`, `dm.fw(1)`), so a
figure survives a change of preset.

## For coding agents

```bash
python -m dartwork_mpl.guide install    # link the skill into your project
```

The skill is the single source of the plotting rules. The MCP server
(`dartwork-mpl-mcp`, stdio) exposes five tools:

| Tool | Does |
|---|---|
| `guide` | the skill, or one reference page |
| `search_reference` | find templates, presets, colours, lint rules |
| `get_reference` | a template's source, a preset's or colour's values |
| `lint` | anti-pattern lint; runs nothing |
| `render` | run the code once, return the image, source, check report and manifest |

`render` executes the code it is given with your user's rights. It is not a
sandbox.

## Developing

```bash
uv sync
uv run ruff check && uv run ruff format --check
uv run basedpyright
uv run pytest -q -n auto --mpl
```

Read [`docs/handbook/index.md`](docs/handbook/index.md) first: purpose,
structure, invariants and gates. Agents start at [`CLAUDE.md`](CLAUDE.md).

## License

See [`LICENSE`](LICENSE).
