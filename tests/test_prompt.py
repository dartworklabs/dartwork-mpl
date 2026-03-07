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
        assert result.read_text(encoding="utf-8") == get_prompt(
            "general-guide"
        )

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
