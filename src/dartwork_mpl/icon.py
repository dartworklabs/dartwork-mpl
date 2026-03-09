"""Matplotlib 피규어를 위한 아이콘 폰트 유틸리티.

이 모듈은 Matplotlib에서 직접 Material Design Icons,
Font Awesome 6 등의 외부 아이콘 폰트를 편리하게 불러와
유니코드 문자로 표시할 수 있도록 지원합니다.

Examples
--------
>>> import dartwork_mpl as dm
>>> mdi = dm.icon_font('mdi')
>>> ax.text(0.5, 0.5, "\U000f050f",  # 온도계 아이콘
...         fontproperties=mdi, fontsize=20)
"""

from pathlib import Path

from matplotlib import font_manager as fm

_ICON_DIR: Path = Path(__file__).parent / "asset/icon"

_REGISTRY: dict[str, str] = {
    "mdi": "materialdesignicons-webfont.ttf",
    "fa-solid": "Font Awesome 6 Free-Solid-900.otf",
    "fa-regular": "Font Awesome 6 Free-Regular-400.otf",
    "fa-brands": "Font Awesome 6 Brands-Regular-400.otf",
}

__all__ = ["icon_font", "icon_font_path", "list_icon_fonts", "ensure_loaded"]


def icon_font_path(name: str = "mdi") -> Path:
    """패키지에 내장된 아이콘 폰트 파일의 절대 경로를 반환합니다.

    Parameters
    ----------
    name : str, optional
        접근할 아이콘 폰트의 식별자 이름.
        사용 가능한 값: ``'mdi'``, ``'fa-solid'``, ``'fa-regular'``,
        ``'fa-brands'``. 기본값은 ``'mdi'``\ 입니다.

    Returns
    -------
    Path
        해당 폰트 파일(.ttf 혹은 .otf)의 절대 경로.

    Raises
    ------
    ValueError
        요청한 이름(*name*)\ 이 등록된 폰트 식별자가 아닌 경우.
    FileNotFoundError
        폰트 파일이 디스크 경로에 실제로 존재하지 않는 경우.

    Examples
    --------
    >>> import dartwork_mpl as dm
    >>> path = dm.icon_font_path('mdi')
    >>> path.name
    'materialdesignicons-webfont.ttf'
    """
    ensure_loaded()

    if name not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY))
        raise ValueError(f"Unknown icon font '{name}'. Available: {available}")

    path = _ICON_DIR / _REGISTRY[name]
    if not path.exists():
        raise FileNotFoundError(
            f"Icon font file not found: {path}. Please reinstall dartwork-mpl."
        )
    return path


def icon_font(name: str = "mdi") -> fm.FontProperties:
    """``ax.text()``\ 등 텍스트 출력 파라미터로 바로 전달 가능한
    :class:`~matplotlib.font_manager.FontProperties` 객체를 생성합니다.

    Parameters
    ----------
    name : str, optional
        불러올 아이콘 폰트 식별자 이름.
        사용 가능한 값: ``'mdi'``, ``'fa-solid'``, ``'fa-regular'``,
        ``'fa-brands'``. 기본값은 ``'mdi'``\ 입니다.

    Returns
    -------
    FontProperties
        해당 폰트에 맞게 설정이 완료된 Matplotlib FontProperties 인스턴스.

    Examples
    --------
    >>> import dartwork_mpl as dm
    >>> mdi = dm.icon_font('mdi')
    >>> # 가운데에 아이콘 텍스트 출력
    >>> ax.text(0.5, 0.5, "\U000f050f",
    ...         fontproperties=mdi, fontsize=20,
    ...         ha='center', va='center')
    """
    ensure_loaded()
    return fm.FontProperties(fname=str(icon_font_path(name)))


def list_icon_fonts() -> list[str]:
    """사용 가능한 아이콘 폰트 식별자 목록을 반환합니다.

    Returns
    -------
    list[str]
        사용 가능한 식별자 목록 (예: ``['fa-brands', 'fa-regular',
        'fa-solid', 'mdi']``).
    """
    return sorted(_REGISTRY.keys())


def _register_icon_fonts() -> None:
    """번들된 모든 아이콘 폰트를 시스템 matplotlib 폰트 매니저에 등록합니다.

    이 함수는 모듈이 처음 import 되거나 내부적으로 load가 필요할 때 자동으로 호출됩니다.
    """
    for filename in _REGISTRY.values():
        font_path = _ICON_DIR / filename
        if font_path.exists():
            fm.fontManager.addfont(str(font_path))


_loaded: bool = False


def ensure_loaded() -> None:
    """아이콘 폰트가 시스템에 아직 로드되지 않았다면 로드(등록)를 보장합니다."""
    global _loaded
    if not _loaded:
        _register_icon_fonts()
        _loaded = True
