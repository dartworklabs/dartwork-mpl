"""Tests for ``scripts/extract_release_notes.py``.

The reflow logic is the second half of the release process: we cut a
section from ``CHANGELOG.md`` and feed it to ``gh release create``.
The CHANGELOG keeps the Keep-a-Changelog hard-wrap convention, so
without reflow the GitHub release page renders at half-column width
(observed empirically on v0.5.3 before reflow was applied).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _REPO_ROOT / "scripts" / "extract_release_notes.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "extract_release_notes", _SCRIPT
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def mod():
    return _load_module()


_CHANGELOG_SAMPLE = """# Changelog

## [Unreleased]

## [0.5.3] - 2026-06-20

### Added
- **18 tier-2 advanced plot templates** under
  `asset/prompt/05-templates/advanced/` — one per existing basic
  template.
- **3 new MCP tools**:
  - `suggest_chart_type` — recommends a chart type from data shape
    before writing code.
  - `compose_layered_plot` — returns an `{applied, missing}`
    checklist.

### Fixed
- Existing lint + execution
  + visual-validation chain wired through (PR #344).

## [0.5.2] - 2026-06-09

### Added
- Earlier stuff.
"""


class TestExtractSection:
    def test_finds_target_version(self, mod) -> None:
        body = mod.extract_section(_CHANGELOG_SAMPLE, "0.5.3")
        assert "### Added" in body
        assert "### Fixed" in body
        # Must NOT include the next section's header or body.
        assert "0.5.2" not in body
        assert "Earlier stuff" not in body

    def test_missing_version_raises(self, mod) -> None:
        with pytest.raises(LookupError):
            mod.extract_section(_CHANGELOG_SAMPLE, "9.9.9")

    def test_unreleased_section_is_empty_body(self, mod) -> None:
        body = mod.extract_section(_CHANGELOG_SAMPLE, "Unreleased")
        # Body is empty (the only thing between headers is whitespace).
        assert body == ""


class TestReflow:
    def test_paragraph_collapses_to_one_line(self, mod) -> None:
        out = mod.reflow(
            "- **18 templates** under\n  `path/` — one per template.\n"
        )
        # The bullet line ends up as a single long line.
        bullet_lines = [
            line for line in out.splitlines() if line.startswith("-")
        ]
        assert len(bullet_lines) == 1
        assert "templates" in bullet_lines[0]
        assert "one per template" in bullet_lines[0]

    def test_plus_inside_text_is_not_a_new_bullet(self, mod) -> None:
        """Regression guard for the v0.5.3 reflow trap.

        ``lint + execution`` continued onto a new line as ``  + visual``
        used to be misparsed as a brand-new bullet, splitting the
        item. The fix excludes ``+`` from bullet detection — markdown
        lists in this repo use only ``-`` and ``*``.
        """
        out = mod.reflow(
            "- Existing lint + execution\n  + visual-validation chain.\n"
        )
        bullet_lines = [
            line
            for line in out.splitlines()
            if line.lstrip().startswith(("- ", "* "))
        ]
        assert len(bullet_lines) == 1
        assert "lint + execution + visual-validation" in bullet_lines[0]

    def test_headings_preserved(self, mod) -> None:
        out = mod.reflow("### Added\n- item one.\n\n### Fixed\n- item two.\n")
        lines = out.splitlines()
        assert "### Added" in lines
        assert "### Fixed" in lines

    def test_nested_bullets_preserve_indent(self, mod) -> None:
        out = mod.reflow(
            "- top item:\n  - nested item with continuation\n    text.\n"
        )
        # Two bullets in output, second one indented.
        bullets = [
            line for line in out.splitlines() if line.lstrip().startswith("- ")
        ]
        assert len(bullets) == 2
        assert bullets[0].startswith("- ")
        assert bullets[1].startswith("  - ")
        assert "continuation text" in bullets[1]

    def test_blank_lines_separate_paragraphs(self, mod) -> None:
        out = mod.reflow("- one.\n\n- two.\n")
        assert "\n\n" in out
