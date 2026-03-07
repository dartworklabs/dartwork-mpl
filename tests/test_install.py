"""Tests for install module."""

from __future__ import annotations

from pathlib import Path

import pytest

from dartwork_mpl.install import install_llm_txt, uninstall_llm_txt

# USAGE_GUIDE.md may not exist in all environments
_USAGE_GUIDE_EXISTS = (
    Path(__file__).parent.parent
    / "src"
    / "dartwork_mpl"
    / "asset"
    / "USAGE_GUIDE.md"
).exists()


@pytest.mark.skipif(
    not _USAGE_GUIDE_EXISTS,
    reason="USAGE_GUIDE.md asset not present",
)
class TestInstallLlmTxt:
    """Tests for install_llm_txt()."""

    def test_creates_files(self, tmp_path: Path) -> None:
        install_llm_txt(project_dir=tmp_path)

        claude_file = (
            tmp_path
            / ".claude"
            / "commands"
            / "dartwork-mpl-usage.md"
        )
        cursor_file = (
            tmp_path / ".cursor" / "dartwork-mpl-usage.md"
        )

        assert claude_file.exists()
        assert cursor_file.exists()

    def test_claude_has_content(self, tmp_path: Path) -> None:
        install_llm_txt(project_dir=tmp_path)

        claude_file = (
            tmp_path
            / ".claude"
            / "commands"
            / "dartwork-mpl-usage.md"
        )
        content = claude_file.read_text(encoding="utf-8")
        assert "dartwork-mpl" in content
        assert len(content) > 100


@pytest.mark.skipif(
    not _USAGE_GUIDE_EXISTS,
    reason="USAGE_GUIDE.md asset not present",
)
class TestUninstallLlmTxt:
    """Tests for uninstall_llm_txt()."""

    def test_removes_installed_files(
        self, tmp_path: Path
    ) -> None:
        install_llm_txt(project_dir=tmp_path)
        uninstall_llm_txt(project_dir=tmp_path)

        claude_file = (
            tmp_path
            / ".claude"
            / "commands"
            / "dartwork-mpl-usage.md"
        )
        assert not claude_file.exists()


class TestUninstallWhenEmpty:
    """Tests for uninstall when nothing is installed."""

    def test_no_error_when_nothing_installed(
        self, tmp_path: Path
    ) -> None:
        """Should not crash when no files exist."""
        uninstall_llm_txt(project_dir=tmp_path)
