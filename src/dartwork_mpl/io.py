"""Figure I/O management utilities.

Provides functions for saving Matplotlib figures in various formats and
rendering them as SVG or other image formats in Jupyter environments.
"""

from __future__ import annotations

__all__ = ["save_and_show", "save_formats", "show"]

import gzip
import io
import warnings
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from xml.dom import minidom
from xml.parsers.expat import ExpatError

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from ._helpers import create_parent_path

# Image extensions matplotlib's savefig knows how to write — if a caller
# passes a path that already ends with one of these, we strip it so the
# requested ``formats`` are appended cleanly instead of producing
# ``name.png.png`` / ``name.png.svg``.
_KNOWN_IMAGE_SUFFIXES = frozenset(
    {
        ".png",
        ".pdf",
        ".svg",
        ".svgz",
        ".eps",
        ".ps",
        ".jpg",
        ".jpeg",
        ".tif",
        ".tiff",
        ".webp",
        ".raw",
        ".rgba",
    }
)


def _normalize_image_stem(image_stem: str) -> str:
    """Strip a trailing image suffix from ``image_stem`` if present.

    Callers occasionally pass ``"out/chart.png"`` instead of the
    documented ``"out/chart"`` (often by reusing a path variable
    that already carries an extension). Without normalization
    ``save_formats(..., formats=("png", "svg"))`` would emit
    ``chart.png.png`` and ``chart.png.svg`` — silent file-naming
    bugs that pollute output directories. Normalize once at the
    boundary and emit a :class:`UserWarning` so call sites can be
    cleaned up over time.
    """
    suffix = Path(image_stem).suffix.lower()
    if suffix in _KNOWN_IMAGE_SUFFIXES:
        normalized = image_stem[: -len(suffix)]
        warnings.warn(
            (
                f"save_formats: image_stem {image_stem!r} ends with image "
                f"suffix {suffix!r}; stripping to {normalized!r}. "
                "Pass the path *without* an extension to silence this."
            ),
            UserWarning,
            stacklevel=3,
        )
        return normalized
    return image_stem


def _with_reproducible_metadata(
    caller_metadata: dict[str, Any] | None, drop_key: str
) -> dict[str, Any]:
    """Return savefig ``metadata`` that drops a churning timestamp field.

    Matplotlib's SVG / PDF backends embed a wall-clock timestamp
    (``Date`` in SVG's ``<dc:date>``, ``CreationDate`` in PDF) that makes
    every re-render differ even when the plotted data is identical.
    Setting the field to ``None`` omits it entirely, so an unchanged
    figure serialises to a byte-identical file. The caller always wins:
    if they passed a ``metadata`` dict that already sets ``drop_key`` it is
    returned unchanged; otherwise a copy with ``drop_key=None`` added is
    returned, leaving their other keys intact.
    """
    if caller_metadata is None:
        return {drop_key: None}
    if drop_key in caller_metadata:
        return caller_metadata
    merged = dict(caller_metadata)
    merged[drop_key] = None
    return merged


def _save_deterministic_svgz(
    fig: Figure, out: str, bbox_inches: str | None, svg_kwargs: dict[str, Any]
) -> None:
    """Write SVGZ with a fixed gzip header timestamp."""
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches=bbox_inches, **svg_kwargs)
    with (
        open(out, "wb") as raw,
        gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed,
    ):
        compressed.write(buf.getvalue())


def save_formats(
    fig: Figure,
    image_stem: str,
    formats: tuple[str, ...] = ("png", "pdf"),
    bbox_inches: str | None = None,
    validate: bool = True,
    *,
    validate_quiet: bool = False,
    adopt_orphan_tick_font: bool | None = None,
    **kwargs: Any,
) -> None:
    """Save a figure in multiple specified formats at once.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        The Matplotlib figure to save.
    image_stem : str
        Base path and filename without extension. If the value
        accidentally ends with a known image suffix (``.png``,
        ``.pdf``, ``.svg``, …) it is stripped automatically and a
        :class:`UserWarning` is emitted — prevents double-extension
        output like ``chart.png.png``.
    formats : tuple[str, ...], optional
        Tuple of format extensions to save. Default is ("png", "pdf").
    bbox_inches : str | None, optional
        Bounding box setting for the saved figure. Commonly "tight"
        to minimize whitespace. Default is None.
    validate : bool, optional
        If True, performs visual validation before saving and prints
        ``[VISUAL]`` warnings to stdout on issues. Default is True.
        Pair with ``validate_quiet=True`` to keep the check but
        suppress the stdout output.
    validate_quiet : bool, optional
        If ``True`` and ``validate=True``, runs the visual checks but
        does not print ``[VISUAL]`` warnings to stdout. The returned
        warning list inside :func:`~dartwork_mpl.validate.validate_figure`
        is unchanged; this only silences the print side-effect for
        automated pipelines that don't want noise but still want the
        check to run. Default is ``False`` (print as before).
    adopt_orphan_tick_font : bool | None, optional
        If ``True``, tick labels (and offset text) on any axis that has
        no axis label adopt that axis's label font before saving, via
        :func:`~dartwork_mpl.layout.adopt_axis_label_font`. This guarantees
        the saved output reflects the adoption even when
        :func:`~dartwork_mpl.layout.simple_layout` was not called (it
        already applies the same step by default). Default is ``None`` —
        the value is read from
        :data:`dartwork_mpl.config.adopt_orphan_tick_font` (itself
        defaulting to ``True``), so set ``dm.config.adopt_orphan_tick_font
        = False`` once to flip every call site at once. Pass ``True`` /
        ``False`` explicitly to override per call.
    **kwargs
        Additional keyword arguments passed to ``savefig``. A
        ``metadata`` dict is honoured (see the Reproducibility note).

    Notes
    -----
    **Reproducibility.** SVG and PDF output is deterministic by default:
    the SVG element ids are pinned with a fixed ``svg.hashsalt`` derived
    from the output basename, and the wall-clock timestamp each backend
    would otherwise embed (SVG ``<dc:date>``, PDF ``/CreationDate``) is
    dropped, so re-rendering an unchanged figure yields a byte-identical
    file instead of churning version control. PNG is left untouched.
    To override: pass your own ``metadata={"Date": ...}`` /
    ``metadata={"CreationDate": ...}`` to keep a timestamp (the caller
    always wins; other metadata keys are preserved), or set
    ``matplotlib.rcParams["svg.hashsalt"]`` globally to keep your own salt
    (a non-``None`` ambient salt is never overridden). No global rcParams
    state is mutated — the salt is applied via a scoped ``rc_context``.

    When the adoption is on (whether via this keyword or the
    :data:`dartwork_mpl.config` default), this call **mutates the
    figure**: it restyles the tick-label fonts of any unlabeled axis,
    and the change persists after the call. This is the one mutation
    ``save_formats`` performs (it otherwise only reads and writes). It
    is idempotent and matches what ``simple_layout`` already applies.
    It does **not** re-fit margins — call ``simple_layout`` for layouts
    that must grow to fit enlarged orphan ticks. On figures using
    matplotlib ``constrained_layout``, the font change can trigger a
    re-layout on the next draw (expected matplotlib behavior). Pass
    ``adopt_orphan_tick_font=False`` to keep the figure untouched.
    """
    if adopt_orphan_tick_font is None:
        from .config import config

        adopt_orphan_tick_font = config.adopt_orphan_tick_font

    if adopt_orphan_tick_font:
        from .layout import adopt_axis_label_font

        adopt_axis_label_font(fig)

    if validate:
        from .validate import validate_figure

        validate_figure(fig, quiet=validate_quiet)

    image_stem = _normalize_image_stem(image_stem)
    create_parent_path(image_stem)
    # Salt SVG element ids with the output basename so a re-render of an
    # unchanged figure is byte-identical (see the Reproducibility note).
    salt = Path(image_stem).name
    caller_metadata = kwargs.get("metadata")
    for fmt in formats:
        # Accept both ``"png"`` and ``".png"`` — without the lstrip a
        # leading-dot format produced ``name..png``.
        fmt = fmt.lstrip(".")
        out = f"{image_stem}.{fmt}"
        if fmt in ("svg", "svgz"):
            svg_kwargs = dict(kwargs)
            svg_kwargs["metadata"] = _with_reproducible_metadata(
                caller_metadata, "Date"
            )
            # Only pin the hashsalt when the caller hasn't set one globally
            # — a user who configured ``svg.hashsalt`` for their own
            # reproducible build keeps it.
            if plt.rcParams["svg.hashsalt"] is None:
                with plt.rc_context({"svg.hashsalt": salt}):
                    if fmt == "svgz":
                        _save_deterministic_svgz(
                            fig, out, bbox_inches, svg_kwargs
                        )
                    else:
                        fig.savefig(out, bbox_inches=bbox_inches, **svg_kwargs)
            else:
                if fmt == "svgz":
                    _save_deterministic_svgz(fig, out, bbox_inches, svg_kwargs)
                else:
                    fig.savefig(out, bbox_inches=bbox_inches, **svg_kwargs)
        elif fmt == "pdf":
            pdf_kwargs = dict(kwargs)
            pdf_kwargs["metadata"] = _with_reproducible_metadata(
                caller_metadata, "CreationDate"
            )
            fig.savefig(out, bbox_inches=bbox_inches, **pdf_kwargs)
        else:
            fig.savefig(out, bbox_inches=bbox_inches, **kwargs)


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

    Raises
    ------
    ImportError
        If IPython is not installed. ``show`` renders inline in Jupyter
        via IPython, which is an optional extra — install it with
        ``pip install "dartwork-mpl[notebook]"``.
    """
    try:
        from IPython.display import HTML, SVG, display
    except ImportError as exc:  # pragma: no cover - exercised via mock
        raise ImportError(
            "dm.show() needs IPython for inline Jupyter display, which is "
            "an optional extra. Install it with "
            "'pip install \"dartwork-mpl[notebook]\"' "
            "(or 'uv add \"dartwork-mpl[notebook]\"')."
        ) from exc

    def _display_svg_html(svg_data: str) -> None:
        """Wrap the IPython HTML-display call to centralise typing."""
        display(HTML(svg_data))  # type: ignore[no-untyped-call]

    # ``show`` renders SVG only. A non-SVG path (``.png`` / ``.pdf`` or an
    # extensionless file) makes IPython's ``SVG`` raise an XML ExpatError
    # — either while reading the file here or when we re-parse the payload
    # below. Convert both to one clear message pointing at
    # ``save_and_show`` (which dispatches by format) instead of surfacing
    # a raw XML error. The payload is matplotlib's own SVG backend
    # output, never user-supplied XML, so XXE/billion-laughs don't apply.
    try:
        svg_obj = SVG(data=image_path)  # type: ignore[no-untyped-call]
        dom = minidom.parseString(svg_obj.data)  # trusted dartwork SVG only
    except ExpatError as exc:
        raise ValueError(
            f"dm.show() displays SVG only, but {image_path!r} is not valid "
            "SVG. Save with a '.svg' path, or use dm.save_and_show() which "
            "handles PNG/JPG/PDF too."
        ) from exc

    desired_width = size
    doc_el = dom.documentElement
    width_attr = doc_el.getAttribute("width") if doc_el else ""
    height_attr = doc_el.getAttribute("height") if doc_el else ""

    try:
        width = float(width_attr.replace(unit, ""))
        height = float(height_attr.replace(unit, ""))
    except ValueError:
        _display_svg_html(svg_obj.data)
        return

    if width <= 0:
        _display_svg_html(svg_obj.data)
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

    _display_svg_html(svg_obj.data)


def save_and_show(
    fig: Figure,
    image_path: str | None = None,
    size: int = 600,
    unit: str = "pt",
    *,
    adopt_orphan_tick_font: bool | None = None,
    close_figure: bool = True,
    **kwargs: Any,
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
    adopt_orphan_tick_font : bool | None, optional
        If ``True``, apply :func:`~dartwork_mpl.layout.adopt_axis_label_font`
        before saving so unlabeled axes' tick labels take the axis-label
        font, matching :func:`save_formats`. Mutates the figure (see that
        function's Notes). Default is ``None`` — the value is read from
        :data:`dartwork_mpl.config.adopt_orphan_tick_font` (itself
        defaulting to ``True``). Pass ``True`` / ``False`` explicitly to
        override per call.
    close_figure : bool, optional
        If ``True`` (default), the figure is closed via :func:`plt.close`
        after saving — matching the historical behaviour, where the function
        was intended for one-shot "render-then-display" use in notebooks.
        Pass ``False`` to keep the figure open so you can keep editing it
        (e.g. add an annotation and resave with :func:`save_formats`).
        ``save_formats`` itself never closes; this keyword brings parity.
    **kwargs
        Additional keyword arguments passed to ``savefig``.
    """
    if adopt_orphan_tick_font is None:
        from .config import config

        adopt_orphan_tick_font = config.adopt_orphan_tick_font

    if adopt_orphan_tick_font:
        from .layout import adopt_axis_label_font

        adopt_axis_label_font(fig)

    if image_path is None:
        with NamedTemporaryFile(suffix=".svg", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            fig.savefig(tmp_path, bbox_inches=None, **kwargs)
            if close_figure:
                plt.close(fig)
            show(tmp_path, size=size, unit=unit)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    else:
        create_parent_path(image_path)
        fig.savefig(image_path, bbox_inches=None, **kwargs)
        # matplotlib appends the default format when the path has no
        # recognised extension (``"first"`` -> ``"first.png"``), so
        # resolve the file actually written *before* closing the figure
        # (its canvas is the authoritative list of supported formats).
        saved_path = _resolve_saved_path(image_path, kwargs, fig)
        if close_figure:
            plt.close(fig)
        _display_saved(saved_path, size=size, unit=unit)


def _resolve_saved_path(
    image_path: str, kwargs: dict[str, Any], fig: Figure
) -> str:
    """Return the path ``savefig`` actually wrote for ``image_path``.

    ``savefig`` appends ``format`` / ``rcParams["savefig.format"]`` when
    the path has no recognised extension.
    """
    suffix = Path(image_path).suffix.lstrip(".").lower()
    known = set(fig.canvas.get_supported_filetypes())
    if suffix in known:
        return image_path
    fmt = str(kwargs.get("format") or plt.rcParams["savefig.format"])
    return f"{image_path}.{fmt.lstrip('.')}"


def _display_saved(path: str, *, size: int, unit: str) -> None:
    """Display a saved figure inline, dispatching on its file format."""
    suffix = Path(path).suffix.lower()
    if suffix == ".svg":
        show(path, size=size, unit=unit)
        return
    if suffix in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        try:
            from IPython.display import Image, display
        except ImportError as exc:  # pragma: no cover - mirror show()
            raise ImportError(
                "dm.save_and_show() needs IPython for inline display; "
                "install it with 'pip install \"dartwork-mpl[notebook]\"'."
            ) from exc
        display(Image(filename=path, width=size))  # type: ignore[no-untyped-call]
        return
    # Non-inlineable formats (PDF, EPS, …) were still saved; there is no
    # inline preview, so report the path rather than crashing.
    warnings.warn(
        f"Saved {path!r}; inline preview is only available for SVG and "
        "raster formats, so nothing is displayed for this format.",
        stacklevel=2,
    )
