"""Colormap management utilities for matplotlib.

This module handles loading and registration of custom colormaps from
text files in the package's asset directory.
"""

from pathlib import Path

import matplotlib as mpl
import matplotlib.colors as mcolors


def _parse_colormap(
    path: str | Path, reverse: bool = False
) -> mcolors.ListedColormap:
    """
    Parse a colormap from a text file and create a matplotlib ListedColormap.

    Parameters
    ----------
    path : str or Path
        Path to the colormap text file containing RGB values.
    reverse : bool, optional
        If True, reverse the colormap order. Default is False.

    Returns
    -------
    matplotlib.colors.ListedColormap
        A ListedColormap object with the parsed colors.
        The colormap name will be 'dm.{filename}' or 'dm.{filename}_r'
        if reversed.
    """
    path_obj: Path = Path(path)

    colors: list[list[float]] = []
    with open(path_obj) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            color: list[float] = [float(v) for v in line.split()]
            colors.append(color)

    if reverse:
        colors = colors[::-1]
        name: str = f"dm.{path_obj.stem}_r"
    else:
        name = f"dm.{path_obj.stem}"

    return mcolors.ListedColormap(colors, name=name)


def _load_colormaps() -> None:
    """
    Load all colormap files from the asset/cmap directory and register them.

    This function automatically discovers all .txt files in the
    asset/cmap directory, parses them as colormaps, and registers both
    normal and reversed versions with matplotlib's colormap registry.

    Notes
    -----
    This function is automatically called when the module is imported.
    """
    root_dir: Path = Path(__file__).parent / "asset/cmap"
    for path in root_dir.glob("*.txt"):
        cmap: mcolors.ListedColormap = _parse_colormap(path)
        mpl.colormaps.register(cmap=cmap)

        cmap_r: mcolors.ListedColormap = _parse_colormap(path, reverse=True)
        mpl.colormaps.register(cmap=cmap_r)

_loaded: bool = False


def ensure_loaded() -> None:
    """Ensure colormaps are loaded and registered."""
    global _loaded
    if not _loaded:
        _load_colormaps()
        _loaded = True
