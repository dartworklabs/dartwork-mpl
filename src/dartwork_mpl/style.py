"""Matplotlib style management utilities.

This module provides functions and classes for loading and applying
matplotlib styles from the package's built-in style library.
"""

import contextlib
import json
from collections.abc import Iterator
from pathlib import Path

import matplotlib.pyplot as plt

__all__ = ["Style", "style", "style_path", "list_styles", "load_style_dict"]


def style_path(name: str) -> Path:
    """
    Get the path to a style file.

    Parameters
    ----------
    name : str
        Name of the style (e.g., 'report', 'scientific').

    Returns
    -------
    Path
        Absolute path to the style file (.mplstyle).

    Raises
    ------
    ValueError
        If the specified style name cannot be found.
    """
    path: Path = Path(__file__).parent / f"asset/mplstyle/{name}.mplstyle"
    if not path.exists():
        raise ValueError(f"Not found style: {name}")

    return path


def list_styles() -> list[str]:
    """
    Return a list of all available styles.

    Returns
    -------
    list[str]
        List of style names.
    """
    path: Path = Path(__file__).parent / "asset/mplstyle"
    return sorted([p.stem for p in path.glob("*.mplstyle")])


def load_style_dict(name: str) -> dict[str, float | str]:
    """
    Read key-value pairs from an mplstyle file.

    Parameters
    ----------
    name : str
        Name of the style to load.

    Returns
    -------
    dict[str, float | str]
        Dictionary of style parameters. Values are converted to float
        where possible; otherwise they are kept as strings.
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
    Class for managing and applying multiple matplotlib styles.

    This class provides functionality for loading style presets and
    stacking multiple styles sequentially.

    Examples
    --------
    >>> import dartwork_mpl as dm
    >>> dm.style.use("scientific")  # Apply a single preset
    >>> dm.style.stack(["base", "lang-kr"])  # Stack multiple styles
    """

    def __init__(self) -> None:
        """Initialize the Style instance and load presets."""
        self.presets: dict[str, list[str]] = {}
        # Load presets
        self.load_presets()

    @staticmethod
    def presets_path() -> Path:
        """
        Get the path to the presets configuration file (presets.json).

        Returns
        -------
        Path
            Path to the presets.json file containing combined style presets.
        """
        return Path(__file__).parent / "asset/mplstyle/presets.json"

    def load_presets(self) -> None:
        """
        Load style presets from the JSON file.

        Reads presets.json and stores the configuration in the instance's
        presets attribute.
        """
        with open(self.presets_path()) as f:
            self.presets = json.load(f)

    @staticmethod
    def stack(style_names: list[str]) -> None:
        """
        Stack multiple styles in order.

        Applies multiple style files sequentially. Later styles override
        values set by earlier ones for the same keys.

        Parameters
        ----------
        style_names : list[str]
            List of style names to apply. Styles are applied in order,
            with later entries taking precedence.

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
        plt.style.use([style_path(style_name) for style_name in style_names])

    def use(self, preset_name: str | list[str], **kwargs: float | str) -> None:
        """
        Apply a preset style configuration or a list of presets.

        This is the recommended way to apply styles in this module.
        Presets are pre-optimized combinations of styles for specific use cases.

        Parameters
        ----------
        preset_name : str or list of str
            Name of the preset to apply. Available presets:
            - "scientific": Academic papers (default English)
            - "report": Documents, reports, and dashboards
            - "minimal": Tufte-style with minimal lines and ticks
            - "presentation": Slide presentations
            - "poster": Conference posters and large displays
            - "web": Web pages and documentation
            - "dark": Dark background theme
            - "scientific-kr": Academic papers (Korean fonts)
            - "report-kr": Reports and dashboards (Korean fonts)
            - "minimal-kr": Minimal style (Korean fonts)
            - "presentation-kr": Presentations (Korean fonts)
            - "poster-kr": Conference posters (Korean fonts)
            - "web-kr": Web pages (Korean fonts)
            - "dark-kr": Dark theme (Korean fonts)
        **kwargs : float | str
            Additional rcParams to override the preset defaults (e.g.,
            font_size=12). Both underscore (font_size) and dot (font.size)
            notation are supported.

        Raises
        ------
        KeyError
            If the requested preset name is not found in the presets dictionary.

        Examples
        --------
        >>> import dartwork_mpl as dm
        >>> dm.style.use("scientific")
        >>> dm.style.use("presentation-kr", font_size=16)
        >>> dm.style.use(["scientific", "dark"])  # Stack multiple presets
        """
        # Handle both single string and list of strings
        if isinstance(preset_name, list):
            # Stack multiple presets in order
            style_list = []
            for name in preset_name:
                if name not in self.presets:
                    raise KeyError(f"Preset '{name}' not found")
                style_list.extend(self.presets[name])
            self.stack(style_list)
        else:
            # Single preset
            if preset_name not in self.presets:
                raise KeyError(f"Preset '{preset_name}' not found")
            self.stack(self.presets[preset_name])

        if kwargs:
            overrides = {}
            for k, v in kwargs.items():
                k_dot = k.replace("_", ".")
                if k_dot in plt.rcParams:
                    overrides[k_dot] = v
                else:
                    overrides[k] = v
            plt.rcParams.update(overrides)

    @contextlib.contextmanager
    def context(
        self, preset_name: str, **kwargs: float | str
    ) -> Iterator[None]:
        """
        Context manager that temporarily applies a style within a code block.

        Parameters
        ----------
        preset_name : str
            Name of the preset to apply.
        **kwargs : float | str
            Additional rcParams to override.

        Examples
        --------
        >>> with dm.style.context("dark"):
        ...     plt.plot([1, 2, 3])
        """
        if preset_name not in self.presets:
            raise KeyError(f"Preset '{preset_name}' not found")

        style_list: list[Path | dict[str, float | str]] = [
            style_path(style_name) for style_name in self.presets[preset_name]
        ]

        if kwargs:
            overrides: dict[str, float | str] = {}
            for k, v in kwargs.items():
                k_dot = k.replace("_", ".")
                if k_dot in plt.rcParams:
                    overrides[k_dot] = v
                else:
                    overrides[k] = v
            style_list.append(overrides)

        with plt.style.context(style_list):
            yield

    def presets_dict(self) -> dict[str, list[str]]:
        """
        Return all available presets as a dictionary.

        Returns
        -------
        dict[str, list[str]]
            Dictionary mapping preset names (keys) to their constituent
            style lists (values).
        """
        return dict(self.presets.items())


style: Style = Style()
