#!/usr/bin/env python3
"""Build the packaged v6 color authority from frozen v5 inputs.

This offline script intentionally uses only the Python standard library.  It
verifies the raw bytes of every historical input before decoding any of them,
then emits deterministic finite JSON.
"""

import argparse
import hashlib
import json
import math
import os
import stat
import tempfile
from collections.abc import Mapping, Sequence
from itertools import pairwise
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
V5_RECIPE_PATH = (
    REPO_ROOT
    / "docs/superpowers/specs/assets/2026-07-03-color-system-v5"
    / "color_v5_ssot.json"
)
COMPATIBILITY_PATH = (
    REPO_ROOT
    / "docs/superpowers/specs/assets/2026-07-14-oklab-centered-color-system"
    / "color_v5_compatibility.json"
)
QUALITY_PATH = COMPATIBILITY_PATH.with_name("color_v5_quality.json")
ORACLE_PATH = REPO_ROOT / "src/dartwork_mpl/_colors/_compatibility_metrics.py"
DEFAULT_OUTPUT = REPO_ROOT / "src/dartwork_mpl/asset/color/color_v6_ssot.json"
_BASELINE_COMMIT = "12d16bac22dee790bd0696ca92a814a797dc728b"
_MULTI_HUE_VIVID_CUTOFFS = {
    "afterglow": 1,
    "aurora": 33,
    "blaze": 8,
    "canopy": 16,
    "glacier": 1,
    "haze": 37,
    "iris": 32,
    "lagoon": 29,
    "lava": 19,
}

_RAW_SHA256 = {
    "recipe": "a75bd08f2ae5606ec3076a01877ba813b9f2899a96b95739a44e5d3493b68518",
    "compatibility": "bc0b9fa8a5d888b60808de48dbdadb1ff25690e435a7bcc44aa63d31ce742818",
    "quality": "326906a7ab05b48ec35f37d8e2a73931106fc03edde7db263e1e6735f3c95616",
    "oracle": "52718f3bf19f2fc2e5c7b95ef3cfe6338335b684eea86cd4b55892ed03765548",
}
_SOURCE_PATHS = {
    "recipe": (
        "docs/superpowers/specs/assets/2026-07-03-color-system-v5/"
        "color_v5_ssot.json"
    ),
    "compatibility": (
        "docs/superpowers/specs/assets/2026-07-14-oklab-centered-"
        "color-system/color_v5_compatibility.json"
    ),
    "quality": (
        "docs/superpowers/specs/assets/2026-07-14-oklab-centered-"
        "color-system/color_v5_quality.json"
    ),
    "oracle": "src/dartwork_mpl/_colors/_compatibility_metrics.py",
}
_LEGACY_WHITE_Y = 1.0000001
_MIGRATION_DENOMINATOR = 116.00000386666655
_TOE_LSTAR = 8.0
_TOE_KAPPA = 24389.0 / 27.0
_TOE_TONE: float = ((_TOE_LSTAR / _TOE_KAPPA) / _LEGACY_WHITE_Y) ** (1.0 / 3.0)
_RELATIVE_Y_COEFFICIENTS = (
    0.21267287873271212,
    0.7151521284847872,
    0.07217499278250072,
)


def _raw_sha256(path: Path) -> str:
    """Return the SHA-256 digest of one file's raw bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_pinned_json(path: Path, expected_sha256: str) -> dict[str, object]:
    """Verify raw bytes and decode one frozen JSON object.

    Parameters
    ----------
    path : pathlib.Path
        Historical JSON input.
    expected_sha256 : str
        Accepted SHA-256 digest of the raw file bytes.

    Returns
    -------
    dict[str, object]
        Decoded top-level object.

    Raises
    ------
    RuntimeError
        If raw provenance or the JSON top-level shape is invalid.
    """
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected_sha256:
        raise RuntimeError(
            f"raw SHA-256 mismatch for {path}: expected "
            f"{expected_sha256}, got {actual}"
        )
    decoded: object = json.loads(raw)
    if not isinstance(decoded, dict):
        raise RuntimeError(f"expected a JSON object in {path}")
    return decoded


def _verify_pinned_source(path: Path, expected_sha256: str) -> None:
    """Reject a non-JSON frozen source whose raw bytes have drifted."""
    actual = _raw_sha256(path)
    if actual != expected_sha256:
        raise RuntimeError(
            f"raw SHA-256 mismatch for {path}: expected "
            f"{expected_sha256}, got {actual}"
        )


def _legacy_lstar_to_tone(legacy_lstar: float) -> float:
    """Migrate one historical CIE lightness value to neutral tone.

    The function exists only in this offline provenance builder.  The emitted
    production recipe contains already-migrated values.
    """
    if not math.isfinite(legacy_lstar):
        raise ValueError("historical lightness must be finite")
    if legacy_lstar < 0.0:
        raise ValueError("historical lightness must be non-negative")
    if legacy_lstar <= _TOE_LSTAR:
        raw_y = legacy_lstar / _TOE_KAPPA
        return ((raw_y / _LEGACY_WHITE_Y) ** (1.0 / 3.0)) if raw_y else 0.0
    upper = (legacy_lstar + 16.0) / _MIGRATION_DENOMINATOR
    return max(_TOE_TONE, upper)


def _canonical_sha256(value: object) -> str:
    """Hash one JSON value with the v6 canonical encoding."""
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _require_mapping(value: object, label: str) -> Mapping[str, object]:
    """Narrow one decoded value to a string-keyed mapping."""
    if not isinstance(value, Mapping) or not all(
        isinstance(key, str) for key in value
    ):
        raise RuntimeError(f"{label} must be a string-keyed object")
    return value


def _require_sequence(value: object, label: str) -> Sequence[object]:
    """Narrow one decoded value to a non-string sequence."""
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise RuntimeError(f"{label} must be an array")
    return value


def _require_real(value: object, label: str) -> float:
    """Narrow one decoded value to a finite JSON number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"{label} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise RuntimeError(f"{label} must be finite")
    return result


def _recipe_payload(v5_recipe: Mapping[str, object]) -> dict[str, object]:
    """Transform the historical recipe into operational v6 coordinates."""
    legacy_params = _require_mapping(v5_recipe["params"], "recipe params")
    family_params: dict[str, object] = {}
    for family, raw_params in legacy_params.items():
        params = _require_mapping(raw_params, f"recipe params.{family}")
        family_params[family] = {
            "h0": params["h0"],
            "dh": params["dh"],
            "gamma": params["gamma"],
            "tp": params["tp"],
            "cmax": params["cmax"],
            "tone_floor": _legacy_lstar_to_tone(
                _require_real(params["floor"], f"recipe params.{family}.floor")
            ),
            "cend": params["cend"],
            "c0": params["c0"],
        }

    legacy_fourier = _require_mapping(v5_recipe["fourier"], "recipe fourier")
    legacy_floor = _require_sequence(
        legacy_fourier["floor_k3"], "recipe fourier floor"
    )
    migrated_floor = [
        (_require_real(legacy_floor[0], "recipe Fourier constant") + 16.0)
        / _MIGRATION_DENOMINATOR,
        *[
            _require_real(coefficient, "recipe Fourier harmonic")
            / _MIGRATION_DENOMINATOR
            for coefficient in legacy_floor[1:]
        ],
    ]
    fourier = {
        "cmax_k3": legacy_fourier["cmax_k3"],
        "tone_floor_k3": migrated_floor,
        "cend_k2": legacy_fourier["cend_k2"],
        "c0_k2": legacy_fourier["c0_k2"],
    }

    legacy_constants = _require_mapping(
        v5_recipe["constants"], "recipe constants"
    )
    legacy_gray = _require_mapping(
        legacy_constants["gray"], "recipe constants.gray"
    )
    constants = {
        "TONE_TOP": _legacy_lstar_to_tone(
            _require_real(legacy_constants["L_TOP"], "recipe top")
        ),
        "SHAPE_Q": legacy_constants["shape_q"],
        "SHAPE_R": legacy_constants["shape_r"],
        "GAMUT_CHROMA_FRAC": legacy_constants["gamut_chroma_frac"],
        "GRAY_TONE_FLOOR": _legacy_lstar_to_tone(
            _require_real(legacy_gray["floor"], "recipe gray floor")
        ),
        "GRAY_TINT_HUE": legacy_gray["tint_hue"],
        "GRAY_C_PROFILE": legacy_gray["C_profile"],
        "TONE_DERIVATION_GRID": 1.0 / _MIGRATION_DENOMINATOR,
    }
    return {
        "family_order": list(legacy_params),
        "family_params": family_params,
        "fourier": fourier,
        "constants": constants,
    }


def _max_run_length(row: Sequence[object]) -> int:
    """Return the longest run of adjacent equal values in one row."""
    longest = 0
    current = 0
    previous: object = object()
    for value in row:
        current = current + 1 if value == previous else 1
        longest = max(longest, current)
        previous = value
    return longest


def _row_contract(row: Sequence[object]) -> dict[str, object]:
    """Describe one frozen literal row without imposing uniqueness."""
    values = list(row)
    return {
        "adjacent_duplicate_count": sum(
            left == right for left, right in pairwise(values)
        ),
        "canonical_sha256": _canonical_sha256(values),
        "count": len(values),
        "max_run_length": _max_run_length(values),
        "unique_count": len(set(values)),
    }


def _row_contracts(
    compatibility: Mapping[str, object], quality: Mapping[str, object]
) -> dict[str, object]:
    """Derive all 671 forward-row contracts from frozen literals."""
    literal_inputs = _require_mapping(
        quality["literal_inputs"], "quality literal_inputs"
    )
    direct = _require_mapping(
        literal_inputs["cmaps_preview_32"], "quality direct previews"
    )
    discrete = _require_mapping(
        compatibility["discrete_hex"], "compatibility discrete rows"
    )
    discrete_flat: dict[str, object] = {}
    for name, raw_forms in discrete.items():
        forms = _require_mapping(raw_forms, f"discrete {name}")
        for size, row in forms.items():
            discrete_flat[f"{name}/{size}"] = row

    sections: dict[str, Mapping[str, object]] = {
        "palette": _require_mapping(
            compatibility["palette"], "compatibility palette"
        ),
        "direct_32": direct,
        "full_256": _require_mapping(
            compatibility["cmaps256"], "compatibility full LUTs"
        ),
        "cycles": _require_mapping(
            compatibility["cycles"], "compatibility cycles"
        ),
        "curated_rows": _require_mapping(
            compatibility["curated_rows"], "compatibility curated rows"
        ),
        "dark_cycle": {"dark_cycle": compatibility["dark_cycle"]},
        "discrete_forward": discrete_flat,
    }
    return {
        section: {
            name: _row_contract(_require_sequence(row, f"{section}.{name}"))
            for name, row in rows.items()
        }
        for section, rows in sections.items()
    }


def _ensure_finite(value: object, path: str = "payload") -> None:
    """Reject non-finite numbers before deterministic JSON emission."""
    if isinstance(value, float) and not math.isfinite(value):
        raise RuntimeError(f"{path} contains a non-finite number")
    if isinstance(value, Mapping):
        for key, item in value.items():
            _ensure_finite(item, f"{path}.{key}")
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, item in enumerate(value):
            _ensure_finite(item, f"{path}[{index}]")


def _build_payload(baseline_commit: str) -> dict[str, object]:
    """Build the complete v6 authority after raw provenance checks."""
    if baseline_commit != _BASELINE_COMMIT:
        raise RuntimeError(
            "baseline commit does not match the accepted v5 provenance"
        )
    v5_recipe = _read_pinned_json(V5_RECIPE_PATH, _RAW_SHA256["recipe"])
    compatibility = _read_pinned_json(
        COMPATIBILITY_PATH, _RAW_SHA256["compatibility"]
    )
    quality = _read_pinned_json(QUALITY_PATH, _RAW_SHA256["quality"])
    _verify_pinned_source(ORACLE_PATH, _RAW_SHA256["oracle"])

    quality_policy = _require_mapping(quality["policy"], "quality policy")
    baselines = {
        "recipe": {
            "path": _SOURCE_PATHS["recipe"],
            "raw_sha256": _RAW_SHA256["recipe"],
        },
        "compatibility": {
            "path": _SOURCE_PATHS["compatibility"],
            "raw_sha256": _RAW_SHA256["compatibility"],
            "canonical_hashes": compatibility["canonical_hashes"],
        },
        "quality": {
            "path": _SOURCE_PATHS["quality"],
            "raw_sha256": _RAW_SHA256["quality"],
            "metrics": quality["metrics"],
            "global_extrema": quality["global_extrema"],
            "policy": quality["policy"],
        },
        "oracle": {
            "path": _SOURCE_PATHS["oracle"],
            "raw_sha256": _RAW_SHA256["oracle"],
        },
    }
    payload: dict[str, object] = {
        "schema": "dartwork-mpl.color-ssot/v6",
        "baseline_commit": baseline_commit,
        "coordinates": {
            "authoring": "OKLab/OKLCH",
            "canonical": "OKLab",
            "neutral_tone": (
                "cbrt(modeled relative CIE Y from nominal D65 sRGB)"
            ),
            "output": (
                "modeled relative CIE Y calculated from nominal D65 sRGB"
            ),
            "relative_y_coefficients": list(_RELATIVE_Y_COEFFICIENTS),
            "validation_only": ["CIELAB", "CIEDE2000", "Machado/BVM CVD"],
        },
        "migration": {
            "denominator": _MIGRATION_DENOMINATOR,
            "legacy_coordinate": "CIELAB L* D65",
            "legacy_white_y": _LEGACY_WHITE_Y,
            "lower_formula": "cbrt((L* / (24389 / 27)) / S)",
            "scope": "offline v5 compatibility provenance only",
            "toe_lstar": _TOE_LSTAR,
            "toe_kappa": _TOE_KAPPA,
            "upper_formula": "(L* + 16) / D",
        },
        "policies": {
            "gamut": {
                "iterations": 24,
                "max_chroma_upper": 0.4,
                "strategy": "preserve OKLCH L/h and reduce C",
                "tolerance": 1e-6,
            },
            "tone": {
                "catalog_chroma_fraction": 0.97,
                "luminance_search_iterations": 40,
                "max_chroma_search_iterations": 22,
                "max_chroma_tone_iterations": 30,
                "max_chroma_upper": 0.4,
                "probe_chroma": 0.04,
            },
            "cvd": {
                "gate_pipeline": quality_policy["cvd_gate_pipeline"],
                "models_by_deficiency": {
                    "deutan": "Machado et al. 2009 severity 1.0",
                    "protan": "Machado et al. 2009 severity 1.0",
                    "tritan": (
                        "Brettel-Vienot-Mollon 1997 adapted linear-sRGB"
                    ),
                },
                "role": "model-specific validation only",
            },
            "presentation": {
                "multi_hue_vivid_cutoffs": dict(_MULTI_HUE_VIVID_CUTOFFS)
            },
        },
        "recipe": _recipe_payload(v5_recipe),
        "baselines": baselines,
        "multi_hue_discrete_indices": compatibility[
            "multi_hue_discrete_indices"
        ],
        "row_contracts": _row_contracts(compatibility, quality),
    }
    _ensure_finite(payload)
    payload["section_hashes"] = {
        name: _canonical_sha256(payload[name]) for name in sorted(payload)
    }
    return payload


def _set_temporary_mode(descriptor: int, temporary: Path, mode: int) -> None:
    """Set temporary permissions through the best platform capability."""
    fchmod = getattr(os, "fchmod", None)
    if callable(fchmod):
        fchmod(descriptor, mode)
        return
    os.chmod(temporary, mode)


def _atomic_write_text(target: Path, text: str) -> None:
    """Fsync a unique sibling temporary and atomically replace ``target``."""
    target_mode = (
        stat.S_IMODE(target.stat().st_mode) if target.exists() else 0o644
    )
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    temporary = Path(temporary_name)
    descriptor_owned = True
    try:
        _set_temporary_mode(descriptor, temporary, target_mode)
        stream = os.fdopen(descriptor, "w", encoding="utf-8", newline="")
        descriptor_owned = False
        with stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if descriptor_owned:
            try:
                os.close(descriptor)
            finally:
                temporary.unlink(missing_ok=True)
        else:
            temporary.unlink(missing_ok=True)


def _write_payload(payload: Mapping[str, object], output: Path) -> None:
    """Atomically write deterministic pretty-printed JSON."""
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = (
        json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    _atomic_write_text(output, encoded)


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the offline builder."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-commit", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    """Build and write the packaged v6 color authority."""
    arguments = _parse_args()
    payload = _build_payload(arguments.baseline_commit)
    _write_payload(payload, arguments.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
