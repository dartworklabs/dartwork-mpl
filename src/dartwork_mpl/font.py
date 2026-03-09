"""Matplotlib을 위한 폰트 관리 유틸리티 모듈.

이 모듈은 패키지의 에셋(asset/font) 디렉토리에 있는 커스텀 폰트들을
matplotlib의 내부 폰트 매니저(font manager)에 등록하는 역할을 담당합니다.
"""

from pathlib import Path

from matplotlib import font_manager

__all__ = ["ensure_loaded"]


def _add_fonts() -> None:
    """에셋 디렉토리의 커스텀 폰트들을 matplotlib 폰트 매니저에 일괄 추가합니다.

    이 함수는 ``asset/font`` 디렉토리 내의 폰트 파일들을 검색하고,
    이를 matplotlib의 폰트 매니저에 등록하여 차트 작성 시 해당 폰트들을
    사용할 수 있도록 준비합니다.

    Notes
    -----
    이 함수는 라이브러리가 임포트될 때 자동으로 한 번 호출되므로,
    사용자가 직접 호출할 필요는 없습니다.
    """
    font_dir: list[Path] = [Path(__file__).parent / "asset/font"]
    for font in font_manager.findSystemFonts(font_dir):
        font_manager.fontManager.addfont(font)


_loaded: bool = False


def ensure_loaded() -> None:
    """커스텀 폰트들이 메모리에 성공적으로 로드되고 등록되었는지 확인합니다."""
    global _loaded
    if not _loaded:
        _add_fonts()
        _loaded = True
