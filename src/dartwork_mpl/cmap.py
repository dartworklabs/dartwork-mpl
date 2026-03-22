"""Colormap management utilities for Matplotlib.

Loads custom colormaps from text files in the package's asset/cmap
directory and registers them with matplotlib.
"""

from pathlib import Path

import matplotlib as mpl
import matplotlib.colors as mcolors

__all__ = ["ensure_loaded"]


def _parse_colormap(
    path: str | Path, reverse: bool = False
) -> mcolors.ListedColormap:
    """Parse a text file into a ListedColormap object.

    Parameters
    ----------
    path : str | Path
        Path to a colormap text file containing RGB values.
    reverse : bool, optional
        If True, reverses the color order. Default is False.

    Returns
    -------
    matplotlib.colors.ListedColormap
        A ListedColormap populated with the parsed colors.
        The colormap is named ``'dc.{filename}'`` by default, or
        ``'dc.{filename}_r'`` if reversed.
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
        name: str = f"dc.{path_obj.stem}_r"
    else:
        name = f"dc.{path_obj.stem}"

    return mcolors.ListedColormap(colors, name=name)


def _load_colormaps() -> None:
    """Load and register all colormap files from the ``asset/cmap`` directory.

    Scans for all ``.txt`` files in the asset directory, parses them
    into colormaps, and registers both the normal and reversed versions
    with matplotlib's colormap registry.

    Notes
    -----
    This function is called automatically once when the library is
    imported; users do not need to call it directly.
    """
    root_dir: Path = Path(__file__).parent / "asset/cmap"
    for path in root_dir.glob("*.txt"):
        cmap: mcolors.ListedColormap = _parse_colormap(path)
        mpl.colormaps.register(cmap=cmap)

        cmap_r: mcolors.ListedColormap = _parse_colormap(path, reverse=True)
        mpl.colormaps.register(cmap=cmap_r)


_loaded: bool = False


def ensure_loaded() -> None:
    """Ensure all custom colormaps are loaded and registered."""
    global _loaded
    if not _loaded:
        _load_colormaps()
        _loaded = True
