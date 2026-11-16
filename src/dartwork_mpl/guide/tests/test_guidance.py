"""Every piece of guidance runs, names only what exists, and lints clean.

The skill and its references are executed as written: each Markdown file's
Python blocks in order in one namespace (a later block may use an earlier
one's figure). Before running, every ``dm.<name>`` the text mentions (in code
or in prose) must exist, and every keyword passed to a ``dm`` callable must
be one it accepts.
"""

from __future__ import annotations

import ast
import inspect
import re

import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm
from dartwork_mpl import guide

SKILL = guide.skill_path()
PAGES = [
    "SKILL.md",
    *sorted(
        f"references/{p.name}" for p in (SKILL / "references").glob("*.md")
    ),
]
BLOCK = re.compile(r"^```python\n(.*?)^```", re.MULTILINE | re.DOTALL)
MENTION = re.compile(r"\bdm((?:\.[A-Za-z_]\w*)+)")


def resolve(path: str) -> object:
    """``dm.style.use`` → the object; a missing name fails the test."""
    obj: object = dm
    for part in path.strip(".").split("."):
        assert hasattr(obj, part), f"dm{path} does not exist"
        obj = getattr(obj, part)
    return obj


def check_calls(source: str, where: str) -> None:
    """Every ``dm.x(...)`` keyword is a parameter of ``dm.x``."""
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        text = ast.unparse(node.func)
        if not re.fullmatch(r"dm(\.\w+)+", text):
            continue
        func = resolve(text.removeprefix("dm"))
        try:
            params = inspect.signature(func).parameters  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
        if any(p.kind is p.VAR_KEYWORD for p in params.values()):
            continue
        for kw in node.keywords:
            assert kw.arg is None or kw.arg in params, (
                f"{where}: {text}() takes no {kw.arg}="
            )


def run(source: str, namespace: dict[str, object], where: str) -> None:
    check_calls(source, where)
    exec(compile(source, where, "exec"), namespace)


@pytest.fixture(autouse=True)
def in_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with dm.style.context("report"):
        yield
    plt.close("all")


@pytest.mark.parametrize("ref", PAGES)
def test_page_names_only_what_exists_and_its_code_runs(ref):
    text = (SKILL / ref).read_text(encoding="utf-8")
    for path in MENTION.findall(text):
        resolve(path)
    namespace: dict[str, object] = {}
    for i, block in enumerate(BLOCK.findall(text)):
        run(block, namespace, f"{ref}#{i}")


def test_the_skill_stays_short_and_routes_to_pages_that_exist():
    skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert len(skill.splitlines()) <= 120
    for name in re.findall(r"`references/([a-z-]+)\.md`", skill):
        assert (SKILL / "references" / f"{name}.md").is_file()


def test_skill_names_the_version_it_was_written_for():
    """``npx skills add`` can fetch a skill of another release; the skill
    states its version so an agent can tell. A release bumps it with
    ``pyproject.toml``."""
    from importlib.metadata import version

    head = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert f"  version: {version('dartwork-mpl')}\n" in head
    assert f"for dartwork-mpl {version('dartwork-mpl')}.**" in head
