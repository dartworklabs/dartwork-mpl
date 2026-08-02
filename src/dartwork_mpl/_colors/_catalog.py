"""Pure immutable color-catalog snapshots for compatibility comparison.

The candidate path deliberately compiles live recipe inputs and derives every
consumer surface without importing the committed generated artifact, runtime
registries, or modules that depend on either of them.
"""

import ast
import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import MappingProxyType
from typing import Literal, TypeAlias, cast

from . import _cmaps, _curated, _cycles, _generate
from ._ssot import load_color_v6_ssot

__all__ = [
    "CatalogSnapshot",
    "build_typing_payload",
    "compile_candidate_snapshot",
    "load_v5_snapshot",
    "load_vendor_color_names",
    "load_vendor_colors",
    "scan_mcp_discovery",
]

FamilyKind: TypeAlias = Literal[
    "sequential", "multi-hue", "diverging", "cyclic", "qualitative"
]
PaletteCoordinate: TypeAlias = tuple[str, int]
HexRows: TypeAlias = Mapping[str, tuple[str, ...]]
NestedHexRows: TypeAlias = Mapping[str, Mapping[str, tuple[str, ...]]]
IndexRows: TypeAlias = Mapping[str, Mapping[str, tuple[int, ...]]]
SemanticCoordinates: TypeAlias = Mapping[str, Mapping[str, PaletteCoordinate]]
SemanticColors: TypeAlias = Mapping[str, Mapping[str, str]]
StringRows: TypeAlias = Mapping[str, tuple[str, ...]]
VendorColors: TypeAlias = Mapping[str, str]
PublicInventory: TypeAlias = tuple[Mapping[str, object], ...]

_PACKAGE_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = Path(__file__).resolve().parents[3]
_COLOR_ASSET_DIR = _PACKAGE_DIR / "asset" / "color"
_MCP_DIR = _PACKAGE_DIR / "mcp"
_DARK_STYLE_PATH = _PACKAGE_DIR / "asset" / "mplstyle" / "theme-dark.mplstyle"
_SEMANTIC_SOURCE_PATH = Path(__file__).with_name("_semantic.py")
_V5_COMPAT_PATH = (
    _REPO_ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "assets"
    / "2026-07-14-oklab-centered-color-system"
    / "color_v5_compatibility.json"
)
_V5_COMPAT_SHA256 = (
    "bc0b9fa8a5d888b60808de48dbdadb1ff25690e435a7bcc44aa63d31ce742818"
)
_COMPATIBILITY_SCHEMA = "dartwork-mpl.color-compatibility/v1"
_CYCLIC_NAMES = ("hue", "halo", "corona")
_MAX_DISCRETE_N: Mapping[FamilyKind, int] = MappingProxyType(
    {
        "sequential": 10,
        "multi-hue": 8,
        "diverging": 9,
        "cyclic": 24,
        "qualitative": 8,
    }
)
_VENDOR_JSON_SOURCES = (
    ("tw", "tailwind_colors.json"),
    ("md", "material_colors.json"),
    ("ad", "ant_colors.json"),
    ("cu", "chakra_colors.json"),
    ("pr", "primer_colors.json"),
)
_VENDOR_PREFIXES = ("oc", *(prefix for prefix, _ in _VENDOR_JSON_SOURCES))
_VENDOR_NAME_PATTERN = re.compile(
    rf"(?:{'|'.join(_VENDOR_PREFIXES)})\.[a-z0-9]+\Z"
)
_VENDOR_HEX_PATTERN = re.compile(r"#[0-9a-f]{6}\Z")
_EXACT_FIELD_TO_MANIFEST_KEY = MappingProxyType(
    {
        "palette": "palette",
        "cycles": "cycles",
        "cmaps_256": "cmaps256",
        "curated_rows": "curated_rows",
        "diverging_canonicals": "diverging_canonicals",
        "semantic_coordinates": "semantic_coordinates",
        "semantic_colors": "semantic_colors",
        "dark_cycle_coordinates": "dark_cycle_coordinates",
        "dark_cycle": "dark_cycle",
        "taxonomy": "taxonomy",
        "registrations": "registrations",
        "typing_literals": "typing_literals",
        "mcp_discovery": "mcp_discovery",
        "public_inventory": "public_inventory",
        "discrete_hex": "discrete_hex",
        "reverse_discrete_hex": "reverse_discrete_hex",
        "multi_hue_discrete_indices": "multi_hue_discrete_indices",
        "vendor_colors": "vendor_colors",
    }
)


def _require_mapping(value: object, label: str) -> Mapping[str, object]:
    """Narrow ``value`` to a string-keyed mapping.

    Parameters
    ----------
    value : object
        Value to validate.
    label : str
        Human-readable field label for errors.

    Returns
    -------
    Mapping[str, object]
        Validated mapping.

    Raises
    ------
    TypeError
        If the value is not a string-keyed mapping.
    """
    if not isinstance(value, Mapping) or not all(
        isinstance(key, str) for key in value
    ):
        raise TypeError(f"{label} must be a string-keyed mapping")
    return cast(Mapping[str, object], value)


def _require_sequence(value: object, label: str) -> Sequence[object]:
    """Narrow ``value`` to a non-string sequence."""
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{label} must be a sequence")
    return cast(Sequence[object], value)


def _freeze_hex_rows(rows: Mapping[str, Sequence[str]]) -> HexRows:
    """Copy hex rows into a deterministic read-only mapping of tuples."""
    frozen: dict[str, tuple[str, ...]] = {}
    for name, row in sorted(rows.items()):
        if not isinstance(name, str) or not all(
            isinstance(value, str) for value in row
        ):
            raise TypeError("hex rows must contain string names and values")
        frozen[name] = tuple(row)
    return MappingProxyType(frozen)


def _freeze_nested_hex_rows(
    rows: Mapping[str, Mapping[str, Sequence[str]]],
) -> NestedHexRows:
    """Copy nested hex rows into deterministic read-only mappings."""
    return MappingProxyType(
        {name: _freeze_hex_rows(forms) for name, forms in sorted(rows.items())}
    )


def _freeze_index_rows(
    rows: Mapping[str, Mapping[str, Sequence[int]]],
) -> IndexRows:
    """Copy nested integer rows into deterministic read-only mappings."""
    frozen: dict[str, Mapping[str, tuple[int, ...]]] = {}
    for name, forms in sorted(rows.items()):
        frozen_forms: dict[str, tuple[int, ...]] = {}
        for size, indices in sorted(forms.items()):
            if not all(
                isinstance(index, int) and not isinstance(index, bool)
                for index in indices
            ):
                raise TypeError("discrete indices must be integers")
            frozen_forms[size] = tuple(indices)
        frozen[name] = MappingProxyType(frozen_forms)
    return MappingProxyType(frozen)


def _coordinate(value: Sequence[object], label: str) -> PaletteCoordinate:
    """Validate and copy one palette coordinate."""
    if (
        len(value) != 2
        or not isinstance(value[0], str)
        or not isinstance(value[1], int)
        or isinstance(value[1], bool)
    ):
        raise TypeError(f"{label} must be a [family, integer index] pair")
    return value[0], value[1]


def _freeze_semantic_coordinates(
    coordinates: Mapping[str, Mapping[str, Sequence[object]]],
) -> SemanticCoordinates:
    """Copy locale semantic coordinates into read-only mappings."""
    frozen: dict[str, Mapping[str, PaletteCoordinate]] = {}
    for locale, tokens in sorted(coordinates.items()):
        frozen[locale] = MappingProxyType(
            {
                token: _coordinate(value, f"{locale}.{token}")
                for token, value in sorted(tokens.items())
            }
        )
    return MappingProxyType(frozen)


def _freeze_semantic_colors(
    colors: Mapping[str, Mapping[str, str]],
) -> SemanticColors:
    """Copy locale semantic colors into deterministic read-only mappings."""
    return MappingProxyType(
        {
            locale: _freeze_string_mapping(tokens)
            for locale, tokens in sorted(colors.items())
        }
    )


def _freeze_coordinates(
    coordinates: Sequence[Sequence[object]],
) -> tuple[PaletteCoordinate, ...]:
    """Copy a coordinate sequence into immutable pairs."""
    return tuple(
        _coordinate(value, f"coordinate {index}")
        for index, value in enumerate(coordinates)
    )


def _freeze_string_rows(rows: Mapping[str, Sequence[str]]) -> StringRows:
    """Copy named string sequences into deterministic read-only mappings."""
    return _freeze_hex_rows(rows)


def _freeze_string_mapping(values: Mapping[str, str]) -> Mapping[str, str]:
    """Copy a string mapping into deterministic read-only storage."""
    if not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in values.items()
    ):
        raise TypeError("mapping keys and values must be strings")
    return MappingProxyType(dict(sorted(values.items())))


def _freeze_integer_mapping(values: Mapping[str, int]) -> Mapping[str, int]:
    """Copy an integer mapping into deterministic read-only storage."""
    if not all(
        isinstance(key, str)
        and isinstance(value, int)
        and not isinstance(value, bool)
        for key, value in values.items()
    ):
        raise TypeError("inventory keys must be strings and values integers")
    return MappingProxyType(dict(sorted(values.items())))


def _freeze_vendor_colors(values: Mapping[str, str]) -> VendorColors:
    """Copy one normalized vendor-token mapping into read-only storage."""
    frozen: dict[str, str] = {}
    for name, value in sorted(values.items()):
        if _VENDOR_NAME_PATTERN.fullmatch(name) is None:
            raise ValueError(f"invalid vendor color name: {name!r}")
        if (
            not isinstance(value, str)
            or _VENDOR_HEX_PATTERN.fullmatch(value) is None
        ):
            raise ValueError(
                f"vendor color {name!r} must be normalized lowercase #rrggbb"
            )
        frozen[name] = value
    return MappingProxyType(frozen)


def _freeze_nested_value(value: object) -> object:
    """Recursively copy JSON-like mappings and sequences into frozen forms."""
    if isinstance(value, Mapping):
        mapping = _require_mapping(value, "nested catalog value")
        return MappingProxyType(
            {
                key: _freeze_nested_value(item)
                for key, item in sorted(mapping.items())
            }
        )
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(_freeze_nested_value(item) for item in value)
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("nested catalog floats must be finite")
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise TypeError(f"unsupported nested catalog value: {type(value).__name__}")


def _freeze_strings(values: Sequence[str], label: str) -> tuple[str, ...]:
    """Copy a sequence after validating that every element is a string."""
    if isinstance(values, (str, bytes)) or not all(
        isinstance(value, str) for value in values
    ):
        raise TypeError(f"{label} must contain only strings")
    return tuple(values)


def _freeze_public_inventory(
    rows: Sequence[Mapping[str, object]],
) -> PublicInventory:
    """Copy public inventory rows while preserving their public order."""
    return tuple(
        cast(Mapping[str, object], _freeze_nested_value(row)) for row in rows
    )


def _thaw(value: object) -> object:
    """Convert nested immutable catalog containers to JSON containers."""
    if isinstance(value, Mapping):
        return {
            str(key): _thaw(item)
            for key, item in sorted(
                value.items(), key=lambda pair: str(pair[0])
            )
        }
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _payload_value(
    payload: Mapping[str, object], key: str, legacy_key: str | None = None
) -> object:
    """Read a required payload value with one accepted manifest alias."""
    if key in payload:
        return payload[key]
    if legacy_key is not None and legacy_key in payload:
        return payload[legacy_key]
    raise KeyError(key)


@dataclass(frozen=True, slots=True)
class CatalogSnapshot:
    """Immutable snapshot of every exact public color-catalog surface.

    All nested containers are copied and frozen during construction. The
    optional provenance maps make the catalog self-contained for later report
    layers without making provenance part of exact candidate equality.
    """

    palette: HexRows
    cycles: HexRows
    cmaps_256: HexRows
    curated_rows: HexRows
    diverging_canonicals: HexRows
    semantic_coordinates: SemanticCoordinates
    semantic_colors: SemanticColors
    dark_cycle_coordinates: tuple[PaletteCoordinate, ...]
    dark_cycle: tuple[str, ...]
    taxonomy: Mapping[str, str]
    registrations: tuple[str, ...]
    typing_literals: StringRows
    mcp_discovery: StringRows
    public_inventory: PublicInventory
    discrete_hex: NestedHexRows
    reverse_discrete_hex: NestedHexRows
    multi_hue_discrete_indices: IndexRows
    vendor_colors: VendorColors
    cmaps_preview_32: HexRows = field(default_factory=dict)
    cmaps_unlocked_preview_32: HexRows = field(default_factory=dict)
    cmaps_unlocked_preview_error: str | None = None
    schema: str = _COMPATIBILITY_SCHEMA
    baseline_commit: str | None = None
    source_hashes: Mapping[str, str] = field(default_factory=dict)
    canonical_hashes: Mapping[str, str] = field(default_factory=dict)
    inventory: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Defensively normalize every retained nested input container."""
        object.__setattr__(self, "palette", _freeze_hex_rows(self.palette))
        object.__setattr__(self, "cycles", _freeze_hex_rows(self.cycles))
        object.__setattr__(self, "cmaps_256", _freeze_hex_rows(self.cmaps_256))
        object.__setattr__(
            self, "curated_rows", _freeze_hex_rows(self.curated_rows)
        )
        object.__setattr__(
            self,
            "diverging_canonicals",
            _freeze_hex_rows(self.diverging_canonicals),
        )
        object.__setattr__(
            self,
            "semantic_coordinates",
            _freeze_semantic_coordinates(
                cast(
                    Mapping[str, Mapping[str, Sequence[object]]],
                    self.semantic_coordinates,
                )
            ),
        )
        object.__setattr__(
            self,
            "semantic_colors",
            _freeze_semantic_colors(self.semantic_colors),
        )
        object.__setattr__(
            self,
            "dark_cycle_coordinates",
            _freeze_coordinates(
                cast(Sequence[Sequence[object]], self.dark_cycle_coordinates)
            ),
        )
        object.__setattr__(
            self, "dark_cycle", _freeze_strings(self.dark_cycle, "dark_cycle")
        )
        object.__setattr__(
            self, "taxonomy", _freeze_string_mapping(self.taxonomy)
        )
        object.__setattr__(
            self,
            "registrations",
            _freeze_strings(self.registrations, "registrations"),
        )
        object.__setattr__(
            self, "typing_literals", _freeze_string_rows(self.typing_literals)
        )
        object.__setattr__(
            self, "mcp_discovery", _freeze_string_rows(self.mcp_discovery)
        )
        object.__setattr__(
            self,
            "public_inventory",
            _freeze_public_inventory(self.public_inventory),
        )
        object.__setattr__(
            self, "discrete_hex", _freeze_nested_hex_rows(self.discrete_hex)
        )
        object.__setattr__(
            self,
            "reverse_discrete_hex",
            _freeze_nested_hex_rows(self.reverse_discrete_hex),
        )
        object.__setattr__(
            self,
            "multi_hue_discrete_indices",
            _freeze_index_rows(self.multi_hue_discrete_indices),
        )
        object.__setattr__(
            self, "vendor_colors", _freeze_vendor_colors(self.vendor_colors)
        )
        object.__setattr__(
            self, "cmaps_preview_32", _freeze_hex_rows(self.cmaps_preview_32)
        )
        object.__setattr__(
            self,
            "cmaps_unlocked_preview_32",
            _freeze_hex_rows(self.cmaps_unlocked_preview_32),
        )
        if self.cmaps_unlocked_preview_error is not None and not isinstance(
            self.cmaps_unlocked_preview_error, str
        ):
            raise TypeError(
                "cmaps_unlocked_preview_error must be a string or None"
            )
        object.__setattr__(
            self, "source_hashes", _freeze_string_mapping(self.source_hashes)
        )
        object.__setattr__(
            self,
            "canonical_hashes",
            _freeze_string_mapping(self.canonical_hashes),
        )
        object.__setattr__(
            self, "inventory", _freeze_integer_mapping(self.inventory)
        )

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "CatalogSnapshot":
        """Construct a snapshot from Task 1 JSON or a thawed snapshot.

        Parameters
        ----------
        payload : Mapping[str, object]
            Decoded Task 1 manifest or :meth:`thaw` result.

        Returns
        -------
        CatalogSnapshot
            Deeply copied immutable snapshot.
        """
        semantic_coordinates = _require_mapping(
            _payload_value(payload, "semantic_coordinates"),
            "semantic_coordinates",
        )
        dark_coordinates = _require_sequence(
            _payload_value(payload, "dark_cycle_coordinates"),
            "dark_cycle_coordinates",
        )
        public_inventory = _require_sequence(
            _payload_value(payload, "public_inventory"), "public_inventory"
        )
        return cls(
            palette=cast(
                HexRows,
                _require_mapping(_payload_value(payload, "palette"), "palette"),
            ),
            cycles=cast(
                HexRows,
                _require_mapping(_payload_value(payload, "cycles"), "cycles"),
            ),
            cmaps_256=cast(
                HexRows,
                _require_mapping(
                    _payload_value(payload, "cmaps_256", "cmaps256"),
                    "cmaps_256",
                ),
            ),
            curated_rows=cast(
                HexRows,
                _require_mapping(
                    _payload_value(payload, "curated_rows"), "curated_rows"
                ),
            ),
            diverging_canonicals=cast(
                HexRows,
                _require_mapping(
                    _payload_value(payload, "diverging_canonicals"),
                    "diverging_canonicals",
                ),
            ),
            semantic_coordinates=cast(
                SemanticCoordinates, semantic_coordinates
            ),
            semantic_colors=cast(
                SemanticColors,
                _require_mapping(
                    _payload_value(payload, "semantic_colors"),
                    "semantic_colors",
                ),
            ),
            dark_cycle_coordinates=cast(
                tuple[PaletteCoordinate, ...], tuple(dark_coordinates)
            ),
            dark_cycle=cast(
                tuple[str, ...],
                tuple(
                    _require_sequence(
                        _payload_value(payload, "dark_cycle"), "dark_cycle"
                    )
                ),
            ),
            taxonomy=cast(
                Mapping[str, str],
                _require_mapping(
                    _payload_value(payload, "taxonomy"), "taxonomy"
                ),
            ),
            registrations=cast(
                tuple[str, ...],
                tuple(
                    _require_sequence(
                        _payload_value(payload, "registrations"),
                        "registrations",
                    )
                ),
            ),
            typing_literals=cast(
                StringRows,
                _require_mapping(
                    _payload_value(payload, "typing_literals"),
                    "typing_literals",
                ),
            ),
            mcp_discovery=cast(
                StringRows,
                _require_mapping(
                    _payload_value(payload, "mcp_discovery"), "mcp_discovery"
                ),
            ),
            public_inventory=cast(PublicInventory, tuple(public_inventory)),
            discrete_hex=cast(
                NestedHexRows,
                _require_mapping(
                    _payload_value(payload, "discrete_hex"), "discrete_hex"
                ),
            ),
            reverse_discrete_hex=cast(
                NestedHexRows,
                _require_mapping(
                    _payload_value(payload, "reverse_discrete_hex"),
                    "reverse_discrete_hex",
                ),
            ),
            multi_hue_discrete_indices=cast(
                IndexRows,
                _require_mapping(
                    _payload_value(payload, "multi_hue_discrete_indices"),
                    "multi_hue_discrete_indices",
                ),
            ),
            vendor_colors=cast(
                VendorColors,
                _require_mapping(
                    _payload_value(payload, "vendor_colors"), "vendor_colors"
                ),
            ),
            cmaps_preview_32=cast(
                HexRows,
                _require_mapping(
                    payload.get("cmaps_preview_32", {}), "cmaps_preview_32"
                ),
            ),
            cmaps_unlocked_preview_32=cast(
                HexRows,
                _require_mapping(
                    payload.get("cmaps_unlocked_preview_32", {}),
                    "cmaps_unlocked_preview_32",
                ),
            ),
            cmaps_unlocked_preview_error=cast(
                str | None, payload.get("cmaps_unlocked_preview_error")
            ),
            schema=cast(str, payload.get("schema", _COMPATIBILITY_SCHEMA)),
            baseline_commit=cast(str | None, payload.get("baseline_commit")),
            source_hashes=cast(
                Mapping[str, str],
                _require_mapping(
                    payload.get("source_hashes", {}), "source_hashes"
                ),
            ),
            canonical_hashes=cast(
                Mapping[str, str],
                _require_mapping(
                    payload.get("canonical_hashes", {}), "canonical_hashes"
                ),
            ),
            inventory=cast(
                Mapping[str, int],
                _require_mapping(payload.get("inventory", {}), "inventory"),
            ),
        )

    def thaw(self) -> dict[str, object]:
        """Return a deterministic deep mutable copy for serialization."""
        return {
            "baseline_commit": self.baseline_commit,
            "canonical_hashes": _thaw(self.canonical_hashes),
            "cmaps_256": _thaw(self.cmaps_256),
            "cmaps_preview_32": _thaw(self.cmaps_preview_32),
            "cmaps_unlocked_preview_error": self.cmaps_unlocked_preview_error,
            "cmaps_unlocked_preview_32": _thaw(self.cmaps_unlocked_preview_32),
            "curated_rows": _thaw(self.curated_rows),
            "cycles": _thaw(self.cycles),
            "dark_cycle": _thaw(self.dark_cycle),
            "dark_cycle_coordinates": _thaw(self.dark_cycle_coordinates),
            "discrete_hex": _thaw(self.discrete_hex),
            "diverging_canonicals": _thaw(self.diverging_canonicals),
            "inventory": _thaw(self.inventory),
            "mcp_discovery": _thaw(self.mcp_discovery),
            "multi_hue_discrete_indices": _thaw(
                self.multi_hue_discrete_indices
            ),
            "palette": _thaw(self.palette),
            "public_inventory": _thaw(self.public_inventory),
            "registrations": _thaw(self.registrations),
            "reverse_discrete_hex": _thaw(self.reverse_discrete_hex),
            "schema": self.schema,
            "semantic_colors": _thaw(self.semantic_colors),
            "semantic_coordinates": _thaw(self.semantic_coordinates),
            "source_hashes": _thaw(self.source_hashes),
            "taxonomy": _thaw(self.taxonomy),
            "typing_literals": _thaw(self.typing_literals),
            "vendor_colors": _thaw(self.vendor_colors),
        }

    def exact_payload(self) -> dict[str, object]:
        """Return only the 18 normalized exact compatibility surfaces.

        Returns
        -------
        dict[str, object]
            Deep mutable JSON-compatible values keyed by Python field name.
            Provenance and candidate-only preview LUTs are intentionally
            excluded.
        """
        return {
            field_name: _thaw(getattr(self, field_name))
            for field_name in _EXACT_FIELD_TO_MANIFEST_KEY
        }

    def to_json(self) -> str:
        """Serialize the snapshot to stable UTF-8-compatible JSON text."""
        return (
            json.dumps(
                self.thaw(),
                ensure_ascii=False,
                allow_nan=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )


def load_v5_snapshot() -> CatalogSnapshot:
    """Load the immutable Task 1 snapshot after checking its raw SHA-256.

    Returns
    -------
    CatalogSnapshot
        Frozen baseline snapshot. Its 32-stop preview mapping is empty.

    Raises
    ------
    RuntimeError
        If the raw fixture bytes no longer match the accepted Task 1 hash.
    """
    raw = _V5_COMPAT_PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != _V5_COMPAT_SHA256:
        raise RuntimeError(
            "v5 compatibility manifest SHA-256 mismatch: "
            f"expected {_V5_COMPAT_SHA256}, got {digest}"
        )
    decoded: object = json.loads(raw)
    return CatalogSnapshot.from_payload(
        _require_mapping(decoded, "v5 compatibility manifest")
    )


def _palette_coordinate(node: ast.AST) -> PaletteCoordinate:
    """Parse one narrowly allowed ``PALETTE[family][index]`` expression."""
    if not isinstance(node, ast.Subscript) or not isinstance(
        node.value, ast.Subscript
    ):
        raise ValueError("semantic value must index PALETTE twice")
    family_lookup = node.value
    if not isinstance(family_lookup.value, ast.Name) or (
        family_lookup.value.id != "PALETTE"
    ):
        raise ValueError("semantic value must read PALETTE")
    family = family_lookup.slice
    index = node.slice
    if (
        not isinstance(family, ast.Constant)
        or not isinstance(family.value, str)
        or not isinstance(index, ast.Constant)
        or not isinstance(index.value, int)
        or isinstance(index.value, bool)
    ):
        raise ValueError("semantic palette coordinate must be literal")
    return family.value, index.value


def _coordinate_dict(node: ast.AST) -> dict[str, PaletteCoordinate]:
    """Parse a semantic token dictionary from source AST."""
    if not isinstance(node, ast.Dict):
        raise ValueError("semantic declaration must be a dictionary")
    result: dict[str, PaletteCoordinate] = {}
    for key_node, value_node in zip(node.keys, node.values, strict=True):
        if not isinstance(key_node, ast.Constant) or not isinstance(
            key_node.value, str
        ):
            raise ValueError("semantic token name must be a string literal")
        result[key_node.value] = _palette_coordinate(value_node)
    return result


def _semantic_declarations() -> dict[str, dict[str, PaletteCoordinate]]:
    """AST-parse live semantic declarations without importing the module."""
    tree = ast.parse(_SEMANTIC_SOURCE_PATH.read_text(encoding="utf-8"))
    assignments: dict[str, ast.AST] = {}
    for node in tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.value is not None
            and node.target.id in {"_MAPS", "_COMMON"}
        ):
            assignments[node.target.id] = node.value
    if set(assignments) != {"_MAPS", "_COMMON"}:
        raise ValueError("semantic declarations are incomplete")

    common = _coordinate_dict(assignments["_COMMON"])
    maps_node = assignments["_MAPS"]
    if not isinstance(maps_node, ast.Dict):
        raise ValueError("_MAPS must be a dictionary")
    locales: dict[str, dict[str, PaletteCoordinate]] = {}
    for key_node, value_node in zip(
        maps_node.keys, maps_node.values, strict=True
    ):
        if not isinstance(key_node, ast.Constant) or not isinstance(
            key_node.value, str
        ):
            raise ValueError("semantic locale must be a string literal")
        locales[key_node.value] = {**common, **_coordinate_dict(value_node)}
    return locales


def _resolve_semantic(
    palette: Mapping[str, Sequence[str]],
) -> tuple[dict[str, dict[str, PaletteCoordinate]], dict[str, dict[str, str]]]:
    """Resolve live semantic coordinates against a candidate palette."""
    coordinates = _semantic_declarations()
    colors = {
        locale: {
            token: palette[family][index]
            for token, (family, index) in sorted(tokens.items())
        }
        for locale, tokens in sorted(coordinates.items())
    }
    return coordinates, colors


def _resolve_dark_cycle(
    palette: Mapping[str, Sequence[str]],
) -> tuple[list[PaletteCoordinate], list[str]]:
    """Parse the dark mplstyle cycle and resolve its candidate hex values."""
    source = _DARK_STYLE_PATH.read_text(encoding="utf-8")
    declaration = re.search(
        r"axes\.prop_cycle:\s*cycler\('color',\s*\[([^\]]+)\]", source
    )
    if declaration is None:
        raise ValueError("theme-dark cycle declaration not found")
    tokens = re.findall(r"'([^']+)'", declaration.group(1))
    coordinates: list[PaletteCoordinate] = []
    colors: list[str] = []
    for token in tokens:
        match = re.fullmatch(r"dc\.([a-z_]+)(\d+)", token)
        if match is None:
            raise ValueError(f"unexpected dark-cycle token: {token}")
        family, index_text = match.groups()
        coordinate = family, int(index_text)
        coordinates.append(coordinate)
        colors.append(palette[coordinate[0]][coordinate[1]])
    return coordinates, colors


def _normalize_vendor_hex(value: object, label: str) -> str:
    """Normalize one source hex literal to lowercase ``#rrggbb``."""
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a string")
    normalized = value.strip().lower()
    if not normalized.startswith("#"):
        normalized = f"#{normalized}"
    if _VENDOR_HEX_PATTERN.fullmatch(normalized) is None:
        raise ValueError(f"{label} must be a six-digit RGB hex value")
    return normalized


def _insert_vendor_color(
    colors: dict[str, str], name: str, value: object, label: str
) -> None:
    """Validate and insert one vendor color without overwriting collisions."""
    if _VENDOR_NAME_PATTERN.fullmatch(name) is None:
        raise ValueError(f"invalid vendor color name from {label}: {name!r}")
    if name in colors:
        raise ValueError(f"duplicate vendor color {name!r} in {label}")
    colors[name] = _normalize_vendor_hex(value, f"{label}.{name}")


def _reject_duplicate_json_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    """Decode one JSON object while rejecting repeated literal keys."""
    decoded: dict[str, object] = {}
    for key, value in pairs:
        if key in decoded:
            raise ValueError(f"duplicate JSON key {key!r}")
        decoded[key] = value
    return decoded


def _vendor_json_colors(path: Path, prefix: str) -> dict[str, str]:
    """Parse normalized token values from one bundled JSON palette asset."""
    if prefix not in _VENDOR_PREFIXES or prefix == "oc":
        raise ValueError(f"unsupported JSON vendor prefix: {prefix!r}")
    decoded: object = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_json_keys,
    )
    families = _require_mapping(decoded, path.name)
    colors: dict[str, str] = {}
    for family, shades_value in families.items():
        shades = _require_sequence(shades_value, f"{path.name}.{family}")
        normalized_family = family.lower().replace(" ", "")
        for pair_value in shades:
            pair = _require_sequence(pair_value, f"{path.name}.{family} shade")
            if (
                len(pair) != 2
                or not isinstance(pair[0], (str, int))
                or isinstance(pair[0], bool)
            ):
                raise TypeError(f"invalid shade entry in {path.name}")
            name = f"{prefix}.{normalized_family}{pair[0]}"
            _insert_vendor_color(colors, name, pair[1], path.name)
    return colors


def _open_color_colors(path: Path) -> dict[str, str]:
    """Parse normalized Open Color token values from its text source."""
    colors: dict[str, str] = {}
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, separator, value = stripped.partition(":")
        if not separator or not key.strip():
            raise ValueError(f"invalid OpenColor source line {line_number}")
        _insert_vendor_color(
            colors, f"oc.{key.strip()}", value, f"{path.name}:{line_number}"
        )
    return colors


def _merge_vendor_colors(
    target: dict[str, str], source: Mapping[str, str], label: str
) -> None:
    """Merge one parsed vendor mapping without allowing token collisions."""
    for name, value in source.items():
        if name in target:
            raise ValueError(f"duplicate vendor color {name!r} from {label}")
        target[name] = value


def load_vendor_colors() -> VendorColors:
    """Parse all 892 third-party token values from bundled source assets."""
    colors = _open_color_colors(_COLOR_ASSET_DIR / "opencolor.txt")
    for prefix, filename in _VENDOR_JSON_SOURCES:
        _merge_vendor_colors(
            colors,
            _vendor_json_colors(_COLOR_ASSET_DIR / filename, prefix),
            filename,
        )
    if len(colors) != 892:
        raise ValueError(
            f"vendor color inventory must contain 892 unique entries; "
            f"got {len(colors)}"
        )
    return _freeze_vendor_colors(colors)


def load_vendor_color_names() -> tuple[str, ...]:
    """Derive all third-party color names from value-preserving parsing."""
    return tuple(load_vendor_colors())


class _McpDecoratorVisitor(ast.NodeVisitor):
    """Collect MCP decorator identities in source declaration order."""

    def __init__(self) -> None:
        self.tool_names: list[str] = []
        self.resource_uris: list[str] = []
        self.prompt_names: list[str] = []

    @staticmethod
    def _public_function_name(
        decorator: ast.Call, fallback: str, kind: str
    ) -> str:
        """Resolve FastMCP's literal positional/keyword public name."""
        if len(decorator.args) > 1:
            raise ValueError(f"MCP {kind} name must be literal and unambiguous")

        positional: str | None = None
        if decorator.args:
            argument = decorator.args[0]
            if not isinstance(argument, ast.Constant) or not (
                argument.value is None or isinstance(argument.value, str)
            ):
                raise ValueError(
                    f"MCP {kind} name must be literal string or None"
                )
            positional = argument.value

        name_keywords = [
            keyword for keyword in decorator.keywords if keyword.arg == "name"
        ]
        if any(keyword.arg is None for keyword in decorator.keywords):
            raise ValueError(
                f"MCP {kind} name must be literal; **kwargs are ambiguous"
            )
        if len(name_keywords) > 1:
            raise ValueError(f"MCP {kind} name must be literal and unambiguous")

        keyword_name: str | None = None
        if name_keywords:
            value = name_keywords[0].value
            if not isinstance(value, ast.Constant) or not (
                value.value is None or isinstance(value.value, str)
            ):
                raise ValueError(
                    f"MCP {kind} name must be literal string or None"
                )
            keyword_name = value.value

        if positional is not None and keyword_name is not None:
            raise ValueError(f"MCP {kind} name must be literal and unambiguous")
        if keyword_name is not None:
            return keyword_name
        if positional is not None:
            return positional
        return fallback

    def _visit_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        """Collect supported decorators from one function definition."""
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(
                decorator.func, ast.Attribute
            ):
                continue
            owner = decorator.func.value
            if not isinstance(owner, ast.Name) or owner.id != "mcp":
                continue
            if decorator.func.attr == "tool":
                self.tool_names.append(
                    self._public_function_name(decorator, node.name, "tool")
                )
            elif decorator.func.attr == "prompt":
                self.prompt_names.append(
                    self._public_function_name(decorator, node.name, "prompt")
                )
            elif decorator.func.attr == "resource":
                if not decorator.args or not isinstance(
                    decorator.args[0], ast.Constant
                ):
                    raise ValueError("MCP resource URI must be literal")
                uri = decorator.args[0].value
                if not isinstance(uri, str):
                    raise ValueError("MCP resource URI must be a string")
                self.resource_uris.append(uri)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit a synchronous function definition."""
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit an asynchronous function definition."""
        self._visit_function(node)


def _scan_mcp_source(path: Path) -> _McpDecoratorVisitor:
    """Scan one MCP module from source without importing it."""
    visitor = _McpDecoratorVisitor()
    visitor.visit(ast.parse(path.read_text(encoding="utf-8")))
    return visitor


def scan_mcp_discovery() -> dict[str, tuple[str, ...]]:
    """Return exact MCP discovery identity from decorator source AST."""
    tools = _scan_mcp_source(_MCP_DIR / "tools.py")
    resources = _scan_mcp_source(_MCP_DIR / "resources.py")
    prompts = _scan_mcp_source(_MCP_DIR / "prompts.py")
    return {
        "tool_names": tuple(tools.tool_names),
        "resource_uris": tuple(
            uri for uri in resources.resource_uris if "{" not in uri
        ),
        "resource_template_uris": tuple(
            uri for uri in resources.resource_uris if "{" in uri
        ),
        "prompt_names": tuple(prompts.prompt_names),
    }


def _derive_taxonomy(
    palette: Mapping[str, Sequence[str]],
    cmaps_256: Mapping[str, Sequence[str]],
    cycles: Mapping[str, Sequence[str]],
) -> tuple[dict[str, FamilyKind], list[dict[str, object]]]:
    """Derive taxonomy and ordered public inventory from candidate names."""
    palette_names = set(palette)
    cmap_names = set(cmaps_256)
    if not palette_names <= cmap_names:
        missing = sorted(palette_names - cmap_names)
        raise ValueError(
            f"candidate colormaps missing palette names: {missing}"
        )
    if not set(_CYCLIC_NAMES) <= cmap_names:
        missing = sorted(set(_CYCLIC_NAMES) - cmap_names)
        raise ValueError(f"candidate colormaps missing cyclic names: {missing}")

    sequential = tuple(sorted(palette_names))
    diverging = tuple(sorted(name for name in cmap_names if "_" in name))
    excluded = palette_names | set(diverging) | set(_CYCLIC_NAMES)
    multi_hue = tuple(sorted(cmap_names - excluded))
    qualitative = tuple(_curated.CURATED_QUALITATIVE_ORDER) + tuple(
        sorted(cycles)
    )
    groups: tuple[tuple[FamilyKind, tuple[str, ...], bool, int | None], ...] = (
        ("sequential", sequential, True, 10),
        ("multi-hue", multi_hue, True, None),
        ("diverging", diverging, True, 8),
        ("cyclic", _CYCLIC_NAMES, True, None),
        ("qualitative", qualitative, False, 8),
    )
    flattened = [
        name for _kind, names, _continuous, _size in groups for name in names
    ]
    if len(flattened) != len(set(flattened)):
        raise ValueError("candidate family categories overlap")

    taxonomy: dict[str, FamilyKind] = {}
    inventory: list[dict[str, object]] = []
    for kind, names, continuous, discrete_size in groups:
        for name in names:
            taxonomy[name] = kind
            inventory.append(
                {
                    "name": name,
                    "kind": kind,
                    "continuous": continuous,
                    "discrete_size": discrete_size,
                }
            )
    return taxonomy, inventory


def _derive_registrations(
    cmaps_256: Mapping[str, Sequence[str]], cycles: Mapping[str, Sequence[str]]
) -> tuple[str, ...]:
    """Derive all continuous/reverse and qualitative forward cmap names."""
    names = {
        registration
        for name in cmaps_256
        for registration in (f"dc.{name}", f"dc.{name}_r")
    }
    names.update(f"dc.{name}" for name in _curated.CURATED_QUALITATIVE_ORDER)
    names.update(f"dc.{name}" for name in cycles)
    return tuple(sorted(names))


def _derive_diverging_canonicals(
    taxonomy: Mapping[str, FamilyKind], palette: Mapping[str, Sequence[str]]
) -> dict[str, tuple[str, ...]]:
    """Derive curated and palette-coordinate diverging canonical rows."""
    rows: dict[str, tuple[str, ...]] = {}
    for name, kind in sorted(taxonomy.items()):
        if kind != "diverging":
            continue
        if name in _curated.CURATED_DIVERGING_ORDER:
            rows[name] = tuple(_curated.CURATED[name])
            continue
        low, high = name.split("_", maxsplit=1)
        rows[name] = tuple(
            palette[low][index] for index in (7, 5, 3, 1)
        ) + tuple(palette[high][index] for index in (1, 3, 5, 7))
    return rows


def _sequential_discrete(row: Sequence[str], n: int) -> list[str]:
    """Apply the shipped sequential ladder sampling policy."""
    if n == 10:
        return list(row)
    if n == 9:
        return list(row[:9])
    if n == 1:
        return [row[5]]
    indices = [math.floor(1 + index * 7 / (n - 1) + 0.5) for index in range(n)]
    return [row[index] for index in indices]


def _diverging_discrete(
    canonical: Sequence[str], cmap: Sequence[str], n: int
) -> list[str]:
    """Apply the shipped diverging canonical/center sampling policy."""
    if n % 2 == 0:
        half = n // 2
        indices = [*range(half), *range(8 - half, 8)]
        return [canonical[index] for index in indices]
    half = (n - 1) // 2
    return [*canonical[:half], cmap[128], *canonical[8 - half :]]


def _derive_discrete(
    taxonomy: Mapping[str, FamilyKind],
    palette: Mapping[str, Sequence[str]],
    cycles: Mapping[str, Sequence[str]],
    cmaps_256: Mapping[str, Sequence[str]],
    diverging_canonicals: Mapping[str, Sequence[str]],
    frozen_multi_hue_indices: IndexRows,
) -> tuple[
    dict[str, dict[str, list[str]]],
    dict[str, dict[str, list[str]]],
    dict[str, dict[str, tuple[int, ...]]],
]:
    """Derive all 547 forward/reverse forms from candidate values."""
    discrete: dict[str, dict[str, list[str]]] = {}
    reverse_discrete: dict[str, dict[str, list[str]]] = {}
    multi_hue_indices: dict[str, dict[str, tuple[int, ...]]] = {}
    for name, kind in sorted(taxonomy.items()):
        forms: dict[str, list[str]] = {}
        if kind == "multi-hue":
            if name not in frozen_multi_hue_indices:
                raise ValueError(f"missing frozen multi-hue indices for {name}")
            multi_hue_indices[name] = {
                size: tuple(indices)
                for size, indices in frozen_multi_hue_indices[name].items()
            }
        for n in range(1, _MAX_DISCRETE_N[kind] + 1):
            if kind == "sequential":
                colors = _sequential_discrete(palette[name], n)
            elif kind == "diverging":
                colors = _diverging_discrete(
                    diverging_canonicals[name], cmaps_256[name], n
                )
            elif kind == "multi-hue":
                colors = [
                    cmaps_256[name][index]
                    for index in multi_hue_indices[name][str(n)]
                ]
            elif kind == "cyclic":
                row = cmaps_256[name]
                colors = [
                    row[min(int(index * len(row) / n), len(row) - 1)]
                    for index in range(n)
                ]
            else:
                qualitative_row = cycles.get(name)
                if qualitative_row is None:
                    qualitative_row = _curated.CURATED.get(name)
                if qualitative_row is None:
                    raise ValueError(f"missing qualitative row for {name}")
                colors = list(qualitative_row[:n])
            forms[str(n)] = colors
        discrete[name] = forms
        reverse_discrete[name] = {
            size: list(reversed(colors)) for size, colors in forms.items()
        }
    return discrete, reverse_discrete, multi_hue_indices


def build_typing_payload(
    candidate: CatalogSnapshot, vendor_names: Sequence[str]
) -> dict[str, tuple[str, ...]]:
    """Build typed color/cmap names from candidate data and vendor names.

    Parameters
    ----------
    candidate : CatalogSnapshot
        Candidate values whose name surfaces should be typed.
    vendor_names : Sequence[str]
        Names parsed from bundled third-party source assets.

    Returns
    -------
    dict[str, tuple[str, ...]]
        Sorted color and colormap literal vocabularies.
    """
    color_names = set(vendor_names)
    color_names.update(
        f"dc.{family}{index}"
        for family, row in candidate.palette.items()
        for index in range(len(row))
    )
    color_names.update(
        f"dc.{name}{index}"
        for name, row in candidate.curated_rows.items()
        for index in range(len(row))
    )
    color_names.update(
        f"dc.{name}{index}"
        for name, row in candidate.diverging_canonicals.items()
        for index in range(len(row))
    )
    color_names.update(
        token
        for locale in candidate.semantic_coordinates.values()
        for token in locale
    )
    return {
        "color_names": tuple(sorted(color_names)),
        "colormap_names": tuple(sorted(candidate.registrations)),
    }


def _canonical_digest(value: object) -> str:
    """Return the Task 1 canonical compact-JSON SHA-256 digest."""
    canonical = json.dumps(
        _thaw(value),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _candidate_canonical_hashes(candidate: CatalogSnapshot) -> dict[str, str]:
    """Hash every exact candidate surface with Task 1 canonical rules."""
    return {
        manifest_key: _canonical_digest(getattr(candidate, field_name))
        for field_name, manifest_key in _EXACT_FIELD_TO_MANIFEST_KEY.items()
    }


def _candidate_inventory(candidate: CatalogSnapshot) -> dict[str, int]:
    """Summarize compatibility inventory from candidate surfaces."""
    color_names = candidate.typing_literals["color_names"]
    return {
        "palette_positions": sum(
            len(row) for row in candidate.palette.values()
        ),
        "cycle_positions": sum(len(row) for row in candidate.cycles.values()),
        "cmap_positions": sum(len(row) for row in candidate.cmaps_256.values()),
        "qualitative_families": sum(
            kind == "qualitative" for kind in candidate.taxonomy.values()
        ),
        "families": len(candidate.taxonomy),
        "registered_colormaps": len(candidate.registrations),
        "dc_tokens": sum(name.startswith("dc.") for name in color_names),
        "vendor_tokens": sum(
            not name.startswith("dc.") for name in color_names
        ),
    }


def _candidate_source_hashes() -> dict[str, str]:
    """Hash live compiler and declarative sources used by candidate assembly."""
    paths = {
        "src/dartwork_mpl/_colors/_catalog.py": Path(__file__),
        "src/dartwork_mpl/_colors/_cmaps.py": Path(_cmaps.__file__),
        "src/dartwork_mpl/_colors/_curated.py": Path(_curated.__file__),
        "src/dartwork_mpl/_colors/_cycles.py": Path(_cycles.__file__),
        "src/dartwork_mpl/_colors/_generate.py": Path(_generate.__file__),
        "src/dartwork_mpl/_colors/_gamut.py": Path(__file__).with_name(
            "_gamut.py"
        ),
        "src/dartwork_mpl/_colors/_color.py": Path(__file__).with_name(
            "_color.py"
        ),
        "src/dartwork_mpl/_colors/_conversion.py": Path(__file__).with_name(
            "_conversion.py"
        ),
        "src/dartwork_mpl/_colors/_metrics.py": Path(__file__).with_name(
            "_metrics.py"
        ),
        "src/dartwork_mpl/_colors/_recipe.py": Path(__file__).with_name(
            "_recipe.py"
        ),
        "src/dartwork_mpl/_colors/_semantic.py": _SEMANTIC_SOURCE_PATH,
        "src/dartwork_mpl/_colors/_ssot.py": Path(__file__).with_name(
            "_ssot.py"
        ),
        "src/dartwork_mpl/_colors/_tone.py": Path(__file__).with_name(
            "_tone.py"
        ),
        "src/dartwork_mpl/asset/mplstyle/theme-dark.mplstyle": (
            _DARK_STYLE_PATH
        ),
        "src/dartwork_mpl/mcp/prompts.py": _MCP_DIR / "prompts.py",
        "src/dartwork_mpl/mcp/resources.py": _MCP_DIR / "resources.py",
        "src/dartwork_mpl/mcp/tools.py": _MCP_DIR / "tools.py",
    }
    paths.update(
        {
            f"src/dartwork_mpl/asset/color/{path.name}": path
            for path in sorted(_COLOR_ASSET_DIR.glob("*.json"))
        }
    )
    paths["src/dartwork_mpl/asset/color/opencolor.txt"] = (
        _COLOR_ASSET_DIR / "opencolor.txt"
    )
    return {
        name: hashlib.sha256(path.read_bytes()).hexdigest()
        for name, path in sorted(paths.items())
    }


def compile_candidate_snapshot() -> CatalogSnapshot:
    """Compile and independently assemble the live candidate catalog.

    Returns
    -------
    CatalogSnapshot
        Candidate snapshot with 32/256 LUTs and derived exact surfaces.
    """
    authority = load_color_v6_ssot()
    vendor_colors = load_vendor_colors()
    palette = _generate.compile_palette(luminance_lock=True)
    cycles = {
        name: _cycles.cycle_hexes(name, palette) for name in _cycles.CYCLE_SPECS
    }
    cmaps_preview_32 = _cmaps.compile_cmaps(palette, n=32, luminance_lock=True)
    cmaps_256 = _cmaps.compile_cmaps(palette, n=256, luminance_lock=True)
    cmaps_unlocked_preview_error: str | None = None
    try:
        cmaps_unlocked_preview_32 = _cmaps.compile_cmaps(
            palette, n=32, luminance_lock=False
        )
    except Exception as error:  # noqa: BLE001 - diagnostic-only boundary
        cmaps_unlocked_preview_32 = {}
        cmaps_unlocked_preview_error = f"{type(error).__name__}: {error}"
    curated_rows = {name: tuple(row) for name, row in _curated.CURATED.items()}
    taxonomy, public_inventory = _derive_taxonomy(palette, cmaps_256, cycles)
    registrations = _derive_registrations(cmaps_256, cycles)
    diverging_canonicals = _derive_diverging_canonicals(taxonomy, palette)
    semantic_coordinates, semantic_colors = _resolve_semantic(palette)
    dark_coordinates, dark_cycle = _resolve_dark_cycle(palette)
    frozen_indices = _freeze_index_rows(
        cast(
            Mapping[str, Mapping[str, Sequence[int]]],
            authority["multi_hue_discrete_indices"],
        )
    )
    discrete, reverse_discrete, multi_hue_indices = _derive_discrete(
        taxonomy,
        palette,
        cycles,
        cmaps_256,
        diverging_canonicals,
        frozen_indices,
    )
    candidate = CatalogSnapshot(
        palette=cast(HexRows, palette),
        cycles=cast(HexRows, cycles),
        cmaps_256=cast(HexRows, cmaps_256),
        curated_rows=cast(HexRows, curated_rows),
        diverging_canonicals=cast(HexRows, diverging_canonicals),
        semantic_coordinates=cast(SemanticCoordinates, semantic_coordinates),
        semantic_colors=cast(SemanticColors, semantic_colors),
        dark_cycle_coordinates=tuple(dark_coordinates),
        dark_cycle=tuple(dark_cycle),
        taxonomy=taxonomy,
        registrations=registrations,
        typing_literals={},
        mcp_discovery=scan_mcp_discovery(),
        public_inventory=cast(PublicInventory, tuple(public_inventory)),
        discrete_hex=cast(NestedHexRows, discrete),
        reverse_discrete_hex=cast(NestedHexRows, reverse_discrete),
        multi_hue_discrete_indices=cast(IndexRows, multi_hue_indices),
        vendor_colors=vendor_colors,
        cmaps_preview_32=cast(HexRows, cmaps_preview_32),
        cmaps_unlocked_preview_32=cast(HexRows, cmaps_unlocked_preview_32),
        cmaps_unlocked_preview_error=cmaps_unlocked_preview_error,
        source_hashes=_candidate_source_hashes(),
    )
    candidate = replace(
        candidate,
        typing_literals=build_typing_payload(candidate, tuple(vendor_colors)),
    )
    return replace(
        candidate,
        canonical_hashes=_candidate_canonical_hashes(candidate),
        inventory=_candidate_inventory(candidate),
    )
