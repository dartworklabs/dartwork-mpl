#!/usr/bin/env python3
"""Write the deterministic v5/v6 color-system comparison artifacts."""

from __future__ import annotations

import argparse
import builtins
import hashlib
import os
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass, field
from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import MappingProxyType, ModuleType
from typing import NoReturn, Protocol, cast

_REPO_ROOT = Path(__file__).resolve().parents[1]
_COLORS_DIR = (_REPO_ROOT / "src" / "dartwork_mpl" / "_colors").resolve()
_AUDIT_NAMESPACE = "_dartwork_mpl_color_audit"
_AUDIT_SOURCE_STEMS = (
    "_catalog",
    "_cmaps",
    "_comparison",
    "_compatibility_metrics",
    "_conversion",
    "_curated",
    "_cycles",
    "_gamut",
    "_gates",
    "_generate",
    "_recipe",
    "_ssot",
    "_tone",
)
_AUDIT_SOURCE_PATHS: Mapping[str, Path] = MappingProxyType(
    {
        f"{_AUDIT_NAMESPACE}.{stem}": (_COLORS_DIR / f"{stem}.py").resolve()
        for stem in _AUDIT_SOURCE_STEMS
    }
)
_AUDIT_CATALOG_NAME = f"{_AUDIT_NAMESPACE}._catalog"
_AUDIT_COMPARISON_NAME = f"{_AUDIT_NAMESPACE}._comparison"
_STANDARD_IMPORT = builtins.__import__
_AUDIT_BUILTINS_TEMPLATE: Mapping[str, object] = MappingProxyType(
    {**vars(builtins), "__import__": _STANDARD_IMPORT}
)


def _new_audit_builtins() -> dict[str, object]:
    """Return a fresh builtins mapping pinned to this CLI's import callback."""
    if _AUDIT_BUILTINS_TEMPLATE.get("__import__") is not _STANDARD_IMPORT:
        raise RuntimeError("color-audit standard import callback drifted")
    return dict(_AUDIT_BUILTINS_TEMPLATE)


class _ComparisonReport(Protocol):
    """Minimum report surface required by the humble CLI."""

    passed: bool

    def to_json(self) -> str:
        """Serialize the strict machine-readable gate record."""
        ...


class _AuditArgumentParser(argparse.ArgumentParser):
    """Raise an ordinary exception for invalid CLI arguments."""

    def error(self, message: str) -> NoReturn:
        """Map parser failures into the main exit-two boundary."""
        raise ValueError(message)


class _AuditNamespaceLoader(Loader):
    """Mark the private root package created by this CLI instance."""

    def create_module(self, spec: ModuleSpec) -> ModuleType | None:
        """Use the manually allocated private root package."""
        del spec
        return None

    def exec_module(self, module: ModuleType) -> None:
        """Reject import execution because the root is created explicitly."""
        raise RuntimeError(
            f"color-audit namespace execution is forbidden: {module.__name__}"
        )


@dataclass(frozen=True, slots=True)
class _AuditSourceLoader(Loader):
    """Compile one allowlisted private module from captured source bytes."""

    name: str
    source: Path
    source_bytes: bytes = field(repr=False)
    source_sha256: str
    _completed_executions: set[ModuleType] = field(
        default_factory=set, init=False, repr=False, compare=False
    )

    @classmethod
    def from_source(cls, name: str, source: Path) -> _AuditSourceLoader:
        """Capture the exact allowlisted source bytes for one module."""
        resolved = source.resolve(strict=True)
        expected = _AUDIT_SOURCE_PATHS.get(name)
        if expected is None or resolved != expected:
            raise RuntimeError(f"color-audit source is not allowlisted: {name}")
        source_bytes = resolved.read_bytes()
        return cls(
            name=name,
            source=resolved,
            source_bytes=source_bytes,
            source_sha256=hashlib.sha256(source_bytes).hexdigest(),
        )

    def create_module(self, spec: ModuleSpec) -> ModuleType | None:
        """Use the import system's ordinary module allocation."""
        del spec
        return None

    def exec_module(self, module: ModuleType) -> None:
        """Execute only the bytes captured from this loader's exact path."""
        specification = getattr(module, "__spec__", None)
        if not isinstance(specification, ModuleSpec):
            raise RuntimeError(
                f"color-audit module has no valid spec: {self.name}"
            )
        if specification.loader is not self:
            raise RuntimeError(
                f"color-audit module has another loader: {self.name}"
            )
        if module.__name__ != self.name:
            raise RuntimeError(
                f"color-audit loader received another module: {self.name}"
            )
        if getattr(module, "__loader__", None) is not self:
            raise RuntimeError(
                f"color-audit module loader identity drifted: {self.name}"
            )
        source = _resolved_audit_source(
            self.name, getattr(module, "__file__", None)
        )
        if source != self.source:
            raise RuntimeError(
                f"color-audit module has wrong source: {self.name}"
            )
        code = compile(
            self.source_bytes, str(self.source), "exec", dont_inherit=True
        )
        module.__dict__["__builtins__"] = _new_audit_builtins()
        exec(code, module.__dict__)
        self._completed_executions.add(module)


class _AuditSourceFinder(MetaPathFinder):
    """Own every import lookup inside the private audit namespace."""

    def __init__(self) -> None:
        """Start with no source loaders allocated."""
        self._loaders: dict[str, _AuditSourceLoader] = {}

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None,
        target: ModuleType | None = None,
    ) -> ModuleSpec | None:
        """Return an exact-path spec or reject an unknown private alias."""
        prefix = f"{_AUDIT_NAMESPACE}."
        if not fullname.startswith(prefix):
            return None
        source = _AUDIT_SOURCE_PATHS.get(fullname)
        if source is None:
            raise ModuleNotFoundError(
                f"unknown private color-audit module: {fullname}"
            )
        if target is not None:
            raise RuntimeError(
                f"color-audit module reload is forbidden: {fullname}"
            )
        try:
            search_path = tuple(Path(value).resolve() for value in path or ())
        except (OSError, TypeError) as error:
            raise RuntimeError(
                f"color-audit module has invalid search path: {fullname}"
            ) from error
        if search_path != (_COLORS_DIR,):
            raise RuntimeError(
                f"color-audit module has another search path: {fullname}"
            )
        loader = self._loaders.get(fullname)
        if loader is None:
            loader = _AuditSourceLoader.from_source(fullname, source)
            self._loaders[fullname] = loader
        specification = ModuleSpec(fullname, loader, origin=str(source))
        specification.has_location = True
        return specification

    def loader_for(self, name: str) -> _AuditSourceLoader:
        """Return the source loader allocated for one completed import."""
        try:
            return self._loaders[name]
        except KeyError as error:
            raise RuntimeError(
                f"color-audit module bypassed owned loading: {name}"
            ) from error


@dataclass(frozen=True, slots=True)
class _AuditModuleProvenance:
    """Retain the identities and source used for one private module."""

    module: ModuleType
    loader: _AuditNamespaceLoader | _AuditSourceLoader
    specification: ModuleSpec
    source: Path
    source_sha256: str | None


_AUDIT_MODULE_CACHE: Mapping[str, _AuditModuleProvenance] | None = None


def _validate_audit_namespace(package: ModuleType) -> None:
    """Require the root package and its loader to belong to this CLI."""
    path_value = getattr(package, "__path__", None)
    if path_value is None:
        raise RuntimeError("color-audit namespace collision: missing __path__")
    paths = tuple(Path(value).resolve() for value in path_value)
    if paths != (_COLORS_DIR,):
        raise RuntimeError("color-audit namespace collision: another path")
    specification = getattr(package, "__spec__", None)
    loader = getattr(package, "__loader__", None)
    if not isinstance(specification, ModuleSpec):
        raise RuntimeError("color-audit namespace has no valid spec")
    if not isinstance(loader, _AuditNamespaceLoader):
        raise RuntimeError("color-audit namespace has another loader")
    if specification.loader is not loader:
        raise RuntimeError("color-audit namespace loader identity drifted")
    if specification.name != _AUDIT_NAMESPACE:
        raise RuntimeError("color-audit namespace spec name drifted")
    locations = specification.submodule_search_locations
    if locations is None:
        raise RuntimeError("color-audit namespace has no search locations")
    spec_paths = tuple(Path(value).resolve() for value in locations)
    if spec_paths != (_COLORS_DIR,):
        raise RuntimeError("color-audit namespace spec path drifted")


def _new_audit_namespace() -> ModuleType:
    """Create a private source package without canonical parent initialization."""
    package = ModuleType(_AUDIT_NAMESPACE)
    loader = _AuditNamespaceLoader()
    search_path = str(_COLORS_DIR)
    specification = ModuleSpec(_AUDIT_NAMESPACE, loader=loader, is_package=True)
    specification.submodule_search_locations = [search_path]
    package.__loader__ = loader
    package.__package__ = _AUDIT_NAMESPACE
    package.__path__ = [search_path]
    package.__spec__ = specification
    return package


def _resolved_audit_source(name: str, source: object) -> Path:
    """Resolve one module source and reject malformed or escaped paths."""
    try:
        resolved = Path(cast(str | os.PathLike[str], source)).resolve()
    except (OSError, TypeError) as error:
        raise RuntimeError(
            f"color-audit module has invalid source path: {name}"
        ) from error
    expected = _AUDIT_SOURCE_PATHS.get(name)
    if expected is None:
        raise RuntimeError(f"unknown private color-audit module: {name}")
    if resolved != expected:
        raise RuntimeError(f"color-audit module has wrong source: {name}")
    return resolved


def _audit_alias_entries() -> dict[str, object]:
    """Return the current root and prefixed private audit entries."""
    return {
        name: module
        for name, module in sys.modules.items()
        if name == _AUDIT_NAMESPACE or name.startswith(f"{_AUDIT_NAMESPACE}.")
    }


def _typed_audit_modules(
    entries: Mapping[str, object],
) -> dict[str, ModuleType]:
    """Require every cached audit entry to be an actual module object."""
    modules: dict[str, ModuleType] = {}
    for name, module in entries.items():
        if not isinstance(module, ModuleType):
            raise RuntimeError(
                f"color-audit namespace collision: invalid module {name}"
            )
        modules[name] = module
    return modules


def _validate_file_module(
    name: str,
    module: ModuleType,
    loader: _AuditSourceLoader,
    specification: ModuleSpec,
) -> None:
    """Require one alias to retain its owned loader, spec, and source."""
    if module.__name__ != name or module.__package__ != _AUDIT_NAMESPACE:
        raise RuntimeError(f"color-audit module identity drifted: {name}")
    if module.__spec__ is not specification:
        raise RuntimeError(f"color-audit module spec was replaced: {name}")
    if specification.name != name or specification.loader is not loader:
        raise RuntimeError(f"color-audit module spec drifted: {name}")
    if getattr(module, "__loader__", None) is not loader:
        raise RuntimeError(f"color-audit module loader was replaced: {name}")
    source = _resolved_audit_source(name, getattr(module, "__file__", None))
    origin = _resolved_audit_source(name, specification.origin)
    if source != loader.source or origin != loader.source:
        raise RuntimeError(f"color-audit module origin drifted: {name}")
    if hashlib.sha256(loader.source_bytes).hexdigest() != loader.source_sha256:
        raise RuntimeError(f"color-audit loader bytes drifted: {name}")
    current_sha256 = hashlib.sha256(loader.source.read_bytes()).hexdigest()
    if current_sha256 != loader.source_sha256:
        raise RuntimeError(f"color-audit source changed after loading: {name}")
    if module not in loader._completed_executions:
        raise RuntimeError(
            f"color-audit source execution did not complete: {name}"
        )
    private_builtins = module.__dict__.get("__builtins__")
    if (
        not isinstance(private_builtins, dict)
        or _AUDIT_BUILTINS_TEMPLATE.get("__import__") is not _STANDARD_IMPORT
        or private_builtins.get("__import__") is not _STANDARD_IMPORT
    ):
        raise RuntimeError(
            f"color-audit module import callback drifted: {name}"
        )


def _capture_audit_provenance(
    package: ModuleType,
    finder: _AuditSourceFinder,
    modules: Mapping[str, ModuleType],
) -> Mapping[str, _AuditModuleProvenance]:
    """Freeze the exact module closure created by one owned bootstrap."""
    expected_names = {_AUDIT_NAMESPACE, *_AUDIT_SOURCE_PATHS}
    actual_names = set(modules)
    unexpected = sorted(actual_names - expected_names)
    if unexpected:
        raise RuntimeError(
            "color-audit bootstrap loaded unknown modules: "
            + ", ".join(unexpected)
        )
    missing = sorted(expected_names - actual_names)
    if missing:
        raise RuntimeError(
            "color-audit bootstrap missed required modules: "
            + ", ".join(missing)
        )
    _validate_audit_namespace(package)
    package_spec = cast(ModuleSpec, package.__spec__)
    package_loader = cast(_AuditNamespaceLoader, package.__loader__)
    records: dict[str, _AuditModuleProvenance] = {
        _AUDIT_NAMESPACE: _AuditModuleProvenance(
            module=package,
            loader=package_loader,
            specification=package_spec,
            source=_COLORS_DIR,
            source_sha256=None,
        )
    }
    for name in sorted(_AUDIT_SOURCE_PATHS):
        module = modules[name]
        loader = finder.loader_for(name)
        specification = getattr(module, "__spec__", None)
        if not isinstance(specification, ModuleSpec):
            raise RuntimeError(f"color-audit module has no valid spec: {name}")
        _validate_file_module(name, module, loader, specification)
        leaf = name.rpartition(".")[2]
        if getattr(package, leaf, None) is not module:
            raise RuntimeError(f"color-audit package binding drifted: {name}")
        records[name] = _AuditModuleProvenance(
            module=module,
            loader=loader,
            specification=specification,
            source=loader.source,
            source_sha256=loader.source_sha256,
        )
    return MappingProxyType(dict(sorted(records.items())))


def _reuse_audit_modules(
    cached: Mapping[str, _AuditModuleProvenance],
) -> tuple[ModuleType, ModuleType]:
    """Return entries only when every cached provenance identity is intact."""
    entries = _audit_alias_entries()
    cached_names = set(cached)
    current_names = set(entries)
    injected = sorted(current_names - cached_names)
    if injected:
        raise RuntimeError(
            "color-audit cached namespace has injected modules: "
            + ", ".join(injected)
        )
    removed = sorted(cached_names - current_names)
    if removed:
        raise RuntimeError(
            "color-audit cached namespace has removed modules: "
            + ", ".join(removed)
        )
    for name, record in cached.items():
        if entries[name] is not record.module:
            raise RuntimeError(
                f"color-audit cached module was replaced: {name}"
            )

    package_record = cached[_AUDIT_NAMESPACE]
    package = package_record.module
    _validate_audit_namespace(package)
    if package.__spec__ is not package_record.specification:
        raise RuntimeError("color-audit namespace spec was replaced")
    if package.__loader__ is not package_record.loader:
        raise RuntimeError("color-audit namespace loader was replaced")
    for name in sorted(_AUDIT_SOURCE_PATHS):
        record = cached[name]
        if not isinstance(record.loader, _AuditSourceLoader):
            raise RuntimeError(f"color-audit loader has wrong type: {name}")
        _validate_file_module(
            name, record.module, record.loader, record.specification
        )
        leaf = name.rpartition(".")[2]
        if getattr(package, leaf, None) is not record.module:
            raise RuntimeError(f"color-audit package binding drifted: {name}")
    catalog = cached[_AUDIT_CATALOG_NAME].module
    comparison = cached[_AUDIT_COMPARISON_NAME].module
    return catalog, comparison


def _remove_audit_finder(finder: _AuditSourceFinder) -> None:
    """Remove exactly the temporary source finder installed by this CLI."""
    positions = [
        index for index, value in enumerate(sys.meta_path) if value is finder
    ]
    for index in reversed(positions):
        sys.meta_path.pop(index)
    if positions != [0]:
        raise RuntimeError("color-audit source finder identity drifted")


def _discard_owned_audit_namespace() -> None:
    """Clear a failed or compromised bootstrap from module state."""
    global _AUDIT_MODULE_CACHE

    for name in _audit_alias_entries():
        sys.modules.pop(name, None)
    _AUDIT_MODULE_CACHE = None


def _load_audit_modules() -> tuple[ModuleType, ModuleType]:
    """Load construction and comparison modules in an isolated source package."""
    global _AUDIT_MODULE_CACHE

    if _AUDIT_MODULE_CACHE is not None:
        try:
            return _reuse_audit_modules(_AUDIT_MODULE_CACHE)
        except BaseException:
            _discard_owned_audit_namespace()
            raise

    if _audit_alias_entries():
        raise RuntimeError(
            "color-audit namespace collision: preexisting alias modules"
        )

    package = _new_audit_namespace()
    finder = _AuditSourceFinder()
    sys.modules[_AUDIT_NAMESPACE] = package
    try:
        sys.meta_path.insert(0, finder)
        try:
            catalog = _STANDARD_IMPORT(
                _AUDIT_CATALOG_NAME, fromlist=("_audit_entry",)
            )
            comparison = _STANDARD_IMPORT(
                _AUDIT_COMPARISON_NAME, fromlist=("_audit_entry",)
            )
            modules = _typed_audit_modules(_audit_alias_entries())
            if modules.get(_AUDIT_CATALOG_NAME) is not catalog:
                raise RuntimeError("color-audit catalog import was not cached")
            if modules.get(_AUDIT_COMPARISON_NAME) is not comparison:
                raise RuntimeError(
                    "color-audit comparison import was not cached"
                )
            provenance = _capture_audit_provenance(package, finder, modules)
        finally:
            _remove_audit_finder(finder)
        _AUDIT_MODULE_CACHE = provenance
    except BaseException:
        _discard_owned_audit_namespace()
        raise

    return catalog, comparison


def load_v5_snapshot() -> object:
    """Load the frozen snapshot through the isolated audit namespace."""
    catalog, _comparison = _load_audit_modules()
    loader = cast(Callable[[], object], catalog.load_v5_snapshot)
    return loader()


def compile_candidate_snapshot() -> object:
    """Compile live construction sources through the isolated namespace."""
    catalog, _comparison = _load_audit_modules()
    compiler = cast(Callable[[], object], catalog.compile_candidate_snapshot)
    return compiler()


def compare_catalog(baseline: object, candidate: object) -> _ComparisonReport:
    """Compare snapshots through the isolated standard-library report module."""
    _catalog, comparison = _load_audit_modules()
    comparator = cast(
        Callable[[object, object], _ComparisonReport],
        comparison.compare_catalog,
    )
    return comparator(baseline, candidate)


def render_comparison_html(report: _ComparisonReport) -> str:
    """Render standalone HTML through the isolated comparison module."""
    _catalog, comparison = _load_audit_modules()
    renderer = cast(
        Callable[[_ComparisonReport], str], comparison.render_comparison_html
    )
    return renderer(report)


def _parser() -> argparse.ArgumentParser:
    """Build the humble command-line interface."""
    parser = _AuditArgumentParser(
        description=(
            "Compare the frozen v5 color catalog with the live compiler and "
            "write standalone JSON/HTML diagnostics."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_REPO_ROOT / "build" / "color-system-comparison",
        help="artifact directory (default: build/color-system-comparison)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI spelling; artifacts are still written before the exit code",
    )
    return parser


def _atomic_write_text(path: Path, text: str) -> None:
    """Replace one UTF-8 file atomically using a unique sibling temporary."""
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    descriptor_open = True
    try:
        with os.fdopen(
            descriptor, "w", encoding="utf-8", newline="\n"
        ) as stream:
            descriptor_open = False
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        if descriptor_open:
            os.close(descriptor)
        with suppress(FileNotFoundError):
            os.unlink(temporary_name)
        raise


def main(argv: Sequence[str] | None = None) -> int:
    """Generate artifacts and return 0 pass, 1 completed fail, or 2 error."""
    try:
        arguments = _parser().parse_args(argv)
        # Parsing must first select the output directory.  From this point,
        # remove its prior completion marker before any fallible audit or
        # publication work so an ordinary error cannot masquerade as a new
        # completed report.
        with suppress(FileNotFoundError):
            (arguments.output / "report.json").unlink()
        arguments.output.mkdir(parents=True, exist_ok=True)
        baseline = load_v5_snapshot()
        candidate = compile_candidate_snapshot()
        report = compare_catalog(baseline, candidate)
        report_json = report.to_json()
        report_html = render_comparison_html(report)
        _atomic_write_text(arguments.output / "index.html", report_html)
        _atomic_write_text(arguments.output / "report.json", report_json)
        return 0 if report.passed else 1
    except Exception as error:  # noqa: BLE001 - every ordinary failure is exit 2
        print(f"color comparison failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
