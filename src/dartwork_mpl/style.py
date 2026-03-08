"""Matplotlib style management utilities.

This module provides functions and classes for managing and applying
matplotlib styles from the package's style library.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt

__all__ = [
    "Style",
    "style",
    "style_path",
    "list_styles",
    "load_style_dict",
]


def style_path(name: str) -> Path:
    """
    Get the path to a style file.

    Parameters
    ----------
    name : str
        Name of the style.

    Returns
    -------
    Path
        Path to the style file.

    Raises
    ------
    ValueError
        If the style is not found.
    """
    path: Path = Path(__file__).parent / f"asset/mplstyle/{name}.mplstyle"
    if not path.exists():
        raise ValueError(f"Not found style: {name}")

    return path


def list_styles() -> list[str]:
    """
    List all available styles.

    Returns
    -------
    list[str]
        List of style names.
    """
    path: Path = Path(__file__).parent / "asset/mplstyle"
    return sorted([p.stem for p in path.glob("*.mplstyle")])


def load_style_dict(name: str) -> dict[str, float | str]:
    """
    Load key, value pairs from a mplstyle file.

    Parameters
    ----------
    name : str
        Name of the style.

    Returns
    -------
    dict[str, float | str]
        Dictionary of style parameters. Values are converted to float
        if possible, otherwise kept as strings.
    """
    # Load key, value pair from mplstyle files.
    path: Path = style_path(name)
    style_dict: dict[str, float | str] = {}
    with open(path) as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # Split on first colon only (values may contain colons).
            if ":" not in stripped:
                continue
            key, raw_value = stripped.split(":", maxsplit=1)
            key = key.strip()

            # Strip inline comments: find ' #' outside of quotes.
            value_str = raw_value.split(" #")[0].strip()
            if not value_str:
                continue

            try:
                value_float: float = float(value_str)
                style_dict[key] = value_float
            except ValueError:
                style_dict[key] = value_str

    return style_dict


class Style:
    """
    A class for managing and applying multiple matplotlib styles.

    This class provides functionality to load style presets and apply
    multiple styles in sequence.

    Examples
    --------
    >>> import dartwork_mpl as dm
    >>> dm.style.use("scientific")  # Apply a preset
    >>> dm.style.stack(["base", "lang-kr"])  # Stack multiple styles
    """

    def __init__(self) -> None:
        """Initialize Style instance and load presets."""
        self.presets: dict[str, list[str]] = {}
        # Load presets
        self.load_presets()

    @staticmethod
    def presets_path() -> Path:
        """
        Get the path to the presets file.

        Returns
        -------
        Path
            Path to the presets.json file containing style preset
            definitions.
        """
        return Path(__file__).parent / "asset/mplstyle/presets.json"

    def load_presets(self) -> None:
        """
        Load style presets from the JSON file.

        This method reads the presets.json file and stores the preset
        definitions in the instance's presets attribute.
        """
        with open(self.presets_path()) as f:
            self.presets = json.load(f)

    @staticmethod
    def stack(style_names: list[str]) -> None:
        """
        Stack multiple styles in order.

        This method applies multiple style files in sequence. Later styles
        override earlier ones for conflicting settings.

        Parameters
        ----------
        style_names : list[str]
            List of style names to stack. Styles are applied in order,
            with later styles taking precedence.

        Examples
        --------
        >>> import dartwork_mpl as dm
        >>> dm.style.stack(["base", "font-scientific", "lang-kr"])
        """
        from .cmap import ensure_loaded as ensure_cmaps_loaded
        from .font import ensure_loaded as ensure_fonts_loaded

        # Ensure fonts and colormaps are registered before Matplotlib tries to resolve them
        ensure_fonts_loaded()
        ensure_cmaps_loaded()

        plt.rcParams.update(plt.rcParamsDefault)
        plt.style.use(style_path(style_name) for style_name in style_names)

    def use(self, preset_name: str) -> None:
        """
        Apply a preset style configuration.

        This is the recommended way to apply styles. Presets are predefined
        combinations of styles optimized for specific use cases.

        Parameters
        ----------
        preset_name : str
            Name of the preset to apply. Available presets:
            - "scientific": For academic papers
            - "report": For reports and dashboards
            - "presentation": For presentations
            - "poster": For conference posters and large displays
            - "web": For web pages and documentation
            - "minimal": Tufte-style, no spines/ticks
            - "dark": Dark background theme
            - "scientific-kr": Scientific with Korean font
            - "report-kr": Report with Korean font
            - "presentation-kr": Presentation with Korean font
            - "poster-kr": Poster with Korean font
            - "web-kr": Web/docs with Korean font
            - "minimal-kr": Minimal with Korean font
            - "dark-kr": Dark theme with Korean font

        Raises
        ------
        KeyError
            If the preset name is not found in the presets dictionary.

        Examples
        --------
        >>> import dartwork_mpl as dm
        >>> dm.style.use("scientific")
        >>> dm.style.use("presentation-kr")
        """
        if preset_name not in self.presets:
            raise KeyError(f"Preset '{preset_name}' not found")
        self.stack(self.presets[preset_name])

    def presets_dict(self) -> dict[str, list[str]]:
        """
        Get all available presets as a dictionary.

        Returns
        -------
        dict[str, list[str]]
            Dictionary mapping preset names to their style configuration
            lists.
        """
        return dict(self.presets.items())


style: Style = Style()
