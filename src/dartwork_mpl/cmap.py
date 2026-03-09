"""Matplotlib을 위한 컬러맵(Colormap) 관리 유틸리티 모듈.

이 모듈은 패키지의 에셋(asset/cmap) 디렉토리에 포함된 텍스트 파일들로부터
커스텀 컬러맵들을 읽어오고 등록하는 역할을 담당합니다.
"""

from pathlib import Path

import matplotlib as mpl
import matplotlib.colors as mcolors

__all__ = ["ensure_loaded"]


def _parse_colormap(
    path: str | Path, reverse: bool = False
) -> mcolors.ListedColormap:
    """텍스트 파일로부터 컬러맵 정보를 파싱하여 ListedColormap 객체로 생성합니다.

    Parameters
    ----------
    path : str | Path
        RGB 값이 포함된 컬러맵 텍스트 파일의 경로.
    reverse : bool, optional
        True일 경우 컬러맵의 색상 배열 순서를 뒤집습니다. 기본값은 False.

    Returns
    -------
    matplotlib.colors.ListedColormap
        파싱된 색상들을 가진 ListedColormap 객체.
        컬러맵 이름은 기본적으로 ``'dc.{filename}'``이 되며, 역순(reversed)인
        경우 ``'dc.{filename}_r'``로 명명됩니다.
    """
    path_obj: Path = Path(path)

    colors: list[list[float]] = []
    with open(path_obj) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            color: list[float] = [float(v) for v in line.split()]
            colors.append(color)

    if reverse:
        colors = colors[::-1]
        name: str = f"dc.{path_obj.stem}_r"
    else:
        name = f"dc.{path_obj.stem}"

    return mcolors.ListedColormap(colors, name=name)


def _load_colormaps() -> None:
    """``asset/cmap`` 디렉토리의 모든 컬러맵 파일을 메모리에 로드하고 등록합니다.

    이 함수는 에셋 디렉토리 내의 모든 ``.txt`` 파일들을 자동으로 검색하여
    컬러맵으로 파싱한 뒤, 일반 버전과 역순(reversed) 버전 모두를
    matplotlib의 내부 컬러맵 레지스트리에 일괄 등록합니다.

    Notes
    -----
    이 함수는 라이브러리가 임포트될 때 자동으로 한 번 호출되므로,
    사용자가 직접 호출할 필요는 없습니다.
    """
    root_dir: Path = Path(__file__).parent / "asset/cmap"
    for path in root_dir.glob("*.txt"):
        cmap: mcolors.ListedColormap = _parse_colormap(path)
        mpl.colormaps.register(cmap=cmap)

        # backward compatibility
        alias_cmap = mcolors.ListedColormap(
            cmap.colors, name=cmap.name.replace("dc.", "dm.")
        )
        try:
            mpl.colormaps.register(cmap=alias_cmap)
        except ValueError:
            pass  # Ignore if it somehow already exists

        cmap_r: mcolors.ListedColormap = _parse_colormap(path, reverse=True)
        mpl.colormaps.register(cmap=cmap_r)

        alias_cmap_r = mcolors.ListedColormap(
            cmap_r.colors, name=cmap_r.name.replace("dc.", "dm.")
        )
        try:
            mpl.colormaps.register(cmap=alias_cmap_r)
        except ValueError:
            pass


_loaded: bool = False


def ensure_loaded() -> None:
    """설정된 모든 커스텀 컬러맵들이 메모리에 로드되고 등록되었는지 확인합니다."""
    global _loaded
    if not _loaded:
        _load_colormaps()
        _loaded = True
