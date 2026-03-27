# Installation

**dartwork-mpl** is a library of utilities and assets for matplotlib that makes creating publication-quality figures easier.

## Quick Install

Install **dartwork-mpl** directly from GitHub. The package includes matplotlib style presets, curated color palettes, and layout utilities.

::::{tab-set}

:::{tab-item} 🚀 uv
:sync: uv

[uv](https://github.com/astral-sh/uv) is a blazingly fast Python package manager written in Rust. It's recommended for modern Python projects.

```bash
# Add to your project dependencies (Recommended)
# This automatically updates your pyproject.toml
uv add git+https://github.com/dartworklabs/dartwork-mpl

# Or install directly into the current environment
uv pip install git+https://github.com/dartworklabs/dartwork-mpl

# Install a specific branch or tag
uv add git+https://github.com/dartworklabs/dartwork-mpl@main
```

> **Why uv?** It's 10-100x faster than pip, handles dependency resolution better, and integrates seamlessly with modern Python workflows.

:::

:::{tab-item} 📦 pip
:sync: pip

Use the standard Python package installer. This works with any Python environment.

```bash
# Install from GitHub
pip install git+https://github.com/dartworklabs/dartwork-mpl

# Upgrade to the latest version
pip install --upgrade git+https://github.com/dartworklabs/dartwork-mpl

# Install a specific branch
pip install git+https://github.com/dartworklabs/dartwork-mpl@main
```

> **Note:** Make sure you have Git installed on your system, as pip needs it to clone the repository.

:::

::::

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
