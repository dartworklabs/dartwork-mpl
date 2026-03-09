"""IDE 연동 및 LLM 어시스턴트를 위한 설치 유틸리티 모듈.

이 모듈은 다양한 IDE 환경(Cursor 등)과 AI 코딩 어시스턴트(Claude Code 등)에
dartwork-mpl 사용 가이드를 자동으로 설치하거나 제거하는 함수들을 제공합니다.
"""

from pathlib import Path

__all__ = ["install_llm_txt", "uninstall_llm_txt"]


def install_llm_txt(project_dir: str | Path | None = None) -> None:
    """프로젝트의 IDE 연동 폴더들에 dartwork-mpl 사용 가이드를 설치합니다.

    이 함수는 다음과 같은 경로에 사용 가이드를 복사하여
    다양한 AI 코딩 어시스턴트들이 라이브러리 컨텍스트를 파악할 수 있도록 돕습니다:
    - ``.claude/commands/`` (Claude Code 용)
    - ``.cursor/`` (Cursor IDE 용)

    Parameters
    ----------
    project_dir : str | Path | None, optional
        설치할 대상 프로젝트 디렉토리 경로. None인 경우
        현재 작업 디렉토리(CWD)를 사용합니다. 기본값은 None.

    Raises
    ------
    FileNotFoundError
        패키지 에셋에서 사용 가이드(USAGE_GUIDE.md) 파일을 찾을 수 없을 때 발생합니다.
    """
    # Get the usage guide path from the asset folder
    usage_guide_path: Path = Path(__file__).parent / "asset" / "USAGE_GUIDE.md"

    if not usage_guide_path.exists():
        raise FileNotFoundError(f"Usage guide not found at: {usage_guide_path}")

    # Get project directory (current working directory if not specified)
    if project_dir is None:
        project_dir_obj: Path = Path.cwd()
    else:
        project_dir_obj = Path(project_dir)

    # Install for Claude Code
    claude_dir: Path = project_dir_obj / ".claude" / "commands"
    claude_dir.mkdir(parents=True, exist_ok=True)
    claude_file: Path = claude_dir / "dartwork-mpl-usage.md"

    # Install for Cursor IDE
    cursor_dir: Path = project_dir_obj / ".cursor"
    cursor_dir.mkdir(parents=True, exist_ok=True)
    cursor_file: Path = cursor_dir / "dartwork-mpl-usage.md"

    # Read the original usage guide
    with open(usage_guide_path, encoding="utf-8") as f:
        content: str = f.read()

    # Create Claude Code version with command prefix
    claude_content: str = f"""# dartwork-mpl Library Usage Command

This command provides comprehensive usage guide for the dartwork-mpl library.

## Usage
Type `/dartwork-mpl` to get help with dartwork-mpl library usage.

---

{content}
"""

    # Create Cursor IDE version with instruction format
    cursor_content: str = f"""// Cursor IDE Instructions for dartwork-mpl library
// This file provides context about dartwork-mpl library usage

{content}
"""

    # Write files
    with open(claude_file, "w", encoding="utf-8") as f:
        f.write(claude_content)

    with open(cursor_file, "w", encoding="utf-8") as f:
        f.write(cursor_content)

    print("✅ dartwork-mpl usage guide installed successfully!")
    print(f"📁 Project: {project_dir_obj}")
    print(f"📁 Claude Code: {claude_file}")
    print(f"📁 Cursor IDE: {cursor_file}")
    print()
    print("🔧 Usage:")
    print("- In Claude Code: Type '/dartwork-mpl' for help")
    print(
        "- In Cursor IDE: The AI will automatically"
        " have access to dartwork-mpl context"
    )


def uninstall_llm_txt(project_dir: str | Path | None = None) -> None:
    """프로젝트의 IDE 연동 폴더들에서 dartwork-mpl 사용 가이드를 제거합니다.

    Parameters
    ----------
    project_dir : str | Path | None, optional
        제거할 대상 프로젝트 디렉토리 경로. None인 경우
        현재 작업 디렉토리(CWD)를 사용합니다. 기본값은 None.
    """
    # Get project directory (current working directory if not specified)
    if project_dir is None:
        project_dir_obj: Path = Path.cwd()
    else:
        project_dir_obj = Path(project_dir)

    # Files to remove
    files_to_remove: list[Path] = [
        project_dir_obj / ".claude" / "commands" / "dartwork-mpl-usage.md",
        project_dir_obj / ".cursor" / "dartwork-mpl-usage.md",
    ]

    removed_files: list[Path] = []
    for file_path in files_to_remove:
        if file_path.exists():
            file_path.unlink()
            removed_files.append(file_path)

    if removed_files:
        print("✅ dartwork-mpl usage guide uninstalled successfully!")
        for file_path in removed_files:
            print(f"🗑️  Removed: {file_path}")
    else:
        print("ℹ️  No dartwork-mpl usage guides found to remove.")


if __name__ == "__main__":
    install_llm_txt()
