"""Matplotlib 피규어 관리를 위한 기타 범용 유틸리티.

별도의 단일 모듈로 분리하기 다소 애매한 작은 유틸리티성 함수들을
모아두었습니다. 기존 하위 버전들과의 하위 호환성을 위해 다른 폴더로
이동된 핵심 함수들도 해당 모듈을 거쳐 re-exports 되고 있습니다.
"""

from __future__ import annotations

# Re-exports for backward compatibility – these were moved to
# dedicated modules but many consumers still import from util.
from .annotation import arrow_axis, label_axes
from .io import save_and_show, save_formats, show
from .layout import get_bounding_box, set_xmargin, set_ymargin, simple_layout
from .prompt import copy_prompt, get_prompt, list_prompts, prompt_path
from .scale import fs, fw, lw

__all__ = [
    # Re-exports (moved modules)
    "fs",
    "fw",
    "lw",
    "simple_layout",
    "get_bounding_box",
    "set_xmargin",
    "set_ymargin",
    "save_formats",
    "save_and_show",
    "show",
    "label_axes",
    "arrow_axis",
    "prompt_path",
    "get_prompt",
    "list_prompts",
    "copy_prompt",
    # Residual helpers (kept here)
    "set_decimal",
    "mix_colors",
    "pseudo_alpha",
    "cm2in",
    "make_offset",
]

import matplotlib.colors as mcolors
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.transforms import ScaledTranslation


def set_decimal(ax: Axes, xn: int | None = None, yn: int | None = None) -> None:
    """x축 및/또는 y축 눈금 라벨의 소수점 자릿수를 고정시킵니다.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        설정을 변경할 Axes 객체.
    xn : int | None, optional
        x축 눈금 라벨에 표시할 소수점 이하 자릿수 깊이.
        None일 경우 변경하지 않습니다.
    yn : int | None, optional
        y축 눈금 라벨에 표시할 소수점 이하 자릿수 깊이.
        None일 경우 변경하지 않습니다.
    """
    if xn is not None:
        xticks = ax.get_xticks()
        ax.set_xticks(xticks)
        ax.set_xticklabels([f"{x:.{xn}f}" for x in xticks])

    if yn is not None:
        yticks = ax.get_yticks()
        ax.set_yticks(yticks)
        ax.set_yticklabels([f"{y:.{yn}f}" for y in yticks])


def mix_colors(
    color1: str | tuple[float, float, float],
    color2: str | tuple[float, float, float],
    alpha: float = 0.5,
) -> tuple[float, float, float]:
    """두 개의 색상을 지정된 가중치(alpha)에 따라 섞습니다.

    Parameters
    ----------
    color1 : str | tuple[float, float, float]
        혼합할 첫 번째 색상. matplotlib에서 인식할 수 있는 어떤 형태든 지원합니다.
    color2 : str | tuple[float, float, float]
        혼합할 두 번째 색상.
    alpha : float, optional
        첫 번째 색상이 가지는 가중치 혹은 불투명도(0과 1사이). 기본 설정값은 0.5.

    Returns
    -------
    tuple[float, float, float]
        두 색상이 섞인 결과물의 RGB 튜플.
    """
    color1 = mcolors.to_rgb(color1)
    color2 = mcolors.to_rgb(color2)

    r, g, b = (
        alpha * c1 + (1 - alpha) * c2
        for c1, c2 in zip(color1[:3], color2[:3], strict=False)
    )
    return r, g, b


def pseudo_alpha(
    color: str | tuple[float, float, float],
    alpha: float = 1.0,
    background: str | tuple[float, float, float] = "white",
) -> tuple[float, float, float]:
    """배경색과 섞어서 투명도(alpha)가 적용된 것처럼 보이는 색상의 실제 RGB를 반환합니다.

    실제로 alpha가 적용되면 선이 겹치거나 이미지를 덮을 때 색이 진해지는 문제가 생길 수 있습니다.
    이럴 경우 불투명한 새로운 색상을 배경과 직접 믹스하여 "시각적인 모의 투명도"를 부여할 수 있게
    해 주는 편리한 함수입니다.

    Parameters
    ----------
    color : str | tuple[float, float, float]
        목표로 하는 원본 대상 색상.
    alpha : float, optional
        적용하고자 하는 모의 투명도(0에서 1사이값). 기본값은 1.0(불투명 원본).
    background : str | tuple[float, float, float], optional
        색상을 믹스할 배경 색상. 기본값은 "white".

    Returns
    -------
    tuple[float, float, float]
        투명도 효과가 처리된 결과 색상의 RGB 튜플.
    """
    return mix_colors(color, background, alpha=alpha)


def cm2in(cm: float) -> float:
    """주어진 센티미터(cm) 단위를 인치(inch) 값으로 변환합니다.

    Parameters
    ----------
    cm : float
        센티미터 단위의 스케일 크기.

    Returns
    -------
    float
        변환된 인치 단위의 스케일 크기.
    """
    return cm / 2.54


def make_offset(x: float, y: float, fig: Figure) -> ScaledTranslation:
    """피규어 내부 요소(텍스트 등)를 이동시키기 위한 오프셋 변환 객체를 생성합니다.

    Parameters
    ----------
    x : float
        이동할 x축 오프셋 (단위: points).
    y : float
        이동할 y축 오프셋 (단위: points).
    fig : matplotlib.figure.Figure
        기준이 되는 Figure 캔버스 범위.

    Returns
    -------
    matplotlib.transforms.ScaledTranslation
        적용 가능한 오프셋 좌표 변환 도구.
    """
    dx, dy = x / 72, y / 72
    offset = ScaledTranslation(dx, dy, fig.dpi_scale_trans)
    return offset
