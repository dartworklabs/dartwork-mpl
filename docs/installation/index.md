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
uv add git+https://github.com/dartwork-repo/dartwork-mpl

# Or install directly into the current environment
uv pip install git+https://github.com/dartwork-repo/dartwork-mpl

# Install a specific branch or tag
uv add git+https://github.com/dartwork-repo/dartwork-mpl@main
```

> **Why uv?** It's 10-100x faster than pip, handles dependency resolution better, and integrates seamlessly with modern Python workflows.

:::

:::{tab-item} 📦 pip
:sync: pip

Use the standard Python package installer. This works with any Python environment.

```bash
# Install from GitHub
pip install git+https://github.com/dartwork-repo/dartwork-mpl

# Upgrade to the latest version
pip install --upgrade git+https://github.com/dartwork-repo/dartwork-mpl

# Install a specific branch
pip install git+https://github.com/dartwork-repo/dartwork-mpl@main
```

> **Note:** Make sure you have Git installed on your system, as pip needs it to clone the repository.

:::

::::

## Basic Import

Once installed, import **dartwork-mpl** alongside matplotlib. The package is typically imported as `dm` for convenience.

```{code-block} python
:caption: example.py

import dartwork_mpl as dm
import matplotlib.pyplot as plt
import numpy as np

# Apply a style preset (Recommended)
dm.style.use('scientific')  # Academic papers
```

Available presets (from `presets.json`) are:

- `scientific`, `investment`, `presentation`
- `scientific-kr`, `investment-kr`, `presentation-kr`

Each preset layers one or more of the bundled styles from `asset/mplstyle`
(e.g., `base`, `dmpl`, `dmpl_light`, `font-*`, `lang-kr`). See the
[Usage Guide](../usage_guide/index.md) for the exact mappings.

## Verify Installation

After installation, verify that **dartwork-mpl** is properly installed and accessible:

```{code-block} python
:caption: verify.py

import dartwork_mpl as dm

# Check installed version
print(dm.__version__)  # Should print something like '0.2.1'

# List all available style files
print(dm.list_styles())  # ['base', 'dmpl', 'dmpl_light', 'font-investment', ...]

# Verify color system is working
color = dm.oklch(0.7, 0.15, 150)
print(color.to_hex())  # Should print a hex color string

# Check available prompts
print(dm.list_prompts())  # Available AI assistant prompt guides
```

If these commands run without errors, you're all set! 🎉

> **Troubleshooting:** If you encounter import errors, make sure:
>
> - Your Python environment is activated (if using virtual environments)
> - The package was installed in the correct environment
> - You have matplotlib installed as a dependency
