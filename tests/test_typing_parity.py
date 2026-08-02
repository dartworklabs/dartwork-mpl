"""Pin the generated typing Literals to the live registries (G5).

The pre-generation hand-maintained ``_typing.py`` drifted to ~98%
phantom/missing entries across two palette waves and the colormap
overhaul. These tests enforce exact equality in both directions; on
failure, rerun ``scripts/generate_typing.py``.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import textwrap
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from typing import get_args

import matplotlib as mpl
import matplotlib.colors as mcolors
import pytest

import dartwork_mpl  # noqa: F401 — registers color namespaces
from dartwork_mpl._colors._typing import DartworkColor, DartworkColormap

_ROOT = Path(__file__).resolve().parents[1]
_GENERATOR = _ROOT / "scripts" / "generate_typing.py"
_TARGET = _ROOT / "src" / "dartwork_mpl" / "_colors" / "_typing.py"
_REGEN = "uv run python scripts/generate_typing.py"

_COLOR_PREFIXES = ("ad.", "cu.", "dc.", "md.", "oc.", "pr.", "tw.")


def _load_generator() -> ModuleType:
    """Load the typing generator without executing its CLI entry point."""
    spec = importlib.util.spec_from_file_location(
        "dartwork_mpl_generate_typing_test", _GENERATOR
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _alias_module_names(namespace: str) -> set[str]:
    """Return the private root and closure names currently loaded."""
    return {
        name
        for name in sys.modules
        if name == namespace or name.startswith(f"{namespace}.")
    }


def _clear_test_alias(namespace: str) -> None:
    """Remove one test-only private namespace after an expected RED failure."""
    for name in _alias_module_names(namespace):
        sys.modules.pop(name, None)


def _fake_catalog(
    module: ModuleType,
    namespace: str,
    failure_stage: str | None = None,
    *,
    add_sourceless_module: bool = False,
) -> ModuleType:
    """Build a minimal catalog double for scoped-loader behavior tests."""
    catalog = ModuleType(f"{namespace}._catalog")
    catalog.__file__ = str(module.COLORS_DIR / "_catalog.py")

    def compile_candidate() -> object:
        """Return a candidate unless candidate compilation is under test."""
        if failure_stage == "candidate":
            raise RuntimeError("expected candidate failure")
        return object()

    def load_vendor_names() -> tuple[str, ...]:
        """Return vendor names unless vendor loading is under test."""
        if failure_stage == "vendor":
            raise RuntimeError("expected vendor failure")
        return ("oc.vendor0",)

    def build_payload(
        candidate: object, vendor_names: Sequence[str]
    ) -> dict[str, tuple[str, ...]]:
        """Return one deterministic payload unless building is under test."""
        assert candidate is not None
        assert tuple(vendor_names) == ("oc.vendor0",)
        if failure_stage == "builder":
            raise RuntimeError("expected builder failure")
        return {
            "color_names": ("dc.source0", *vendor_names),
            "colormap_names": ("dc.source", "dc.source_r"),
        }

    catalog.__dict__["compile_candidate_snapshot"] = compile_candidate
    catalog.__dict__["load_vendor_color_names"] = load_vendor_names
    catalog.__dict__["build_typing_payload"] = build_payload
    if add_sourceless_module:
        poison = ModuleType(f"{namespace}._poison")
        sys.modules[poison.__name__] = poison
    return catalog


def _install_fake_catalog_import(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    namespace: str,
    failure_stage: str | None = None,
    *,
    add_sourceless_module: bool = False,
) -> None:
    """Route the generator's catalog import to a deterministic test double."""

    def import_module(name: str) -> ModuleType:
        """Install the fake closure or raise during the import stage."""
        assert name == f"{namespace}._catalog"
        if failure_stage == "import":
            partial = ModuleType(f"{namespace}._partial")
            partial.__file__ = str(module.COLORS_DIR / "_catalog.py")
            sys.modules[partial.__name__] = partial
            raise RuntimeError("expected import failure")
        catalog = _fake_catalog(
            module,
            namespace,
            failure_stage,
            add_sourceless_module=add_sourceless_module,
        )
        sys.modules[name] = catalog
        return catalog

    monkeypatch.setattr(module.importlib, "import_module", import_module)


def test_colormap_literal_matches_registry_exactly() -> None:
    registered = {n for n in mpl.colormaps if n.startswith("dc.")}
    literal = set(get_args(DartworkColormap))
    assert literal == registered, (
        f"DartworkColormap drift — phantom: {sorted(literal - registered)}, "
        f"missing: {sorted(registered - literal)}. Rerun: {_REGEN}"
    )


@pytest.mark.parametrize("prefix", _COLOR_PREFIXES)
def test_color_literal_matches_registry_per_prefix(prefix: str) -> None:
    mapping = mcolors.get_named_colors_mapping()
    registered = {k for k in mapping if k.startswith(prefix)}
    literal = {n for n in get_args(DartworkColor) if n.startswith(prefix)}
    assert literal == registered, (
        f"DartworkColor drift for {prefix!r} — "
        f"phantom: {sorted(literal - registered)[:5]}, "
        f"missing: {sorted(registered - literal)[:5]}. Rerun: {_REGEN}"
    )


def test_color_literal_has_no_foreign_prefixes() -> None:
    """The Literal must contain only the seven canonical prefixes (the
    dm.* alias namespace is deliberately excluded)."""
    foreign = {
        n for n in get_args(DartworkColor) if not n.startswith(_COLOR_PREFIXES)
    }
    assert not foreign, f"unexpected entries: {sorted(foreign)[:5]}"


def test_generated_typing_source_is_byte_identical() -> None:
    """Pin the tracked module to the generator's in-memory result."""
    module = _load_generator()

    expected = module.build().encode("utf-8")

    assert _TARGET.read_bytes() == expected


def test_generate_typing_check_is_nonwriting() -> None:
    """Make the documented check command compare without touching output."""
    before_bytes = _TARGET.read_bytes()
    before_mtime = _TARGET.stat().st_mtime_ns

    result = subprocess.run(
        [sys.executable, str(_GENERATOR), "--check"],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert _TARGET.read_bytes() == before_bytes
    assert _TARGET.stat().st_mtime_ns == before_mtime


def test_generate_typing_check_fails_closed_when_target_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing authority must fail without creating a replacement."""
    module = _load_generator()
    target = tmp_path / "missing" / "_typing.py"
    monkeypatch.setattr(module, "TARGET", target)

    assert module._check(_TARGET.read_text(encoding="utf-8")) == 1
    assert not target.exists()


def test_generate_typing_check_fails_closed_when_target_is_stale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stale authority must fail while preserving its exact bytes."""
    module = _load_generator()
    target = tmp_path / "_typing.py"
    stale = b"# deliberately stale\n"
    target.write_bytes(stale)
    before_mtime = target.stat().st_mtime_ns
    monkeypatch.setattr(module, "TARGET", target)

    assert module._check(_TARGET.read_text(encoding="utf-8")) == 1
    assert target.read_bytes() == stale
    assert target.stat().st_mtime_ns == before_mtime


def test_check_rejects_target_matching_only_monkeypatched_registries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A mutually stale target/registry pair must not make check green."""
    module = _load_generator()
    stale_colors = ["dc.stale0"]
    stale_cmaps = ["dc.stale", "dc.stale_r"]
    stale_source = (
        module.HEADER
        + module._literal_block("DartworkColor", stale_colors)
        + "\n\n"
        + module._literal_block("DartworkColormap", stale_cmaps)
        + "\n"
    )
    target = tmp_path / "_typing.py"
    target.write_text(stale_source, encoding="utf-8")
    monkeypatch.setattr(module, "TARGET", target)
    monkeypatch.setattr(
        mcolors, "get_named_colors_mapping", lambda: {"dc.stale0": "#000000"}
    )
    monkeypatch.setattr(mpl, "colormaps", tuple(stale_cmaps))

    assert module._check(module.build()) == 1


def test_source_payload_removes_introduced_aliases_after_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A successful scoped derivation must leave no reusable alias closure."""
    module = _load_generator()
    namespace = "_dartwork_mpl_typing_test_success"
    monkeypatch.setattr(module, "_SOURCE_NAMESPACE", namespace)
    _install_fake_catalog_import(module, monkeypatch, namespace)

    try:
        payload = module._source_typing_payload()

        assert payload == {
            "color_names": ("dc.source0", "oc.vendor0"),
            "colormap_names": ("dc.source", "dc.source_r"),
        }
        assert _alias_module_names(namespace) == set()
    finally:
        _clear_test_alias(namespace)


@pytest.mark.parametrize(
    "failure_stage", ("import", "candidate", "vendor", "builder")
)
def test_source_payload_removes_introduced_aliases_after_failure(
    failure_stage: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every source derivation failure must clean its introduced closure."""
    module = _load_generator()
    namespace = f"_dartwork_mpl_typing_test_{failure_stage}"
    monkeypatch.setattr(module, "_SOURCE_NAMESPACE", namespace)
    _install_fake_catalog_import(module, monkeypatch, namespace, failure_stage)

    try:
        with pytest.raises(RuntimeError, match=f"expected {failure_stage}"):
            module._source_typing_payload()

        assert _alias_module_names(namespace) == set()
    finally:
        _clear_test_alias(namespace)


@pytest.mark.parametrize("collision", ("root", "orphan"))
def test_source_payload_rejects_preexisting_alias_closure(
    collision: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fail closed when any private root or orphan closure already exists."""
    module = _load_generator()
    namespace = f"_dartwork_mpl_typing_test_collision_{collision}"
    monkeypatch.setattr(module, "_SOURCE_NAMESPACE", namespace)
    if collision == "root":
        preexisting = module._new_source_namespace()
        preexisting_name = namespace
    else:
        preexisting_name = f"{namespace}._orphan"
        preexisting = ModuleType(preexisting_name)
        preexisting.__file__ = str(module.COLORS_DIR / "_catalog.py")
    sys.modules[preexisting_name] = preexisting

    def unexpected_import(name: str) -> ModuleType:
        """Prove collision detection happens before any source import."""
        raise AssertionError(f"unexpected import after collision: {name}")

    monkeypatch.setattr(module.importlib, "import_module", unexpected_import)

    try:
        with pytest.raises(RuntimeError, match="preexisting"):
            module._source_typing_payload()

        assert sys.modules[preexisting_name] is preexisting
    finally:
        _clear_test_alias(namespace)


def test_source_payload_rejects_and_cleans_sourceless_alias_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject an introduced alias dependency without a valid source path."""
    module = _load_generator()
    namespace = "_dartwork_mpl_typing_test_sourceless"
    monkeypatch.setattr(module, "_SOURCE_NAMESPACE", namespace)
    _install_fake_catalog_import(
        module, monkeypatch, namespace, add_sourceless_module=True
    )

    try:
        with pytest.raises(RuntimeError, match="source path"):
            module._source_typing_payload()

        assert _alias_module_names(namespace) == set()
    finally:
        _clear_test_alias(namespace)


def test_build_uses_isolated_source_candidate_without_registry_mutation(
    tmp_path: Path,
) -> None:
    """Build cold without canonical/generated imports or global registration."""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(_ROOT / "src")
    environment["MPLCONFIGDIR"] = str(tmp_path / "mplconfig")
    runner = tmp_path / "typing_runner.py"
    runner.write_text(
        textwrap.dedent(
            """
            import importlib.abc
            import json
            import runpy
            import sys
            from pathlib import Path

            import matplotlib
            import numpy as np
            from matplotlib.colors import get_named_colors_mapping

            ALIAS_ROOT = "_dartwork_mpl_typing_source"
            alias_requests = set()
            FORBIDDEN_SUFFIXES = (
                "._discrete",
                "._families",
                "._generated",
                "._loader",
                "._register",
                "._semantic",
                "._typing",
            )

            def is_forbidden(fullname):
                return (
                    fullname == "dartwork_mpl"
                    or fullname.startswith("dartwork_mpl.")
                    or (
                        fullname.startswith(ALIAS_ROOT + ".")
                        and fullname.endswith(FORBIDDEN_SUFFIXES)
                    )
                )

            class ImportBlocker(importlib.abc.MetaPathFinder):
                def find_spec(self, fullname, path=None, target=None):
                    if fullname.startswith(ALIAS_ROOT + "."):
                        alias_requests.add(fullname)
                    if is_forbidden(fullname):
                        raise ImportError(
                            f"forbidden typing-generator import: {fullname}"
                        )
                    return None

            def named_registry_payload():
                mapping = get_named_colors_mapping()
                return id(mapping), tuple(sorted(mapping.items()))

            def cmap_registry_payload():
                registry = matplotlib.colormaps
                samples = np.linspace(0.0, 1.0, 9)
                rows = []
                for name in registry:
                    cmap = registry[name]
                    rgba = tuple(
                        tuple(channel for channel in color)
                        for color in cmap(samples, bytes=True).tolist()
                    )
                    rows.append((name, cmap.name, cmap.N, rgba))
                return id(registry), tuple(rows)

            sys.meta_path.insert(0, ImportBlocker())
            before_cmaps = cmap_registry_payload()
            before_named = named_registry_payload()
            namespace = runpy.run_path(
                sys.argv[1], run_name="_typing_generator_cli"
            )
            source = namespace["build"]()
            forbidden_loaded = sorted(
                name for name in sys.modules if is_forbidden(name)
            )
            alias_modules = sorted(
                name
                for name in sys.modules
                if name == ALIAS_ROOT
                or name.startswith(ALIAS_ROOT + ".")
            )
            print(
                json.dumps(
                    {
                        "alias_modules": alias_modules,
                        "alias_requests": sorted(alias_requests),
                        "cmap_registry_unchanged": (
                            before_cmaps == cmap_registry_payload()
                        ),
                        "forbidden_loaded": forbidden_loaded,
                        "matches_target": (
                            Path(sys.argv[2]).read_bytes()
                            == source.encode("utf-8")
                        ),
                        "named_registry_unchanged": (
                            before_named == named_registry_payload()
                        ),
                    },
                    sort_keys=True,
                )
            )
            """
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(runner), str(_GENERATOR), str(_TARGET)],
        cwd=_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    audit = json.loads(result.stdout)
    assert audit["matches_target"] is True
    assert audit["forbidden_loaded"] == []
    assert audit["cmap_registry_unchanged"] is True
    assert audit["named_registry_unchanged"] is True
    assert audit["alias_modules"] == []
    assert "_dartwork_mpl_typing_source._catalog" in audit["alias_requests"]
