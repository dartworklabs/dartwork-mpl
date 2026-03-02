"""Utility functions for matplotlib figure management.

This module provides helper functions for figure layout, font/line
scaling, color mixing, SVG display, and prompt file management.
"""

from pathlib import Path
from shutil import copy2
from tempfile import NamedTemporaryFile
from xml.dom import minidom

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
from IPython.display import HTML, SVG, display
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
from matplotlib.transforms import ScaledTranslation
from scipy.optimize import OptimizeResult, minimize


def _create_parent_path_if_not_exists(path: str | Path) -> None:
    """
    Create parent directory if it doesn't exist.

    Parameters
    ----------
    path : str or Path
        Path to check and create parent directory for.
    """
    path = Path(path)
    if not path.parent.exists():
        path.parent.mkdir(parents=True)


def set_decimal(ax: Axes, xn: int | None = None, yn: int | None = None) -> None:
    """
    Set decimal places for tick labels.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Axes object to modify.
    xn : int, optional
        Number of decimal places for x-axis tick labels.
    yn : int, optional
        Number of decimal places for y-axis tick labels.
    """
    if xn is not None:
        xticks = ax.get_xticks()
        ax.set_xticks(xticks)
        ax.set_xticklabels([f"{x:.{xn}f}" for x in xticks])

    if yn is not None:
        yticks = ax.get_yticks()
        ax.set_yticks(yticks)
        ax.set_yticklabels([f"{y:.{yn}f}" for y in yticks])


def get_bounding_box(boxes: list) -> tuple[float, float, float, float]:
    """
    Get the bounding box that contains all given boxes.

    Parameters
    ----------
    boxes : list
        List of box objects with p0, width, and height attributes.

    Returns
    -------
    tuple
        (min_x, min_y, bbox_width, bbox_height) of the bounding box.
    """
    # Initialize extremes
    min_x = float("inf")
    min_y = float("inf")
    max_x = float("-inf")
    max_y = float("-inf")

    # Iterate through each box
    for box in boxes:
        # Update minimum x and y
        min_x = min(min_x, box.p0[0])
        min_y = min(min_y, box.p0[1])

        # Update maximum x and y
        max_x = max(max_x, box.p0[0] + box.width)
        max_y = max(max_y, box.p0[1] + box.height)

    # Calculate bounding box width and height
    bbox_width = max_x - min_x
    bbox_height = max_y - min_y

    return (min_x, min_y, bbox_width, bbox_height)


def simple_layout(
    fig: Figure,
    gs: GridSpec | None = None,
    margins: tuple[float, float, float, float] = (0.05, 0.05, 0.05, 0.05),
    bbox: tuple[float, float, float, float] = (0, 1, 0, 1),
    verbose: bool = False,
    gtol: float = 1e-2,
    bound_margin: float = 0.2,
    use_all_axes: bool = True,
    importance_weights: tuple[float, float, float, float] = (1, 1, 1, 1),
) -> OptimizeResult:
    """주어진 GridSpec에 대해 간단한 레이아웃을 적용한다.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        Figure 객체.
    gs : matplotlib.gridspec.GridSpec, optional
        GridSpec 객체. None이면 첫 번째 GridSpec 사용.
        기본값은 None.
    margins : tuple[float, float, float, float], optional
        인치 단위 여백 (left, right, bottom, top).
        기본값은 (0.05, 0.05, 0.05, 0.05).
    bbox : tuple[float, float, float, float], optional
        Figure 좌표계 바운딩 박스
        (left, right, bottom, top).
        기본값은 (0, 1, 0, 1).
    verbose : bool, optional
        상세 출력 여부. 기본값은 False.
    gtol : float, optional
        기울기 허용 오차. 목적 함수의 최대 변화량이
        이 값보다 작으면 최적화 중단. 기본값은 1e-2.
    bound_margin : float, optional
        경계 생성을 위한 여백. 기본값은 0.2.
    use_all_axes : bool, optional
        True이면 Figure 내 모든 Axes 사용.
        False이면 주어진 GridSpec의 Axes만 사용.
        기본값은 True.
    importance_weights : tuple[float, float, float, float], optional
        각 타겟의 중요도 가중치
        (left, right, bottom, top).
        기본값은 (1, 1, 1, 1).

    Returns
    ----------
    result : scipy.optimize.OptimizeResult
        최적화 결과.
    """
    if gs is None:
        gs = fig.axes[0].get_gridspec()

    importance_weights = np.array(importance_weights)
    margins = np.array(margins) * fig.get_dpi()

    def fun(x: np.ndarray) -> float:
        gs.update(left=x[0], right=x[1], bottom=x[2], top=x[3])

        if use_all_axes:
            ax_bboxes = [ax.get_tightbbox() for ax in fig.axes]
        else:
            ax_bboxes = [
                ax.get_tightbbox()
                for ax in fig.axes
                if id(ax.get_gridspec()) == id(gs)
            ]

        all_bbox = get_bounding_box(ax_bboxes)

        values = np.array(all_bbox)

        # Targets.
        fbox = fig.bbox
        targets = np.array(
            [
                fbox.width * bbox[0] + margins[0],
                fbox.height * bbox[2] + margins[2],
                fbox.width * (bbox[1] - bbox[0]) - 2 * margins[1],
                fbox.height * (bbox[3] - bbox[2]) - 2 * margins[3],
            ]
        )

        scales = np.array([fbox.width, fbox.height, fbox.width, fbox.height])

        loss = np.square((values - targets) / scales * importance_weights).sum()

        return loss

    # Order: left, right, bottom, top.
    bounds = [
        (bbox[0], bbox[0] + bound_margin),
        (bbox[1] - bound_margin, bbox[1]),
        (bbox[2], bbox[2] + bound_margin),
        (bbox[3] - bound_margin, bbox[3]),
    ]

    result = minimize(
        fun,
        x0=np.array(bounds).mean(axis=1),
        bounds=bounds,
        # # Gradient-free optimization.
        # method='Nelder-Mead',
        # # Relax convergence criteria.
        # options=dict(xatol=1e-3),
        method="L-BFGS-B",
        options={"gtol": gtol},
    )

    return result


def fs(n: int | float) -> float:
    """
    Return base font size + n.

    Parameters
    ----------
    n : int or float
        Value to add to base font size.

    Returns
    -------
    float
        Base font size + n.
    """
    return plt.rcParams["font.size"] + n


def fw(n: int) -> int:
    """
    Return base font weight + 100 * n.
    Only works for integer weights and n.

    Parameters
    ----------
    n : int
        Value to multiply by 100 and add to base font weight.

    Returns
    -------
    int
        Base font weight + 100 * n.
    """
    return plt.rcParams["font.weight"] + 100 * n


def lw(n: int | float) -> float:
    """
    Return base line width + n.

    Parameters
    ----------
    n : int or float
        Value to add to base line width.

    Returns
    -------
    float
        Base line width + n.
    """
    return plt.rcParams["lines.linewidth"] + n


def label_axes(
    axes: list[Axes] | np.ndarray,
    labels: list[str] | None = None,
    fontsize: float = 10,
    fontweight: str = "bold",
    x: float | str = "auto",
    y: float = 1.05,
    **kwargs,
) -> list:
    """
    Add standardized panel labels (a, b, c, ...) to subplot axes.

    Labels are placed at the top-left corner of each axes using
    the axes coordinate system. Default style: bold 11pt lowercase
    letters without parentheses.

    Parameters
    ----------
    axes : list of Axes or ndarray
        Axes objects to label.
    labels : list of str, optional
        Custom labels. If None, uses lowercase alphabet (a, b, c, ...).
    fontsize : float, optional
        Font size in points. Default is 11.
    fontweight : str, optional
        Font weight. Default is 'bold'.
    x : float or 'auto', optional
        X position in axes coordinates. If 'auto' (default), uses
        -0.18 for axes with a y-axis label, -0.02 for axes without.
    y : float, optional
        Y position in axes coordinates. Default is 1.06.
    **kwargs
        Additional keyword arguments passed to ``ax.text()``.

    Returns
    -------
    list
        List of Text objects created.

    Examples
    --------
    >>> import dartwork_mpl as dm
    >>> fig, axes = plt.subplots(1, 3)
    >>> dm.label_axes(axes)           # labels: a, b, c
    >>> dm.label_axes([ax1, ax2])     # same
    >>> dm.label_axes(axes, labels=['i', 'ii', 'iii'])  # custom
    """
    import string

    if isinstance(axes, np.ndarray):
        axes = axes.flatten().tolist()

    if labels is None:
        labels = list(string.ascii_lowercase[: len(axes)])

    texts = []
    for ax, label in zip(axes, labels, strict=False):
        # Auto-detect x position based on ylabel presence
        if x == "auto":
            has_ylabel = ax.get_ylabel().strip() != ""
            x_pos = -0.18 if has_ylabel else -0.02
        else:
            x_pos = x

        t = ax.text(
            x_pos,
            y,
            label,
            transform=ax.transAxes,
            fontsize=fontsize,
            fontweight=fontweight,
            va="bottom",
            ha="left",
            **kwargs,
        )
        texts.append(t)

    return texts


def arrow_axis(
    ax: Axes,
    direction: str,
    label: str,
    *,
    offset: float = -0.05,
    low: str = "Low",
    high: str = "High",
    fontsize: float | None = None,
    fontsize_label: float | None = None,
    pad: float = -0.005,
    weight: str = "normal",
    color: str = "black",
    arrow_kw: dict | None = None,
) -> None:
    """Draw a bidirectional arrow axis with Low/High labels.

    Creates  ``Low ◄── label ──► High``  along a spine edge.
    Text extents are measured dynamically so that *low*'s leading edge
    aligns with the spine start and *high*'s trailing edge aligns with
    the spine end.  Arrows fill the remaining space.

    Parameters
    ----------
    ax : Axes
        Target axes.
    direction : {'x', 'y'}
        ``'x'`` places a horizontal axis below the x-spine;
        ``'y'`` places a vertical axis left of the y-spine
        (text rotated 90° CCW).
    label : str
        Center axis label (e.g. ``'Installation cost'``).
    offset : float, optional
        Axes-fraction distance from the spine.
        Negative values move outside the plot area.
        Default is ``-0.05``.
    low : str, optional
        Text for the low end. Default ``'Low'``.
    high : str, optional
        Text for the high end. Default ``'High'``.
    fontsize : float or None, optional
        Font size for *low*/*high* labels.
        ``None`` → ``fs(-1)`` (current base size − 1).
    fontsize_label : float or None, optional
        Font size for the center *label*.
        ``None`` → ``fs(0)`` (current base size).
    pad : float, optional
        Axes-fraction gap between text edges and arrowheads.
        Negative values push arrows into font side-bearing space
        for a tighter visual fit.  Default ``-0.005``.
    weight : str, optional
        Font weight for all text elements.  Default ``'normal'``.
    color : str, optional
        Color for text and arrows.  Default ``'black'``.
    arrow_kw : dict or None, optional
        Override ``arrowprops`` dict passed to ``ax.annotate``.
        ``None`` → ``dict(arrowstyle='-|>,head_width=0.1',
        color=color, lw=0.25)``.

    Examples
    --------
    >>> import dartwork_mpl as dm
    >>> fig, ax = plt.subplots()
    >>> dm.arrow_axis(ax, 'x', 'Installation cost')
    >>> dm.arrow_axis(ax, 'y', 'Information richness')
    """
    if fontsize is None:
        fontsize = fs(-1)
    if fontsize_label is None:
        fontsize_label = fs(0)
    if arrow_kw is None:
        arrow_kw = {"arrowstyle": "-|>,head_width=0.1", "color": color, "lw": 0.25}

    renderer = ax.get_figure().canvas.get_renderer()
    inv = ax.transAxes.inverted()
    rot_kw = (
        {"rotation": 90, "rotation_mode": "anchor"} if direction == "y" else {}
    )

    # ── place texts ──────────────────────────────────────────
    if direction == "x":
        p_lo, p_hi, p_lb = (0, offset), (1, offset), (0.5, offset)
    else:
        p_lo, p_hi, p_lb = (offset, 0), (offset, 1), (offset, 0.5)

    t_lo = ax.text(
        *p_lo, low, transform=ax.transAxes,
        fontsize=fontsize, fontweight=weight, color=color,
        ha="left", va="center", clip_on=False, **rot_kw,
    )
    t_hi = ax.text(
        *p_hi, high, transform=ax.transAxes,
        fontsize=fontsize, fontweight=weight, color=color,
        ha="right", va="center", clip_on=False, **rot_kw,
    )
    t_lb = ax.text(
        *p_lb, label, transform=ax.transAxes,
        fontsize=fontsize_label, fontweight=weight, color=color,
        ha="center", va="center", clip_on=False, **rot_kw,
    )

    # ── measure extents in axes fraction ─────────────────────
    ax.get_figure().canvas.draw()

    def _edges(t):
        bb = t.get_window_extent(renderer)
        return inv.transform([[bb.x0, bb.y0], [bb.x1, bb.y1]])

    i = 0 if direction == "x" else 1
    lo_end = _edges(t_lo)[1][i]
    hi_start = _edges(t_hi)[0][i]
    lb_lo = _edges(t_lb)[0][i]
    lb_hi = _edges(t_lb)[1][i]

    # ── draw arrows ──────────────────────────────────────────
    def _arrow(tip, tail):
        if direction == "x":
            ax.annotate(
                "", xy=(tip, offset), xytext=(tail, offset),
                xycoords="axes fraction", arrowprops=arrow_kw,
                annotation_clip=False,
            )
        else:
            ax.annotate(
                "", xy=(offset, tip), xytext=(offset, tail),
                xycoords="axes fraction", arrowprops=arrow_kw,
                annotation_clip=False,
            )

    _arrow(lo_end + pad, lb_lo - pad)    # Low  ◄── label
    _arrow(hi_start - pad, lb_hi + pad)  # label ──► High

def mix_colors(
    color1: str | tuple[float, float, float],
    color2: str | tuple[float, float, float],
    alpha: float = 0.5,
) -> tuple[float, float, float]:
    """
    Mix two colors.

    Parameters
    ----------
    color1 : color
        First color (any format accepted by matplotlib).
    color2 : color
        Second color (any format accepted by matplotlib).
    alpha : float, optional
        Weight of the first color, between 0 and 1.

    Returns
    -------
    tuple
        RGB tuple of the mixed color.
    """
    color1 = mcolors.to_rgb(color1)
    color2 = mcolors.to_rgb(color2)

    return tuple(
        alpha * c1 + (1 - alpha) * c2
        for c1, c2 in zip(color1, color2, strict=False)
    )


def pseudo_alpha(
    color: str | tuple[float, float, float],
    alpha: float = 1.0,
    background: str | tuple[float, float, float] = "white",
) -> tuple[float, float, float]:
    """
    Return a color with pseudo alpha.

    Parameters
    ----------
    color : color
        Color to apply pseudo-transparency to.
    alpha : float, optional
        Alpha value between 0 and 1.
    background : color, optional
        Background color to mix with.

    Returns
    -------
    tuple
        RGB tuple of the resulting color.
    """
    return mix_colors(color, background, alpha=alpha)


def cm2in(cm: float) -> float:
    """
    Convert centimeters to inches.

    Parameters
    ----------
    cm : float
        Value in centimeters.

    Returns
    -------
    float
        Value in inches.
    """
    return cm / 2.54


def make_offset(x: float, y: float, fig: Figure) -> ScaledTranslation:
    """
    Create a translation offset for figure elements.

    Parameters
    ----------
    x : float
        X offset in points.
    y : float
        Y offset in points.
    fig : matplotlib.figure.Figure
        Figure to create offset for.

    Returns
    -------
    matplotlib.transforms.ScaledTranslation
        Offset transform.
    """
    dx, dy = x / 72, y / 72
    offset = ScaledTranslation(dx, dy, fig.dpi_scale_trans)

    return offset


def save_formats(
    fig: Figure,
    image_stem: str,
    formats: tuple[str, ...] = ("svg", "png", "pdf", "eps"),
    bbox_inches: str | None = None,
    **kwargs,
) -> None:
    """
    Save a figure in multiple formats.

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
    **kwargs
        Additional arguments passed to savefig.
    """
    _create_parent_path_if_not_exists(image_stem)
    for fmt in formats:
        fig.savefig(f"{image_stem}.{fmt}", bbox_inches=bbox_inches, **kwargs)


def show(image_path: str, size: int = 600, unit: str = "pt") -> None:
    """
    Display an SVG image with specified size.

    Parameters
    ----------
    image_path : str
        Path to the SVG image.
    size : int, optional
        Desired width in specified units.
    unit : str, optional
        Unit for size ('pt', 'px', etc.).
    """
    # SVG 객체 생성
    svg_obj = SVG(data=image_path)

    # 원하는 가로 폭 또는 세로 높이 설정
    desired_width = size

    # SVG 코드에서 현재 가로 폭과 세로 높이 가져오기
    dom = minidom.parseString(svg_obj.data)
    width = float(dom.documentElement.getAttribute("width")[: -len(unit)])
    height = float(dom.documentElement.getAttribute("height")[: -len(unit)])

    # 비율 계산
    aspect_ratio = height / width
    desired_height = int(desired_width * aspect_ratio)

    # 가로 폭과 세로 높이 설정
    if f'width="{width}{unit}"' in svg_obj.data:
        svg_obj.data = svg_obj.data.replace(
            f'width="{width}{unit}"', f'width="{desired_width}{unit}"'
        )
    else:
        width = int(width)
        svg_obj.data = svg_obj.data.replace(
            f'width="{width}{unit}"', f'width="{desired_width}{unit}"'
        )

    if f'height="{height}{unit}"' in svg_obj.data:
        svg_obj.data = svg_obj.data.replace(
            f'height="{height}{unit}"', f'height="{desired_height}{unit}"'
        )
    else:
        height = int(height)
        svg_obj.data = svg_obj.data.replace(
            f'height="{height}{unit}"', f'height="{desired_height}{unit}"'
        )

    # HTML을 사용하여 SVG 이미지 표시
    svg_code = svg_obj.data
    display(HTML(svg_code))


def save_and_show(
    fig: Figure,
    image_path: str | None = None,
    size: int = 600,
    unit: str = "pt",
    **kwargs,
) -> None:
    """
    Save a figure and display it.

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
        with NamedTemporaryFile(suffix=".svg") as f:
            f.close()
            image_path = f.name

            fig.savefig(image_path, bbox_inches=None, **kwargs)
            plt.close(fig)

            show(image_path, size=size, unit=unit)
    else:
        _create_parent_path_if_not_exists(image_path)
        fig.savefig(image_path, bbox_inches=None, **kwargs)
        plt.close(fig)

        show(image_path, size=size, unit=unit)


def prompt_path(name: str) -> Path:
    """
    Get the path to a prompt guide file.

    Parameters
    ----------
    name : str
        Name of the prompt guide
        ('layout-guide' or 'general-guide').

    Returns
    ----------
    Path
        Path to the prompt guide file.

    Raises
    ----------
    ValueError
        If the prompt guide is not found.
    """
    path: Path = Path(__file__).parent / f"asset/prompt/{name}.md"
    if not path.exists():
        raise ValueError(f"Prompt guide not found: {name}")

    return path


def get_prompt(name: str) -> str:
    """
    Read and return the content of a prompt guide file.

    Parameters
    ----------
    name : str
        Name of the prompt guide
        ('layout-guide' or 'general-guide').

    Returns
    ----------
    str
        Content of the prompt guide file.

    Raises
    ----------
    ValueError
        If the prompt guide is not found.
    """
    path = prompt_path(name)
    return path.read_text(encoding="utf-8")


def list_prompts() -> list[str]:
    """
    List all available prompt guide files.

    Returns
    ----------
    list[str]
        List of available prompt guide names.
    """
    path: Path = Path(__file__).parent / "asset/prompt"
    if not path.exists():
        return []
    return sorted([p.stem for p in path.glob("*.md")])


def copy_prompt(name: str, destination: str | Path) -> Path:
    """
    Copy a prompt guide file to the specified destination.

    Parameters
    ----------
    name : str
        Name of the prompt guide
        ('layout-guide' or 'general-guide').
    destination : str or Path
        Destination path where the prompt file should
        be copied. If a directory path is provided, the
        file will be copied with its original name. If a
        file path is provided, the file will be copied
        to that exact location.

    Returns
    ----------
    Path
        Path to the copied file.

    Raises
    ----------
    ValueError
        If the prompt guide is not found.
    FileNotFoundError
        If the destination directory does not exist.

    Examples
    ----------
    >>> import dartwork_mpl as dm
    >>> 
    >>> # Copy to a directory (keeps original filename)
    >>> copied_path = dm.copy_prompt('layout-guide', '.cursor/rules/')
    >>> print(copied_path)
    PosixPath('.cursor/rules/layout-guide.md')
    >>> 
    >>> # Copy to a specific file path
    >>> copied_path = dm.copy_prompt('general-guide', '.cursor/rules/my-guide.md')
    >>> print(copied_path)
    PosixPath('.cursor/rules/my-guide.md')
    """
    source_path = prompt_path(name)
    dest_path = Path(destination)

    # If destination is a directory, append the source filename
    if dest_path.is_dir() or (not dest_path.exists() and not dest_path.suffix):
        dest_path = dest_path / f"{name}.md"

    # Ensure parent directory exists
    _create_parent_path_if_not_exists(dest_path)

    # Copy the file
    copy2(source_path, dest_path)

    return dest_path
