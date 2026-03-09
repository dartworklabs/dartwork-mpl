"""색상, 팔레트, 컬러맵(colormap) 탐색 도구.

dartwork-mpl에서 사용할 수 있는 불연속 팔레트와 컬러맵 목록을
조회하고 시각화해 볼 수 있는 유틸리티 함수들을 제공합니다.
"""

from __future__ import annotations

import re

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt

__all__ = ["list_palettes", "list_colormaps", "show_palette"]


def _get_all_colors() -> list[str]:
    from .color._loader import ensure_loaded

    ensure_loaded()
    return list(mcolors.get_named_colors_mapping().keys())


def list_palettes() -> list[str]:
    """사용 가능한 모든 불연속형 색상 팔레트의 목록을 조회합니다.

    Returns
    -------
    list[str]
        팔레트 이름들의 정렬된 리스트 (예: 'dc.vivid', 'oc.blue' 등).
    """
    colors: list[str] = _get_all_colors()
    palettes: set[str] = set()
    # match prefix.name + digits
    pattern: re.Pattern[str] = re.compile(
        r"^([a-z]+)\.([a-z]+(?:\-[a-z]+)?)\d+$"
    )
    for c in colors:
        match = pattern.match(c)
        if match:
            palettes.add(f"{match.group(1)}.{match.group(2)}")
    return sorted(palettes)


def list_colormaps(include_reversed: bool = False) -> list[str]:
    """등록된 다트워크 전용 컬러맵(Colormap)들의 목록을 조회합니다.

    Parameters
    ----------
    include_reversed : bool, default=False
        이름 끝에 '_r'이 붙은 반전된(reversed) 컬러맵도 목록에 포함할지 여부.
        기본값은 False입니다.

    Returns
    -------
    list[str]
        등록된 컬러맵 이름들의 정렬된 리스트.
    """
    from .cmap import ensure_loaded

    ensure_loaded()
    cmaps: list[str] = [c for c in plt.colormaps() if c.startswith("dc.")]
    if not include_reversed:
        cmaps = [c for c in cmaps if not c.endswith("_r")]
    return sorted(cmaps)


def show_palette(palette_name: str) -> None:
    """특정 불연속 팔레트의 색상들을 시각적으로 출력합니다.

    지정된 팔레트에 포함된 모든 색조(shades)를 네모난 형태의
    색상표로 나란히 나열하여 보여줍니다. Jupyter 노트북 환경 등에서
    색상을 미리 확인할 때 유용합니다.

    Parameters
    ----------
    palette_name : str
        시각화하여 확인할 팔레트의 이름 (예: 'dc.acid', 'oc.gray').

    Raises
    ------
    ValueError
        팔레트 이름이 존재하지 않거나 해당 팔레트에 번호가 매겨진
        색상 요소들이 없는 경우 발생합니다.
    """
    colors: list[str] = _get_all_colors()
    # find all colors that start with palette_name followed by a number
    pattern: re.Pattern[str] = re.compile(rf"^{re.escape(palette_name)}(\d+)$")

    palette_colors: list[tuple[int, str]] = []
    for c in colors:
        match = pattern.match(c)
        if match:
            palette_colors.append((int(match.group(1)), c))

    if not palette_colors:
        raise ValueError(
            f"Palette '{palette_name}' not found or has no numbered shades."
        )

    palette_colors.sort(key=lambda x: x[0])
    color_names: list[str] = [c[1] for c in palette_colors]

    n: int = len(color_names)
    fig, ax = plt.subplots(figsize=(n * 0.8, 1.2))

    for i, cname in enumerate(color_names):
        ax.add_patch(
            plt.Rectangle((i, 0), 1, 1, facecolor=cname, edgecolor="none")
        )

        # Simple contrast heuristic: lighter text for darker shades (index >= 5 usually)
        shade_idx = palette_colors[i][0]
        text_color = "white" if shade_idx >= 5 else "black"

        ax.text(
            i + 0.5,
            0.5,
            str(shade_idx),
            color=text_color,
            ha="center",
            va="center",
            fontsize=11,
            fontweight="bold",
        )

    ax.set_xlim(0, n)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(palette_name, loc="left", pad=10, fontweight="bold")

    for spine in ax.spines.values():
        spine.set_visible(False)

    plt.tight_layout()
    plt.show()
