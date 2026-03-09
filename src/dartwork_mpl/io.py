"""피규어(Figure) 입출력 관리 유틸리티.

Matplotlib 피규어를 다양한 포맷으로 저장하거나, Jupyter 환경에서
SVG 등 이미지 포맷으로 렌더링하기 위한 함수들을 제공합니다.
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
    """피규어를 여러 지정된 포맷으로 한 번에 저장합니다.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        저장할 Matplotlib 피규어 객체.
    image_stem : str
        확장자를 제외한 저장할 파일의 기본 경로 및 이름.
    formats : tuple[str, ...], optional
        저장할 포맷 확장자들의 튜플. 기본값은 ("png", "pdf").
    bbox_inches : str | None, optional
        저장될 피규어의 경계 상자 설정. 주로 "tight"를 사용하여
        여백을 최소화할 때 씁니다. 기본값은 None.
    validate : bool, optional
        True이면 저장하기 전에 피규어에 대한 시각적 유효성 검사를 수행하고
        문제가 있을 시 stdout에 ``[VISUAL]`` 경고를 출력합니다. 기본값은 True.
    **kwargs
        ``savefig`` 함수로 전달될 추가 인자들.
    """
    if validate:
        from .validate import validate_figure

        validate_figure(fig)

    create_parent_path(image_stem)
    for fmt in formats:
        fig.savefig(f"{image_stem}.{fmt}", bbox_inches=bbox_inches, **kwargs)


def show(image_path: str, size: int = 600, unit: str = "pt") -> None:
    """SVG 이미지를 불러와서 지정된 크기로 브라우저/Jupyter에 표시합니다.

    Parameters
    ----------
    image_path : str
        표시할 SVG 이미지의 위치 경로.
    size : int, optional
        원하는 출력 너비. 기본값은 600.
    unit : str, optional
        너비를 지정하는 단위 ('pt', 'px' 등). 기본값은 'pt'.
    """
    from IPython.display import HTML, SVG, display

    svg_obj = SVG(data=image_path)

    desired_width = size

    # Parse SVG dimensions with defensive handling.
    dom = minidom.parseString(svg_obj.data)
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
    """피규어를 디스크에 저장한 뒤, Jupyter나 웹 환경에서 바로 표시합니다.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        저장하고 표시할 Matplotlib 피규어 객체.
    image_path : str | None, optional
        이미지를 저장할 경로. None이면 시스템 임시 파일을 사용합니다.
    size : int, optional
        출력되어 보일 너비 크기. 기본값은 600.
    unit : str, optional
        크기의 단위 ('pt', 'px' 등). 기본값은 'pt'.
    **kwargs
        ``savefig`` 호출 시 함께 전달될 추가 인자들.
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
