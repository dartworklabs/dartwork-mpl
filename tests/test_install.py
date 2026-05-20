"""Tests for install module."""

from __future__ import annotations

from pathlib import Path

import pytest

from dartwork_mpl.install import (
    INSTALL_TARGETS,
    install_llm_txt,
    uninstall_llm_txt,
)

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


@pytest.fixture(autouse=True)
def _isolate_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the working directory to ``tmp_path`` for every test here.

    All tests in this module pass ``project_dir=tmp_path`` explicitly,
    so install/uninstall already write inside the pytest tmp tree.
    This guard adds a second line of defence: if a future test ever
    forgets the explicit argument, ``Path.cwd()`` (the install module's
    fallback) will resolve into ``tmp_path`` instead of e.g. the
    user's home directory, where running ``pytest`` from anywhere
    could otherwise create real ``.claude/`` / ``.cursor/`` folders.
    """
    monkeypatch.chdir(tmp_path)


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


@pytest.mark.skipif(
    not _SSOT_DIR_EXISTS,
    reason="asset/prompt SSOT not present in this checkout",
)
class TestMultiTargetInstall:
    """Multi-target install support (Copilot, Codex, Gemini, Continue,
    Aider, Windsurf, Cursor MDC). Back-compat: ``targets=None``
    installs only the legacy claude + cursor pair.
    """

    def test_default_targets_match_legacy_pair(self, tmp_path: Path) -> None:
        written = install_llm_txt(project_dir=tmp_path)
        assert set(written.keys()) == {"claude", "cursor"}

    def test_targets_all_writes_every_known_target(
        self, tmp_path: Path
    ) -> None:
        written = install_llm_txt(project_dir=tmp_path, targets="all")
        assert set(written.keys()) == set(INSTALL_TARGETS)
        # Spot-check each canonical destination exists.
        assert (tmp_path / "AGENTS.md").exists()
        assert (tmp_path / "GEMINI.md").exists()
        assert (tmp_path / "CONVENTIONS.md").exists()
        assert (tmp_path / ".github" / "copilot-instructions.md").exists()
        assert (tmp_path / ".continue" / "rules" / "dartwork-mpl.md").exists()
        assert (tmp_path / ".windsurf" / "rules" / "dartwork-mpl.md").exists()
        assert (tmp_path / ".cursor" / "rules" / "dartwork-mpl.mdc").exists()

    def test_targets_list_selects_specific_targets(
        self, tmp_path: Path
    ) -> None:
        written = install_llm_txt(
            project_dir=tmp_path, targets=["copilot", "aider"]
        )
        assert set(written.keys()) == {"copilot", "aider"}
        assert (tmp_path / ".github" / "copilot-instructions.md").exists()
        assert (tmp_path / "CONVENTIONS.md").exists()
        assert not (tmp_path / ".claude").exists()
        assert not (tmp_path / ".cursor").exists()

    def test_unknown_target_raises(self, tmp_path: Path) -> None:
        with pytest.raises(KeyError, match="Unknown install target"):
            install_llm_txt(project_dir=tmp_path, targets=["not-a-target"])

    def test_cursor_mdc_has_frontmatter(self, tmp_path: Path) -> None:
        install_llm_txt(project_dir=tmp_path, targets=["cursor-rules"])
        mdc = (tmp_path / ".cursor" / "rules" / "dartwork-mpl.mdc").read_text(
            encoding="utf-8"
        )
        # MDC files start with YAML front-matter.
        assert mdc.startswith("---\n")
        assert "description:" in mdc
        assert "globs:" in mdc

    def test_bundle_includes_templates_quick_reference(
        self, tmp_path: Path
    ) -> None:
        install_llm_txt(project_dir=tmp_path)
        body = (
            tmp_path / ".claude" / "commands" / "dartwork-mpl-usage.md"
        ).read_text(encoding="utf-8")
        # Quick-reference header + at least one canonical template row.
        assert "AI Plot Templates" in body
        assert "| `bar` |" in body
        assert "| `line` |" in body

    def test_uninstall_all_targets_cleans_up_everything(
        self, tmp_path: Path
    ) -> None:
        install_llm_txt(project_dir=tmp_path, targets="all")
        removed = uninstall_llm_txt(project_dir=tmp_path)
        # Every file listed in INSTALL_TARGETS should be gone.
        assert len(removed) >= len(INSTALL_TARGETS)
        assert not (tmp_path / "AGENTS.md").exists()
        assert not (tmp_path / "GEMINI.md").exists()
        assert not (tmp_path / "CONVENTIONS.md").exists()
