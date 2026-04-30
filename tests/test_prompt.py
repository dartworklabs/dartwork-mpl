"""Tests for prompt module."""

from __future__ import annotations

from pathlib import Path

import pytest

from dartwork_mpl.prompt import (
    copy_prompt,
    get_prompt,
    list_prompts,
    prompt_path,
)


class TestPromptPath:
    """Tests for prompt_path()."""

    def test_existing_prompt(self) -> None:
        p = prompt_path("general-guide")
        assert p.exists()
        assert p.suffix == ".md"

    def test_layout_guide_exists(self) -> None:
        p = prompt_path("layout-guide")
        assert p.exists()

    def test_nonexistent_raises(self) -> None:
        with pytest.raises(ValueError, match="not found"):
            prompt_path("nonexistent_prompt_xyzzy")


class TestGetPrompt:
    """Tests for get_prompt()."""

    def test_returns_string(self) -> None:
        content = get_prompt("general-guide")
        assert isinstance(content, str)
        assert len(content) > 0

    def test_nonexistent_raises(self) -> None:
        with pytest.raises(ValueError):
            get_prompt("nonexistent_prompt_xyzzy")


class TestListPrompts:
    """Tests for list_prompts()."""

    def test_returns_list(self) -> None:
        result = list_prompts()
        assert isinstance(result, list)

    def test_contains_known_prompts(self) -> None:
        result = list_prompts()
        assert "general-guide" in result
        assert "layout-guide" in result

    def test_sorted(self) -> None:
        result = list_prompts()
        assert result == sorted(result)


class TestCopyPrompt:
    """Tests for copy_prompt()."""

    def test_copy_to_directory(self, tmp_path: Path) -> None:
        result = copy_prompt("general-guide", tmp_path)
        assert result.exists()
        assert result.name == "general-guide.md"
        assert result.read_text(encoding="utf-8") == get_prompt("general-guide")

    def test_copy_to_file_path(self, tmp_path: Path) -> None:
        dest = tmp_path / "my_prompt.md"
        result = copy_prompt("general-guide", dest)
        assert result == dest
        assert result.exists()

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        dest = tmp_path / "nested" / "dir" / "prompt.md"
        result = copy_prompt("general-guide", dest)
        assert result.exists()

    def test_nonexistent_prompt_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            copy_prompt("nonexistent_xyzzy", tmp_path)


class TestDeprecatedGuideStubs:
    """The 0.3 prompt files (``coding-rules``, ``general-guide``,
    ``layout-guide``) were retired in 0.4. They MUST now be short
    redirect stubs that point readers at the 0.4 SSOT, not stale
    0.3 content (which would mislead an agent)."""

    @pytest.mark.parametrize(
        "name", ["coding-rules", "general-guide", "layout-guide"]
    )
    def test_stub_is_short(self, name: str) -> None:
        body = get_prompt(name)
        # Stale 0.3 files were 460 - 1180 lines. The redirect stubs are
        # well under 100 lines; pick a generous ceiling.
        assert body.count("\n") < 100, (
            f"{name}.md is too long to be a redirect stub "
            f"({body.count(chr(10))} lines); legacy 0.3 content may have "
            "leaked back in."
        )

    @pytest.mark.parametrize(
        "name", ["coding-rules", "general-guide", "layout-guide"]
    )
    def test_stub_points_at_new_ssot(self, name: str) -> None:
        body = get_prompt(name)
        # Each stub must mention the 0.4 SSOT files so callers can
        # follow the redirect manually.
        assert "00-index.md" in body, (
            f"{name}.md should redirect to 00-index.md"
        )
        assert "01-policy.md" in body, f"{name}.md should mention 01-policy.md"

    @pytest.mark.parametrize(
        "name", ["coding-rules", "general-guide", "layout-guide"]
    )
    def test_stub_marks_as_deprecated(self, name: str) -> None:
        body = get_prompt(name)
        assert "DEPRECATED" in body or "Deprecated" in body, (
            f"{name}.md must keep its deprecation notice"
        )
