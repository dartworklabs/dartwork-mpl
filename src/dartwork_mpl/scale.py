"""rcParams 기본값을 기준으로 한 폰트 및 선 굵기 스케일링 도구.

현재 설정된 matplotlib 스타일의 기본 크기로부터 일정한 오프셋을
더하거나 빼서 크기를 조절하는 ``fs``, ``fw``, ``lw`` 헬퍼 함수를 제공합니다.
"""

from __future__ import annotations

__all__ = ["fs", "fw", "lw"]

import matplotlib.pyplot as plt

_WEIGHT_MAP: dict[str, int] = {
    "ultralight": 100,
    "light": 200,
    "normal": 400,
    "regular": 400,
    "book": 400,
    "medium": 500,
    "roman": 500,
    "semibold": 600,
    "demibold": 600,
    "demi": 600,
    "bold": 700,
    "heavy": 800,
    "extra bold": 800,
    "black": 900,
}


def fs(n: int | float) -> float:
    """기본 폰트 크기(font size)에 *n*\ 을 더한 값을 반환합니다.

    Parameters
    ----------
    n : int | float
        기본 ``rcParams['font.size']``\ 에 더할 오프셋 값.
        양수면 폰트가 더 커지고, 음수면 작아집니다.

    Returns
    -------
    float
        스케일링이 완료된 새로운 폰트 크기.
    """
    return float(plt.rcParams["font.size"]) + float(n)


def fw(n: int) -> int:
    """기본 폰트 굵기(font weight)에 100 × *n*\ 을 더한 값을 반환합니다.

    문자열로 된 굵기 속성(예: ``'normal'``, ``'bold'``)은 연산을 수행하기 전에
    매칭되는 숫자형 단위(예: 400, 700)로 자동 변환됩니다.

    Parameters
    ----------
    n : int
        기본 폰트 굵기에 더할 가중치 단계별 횟수(한 단계당 100).
        예컨대 n=1을 지정하면 기존 폰트보다 한 단계 굵은 폰트를 사용하게 됩니다.

    Returns
    -------
    int
        숫자형태로 계산된 새로운 폰트 굵기.
    """
    base = plt.rcParams["font.weight"]
    if isinstance(base, str):
        base = _WEIGHT_MAP.get(base.lower(), 400)
    return int(base) + 100 * n


def lw(n: int | float) -> float:
    """기본 선 두께(line width)에 *n*\ 을 더한 값을 반환합니다.

    Parameters
    ----------
    n : int | float
        기본 ``rcParams['lines.linewidth']``\ 에 더할 오프셋 값.
        양수면 선이 굵어지고, 음수면 얇아집니다.

    Returns
    -------
    float
        스케일링이 완료된 새로운 선 두께.
    """
    return float(plt.rcParams["lines.linewidth"]) + float(n)
