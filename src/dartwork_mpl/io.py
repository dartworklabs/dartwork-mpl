"""Figure I/O management utilities.

Provides functions for saving Matplotlib figures in various formats and
rendering them as SVG or other image formats in Jupyter environments.
"""

from __future__ import annotations

__all__ = ["save_and_show", "save_formats", "show"]

from pathlib import Path
from tempfile import NamedTemporaryFile
from xml.dom import minidom

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from ._helpers import create_parent_path


def save_formats(
    fig: Figure,
    image_stem: str,
    formats: tuple[str, ...] = ("png", "pdf"),
    bbox_inches: str | None = None,
    validate: bool = True,
    **kwargs,
) -> None:
    """Save a figure in multiple specified formats at once.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        The Matplotlib figure to save.
    image_stem : str
        Base path and filename without extension.
    formats : tuple[str, ...], optional
        Tuple of format extensions to save. Default is ("png", "pdf").
    bbox_inches : str | None, optional
        Bounding box setting for the saved figure. Commonly "tight"
        to minimize whitespace. Default is None.
    validate : bool, optional
        If True, performs visual validation before saving and prints
        ``[VISUAL]`` warnings to stdout on issues. Default is True.
    **kwargs
        Additional keyword arguments passed to ``savefig``.
    """
    if validate:
        from .validate import validate_figure

        validate_figure(fig)

    create_parent_path(image_stem)
    for fmt in formats:
        fig.savefig(f"{image_stem}.{fmt}", bbox_inches=bbox_inches, **kwargs)


def show(image_path: str, size: int = 600, unit: str = "pt") -> None:
    """Load an SVG image and display it at the specified size in a browser or Jupyter.

    Parameters
    ----------
    image_path : str
        Path to the SVG image to display.
    size : int, optional
        Desired output width. Default is 600.
    unit : str, optional
        Unit for the width ('pt', 'px', etc.). Default is 'pt'.
    """
    from IPython.display import HTML, SVG, display

    svg_obj = SVG(data=image_path)

    desired_width = size

    # Parse SVG dimensions with defensive handling.
    # The SVG payload is produced by matplotlib's own SVG backend (via
    # IPython.display.SVG) on dartwork-mpl figures, never user-supplied
    # XML, so XXE/billion-laughs vectors do not apply here.
    dom = minidom.parseString(svg_obj.data)  # noqa: S318  # trusted dartwork SVG only
    doc_el = dom.documentElement
    width_attr = doc_el.getAttribute("width") if doc_el else ""
    height_attr = doc_el.getAttribute("height") if doc_el else ""

    try:
        width = float(width_attr.replace(unit, ""))
        height = float(height_attr.replace(unit, ""))
    except ValueError:
        display(HTML(svg_obj.data))
        return

    if width <= 0:
        display(HTML(svg_obj.data))
        return

    aspect_ratio = height / width
    desired_height = int(desired_width * aspect_ratio)

    # Replace width attribute.
    for w_str in (str(width), str(int(width))):
        old = f'width="{w_str}{unit}"'
        if old in svg_obj.data:
            svg_obj.data = svg_obj.data.replace(
                old, f'width="{desired_width}{unit}"'
            )
            break

    # Replace height attribute.
    for h_str in (str(height), str(int(height))):
        old = f'height="{h_str}{unit}"'
        if old in svg_obj.data:
            svg_obj.data = svg_obj.data.replace(
                old, f'height="{desired_height}{unit}"'
            )
            break

    display(HTML(svg_obj.data))


def save_and_show(
    fig: Figure,
    image_path: str | None = None,
    size: int = 600,
    unit: str = "pt",
    **kwargs,
) -> None:
    """Save a figure to disk, then display it in a Jupyter or web environment.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        The Matplotlib figure to save and display.
    image_path : str | None, optional
        Path to save the image. If None, a system temporary file is used.
    size : int, optional
        Display width. Default is 600.
    unit : str, optional
        Unit for the size ('pt', 'px', etc.). Default is 'pt'.
    **kwargs
        Additional keyword arguments passed to ``savefig``.
    """
    if image_path is None:
        tmp = NamedTemporaryFile(suffix=".svg", delete=False)
        tmp_path = tmp.name
        tmp.close()
        try:
            fig.savefig(tmp_path, bbox_inches=None, **kwargs)
            plt.close(fig)
            show(tmp_path, size=size, unit=unit)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    else:
        create_parent_path(image_path)
        fig.savefig(image_path, bbox_inches=None, **kwargs)
        plt.close(fig)
        show(image_path, size=size, unit=unit)
