"""Tests for prompt module."""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from dartwork_mpl.prompt import (
    _CANONICAL_PROMPTS,
    copy_prompt,
    get_prompt,
    list_prompts,
    prompt_path,
)


class TestPromptPath:
    """Tests for prompt_path()."""

    def test_existing_prompt(self) -> None:
        p = prompt_path("00-index")
        assert p.exists()
        assert p.suffix == ".md"

    def test_policy_exists(self) -> None:
        p = prompt_path("01-policy")
        assert p.exists()

    def test_recipes_exists(self) -> None:
        p = prompt_path("03-recipes")
        assert p.exists()

    def test_anti_patterns_exists(self) -> None:
        p = prompt_path("02-anti-patterns")
        assert p.exists()
        assert p.suffix == ".yaml"

    def test_nonexistent_raises(self) -> None:
        with pytest.raises(ValueError, match="not found"):
            prompt_path("nonexistent_prompt_xyzzy")


class TestGetPrompt:
    """Tests for get_prompt()."""

    def test_returns_string(self) -> None:
        content = get_prompt("00-index")
        assert isinstance(content, str)
        assert len(content) > 0

    def test_returns_anti_patterns_yaml(self) -> None:
        content = get_prompt("02-anti-patterns")
        assert "id: figsize-direct" in content

    def test_nonexistent_raises(self) -> None:
        with pytest.raises(ValueError, match="02-anti-patterns"):
            get_prompt("nonexistent_prompt_xyzzy")


class TestListPrompts:
    """Tests for list_prompts()."""

    def test_returns_list(self) -> None:
        result = list_prompts()
        assert isinstance(result, list)

    def test_contains_canonical_prompts(self) -> None:
        result = list_prompts()
        for name in _CANONICAL_PROMPTS:
            assert name in result, (
                f"canonical prompt {name!r} missing from list_prompts()"
            )

    def test_sorted(self) -> None:
        result = list_prompts()
        assert result == sorted(result)

    def test_canonical_only_after_t5_cleanup(self) -> None:
        """Post-T5 the prompt corpus is exactly the canonical set —
        no ``coding-rules`` / ``general-guide`` / ``layout-guide``
        stubs and no ``_legacy/`` directory."""
        result = list_prompts()
        assert set(result) == _CANONICAL_PROMPTS, (
            f"unexpected prompt files: {set(result) - _CANONICAL_PROMPTS}"
        )
        assert result == [
            "00-index",
            "01-policy",
            "02-anti-patterns",
            "03-recipes",
        ]

    def test_legacy_stubs_removed(self) -> None:
        """The redirect stubs deleted in T5 must stay deleted."""
        for name in ("coding-rules", "general-guide", "layout-guide"):
            with pytest.raises(ValueError, match="not found"):
                prompt_path(name)


class TestDriftGuard:
    """T5 contract: ``list_prompts`` warns when the corpus drifts from
    the declared canonical set."""

    def test_no_warning_on_clean_corpus(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("error")  # any warning becomes a failure
            list_prompts()

    def test_warning_when_unexpected_file_appears(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Stage a fake corpus directory containing the canonical set
        plus one rogue file; confirm ``list_prompts`` emits a
        ``UserWarning`` that names the unexpected entry."""
        fake_corpus = tmp_path / "asset" / "prompt"
        fake_corpus.mkdir(parents=True)
        for name in _CANONICAL_PROMPTS:
            suffix = ".yaml" if name == "02-anti-patterns" else ".md"
            (fake_corpus / f"{name}{suffix}").write_text("stub")
        (fake_corpus / "leaked-old-doc.md").write_text("stale")

        from dartwork_mpl import prompt as prompt_mod

        monkeypatch.setattr(prompt_mod, "_PROMPT_DIR", fake_corpus)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            list_prompts()

        messages = [str(w.message) for w in caught if w.category is UserWarning]
        assert any("Unexpected" in m for m in messages), (
            f"expected drift warning, got: {messages}"
        )
        assert any("leaked-old-doc" in m for m in messages)


class TestCopyPrompt:
    """Tests for copy_prompt()."""

    def test_copy_to_directory(self, tmp_path: Path) -> None:
        result = copy_prompt("00-index", tmp_path)
        assert result.exists()
        assert result.name == "00-index.md"
        assert result.read_text(encoding="utf-8") == get_prompt("00-index")

    def test_copy_anti_patterns_preserves_yaml_suffix(
        self, tmp_path: Path
    ) -> None:
        result = copy_prompt("02-anti-patterns", tmp_path)
        assert result.exists()
        assert result.name == "02-anti-patterns.yaml"
        assert result.suffix == ".yaml"
        assert result.read_text(encoding="utf-8") == get_prompt(
            "02-anti-patterns"
        )

    def test_copy_to_file_path(self, tmp_path: Path) -> None:
        dest = tmp_path / "my_prompt.md"
        result = copy_prompt("00-index", dest)
        assert result == dest
        assert result.exists()

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        dest = tmp_path / "nested" / "dir" / "prompt.md"
        result = copy_prompt("00-index", dest)
        assert result.exists()

    def test_nonexistent_prompt_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            copy_prompt("nonexistent_xyzzy", tmp_path)


def test_anti_patterns_catalog_uses_live_agent_doc_name() -> None:
    content = get_prompt("02-anti-patterns")
    assert 'dm.get_agent_doc("general-guide")' not in content


def test_prompt_corpus_explains_the_color_metric_split() -> None:
    """Keep agent guidance aligned with the accepted color architecture."""
    corpus = "\n".join(
        get_prompt(name)
        for name in ("00-index", "01-policy", "02-anti-patterns")
    )
    normalized = corpus.lower().replace("_", " ").replace("-", " ")
    required = (
        "oklab",
        "oklch",
        "construction",
        "modeled relative cie y",
        "ciede2000",
        "validation",
    )
    missing = [term for term in required if term not in normalized]
    assert not missing, f"missing color-system guidance: {missing}"

    stale_claims = (
        "construction uses cielab",
        "cielab l* target",
        "preserve cielab l*",
        "physical relative y",
    )
    stale = [claim for claim in stale_claims if claim in normalized]
    assert not stale, f"stale hybrid-construction guidance: {stale}"
