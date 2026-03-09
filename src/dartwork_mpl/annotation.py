"""축(Axes) 기반의 주석 생성 헬퍼 모듈.

피규어 패널들에 표준 알파벳 서브라벨을 달아주는 ``label_axes`` 함수나,
Low-High 같은 양방향 화살표 축을 그리는 ``arrow_axis`` 기능을 제공합니다.
"""

from __future__ import annotations

__all__ = ["label_axes", "arrow_axis"]

import string

import numpy as np
from matplotlib.axes import Axes
from typing import Any

from .scale import fs


def label_axes(
    axes: list[Axes] | np.ndarray,
    labels: list[str] | None = None,
    fontsize: float = 10,
    fontweight: str = "bold",
    x: float | str = "auto",
    y: float = 1.05,
    **kwargs,
) -> list:
    """서브플롯 패널에 표준화된 식별 라벨(a, b, c, ...)을 자동으로 추가합니다.

    주로 학술 논문 및 보고서에서 피규어의 여러 패널을 설명하기 위해,
    각 Axes 공간의 왼쪽 가장자리 또는 상단 모서리에 라벨을 일괄 배치시키는데 사용됩니다.

    Parameters
    ----------
    axes : list[Axes] | np.ndarray
        라벨을 지정해줄 Axes 객체 목록이나 배열.
    labels : list[str] | None, optional
        사용자 정의 텍스트 라벨. None이 주어지면 기본 소문자 알파벳
        리스트를 (a, b, c, 등등) 자동으로 할당합니다.
    fontsize : float, optional
        라벨의 폰트 크기. 기본값은 10 포인트.
    fontweight : str, optional
        라벨의 폰트 두께. 기본값은 "bold".
    x : float | str, optional
        Axes 상대 좌표(0.0~1.0 구간 넘어섬)계에서의 가로 위치 좌표.
        "auto"일 경우 y축 이름 유무에 따라 가장 적절한 x 위치를 자동으로 찾습니다(-0.18 또는 -0.02).
    y : float, optional
        Axes 상대 좌표계에서의 세로 위치 좌표. 기본값은 1.05.
    **kwargs
        ``ax.text()`` 함수로 추가 전달할 여분의 텍스트 설정 인자들.

    Returns
    -------
    list
        생성된 내부 Text 객체들의 리스트.
    """
    if isinstance(axes, np.ndarray):
        axes = axes.flatten().tolist()

    if labels is None:
        labels = list(string.ascii_lowercase[: len(axes)])

    texts = []
    for ax, label in zip(axes, labels, strict=False):
        if x == "auto":
            has_ylabel = ax.get_ylabel().strip() != ""
            x_pos = -0.18 if has_ylabel else -0.02
        else:
            x_pos = float(x)  # type: ignore[arg-type]

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
    """그리프의 가장자리나 내부에 높음(High)-낮음(Low)을 가리키는 양방향 라벨과 화살표 축을 그립니다.

    결과물 시각화 컨셉: ``Low ◄── label ──► High`` 형태로 spine의 바깥쪽 주변을 꾸며줍니다.

    Parameters
    ----------
    ax : Axes
        주석을 적용할 대상 축 객체.
    direction : {'x', 'y'}
        "x": x축 스파인 하단에 가로 축 화살표 삽입.
        "y": y축 스파인 왼쪽 바깥에 세로 축 화살표 삽입.
    label : str
        축 중간(가운데)에 위치할 중심 라벨의 텍스트 지정.
    offset : float, optional
        Axes 스케일 기준으로 스파인 외부로 떨어트려 그릴 간격 차이 수준값.
        기본값은 약간 바깥쪽인 -0.05 입니다.
    low : str, optional
        축의 최하단/최좌측에 나타낼 방향성에 해당하는 텍스트 값 ("Low").
    high : str, optional
        축의 최상단/최우측에 나타낼 방향성에 해당하는 텍스트 값 ("High").
    fontsize : float | None, optional
        상하단(Low/High)을 표시하는 서브 텍스트들의 폰트 사이즈. 기본값은 fs(-1).
    fontsize_label : float | None, optional
        가운데 중심 문자열의 텍스트 사이즈. 기본값은 fs(0).
    pad : float, optional
        글자와 화살촉 사이의 여백 및 공백 거리 비율. 기본값은 -0.005.
    weight : str, optional
        모든 적용될 텍스트 파츠들의 활자체 가중치 굵기.
    color : str, optional
        텍스트 및 화살표 양측에 할당시킬 색상. 기본값은 "black".
    arrow_kw : dict | None, optional
        내부적으로 호출되는 화살표 생성함수 ``ax.annotate``의 화살표형상 속성을 결정하는 arrowprops를 재정의합니다.
    """
    if fontsize is None:
        fontsize = fs(-1)
    if fontsize_label is None:
        fontsize_label = fs(0)
    if arrow_kw is None:
        arrow_kw = {
            "arrowstyle": "-|>,head_width=0.1",
            "color": color,
            "lw": 0.25,
        }

    fig = ax.get_figure()
    if fig is None or fig.canvas is None:
        raise ValueError("Axes must be part of a Figure with a canvas")
    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
    inv = ax.transAxes.inverted()
    rot_kw: dict[str, Any] = (
        {"rotation": 90, "rotation_mode": "anchor"} if direction == "y" else {}
    )

    # ── place texts ──────────────────────────────────────────
    if direction == "x":
        p_lo: tuple[float, float] = (0.0, float(offset))
        p_hi: tuple[float, float] = (1.0, float(offset))
        p_lb: tuple[float, float] = (0.5, float(offset))
    else:
        p_lo = (float(offset), 0.0)
        p_hi = (float(offset), 1.0)
        p_lb = (float(offset), 0.5)

    t_lo = ax.text(
        *p_lo,
        low,
        transform=ax.transAxes,
        fontsize=fontsize,
        fontweight=weight,
        color=color,
        ha="left",
        va="center",
        clip_on=False,
        **rot_kw,
    )
    t_hi = ax.text(
        *p_hi,
        high,
        transform=ax.transAxes,
        fontsize=fontsize,
        fontweight=weight,
        color=color,
        ha="right",
        va="center",
        clip_on=False,
        **rot_kw,
    )
    t_lb = ax.text(
        *p_lb,
        label,
        transform=ax.transAxes,
        fontsize=fontsize_label,
        fontweight=weight,
        color=color,
        ha="center",
        va="center",
        clip_on=False,
        **rot_kw,
    )

    # ── measure extents in axes fraction ─────────────────────
    fig.canvas.draw()

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
                "",
                xy=(tip, offset),
                xytext=(tail, offset),
                xycoords="axes fraction",
                arrowprops=arrow_kw,
                annotation_clip=False,
            )
        else:
            ax.annotate(
                "",
                xy=(offset, tip),
                xytext=(offset, tail),
                xycoords="axes fraction",
                arrowprops=arrow_kw,
                annotation_clip=False,
            )

    _arrow(lo_end + pad, lb_lo - pad)
    _arrow(hi_start - pad, lb_hi + pad)
