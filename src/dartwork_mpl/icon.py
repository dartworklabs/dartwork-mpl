"""Icon font utilities for matplotlib plots.

This module provides convenient access to bundled icon fonts
(Material Design Icons, Font Awesome 6) for use in matplotlib
figures. Icons are rendered as text using their Unicode codepoints.

Examples
--------
>>> import dartwork_mpl as dm
>>> mdi = dm.icon_font('mdi')
>>> ax.text(0.5, 0.5, "\U000f050f",  # thermometer
...         fontproperties=mdi, fontsize=20)
"""

from pathlib import Path

from matplotlib import font_manager as fm

_ICON_DIR: Path = Path(__file__).parent / "asset/icon"

_REGISTRY: dict[str, str] = {
    "mdi": "materialdesignicons-webfont.ttf",
    "fa-solid": "Font Awesome 6 Free-Solid-900.otf",
    "fa-regular": "Font Awesome 6 Free-Regular-400.otf",
    "fa-brands": "Font Awesome 6 Brands-Regular-400.otf",
}

__all__ = ["icon_font", "icon_font_path", "list_icon_fonts", "ensure_loaded"]


def icon_font_path(name: str = "mdi") -> Path:
    """Return the filesystem path to a bundled icon font file.

    Parameters
    ----------
    name : str, optional
        Icon font identifier. One of ``'mdi'``, ``'fa-solid'``,
        ``'fa-regular'``, ``'fa-brands'``. Default is ``'mdi'``.

    Returns
    -------
    Path
        Absolute path to the font file.

    Raises
    ------
    ValueError
        If *name* is not a recognized icon font identifier.
    FileNotFoundError
        If the font file does not exist on disk.

    Examples
    --------
    >>> import dartwork_mpl as dm
    >>> path = dm.icon_font_path('mdi')
    >>> path.name
    'materialdesignicons-webfont.ttf'
    """
    ensure_loaded()

    if name not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY))
        raise ValueError(f"Unknown icon font '{name}'. Available: {available}")

    path = _ICON_DIR / _REGISTRY[name]
    if not path.exists():
        raise FileNotFoundError(
            f"Icon font file not found: {path}. Please reinstall dartwork-mpl."
        )
    return path


def icon_font(name: str = "mdi") -> fm.FontProperties:
    """Return a :class:`~matplotlib.font_manager.FontProperties` for
    an icon font, ready to use with ``ax.text()``.

    Parameters
    ----------
    name : str, optional
        Icon font identifier. One of ``'mdi'``, ``'fa-solid'``,
        ``'fa-regular'``, ``'fa-brands'``. Default is ``'mdi'``.

    Returns
    -------
    FontProperties
        Matplotlib FontProperties object.

    Examples
    --------
    >>> import dartwork_mpl as dm
    >>> mdi = dm.icon_font('mdi')
    >>> ax.text(0.5, 0.5, "\U000f050f",
    ...         fontproperties=mdi, fontsize=20,
    ...         ha='center', va='center')
    """
    ensure_loaded()
    return fm.FontProperties(fname=str(icon_font_path(name)))


def list_icon_fonts() -> list[str]:
    """Return a sorted list of available icon font identifiers.

    Returns
    -------
    list[str]
        Available font names (e.g. ``['fa-brands', 'fa-regular',
        'fa-solid', 'mdi']``).
    """
    return sorted(_REGISTRY.keys())


def _register_icon_fonts() -> None:
    """Register all bundled icon fonts with matplotlib's font manager.

    This function is called automatically on module import.
    """
    for filename in _REGISTRY.values():
        font_path = _ICON_DIR / filename
        if font_path.exists():
            fm.fontManager.addfont(str(font_path))


_loaded: bool = False


def ensure_loaded() -> None:
    """Ensure icon fonts are loaded and registered."""
    global _loaded
    if not _loaded:
        _register_icon_fonts()
        _loaded = True
