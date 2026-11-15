"""The guide surface as an agent uses it: read, search, lint, install."""

from __future__ import annotations

import pytest

import dartwork_mpl as dm
from dartwork_mpl import guide
from dartwork_mpl.guide.__main__ import main


def test_every_reference_reads_and_an_unknown_one_is_refused():
    refs = guide.references()
    assert {"guide/skill", "guide/anti-patterns", "template/bar"} <= {
        r.id for r in refs
    }
    assert sum(r.id.startswith("template/advanced/") for r in refs) == 18
    assert guide.read("guide/skill").startswith("---\nname: dartwork-mpl")
    with pytest.raises(ValueError, match="no reference"):
        guide.read("template/nope")


def test_search_finds_the_template_an_agent_asks_for():
    assert guide.search("horizontal bar ranking")[0].id.endswith(
        "bar_horizontal"
    )
    assert guide.search("korean")[0].id == "guide/korean"


def test_lint_code_reads_live_registries():
    found = dm.lint_code(
        'ax.plot(x, color="dc.blue6")\nax.imshow(z, cmap="dc.blu")'
    )
    assert [(f.rule_id, str(f.severity), f.line) for f in found] == [
        ("invalid-colormap-name", "critical", 2)
    ]


def test_install_links_once_per_folder_and_keeps_foreign_files(tmp_path):
    done = guide.install_skill(tmp_path)
    assert [d.action for d in done] == ["linked", "linked"]
    skill = tmp_path / ".claude/skills/dartwork-mpl/SKILL.md"
    assert skill.read_text(encoding="utf-8") == guide.read("guide/skill")
    assert [d.action for d in guide.install_skill(tmp_path)] == [
        "unchanged"
    ] * 2

    foreign = tmp_path / "other"
    (foreign / ".agents/skills/dartwork-mpl").mkdir(parents=True)
    with pytest.raises(FileExistsError, match="--force"):
        guide.install_skill(foreign)
    assert main(["install", "--dest", str(foreign), "--copy", "--force"]) == 0
    assert (foreign / ".agents/skills/dartwork-mpl/SKILL.md").is_file()


def test_install_skips_a_folder_linked_to_another(tmp_path):
    (tmp_path / ".claude/skills").mkdir(parents=True)
    (tmp_path / ".agents").mkdir()
    (tmp_path / ".agents/skills").symlink_to(tmp_path / ".claude/skills")
    assert len(guide.install_skill(tmp_path, copy=True)) == 1
