# Installation

**dartwork-mpl** is a library of utilities and assets for matplotlib that makes creating publication-quality figures easier.

:::{tip}
The **live install picker** above auto-detects your OS and lets you switch
between `uv`, `pip`, `Poetry`, and `conda` with one click — the command box
updates and the **Copy** button copies the exact line you'll paste into your
terminal.
:::

## Quick Install

**dartwork-mpl** is on [PyPI](https://pypi.org/project/dartwork-mpl/), so a
standard install needs **no Git**. Requires Python 3.10+. The package
includes matplotlib style presets, curated color palettes, and layout
utilities.

::::{tab-set}

:::{tab-item} 🚀 uv
:sync: uv

[uv](https://github.com/astral-sh/uv) is a blazingly fast Python package manager written in Rust. It's recommended for modern Python projects.

```bash
# Add to your project dependencies (recommended — updates pyproject.toml)
uv add dartwork-mpl

# Or install into the current environment
uv pip install dartwork-mpl
```

> **Why uv?** It's 10-100x faster than pip, handles dependency resolution better, and integrates seamlessly with modern Python workflows.

:::

:::{tab-item} 📦 pip
:sync: pip

Use the standard Python package installer. This works with any Python environment.

```bash
# Install from PyPI
pip install dartwork-mpl

# Upgrade to the latest release
pip install --upgrade dartwork-mpl
```

:::

::::

Using **Poetry** or **conda**? See the exact commands in the
[Plain text install matrix](#plain-text-install-matrix) below.

### Optional extras

The core install is intentionally lean — add an extra only when you need it:

| Extra | Enables | Example |
|---|---|---|
| `[notebook]` | `dm.show()` inline SVG display in Jupyter | `pip install "dartwork-mpl[notebook]"` |
| `[mcp]` | the MCP server for AI assistants | `uv add "dartwork-mpl[mcp]"` |
| `[ui]` | the interactive parameter viewer | `pip install "dartwork-mpl[ui]"` |

## Plain text install matrix

Static fallback for the live install picker — useful when JavaScript is
disabled (AI agents, terminal browsers, search-engine indexing). The
command is the same on every OS; the only differences are which package
manager you have and whether you want to add the package to a project
file (`uv add`, `poetry add`) or install into the current environment
(`uv pip`, `pip install`).

| Manager | Command |
|---|---|
| `uv` (project) | `uv add dartwork-mpl` |
| `uv` (env) | `uv pip install dartwork-mpl` |
| `pip` | `pip install dartwork-mpl` |
| `Poetry` | `poetry add dartwork-mpl` |
| `conda + pip` | activate the env, then `pip install dartwork-mpl` |

On all three platforms (macOS / Linux / Windows) the commands are
identical apart from shell quoting; Windows users in `cmd.exe` may need
to drop the quotes around extras (e.g. `pip install dartwork-mpl[mcp]`).

## Latest development version

To track the unreleased `main` branch instead of the PyPI release (this
path **does** need Git):

```bash
uv add "git+https://github.com/dartworklabs/dartwork-mpl@main"
# or
pip install "git+https://github.com/dartworklabs/dartwork-mpl@main"
```

Contributors working from a local clone use an editable install
(`uv pip install -e ".[dev]"`) — see the repository README.

## Basic Import

Once installed, import **dartwork-mpl** alongside matplotlib:

```python
import dartwork_mpl as dm
import matplotlib.pyplot as plt

dm.style.use('scientific')  # Apply a style preset
```

Available presets: `scientific`, `report`, `minimal`, `presentation`, `poster`, `web`,
`dark`, and `-kr` variants for Korean. See the [Quick Start](../usage_guide/quickstart.md)
for a full end-to-end example and [Styles and Presets](../usage_guide/styles.md)
for a detailed comparison.

## Verify Installation

After installation, verify that **dartwork-mpl** is properly installed and accessible:

```python
import dartwork_mpl as dm

print(dm.__version__)     # Current installed version
print(dm.list_styles())   # Available style presets
```

If these commands run without errors, you're all set! 🎉

> **Troubleshooting:** If you encounter import errors, make sure:
>
> - Your Python environment is activated (if using virtual environments)
> - The package was installed in the correct environment
> - You have matplotlib installed as a dependency

## Next Steps

::::{grid} 1

:::{grid-item-card} 🚀 Quick Start
Ready to create your first publication-quality figure? Follow the end-to-end
workflow — apply a style, plot, and export in under a minute.

→ [Quick Start](../usage_guide/quickstart.md)
:::

::::
