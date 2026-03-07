"""Figure I/O: save, display, and format helpers.

Provides ``save_formats``, ``show``, and ``save_and_show`` for
persisting matplotlib figures and rendering SVGs in Jupyter.
"""

from __future__ import annotations

__all__ = ["save_formats", "save_and_show", "show"]

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
    """Save a figure in multiple formats.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        Figure to save.
    image_stem : str
        Base filename without extension.
    formats : tuple, optional
        Tuple of format extensions to save.
    bbox_inches : str or Bbox, optional
        Bounding box in inches.
    validate : bool, optional
        If True, run visual validation before saving and print
        ``[VISUAL]`` warnings to stdout.  Default True.
    **kwargs
        Additional arguments passed to savefig.
    """
    if validate:
        from .validate import validate_figure

        validate_figure(fig)

    create_parent_path(image_stem)
    for fmt in formats:
        fig.savefig(f"{image_stem}.{fmt}", bbox_inches=bbox_inches, **kwargs)


def show(image_path: str, size: int = 600, unit: str = "pt") -> None:
    """Display an SVG image with specified size.

    Parameters
    ----------
    image_path : str
        Path to the SVG image.
    size : int, optional
        Desired width in specified units.
    unit : str, optional
        Unit for size ('pt', 'px', etc.).
    """
    from IPython.display import HTML, SVG, display

    svg_obj = SVG(data=image_path)

    desired_width = size

    # Parse SVG dimensions with defensive handling.
    dom = minidom.parseString(svg_obj.data)
    width_attr = dom.documentElement.getAttribute("width") or ""
    height_attr = dom.documentElement.getAttribute("height") or ""

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
                old, f'width="{desired_width}{unit}"',
            )
            break

    # Replace height attribute.
    for h_str in (str(height), str(int(height))):
        old = f'height="{h_str}{unit}"'
        if old in svg_obj.data:
            svg_obj.data = svg_obj.data.replace(
                old, f'height="{desired_height}{unit}"',
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
    """Save a figure and display it.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        Figure to save and display.
    image_path : str, optional
        Path to save the image. If None, uses a temporary file.
    size : int, optional
        Display size.
    unit : str, optional
        Unit for size.
    **kwargs
        Additional arguments passed to savefig.
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
