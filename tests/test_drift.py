"""Drift detection for auto-generated bundles.

The Sphinx build refreshes ``llms-full.txt`` (concatenated agent
reference) and ``05-templates/_index.json`` (AI-template metadata)
from canonical sources on every run. PRs that touch those upstream
sources but forget to re-run the docs build would silently ship a
stale dump to PyPI / GitHub-raw consumers — these tests catch that.

They re-run the same composition logic in-process and compare against
the committed artifact. If you see a failure here, run::

    uv run sphinx-build -b html docs docs/_build/html

and commit the regenerated ``llms-full.txt`` plus
``src/dartwork_mpl/asset/prompt/05-templates/_index.json``.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_build_hooks():
    """Import ``docs/_ext/build_hooks.py`` without going through Sphinx."""
    spec = importlib.util.spec_from_file_location(
        "build_hooks", REPO_ROOT / "docs" / "_ext" / "build_hooks.py"
    )
    if spec is None or spec.loader is None:
        pytest.skip("docs/_ext/build_hooks.py not importable")
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("build_hooks", mod)
    spec.loader.exec_module(mod)
    return mod


def _compose_llms_full(build_hooks) -> str:
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


def test_llms_full_txt_in_sync() -> None:
    """Repo-root ``llms-full.txt`` must match the live concatenation
    of its canonical sources. A drift means a PR changed an upstream
    file without rerunning the docs build.
    """
    out = REPO_ROOT / "llms-full.txt"
    if not out.exists():
        pytest.skip("llms-full.txt not present in this checkout")
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
            "llms-full.txt is stale. Re-run "
            "`uv run sphinx-build -b html docs docs/_build/html` "
            "and commit the regenerated file.\n"
            f"First divergence at offset {first_diff}.\n"
            f"  expected: ...{expected[ctx_start:ctx_end]!r}...\n"
            f"  actual:   ...{actual[ctx_start:ctx_end]!r}..."
        )


def test_template_index_in_sync() -> None:
    """``05-templates/_index.json`` must mirror the metadata blocks in
    ``docs/examples_source/09_ai_templates/plot_*.py``.
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
    if not out.exists():
        pytest.skip("_index.json not yet generated in this checkout")

    build_hooks = _load_build_hooks()
    template_dir = REPO_ROOT / "docs" / "examples_source" / "09_ai_templates"
    if not template_dir.exists():
        pytest.skip("09_ai_templates source dir missing")

    expected: dict[str, dict[str, object]] = {}
    for path in sorted(template_dir.glob("plot_*.py")):
        text = path.read_text(encoding="utf-8")
        match = build_hooks._TEMPLATE_META_RE.search(text)
        if not match:
            pytest.fail(f"meta block missing in {path.name}")
        meta = build_hooks._parse_template_meta(
            match.group(1), source=str(path.relative_to(REPO_ROOT))
        )
        stem = path.stem
        template_id = stem if stem == "plot_3d" else stem.removeprefix("plot_")
        meta["source_path"] = str(path.relative_to(REPO_ROOT))
        expected[template_id] = meta

    actual = json.loads(out.read_text(encoding="utf-8"))
    if expected != actual:
        missing = set(expected) - set(actual)
        extra = set(actual) - set(expected)
        pytest.fail(
            "_index.json is stale. Re-run "
            "`uv run sphinx-build -b html docs docs/_build/html` "
            "and commit it.\n"
            f"  missing template ids: {sorted(missing)}\n"
            f"  extra template ids:   {sorted(extra)}"
        )
