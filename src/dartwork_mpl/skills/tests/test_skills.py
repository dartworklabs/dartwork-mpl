"""The bundled agent skill: its format, its code, and its installer.

An agent in an unrelated project reads ``SKILL.md`` first and the
``references/`` files on demand, and runs their code. So the format limits
of the Agent Skills standard are checked, every Python block is executed and
linted, and the installer is exercised on real directories (symlinks,
copies, foreign folders and the ``.claude/skills -> .agents/skills`` link).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

import matplotlib as mpl
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import pytest
import yaml

import dartwork_mpl as dm
import dartwork_mpl.skills as skills_module
from dartwork_mpl.skills import (
    SKILL_NAME,
    SkillInstallError,
    install_skill,
    skill_path,
    skill_version,
)
from dartwork_mpl.skills.__main__ import main

SKILL = skill_path()
SKILL_MD = SKILL / "SKILL.md"
REFERENCES = sorted((SKILL / "references").glob("*.md"))
CONSUMER_ENTRY = Path(dm.agent_doc_path("AGENTS"))
TRIGGERS = (
    "matplotlib",
    "plot",
    "chart",
    "figure",
    "graph",
    "그래프",
    "그림",
    "플롯",
)
_FENCE = re.compile(r"```python\n(.*?)```", re.S)


def _frontmatter(text: str) -> dict[str, object]:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert match, "SKILL.md must start with YAML frontmatter"
    data = yaml.safe_load(match.group(1))
    assert isinstance(data, dict)
    return data


def test_frontmatter_follows_the_agent_skills_format() -> None:
    meta = _frontmatter(SKILL_MD.read_text(encoding="utf-8"))
    name = meta["name"]
    assert name == SKILL_NAME == SKILL.name
    assert isinstance(name, str)
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name)
    assert len(name) <= 64
    description = meta["description"]
    assert isinstance(description, str)
    assert len(description) <= 1024
    assert set(meta) <= {"name", "description", "license", "metadata"}


def test_description_leads_with_trigger_words() -> None:
    """Skill lists truncate descriptions; the triggers come first."""
    description = _frontmatter(SKILL_MD.read_text(encoding="utf-8"))[
        "description"
    ]
    assert isinstance(description, str)
    head = description[:120]
    missing = [word for word in TRIGGERS if word not in head]
    assert not missing, f"move {missing} into the first 120 characters"


def test_skill_body_stays_a_short_router() -> None:
    lines = SKILL_MD.read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 120


def test_references_are_one_level_deep_and_all_routed() -> None:
    text = SKILL_MD.read_text(encoding="utf-8")
    linked = set(re.findall(r"references/([\w.-]+\.md)", text))
    present = {p.name for p in REFERENCES}
    assert linked == present, (linked, present)
    nested = [p for p in (SKILL / "references").rglob("*") if p.is_dir()]
    assert not nested
    other = {
        p.name
        for p in SKILL.iterdir()
        if p.name not in {"SKILL.md", "references"}
    }
    assert not other, f"unexpected files in the skill folder: {other}"


def test_skill_states_how_to_coexist_with_dataviz() -> None:
    text = SKILL_MD.read_text(encoding="utf-8")
    assert "/dataviz" in text
    for rule in ("static", "dm.figsize", "hover", "rounded bar"):
        assert rule in text


def test_consumer_entry_is_short_and_points_to_the_skill() -> None:
    text = dm.get_agent_doc("AGENTS")
    assert dm.get_agent_doc("CLAUDE") == text
    assert len(text.splitlines()) <= 60
    assert "python -m dartwork_mpl.skills install" in text
    assert "SKILL.md" in text
    for contributor_rule in (
        "ADR",
        "test_shipped_colors_hash",
        "design document",
    ):
        assert contributor_rule not in text


_DOCS = [SKILL_MD, *REFERENCES, CONSUMER_ENTRY]


@pytest.mark.parametrize("doc", _DOCS, ids=lambda p: p.name)
def test_python_blocks_run_and_pass_lint(
    doc: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each document's blocks run in order in one namespace, like a reader would."""
    blocks = _FENCE.findall(doc.read_text(encoding="utf-8"))
    assert blocks, f"{doc.name} has no python example"
    monkeypatch.chdir(tmp_path)
    namespace: dict[str, object] = {"__name__": "__skill_example__"}
    for block in blocks:
        critical = [
            issue
            for issue in dm.lint_code(block)
            if issue.severity == "critical"
        ]
        assert not critical, critical
        exec(compile(block, f"{doc.name}:example", "exec"), namespace)
        plt.close("all")


def test_listed_aspect_tokens_and_presets_match_runtime() -> None:
    text = SKILL_MD.read_text(encoding="utf-8")
    line = next(
        ln for ln in text.split("\n- ") if ln.startswith("Aspect tokens")
    )
    listed = set(re.findall(r"`(\w+)`", line))
    assert listed == set(dm.list_aspect_tokens())
    table = text.split("## Preset by purpose", 1)[1].split("##", 1)[0]
    presets = set(re.findall(r"`([a-z]+)`", table))
    base = {name for name in dm.style.presets if not name.endswith("-kr")}
    assert presets == base


def test_template_list_matches_bundled_templates() -> None:
    text = (SKILL / "references" / "templates.md").read_text(encoding="utf-8")
    names = re.search(r"runnable script:(.*?)\.", text, re.S)
    count = re.search(r"ships (\d+) chart types", text)
    assert names and count
    listed = {name.strip() for name in names.group(1).split(",")}
    folder = Path(dm.prompt_path("00-index")).parent / "05-templates"
    basic = {p.stem for p in folder.glob("*.py")}
    advanced = {p.stem for p in (folder / "advanced").glob("*.py")}
    assert listed == basic == advanced
    assert int(count.group(1)) == len(basic)


def test_korean_reference_lists_every_kr_preset() -> None:
    text = (SKILL / "references" / "korean.md").read_text(encoding="utf-8")
    listed = set(re.findall(r"`([a-z]+-kr)`", text))
    assert listed == {n for n in dm.style.presets if n.endswith("-kr")}


def test_every_colour_or_colormap_name_exists() -> None:
    """Prose names (not only code) are copied by agents; each must resolve."""
    named = set(mcolors.get_named_colors_mapping())
    cmaps = set(mpl.colormaps)
    text = "\n".join(p.read_text(encoding="utf-8") for p in _DOCS)
    names = set(
        re.findall(r"\b(?:dc|oc|tw|md|ad|cu|pr)\.[a-z][a-z_0-9]*", text)
    )
    assert len(names) > 20
    assert not {n for n in names if n not in named | cmaps}


# ---------------------------------------------------------------- installer


def _is_link_to_skill(path: Path) -> bool:
    return path.is_symlink() and path.resolve() == SKILL


def test_install_links_both_agents_and_is_idempotent(tmp_path: Path) -> None:
    first = install_skill(tmp_path)
    assert [(r.target, r.action) for r in first] == [
        ("claude", "linked"),
        ("codex", "linked"),
    ]
    assert _is_link_to_skill(tmp_path / ".claude/skills" / SKILL_NAME)
    assert _is_link_to_skill(tmp_path / ".agents/skills" / SKILL_NAME)
    assert (tmp_path / ".claude/skills" / SKILL_NAME / "SKILL.md").is_file()

    again = install_skill(tmp_path)
    assert [r.action for r in again] == ["unchanged", "unchanged"]


def test_install_one_target(tmp_path: Path) -> None:
    (result,) = install_skill(tmp_path, targets=["codex"])
    assert result.action == "linked"
    assert not (tmp_path / ".claude").exists()


_MARKER = ".dartwork-mpl-skill.json"


def _leftovers(skills_dir: Path) -> list[str]:
    """Temporary staging folders the installer left behind."""
    return [p.name for p in skills_dir.iterdir() if p.name != SKILL_NAME]


def test_copy_records_hashes_and_is_idempotent(tmp_path: Path) -> None:
    (result,) = install_skill(tmp_path, targets=["claude"], copy=True)
    copy = tmp_path / ".claude/skills" / SKILL_NAME
    assert result.action == "copied"
    assert copy.is_dir() and not copy.is_symlink()
    assert (copy / "SKILL.md").read_bytes() == SKILL_MD.read_bytes()
    marker = json.loads((copy / _MARKER).read_text(encoding="utf-8"))
    assert marker["version"] == skill_version()
    assert (
        marker["files"]["SKILL.md"]
        == hashlib.sha256(SKILL_MD.read_bytes()).hexdigest()
    )
    assert set(marker["files"]) == {
        p.relative_to(SKILL).as_posix() for p in SKILL.rglob("*") if p.is_file()
    }

    (again,) = install_skill(tmp_path, targets=["claude"], copy=True)
    assert again.action == "unchanged"
    assert not _leftovers(copy.parent)


def test_untouched_copy_from_an_older_version_is_refreshed(
    tmp_path: Path,
) -> None:
    """A copy whose files still match its own record is safe to replace."""
    install_skill(tmp_path, targets=["claude"], copy=True)
    copy = tmp_path / ".claude/skills" / SKILL_NAME
    old = copy / "references" / "korean.md"
    old.write_text("from an older dartwork-mpl", encoding="utf-8")
    marker = json.loads((copy / _MARKER).read_text(encoding="utf-8"))
    marker["files"]["references/korean.md"] = hashlib.sha256(
        old.read_bytes()
    ).hexdigest()
    (copy / _MARKER).write_text(json.dumps(marker), encoding="utf-8")

    (refreshed,) = install_skill(tmp_path, targets=["claude"], copy=True)
    assert refreshed.action == "replaced"
    assert old.read_bytes() == (SKILL / "references" / "korean.md").read_bytes()
    assert not _leftovers(copy.parent)


@pytest.mark.parametrize("copy_again", [True, False], ids=["copy", "link"])
def test_edited_copy_is_refused_unless_forced(
    tmp_path: Path, copy_again: bool
) -> None:
    install_skill(tmp_path, targets=["claude"], copy=True)
    copy = tmp_path / ".claude/skills" / SKILL_NAME
    edited = copy / "references" / "korean.md"
    edited.write_text("my team's Korean notes", encoding="utf-8")

    with pytest.raises(SkillInstallError, match=r"references/korean\.md"):
        install_skill(tmp_path, targets=["claude"], copy=copy_again)
    assert edited.read_text(encoding="utf-8") == "my team's Korean notes"

    (forced,) = install_skill(
        tmp_path, targets=["claude"], copy=copy_again, force=True
    )
    assert forced.action == "replaced"
    assert _is_link_to_skill(copy) is not copy_again
    assert (
        edited.read_bytes() == (SKILL / "references" / "korean.md").read_bytes()
    )


def test_copy_with_an_unreadable_marker_is_refused(tmp_path: Path) -> None:
    install_skill(tmp_path, targets=["codex"], copy=True)
    copy = tmp_path / ".agents/skills" / SKILL_NAME
    (copy / _MARKER).write_text("not json", encoding="utf-8")
    with pytest.raises(SkillInstallError, match="unreadable"):
        install_skill(tmp_path, targets=["codex"], copy=True)


def test_failed_swap_keeps_the_previous_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_skill(tmp_path, targets=["claude"], copy=True)
    copy = tmp_path / ".claude/skills" / SKILL_NAME
    before = {
        p.relative_to(copy).as_posix(): p.read_bytes()
        for p in copy.rglob("*")
        if p.is_file()
    }
    real_replace = os.replace

    def fail_into_place(src: Path, dst: Path) -> None:
        if Path(dst) == copy and Path(src).name == SKILL_NAME:
            raise OSError("disk full")
        real_replace(src, dst)

    monkeypatch.setattr(skills_module.os, "replace", fail_into_place)
    with pytest.raises(SkillInstallError, match="previous install was kept"):
        install_skill(tmp_path, targets=["claude"], force=True)

    after = {
        p.relative_to(copy).as_posix(): p.read_bytes()
        for p in copy.rglob("*")
        if p.is_file()
    }
    assert not copy.is_symlink()
    assert after == before
    assert not _leftovers(copy.parent)


def test_failed_staging_changes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failure while building the new copy leaves every target untouched."""
    install_skill(tmp_path)  # links for both agents

    def no_space(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(skills_module.shutil, "copytree", no_space)
    with pytest.raises(SkillInstallError, match="disk full"):
        install_skill(tmp_path, copy=True)
    for rel in (".claude/skills", ".agents/skills"):
        assert _is_link_to_skill(tmp_path / rel / SKILL_NAME)
        assert not _leftovers(tmp_path / rel)


def test_relinking_replaces_a_copy_with_a_link(tmp_path: Path) -> None:
    install_skill(tmp_path, targets=["claude"], copy=True)
    (linked,) = install_skill(tmp_path, targets=["claude"])
    link = tmp_path / ".claude/skills" / SKILL_NAME
    assert linked.action == "replaced"
    assert _is_link_to_skill(link)
    (again,) = install_skill(tmp_path, targets=["claude"])
    assert again.action == "unchanged"


def test_foreign_folder_is_refused_before_anything_changes(
    tmp_path: Path,
) -> None:
    mine = tmp_path / ".agents/skills" / SKILL_NAME
    mine.mkdir(parents=True)
    (mine / "SKILL.md").write_text("my own skill", encoding="utf-8")

    with pytest.raises(SkillInstallError, match="--force"):
        install_skill(tmp_path)
    assert not (tmp_path / ".claude").exists()
    assert (mine / "SKILL.md").read_text(encoding="utf-8") == "my own skill"

    results = install_skill(tmp_path, force=True)
    assert [r.action for r in results] == ["linked", "replaced"]
    assert _is_link_to_skill(mine)


def test_foreign_symlink_is_refused(tmp_path: Path) -> None:
    other = tmp_path / "elsewhere"
    other.mkdir()
    link = tmp_path / ".claude/skills" / SKILL_NAME
    link.parent.mkdir(parents=True)
    link.symlink_to(other, target_is_directory=True)
    with pytest.raises(SkillInstallError):
        install_skill(tmp_path, targets=["claude"])
    assert link.resolve() == other


def test_link_from_another_environment_is_relinked(tmp_path: Path) -> None:
    """A link left by an old virtualenv (even a dangling one) is ours to update."""
    old = tmp_path / "old-venv/site-packages/dartwork_mpl/skills" / SKILL_NAME
    link = tmp_path / ".claude/skills" / SKILL_NAME
    link.parent.mkdir(parents=True)
    link.symlink_to(old, target_is_directory=True)
    (result,) = install_skill(tmp_path, targets=["claude"])
    assert result.action == "replaced"
    assert _is_link_to_skill(link)


def test_shared_skills_directory_is_installed_once(tmp_path: Path) -> None:
    """skm-style projects link .claude/skills to .agents/skills."""
    (tmp_path / ".agents/skills").mkdir(parents=True)
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude/skills").symlink_to(
        Path("..") / ".agents" / "skills", target_is_directory=True
    )
    results = install_skill(tmp_path)
    assert [r.action for r in results] == ["linked", "shared"]
    assert _is_link_to_skill(tmp_path / ".agents/skills" / SKILL_NAME)


def test_unknown_target_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="targets"):
        install_skill(tmp_path, targets=["cursor"])


def test_cli_install_path_and_refusal(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["install", "--claude", "--dest", str(tmp_path)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == f"dartwork-mpl {skill_version()} skill: {SKILL}"
    assert out[1].startswith("linked")
    assert any("--copy" in line and "environment" in line for line in out)
    assert _is_link_to_skill(tmp_path / ".claude/skills" / SKILL_NAME)
    assert not (tmp_path / ".agents").exists()

    assert main(["install", "--claude", "--dest", str(tmp_path)]) == 0
    assert capsys.readouterr().out.splitlines()[1].startswith("unchanged")

    assert main(["path"]) == 0
    assert capsys.readouterr().out.strip() == str(SKILL)

    foreign = tmp_path / ".agents/skills" / SKILL_NAME
    foreign.mkdir(parents=True)
    assert main(["install", "--codex", "--dest", str(tmp_path)]) == 1
    assert "--force" in capsys.readouterr().err


def test_symlink_failure_suggests_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        raise OSError("symbolic links are not permitted")

    monkeypatch.setattr(Path, "symlink_to", refuse)
    with pytest.raises(SkillInstallError, match="--copy"):
        install_skill(tmp_path, targets=["claude"])
    assert not _leftovers(tmp_path / ".claude/skills")
