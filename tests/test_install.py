"""Tests for install module."""

from __future__ import annotations

from pathlib import Path

import pytest

from dartwork_mpl.install import install_llm_txt, uninstall_llm_txt

# SSOT prompt directory must exist for install_llm_txt to compose its
# bundle. In well-formed checkouts it always does; the skip is only a
# safety net for partial vendoring scenarios.
_SSOT_DIR_EXISTS = (
    Path(__file__).parent.parent
    / "src"
    / "dartwork_mpl"
    / "asset"
    / "prompt"
    / "00-index.md"
).exists()


@pytest.mark.skipif(
    not _SSOT_DIR_EXISTS,
    reason="asset/prompt SSOT not present in this checkout",
)
class TestInstallLlmTxt:
    """Tests for install_llm_txt()."""

    def test_creates_files(self, tmp_path: Path) -> None:
        install_llm_txt(project_dir=tmp_path)

        claude_file = (
            tmp_path / ".claude" / "commands" / "dartwork-mpl-usage.md"
        )
        cursor_file = tmp_path / ".cursor" / "dartwork-mpl-usage.md"

        assert claude_file.exists()
        assert cursor_file.exists()

    def test_claude_bundle_includes_ssot_pieces(self, tmp_path: Path) -> None:
        install_llm_txt(project_dir=tmp_path)

        claude_file = (
            tmp_path / ".claude" / "commands" / "dartwork-mpl-usage.md"
        )
        content = claude_file.read_text(encoding="utf-8")
        # The bundle composes the SSOT pieces; verify each is named.
        assert "dartwork-mpl" in content
        assert "00-index.md" in content
        assert "01-policy.md" in content
        assert "03-recipes.md" in content
        assert len(content) > 500

    def test_cursor_bundle_does_not_use_legacy_zero_resize(
        self, tmp_path: Path
    ) -> None:
        """Installed bundle must reflect the 0.4 width/aspect policy.

        The retired "Zero-Resize" phrase must not appear anywhere in
        the bundle. If a future SSOT file ever needs to mention it
        (e.g. a migration note in the human-facing guide), that file
        should be excluded from the install bundle, not allowed to
        leak the deprecated language to AI assistants.
        """
        install_llm_txt(project_dir=tmp_path)

        cursor_file = tmp_path / ".cursor" / "dartwork-mpl-usage.md"
        content = cursor_file.read_text(encoding="utf-8")
        assert "Zero-Resize" not in content


@pytest.mark.skipif(
    not _SSOT_DIR_EXISTS,
    reason="asset/prompt SSOT not present in this checkout",
)
class TestUninstallLlmTxt:
    """Tests for uninstall_llm_txt()."""

    def test_removes_installed_files(self, tmp_path: Path) -> None:
        install_llm_txt(project_dir=tmp_path)
        uninstall_llm_txt(project_dir=tmp_path)

        claude_file = (
            tmp_path / ".claude" / "commands" / "dartwork-mpl-usage.md"
        )
        assert not claude_file.exists()


class TestUninstallWhenEmpty:
    """Tests for uninstall when nothing is installed."""

    def test_no_error_when_nothing_installed(self, tmp_path: Path) -> None:
        """Should not crash when no files exist."""
        uninstall_llm_txt(project_dir=tmp_path)
