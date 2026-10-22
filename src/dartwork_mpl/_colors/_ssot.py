"""Parsed immutable access to the packaged v6 color authority.

``load_color_v6_ssot`` reads ``asset/color/color_v6_ssot.json`` once,
checks every hash, provenance pin, range and shape, and returns a
``ColorAuthority``: typed sections that consumers read as attributes, so
no consumer re-narrows the JSON. The JSON file and its pinned section
hashes are the authority; these types are its parsed form and are built
only by the loader (their range rules are checked there, not again by the
dataclasses).
"""

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from itertools import pairwise
from pathlib import Path
from types import MappingProxyType
from typing import TypeAlias, cast

__all__ = [
    "ColorAuthority",
    "CvdPolicy",
    "GamutPolicy",
    "Policies",
    "PresentationPolicy",
    "Recipe",
    "RecipeConstants",
    "RecipeFamily",
    "TonePolicy",
    "load_color_v6_ssot",
]

JsonMapping: TypeAlias = Mapping[str, object]
"""A deeply frozen JSON object (``MappingProxyType`` and tuples)."""


@dataclass(frozen=True, slots=True)
class GamutPolicy:
    """sRGB gamut mapping: bisect OKLCH chroma, keeping lightness and hue.

    ``iterations`` is positive, ``max_chroma_upper`` positive and
    ``tolerance`` non-negative.
    """

    iterations: int
    max_chroma_upper: float
    strategy: str
    tolerance: float


@dataclass(frozen=True, slots=True)
class TonePolicy:
    """Neutral-tone search budgets and chroma bounds.

    The three iteration counts are positive; ``catalog_chroma_fraction``
    is in (0, 1]; ``0 < probe_chroma <= max_chroma_upper``.
    """

    catalog_chroma_fraction: float
    luminance_search_iterations: int
    max_chroma_search_iterations: int
    max_chroma_tone_iterations: int
    max_chroma_upper: float
    probe_chroma: float


@dataclass(frozen=True, slots=True)
class CvdPolicy:
    """Colour-vision-deficiency simulation used for validation only.

    ``models_by_deficiency`` names a non-empty model for exactly
    ``protan``, ``deutan`` and ``tritan``.
    """

    gate_pipeline: str
    models_by_deficiency: Mapping[str, str]
    role: str


@dataclass(frozen=True, slots=True)
class PresentationPolicy:
    """Documentation-only presentation choices.

    ``multi_hue_vivid_cutoffs`` maps each of the nine multi-hue families to
    a 64-step preview index in ``[0, 64)``.
    """

    multi_hue_vivid_cutoffs: Mapping[str, int]


@dataclass(frozen=True, slots=True)
class Policies:
    """Construction and validation policy domains of the authority."""

    gamut: GamutPolicy
    tone: TonePolicy
    cvd: CvdPolicy
    presentation: PresentationPolicy


@dataclass(frozen=True, slots=True)
class RecipeFamily:
    """One sequential family's recipe row, every value a finite float.

    ``gamma`` is positive, ``tp`` in (0, 1], ``cmax`` non-negative, and
    ``cend``, ``c0`` and ``tone_floor`` in [0, 1].
    """

    h0: float
    dh: float
    gamma: float
    tp: float
    cmax: float
    tone_floor: float
    cend: float
    c0: float


@dataclass(frozen=True, slots=True)
class RecipeConstants:
    """Shared recipe constants; tones are in [0, 1].

    ``gray_c_profile`` holds ten non-negative chroma values;
    ``tone_derivation_grid``, ``shape_q`` and ``shape_r`` are positive and
    ``gamut_chroma_frac`` is in (0, 1].
    """

    tone_top: float
    shape_q: float
    shape_r: float
    gamut_chroma_frac: float
    gray_tone_floor: float
    gray_tint_hue: float
    gray_c_profile: tuple[float, ...]
    tone_derivation_grid: float


@dataclass(frozen=True, slots=True)
class Recipe:
    """The operational palette recipe.

    ``family_order`` lists the 19 recipe families; ``family_params`` has a
    row for exactly those names. ``fourier`` holds the four extension
    curves (``cmax_k3``, ``tone_floor_k3``: 7 coefficients; ``cend_k2``,
    ``c0_k2``: 5).
    """

    family_order: tuple[str, ...]
    family_params: Mapping[str, RecipeFamily]
    fourier: Mapping[str, tuple[float, ...]]
    constants: RecipeConstants


@dataclass(frozen=True, slots=True)
class ColorAuthority:
    """The parsed, validated, immutable v6 colour authority.

    ``recipe`` and ``policies`` are typed. The remaining sections keep
    their frozen JSON form: ``baselines`` and ``migration`` are provenance
    nothing computes from; ``coordinates``, ``row_contracts`` and
    ``multi_hue_discrete_indices`` are read by the build and gates.
    ``section_hashes`` maps every other top-level section name to its
    canonical SHA-256.
    """

    schema: str
    baseline_commit: str
    baselines: JsonMapping
    coordinates: JsonMapping
    migration: JsonMapping
    policies: Policies
    recipe: Recipe
    row_contracts: JsonMapping
    multi_hue_discrete_indices: JsonMapping
    section_hashes: Mapping[str, str]


_SSOT_PATH = (
    Path(__file__).resolve().parents[1] / "asset/color/color_v6_ssot.json"
)
_SCHEMA = "dartwork-mpl.color-ssot/v6"
_BASELINE_COMMIT = "12d16bac22dee790bd0696ca92a814a797dc728b"
_PINNED_BASELINES = MappingProxyType(
    {
        "recipe": (
            "docs/superpowers/specs/assets/2026-07-03-color-system-v5/"
            "color_v5_ssot.json",
            "a75bd08f2ae5606ec3076a01877ba813b9f2899a96b95739a44e5d3493b68518",
        ),
        "compatibility": (
            "docs/superpowers/specs/assets/2026-07-14-oklab-centered-"
            "color-system/color_v5_compatibility.json",
            "bc0b9fa8a5d888b60808de48dbdadb1ff25690e435a7bcc44aa63d31ce742818",
        ),
        "quality": (
            "docs/superpowers/specs/assets/2026-07-14-oklab-centered-"
            "color-system/color_v5_quality.json",
            "326906a7ab05b48ec35f37d8e2a73931106fc03edde7db263e1e6735f3c95616",
        ),
        "oracle": (
            "src/dartwork_mpl/_colors/_compatibility_metrics.py",
            "52718f3bf19f2fc2e5c7b95ef3cfe6338335b684eea86cd4b55892ed03765548",
        ),
    }
)
_AUDITED_SECTION_HASHES = MappingProxyType(
    {
        "baseline_commit": (
            "bedb4939ab85b17ace519b5f41ee8d3f6ad6a49d6d2935bb59b88c529a985b8f"
        ),
        "baselines": (
            "e54f5882d71d472dda15773f7bb28ff14c528323e875bb70b9300e86ec853c03"
        ),
        "coordinates": (
            "a38b6b417025c88bd30545b9852fdea3c647e980f7bf32f6908368de2fb55eda"
        ),
        "migration": (
            "79c14fd0d8d6e030ead1004a891473af0b0834014f8cae8047c1d3e19bc9f5b4"
        ),
        "multi_hue_discrete_indices": (
            "d932f4729a46847ded12ceeb7d8e4edb33ffe9d6ac0b4f5f60f053c60bbdc02f"
        ),
        "policies": (
            "42c27fd35dced335358118f566ec14feaf39eda58ca6df8584dd2156291d094a"
        ),
        "recipe": (
            "1871edf723343f54a252fb4bab77c37c285b800bcc324a2d0e6a065be33d67c4"
        ),
        "row_contracts": (
            "d4a80515b3b2df5129de09b04b47df16b1751bd8fdb83064151150422ef1462a"
        ),
        "schema": (
            "f550ca2eafef4f68b0a42848464b483a130596dfdb2c3bde0a91a513d6759636"
        ),
    }
)
_BASELINE_RECORD_FIELDS = MappingProxyType(
    {
        "recipe": frozenset({"path", "raw_sha256"}),
        "compatibility": frozenset({"canonical_hashes", "path", "raw_sha256"}),
        "quality": frozenset(
            {"global_extrema", "metrics", "path", "policy", "raw_sha256"}
        ),
        "oracle": frozenset({"path", "raw_sha256"}),
    }
)
_COMPATIBILITY_HASH_FIELDS = frozenset(
    {
        "cmaps256",
        "curated_rows",
        "cycles",
        "dark_cycle",
        "dark_cycle_coordinates",
        "discrete_hex",
        "diverging_canonicals",
        "mcp_discovery",
        "multi_hue_discrete_indices",
        "palette",
        "public_inventory",
        "registrations",
        "reverse_discrete_hex",
        "semantic_colors",
        "semantic_coordinates",
        "taxonomy",
        "typing_literals",
        "vendor_colors",
    }
)
_MULTI_HUE_FAMILIES = frozenset(
    {
        "afterglow",
        "aurora",
        "blaze",
        "canopy",
        "glacier",
        "haze",
        "iris",
        "lagoon",
        "lava",
    }
)
_ROW_CONTRACT_COUNTS = MappingProxyType(
    {
        "palette": 20,
        "direct_32": 43,
        "full_256": 43,
        "cycles": 2,
        "curated_rows": 15,
        "dark_cycle": 1,
        "discrete_forward": 547,
    }
)
_TOP_LEVEL_KEYS = frozenset(
    {
        "baseline_commit",
        "baselines",
        "coordinates",
        "migration",
        "multi_hue_discrete_indices",
        "policies",
        "recipe",
        "row_contracts",
        "schema",
        "section_hashes",
    }
)
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


def _canonical_sha256(value: object) -> str:
    """Hash one decoded JSON value with the canonical section encoding."""
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _require_mapping(value: object, label: str) -> Mapping[str, object]:
    """Return a decoded object after validating string keys.

    Raises
    ------
    RuntimeError
        If ``value`` is not a string-keyed mapping.
    """
    if not isinstance(value, Mapping) or not all(
        isinstance(key, str) for key in value
    ):
        raise RuntimeError(f"{label} must be a string-keyed object")
    return cast(Mapping[str, object], value)


def _require_sequence(value: object, label: str) -> Sequence[object]:
    """Return a decoded array after rejecting strings.

    Raises
    ------
    RuntimeError
        If ``value`` is not a non-string sequence.
    """
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise RuntimeError(f"{label} must be an array")
    return cast(Sequence[object], value)


def _require_real(value: object, label: str) -> float:
    """Return one finite non-boolean JSON number as ``float``.

    Raises
    ------
    RuntimeError
        If ``value`` is not a finite real number.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"{label} must be a finite number")
    try:
        result = float(value)
    except OverflowError as error:
        raise RuntimeError(f"{label} must be a finite number") from error
    if not math.isfinite(result):
        raise RuntimeError(f"{label} must be finite")
    return result


def _require_integer(value: object, label: str) -> int:
    """Return one non-boolean JSON integer.

    Raises
    ------
    RuntimeError
        If ``value`` is not an integer.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise RuntimeError(f"{label} must be an integer")
    return value


def _validate_finite(value: object, path: str = "color v6 SSOT") -> None:
    """Reject every non-finite numeric leaf before hash validation."""
    if isinstance(value, float) and not math.isfinite(value):
        raise RuntimeError(f"{path} must contain only finite numbers")
    if isinstance(value, Mapping):
        for key, item in value.items():
            _validate_finite(item, f"{path}.{key}")
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, item in enumerate(value):
            _validate_finite(item, f"{path}[{index}]")


def _object_without_duplicate_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    """Construct one decoded JSON object while rejecting duplicate names."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise RuntimeError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _validate_section_hashes(payload: Mapping[str, object]) -> None:
    """Validate all top-level authoritative section hashes."""
    raw_hashes = _require_mapping(payload["section_hashes"], "section hashes")
    expected_sections = set(payload) - {"section_hashes"}
    if set(raw_hashes) != expected_sections:
        raise RuntimeError("section hash coverage does not match SSOT sections")
    for name in sorted(expected_sections):
        digest = raw_hashes[name]
        if not isinstance(digest, str) or not _SHA256_PATTERN.fullmatch(digest):
            raise RuntimeError(f"section hash for {name} is malformed")
        if digest != _canonical_sha256(payload[name]):
            raise RuntimeError(f"section hash mismatch for {name}")


def _validate_audited_section_hashes(payload: Mapping[str, object]) -> None:
    """Match sections to digests derived from the raw-SHA-pinned audit.

    The hashes stored inside the JSON prove internal consistency only.  These
    accessor-side pins keep a coordinated payload/hash edit from silently
    redefining the accepted v6 authority.
    """
    actual = {
        name: _canonical_sha256(payload[name])
        for name in _AUDITED_SECTION_HASHES
    }
    if actual != dict(_AUDITED_SECTION_HASHES):
        changed = sorted(
            name
            for name, digest in actual.items()
            if digest != _AUDITED_SECTION_HASHES[name]
        )
        raise RuntimeError(
            "audited color v6 SSOT section mismatch: " + ", ".join(changed)
        )


def _contains_candidate_authority(value: object) -> bool:
    """Return whether a baseline subtree contains candidate-owned keys."""
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and key.casefold().startswith("candidate"):
                return True
            if _contains_candidate_authority(item):
                return True
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return any(_contains_candidate_authority(item) for item in value)
    return False


def _validate_provenance(payload: Mapping[str, object]) -> None:
    """Validate the accepted commit and four raw historical sources."""
    if payload["baseline_commit"] != _BASELINE_COMMIT:
        raise RuntimeError("baseline provenance commit does not match")
    baselines = _require_mapping(payload["baselines"], "baselines")
    if set(baselines) != set(_PINNED_BASELINES):
        raise RuntimeError("baseline provenance source set does not match")
    for name, (expected_path, expected_sha256) in _PINNED_BASELINES.items():
        record = _require_mapping(baselines[name], f"baseline {name}")
        if set(record) != _BASELINE_RECORD_FIELDS[name]:
            raise RuntimeError(f"baseline authority fields mismatch for {name}")
        if (
            record.get("path") != expected_path
            or record.get("raw_sha256") != expected_sha256
        ):
            raise RuntimeError(f"baseline provenance mismatch for {name}")
    compatibility = _require_mapping(
        baselines["compatibility"], "compatibility baseline"
    )
    canonical_hashes = _require_mapping(
        compatibility["canonical_hashes"],
        "compatibility baseline canonical hashes",
    )
    if set(canonical_hashes) != _COMPATIBILITY_HASH_FIELDS or any(
        not isinstance(digest, str) or _SHA256_PATTERN.fullmatch(digest) is None
        for digest in canonical_hashes.values()
    ):
        raise RuntimeError("compatibility baseline authority is malformed")

    quality = _require_mapping(baselines["quality"], "quality baseline")
    for field in ("metrics", "global_extrema", "policy"):
        authority = _require_mapping(
            quality[field], f"quality baseline {field}"
        )
        if not authority:
            raise RuntimeError(f"quality baseline {field} must not be empty")
    if _contains_candidate_authority(baselines):
        raise RuntimeError("baseline authority must not contain candidate data")


def _validate_coordinates(payload: Mapping[str, object]) -> None:
    """Validate coordinate roles and the modeled relative-Y row."""
    coordinates = _require_mapping(payload["coordinates"], "coordinates")
    expected_fields = {
        "authoring",
        "canonical",
        "neutral_tone",
        "output",
        "relative_y_coefficients",
        "validation_only",
    }
    if set(coordinates) != expected_fields:
        raise RuntimeError("coordinate authority fields do not match")
    expected_strings = {
        "authoring": "OKLab/OKLCH",
        "canonical": "OKLab",
        "neutral_tone": ("cbrt(modeled relative CIE Y from nominal D65 sRGB)"),
        "output": ("modeled relative CIE Y calculated from nominal D65 sRGB"),
    }
    if any(
        coordinates[name] != value for name, value in expected_strings.items()
    ):
        raise RuntimeError("coordinate roles do not match the v6 contract")
    raw_coefficients = _require_sequence(
        coordinates["relative_y_coefficients"], "relative-Y coefficients"
    )
    coefficients = tuple(
        _require_real(value, f"relative-Y coefficient {index}")
        for index, value in enumerate(raw_coefficients)
    )
    expected_coefficients = (
        0.21267287873271212,
        0.7151521284847872,
        0.07217499278250072,
    )
    if coefficients != expected_coefficients or sum(coefficients) != 1.0:
        raise RuntimeError("relative-Y coefficients do not match")
    validation_only = _require_sequence(
        coordinates["validation_only"], "validation-only coordinates"
    )
    if tuple(validation_only) != ("CIELAB", "CIEDE2000", "Machado/BVM CVD"):
        raise RuntimeError("validation-only coordinate roles do not match")


def _validate_migration(payload: Mapping[str, object]) -> None:
    """Validate the offline-only legacy-coordinate provenance record."""
    migration = _require_mapping(payload["migration"], "migration")
    expected_fields = {
        "denominator",
        "legacy_coordinate",
        "legacy_white_y",
        "lower_formula",
        "scope",
        "toe_kappa",
        "toe_lstar",
        "upper_formula",
    }
    if set(migration) != expected_fields:
        raise RuntimeError("migration authority fields do not match")
    numeric = {
        name: _require_real(migration[name], f"migration {name}")
        for name in ("denominator", "legacy_white_y", "toe_kappa", "toe_lstar")
    }
    if any(value <= 0.0 for value in numeric.values()):
        raise RuntimeError("migration numeric values must be positive")
    expected_strings = {
        "legacy_coordinate": "CIELAB L* D65",
        "lower_formula": "cbrt((L* / (24389 / 27)) / S)",
        "scope": "offline v5 compatibility provenance only",
        "upper_formula": "(L* + 16) / D",
    }
    if any(
        migration[name] != value for name, value in expected_strings.items()
    ):
        raise RuntimeError("migration provenance does not match")


def _parse_policies(payload: Mapping[str, object]) -> Policies:
    """Parse deterministic construction and validation policy domains."""
    policies = _require_mapping(payload["policies"], "policies")
    if set(policies) != {"gamut", "tone", "cvd", "presentation"}:
        raise RuntimeError("policy sections do not match")

    gamut = _require_mapping(policies["gamut"], "gamut policy")
    if set(gamut) != {
        "iterations",
        "max_chroma_upper",
        "strategy",
        "tolerance",
    }:
        raise RuntimeError("gamut policy fields do not match")
    gamut_iterations = _require_integer(gamut["iterations"], "gamut iterations")
    if gamut_iterations <= 0:
        raise RuntimeError("gamut iterations must be positive")
    gamut_maximum = _require_real(gamut["max_chroma_upper"], "gamut maximum")
    if gamut_maximum <= 0.0:
        raise RuntimeError("gamut maximum chroma must be positive")
    gamut_tolerance = _require_real(gamut["tolerance"], "gamut tolerance")
    if gamut_tolerance < 0.0:
        raise RuntimeError("gamut tolerance must be non-negative")
    gamut_strategy = gamut["strategy"]
    if (
        not isinstance(gamut_strategy, str)
        or gamut_strategy != "preserve OKLCH L/h and reduce C"
    ):
        raise RuntimeError("gamut strategy does not match")
    gamut_policy = GamutPolicy(
        iterations=gamut_iterations,
        max_chroma_upper=gamut_maximum,
        strategy=gamut_strategy,
        tolerance=gamut_tolerance,
    )

    tone = _require_mapping(policies["tone"], "tone policy")
    expected_tone_fields = {
        "catalog_chroma_fraction",
        "luminance_search_iterations",
        "max_chroma_search_iterations",
        "max_chroma_tone_iterations",
        "max_chroma_upper",
        "probe_chroma",
    }
    if set(tone) != expected_tone_fields:
        raise RuntimeError("tone policy fields do not match")
    iterations: dict[str, int] = {}
    for field in (
        "luminance_search_iterations",
        "max_chroma_search_iterations",
        "max_chroma_tone_iterations",
    ):
        iterations[field] = _require_integer(
            tone[field], f"tone policy {field}"
        )
        if iterations[field] <= 0:
            raise RuntimeError(f"tone policy {field} must be positive")
    fraction = _require_real(
        tone["catalog_chroma_fraction"], "tone catalog chroma fraction"
    )
    if not 0.0 < fraction <= 1.0:
        raise RuntimeError("tone catalog chroma fraction must be in (0, 1]")
    max_chroma = _require_real(tone["max_chroma_upper"], "tone maximum chroma")
    probe = _require_real(tone["probe_chroma"], "tone probe chroma")
    if max_chroma <= 0.0 or not 0.0 < probe <= max_chroma:
        raise RuntimeError("tone chroma bounds are malformed")
    tone_policy = TonePolicy(
        catalog_chroma_fraction=fraction,
        luminance_search_iterations=iterations["luminance_search_iterations"],
        max_chroma_search_iterations=iterations["max_chroma_search_iterations"],
        max_chroma_tone_iterations=iterations["max_chroma_tone_iterations"],
        max_chroma_upper=max_chroma,
        probe_chroma=probe,
    )

    cvd = _require_mapping(policies["cvd"], "CVD policy")
    if set(cvd) != {"gate_pipeline", "models_by_deficiency", "role"}:
        raise RuntimeError("CVD policy fields do not match")
    models = _require_mapping(cvd["models_by_deficiency"], "CVD models")
    model_names = {
        deficiency: model
        for deficiency, model in models.items()
        if isinstance(model, str) and model
    }
    if set(models) != {"protan", "deutan", "tritan"} or len(model_names) != len(
        models
    ):
        raise RuntimeError("CVD model authority is malformed")
    gate_pipeline = cvd["gate_pipeline"]
    if not isinstance(gate_pipeline, str) or not gate_pipeline:
        raise RuntimeError("CVD gate pipeline must be a non-empty string")
    cvd_role = cvd["role"]
    if (
        not isinstance(cvd_role, str)
        or cvd_role != "model-specific validation only"
    ):
        raise RuntimeError("CVD role must remain validation-only")
    cvd_policy = CvdPolicy(
        gate_pipeline=gate_pipeline,
        models_by_deficiency=MappingProxyType(
            dict(sorted(model_names.items()))
        ),
        role=cvd_role,
    )

    presentation = _require_mapping(
        policies["presentation"], "presentation policy"
    )
    if set(presentation) != {"multi_hue_vivid_cutoffs"}:
        raise RuntimeError("presentation policy fields do not match")
    cutoffs = _require_mapping(
        presentation["multi_hue_vivid_cutoffs"], "multi-hue vivid cutoffs"
    )
    if set(cutoffs) != _MULTI_HUE_FAMILIES:
        raise RuntimeError("multi-hue vivid cutoff family set does not match")
    parsed_cutoffs: dict[str, int] = {}
    for family, raw_cutoff in cutoffs.items():
        cutoff = _require_integer(
            raw_cutoff, f"multi-hue vivid cutoff {family}"
        )
        if not 0 <= cutoff < 64:
            raise RuntimeError(
                f"multi-hue vivid cutoff {family} is out of range"
            )
        parsed_cutoffs[family] = cutoff
    return Policies(
        gamut=gamut_policy,
        tone=tone_policy,
        cvd=cvd_policy,
        presentation=PresentationPolicy(
            multi_hue_vivid_cutoffs=MappingProxyType(
                dict(sorted(parsed_cutoffs.items()))
            )
        ),
    )


def _parse_recipe(payload: Mapping[str, object]) -> Recipe:
    """Parse operational recipe shape and every neutral-tone value."""
    recipe = _require_mapping(payload["recipe"], "recipe")
    if set(recipe) != {"family_order", "family_params", "fourier", "constants"}:
        raise RuntimeError("recipe sections do not match the v6 contract")
    family_order = _require_sequence(
        recipe["family_order"], "recipe family order"
    )
    family_params = _require_mapping(
        recipe["family_params"], "recipe family params"
    )
    if (
        len(family_order) != 19
        or len(family_params) != 19
        or not all(isinstance(name, str) for name in family_order)
        or set(cast(Sequence[str], family_order)) != set(family_params)
    ):
        raise RuntimeError("recipe family authority must contain 19 rows")
    parameter_fields = {
        "h0",
        "dh",
        "gamma",
        "tp",
        "cmax",
        "tone_floor",
        "cend",
        "c0",
    }
    family_names = tuple(name for name in family_order if isinstance(name, str))
    parsed_families: dict[str, RecipeFamily] = {}
    for family, raw_params in family_params.items():
        params = _require_mapping(raw_params, f"recipe family {family}")
        if set(params) != parameter_fields:
            raise RuntimeError(f"recipe family {family} fields do not match")
        values = {
            field: _require_real(raw_value, f"recipe family {family}.{field}")
            for field, raw_value in params.items()
        }
        gamma = _require_real(params["gamma"], f"recipe family {family}.gamma")
        if gamma <= 0.0:
            raise RuntimeError(f"recipe family {family}.gamma must be positive")
        peak = _require_real(params["tp"], f"recipe family {family}.tp")
        if not 0.0 < peak <= 1.0:
            raise RuntimeError(f"recipe family {family}.tp must be in (0, 1]")
        maximum_chroma = _require_real(
            params["cmax"], f"recipe family {family}.cmax"
        )
        if maximum_chroma < 0.0:
            raise RuntimeError(
                f"recipe family {family}.cmax must be non-negative"
            )
        for field in ("cend", "c0"):
            fraction = _require_real(
                params[field], f"recipe family {family}.{field}"
            )
            if not 0.0 <= fraction <= 1.0:
                raise RuntimeError(
                    f"recipe family {family}.{field} must be in [0, 1]"
                )
        tone_floor = _require_real(
            params["tone_floor"], f"recipe family {family}.tone_floor"
        )
        if not 0.0 <= tone_floor <= 1.0:
            raise RuntimeError(f"recipe family {family} tone is out of range")
        parsed_families[family] = RecipeFamily(
            h0=values["h0"],
            dh=values["dh"],
            gamma=gamma,
            tp=peak,
            cmax=maximum_chroma,
            tone_floor=tone_floor,
            cend=values["cend"],
            c0=values["c0"],
        )

    constants = _require_mapping(recipe["constants"], "recipe constants")
    expected_constants = {
        "TONE_TOP",
        "SHAPE_Q",
        "SHAPE_R",
        "GAMUT_CHROMA_FRAC",
        "GRAY_TONE_FLOOR",
        "GRAY_TINT_HUE",
        "GRAY_C_PROFILE",
        "TONE_DERIVATION_GRID",
    }
    if set(constants) != expected_constants:
        raise RuntimeError("recipe constants do not match the v6 contract")
    exponents: dict[str, float] = {}
    for name in ("SHAPE_Q", "SHAPE_R"):
        exponent = _require_real(constants[name], f"recipe constant {name}")
        if exponent <= 0.0:
            raise RuntimeError(f"recipe constant {name} must be positive")
        exponents[name] = exponent
    chroma_fraction = _require_real(
        constants["GAMUT_CHROMA_FRAC"], "recipe constant GAMUT_CHROMA_FRAC"
    )
    if not 0.0 < chroma_fraction <= 1.0:
        raise RuntimeError(
            "recipe constant GAMUT_CHROMA_FRAC must be in (0, 1]"
        )
    gray_tint_hue = _require_real(
        constants["GRAY_TINT_HUE"], "recipe constant GRAY_TINT_HUE"
    )
    gray_profile = _require_sequence(
        constants["GRAY_C_PROFILE"], "recipe constant GRAY_C_PROFILE"
    )
    if len(gray_profile) != 10:
        raise RuntimeError(
            "recipe constant GRAY_C_PROFILE must contain ten values"
        )
    gray_chroma: list[float] = []
    for index, value in enumerate(gray_profile):
        chroma = _require_real(
            value, f"recipe constant GRAY_C_PROFILE[{index}]"
        )
        if chroma < 0.0:
            raise RuntimeError(
                "recipe constant GRAY_C_PROFILE values must be non-negative"
            )
        gray_chroma.append(chroma)
    tones: dict[str, float] = {}
    for name in ("TONE_TOP", "GRAY_TONE_FLOOR"):
        tone = _require_real(constants[name], f"recipe constant {name}")
        if not 0.0 <= tone <= 1.0:
            raise RuntimeError(f"recipe constant {name} tone is out of range")
        tones[name] = tone
    grid = _require_real(
        constants["TONE_DERIVATION_GRID"], "tone derivation grid"
    )
    if grid <= 0.0:
        raise RuntimeError("tone derivation grid must be positive")

    fourier = _require_mapping(recipe["fourier"], "recipe Fourier curves")
    expected_lengths = {
        "cmax_k3": 7,
        "tone_floor_k3": 7,
        "cend_k2": 5,
        "c0_k2": 5,
    }
    if set(fourier) != set(expected_lengths):
        raise RuntimeError("recipe Fourier curves do not match")
    curves: dict[str, tuple[float, ...]] = {}
    for name, expected_length in expected_lengths.items():
        coefficients = _require_sequence(fourier[name], f"Fourier {name}")
        if len(coefficients) != expected_length:
            raise RuntimeError(f"Fourier {name} has the wrong length")
        curves[name] = tuple(
            _require_real(value, f"Fourier {name}[{index}]")
            for index, value in enumerate(coefficients)
        )
    return Recipe(
        family_order=family_names,
        family_params=MappingProxyType(dict(sorted(parsed_families.items()))),
        fourier=MappingProxyType(dict(sorted(curves.items()))),
        constants=RecipeConstants(
            tone_top=tones["TONE_TOP"],
            shape_q=exponents["SHAPE_Q"],
            shape_r=exponents["SHAPE_R"],
            gamut_chroma_frac=chroma_fraction,
            gray_tone_floor=tones["GRAY_TONE_FLOOR"],
            gray_tint_hue=gray_tint_hue,
            gray_c_profile=tuple(gray_chroma),
            tone_derivation_grid=grid,
        ),
    )


def _validate_row_contracts(payload: Mapping[str, object]) -> None:
    """Validate cardinality and shape of all 671 frozen row contracts."""
    contracts = _require_mapping(payload["row_contracts"], "row contracts")
    if set(contracts) != set(_ROW_CONTRACT_COUNTS):
        raise RuntimeError("row contract sections do not match")
    record_fields = {
        "adjacent_duplicate_count",
        "canonical_sha256",
        "count",
        "max_run_length",
        "unique_count",
    }
    fixed_counts = {
        "palette": 10,
        "direct_32": 32,
        "full_256": 256,
        "cycles": 8,
        "curated_rows": 8,
        "dark_cycle": 7,
    }
    for section, expected_count in _ROW_CONTRACT_COUNTS.items():
        rows = _require_mapping(contracts[section], f"row contracts {section}")
        if len(rows) != expected_count:
            raise RuntimeError(
                f"row contract cardinality mismatch for {section}"
            )
        for name, raw_record in rows.items():
            record = _require_mapping(
                raw_record, f"row contract {section}.{name}"
            )
            if set(record) != record_fields:
                raise RuntimeError(
                    f"row contract {section}.{name} is malformed"
                )
            digest = record["canonical_sha256"]
            if not isinstance(digest, str) or not _SHA256_PATTERN.fullmatch(
                digest
            ):
                raise RuntimeError(
                    f"row contract {section}.{name} hash is malformed"
                )
            count = _require_integer(
                record["count"], f"row contract {section}.{name}.count"
            )
            unique = _require_integer(
                record["unique_count"],
                f"row contract {section}.{name}.unique_count",
            )
            adjacent = _require_integer(
                record["adjacent_duplicate_count"],
                f"row contract {section}.{name}.adjacent_duplicate_count",
            )
            max_run = _require_integer(
                record["max_run_length"],
                f"row contract {section}.{name}.max_run_length",
            )
            if section == "discrete_forward":
                try:
                    expected_row_count = int(name.rsplit("/", 1)[1])
                except (IndexError, ValueError) as error:
                    raise RuntimeError(
                        f"row contract {section}.{name} name is malformed"
                    ) from error
                if expected_row_count <= 0:
                    raise RuntimeError(
                        f"row contract {section}.{name} size is malformed"
                    )
            else:
                expected_row_count = fixed_counts[section]
            if not (
                count == expected_row_count
                and 1 <= unique <= count
                and 0 <= adjacent < count
                and 1 <= max_run <= count
                and unique <= count - adjacent
                and max_run <= adjacent + 1
            ):
                raise RuntimeError(
                    f"row contract {section}.{name} values are malformed"
                )
            if unique == count and (adjacent, max_run) != (0, 1):
                raise RuntimeError(
                    f"row contract {section}.{name} duplicates are impossible"
                )
            if adjacent == 0 and max_run != 1:
                raise RuntimeError(
                    f"row contract {section}.{name} run is impossible"
                )
            if adjacent > 0 and max_run < 2:
                raise RuntimeError(
                    f"row contract {section}.{name} run is impossible"
                )


def _validate_multi_hue_indices(payload: Mapping[str, object]) -> None:
    """Validate each shipped discrete index row against the LUT domain."""
    families = _require_mapping(
        payload["multi_hue_discrete_indices"], "multi-hue indices"
    )
    if set(families) != _MULTI_HUE_FAMILIES:
        raise RuntimeError("multi-hue index family set does not match")
    for family, raw_forms in families.items():
        forms = _require_mapping(raw_forms, f"multi-hue {family}")
        if set(forms) != {str(size) for size in range(1, 9)}:
            raise RuntimeError(f"multi-hue {family} size set does not match")
        for size, raw_indices in forms.items():
            try:
                expected_length = int(size)
            except ValueError as error:
                raise RuntimeError(
                    f"multi-hue {family} size must be an integer"
                ) from error
            if str(expected_length) != size or not 1 <= expected_length <= 8:
                raise RuntimeError(f"multi-hue {family} size is out of range")
            indices = _require_sequence(
                raw_indices, f"multi-hue {family}.{size}"
            )
            if len(indices) != expected_length:
                raise RuntimeError(
                    f"multi-hue {family}.{size} has the wrong length"
                )
            checked = [
                _require_integer(value, f"multi-hue {family}.{size}[{index}]")
                for index, value in enumerate(indices)
            ]
            if any(index < 0 or index > 255 for index in checked):
                raise RuntimeError(
                    f"multi-hue {family}.{size} index is out of LUT range"
                )
            if any(left >= right for left, right in pairwise(checked)):
                raise RuntimeError(
                    f"multi-hue {family}.{size} indices must increase"
                )


def _freeze(value: object) -> object:
    """Recursively copy decoded JSON into immutable containers."""
    if isinstance(value, Mapping):
        mapping = _require_mapping(value, "SSOT value")
        return MappingProxyType(
            {key: _freeze(item) for key, item in sorted(mapping.items())}
        )
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(_freeze(item) for item in value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise RuntimeError(f"unsupported SSOT value type: {type(value).__name__}")


def _freeze_mapping(value: object) -> JsonMapping:
    """Deeply freeze one validated JSON object section."""
    frozen = _freeze(value)
    if not isinstance(frozen, Mapping):
        raise RuntimeError("SSOT section must be a string-keyed object")
    return cast(JsonMapping, frozen)


def _load_color_v6_ssot(path: Path) -> ColorAuthority:
    """Load, validate, and parse one v6 authority file.

    Parameters
    ----------
    path : pathlib.Path
        JSON asset path.

    Returns
    -------
    ColorAuthority
        The parsed authority; its untyped sections are deeply frozen.

    Raises
    ------
    RuntimeError
        If any schema, hash, provenance, range, or shape check fails.
    """
    try:
        decoded: object = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_object_without_duplicate_keys,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"could not decode color v6 SSOT: {path}") from error
    payload = _require_mapping(decoded, "color v6 SSOT")
    _validate_finite(payload)
    if set(payload) != _TOP_LEVEL_KEYS:
        raise RuntimeError("color v6 SSOT top-level sections do not match")
    if payload["schema"] != _SCHEMA:
        raise RuntimeError("color v6 SSOT schema does not match")
    _validate_section_hashes(payload)
    _validate_provenance(payload)
    _validate_coordinates(payload)
    _validate_migration(payload)
    policies = _parse_policies(payload)
    recipe = _parse_recipe(payload)
    _validate_row_contracts(payload)
    _validate_multi_hue_indices(payload)
    _validate_audited_section_hashes(payload)
    section_hashes = _require_mapping(payload["section_hashes"], "hashes")
    return ColorAuthority(
        schema=_SCHEMA,
        baseline_commit=_BASELINE_COMMIT,
        baselines=_freeze_mapping(payload["baselines"]),
        coordinates=_freeze_mapping(payload["coordinates"]),
        migration=_freeze_mapping(payload["migration"]),
        policies=policies,
        recipe=recipe,
        row_contracts=_freeze_mapping(payload["row_contracts"]),
        multi_hue_discrete_indices=_freeze_mapping(
            payload["multi_hue_discrete_indices"]
        ),
        section_hashes=MappingProxyType(
            {
                name: digest
                for name, digest in sorted(section_hashes.items())
                if isinstance(digest, str)
            }
        ),
    )


@lru_cache(maxsize=1)
def load_color_v6_ssot() -> ColorAuthority:
    """Return the cached, validated, parsed v6 authority."""
    return _load_color_v6_ssot(_SSOT_PATH)
