"""Matplotlib 스타일 관리 유틸리티.

이 모듈은 패키지의 내장 스타일 라이브러리에서 matplotlib 스타일을
가져오고 적용하기 위한 함수와 클래스를 제공합니다.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt

__all__ = ["Style", "style", "style_path", "list_styles", "load_style_dict"]


def style_path(name: str) -> Path:
    """
    스타일 파일의 경로를 가져옵니다.

    Parameters
    ----------
    name : str
        스타일의 이름 (예: 'report', 'scientific' 등).

    Returns
    -------
    Path
        해당 스타일 파일(.mplstyle)의 절대 경로.

    Raises
    ------
    ValueError
        해당 이름의 스타일을 찾을 수 없는 경우 발생합니다.
    """
    path: Path = Path(__file__).parent / f"asset/mplstyle/{name}.mplstyle"
    if not path.exists():
        raise ValueError(f"Not found style: {name}")

    return path


def list_styles() -> list[str]:
    """
    사용 가능한 모든 스타일의 목록을 반환합니다.

    Returns
    -------
    list[str]
        스타일 이름들이 담긴 리스트.
    """
    path: Path = Path(__file__).parent / "asset/mplstyle"
    return sorted([p.stem for p in path.glob("*.mplstyle")])


def load_style_dict(name: str) -> dict[str, float | str]:
    """
    mplstyle 파일에서 키와 값 쌍을 읽어옵니다.

    Parameters
    ----------
    name : str
        불러올 스타일의 이름.

    Returns
    -------
    dict[str, float | str]
        스타일 파라미터가 담긴 딕셔너리. 가능한 경우 값은 float로
        변환되며, 그렇지 않은 경우 문자열 그대로 유지됩니다.
    """
    # Load key, value pair from mplstyle files.
    path: Path = style_path(name)
    style_dict: dict[str, float | str] = {}
    with open(path) as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # Split on first colon only (values may contain colons).
            if ":" not in stripped:
                continue
            key, raw_value = stripped.split(":", maxsplit=1)
            key = key.strip()

            # Strip inline comments: find ' #' outside of quotes.
            value_str = raw_value.split(" #")[0].strip()
            if not value_str:
                continue

            try:
                value_float: float = float(value_str)
                style_dict[key] = value_float
            except ValueError:
                style_dict[key] = value_str

    return style_dict


class Style:
    """
    여러 matplotlib 스타일을 관리하고 적용하기 위한 클래스입니다.

    이 클래스는 스타일 프리셋을 불러오고, 여러 스타일을 순차적으로
    적용(스태킹)하는 기능을 제공합니다.

    Examples
    --------
    >>> import dartwork_mpl as dm
    >>> dm.style.use("scientific")  # 단일 프리셋 적용
    >>> dm.style.stack(["base", "lang-kr"])  # 여러 스타일 겹쳐서 적용
    """

    def __init__(self) -> None:
        """Style 인스턴스를 초기화하고 프리셋을 불러옵니다."""
        self.presets: dict[str, list[str]] = {}
        # Load presets
        self.load_presets()

    @staticmethod
    def presets_path() -> Path:
        """
        프리셋 설정 파일(presets.json)의 경로를 가져옵니다.

        Returns
        -------
        Path
            조합된 스타일 프리셋이 정의되어 있는 presets.json 파일의 경로.
        """
        return Path(__file__).parent / "asset/mplstyle/presets.json"

    def load_presets(self) -> None:
        """
        JSON 파일에서 스타일 프리셋을 불러옵니다.

        presets.json 파일을 읽어서 인스턴스의 presets 속성에 설정값들을 저장합니다.
        """
        with open(self.presets_path()) as f:
            self.presets = json.load(f)

    @staticmethod
    def stack(style_names: list[str]) -> None:
        """
        여러 스타일을 순서대로 스태킹(적용)합니다.

        여러 스타일 파일을 순차적으로 적용합니다. 나중에 적용된 스타일이
        이전에 설정된 같은 항목의 값을 덮어씁니다.

        Parameters
        ----------
        style_names : list[str]
            적용할 스타일 이름들의 리스트. 리스트의 순서대로 적용되며,
            뒤에 있는 스타일이 우선순위를 가집니다.

        Examples
        --------
        >>> import dartwork_mpl as dm
        >>> dm.style.stack(["base", "font-scientific", "lang-kr"])
        """
        from .cmap import ensure_loaded as ensure_cmaps_loaded
        from .font import ensure_loaded as ensure_fonts_loaded

        # Ensure fonts and colormaps are registered before Matplotlib tries to resolve them
        ensure_fonts_loaded()
        ensure_cmaps_loaded()

        plt.rcParams.update(plt.rcParamsDefault)
        plt.style.use([style_path(style_name) for style_name in style_names])

    def use(self, preset_name: str, **kwargs: float | str) -> None:
        """
        프리셋 스타일 설정을 적용합니다.

        이 모듈에서 스타일을 적용할 때 가장 권장되는 방법입니다.
        프리셋은 특정 사용 목적에 맞게 미리 최적화된 스타일들의 조합입니다.

        Parameters
        ----------
        preset_name : str
            적용할 프리셋의 이름. 사용 가능한 프리셋 목록:
            - "scientific": 학술 논문용 (기본 영문)
            - "report": 문서 보고서 및 대시보드용
            - "minimal": 선과 눈금이 없는 Tufte 스타일
            - "presentation": 프레젠테이션(발표)용
            - "poster": 컨퍼런스 포스터 및 대형 디스플레이용
            - "web": 웹페이지 및 공식 문서용
            - "dark": 어두운 배경의 다크 테마
            - "scientific-kr": 학술 논문용 (한국어 폰트 적용)
            - "report-kr": 문서 보고서 및 대시보드용 (한국어 폰트 적용)
            - "minimal-kr": 미니멀 스타일 (한국어 폰트 적용)
            - "presentation-kr": 프레젠테이션용 (한국어 폰트 적용)
            - "poster-kr": 컨퍼런스 포스터용 (한국어 폰트 적용)
            - "web-kr": 웹페이지용 (한국어 폰트 적용)
            - "dark-kr": 다크 테마 (한국어 폰트 적용)
        **kwargs : float | str
            프리셋의 기본 설정을 덮어쓸 추가적인 rcParams 설정 (예: font_size=12).
            키 값으로는 언더스코어(font_size) 또는 마침표(font.size) 표기법 모두 지원합니다.

        Raises
        ------
        KeyError
            요청한 프리셋 이름이 presets 딕셔너리에 존재하지 않을 때 발생합니다.

        Examples
        --------
        >>> import dartwork_mpl as dm
        >>> dm.style.use("scientific")
        >>> dm.style.use("presentation-kr", font_size=16)
        """
        if preset_name not in self.presets:
            raise KeyError(f"Preset '{preset_name}' not found")
        self.stack(self.presets[preset_name])

        if kwargs:
            overrides = {}
            for k, v in kwargs.items():
                k_dot = k.replace("_", ".")
                if k_dot in plt.rcParams:
                    overrides[k_dot] = v
                else:
                    overrides[k] = v
            plt.rcParams.update(overrides)

    def presets_dict(self) -> dict[str, list[str]]:
        """
        사용 가능한 모든 프리셋을 딕셔너리 형태로 반환합니다.

        Returns
        -------
        dict[str, list[str]]
            프리셋 이름을 키(key)로 하고 구성 스타일 리스트를 값(value)으로
            갖는 딕셔너리.
        """
        return dict(self.presets.items())


style: Style = Style()
