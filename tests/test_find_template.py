"""Tests for the AI plot template metadata index + find_template (T6)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import dartwork_mpl as dm
from dartwork_mpl.prompt import _PROMPT_DIR, find_template

_INDEX_PATH: Path = _PROMPT_DIR / "05-templates" / "_index.json"


@pytest.fixture(scope="module")
def index() -> dict[str, dict[str, object]]:
    assert _INDEX_PATH.exists(), (
        "Template index not built. Run sphinx-build to regenerate "
        "src/dartwork_mpl/asset/prompt/05-templates/_index.json."
    )
    return json.loads(_INDEX_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def basic_index(
    index: dict[str, dict[str, object]],
) -> dict[str, dict[str, object]]:
    """The 18 tier-1 (basic) entries, stripping the nested 'advanced' key."""
    return {k: v for k, v in index.items() if k != "advanced"}


@pytest.fixture(scope="module")
def advanced_index(
    index: dict[str, dict[str, object]],
) -> dict[str, dict[str, object]]:
    """The 18 tier-2 (advanced) entries."""
    return index.get("advanced", {})  # type: ignore[return-value]


class TestIndexShape:
    """The bundled metadata index follows the documented schema.

    Each test runs once against the basic index and once against the
    advanced index (parametrised via the ``tier_index`` fixture).
    """

    REQUIRED_KEYS: frozenset[str] = frozenset(
        {"use_case", "difficulty", "data_shape", "tags", "source_path"}
    )
    DIFFICULTIES: frozenset[str] = frozenset(
        {"beginner", "intermediate", "advanced"}
    )

    @pytest.fixture(params=["basic", "advanced"])
    def tier_index(
        self,
        request: pytest.FixtureRequest,
        basic_index: dict[str, dict[str, object]],
        advanced_index: dict[str, dict[str, object]],
    ) -> dict[str, dict[str, object]]:
        return basic_index if request.param == "basic" else advanced_index

    def test_eighteen_entries(
        self, tier_index: dict[str, dict[str, object]]
    ) -> None:
        assert len(tier_index) == 18

    def test_required_keys_present(
        self, tier_index: dict[str, dict[str, object]]
    ) -> None:
        for template_id, meta in tier_index.items():
            missing = self.REQUIRED_KEYS - meta.keys()
            assert not missing, f"{template_id}: missing keys {sorted(missing)}"

    def test_difficulty_in_enum(
        self, tier_index: dict[str, dict[str, object]]
    ) -> None:
        for template_id, meta in tier_index.items():
            assert meta["difficulty"] in self.DIFFICULTIES, (
                f"{template_id}: bad difficulty {meta['difficulty']!r}"
            )

    def test_tags_are_nonempty_strings(
        self, tier_index: dict[str, dict[str, object]]
    ) -> None:
        for template_id, meta in tier_index.items():
            tags = meta["tags"]
            assert isinstance(tags, list) and tags, (
                f"{template_id}: tags must be a non-empty list"
            )
            for tag in tags:
                assert isinstance(tag, str) and tag.strip()

    def test_source_path_resolves(
        self, tier_index: dict[str, dict[str, object]]
    ) -> None:
        repo_root = _INDEX_PATH.parents[5]  # walk up to repo root
        for template_id, meta in tier_index.items():
            src = repo_root / meta["source_path"]  # type: ignore[arg-type]
            assert src.exists(), (
                f"{template_id}: source_path {src} does not exist"
            )


class TestFindTemplate:
    """T6 success criterion E: intent matching ranks the right template."""

    def test_horizontal_bar_intent_returns_bar_horizontal_first(self) -> None:
        # ``horizontal`` only matches plot_bar_horizontal's tags;
        # ``bar`` matches every bar variant. Together that's enough to
        # rank bar_horizontal first.
        results = find_template("horizontal bar")
        assert results, "expected at least one match"
        assert results[0]["template_id"] == "bar_horizontal"

    def test_distribution_intent_finds_distribution_templates(self) -> None:
        results = find_template("distribution of a single sample")
        ids = [r["template_id"] for r in results]
        # histogram is the strongest match for that exact phrase.
        assert "histogram" in ids

    def test_correlation_intent_finds_scatter(self) -> None:
        results = find_template("correlation between two variables")
        ids = [r["template_id"] for r in results]
        assert "scatter" in ids

    def test_top_k_caps_results(self) -> None:
        results = find_template("bar", top_k=2)
        assert len(results) <= 2

    def test_unmatchable_intent_returns_empty(self) -> None:
        # "xyzzy" appears in no metadata field.
        assert find_template("xyzzy") == []

    def test_blank_intent_returns_empty(self) -> None:
        assert find_template("") == []
        assert find_template("    ") == []

    def test_results_carry_score_and_metadata(self) -> None:
        results = find_template("bar")
        assert results
        first = results[0]
        for key in ("template_id", "score", "use_case", "difficulty", "tags"):
            assert key in first
        assert first["score"] >= 1


class TestPublicSurface:
    """T6: find_template is reachable as dm.find_template."""

    def test_top_level_find_template(self) -> None:
        assert callable(dm.find_template)
        assert dm.find_template is find_template

    def test_in_dunder_all(self) -> None:
        assert "find_template" in dm.__all__
