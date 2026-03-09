"""프롬프트 가이드 파일 관리 모듈.

다트워크 패키지에 번들로 포함된 프롬프트 가이드 마크다운 파일들을
찾고, 읽고, 조회하고, 복사하기 위한 헬퍼 함수들을 제공합니다.
"""

from __future__ import annotations

__all__ = ["prompt_path", "get_prompt", "list_prompts", "copy_prompt"]

from pathlib import Path
from shutil import copy2

from ._helpers import create_parent_path


def prompt_path(name: str) -> Path:
    """지정된 프롬프트 가이드 파일의 절대 경로를 가져옵니다.

    Parameters
    ----------
    name : str
        가져올 프롬프트 가이드의 이름
        (예: ``'layout-guide'``, ``'general-guide'`` 등).

    Returns
    -------
    Path
        조회된 프롬프트 가이드 파일(.md)의 경로.

    Raises
    ------
    ValueError
        해당 이름의 프롬프트 가이드를 라이브러리 내에서 찾을 수 없을 때 발생합니다.
    """
    path: Path = Path(__file__).parent / f"asset/prompt/{name}.md"
    if not path.exists():
        raise ValueError(f"Prompt guide not found: {name}")
    return path


def get_prompt(name: str) -> str:
    """프롬프트 가이드 파일을 읽어서 전체 내용을 문자열로 반환합니다.

    Parameters
    ----------
    name : str
        내용을 조회할 프롬프트 가이드의 이름.

    Returns
    -------
    str
        프롬프트 가이드 파일의 실제 마크다운 문자열 내용.
    """
    path = prompt_path(name)
    return path.read_text(encoding="utf-8")


def list_prompts() -> list[str]:
    """사용 가능한 모든 프롬프트 가이드 파일 목록을 조회합니다.

    Returns
    -------
    list[str]
        활용할 수 있는 프롬프트 가이드 이름들의 정렬된 리스트.
    """
    path: Path = Path(__file__).parent / "asset/prompt"
    if not path.exists():
        return []
    return sorted([p.stem for p in path.glob("*.md")])


def copy_prompt(name: str, destination: str | Path) -> Path:
    """라이브러리 내장 프롬프트 가이드 파일을 지정된 목적지 경로로 복사합니다.

    Parameters
    ----------
    name : str
        복사할 프롬프트 가이드의 이름.
    destination : str | Path
        복사될 목적지 경로.
        만약 디렉토리라면 원본 이름 그대로(``name.md``) 복사되며,
        파일 경로라면 그 이름으로 복사가 완료됩니다.

    Returns
    -------
    Path
        복사가 완료된 새 파일의 절대 경로.

    Raises
    ------
    ValueError
        원본 프롬프트 가이드를 찾을 수 없을 때 발생합니다.
    """
    source_path = prompt_path(name)
    dest_path = Path(destination)

    if dest_path.is_dir() or (not dest_path.exists() and not dest_path.suffix):
        dest_path = dest_path / f"{name}.md"

    create_parent_path(dest_path)
    copy2(source_path, dest_path)

    return dest_path
