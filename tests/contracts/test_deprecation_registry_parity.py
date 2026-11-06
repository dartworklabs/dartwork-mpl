"""Removed ``dm`` names have one registry; every consumer derives from it.

``dartwork_mpl._compat`` is the only hand-edited copy of the removed-name
metadata: each name's release and replacement, the codemod's hint groups
and the lint catalog's removed-name rules. Before it, three copies (the
runtime ``__getattr__`` hints, the codemod's ``_MIGRATE_HINTS`` and the
``dm-*-removed`` rules of ``asset/prompt/02-anti-patterns.yaml``) drifted
apart and a substring check held them together.

These tests check the structure, not the wording; the wording of every
consumer is pinned against a record of main by test_removed_names_golden.py.

1. The registry is closed: every name a hint or rule lists is removed, and
   every removed name is in exactly one codemod hint and one lint rule.
2. Each consumer reads it: the runtime error, the codemod's compiled
   catalog and comments, and lint's parsed rules and findings.
3. The shipped catalog is generated at development time: rendering the
   registry over it changes nothing, and no hand-written rule reports a
   removed name.
4. Using the installed package writes no file.
"""

from __future__ import annotations

import dataclasses
import importlib.util
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from types import ModuleType

import pytest

import dartwork_mpl as dm
from dartwork_mpl._compat import (
    _CODEMOD_HINTS,
    _LINT_RULES,
    _REMOVED_NAMES,
    _REMOVED_PREFIXES,
    CodemodForm,
    LintForm,
    missing_attribute,
)
from dartwork_mpl.lint import load_rules, migrate

REPO = Path(__file__).resolve().parents[2]
GENERATOR = REPO / "scripts" / "generate_removed_name_rules.py"
_HEADER = "import dartwork_mpl as dm\n"
_FAMILIES = tuple(f"{prefix}*" for prefix in _REMOVED_PREFIXES)


def _sample(name: str) -> str:
    """An attribute name a registry entry stands for (``FS_*`` -> ``FS_SAMPLE``)."""
    return name[:-1] + "SAMPLE" if name.endswith("*") else name


def _usage(name: str, form: CodemodForm | LintForm) -> str:
    """Source that uses ``name`` the way ``form`` describes."""
    target = _sample(name)
    sources = {
        "reference": f"{_HEADER}value = dm.{target}\n",
        "call": f"{_HEADER}dm.{target}(1)\n",
        "subscript": f"{_HEADER}value = dm.{target}[0]\n",
        "import": f"from dm.{target} import value\n",
        "figsize": f"{_HEADER}import matplotlib.pyplot as plt\n"
        f"fig = plt.figure(figsize=(dm.{target}(9), 3))\n",
    }
    return sources[form]


def _load_generator() -> ModuleType:
    """The development-time catalog generator, loaded from the checkout."""
    if not GENERATOR.is_file():
        pytest.skip("scripts/ is not reachable (installed-package run)")
    spec = importlib.util.spec_from_file_location(
        "_generate_removed_name_rules", GENERATOR
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_registry_lists_only_removed_names() -> None:
    """Hints and rules name removed names or families, without repeats."""
    known = set(_REMOVED_NAMES) | set(_FAMILIES)
    for entry in (*_CODEMOD_HINTS, *_LINT_RULES):
        assert entry.names, entry
        assert set(entry.names) <= known, entry
        assert len(set(entry.names)) == len(entry.names), entry
    ids = [rule.id for rule in _LINT_RULES]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("name", sorted(_REMOVED_NAMES))
def test_removed_name_covered_by_lint_ssot(name: str) -> None:
    """One registry rule lists the name, and lint reports it under that rule."""
    rules = [rule for rule in _LINT_RULES if name in rule.names]
    assert len(rules) == 1, f"{name!r} must be in exactly one _LINT_RULES entry"
    (rule,) = rules
    found = {issue.rule_id for issue in dm.lint_code(_usage(name, rule.form))}
    assert rule.id in found
    if rule.under is not None:
        source = f"{_HEADER}dm.{rule.under}.{name}(1)\n"
        assert rule.id in {issue.rule_id for issue in dm.lint_code(source)}


@pytest.mark.parametrize("name", sorted(_REMOVED_NAMES))
def test_removed_name_covered_by_codemod(name: str) -> None:
    """One registry hint lists the name, and the codemod writes that hint."""
    hints = [hint for hint in _CODEMOD_HINTS if name in hint.names]
    assert len(hints) == 1, (
        f"{name!r} must be in exactly one _CODEMOD_HINTS entry"
    )
    (hint,) = hints
    migrated = dm.migrate_legacy_code(_usage(name, hint.form))
    assert f"# TODO(dm-migrate): {hint.text}\n" in migrated


def test_fs_prefix_family_covered_everywhere() -> None:
    """A prefix family is listed once by the codemod and once by lint, and
    every consumer reports a member of it."""
    for family in _FAMILIES:
        (hint,) = [hint for hint in _CODEMOD_HINTS if family in hint.names]
        (rule,) = [rule for rule in _LINT_RULES if family in rule.names]
        migrated = dm.migrate_legacy_code(_usage(family, hint.form))
        assert f"# TODO(dm-migrate): {hint.text}\n" in migrated
        found = {i.rule_id for i in dm.lint_code(_usage(family, rule.form))}
        assert rule.id in found
        removed = _REMOVED_PREFIXES[family[:-1]]
        with pytest.raises(AttributeError) as error:
            getattr(dm, _sample(family))
        assert removed.removed_in in str(error.value)
        assert removed.replacement in str(error.value)


def test_runtime_error_reads_the_registry() -> None:
    """``dm.<name>`` and ``missing_attribute`` report the registry's fields."""
    for name, removal in _REMOVED_NAMES.items():
        with pytest.raises(AttributeError) as via_root:
            getattr(dm, name)
        with pytest.raises(AttributeError) as direct:
            missing_attribute(name)
        for error in (via_root, direct):
            message = str(error.value)
            assert f"dm.{name} was removed in {removal.removed_in}." in message
            assert f"Use {removal.replacement}." in message


def test_codemod_catalog_is_compiled_from_the_registry() -> None:
    """The codemod's catalog is the registry's hints plus two native hints."""
    catalog = [
        (pattern.pattern, text) for pattern, text in migrate._MIGRATE_HINTS
    ]
    registry = [(hint.pattern, hint.text) for hint in _CODEMOD_HINTS]
    native = [
        (pattern.pattern, text)
        for pattern, text in (
            migrate._FIGSIZE_TUPLE_HINT,
            migrate._TIGHT_LAYOUT_HINT,
        )
    ]
    assert [entry for entry in catalog if entry not in native] == registry
    assert sorted(set(catalog) - set(registry)) == sorted(native)


def test_catalog_rules_are_the_registry_rules() -> None:
    """The shipped catalog parses to the registry's rules, as one block in order."""
    loaded = load_rules()
    ids = [rule.id for rule in loaded]
    first = ids.index(_LINT_RULES[0].id)
    assert ids[first : first + len(_LINT_RULES)] == [r.id for r in _LINT_RULES]
    by_id = {rule.id: rule for rule in loaded}
    for rule in _LINT_RULES:
        parsed = by_id[rule.id]
        assert (parsed.severity, parsed.detector_kind) == (
            rule.severity,
            "regex",
        )
        assert parsed.detector_value == rule.pattern
        assert parsed.message == rule.message
        assert (parsed.why or "").rstrip() == (rule.why or "")
        assert parsed.fix_suggestion == rule.fix_suggestion


def test_catalog_is_generated_from_the_registry() -> None:
    """Rendering the registry over the shipped catalog changes no byte."""
    generator = _load_generator()
    assert generator.expected() == generator.CATALOG.read_text(
        encoding="utf-8"
    ), (
        "02-anti-patterns.yaml differs from _LINT_RULES in "
        "src/dartwork_mpl/_compat.py; edit _LINT_RULES and run "
        "`uv run python scripts/generate_removed_name_rules.py`"
    )


def test_generator_check_fails_on_a_stale_catalog_without_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A hand edit inside the generated block is reported, not overwritten."""
    generator = _load_generator()
    shipped = generator.CATALOG.read_text(encoding="utf-8")
    stale = shipped.replace("was REMOVED in 0.5.4", "was removed in 0.5.4", 1)
    assert stale != shipped
    catalog = tmp_path / "02-anti-patterns.yaml"
    catalog.write_text(stale, encoding="utf-8")
    monkeypatch.setattr(generator, "CATALOG", catalog)
    assert generator.main(["--check"]) == 1
    assert catalog.read_text(encoding="utf-8") == stale
    rules = generator.load_registry(generator.REGISTRY)._LINT_RULES
    assert generator.main([]) == 0
    assert catalog.read_text(encoding="utf-8") == generator.build(stale, rules)
    assert generator.main(["--check"]) == 0


def test_generator_refuses_a_hand_rule_inside_the_block() -> None:
    """The removed-name rules must stay one block for the splice to be exact."""
    generator = _load_generator()
    text = generator.CATALOG.read_text(encoding="utf-8")
    rules = generator.load_registry(generator.REGISTRY)._LINT_RULES
    hand = "  - id: hand-written-probe\n    severity: info\n\n"
    second = text.index(f"  - id: {rules[1].id}\n")
    with pytest.raises(generator.CatalogError, match="hand-written-probe"):
        generator.build(text[:second] + hand + text[second:], rules)


def test_generator_refuses_a_published_pattern_that_parses_differently() -> (
    None
):
    """A rule's published catalog text may differ from its pattern in quoting only."""
    generator = _load_generator()
    rules = generator.load_registry(generator.REGISTRY)._LINT_RULES
    (published,) = [rule for rule in rules if rule.published_pattern]
    wrong = dataclasses.replace(
        published,
        published_pattern=published.published_pattern.replace(
            "cycle|", "cycles|", 1
        ),
    )
    with pytest.raises(generator.CatalogError, match=published.id):
        generator.render_rule(wrong)


def test_only_registry_rules_report_a_removed_name() -> None:
    """No hand-written catalog rule reports a removed name's use."""
    registry = {rule.id for rule in _LINT_RULES}
    for name in (*_REMOVED_NAMES, *_FAMILIES):
        for form in ("reference", "call"):
            found = {i.rule_id for i in dm.lint_code(_usage(name, form))}
            assert found <= registry, (name, form, found - registry)


_WRITE_PROBE = textwrap.dedent(
    """
    import json, os, sys

    writes = []
    flags_mask = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
    events = {
        "os.rename", "os.remove", "os.mkdir", "os.rmdir", "os.symlink",
        "os.link", "os.truncate", "os.chmod", "os.utime", "os.chown",
        "shutil.copyfile", "shutil.copymode", "shutil.copystat",
        "shutil.move", "shutil.rmtree",
    }

    def hook(event, args):
        if event == "open":
            path, mode, flags = args
            if (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
                isinstance(flags, int) and flags & flags_mask
            ):
                writes.append([event, os.fsdecode(path)])
        elif event in events and isinstance(args[0], (str, bytes, os.PathLike)):
            writes.append([event, os.fsdecode(args[0])])

    sys.addaudithook(hook)

    import dartwork_mpl as dm
    from dartwork_mpl import _compat
    from dartwork_mpl.lint import load_rules

    names = [*_compat._REMOVED_NAMES, "FS_SAMPLE"]
    for name in names:
        try:
            getattr(dm, name)
        except AttributeError:
            pass
    source = "import dartwork_mpl as dm\\n" + "".join(
        f"dm.{name}(1)\\n" for name in names
    )
    dm.lint_code(source)
    dm.migrate_legacy_code(source)
    load_rules()
    dm.get_prompt("02-anti-patterns")
    print(json.dumps({"root": os.path.dirname(dm.__file__), "writes": writes}))
    """
)


def test_installed_package_writes_no_file(tmp_path: Path) -> None:
    """Importing the package and using every removed-name consumer writes no
    file: the registry and the catalog are only read.

    An audit hook in a fresh interpreter records every write-mode open and
    every file-system mutation. The only writer allowed is matplotlib's own
    font cache in ``MPLCONFIGDIR``; ``-B`` keeps the interpreter's bytecode
    cache out, since that is not the package writing. Run against an
    installed wheel, the package root is its site-packages directory.
    """
    cache = tmp_path / "mplconfig"
    env = {**os.environ, "MPLCONFIGDIR": str(cache), "MPLBACKEND": "Agg"}
    result = subprocess.run(
        [sys.executable, "-B", "-c", _WRITE_PROBE],
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
        timeout=300,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout.splitlines()[-1])
    assert Path(report["root"]).resolve() == Path(dm.__file__).parent.resolve()
    outside = [
        write
        for write in report["writes"]
        if not Path(write[1]).resolve().is_relative_to(cache.resolve())
    ]
    assert outside == []


def test_agent_doc_bundle_matches_pyproject_force_include() -> None:
    """Every ``agent.AGENT_DOCS`` file reaches ``dartwork_mpl/asset/agent/``
    in the wheel exactly one way: package data under
    ``src/dartwork_mpl/asset/agent/`` or a repo-root file in pyproject's
    wheel ``force-include`` table — so a doc added to one list can't
    silently miss the wheel (PA-2). Skipped on py<3.11 (no stdlib
    tomllib) or when running against an installed wheel (pyproject not
    reachable)."""
    tomllib = pytest.importorskip("tomllib")

    from dartwork_mpl.agent import _FILENAMES, _PACKAGE_DOCS, AGENT_DOCS

    repo = Path(__file__).resolve().parents[2]
    pyproject = repo / "pyproject.toml"
    if not pyproject.is_file():
        pytest.skip("pyproject.toml not reachable (installed-wheel run)")
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    force_include = data["tool"]["hatch"]["build"]["targets"]["wheel"][
        "force-include"
    ]
    prefix = "dartwork_mpl/asset/agent/"
    forced = {
        dest.removeprefix(prefix): src
        for src, dest in force_include.items()
        if dest.startswith(prefix)
    }
    assert all(forced[name] == name for name in forced), forced
    package_dir = repo / "src" / "dartwork_mpl" / "asset" / "agent"
    packaged = {p.name for p in package_dir.iterdir() if p.is_file()}
    assert packaged == set(_PACKAGE_DOCS)
    assert not set(forced) & packaged, "one source per shipped agent doc"
    expected = {_FILENAMES[name] for name in AGENT_DOCS}
    assert set(forced) | packaged == expected, (
        f"wheel bundle {sorted(set(forced) | packaged)} != AGENT_DOCS "
        f"{sorted(expected)}"
    )


def test_value_label_hints_name_the_same_replacements() -> None:
    """The runtime hint and the codemod hint for add_value_labels agree.

    They are separate wordings in the registry; this pins the bar-label one
    so the two cannot name different replacements.
    """
    runtime = _REMOVED_NAMES["add_value_labels"].replacement
    (codemod,) = [
        hint.text for hint in _CODEMOD_HINTS if "add_value_labels" in hint.names
    ]
    for replacement in (
        "dm.label_bars(ax)",
        "dm.annotate_value(ax, x, y, text)",
    ):
        assert replacement in runtime
        assert replacement in codemod
