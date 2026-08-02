"""Regenerate ``src/dartwork_mpl/_colors/_typing.py`` from live sources.

The two public ``Literal`` vocabularies (``DartworkColor``,
``DartworkColormap``) fossilized badly when maintained by hand (the
pre-0.5 file had ~98% phantom/missing entries), so they are now
generated from the source-only candidate compiler and bundled vendor assets.
The shared catalog builder derives both vocabularies without importing the
canonical package, reading committed ``_generated.py``, or consulting mutable
matplotlib registries.

- ``DartworkColor`` combines candidate ``dc.*`` names with the stable vendor
  source assets (``oc/tw/md/ad/cu/pr``; ``dm.*`` is not a color namespace).
- ``DartworkColormap`` contains candidate forward and reverse registrations.

Run after any palette/colormap add/remove/rename::

    uv run python scripts/generate_typing.py

CI can compare the in-memory result without touching the tracked file::

    uv run python scripts/generate_typing.py --check

``tests/test_typing_parity.py`` pins the emitted file to both the source
compiler and the public runtime surface, so forgetting to rerun fails CI.
"""

from __future__ import annotations

import argparse
import importlib
import sys
from collections.abc import Callable, Mapping, Sequence
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType
from typing import cast

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET = REPO_ROOT / "src" / "dartwork_mpl" / "_colors" / "_typing.py"
COLORS_DIR = TARGET.parent
_SOURCE_NAMESPACE = "_dartwork_mpl_typing_source"

HEADER = '''"""Static type hints for colors and colormaps.

GENERATED FILE — do not edit by hand. Regenerate with::

    .venv-local/bin/python scripts/generate_typing.py

``tests/test_typing_parity.py`` pins these Literals to the live
registries (named-color mapping / colormap registry), so a palette or
colormap change that skips the regen fails CI.
"""

from typing import Literal

'''


def _source_module_names() -> set[str]:
    """Return the private source root and closure currently in memory."""
    return {
        name
        for name in sys.modules
        if name == _SOURCE_NAMESPACE or name.startswith(f"{_SOURCE_NAMESPACE}.")
    }


def _new_source_namespace() -> ModuleType:
    """Create a private package rooted directly at the color source tree."""
    package = ModuleType(_SOURCE_NAMESPACE)
    search_path = str(COLORS_DIR.resolve())
    specification = ModuleSpec(_SOURCE_NAMESPACE, loader=None, is_package=True)
    specification.submodule_search_locations = [search_path]
    package.__package__ = _SOURCE_NAMESPACE
    package.__path__ = [search_path]
    package.__spec__ = specification
    return package


def _validate_source_modules(catalog: ModuleType) -> None:
    """Reject private source modules loaded from outside ``COLORS_DIR``.

    Parameters
    ----------
    catalog : ModuleType
        Loaded private catalog module.

    Raises
    ------
    RuntimeError
        If the catalog or one of its private dependencies escapes the tree.
    """
    expected_root = COLORS_DIR.resolve()
    for name, module in tuple(sys.modules.items()):
        if not name.startswith(f"{_SOURCE_NAMESPACE}."):
            continue
        source = getattr(module, "__file__", None)
        if source is None:
            raise RuntimeError(
                f"typing source module has no source path: {name}"
            )
        try:
            resolved = Path(source).resolve()
        except (OSError, TypeError) as error:
            raise RuntimeError(
                f"typing source module has invalid path: {name}"
            ) from error
        if not resolved.is_file() or not resolved.is_relative_to(expected_root):
            raise RuntimeError(
                f"typing source module has invalid source path: {name}"
            )

    catalog_source = getattr(catalog, "__file__", None)
    if catalog_source is None or Path(catalog_source).resolve() != (
        expected_root / "_catalog.py"
    ):
        raise RuntimeError("typing source catalog has an unexpected path")


def _load_source_catalog() -> ModuleType:
    """Load ``_catalog`` without initializing canonical ``dartwork_mpl``.

    Returns
    -------
    ModuleType
        Catalog module loaded under the private source namespace.

    Raises
    ------
    RuntimeError
        If the private namespace collides with an unrelated package.
    """
    preexisting = sorted(_source_module_names())
    if preexisting:
        joined = ", ".join(preexisting)
        raise RuntimeError(
            "typing source namespace collision: preexisting alias "
            f"module(s): {joined}"
        )

    package = _new_source_namespace()
    sys.modules[_SOURCE_NAMESPACE] = package

    catalog = importlib.import_module(f"{_SOURCE_NAMESPACE}._catalog")
    _validate_source_modules(catalog)
    return catalog


def _remove_introduced_source_modules(before: frozenset[str]) -> None:
    """Remove only private source modules absent before this invocation.

    Parameters
    ----------
    before : frozenset[str]
        Complete module-name snapshot captured before scoped source loading.
    """
    introduced = _source_module_names().difference(before)
    for name in sorted(
        introduced, key=lambda value: value.count("."), reverse=True
    ):
        sys.modules.pop(name, None)


def _source_typing_payload() -> Mapping[str, Sequence[str]]:
    """Derive typing names from one source-only candidate and vendor assets.

    Returns
    -------
    Mapping[str, Sequence[str]]
        Shared catalog-builder payload for colors and colormaps.
    """
    before = frozenset(sys.modules)
    try:
        catalog = _load_source_catalog()
        compile_candidate = cast(
            Callable[[], object], catalog.compile_candidate_snapshot
        )
        load_vendor_names = cast(
            Callable[[], Sequence[str]], catalog.load_vendor_color_names
        )
        build_payload = cast(
            Callable[[object, Sequence[str]], Mapping[str, Sequence[str]]],
            catalog.build_typing_payload,
        )
        candidate = compile_candidate()
        return build_payload(candidate, load_vendor_names())
    finally:
        _remove_introduced_source_modules(before)


def _literal_block(name: str, entries: list[str]) -> str:
    lines = [f"{name} = Literal["]
    lines.extend(f'    "{entry}",' for entry in entries)
    lines.append("]")
    return "\n".join(lines)


def build() -> str:
    """Return the full generated module source."""
    payload = _source_typing_payload()
    colors = list(payload["color_names"])
    cmaps = list(payload["colormap_names"])
    return (
        HEADER
        + _literal_block("DartworkColor", colors)
        + "\n\n"
        + _literal_block("DartworkColormap", cmaps)
        + "\n"
    )


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare generated bytes without writing the tracked module",
    )
    return parser.parse_args(argv)


def _check(source: str) -> int:
    """Return zero when the tracked module matches ``source`` exactly."""
    if not TARGET.exists():
        print(f"missing generated typing module: {TARGET}", file=sys.stderr)
        return 1
    if TARGET.read_bytes() != source.encode("utf-8"):
        print(
            f"stale generated typing module: {TARGET}; "
            "run `uv run python scripts/generate_typing.py`",
            file=sys.stderr,
        )
        return 1
    print(f"up to date: {TARGET}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Generate the typing module or check it without writing."""
    args = _parse_args(argv)
    source = build()
    if args.check:
        return _check(source)

    encoded = source.encode("utf-8")
    if TARGET.exists() and TARGET.read_bytes() == encoded:
        print(f"unchanged: {TARGET}")
        return 0

    TARGET.write_text(source, encoding="utf-8")
    n_colors = source.count('",')
    print(f"wrote {TARGET} ({n_colors} literal entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
