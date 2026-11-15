# dartwork-mpl

A thin layer on top of matplotlib for publication-quality figures. `Figure`
and `Axes` stay native: you keep writing matplotlib, and dartwork-mpl adds a
style preset, physical sizes, deterministic margins and a figure checker.

It is built for one thing: turn on the bundled skill in your coding agent,
say "draw this", and get a beautiful chart.

## Install

```bash
pip install dartwork-mpl
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

The skill is the single source of the plotting rules. The agent draws with
its own shell (`python plot.py`) and reaches the rest from Python:

| Call | Does |
|---|---|
| `dm.check(fig)` | defects in a drawn figure; changes nothing |
| `dm.lint_code(code)` | anti-pattern lint; runs nothing |
| `dm.guide.search(query)` | rank the guide pages and templates for a request |
| `dm.guide.read(id)` | one guide page or template by id |

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
