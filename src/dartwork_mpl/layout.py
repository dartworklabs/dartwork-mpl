"""Matplotlib 피규어(Figure)의 레이아웃 최적화 유틸리티.

``scipy.optimize``를 사용하여 피규어 내부의 서브플롯 영역들을
자동으로 알맞게 배치해 주는 ``simple_layout`` 함수를 제공합니다.
"""

from __future__ import annotations

__all__ = ["simple_layout", "get_bounding_box", "set_xmargin", "set_ymargin"]

from typing import TYPE_CHECKING

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec

if TYPE_CHECKING:
    from scipy.optimize import OptimizeResult


def get_bounding_box(boxes: list) -> tuple[float, float, float, float]:
    """
    주어진 모든 박스 영역을 포함하는 최소 크기의 경계 상자(Bounding Box)를 계산합니다.

    Parameters
    ----------
    boxes : list
        p0 (좌하단 좌표), width (너비), height (높이) 속성을 최소한으로 가지고 있는
        박스 객체들의 리스트.

    Returns
    -------
    tuple[float, float, float, float]
        전체 경계 상자의 (min_x, min_y, bbox_width, bbox_height).
    """
    min_x = float("inf")
    min_y = float("inf")
    max_x = float("-inf")
    max_y = float("-inf")

    for box in boxes:
        min_x = min(min_x, box.p0[0])
        min_y = min(min_y, box.p0[1])
        max_x = max(max_x, box.p0[0] + box.width)
        max_y = max(max_y, box.p0[1] + box.height)

    bbox_width = max_x - min_x
    bbox_height = max_y - min_y

    return (min_x, min_y, bbox_width, bbox_height)


def set_xmargin(
    ax: Axes,
    margin: float = 0.05,
    *,
    left: float | None = None,
    right: float | None = None,
) -> None:
    """x축 제한(limits)에 반응형(responsive) 마진 또는 고정 경계를 설정합니다.

    이 함수는 ``set_xlim``을 감싸서 전역 마진 비율과 동시에
    한쪽, 혹은 양쪽의 고정된 스케일 경계값을 함께 지정할 수 있게 해줍니다.

    Parameters
    ----------
    ax : Axes
        설정을 변경할 matplotlib Axes 객체.
    margin : float, optional
        기본적인 좌우 여백의 비율. 기본값은 0.05.
    left : float | None, optional
        x축의 고정된 시작값(가장 왼쪽). 지정하면 해당 부분의 margin은 무시됩니다.
    right : float | None, optional
        x축의 고정된 끝값(가장 오른쪽). 지정하면 해당 부분의 margin은 무시됩니다.
    """
    ax.margins(x=margin)
    xlim = list(ax.get_xlim())
    if left is not None:
        xlim[0] = left
    if right is not None:
        xlim[1] = right
    ax.set_xlim((float(xlim[0]), float(xlim[1])))


def set_ymargin(
    ax: Axes,
    margin: float = 0.05,
    *,
    bottom: float | None = None,
    top: float | None = None,
) -> None:
    """y축 제한(limits)에 반응형(responsive) 마진 또는 고정 경계를 설정합니다.

    이 함수는 ``set_ylim``을 감싸서 전역 마진 비율과 동시에
    한쪽, 혹은 양쪽의 고정된 스케일 경계값을 함께 지정할 수 있게 해줍니다.

    Parameters
    ----------
    ax : Axes
        설정을 변경할 matplotlib Axes 객체.
    margin : float, optional
        기본적인 위아래 여백의 비율. 기본값은 0.05.
    bottom : float | None, optional
        y축의 고정된 바닥값(가장 아래). 지정하면 해당 부분의 margin은 무시됩니다.
    top : float | None, optional
        y축의 고정된 천장값(가장 위). 지정하면 해당 부분의 margin은 무시됩니다.
    """
    ax.margins(y=margin)
    ylim = list(ax.get_ylim())
    if bottom is not None:
        ylim[0] = bottom
    if top is not None:
        ylim[1] = top
    ax.set_ylim((float(ylim[0]), float(ylim[1])))


def simple_layout(
    fig: Figure,
    gs: GridSpec | None = None,
    margins: tuple[float, float, float, float] = (0.15, 0.05, 0.05, 0.05),
    bbox: tuple[float, float, float, float] = (0, 1, 0, 1),
    verbose: bool = False,
    gtol: float = 1e-2,
    bound_margin: float = 0.2,
    use_all_axes: bool = True,
    importance_weights: tuple[float, float, float, float] = (1, 1, 1, 1),
) -> OptimizeResult:
    """GridSpec에 최적화된 레이아웃을 적용해 서브플롯 위치를 미세 조정합니다.

    이 함수는 L-BFGS-B 최적화 알고리즘을 사용해서 지정한 마진(margins)과
    바운딩 박스(bbox) 내에 내부 플롯들이 가장 잘 들어맞도록 GridSpec의 파라미터를 계산합니다.
    기본 제공되는 `tight_layout`보다 일관되고 예측 가능한 여백 구조를 제공합니다.

    Parameters
    ----------
    fig : Figure
        레이아웃을 적용할 Matplotlib Figure 객체.
    gs : GridSpec | None, optional
        최적화를 수행할 GridSpec 객체. None일 경우 기본적으로 `fig.axes[0]`의 GridSpec을 사용합니다.
    margins : tuple[float, float, float, float], optional
        인치(inch) 단위의 여백값 설정 (왼쪽, 오른쪽, 아래, 위). 기본값은 (0.15, 0.05, 0.05, 0.05).
    bbox : tuple[float, float, float, float], optional
        최적화 대상 영역을 Figure 기준 상대 좌표로 지정 (왼쪽, 오른쪽, 아래, 위).
        기본값 (0, 1, 0, 1)은 Figure 전체 공간을 의미합니다.
    verbose : bool, optional
        최적화 과정에 대한 진단 로그를 출력할지 여부. 기본값은 False.
    gtol : float, optional
        L-BFGS-B 최적화의 그라디언트(경사) 허용 오차. 기본값은 1e-2.
    bound_margin : float, optional
        파라미터 경계를 생성하기 위한 버퍼 마진. 최적화 탐색 공간 크기를 결정합니다. 기본값은 0.2.
    use_all_axes : bool, optional
        True이면 Figure 내의 모든 축(Axes) 텍스트/요소를 기준으로 경계를 계산합니다.
        False이면 `gs`에 포함된 축들만 계산에 포함시킵니다. 기본값은 True.
    importance_weights : tuple[float, float, float, float], optional
        (왼쪽, 오른쪽, 아래, 위) 여백을 맞추는 데 부여할 가중치(중요도). 기본값은 (1, 1, 1, 1).

    Returns
    -------
    OptimizeResult
        scipy의 최적화 결과를 담은 객체.
    """
    actual_gs: GridSpec = gs if gs is not None else fig.axes[0].get_gridspec()  # type: ignore[assignment]

    _import_weights = np.array(importance_weights)
    _margins = np.array(margins) * fig.get_dpi()

    def fun(x: np.ndarray) -> float:
        actual_gs.update(left=x[0], right=x[1], bottom=x[2], top=x[3])

        if use_all_axes:
            ax_bboxes = [ax.get_tightbbox() for ax in fig.axes]
        else:
            ax_bboxes = [
                ax.get_tightbbox()
                for ax in fig.axes
                if id(ax.get_gridspec()) == id(actual_gs)
            ]

        all_bbox = get_bounding_box(ax_bboxes)
        values = np.array(all_bbox)

        fbox = fig.bbox
        targets = np.array(
            [
                fbox.width * bbox[0] + _margins[0],
                fbox.height * bbox[2] + _margins[2],
                fbox.width * (bbox[1] - bbox[0]) - 2 * _margins[1],
                fbox.height * (bbox[3] - bbox[2]) - 2 * _margins[3],
            ]
        )

        scales = np.array([fbox.width, fbox.height, fbox.width, fbox.height])
        loss = np.square((values - targets) / scales * _import_weights).sum()

        return float(loss)

    bounds = [
        (bbox[0], bbox[0] + bound_margin),
        (bbox[1] - bound_margin, bbox[1]),
        (bbox[2], bbox[2] + bound_margin),
        (bbox[3] - bound_margin, bbox[3]),
    ]

    from scipy.optimize import minimize

    result = minimize(
        fun,
        x0=np.array(bounds).mean(axis=1),
        bounds=bounds,
        method="L-BFGS-B",
        options={"gtol": gtol},
    )

    return result
