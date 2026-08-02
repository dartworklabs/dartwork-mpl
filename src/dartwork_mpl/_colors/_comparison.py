"""Deterministic v5/v6 color-catalog comparison and standalone report.

The comparison boundary intentionally depends only on immutable catalog
snapshots and the standard-library compatibility oracle.  It never imports
matplotlib, generated catalog data, or runtime registries.

Modeled relative CIE Y (`relative_y`) is calculated from nominal D65 sRGB; it
is not a measurement of a particular display, perceived brightness, or OKLab
`L`.
"""

from __future__ import annotations

import html
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from itertools import pairwise
from types import MappingProxyType
from typing import Protocol, TypeAlias, cast

from . import _compatibility_metrics as oracle
from . import _gates as gates

__all__ = [
    "ComparisonReport",
    "ExactMismatch",
    "ExactSurfaceComparison",
    "HexRowComparison",
    "QualityComparison",
    "Violation",
    "compare_catalog",
    "compare_exact_surfaces",
    "compare_quality_metrics",
    "render_comparison_html",
]

JsonMapping: TypeAlias = Mapping[str, object]
MaybeSummary: TypeAlias = oracle.NumericSummary | None

_COMPARISON_SCHEMA = "dartwork-mpl.color-comparison/v1"
_HEX_PATTERN = re.compile(r"#[0-9a-fA-F]{6}\Z")
_CVD_MODES = ("protan", "deutan", "tritan")
_MISSING = object()
_MODELED_Y_LIMITATION = (
    "Modeled relative CIE Y (`relative_y`) is calculated from nominal D65 "
    "sRGB; it is not a measurement of a particular display, perceived "
    "brightness, or OKLab `L`."
)


class CatalogSnapshot(Protocol):
    """Structural catalog boundary that avoids importing the live compiler."""

    @property
    def palette(self) -> Mapping[str, tuple[str, ...]]: ...

    @property
    def cycles(self) -> Mapping[str, tuple[str, ...]]: ...

    @property
    def cmaps_256(self) -> Mapping[str, tuple[str, ...]]: ...

    @property
    def cmaps_preview_32(self) -> Mapping[str, tuple[str, ...]]: ...

    @property
    def cmaps_unlocked_preview_32(self) -> Mapping[str, tuple[str, ...]]: ...

    @property
    def cmaps_unlocked_preview_error(self) -> str | None: ...

    @property
    def curated_rows(self) -> Mapping[str, tuple[str, ...]]: ...

    @property
    def dark_cycle(self) -> tuple[str, ...]: ...

    @property
    def discrete_hex(self) -> Mapping[str, Mapping[str, tuple[str, ...]]]: ...

    @property
    def vendor_colors(self) -> Mapping[str, str]: ...

    @property
    def taxonomy(self) -> Mapping[str, str]: ...

    @property
    def schema(self) -> str: ...

    @property
    def baseline_commit(self) -> str | None: ...

    @property
    def source_hashes(self) -> Mapping[str, str]: ...

    @property
    def canonical_hashes(self) -> Mapping[str, str]: ...

    @property
    def inventory(self) -> Mapping[str, int]: ...

    def exact_payload(self) -> dict[str, object]:
        """Return the normalized exact compatibility surfaces."""
        ...


def _freeze(value: object) -> object:
    """Copy JSON-like data into deterministic immutable containers."""
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("comparison mappings require string keys")
        return MappingProxyType(
            {str(key): _freeze(item) for key, item in sorted(value.items())}
        )
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(_freeze(item) for item in value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise TypeError(f"unsupported comparison value: {type(value).__name__}")


def _thaw(value: object) -> object:
    """Return fresh JSON containers for immutable comparison data."""
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


def _freeze_mapping(value: Mapping[str, object]) -> JsonMapping:
    """Narrow the result of recursive freezing to a mapping."""
    return cast(JsonMapping, _freeze(value))


def _summary_payload(summary: MaybeSummary) -> object:
    """Serialize an optional independent-oracle numeric summary."""
    return None if summary is None else summary.to_json_value()


@dataclass(frozen=True, slots=True)
class ExactMismatch:
    """One exact-surface leaf mismatch represented by a JSON pointer."""

    path: str
    baseline_present: bool
    candidate_present: bool
    baseline: object
    candidate: object

    def __post_init__(self) -> None:
        """Detach retained mismatch leaves from caller-owned containers."""
        object.__setattr__(self, "baseline", _freeze(self.baseline))
        object.__setattr__(self, "candidate", _freeze(self.candidate))

    def to_payload(self) -> dict[str, object]:
        """Return a JSON-safe explicit representation."""
        return {
            "baseline": _thaw(self.baseline),
            "baseline_present": self.baseline_present,
            "candidate": _thaw(self.candidate),
            "candidate_present": self.candidate_present,
            "path": self.path,
        }


@dataclass(frozen=True, slots=True)
class ExactSurfaceComparison:
    """Digest and sorted mismatch inventory for one exact surface."""

    surface: str
    baseline_sha256: str
    candidate_sha256: str
    mismatches: tuple[ExactMismatch, ...]

    @property
    def mismatch_count(self) -> int:
        """Return the number of mismatched leaves."""
        return len(self.mismatches)

    def to_payload(self) -> dict[str, object]:
        """Return the complete machine-report representation."""
        return {
            "baseline_sha256": self.baseline_sha256,
            "candidate_sha256": self.candidate_sha256,
            "mismatch_count": self.mismatch_count,
            "mismatches": [item.to_payload() for item in self.mismatches],
            "surface": self.surface,
        }


@dataclass(frozen=True, slots=True)
class RowProfile:
    """Per-stop diagnostics used by JSON and the inline HTML renderer."""

    oklab_l: tuple[float | None, ...]
    relative_y: tuple[float | None, ...]
    neighbor_delta_e_ok: tuple[float | None, ...]
    grayscale_hex: tuple[str | None, ...]
    cvd_hex: Mapping[str, tuple[str | None, ...]]

    def __post_init__(self) -> None:
        """Freeze CVD rows supplied through direct construction."""
        object.__setattr__(
            self,
            "cvd_hex",
            MappingProxyType(
                {mode: tuple(row) for mode, row in sorted(self.cvd_hex.items())}
            ),
        )

    def to_payload(self) -> dict[str, object]:
        """Return literal profile arrays without display rounding."""
        return {
            "cvd_hex": {
                mode: list(row) for mode, row in sorted(self.cvd_hex.items())
            },
            "grayscale_hex": list(self.grayscale_hex),
            "neighbor_delta_e_ok": list(self.neighbor_delta_e_ok),
            "oklab_l": list(self.oklab_l),
            "relative_y": list(self.relative_y),
        }


@dataclass(frozen=True, slots=True)
class HexRowComparison:
    """Raw old/new diagnostics for one named palette, cycle, or LUT row."""

    name: str
    kind: str
    baseline_hex: tuple[str, ...]
    candidate_hex: tuple[str, ...]
    baseline_preview_hex: tuple[str, ...]
    candidate_preview_hex: tuple[str, ...]
    mismatch_indices: tuple[int, ...]
    delta_e_ok: MaybeSummary
    delta_e00: MaybeSummary
    signed_delta_y: MaybeSummary
    absolute_delta_y: MaybeSummary
    light_contrast_delta: MaybeSummary
    dark_contrast_delta: MaybeSummary
    cvd_delta_e00: Mapping[str, MaybeSummary]
    baseline_profile: RowProfile
    candidate_profile: RowProfile

    def __post_init__(self) -> None:
        """Freeze optional CVD summary mapping."""
        object.__setattr__(
            self,
            "cvd_delta_e00",
            MappingProxyType(dict(sorted(self.cvd_delta_e00.items()))),
        )

    @property
    def mismatch_count(self) -> int:
        """Return the number of mismatched or unpaired indices."""
        return len(self.mismatch_indices)

    def to_payload(self) -> dict[str, object]:
        """Return complete row diagnostics for the machine report."""
        return {
            "absolute_delta_y": _summary_payload(self.absolute_delta_y),
            "baseline_hex": list(self.baseline_hex),
            "baseline_preview_hex": list(self.baseline_preview_hex),
            "baseline_profile": self.baseline_profile.to_payload(),
            "candidate_hex": list(self.candidate_hex),
            "candidate_preview_hex": list(self.candidate_preview_hex),
            "candidate_profile": self.candidate_profile.to_payload(),
            "cvd_delta_e00": {
                mode: _summary_payload(summary)
                for mode, summary in sorted(self.cvd_delta_e00.items())
            },
            "dark_contrast_delta": _summary_payload(self.dark_contrast_delta),
            "delta_e00": _summary_payload(self.delta_e00),
            "delta_e_ok": _summary_payload(self.delta_e_ok),
            "kind": self.kind,
            "light_contrast_delta": _summary_payload(self.light_contrast_delta),
            "mismatch_count": self.mismatch_count,
            "mismatch_indices": list(self.mismatch_indices),
            "name": self.name,
            "signed_delta_y": _summary_payload(self.signed_delta_y),
        }


@dataclass(frozen=True, slots=True, order=True)
class Violation:
    """Stable quality or validity failure suitable for sorted output."""

    code: str
    surface: str
    asset: str
    path: str
    message: str
    baseline: object = field(compare=False)
    candidate: object = field(compare=False)

    def __post_init__(self) -> None:
        """Detach retained decision operands from caller-owned containers."""
        object.__setattr__(self, "baseline", _freeze(self.baseline))
        object.__setattr__(self, "candidate", _freeze(self.candidate))

    def to_payload(self) -> dict[str, object]:
        """Return a JSON-safe explicit representation."""
        return {
            "asset": self.asset,
            "baseline": _thaw(self.baseline),
            "candidate": _thaw(self.candidate),
            "code": self.code,
            "message": self.message,
            "path": self.path,
            "surface": self.surface,
        }


@dataclass(frozen=True, slots=True)
class QualityComparison:
    """Pinned quality baseline, candidate metrics, and raw gate decisions."""

    baseline_matches_fixture: bool
    baseline_metrics: JsonMapping
    candidate_metrics: JsonMapping
    baseline_global_extrema: JsonMapping
    candidate_global_extrema: JsonMapping
    policy: JsonMapping
    fixture_sha256: str
    oracle_sha256: str
    violations: tuple[Violation, ...]

    def __post_init__(self) -> None:
        """Detach all nested metric inputs from mutable caller containers."""
        for name in (
            "baseline_metrics",
            "candidate_metrics",
            "baseline_global_extrema",
            "candidate_global_extrema",
            "policy",
        ):
            object.__setattr__(
                self,
                name,
                _freeze_mapping(
                    cast(Mapping[str, object], getattr(self, name))
                ),
            )

    def to_payload(self) -> dict[str, object]:
        """Return the quality section of ``report.json``."""
        return {
            "baseline_global_extrema": _thaw(self.baseline_global_extrema),
            "baseline_matches_fixture": self.baseline_matches_fixture,
            "baseline_metrics": _thaw(self.baseline_metrics),
            "candidate_global_extrema": _thaw(self.candidate_global_extrema),
            "candidate_metrics": _thaw(self.candidate_metrics),
            "fixture_sha256": self.fixture_sha256,
            "oracle_sha256": self.oracle_sha256,
            "policy": _thaw(self.policy),
            "violations": [item.to_payload() for item in self.violations],
        }


@dataclass(frozen=True, slots=True)
class ComparisonReport:
    """Immutable machine-readable gate record and human diagnostics."""

    schema: str
    passed: bool
    baseline_source: JsonMapping
    candidate_source: JsonMapping
    inventory: JsonMapping
    exact_surfaces: Mapping[str, ExactSurfaceComparison]
    palette: Mapping[str, HexRowComparison]
    cycles: Mapping[str, HexRowComparison]
    cmaps_256: Mapping[str, HexRowComparison]
    taxonomy: Mapping[str, str]
    quality: QualityComparison
    violations: tuple[Violation, ...]
    explanatory: JsonMapping

    def __post_init__(self) -> None:
        """Freeze all report mappings while retaining typed row objects."""
        for name in (
            "baseline_source",
            "candidate_source",
            "inventory",
            "explanatory",
        ):
            object.__setattr__(
                self,
                name,
                _freeze_mapping(
                    cast(Mapping[str, object], getattr(self, name))
                ),
            )
        for name in ("exact_surfaces", "palette", "cycles", "cmaps_256"):
            value = cast(Mapping[str, object], getattr(self, name))
            object.__setattr__(
                self, name, MappingProxyType(dict(sorted(value.items())))
            )
        object.__setattr__(
            self,
            "taxonomy",
            MappingProxyType(dict(sorted(self.taxonomy.items()))),
        )

    @property
    def total_exact_mismatches(self) -> int:
        """Return mismatched leaves across all 18 exact surfaces."""
        return sum(item.mismatch_count for item in self.exact_surfaces.values())

    @property
    def total_hex_mismatches(self) -> int:
        """Return mismatched row indices across visualized hex surfaces."""
        return sum(
            row.mismatch_count
            for rows in (self.palette, self.cycles, self.cmaps_256)
            for row in rows.values()
        )

    def to_payload(self) -> dict[str, object]:
        """Return the entire strict JSON report as fresh containers."""
        return {
            "baseline_source": _thaw(self.baseline_source),
            "candidate_source": _thaw(self.candidate_source),
            "cmaps_256": {
                name: row.to_payload() for name, row in self.cmaps_256.items()
            },
            "cycles": {
                name: row.to_payload() for name, row in self.cycles.items()
            },
            "exact_surfaces": {
                name: item.to_payload()
                for name, item in self.exact_surfaces.items()
            },
            "explanatory": _thaw(self.explanatory),
            "inventory": _thaw(self.inventory),
            "palette": {
                name: row.to_payload() for name, row in self.palette.items()
            },
            "passed": self.passed,
            "quality": self.quality.to_payload(),
            "schema": self.schema,
            "taxonomy": dict(self.taxonomy),
            "total_exact_mismatches": self.total_exact_mismatches,
            "total_hex_mismatches": self.total_hex_mismatches,
            "violations": [item.to_payload() for item in self.violations],
        }

    def to_json(self) -> str:
        """Serialize deterministic UTF-8-compatible strict JSON text."""
        return (
            json.dumps(
                self.to_payload(),
                ensure_ascii=False,
                allow_nan=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )


def _json_pointer_token(value: object) -> str:
    """Escape one RFC 6901 JSON-pointer token."""
    return str(value).replace("~", "~0").replace("/", "~1")


def _mismatch_leaf(
    path: str, baseline: object, candidate: object
) -> ExactMismatch:
    """Construct one leaf mismatch with explicit presence flags."""
    baseline_present = baseline is not _MISSING
    candidate_present = candidate is not _MISSING
    return ExactMismatch(
        path=path,
        baseline_present=baseline_present,
        candidate_present=candidate_present,
        baseline=None if not baseline_present else _freeze(baseline),
        candidate=None if not candidate_present else _freeze(candidate),
    )


def _walk_exact(
    baseline: object, candidate: object, path: str
) -> list[ExactMismatch]:
    """Recursively diff JSON data while flattening absent subtrees to leaves."""
    if baseline is _MISSING or candidate is _MISSING:
        present = candidate if baseline is _MISSING else baseline
        if isinstance(present, Mapping) and present:
            result: list[ExactMismatch] = []
            for key in sorted(present, key=str):
                child = f"{path}/{_json_pointer_token(key)}"
                result.extend(
                    _walk_exact(
                        _MISSING if baseline is _MISSING else present[key],
                        present[key] if baseline is _MISSING else _MISSING,
                        child,
                    )
                )
            return result
        if (
            isinstance(present, Sequence)
            and not isinstance(present, (str, bytes))
            and present
        ):
            result = []
            for index, item in enumerate(present):
                result.extend(
                    _walk_exact(
                        _MISSING if baseline is _MISSING else item,
                        item if baseline is _MISSING else _MISSING,
                        f"{path}/{index}",
                    )
                )
            return result
        return [_mismatch_leaf(path, baseline, candidate)]

    if isinstance(baseline, Mapping) and isinstance(candidate, Mapping):
        result = []
        for key in sorted(set(baseline) | set(candidate), key=str):
            result.extend(
                _walk_exact(
                    baseline.get(key, _MISSING),
                    candidate.get(key, _MISSING),
                    f"{path}/{_json_pointer_token(key)}",
                )
            )
        return result
    if (
        isinstance(baseline, Sequence)
        and not isinstance(baseline, (str, bytes))
        and isinstance(candidate, Sequence)
        and not isinstance(candidate, (str, bytes))
    ):
        result = []
        for index in range(max(len(baseline), len(candidate))):
            result.extend(
                _walk_exact(
                    baseline[index] if index < len(baseline) else _MISSING,
                    candidate[index] if index < len(candidate) else _MISSING,
                    f"{path}/{index}",
                )
            )
        return result
    if type(baseline) is not type(candidate) or baseline != candidate:
        return [_mismatch_leaf(path, baseline, candidate)]
    return []


def compare_exact_surfaces(
    baseline: CatalogSnapshot, candidate: CatalogSnapshot
) -> Mapping[str, ExactSurfaceComparison]:
    """Compare every normalized exact compatibility surface."""
    old = baseline.exact_payload()
    new = candidate.exact_payload()
    if tuple(old) != tuple(new):
        raise ValueError("catalog snapshots declare different exact surfaces")
    result: dict[str, ExactSurfaceComparison] = {}
    for surface in old:
        mismatches = tuple(
            sorted(
                _walk_exact(old[surface], new[surface], f"/{surface}"),
                key=lambda item: item.path,
            )
        )
        result[surface] = ExactSurfaceComparison(
            surface=surface,
            baseline_sha256=oracle.canonical_json_sha256(old[surface]),
            candidate_sha256=oracle.canonical_json_sha256(new[surface]),
            mismatches=mismatches,
        )
    return MappingProxyType(result)


def _strict_rgb(color: object) -> oracle.Rgb | None:
    """Parse a strict hex leaf, returning ``None`` for candidate invalidity."""
    if not isinstance(color, str) or _HEX_PATTERN.fullmatch(color) is None:
        return None
    try:
        return oracle.hex_to_srgb(color)
    except oracle.OracleValidationError:
        return None


def _summarize(values: Sequence[float]) -> MaybeSummary:
    """Summarize valid non-empty values and preserve undefined as null."""
    return oracle.summarize_numeric(values) if values else None


def _gray_hex(rgb: oracle.Rgb) -> str:
    """Encode the same modeled relative CIE Y as a neutral nominal-sRGB gray."""
    y_value = oracle.relative_y_srgb_d65(rgb)
    channel = oracle.linear_channel_to_srgb(y_value)
    return oracle.srgb_to_hex((channel, channel, channel))


def _row_profile(row: Sequence[str]) -> RowProfile:
    """Compute nullable per-stop profiles without rejecting candidate rows."""
    rgb_values = [_strict_rgb(color) for color in row]
    oklab_l: list[float | None] = []
    relative_y: list[float | None] = []
    grayscale: list[str | None] = []
    cvd: dict[str, list[str | None]] = {mode: [] for mode in _CVD_MODES}
    for color, rgb in zip(row, rgb_values, strict=True):
        if rgb is None:
            oklab_l.append(None)
            relative_y.append(None)
            grayscale.append(None)
            for mode in _CVD_MODES:
                cvd[mode].append(None)
            continue
        oklab_l.append(oracle.srgb_to_oklab(rgb)[0])
        relative_y.append(oracle.relative_y_srgb_d65(rgb))
        grayscale.append(_gray_hex(rgb))
        for mode in _CVD_MODES:
            cvd[mode].append(oracle.simulate_cvd_hex(color, mode))
    neighbor: list[float | None] = []
    for first, second in pairwise(rgb_values):
        neighbor.append(
            None
            if first is None or second is None
            else oracle.delta_e_ok(first, second)
        )
    return RowProfile(
        oklab_l=tuple(oklab_l),
        relative_y=tuple(relative_y),
        neighbor_delta_e_ok=tuple(neighbor),
        grayscale_hex=tuple(grayscale),
        cvd_hex={mode: tuple(values) for mode, values in cvd.items()},
    )


def _compare_hex_row(
    name: str,
    kind: str,
    baseline_row: Sequence[str],
    candidate_row: Sequence[str],
    *,
    baseline_preview: Sequence[str] | None = None,
    candidate_preview: Sequence[str] | None = None,
) -> HexRowComparison:
    """Compare one row with independent raw color and profile diagnostics."""
    old = tuple(baseline_row)
    new = tuple(candidate_row)
    mismatch_indices = tuple(
        index
        for index in range(max(len(old), len(new)))
        if index >= len(old) or index >= len(new) or old[index] != new[index]
    )
    delta_ok: list[float] = []
    delta_00: list[float] = []
    signed_y: list[float] = []
    absolute_y: list[float] = []
    light_delta: list[float] = []
    dark_delta: list[float] = []
    cvd_delta: dict[str, list[float]] = {mode: [] for mode in _CVD_MODES}
    light = oracle.hex_to_srgb("#ffffff")
    dark = oracle.hex_to_srgb("#1e1e1e")
    for old_color, new_color in zip(old, new, strict=False):
        old_rgb = _strict_rgb(old_color)
        new_rgb = _strict_rgb(new_color)
        if old_rgb is None or new_rgb is None:
            continue
        delta_ok.append(oracle.delta_e_ok(old_rgb, new_rgb))
        delta_00.append(oracle.ciede2000_rgb(old_rgb, new_rgb))
        y_delta = oracle.relative_y_srgb_d65(
            new_rgb
        ) - oracle.relative_y_srgb_d65(old_rgb)
        signed_y.append(y_delta)
        absolute_y.append(abs(y_delta))
        light_delta.append(
            oracle.wcag_contrast_ratio(new_rgb, light)
            - oracle.wcag_contrast_ratio(old_rgb, light)
        )
        dark_delta.append(
            oracle.wcag_contrast_ratio(new_rgb, dark)
            - oracle.wcag_contrast_ratio(old_rgb, dark)
        )
        for mode in _CVD_MODES:
            old_simulated = oracle.hex_to_srgb(
                oracle.simulate_cvd_hex(old_color, mode)
            )
            new_simulated = oracle.hex_to_srgb(
                oracle.simulate_cvd_hex(new_color, mode)
            )
            cvd_delta[mode].append(
                oracle.ciede2000_rgb(old_simulated, new_simulated)
            )
    return HexRowComparison(
        name=name,
        kind=kind,
        baseline_hex=old,
        candidate_hex=new,
        baseline_preview_hex=tuple(
            old if baseline_preview is None else baseline_preview
        ),
        candidate_preview_hex=tuple(
            new if candidate_preview is None else candidate_preview
        ),
        mismatch_indices=mismatch_indices,
        delta_e_ok=_summarize(delta_ok),
        delta_e00=_summarize(delta_00),
        signed_delta_y=_summarize(signed_y),
        absolute_delta_y=_summarize(absolute_y),
        light_contrast_delta=_summarize(light_delta),
        dark_contrast_delta=_summarize(dark_delta),
        cvd_delta_e00={
            mode: _summarize(values) for mode, values in cvd_delta.items()
        },
        baseline_profile=_row_profile(old),
        candidate_profile=_row_profile(new),
    )


def _as_mapping(value: object) -> Mapping[str, object] | None:
    """Return a string-keyed mapping or ``None`` for malformed metrics."""
    if not isinstance(value, Mapping) or not all(
        isinstance(key, str) for key in value
    ):
        return None
    return cast(Mapping[str, object], value)


def _number(value: object) -> float | None:
    """Return one finite non-boolean number or ``None``."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _display_missing(value: object) -> object:
    """Normalize the private missing marker for report serialization."""
    return None if value is _MISSING else _freeze(value)


def _gate_surface(metric: str) -> str:
    """Derive the comparison surface from one shared gate metric path."""
    parts = metric.strip("/").split("/")
    if metric == "/candidate":
        return "candidate"
    if len(parts) >= 2 and parts[0] == "metrics":
        if parts[1] == "topology" and len(parts) >= 3:
            return f"topology.{parts[2]}"
        return parts[1]
    if len(parts) >= 2 and parts[0] == "row_contracts":
        return f"row_contracts.{parts[1]}"
    return "quality"


def _adapt_gate_violation(item: gates.GateViolation) -> Violation:
    """Adapt one shared raw gate decision to the comparison report schema."""
    if item.metric == "/candidate":
        code = "candidate_quality_invalid"
    elif item.rule == "valid":
        code = "quality_metric_invalid"
    else:
        code = "quality_regression"
    return Violation(
        code=code,
        surface=_gate_surface(item.metric),
        asset=item.asset,
        path=item.metric,
        message=item.message,
        baseline=item.allowed,
        candidate=item.observed,
    )


def compare_quality_metrics(
    baseline_metrics: Mapping[str, object],
    candidate_metrics: Mapping[str, object],
    taxonomy: Mapping[str, str],
) -> tuple[Violation, ...]:
    """Adapt the shared raw-value gate policy into report violations."""
    return tuple(
        sorted(
            _adapt_gate_violation(item)
            for item in gates.evaluate_quality_metrics(
                baseline_metrics, candidate_metrics, taxonomy
            )
        )
    )


def _catalog_for_oracle(snapshot: CatalogSnapshot) -> dict[str, object]:
    """Translate Python snapshot naming to the frozen oracle schema."""
    payload = snapshot.exact_payload()
    payload["cmaps256"] = payload.pop("cmaps_256")
    return payload


def _quality_fixture() -> dict[str, object]:
    """Load and validate the immutable quality/reference fixture by raw hash."""
    return gates.load_quality_baseline()


# Same window as ``_gates._GATE_REL_TOL``; see that comment for how it was
# measured. It lives here rather than in the oracle because the oracle pins its
# own source SHA-256 against the quality fixture -- adding a helper there would
# be exactly the self-modification that pin exists to prevent.
QUALITY_REL_TOL = 1e-12
QUALITY_ABS_TOL = 1e-15


def matches_recorded_quality(measured: object, recorded: object) -> bool:
    """Compare a recomputed quality payload against a recorded one.

    Structure, keys, lengths, strings and booleans are compared exactly; only
    numbers get a tolerance. The comparison still answers whether the catalog
    changed, without requiring two architectures to agree on a last bit of a
    derived double.
    """
    if isinstance(measured, Mapping) or isinstance(recorded, Mapping):
        if not (
            isinstance(measured, Mapping) and isinstance(recorded, Mapping)
        ):
            return False
        if set(measured) != set(recorded):
            return False
        return all(
            matches_recorded_quality(measured[key], recorded[key])
            for key in measured
        )
    if isinstance(measured, str) or isinstance(recorded, str):
        return measured == recorded
    if isinstance(measured, bool) or isinstance(recorded, bool):
        return measured is recorded
    if isinstance(measured, Sequence) or isinstance(recorded, Sequence):
        if not (
            isinstance(measured, Sequence) and isinstance(recorded, Sequence)
        ):
            return False
        if len(measured) != len(recorded):
            return False
        return all(
            matches_recorded_quality(left, right)
            for left, right in zip(measured, recorded, strict=True)
        )
    if isinstance(measured, (int, float)) and isinstance(
        recorded, (int, float)
    ):
        return math.isclose(
            float(measured),
            float(recorded),
            rel_tol=QUALITY_REL_TOL,
            abs_tol=QUALITY_ABS_TOL,
        )
    return measured == recorded


def _quality_comparison(
    baseline: CatalogSnapshot, candidate: CatalogSnapshot
) -> tuple[QualityComparison, Mapping[str, tuple[str, ...]]]:
    """Recompute the baseline, compute candidate quality, then apply gates."""
    fixture = _quality_fixture()
    literal_inputs = cast(Mapping[str, object], fixture["literal_inputs"])
    preview_value = literal_inputs["cmaps_preview_32"]
    preview_mapping = _as_mapping(preview_value)
    if preview_mapping is None:
        raise oracle.OracleValidationError(
            "quality fixture previews are not a mapping"
        )
    baseline_previews = MappingProxyType(
        {
            name: tuple(cast(Sequence[str], preview_mapping[name]))
            for name in sorted(preview_mapping)
        }
    )
    expected_metrics = cast(Mapping[str, object], fixture["metrics"])
    expected_extrema = cast(Mapping[str, object], fixture["global_extrema"])
    recomputed_metrics, recomputed_extrema = oracle.compute_catalog_quality(
        _catalog_for_oracle(baseline), baseline_previews
    )
    baseline_matches = matches_recorded_quality(
        recomputed_metrics, expected_metrics
    ) and matches_recorded_quality(recomputed_extrema, expected_extrema)
    if not baseline_matches:
        raise oracle.OracleValidationError(
            "recomputed v5 quality differs from the pinned fixture"
        )

    gate_report = gates.evaluate_catalog(candidate, fixture)
    candidate_metrics = gate_report.candidate_metrics
    candidate_extrema = gate_report.candidate_global_extrema
    quality_violations = tuple(
        sorted(_adapt_gate_violation(item) for item in gate_report.violations)
    )
    policy = cast(Mapping[str, object], fixture["policy"])
    quality = QualityComparison(
        baseline_matches_fixture=baseline_matches,
        baseline_metrics=expected_metrics,
        candidate_metrics=candidate_metrics,
        baseline_global_extrema=expected_extrema,
        candidate_global_extrema=candidate_extrema,
        policy=policy,
        fixture_sha256=gates.QUALITY_FIXTURE_SHA256,
        oracle_sha256=gates.QUALITY_ORACLE_SHA256,
        violations=tuple(sorted(quality_violations)),
    )
    return quality, baseline_previews


def _exact_violations(
    comparisons: Mapping[str, ExactSurfaceComparison],
) -> tuple[Violation, ...]:
    """Promote exact mismatches into the report's unified violation list."""
    result: list[Violation] = []
    for surface, comparison in comparisons.items():
        for mismatch in comparison.mismatches:
            path_parts = mismatch.path.strip("/").split("/")
            asset = path_parts[1] if len(path_parts) > 1 else surface
            result.append(
                Violation(
                    code="exact_mismatch",
                    surface=surface,
                    asset=asset,
                    path=mismatch.path,
                    message="candidate leaf differs from frozen v5",
                    baseline=mismatch.baseline,
                    candidate=mismatch.candidate,
                )
            )
    return tuple(sorted(result))


def _row_comparisons(
    baseline_rows: Mapping[str, Sequence[str]],
    candidate_rows: Mapping[str, Sequence[str]],
    *,
    taxonomy: Mapping[str, str],
    default_kind: str,
    baseline_previews: Mapping[str, Sequence[str]] | None = None,
    candidate_previews: Mapping[str, Sequence[str]] | None = None,
) -> Mapping[str, HexRowComparison]:
    """Build deterministic comparisons for the union of two named row maps."""
    result: dict[str, HexRowComparison] = {}
    for name in sorted(set(baseline_rows) | set(candidate_rows)):
        result[name] = _compare_hex_row(
            name,
            taxonomy.get(name, default_kind),
            baseline_rows.get(name, ()),
            candidate_rows.get(name, ()),
            baseline_preview=(
                None
                if baseline_previews is None
                else baseline_previews.get(name, ())
            ),
            candidate_preview=(
                None
                if candidate_previews is None
                else candidate_previews.get(name, ())
            ),
        )
    return MappingProxyType(result)


def _topology_diagnostic(
    kind: str, row: Sequence[str], profile: RowProfile
) -> dict[str, object]:
    """Summarize taxonomy-specific topology without producing gate decisions."""
    valid_y = [
        (index, value)
        for index, value in enumerate(profile.relative_y)
        if value is not None and math.isfinite(value)
    ]
    neighbor = [
        value
        for value in profile.neighbor_delta_e_ok
        if value is not None and math.isfinite(value)
    ]
    result: dict[str, object] = {
        "count": len(row),
        "neighbor_delta_e_ok": _summary_payload(_summarize(neighbor)),
        "relative_y_span": (
            None
            if not valid_y
            else max(value for _, value in valid_y)
            - min(value for _, value in valid_y)
        ),
        "valid_relative_y_count": len(valid_y),
    }
    if len(valid_y) >= 2:
        result["endpoint_delta_y"] = valid_y[-1][1] - valid_y[0][1]
    else:
        result["endpoint_delta_y"] = None
    try:
        if kind in {"sequential", "multi-hue"}:
            y_values = tuple(profile.relative_y)
            l_values = tuple(profile.oklab_l)
            if (
                len(y_values) < 2
                or any(value is None for value in y_values)
                or any(value is None for value in l_values)
            ):
                raise ValueError("ordered topology requires valid color rows")
            finite_y = cast(tuple[float, ...], y_values)
            finite_l = cast(tuple[float, ...], l_values)
            direction = (
                "increasing" if finite_y[-1] >= finite_y[0] else "decreasing"
            )
            sign = 1.0 if direction == "increasing" else -1.0
            oriented_y = [
                sign * (second - first) for first, second in pairwise(finite_y)
            ]
            oriented_l = [
                sign * (second - first) for first, second in pairwise(finite_l)
            ]
            result.update(
                {
                    "direction": direction,
                    "oklab_l_monotonic": min(oriented_l) >= 0.0,
                    "oriented_delta_l": _summary_payload(
                        _summarize(oriented_l)
                    ),
                    "oriented_delta_y": _summary_payload(
                        _summarize(oriented_y)
                    ),
                    "relative_y_monotonic": min(oriented_y) >= 0.0,
                    "y_span": max(finite_y) - min(finite_y),
                }
            )
        elif kind == "diverging":
            result.update(oracle.diverging_topology(tuple(row)))
        elif kind == "cyclic":
            result.update(oracle.cyclic_topology(tuple(row)))
    except Exception as error:  # noqa: BLE001 - non-gating diagnostic
        result["diagnostic_error"] = f"{type(error).__name__}: {error}"
    return result


def _unlocked_explanatory_rows(candidate: CatalogSnapshot) -> dict[str, object]:
    """Compare locked and direct-OKLCH previews as non-gating diagnostics."""
    rows: dict[str, object] = {}
    names = sorted(
        set(candidate.cmaps_preview_32)
        | set(candidate.cmaps_unlocked_preview_32)
    )
    for name in names:
        locked_hex = tuple(candidate.cmaps_preview_32.get(name, ()))
        direct_hex = tuple(candidate.cmaps_unlocked_preview_32.get(name, ()))
        locked_profile = _row_profile(locked_hex)
        direct_profile = _row_profile(direct_hex)
        delta_ok: list[float] = []
        signed_y: list[float] = []
        absolute_y: list[float] = []
        for locked_color, direct_color in zip(
            locked_hex, direct_hex, strict=False
        ):
            locked_rgb = _strict_rgb(locked_color)
            direct_rgb = _strict_rgb(direct_color)
            if locked_rgb is None or direct_rgb is None:
                continue
            delta_ok.append(oracle.delta_e_ok(locked_rgb, direct_rgb))
            delta_y = oracle.relative_y_srgb_d65(
                direct_rgb
            ) - oracle.relative_y_srgb_d65(locked_rgb)
            signed_y.append(delta_y)
            absolute_y.append(abs(delta_y))
        kind = candidate.taxonomy.get(name, "unknown")
        rows[name] = {
            "absolute_delta_y": _summary_payload(_summarize(absolute_y)),
            "delta_e_ok": _summary_payload(_summarize(delta_ok)),
            "direct_hex": list(direct_hex),
            "direct_profile": direct_profile.to_payload(),
            "locked_hex": list(locked_hex),
            "locked_profile": locked_profile.to_payload(),
            "signed_delta_y": _summary_payload(_summarize(signed_y)),
            "topology": {
                "kind": kind,
                "locked": _topology_diagnostic(
                    kind, locked_hex, locked_profile
                ),
                "direct": _topology_diagnostic(
                    kind, direct_hex, direct_profile
                ),
            },
        }
    return rows


def _source_payload(
    snapshot: CatalogSnapshot, *, baseline: bool
) -> dict[str, object]:
    """Return catalog provenance without treating it as exact surface data."""
    payload: dict[str, object] = {
        "baseline_commit": snapshot.baseline_commit,
        "canonical_hashes": dict(snapshot.canonical_hashes),
        "catalog_schema": snapshot.schema,
        "source_hashes": dict(snapshot.source_hashes),
    }
    if baseline:
        payload["compatibility_raw_sha256"] = (
            "bc0b9fa8a5d888b60808de48dbdadb1ff25690e435a7bcc44aa63d31ce742818"
        )
    return payload


def compare_catalog(
    baseline: CatalogSnapshot, candidate: CatalogSnapshot
) -> ComparisonReport:
    """Compare a pinned v5 catalog with a live compiled candidate catalog."""
    exact = compare_exact_surfaces(baseline, candidate)
    quality, baseline_previews = _quality_comparison(baseline, candidate)
    palette = _row_comparisons(
        baseline.palette,
        candidate.palette,
        taxonomy={},
        default_kind="sequential",
    )
    cycles = _row_comparisons(
        baseline.cycles,
        candidate.cycles,
        taxonomy={},
        default_kind="qualitative",
    )
    cmaps = _row_comparisons(
        baseline.cmaps_256,
        candidate.cmaps_256,
        taxonomy=candidate.taxonomy,
        default_kind="unknown",
        baseline_previews=baseline_previews,
        candidate_previews=candidate.cmaps_preview_32,
    )
    violations = tuple(sorted((*_exact_violations(exact), *quality.violations)))
    inventory = {
        "baseline": dict(baseline.inventory),
        "candidate": dict(candidate.inventory),
        "visualized": {
            "palette_families": len(palette),
            "cycles": len(cycles),
            "continuous_colormaps": len(cmaps),
        },
    }
    explanatory = {
        "direct_oklch_unlocked": {
            "available": (
                candidate.cmaps_unlocked_preview_error is None
                and bool(candidate.cmaps_unlocked_preview_32)
            ),
            "error": candidate.cmaps_unlocked_preview_error,
            "gate_input": False,
            "normative": False,
            "rows": _unlocked_explanatory_rows(candidate),
        }
    }
    return ComparisonReport(
        schema=_COMPARISON_SCHEMA,
        passed=not violations,
        baseline_source=_source_payload(baseline, baseline=True),
        candidate_source=_source_payload(candidate, baseline=False),
        inventory=inventory,
        exact_surfaces=exact,
        palette=palette,
        cycles=cycles,
        cmaps_256=cmaps,
        taxonomy=candidate.taxonomy,
        quality=quality,
        violations=violations,
        explanatory=explanatory,
    )


def _safe_hex(value: str | None) -> tuple[str, str]:
    """Return a CSS-safe color and escaped diagnostic label."""
    if isinstance(value, str) and _HEX_PATTERN.fullmatch(value):
        return value.lower(), value
    return "#000000", "invalid color" if value is None else value


def _color_strip(
    values: Sequence[str | None], *, marker: str, label: str
) -> str:
    """Render one literal inline color strip with no stylesheet interpolation."""
    chips: list[str] = []
    for value in values:
        safe, title = _safe_hex(value)
        chips.append(
            f'<span style="background:{safe}" title="{html.escape(title, quote=True)}"></span>'
        )
    return (
        f'<div class="strip-row" data-strip="{html.escape(marker, quote=True)}">'
        f'<span class="strip-label">{html.escape(label)}</span>'
        f'<span class="strip">{"".join(chips)}</span></div>'
    )


def _profile_points(
    values: Sequence[float | None], *, low: float, high: float
) -> str:
    """Map nullable raw values into one deterministic 100-by-32 SVG polyline."""
    span = high - low
    denominator = max(len(values) - 1, 1)
    points: list[str] = []
    for index, value in enumerate(values):
        if value is None or not math.isfinite(value):
            continue
        x_value = 100.0 * index / denominator
        y_value = 16.0 if span == 0.0 else 30.0 - 28.0 * (value - low) / span
        points.append(f"{x_value:.6f},{y_value:.6f}")
    return " ".join(points)


def _profile_panel(
    *,
    marker: str,
    label: str,
    baseline: Sequence[float | None],
    candidate: Sequence[float | None],
) -> str:
    """Render one old/new profile overlay as inline SVG."""
    finite = [
        value
        for values in (baseline, candidate)
        for value in values
        if value is not None and math.isfinite(value)
    ]
    if finite:
        low, high = min(finite), max(finite)
        old_points = _profile_points(baseline, low=low, high=high)
        new_points = _profile_points(candidate, low=low, high=high)
    else:
        old_points = new_points = ""
    return (
        f'<div class="profile" data-profile="{html.escape(marker, quote=True)}">'
        f'<span>{html.escape(label)}</span><svg viewBox="0 0 100 32" '
        'preserveAspectRatio="none" role="img">'
        f'<polyline class="old-line" points="{old_points}"></polyline>'
        f'<polyline class="new-line" points="{new_points}"></polyline>'
        "</svg></div>"
    )


def _diagnostic_hexes(value: object) -> tuple[str | None, ...]:
    """Return display-safe nullable hex inputs from explanatory JSON data."""
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return ()
    return tuple(item if isinstance(item, str) else None for item in value)


def _diagnostic_numbers(value: object) -> tuple[float | None, ...]:
    """Return finite nullable profile values from explanatory JSON data."""
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return ()
    result: list[float | None] = []
    for item in value:
        number = _number(item)
        result.append(number)
    return tuple(result)


def _diagnostic_profile(
    value: object, field_name: str
) -> tuple[float | None, ...]:
    """Read one nullable profile series from an explanatory row payload."""
    profile = _as_mapping(value)
    return (
        ()
        if profile is None
        else _diagnostic_numbers(profile.get(field_name, ()))
    )


def _unlocked_panels(report: ComparisonReport) -> str:
    """Render one locked-versus-direct panel for every candidate colormap."""
    section = _as_mapping(report.explanatory.get("direct_oklch_unlocked"))
    if section is None:
        return '<p class="empty">Direct OKLCH diagnostics unavailable.</p>'
    available = section.get("available", True)
    error = section.get("error")
    if available is False:
        detail = "" if error is None else f" ({html.escape(str(error))})"
        return (
            '<p class="empty" data-panel="unlocked-diagnostic-error">'
            f"Direct OKLCH diagnostics unavailable{detail}.</p>"
        )
    rows = _as_mapping(section.get("rows"))
    if not rows:
        return '<p class="empty">Direct OKLCH diagnostics unavailable.</p>'

    # Rendered marker contract:
    # data-strip="locked-direct32" data-strip="unlocked-direct32"
    # data-profile="lock-oklab-l" data-profile="lock-relative-y"
    # data-profile="lock-neighbor-delta-e"
    panels: list[str] = []
    for name, value in sorted(rows.items()):
        row = _as_mapping(value) or {}
        locked_hex = _diagnostic_hexes(row.get("locked_hex", ()))
        direct_hex = _diagnostic_hexes(row.get("direct_hex", ()))
        locked_profile = row.get("locked_profile", {})
        direct_profile = row.get("direct_profile", {})
        topology = _as_mapping(row.get("topology")) or {}
        kind = topology.get("kind", "unknown")
        panels.append(
            '<section class="explanatory" '
            'data-panel="luminance-lock-comparison">'
            f"<h3>{html.escape(name)} <small>{html.escape(str(kind))} · "
            "non-normative</small></h3>"
            + _color_strip(
                locked_hex, marker="locked-direct32", label="locked direct 32"
            )
            + _color_strip(
                direct_hex, marker="unlocked-direct32", label="direct OKLCH 32"
            )
            + '<div class="profiles">'
            + _profile_panel(
                marker="lock-oklab-l",
                label="OKLab L: locked → direct",
                baseline=_diagnostic_profile(locked_profile, "oklab_l"),
                candidate=_diagnostic_profile(direct_profile, "oklab_l"),
            )
            + _profile_panel(
                marker="lock-relative-y",
                label="modeled relative Y: locked → direct",
                baseline=_diagnostic_profile(locked_profile, "relative_y"),
                candidate=_diagnostic_profile(direct_profile, "relative_y"),
            )
            + _profile_panel(
                marker="lock-neighbor-delta-e",
                label="neighbor ΔEOK: locked → direct",
                baseline=_diagnostic_profile(
                    locked_profile, "neighbor_delta_e_ok"
                ),
                candidate=_diagnostic_profile(
                    direct_profile, "neighbor_delta_e_ok"
                ),
            )
            + "</div></section>"
        )
    return "".join(panels)


def _summary_text(summary: MaybeSummary) -> str:
    """Format a compact human summary while retaining raw JSON evidence."""
    if summary is None:
        return "undefined"
    return (
        f"max {summary.max:.6g}; p95 {summary.p95:.6g}; mean {summary.mean:.6g}"
    )


def _palette_panel(row: HexRowComparison) -> str:
    """Render one old/new/difference palette family."""
    differences: list[str] = []
    for index in range(max(len(row.baseline_hex), len(row.candidate_hex))):
        old = row.baseline_hex[index] if index < len(row.baseline_hex) else None
        new = (
            row.candidate_hex[index] if index < len(row.candidate_hex) else None
        )
        changed = old != new
        differences.append(
            '<span class="diff-chip '
            + ("changed" if changed else "same")
            + f'" title="index {index}: {html.escape(str(old))} → '
            + f'{html.escape(str(new))}"></span>'
        )
    return (
        '<section class="palette-panel">'
        f"<h3>{html.escape(row.name)} <small>{row.mismatch_count} mismatch</small></h3>"
        + _color_strip(row.baseline_hex, marker="palette-v5", label="v5")
        + _color_strip(row.candidate_hex, marker="palette-v6", label="v6")
        + '<div class="strip-row" data-strip="palette-difference">'
        '<span class="strip-label">difference</span>'
        f'<span class="strip">{"".join(differences)}</span></div></section>'
    )


def _cmap_panel(row: HexRowComparison) -> str:
    """Render one complete continuous-colormap diagnostic panel."""
    preview_profile = _row_profile(row.candidate_preview_hex)
    baseline_preview_profile = _row_profile(row.baseline_preview_hex)
    topology = ""
    if row.kind == "diverging":
        old_y = row.baseline_profile.relative_y
        new_y = row.candidate_profile.relative_y
        old_mirror = tuple(
            None
            if old_y[index] is None or old_y[-index - 1] is None
            else abs(cast(float, old_y[index]) - cast(float, old_y[-index - 1]))
            for index in range(len(old_y) // 2)
        )
        new_mirror = tuple(
            None
            if new_y[index] is None or new_y[-index - 1] is None
            else abs(cast(float, new_y[index]) - cast(float, new_y[-index - 1]))
            for index in range(len(new_y) // 2)
        )
        topology = (
            '<div class="topology" data-panel="diverging-mirror">'
            + _profile_panel(
                marker="mirror-y",
                label="mirrored arm |ΔY|",
                baseline=old_mirror,
                candidate=new_mirror,
            )
            + "</div>"
        )
    elif row.kind == "cyclic":
        old_window = (*row.baseline_hex[-4:], *row.baseline_hex[:4])
        new_window = (*row.candidate_hex[-4:], *row.candidate_hex[:4])
        topology = (
            '<div class="topology" data-panel="cyclic-seam">'
            + _color_strip(
                old_window, marker="cyclic-seam-v5", label="v5 seam -4…+4"
            )
            + _color_strip(
                new_window, marker="cyclic-seam-v6", label="v6 seam -4…+4"
            )
            + "</div>"
        )
    return (
        '<section class="cmap-panel">'
        f"<h3>{html.escape(row.name)} <small>{html.escape(row.kind)} · "
        f"{row.mismatch_count} mismatch</small></h3>"
        + _color_strip(
            row.baseline_preview_hex, marker="v5-direct32", label="v5 direct 32"
        )
        + _color_strip(
            row.candidate_preview_hex,
            marker="v6-direct32",
            label="v6 direct 32",
        )
        + _color_strip(
            baseline_preview_profile.grayscale_hex,
            marker="grayscale-v5",
            label="v5 modeled-Y neutral",
        )
        + _color_strip(
            preview_profile.grayscale_hex,
            marker="grayscale",
            label="modeled-Y neutral",
        )
        + _color_strip(
            baseline_preview_profile.cvd_hex["protan"],
            marker="protan-v5",
            label="v5 protan",
        )
        + _color_strip(
            preview_profile.cvd_hex["protan"], marker="protan", label="protan"
        )
        + _color_strip(
            baseline_preview_profile.cvd_hex["deutan"],
            marker="deutan-v5",
            label="v5 deutan",
        )
        + _color_strip(
            preview_profile.cvd_hex["deutan"], marker="deutan", label="deutan"
        )
        + _color_strip(
            baseline_preview_profile.cvd_hex["tritan"],
            marker="tritan-v5",
            label="v5 tritan",
        )
        + _color_strip(
            preview_profile.cvd_hex["tritan"], marker="tritan", label="tritan"
        )
        + '<div class="profiles">'
        + _profile_panel(
            marker="oklab-l",
            label="OKLab L",
            baseline=baseline_preview_profile.oklab_l,
            candidate=preview_profile.oklab_l,
        )
        + _profile_panel(
            marker="relative-y",
            label="modeled relative Y",
            baseline=baseline_preview_profile.relative_y,
            candidate=preview_profile.relative_y,
        )
        + _profile_panel(
            marker="neighbor-delta-e",
            label="neighbor ΔEOK",
            baseline=baseline_preview_profile.neighbor_delta_e_ok,
            candidate=preview_profile.neighbor_delta_e_ok,
        )
        + "</div>"
        + topology
        + '<p class="raw-summary">ΔEOK '
        + html.escape(_summary_text(row.delta_e_ok))
        + "; ΔE00 "
        + html.escape(_summary_text(row.delta_e00))
        + "; |ΔY| "
        + html.escape(_summary_text(row.absolute_delta_y))
        + "</p></section>"
    )


def _escaped_json(value: object) -> str:
    """Serialize one raw report value as deterministic, escaped JSON."""
    serialized = json.dumps(
        _thaw(value),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return html.escape(serialized, quote=True)


def _violations_panel(violations: Sequence[Violation]) -> str:
    """Render escaped violations, including hostile candidate text safely."""
    if not violations:
        return '<p class="empty">No violations.</p>'
    rows = [
        (
            "<tr>"
            f"<td>{html.escape(item.code)}</td>"
            f"<td>{html.escape(item.surface)}</td>"
            f"<td>{html.escape(item.asset)}</td>"
            f"<td><code>{html.escape(item.path)}</code></td>"
            f"<td>{html.escape(item.message)}</td>"
            f"<td><code>{_escaped_json(item.baseline)}</code></td>"
            f"<td><code>{_escaped_json(item.candidate)}</code></td>"
            "</tr>"
        )
        for item in violations
    ]
    return (
        "<table><thead><tr><th>code</th><th>surface</th><th>asset</th>"
        "<th>path</th><th>decision</th><th>baseline / allowed</th>"
        "<th>candidate / observed</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _flatten_source(prefix: str, value: object) -> list[tuple[str, str]]:
    """Flatten nested provenance into escaped-table-friendly string leaves."""
    if isinstance(value, Mapping):
        rows: list[tuple[str, str]] = []
        for key, item in sorted(value.items(), key=lambda pair: str(pair[0])):
            child = f"{prefix}.{key}" if prefix else str(key)
            rows.extend(_flatten_source(child, item))
        return rows
    rendered = json.dumps(_thaw(value), ensure_ascii=False, allow_nan=False)
    return [(prefix, rendered)]


def _source_table(report: ComparisonReport) -> str:
    """Render baseline/candidate provenance near the report decision."""
    rows: list[str] = []
    for side, payload in (
        ("baseline", report.baseline_source),
        ("candidate", report.candidate_source),
    ):
        for key, value in _flatten_source("", payload):
            rows.append(
                f'<tr data-source="{side}"><td>{side}</td>'
                f"<td>{html.escape(key)}</td><td><code>{html.escape(value)}</code></td></tr>"
            )
    return (
        "<table><thead><tr><th>source</th><th>field</th><th>literal value</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def _inventory_table(report: ComparisonReport) -> str:
    """Render baseline/candidate inventory and numeric deltas."""
    baseline = _as_mapping(report.inventory.get("baseline")) or {}
    candidate = _as_mapping(report.inventory.get("candidate")) or {}
    rows: list[str] = []
    for key in sorted(set(baseline) | set(candidate)):
        old = baseline.get(key, _MISSING)
        new = candidate.get(key, _MISSING)
        old_number = _number(old)
        new_number = _number(new)
        delta = (
            "—"
            if old_number is None or new_number is None
            else f"{new_number - old_number:+g}"
        )
        rows.append(
            f"<tr><td>{html.escape(key)}</td><td>{html.escape(str(_display_missing(old)))}</td>"
            f"<td>{html.escape(str(_display_missing(new)))}</td><td>{delta}</td></tr>"
        )
    return (
        "<table><thead><tr><th>inventory</th><th>v5</th><th>candidate</th>"
        "<th>delta</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _extrema_table(report: ComparisonReport) -> str:
    """Render raw before/after global quality extrema for worst-case review."""
    old_rows = dict(_flatten_source("", report.quality.baseline_global_extrema))
    new_rows = dict(
        _flatten_source("", report.quality.candidate_global_extrema)
    )
    rows = [
        (
            f"<tr><td>{html.escape(key)}</td>"
            f"<td><code>{html.escape(old_rows.get(key, 'missing'))}</code></td>"
            f"<td><code>{html.escape(new_rows.get(key, 'missing'))}</code></td></tr>"
        )
        for key in sorted(set(old_rows) | set(new_rows))
    ]
    return (
        "<table><thead><tr><th>worst-metric provenance</th><th>v5 raw</th>"
        "<th>candidate raw</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _exact_surface_table(report: ComparisonReport) -> str:
    """Render all visual and nonvisual exact-surface digests and counts."""
    rows = [
        (
            f'<tr data-exact-surface="{html.escape(name, quote=True)}">'
            f"<td>{html.escape(name)}</td>"
            f"<td><code>{item.baseline_sha256}</code></td>"
            f"<td><code>{item.candidate_sha256}</code></td>"
            f"<td>{item.mismatch_count}</td></tr>"
        )
        for name, item in report.exact_surfaces.items()
    ]
    return (
        "<table><thead><tr><th>surface</th><th>v5 SHA-256</th>"
        "<th>candidate SHA-256</th><th>mismatches</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def render_comparison_html(report: ComparisonReport) -> str:
    """Render a deterministic, fully offline standalone comparison document."""
    status = "PASS" if report.passed else "FAIL"
    status_class = "pass" if report.passed else "fail"
    palette_html = "".join(
        _palette_panel(row) for row in report.palette.values()
    )
    cycle_html = "".join(
        '<section class="cycle-panel">'
        f"<h3>{html.escape(row.name)} <small>{row.mismatch_count} mismatch</small></h3>"
        + _color_strip(row.baseline_hex, marker="cycle-v5", label="v5")
        + _color_strip(row.candidate_hex, marker="cycle-v6", label="v6")
        + "</section>"
        for row in report.cycles.values()
    )
    cmap_html = "".join(_cmap_panel(row) for row in report.cmaps_256.values())
    unlocked_html = _unlocked_panels(report)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>dartwork-mpl color-system comparison</title>
<style>
:root {{ color-scheme: light dark; --bg:#111318; --panel:#1c2028; --ink:#eef1f5; --muted:#aeb7c4; --line:#39414d; --ok:#35c57a; --bad:#ff6675; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; padding:28px; background:var(--bg); color:var(--ink); font:14px/1.45 ui-monospace, SFMono-Regular, Menlo, monospace; }}
main {{ max-width:1440px; margin:auto; }}
h1,h2,h3,p {{ margin-top:0; }}
h2 {{ margin-top:34px; border-bottom:1px solid var(--line); padding-bottom:8px; }}
h3 {{ display:flex; justify-content:space-between; gap:16px; font-size:14px; }}
small,.strip-label,.raw-summary,.empty {{ color:var(--muted); font-weight:400; }}
.hero,.palette-panel,.cycle-panel,.cmap-panel,.explanatory {{ background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:16px; margin:12px 0; }}
.hero {{ display:grid; grid-template-columns:auto 1fr; gap:12px 22px; align-items:center; }}
.badge {{ border-radius:999px; padding:8px 16px; font-size:18px; font-weight:800; }}
.badge.pass {{ background:var(--ok); color:#07150e; }} .badge.fail {{ background:var(--bad); color:#26070b; }}
.strip-row {{ display:grid; grid-template-columns:132px minmax(0,1fr); gap:10px; align-items:center; margin:5px 0; }}
.strip {{ display:flex; min-height:18px; overflow:hidden; border-radius:3px; border:1px solid #0008; }}
.strip > span {{ flex:1 1 0; min-width:1px; min-height:18px; }}
.diff-chip.same {{ background:#29313b; }} .diff-chip.changed {{ background:var(--bad); }}
.profiles {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px; margin-top:12px; }}
.profile span {{ color:var(--muted); }} .profile svg {{ display:block; width:100%; height:64px; background:#11151c; border:1px solid var(--line); }}
polyline {{ fill:none; vector-effect:non-scaling-stroke; stroke-width:1.4; }} .old-line {{ stroke:#8a94a3; }} .new-line {{ stroke:#4ec9ff; }}
.topology {{ border-left:3px solid #af87ff; color:var(--muted); padding:6px 10px; margin-top:10px; }}
table {{ width:100%; border-collapse:collapse; font-size:12px; }} th,td {{ border:1px solid var(--line); padding:7px; text-align:left; vertical-align:top; }}
code {{ color:#ffd580; }}
@media (max-width:800px) {{ body {{ padding:12px; }} .profiles {{ grid-template-columns:1fr; }} .strip-row {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body><main>
<h1>dartwork-mpl color-system comparison</h1>
<p>{html.escape(_MODELED_Y_LIMITATION)}</p>
<section class="hero"><span class="badge {status_class}">{status}</span>
<div><strong>{report.total_exact_mismatches}</strong> exact leaf mismatches ·
<strong>{report.total_hex_mismatches}</strong> visualized hex mismatches ·
<strong>{len(report.violations)}</strong> violations</div></section>
<h2>Source provenance</h2>{_source_table(report)}
<h2>Inventory delta</h2>{_inventory_table(report)}
<h2>Worst-metric summary</h2>{_extrema_table(report)}
<h2>Violations</h2>{_violations_panel(report.violations)}
<h2>Palette families ({len(report.palette)})</h2>{palette_html}
<h2>Cycles ({len(report.cycles)})</h2>{cycle_html}
<h2>Continuous colormaps ({len(report.cmaps_256)})</h2>{cmap_html}
<h2>Direct OKLCH with the modeled-relative-Y lock disabled</h2>{unlocked_html}
<h2>Exact compatibility surfaces</h2>{_exact_surface_table(report)}
</main></body></html>
"""
