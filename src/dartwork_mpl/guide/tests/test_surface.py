"""The guide surface as an agent uses it: lint and install."""

from __future__ import annotations

import shutil

import pytest

import dartwork_mpl as dm
from dartwork_mpl import guide
from dartwork_mpl.guide import install
from dartwork_mpl.guide.__main__ import main


def test_lint_code_reads_live_registries():
    found = dm.lint_code(
        'ax.plot(x, color="dc.blue6")\nax.imshow(z, cmap="dc.blu")'
    )
    assert [(f.rule_id, str(f.severity), f.line) for f in found] == [
        ("invalid-colormap-name", "critical", 2)
    ]


def test_lint_rules_are_what_lint_code_reports():
    rules = {r["id"]: r for r in dm.lint_rules()}
    assert len(rules) == len(dm.lint_rules())
    found = dm.lint_code(
        "fig, ax = plt.subplots(figsize=(6, 4))\nfig.tight_layout()"
    )
    assert len(found) == 2
    for f in found:
        assert rules[f.rule_id] == {
            "id": f.rule_id,
            "severity": str(f.severity),
            "message": f.message,
            "fix": f.fix,
        }


def test_install_copies_from_outside_the_project_and_refreshes(tmp_path):
    """uvx and global installs live outside the project: a link would break."""
    done = guide.install_skill(tmp_path)
    assert [d.action for d in done] == ["copied", "copied"]
    skill = tmp_path / ".claude/skills/dartwork-mpl/SKILL.md"
    assert skill.read_text(encoding="utf-8") == (
        guide.skill_path() / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert [d.action for d in guide.install_skill(tmp_path)] == ["copied"] * 2

    foreign = tmp_path / "other"
    (foreign / ".agents/skills/dartwork-mpl").mkdir(parents=True)
    with pytest.raises(FileExistsError, match="--force"):
        guide.install_skill(foreign)
    assert main(["install", "--dest", str(foreign), "--force"]) == 0
    assert (foreign / ".agents/skills/dartwork-mpl/SKILL.md").is_file()


def test_install_links_from_the_project_venv_and_copy_replaces_it(
    tmp_path, monkeypatch
):
    """After ``uv add`` the package is inside the project: link it."""
    inside = tmp_path / ".venv/dartwork_mpl/guide/assets/skill"
    shutil.copytree(guide.skill_path(), inside)
    monkeypatch.setattr(install, "skill_path", lambda: inside)
    assert [d.action for d in install.install_skill(tmp_path)] == ["linked"] * 2
    assert [d.action for d in install.install_skill(tmp_path)] == [
        "unchanged"
    ] * 2
    done = install.install_skill(tmp_path, copy=True)
    assert [d.action for d in done] == ["copied"] * 2
    assert not done[0].path.is_symlink()


def test_install_skips_a_folder_linked_to_another(tmp_path):
    (tmp_path / ".claude/skills").mkdir(parents=True)
    (tmp_path / ".agents").mkdir()
    (tmp_path / ".agents/skills").symlink_to(tmp_path / ".claude/skills")
    assert len(guide.install_skill(tmp_path, copy=True)) == 1
