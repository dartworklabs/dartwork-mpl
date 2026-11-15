"""Drift detection for auto-generated bundles.

The Sphinx build validates ``llms-full.txt`` (concatenated agent
reference) and ``05-templates/_index.json`` (AI-template metadata)
against canonical sources on every run. PRs that touch those upstream
sources but forget to regenerate the authorities would silently ship a
stale dump to PyPI / GitHub-raw consumers — these tests catch that.

They re-run the same composition logic in-process and compare against
the committed artifact. Regenerate a stale authority explicitly, commit it,
and then rerun the non-writing Sphinx check.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import cast

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_build_hooks() -> ModuleType:
    """Import ``docs/_ext/build_hooks.py`` without going through Sphinx."""
    spec = importlib.util.spec_from_file_location(
        "build_hooks", REPO_ROOT / "docs" / "_ext" / "build_hooks.py"
    )
    # A tracked file; an unimportable one is a broken checkout, not a skip.
    assert spec is not None and spec.loader is not None, (
        "docs/_ext/build_hooks.py not importable"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("build_hooks", mod)
    spec.loader.exec_module(mod)
    return mod


def _compose_llms_full(build_hooks: ModuleType) -> str:
    """Re-run the concatenation logic to get the expected bytes."""
    parts: list[str] = [build_hooks._LLMS_FULL_HEADER]
    for header, rel in build_hooks._LLMS_FULL_SOURCES:
        parts.append(header)
        if rel is None:
            continue
        src = REPO_ROOT / rel
        if not src.exists():
            pytest.fail(
                f"llms-full source missing in repo: {rel}; "
                f"build_hooks.py would also fail."
            )
        parts.append(src.read_text(encoding="utf-8"))
    return "".join(parts)


def _write_text(path: Path, text: str) -> None:
    """Write one temporary hook fixture, creating its parents."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_llms_hook_rejects_stale_authority_without_rewriting(
    tmp_path: Path,
) -> None:
    """Make the Sphinx hook a check, not an implicit authority writer."""
    build_hooks = _load_build_hooks()
    repo = tmp_path / "repo"
    docs = repo / "docs"
    docs.mkdir(parents=True)
    app = SimpleNamespace(srcdir=str(docs))
    sources = cast(
        Sequence[tuple[str, str | None]], build_hooks._LLMS_FULL_SOURCES
    )
    for _header, relative in sources:
        if relative is not None:
            _write_text(repo / relative, f"canonical: {relative}\n")
    authority = repo / "llms-full.txt"
    _write_text(authority, "stale authority\n")
    before = authority.read_bytes()

    with pytest.raises(RuntimeError, match=r"llms-full\.txt.*stale"):
        build_hooks.generate_llms_full_txt(app)

    assert authority.read_bytes() == before


def test_template_hook_rejects_stale_authority_without_rewriting(
    tmp_path: Path,
) -> None:
    """Fail a Sphinx build instead of silently updating template metadata."""
    build_hooks = _load_build_hooks()
    repo = tmp_path / "repo"
    docs = repo / "docs"
    docs.mkdir(parents=True)
    app = SimpleNamespace(srcdir=str(docs))
    template = docs / "examples_source/09_ai_templates/plot_line.py"
    _write_text(
        template,
        '"""Example template."""\n'
        "# ai-template-meta-start\n"
        "# use_case: Compare one series\n"
        "# difficulty: beginner\n"
        "# data_shape: x and y sequences\n"
        "# tags: line, comparison\n"
        "# ai-template-meta-end\n",
    )
    authority = repo / "src/dartwork_mpl/asset/prompt/05-templates/_index.json"
    _write_text(authority, "{}\n")
    before = authority.read_bytes()

    with pytest.raises(RuntimeError, match=r"_index\.json.*stale"):
        build_hooks.generate_template_index(app)

    assert authority.read_bytes() == before


def test_template_hook_rejects_missing_source_directory(tmp_path: Path) -> None:
    """A missing canonical template root must not become a silent success."""
    build_hooks = _load_build_hooks()
    repo = tmp_path / "repo"
    docs = repo / "docs"
    docs.mkdir(parents=True)
    app = SimpleNamespace(srcdir=str(docs))

    with pytest.raises(FileNotFoundError, match="source directory is missing"):
        build_hooks.generate_template_index(app)


def test_llms_full_txt_in_sync() -> None:
    """Repo-root ``llms-full.txt`` must match the live concatenation
    of its canonical sources. A drift means a PR changed an upstream
    file without rerunning the docs build.
    """
    out = REPO_ROOT / "llms-full.txt"
    assert out.is_file(), "tracked llms-full.txt is missing from this checkout"
    build_hooks = _load_build_hooks()
    expected = _compose_llms_full(build_hooks)
    actual = out.read_text(encoding="utf-8")
    if expected != actual:
        # Provide an actionable diff hint without dumping 47 KB.
        first_diff = next(
            (
                i
                for i, (a, b) in enumerate(zip(expected, actual, strict=False))
                if a != b
            ),
            min(len(expected), len(actual)),
        )
        ctx_start = max(0, first_diff - 60)
        ctx_end = first_diff + 60
        pytest.fail(
            "llms-full.txt is stale. Regenerate the authority explicitly "
            "and commit it before rebuilding the docs.\n"
            f"First divergence at offset {first_diff}.\n"
            f"  expected: ...{expected[ctx_start:ctx_end]!r}...\n"
            f"  actual:   ...{actual[ctx_start:ctx_end]!r}..."
        )


def test_template_index_in_sync() -> None:
    """``05-templates/_index.json`` must mirror the metadata blocks in
    ``docs/examples_source/09_ai_templates/plot_*.py`` (basic tier) and
    ``docs/examples_source/09_ai_templates_advanced/plot_*_advanced.py``
    (tier 2, registered under the basic tier's ids).
    """
    out = (
        REPO_ROOT
        / "src"
        / "dartwork_mpl"
        / "asset"
        / "prompt"
        / "05-templates"
        / "_index.json"
    )
    assert out.is_file(), "tracked 05-templates/_index.json is missing"

    build_hooks = _load_build_hooks()

    def _scan_tier(scan_dir: Path, tier: str) -> dict[str, dict[str, object]]:
        section: dict[str, dict[str, object]] = {}
        for path in sorted(scan_dir.glob("plot_*.py")):
            text = path.read_text(encoding="utf-8")
            match = build_hooks._TEMPLATE_META_RE.search(text)
            if not match:
                pytest.fail(f"meta block missing in {path.name}")
            meta = build_hooks._parse_template_meta(
                match.group(1), source=str(path.relative_to(REPO_ROOT))
            )
            template_id = build_hooks.template_id_of(path.stem, tier)
            meta["source_path"] = str(path.relative_to(REPO_ROOT))
            meta.setdefault("tier", tier)
            section[template_id] = meta
        return section

    basic_dir = REPO_ROOT / "docs" / "examples_source" / "09_ai_templates"
    assert basic_dir.is_dir(), "tracked 09_ai_templates source dir is missing"
    expected: dict[str, dict[str, object]] = _scan_tier(basic_dir, "basic")

    advanced_dir = (
        REPO_ROOT / "docs" / "examples_source" / "09_ai_templates_advanced"
    )
    if advanced_dir.exists():
        expected["advanced"] = _scan_tier(  # type: ignore[assignment]
            advanced_dir, "advanced"
        )

    actual = json.loads(out.read_text(encoding="utf-8"))
    if expected != actual:
        missing = set(expected) - set(actual)
        extra = set(actual) - set(expected)
        pytest.fail(
            "_index.json is stale. Regenerate the authority explicitly "
            "and commit it before rebuilding the docs.\n"
            f"  missing template ids: {sorted(missing)}\n"
            f"  extra template ids:   {sorted(extra)}"
        )
