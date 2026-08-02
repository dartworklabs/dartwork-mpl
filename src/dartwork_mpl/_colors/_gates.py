"""Shared raw-value release gates for the complete color catalog.

The build and comparison report both adapt the immutable decisions from this
module.  Gate policy therefore has one owner and never depends on generated
runtime tables.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from itertools import pairwise
from pathlib import Path
from types import MappingProxyType
from typing import Protocol, cast

from . import _compatibility_metrics as oracle
from . import _ssot

__all__ = [
    "QUALITY_BASELINE_SEMANTIC_SHA256",
    "QUALITY_FIXTURE_SHA256",
    "QUALITY_ORACLE_SHA256",
    "GateReport",
    "GateViolation",
    "check_all",
    "evaluate_catalog",
    "evaluate_quality_metrics",
    "gate_cycle",
    "gate_cyclic_cmap",
    "gate_div_cmap",
    "gate_ladder",
    "gate_seq_cmap",
    "load_quality_baseline",
]

_REPO_ROOT = Path(__file__).resolve().parents[3]
_QUALITY_PATH = (
    _REPO_ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "assets"
    / "2026-07-14-oklab-centered-color-system"
    / "color_v5_quality.json"
)
QUALITY_FIXTURE_SHA256 = (
    "326906a7ab05b48ec35f37d8e2a73931106fc03edde7db263e1e6735f3c95616"
)
QUALITY_BASELINE_SEMANTIC_SHA256 = (
    "09fc8b4afa269bd0e9ed7e4ac399430a66e6413988bf6e40ec6c2fbc6a964c6a"
)
QUALITY_ORACLE_SHA256 = (
    "52718f3bf19f2fc2e5c7b95ef3cfe6338335b684eea86cd4b55892ed03765548"
)
_ROW_CONTRACTS_SHA256 = (
    "d4a80515b3b2df5129de09b04b47df16b1751bd8fdb83064151150422ef1462a"
)
_SUMMARY_FIELDS = ("min", "p05", "p50", "p95", "max", "mean")
_MISSING = object()


class CatalogSnapshot(Protocol):
    """Structural input boundary shared with the independent catalog oracle."""

    @property
    def palette(self) -> Mapping[str, tuple[str, ...]]: ...

    @property
    def cycles(self) -> Mapping[str, tuple[str, ...]]: ...

    @property
    def cmaps_256(self) -> Mapping[str, tuple[str, ...]]: ...

    @property
    def cmaps_preview_32(self) -> Mapping[str, tuple[str, ...]]: ...

    @property
    def curated_rows(self) -> Mapping[str, tuple[str, ...]]: ...

    @property
    def dark_cycle(self) -> tuple[str, ...]: ...

    @property
    def discrete_hex(self) -> Mapping[str, Mapping[str, tuple[str, ...]]]: ...

    @property
    def taxonomy(self) -> Mapping[str, str]: ...

    def exact_payload(self) -> dict[str, object]:
        """Return the normalized exact compatibility surfaces."""
        ...


def _freeze(value: object) -> object:
    """Copy JSON-like gate diagnostics into deterministic immutable forms."""
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("gate mappings require string keys")
        return MappingProxyType(
            {str(key): _freeze(item) for key, item in sorted(value.items())}
        )
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(_freeze(item) for item in value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise TypeError(f"unsupported gate value: {type(value).__name__}")


@dataclass(frozen=True, slots=True, order=True)
class GateViolation:
    """One sortable gate failure expressed with raw finite decision values."""

    asset: str
    metric: str
    rule: str
    observed: float
    allowed: float
    message: str

    def __post_init__(self) -> None:
        """Normalize numeric inputs and reject rounded/non-finite sentinels."""
        for name in ("asset", "metric", "rule", "message"):
            if not isinstance(getattr(self, name), str):
                raise TypeError(f"{name} must be a string")
        for name in ("observed", "allowed"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be a finite raw number")
            normalized = float(value)
            if not math.isfinite(normalized):
                raise ValueError(f"{name} must be a finite raw number")
            object.__setattr__(self, name, normalized)


@dataclass(frozen=True, slots=True)
class GateReport:
    """Immutable shared gate result plus the independently computed metrics."""

    violations: tuple[GateViolation, ...]
    candidate_metrics: Mapping[str, object] = field(default_factory=dict)
    candidate_global_extrema: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Sort failures and detach all retained metric containers."""
        object.__setattr__(self, "violations", tuple(sorted(self.violations)))
        object.__setattr__(
            self,
            "candidate_metrics",
            cast(Mapping[str, object], _freeze(self.candidate_metrics)),
        )
        object.__setattr__(
            self,
            "candidate_global_extrema",
            cast(Mapping[str, object], _freeze(self.candidate_global_extrema)),
        )

    @property
    def passed(self) -> bool:
        """Return whether every shared quality and row-contract gate passed."""
        return not self.violations


def load_quality_baseline() -> dict[str, object]:
    """Load the raw-hash-pinned v5 quality fixture with oracle provenance."""
    return oracle.load_quality_payload(
        _QUALITY_PATH,
        expected_raw_sha256=QUALITY_FIXTURE_SHA256,
        expected_oracle_sha256=QUALITY_ORACLE_SHA256,
    )


def _plain_json_value(value: object) -> object:
    """Copy frozen accessor data into containers accepted by JSON hashing."""
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise RuntimeError("v6 row-contract authority has non-string keys")
        return {
            str(key): _plain_json_value(item)
            for key, item in sorted(value.items())
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_plain_json_value(item) for item in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise RuntimeError("v6 row-contract authority is not JSON-shaped")


def _load_row_contracts() -> Mapping[str, object]:
    """Load the independently hash-pinned v6 row-contract section."""
    payload = _ssot.load_color_v6_ssot()
    contracts = _as_mapping(payload.get("row_contracts"))
    section_hashes = _as_mapping(payload.get("section_hashes"))
    if contracts is None or section_hashes is None:
        raise RuntimeError("v6 row-contract authority is missing")
    actual = oracle.canonical_json_sha256(_plain_json_value(contracts))
    embedded = section_hashes.get("row_contracts")
    if actual != _ROW_CONTRACTS_SHA256 or embedded != _ROW_CONTRACTS_SHA256:
        raise RuntimeError("v6 row-contract authority SHA-256 differs")
    return contracts


def _as_mapping(value: object) -> Mapping[str, object] | None:
    """Return a string-keyed mapping or ``None`` for malformed gate input."""
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


def _pointer_token(value: str) -> str:
    """Escape one JSON-pointer token for stable metric paths."""
    return value.replace("~", "~0").replace("/", "~1")


def _failed_equality_values(
    baseline: object, candidate: object
) -> tuple[float, float]:
    """Represent arbitrary failed equality operands with finite raw values."""
    old = _number(baseline)
    new = _number(candidate)
    if old is not None and new is not None:
        return new, old
    if isinstance(baseline, bool) and isinstance(candidate, bool):
        return float(candidate), float(baseline)
    return 0.0, 1.0


def _append_violation(
    violations: list[GateViolation],
    *,
    asset: str,
    metric: str,
    observed: float,
    allowed: float,
    rule: str,
    message: str,
) -> None:
    """Append one validated raw-value failure."""
    violations.append(
        GateViolation(
            asset=asset,
            metric=metric,
            observed=observed,
            allowed=allowed,
            rule=rule,
            message=message,
        )
    )


def _gate_invalid(
    violations: list[GateViolation], *, asset: str, metric: str, message: str
) -> None:
    """Record a malformed required metric without non-finite sentinels."""
    _append_violation(
        violations,
        asset=asset,
        metric=metric,
        observed=0.0,
        allowed=1.0,
        rule="valid",
        message=message,
    )


def _gate_equal(
    violations: list[GateViolation],
    *,
    asset: str,
    metric: str,
    baseline: object,
    candidate: object,
) -> None:
    """Apply one exact raw equality gate with explicit missing semantics."""
    if baseline is _MISSING or candidate is _MISSING:
        _gate_invalid(
            violations,
            asset=asset,
            metric=metric,
            message="required quality metric is missing",
        )
        return
    if type(baseline) is type(candidate) and baseline == candidate:
        return
    observed, allowed = _failed_equality_values(baseline, candidate)
    _append_violation(
        violations,
        asset=asset,
        metric=metric,
        observed=observed,
        allowed=allowed,
        rule="==",
        message=(
            f"candidate value {candidate!r} must equal frozen value "
            f"{baseline!r}"
        ),
    )


def _gate_number(
    violations: list[GateViolation],
    *,
    asset: str,
    metric: str,
    baseline: object,
    candidate: object,
    relation: str,
    ceiling: float | None = None,
) -> None:
    """Apply one finite raw-number lower or upper bound."""
    old = _number(baseline)
    new = _number(candidate)
    if old is None or new is None:
        if baseline is None and candidate is None:
            return
        _gate_invalid(
            violations,
            asset=asset,
            metric=metric,
            message="gate operands must both be finite numbers or null",
        )
        return
    threshold = old if ceiling is None else min(old, ceiling)
    passed = new >= threshold if relation == ">=" else new <= threshold
    if passed:
        return
    comparator = "at least" if relation == ">=" else "at most"
    _append_violation(
        violations,
        asset=asset,
        metric=metric,
        observed=new,
        allowed=threshold,
        rule=relation,
        message=f"candidate raw value must be {comparator} {threshold!r}",
    )


def _gate_summary_leaves(
    violations: list[GateViolation],
    *,
    asset: str,
    metric: str,
    baseline: object,
    candidate: object,
    relation: str,
) -> None:
    """Gate every raw numeric leaf of one summary mapping."""
    old = _as_mapping(baseline)
    new = _as_mapping(candidate)
    if old is None or new is None:
        _gate_equal(
            violations,
            asset=asset,
            metric=metric,
            baseline=baseline,
            candidate=candidate,
        )
        return
    for field_name in _SUMMARY_FIELDS:
        _gate_number(
            violations,
            asset=asset,
            metric=f"{metric}/{field_name}",
            baseline=old.get(field_name, _MISSING),
            candidate=new.get(field_name, _MISSING),
            relation=relation,
        )


def _compare_ordered_record(
    violations: list[GateViolation],
    *,
    asset: str,
    metric: str,
    baseline: object,
    candidate: object,
    step_cv_ceiling: float | None,
    monotonic_floors: bool = True,
    absolute_quantized_y: bool = False,
) -> None:
    """Apply row shape, OKLab/Y topology, CV, and model diagnostics."""
    old = _as_mapping(baseline)
    new = _as_mapping(candidate)
    if old is None or new is None:
        _gate_invalid(
            violations,
            asset=asset,
            metric=metric,
            message="ordered quality record must be an object",
        )
        return
    for field_name in ("count", "degenerate_neighbor_steps"):
        _gate_equal(
            violations,
            asset=asset,
            metric=f"{metric}/{field_name}",
            baseline=old.get(field_name, _MISSING),
            candidate=new.get(field_name, _MISSING),
        )
    _gate_number(
        violations,
        asset=asset,
        metric=f"{metric}/step_cv",
        baseline=old.get("step_cv", _MISSING),
        candidate=new.get("step_cv", _MISSING),
        relation="<=",
        ceiling=step_cv_ceiling,
    )
    if absolute_quantized_y:
        quantization = _as_mapping(new.get("relative_y_quantization", _MISSING))
        quantization_metric = f"{metric}/relative_y_quantization/margin"
        if quantization is None:
            _gate_invalid(
                violations,
                asset=asset,
                metric=quantization_metric,
                message="required local 8-bit relative-Y record is missing",
            )
        else:
            margin = _number(quantization.get("margin", _MISSING))
            pair_index = quantization.get("worst_pair_index", _MISSING)
            if margin is None or (
                isinstance(pair_index, bool) or not isinstance(pair_index, int)
            ):
                _gate_invalid(
                    violations,
                    asset=asset,
                    metric=quantization_metric,
                    message="local 8-bit relative-Y record is malformed",
                )
            elif margin < 0.0:
                _append_violation(
                    violations,
                    asset=asset,
                    metric=quantization_metric,
                    observed=margin,
                    allowed=0.0,
                    rule=">=",
                    message=(
                        "candidate modeled-relative-Y ordering is impossible "
                        f"within the local 8-bit cells at pair {pair_index}"
                    ),
                )
    if not monotonic_floors:
        return
    _gate_equal(
        violations,
        asset=asset,
        metric=f"{metric}/direction",
        baseline=old.get("direction", _MISSING),
        candidate=new.get("direction", _MISSING),
    )
    for field_name in (
        "oriented_delta_y",
        "oriented_delta_l",
        "protan_oriented_delta_y",
        "deutan_oriented_delta_y",
        "tritan_oriented_delta_y",
    ):
        old_summary = _as_mapping(old.get(field_name, _MISSING))
        new_summary = _as_mapping(new.get(field_name, _MISSING))
        _gate_number(
            violations,
            asset=asset,
            metric=f"{metric}/{field_name}/min",
            baseline=(
                _MISSING
                if old_summary is None
                else old_summary.get("min", _MISSING)
            ),
            candidate=(
                _MISSING
                if new_summary is None
                else new_summary.get("min", _MISSING)
            ),
            relation=">=",
        )
    _gate_number(
        violations,
        asset=asset,
        metric=f"{metric}/y_span",
        baseline=old.get("y_span", _MISSING),
        candidate=new.get("y_span", _MISSING),
        relation=">=",
    )


def _compare_categorical_record(
    violations: list[GateViolation],
    *,
    asset: str,
    metric: str,
    baseline: object,
    candidate: object,
) -> None:
    """Gate independent categorical CIEDE2000/CVD separation floors."""
    old = _as_mapping(baseline)
    new = _as_mapping(candidate)
    if old is None or new is None:
        _gate_invalid(
            violations,
            asset=asset,
            metric=metric,
            message="categorical quality record must be an object",
        )
        return
    for field_name in (
        "common_min_delta_e00",
        "normal_min_delta_e00",
        "protan_min_delta_e00",
        "deutan_min_delta_e00",
        "tritan_min_delta_e00",
    ):
        _gate_number(
            violations,
            asset=asset,
            metric=f"{metric}/{field_name}",
            baseline=old.get(field_name, _MISSING),
            candidate=new.get(field_name, _MISSING),
            relation=">=",
        )


def _compare_diverging_record(
    violations: list[GateViolation],
    *,
    asset: str,
    baseline: object,
    candidate: object,
) -> None:
    """Apply the frozen diverging center, arm, and mirror policy."""
    metric = f"/metrics/topology/diverging/{_pointer_token(asset)}"
    old = _as_mapping(baseline)
    new = _as_mapping(candidate)
    if old is None or new is None:
        _gate_invalid(
            violations,
            asset=asset,
            metric=metric,
            message="diverging topology record must be an object",
        )
        return
    _gate_equal(
        violations,
        asset=asset,
        metric=f"{metric}/center_is_global_max",
        baseline=old.get("center_is_global_max", _MISSING),
        candidate=new.get("center_is_global_max", _MISSING),
    )
    for field_name in (
        "left_arm_min_oriented_delta_y",
        "right_arm_min_oriented_delta_y",
    ):
        _gate_number(
            violations,
            asset=asset,
            metric=f"{metric}/{field_name}",
            baseline=old.get(field_name, _MISSING),
            candidate=new.get(field_name, _MISSING),
            relation=">=",
        )
    for field_name in (
        "center_delta_y",
        "arm_arc_ratio",
        "arm_mean_step_ratio",
    ):
        _gate_number(
            violations,
            asset=asset,
            metric=f"{metric}/{field_name}",
            baseline=old.get(field_name, _MISSING),
            candidate=new.get(field_name, _MISSING),
            relation="<=",
        )
    for field_name in (
        "mirror_delta_y",
        "mirror_step_delta_e_ok",
        "mirror_step_ratio",
    ):
        _gate_summary_leaves(
            violations,
            asset=asset,
            metric=f"{metric}/{field_name}",
            baseline=old.get(field_name, _MISSING),
            candidate=new.get(field_name, _MISSING),
            relation="<=",
        )


def _compare_cyclic_record(
    violations: list[GateViolation],
    *,
    asset: str,
    baseline: object,
    candidate: object,
) -> None:
    """Apply seam and isoluminant/twilight topology-specific rules."""
    metric = f"/metrics/topology/cyclic/{_pointer_token(asset)}"
    old = _as_mapping(baseline)
    new = _as_mapping(candidate)
    if old is None or new is None:
        _gate_invalid(
            violations,
            asset=asset,
            metric=metric,
            message="cyclic topology record must be an object",
        )
        return
    old_kind = old.get("topology_kind", _MISSING)
    new_kind = new.get("topology_kind", _MISSING)
    _gate_equal(
        violations,
        asset=asset,
        metric=f"{metric}/topology_kind",
        baseline=old_kind,
        candidate=new_kind,
    )
    for field_name in (
        "seam_delta_e_ok",
        "seam_delta_e00",
        "seam_to_mean_delta_e_ok_ratio",
    ):
        _gate_number(
            violations,
            asset=asset,
            metric=f"{metric}/{field_name}",
            baseline=old.get(field_name, _MISSING),
            candidate=new.get(field_name, _MISSING),
            relation="<=",
        )
    if old_kind == "isoluminant":
        _gate_number(
            violations,
            asset=asset,
            metric=f"{metric}/relative_y_spread",
            baseline=old.get("relative_y_spread", _MISSING),
            candidate=new.get("relative_y_spread", _MISSING),
            relation="<=",
        )
        _gate_equal(
            violations,
            asset=asset,
            metric=f"{metric}/two_arm",
            baseline=old.get("two_arm", _MISSING),
            candidate=new.get("two_arm", _MISSING),
        )
        return
    if old_kind != "twilight":
        return
    old_arm = _as_mapping(old.get("two_arm", _MISSING))
    new_arm = _as_mapping(new.get("two_arm", _MISSING))
    arm_metric = f"{metric}/two_arm"
    if old_arm is None or new_arm is None:
        _gate_invalid(
            violations,
            asset=asset,
            metric=arm_metric,
            message="twilight topology requires a two-arm record",
        )
        return
    _gate_equal(
        violations,
        asset=asset,
        metric=f"{arm_metric}/midpoint_contains_global_y_min",
        baseline=old_arm.get("midpoint_contains_global_y_min", _MISSING),
        candidate=new_arm.get("midpoint_contains_global_y_min", _MISSING),
    )
    for field_name in (
        "left_min_oriented_delta_y",
        "right_min_oriented_delta_y",
    ):
        _gate_number(
            violations,
            asset=asset,
            metric=f"{arm_metric}/{field_name}",
            baseline=old_arm.get(field_name, _MISSING),
            candidate=new_arm.get(field_name, _MISSING),
            relation=">=",
        )
    _gate_number(
        violations,
        asset=asset,
        metric=f"{arm_metric}/arm_arc_ratio",
        baseline=old_arm.get("arm_arc_ratio", _MISSING),
        candidate=new_arm.get("arm_arc_ratio", _MISSING),
        relation="<=",
    )
    for field_name in (
        "mirror_delta_y",
        "mirror_delta_oklab_l",
        "mirror_step_delta_e_ok",
    ):
        _gate_summary_leaves(
            violations,
            asset=asset,
            metric=f"{arm_metric}/{field_name}",
            baseline=old_arm.get(field_name, _MISSING),
            candidate=new_arm.get(field_name, _MISSING),
            relation="<=",
        )


def evaluate_quality_metrics(
    baseline_metrics: Mapping[str, object],
    candidate_metrics: Mapping[str, object],
    taxonomy: Mapping[str, str],
) -> tuple[GateViolation, ...]:
    """Apply the shared raw-value quality policy without display rounding."""
    violations: list[GateViolation] = []

    old_palette = _as_mapping(baseline_metrics.get("palette")) or {}
    new_palette = _as_mapping(candidate_metrics.get("palette")) or {}
    for asset in sorted(old_palette):
        _compare_ordered_record(
            violations,
            asset=asset,
            metric=f"/metrics/palette/{_pointer_token(asset)}",
            baseline=old_palette[asset],
            candidate=new_palette.get(asset, _MISSING),
            step_cv_ceiling=0.08,
        )

    for section in ("cmaps_direct_32", "cmaps_full_256"):
        old_rows = _as_mapping(baseline_metrics.get(section)) or {}
        new_rows = _as_mapping(candidate_metrics.get(section)) or {}
        for asset in sorted(old_rows):
            ordered = taxonomy.get(asset) in {"sequential", "multi-hue"}
            ceiling = 0.08 if section == "cmaps_direct_32" and ordered else None
            _compare_ordered_record(
                violations,
                asset=asset,
                metric=f"/metrics/{section}/{_pointer_token(asset)}",
                baseline=old_rows[asset],
                candidate=new_rows.get(asset, _MISSING),
                step_cv_ceiling=ceiling,
                monotonic_floors=ordered,
                absolute_quantized_y=(section == "cmaps_full_256" and ordered),
            )

    for section in ("cycles", "curated_rows"):
        old_rows = _as_mapping(baseline_metrics.get(section)) or {}
        new_rows = _as_mapping(candidate_metrics.get(section)) or {}
        for asset in sorted(old_rows):
            _compare_categorical_record(
                violations,
                asset=asset,
                metric=f"/metrics/{section}/{_pointer_token(asset)}",
                baseline=old_rows[asset],
                candidate=new_rows.get(asset, _MISSING),
            )
    if "dark_cycle" in baseline_metrics:
        _compare_categorical_record(
            violations,
            asset="dark_cycle",
            metric="/metrics/dark_cycle",
            baseline=baseline_metrics["dark_cycle"],
            candidate=candidate_metrics.get("dark_cycle", _MISSING),
        )

    old_discrete = _as_mapping(baseline_metrics.get("discrete")) or {}
    new_discrete = _as_mapping(candidate_metrics.get("discrete")) or {}
    for family in sorted(old_discrete):
        old_forms = _as_mapping(old_discrete[family]) or {}
        new_forms = _as_mapping(new_discrete.get(family, _MISSING)) or {}
        for n_text in sorted(old_forms, key=int):
            asset = f"{family}/{n_text}"
            _compare_categorical_record(
                violations,
                asset=asset,
                metric=(
                    f"/metrics/discrete/{_pointer_token(family)}/"
                    f"{_pointer_token(n_text)}"
                ),
                baseline=old_forms[n_text],
                candidate=new_forms.get(n_text, _MISSING),
            )

    old_topology = _as_mapping(baseline_metrics.get("topology")) or {}
    new_topology = _as_mapping(candidate_metrics.get("topology")) or {}
    old_diverging = _as_mapping(old_topology.get("diverging")) or {}
    new_diverging = _as_mapping(new_topology.get("diverging")) or {}
    for asset in sorted(old_diverging):
        _compare_diverging_record(
            violations,
            asset=asset,
            baseline=old_diverging[asset],
            candidate=new_diverging.get(asset, _MISSING),
        )
    old_cyclic = _as_mapping(old_topology.get("cyclic")) or {}
    new_cyclic = _as_mapping(new_topology.get("cyclic")) or {}
    for asset in sorted(old_cyclic):
        _compare_cyclic_record(
            violations,
            asset=asset,
            baseline=old_cyclic[asset],
            candidate=new_cyclic.get(asset, _MISSING),
        )
    return tuple(violations)


def _max_run(values: Sequence[str]) -> int:
    """Return the longest adjacent run in a non-empty row."""
    longest = 0
    current = 0
    previous: object = object()
    for value in values:
        current = current + 1 if value == previous else 1
        longest = max(longest, current)
        previous = value
    return longest


def _candidate_contract_rows(
    candidate: CatalogSnapshot,
) -> dict[str, Mapping[str, Sequence[str]]]:
    """Project a catalog snapshot onto the seven SSOT row-contract sections."""
    discrete = {
        f"{family}/{size}": row
        for family, forms in candidate.discrete_hex.items()
        for size, row in forms.items()
    }
    return {
        "palette": candidate.palette,
        "direct_32": candidate.cmaps_preview_32,
        "full_256": candidate.cmaps_256,
        "cycles": candidate.cycles,
        "curated_rows": candidate.curated_rows,
        "dark_cycle": {"dark_cycle": candidate.dark_cycle},
        "discrete_forward": discrete,
    }


def _evaluate_row_contracts(
    candidate: CatalogSnapshot, contracts_value: object
) -> tuple[GateViolation, ...]:
    """Require every candidate row shape to be no worse than its v5 contract."""
    contracts = _as_mapping(contracts_value)
    if contracts is None:
        raise RuntimeError("row contracts must be a string-keyed object")
    candidate_sections = _candidate_contract_rows(candidate)
    violations: list[GateViolation] = []
    for section in sorted(contracts):
        baseline_rows = _as_mapping(contracts[section])
        candidate_rows = candidate_sections.get(section)
        if baseline_rows is None or candidate_rows is None:
            _gate_invalid(
                violations,
                asset=section,
                metric=f"/row_contracts/{_pointer_token(section)}",
                message="required row-contract section is missing",
            )
            continue
        for asset in sorted(baseline_rows):
            metric = (
                f"/row_contracts/{_pointer_token(section)}/"
                f"{_pointer_token(asset)}"
            )
            baseline = _as_mapping(baseline_rows[asset])
            candidate_row = candidate_rows.get(asset)
            if baseline is None or candidate_row is None:
                _gate_invalid(
                    violations,
                    asset=asset,
                    metric=metric,
                    message="required candidate row or contract is missing",
                )
                continue
            values = tuple(candidate_row)
            observed = {
                "count": len(values),
                "unique_count": len(set(values)),
                "adjacent_duplicate_count": sum(
                    left == right for left, right in pairwise(values)
                ),
                "max_run_length": _max_run(values),
            }
            _gate_equal(
                violations,
                asset=asset,
                metric=f"{metric}/count",
                baseline=baseline.get("count", _MISSING),
                candidate=observed["count"],
            )
            _gate_number(
                violations,
                asset=asset,
                metric=f"{metric}/unique_count",
                baseline=baseline.get("unique_count", _MISSING),
                candidate=observed["unique_count"],
                relation=">=",
            )
            for field_name in ("adjacent_duplicate_count", "max_run_length"):
                _gate_number(
                    violations,
                    asset=asset,
                    metric=f"{metric}/{field_name}",
                    baseline=baseline.get(field_name, _MISSING),
                    candidate=observed[field_name],
                    relation="<=",
                )
            if (
                section == "full_256"
                and candidate.taxonomy.get(asset) == "diverging"
                and len(values) >= 2
            ):
                midpoint = len(values) // 2
                _gate_equal(
                    violations,
                    asset=asset,
                    metric=f"{metric}/center_duplicate",
                    baseline=True,
                    candidate=values[midpoint - 1] == values[midpoint],
                )
    return tuple(violations)


def _catalog_for_oracle(candidate: CatalogSnapshot) -> dict[str, object]:
    """Translate snapshot naming to the pinned independent-oracle schema."""
    payload = candidate.exact_payload()
    payload["cmaps256"] = payload.pop("cmaps_256")
    return payload


def evaluate_catalog(
    candidate: CatalogSnapshot, quality_baseline: Mapping[str, object]
) -> GateReport:
    """Compute and gate the full candidate catalog exactly once per call."""
    validated_baseline = oracle.validate_quality_payload(
        quality_baseline, expected_oracle_sha256=QUALITY_ORACLE_SHA256
    )
    semantic_sha256 = oracle.canonical_json_sha256(validated_baseline)
    if semantic_sha256 != QUALITY_BASELINE_SEMANTIC_SHA256:
        raise oracle.OracleValidationError(
            "quality baseline semantic SHA-256 differs from its pin"
        )
    baseline_metrics_value = validated_baseline["metrics"]
    baseline_metrics = _as_mapping(baseline_metrics_value)
    if baseline_metrics is None:
        raise TypeError("quality baseline metrics must be a mapping")
    try:
        candidate_metrics, candidate_extrema = oracle.compute_catalog_quality(
            _catalog_for_oracle(candidate), candidate.cmaps_preview_32
        )
    except (
        oracle.OracleValidationError,
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        violation = GateViolation(
            asset="catalog",
            metric="/candidate",
            observed=0.0,
            allowed=1.0,
            rule="valid",
            message=f"{type(error).__name__}: {error}",
        )
        return GateReport(violations=(violation,))

    quality_violations = evaluate_quality_metrics(
        baseline_metrics, candidate_metrics, candidate.taxonomy
    )
    row_violations = _evaluate_row_contracts(candidate, _load_row_contracts())
    return GateReport(
        violations=(*quality_violations, *row_violations),
        candidate_metrics=candidate_metrics,
        candidate_global_extrema=candidate_extrema,
    )


def gate_ladder(hexes: list[str]) -> dict[str, bool | float]:
    """Return the legacy display view backed by raw OKLab/Y metrics."""
    metrics = oracle.ordered_quality(hexes)
    oriented = _as_mapping(metrics.get("oriented_delta_l"))
    minimum = None if oriented is None else _number(oriented.get("min"))
    step_cv = _number(metrics.get("step_cv"))
    return {
        "mono": minimum is not None and minimum > 0.0,
        "cv": round(float("inf") if step_cv is None else step_cv, 4),
    }


def gate_cycle(hexes: list[str]) -> dict[str, float]:
    """Return the historical rounded cycle view from the separate oracle."""
    metrics = oracle.categorical_quality(hexes)
    raw = {
        mode: cast(float, metrics[f"{mode}_min_delta_e00"])
        for mode in ("normal", "protan", "deutan", "tritan")
    }
    per = {mode: round(value, 1) for mode, value in raw.items()}
    per["common_min"] = min(per["normal"], per["protan"], per["deutan"])
    per["min00"] = min(per["common_min"], per["tritan"])
    per["common_min_raw"] = min(raw["normal"], raw["protan"], raw["deutan"])
    per["tritan_raw"] = raw["tritan"]
    return per


def gate_seq_cmap(hexes: list[str]) -> dict[str, bool | float]:
    """Return the legacy direct-row view using raw OKLab L and modeled Y."""
    metrics = oracle.ordered_quality(hexes)
    oriented_l = _as_mapping(metrics.get("oriented_delta_l"))
    oriented_y = _as_mapping(metrics.get("oriented_delta_y"))
    min_l = None if oriented_l is None else _number(oriented_l.get("min"))
    min_y = None if oriented_y is None else _number(oriented_y.get("min"))
    step_cv = _number(metrics.get("step_cv"))
    l_summary = _as_mapping(metrics.get("oklab_l"))
    l_min = None if l_summary is None else _number(l_summary.get("min"))
    l_max = None if l_summary is None else _number(l_summary.get("max"))
    return {
        "mono": min_l is not None and min_l >= -0.004,
        "gray_mono": min_y is not None and min_y >= -0.004,
        "cv": round(float("inf") if step_cv is None else step_cv, 3),
        "L_span": (
            0.0
            if l_min is None or l_max is None
            else round(100.0 * (l_max - l_min), 1)
        ),
    }


def gate_div_cmap(hexes: list[str]) -> dict[str, float]:
    """Return the historical apex display from modeled relative Y."""
    topology = oracle.diverging_topology(hexes)
    if topology["center_is_global_max"] is True:
        return {"apex_pct": 50.0}
    y_values = [
        oracle.relative_y_srgb_d65(oracle.hex_to_srgb(color)) for color in hexes
    ]
    top = max(y_values)
    plateau = [
        index for index, value in enumerate(y_values) if value >= top - 0.005
    ]
    apex = (plateau[0] + plateau[-1]) / 2.0
    return {"apex_pct": round(100.0 * apex / (len(y_values) - 1), 1)}


def gate_cyclic_cmap(hexes: list[str]) -> dict[str, float]:
    """Return the historical rounded seam ratio from raw ΔEOK topology."""
    metrics = oracle.cyclic_topology(hexes)
    return {
        "seam_ratio": round(
            cast(float, metrics["seam_to_mean_delta_e_ok_ratio"]), 2
        )
    }


def check_all(
    palette: dict[str, list[str]],
    cycles: dict[str, list[str]],
    cmaps: dict[str, list[str]],
) -> list[str]:
    """Adapt legacy partial inputs to the single frozen-baseline policy.

    This compatibility view intentionally fails closed for unknown asset names.
    The complete release build uses :func:`evaluate_catalog`; this helper uses
    the same comparison primitives for whichever legacy rows were supplied.
    Legacy colormap inputs are direct-32 rows, so full-256 topology remains
    exclusively in the complete catalog gate.
    """
    baseline = load_quality_baseline()
    metrics = _as_mapping(baseline.get("metrics"))
    if metrics is None:
        raise oracle.OracleValidationError(
            "quality baseline metrics must be a mapping"
        )

    old_palette = _as_mapping(metrics.get("palette")) or {}
    old_cycles = _as_mapping(metrics.get("cycles")) or {}
    old_direct = _as_mapping(metrics.get("cmaps_direct_32")) or {}
    old_topology = _as_mapping(metrics.get("topology")) or {}
    old_diverging = _as_mapping(old_topology.get("diverging")) or {}
    old_cyclic = _as_mapping(old_topology.get("cyclic")) or {}

    baseline_palette: dict[str, object] = {}
    candidate_palette: dict[str, object] = {}
    baseline_cycles: dict[str, object] = {}
    candidate_cycles: dict[str, object] = {}
    baseline_direct: dict[str, object] = {}
    candidate_direct: dict[str, object] = {}
    taxonomy: dict[str, str] = {}
    failures: list[str] = []

    for name, row in sorted(palette.items()):
        if name not in old_palette:
            failures.append(f"palette {name}: no frozen asset baseline")
            continue
        baseline_palette[name] = old_palette[name]
        candidate_palette[name] = oracle.ordered_quality(row)

    cycle_aliases = {
        "cycle_default": "octave",
        "cycle_print": "octave_print",
        "octave": "octave",
        "octave_print": "octave_print",
    }
    for supplied_name, row in sorted(cycles.items()):
        cycle_name = cycle_aliases.get(supplied_name)
        if cycle_name is None or cycle_name not in old_cycles:
            failures.append(f"cycle {supplied_name}: no frozen asset baseline")
            continue
        if cycle_name in candidate_cycles:
            failures.append(f"cycle {supplied_name}: duplicate asset alias")
            continue
        baseline_cycles[cycle_name] = old_cycles[cycle_name]
        candidate_cycles[cycle_name] = oracle.categorical_quality(row)

    for supplied_name, row in sorted(cmaps.items()):
        prefix, separator, suffix = supplied_name.partition(".")
        cmap_name = (
            suffix
            if separator and prefix in {"seq", "div", "cyc"}
            else supplied_name
        )
        if cmap_name not in old_direct:
            failures.append(f"cmap {supplied_name}: no frozen asset baseline")
            continue
        if cmap_name in candidate_direct:
            failures.append(f"cmap {supplied_name}: duplicate asset alias")
            continue
        baseline_direct[cmap_name] = old_direct[cmap_name]
        candidate_direct[cmap_name] = oracle.ordered_quality(row)
        if cmap_name in old_diverging:
            taxonomy[cmap_name] = "diverging"
        elif cmap_name in old_cyclic:
            taxonomy[cmap_name] = "cyclic"
        else:
            taxonomy[cmap_name] = "sequential"

    baseline_subset: dict[str, object] = {
        "palette": baseline_palette,
        "cycles": baseline_cycles,
        "cmaps_direct_32": baseline_direct,
    }
    candidate_subset: dict[str, object] = {
        "palette": candidate_palette,
        "cycles": candidate_cycles,
        "cmaps_direct_32": candidate_direct,
    }
    violations = evaluate_quality_metrics(
        baseline_subset, candidate_subset, taxonomy
    )
    failures.extend(
        f"{item.asset} {item.metric}: {item.observed} {item.rule} "
        f"{item.allowed} ({item.message})"
        for item in violations
    )
    return sorted(failures)
