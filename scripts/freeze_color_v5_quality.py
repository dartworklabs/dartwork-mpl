"""Freeze the independent v5 color-quality baseline from pinned literals."""

import argparse
import hashlib
import io
import json
import os
import stat
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import cast

REPO_ROOT = Path(__file__).resolve().parents[1]
ORACLE_DIRECTORY = REPO_ROOT / "src/dartwork_mpl/_colors"
sys.path.insert(0, str(ORACLE_DIRECTORY))
import _compatibility_metrics as oracle  # noqa: E402

JsonMap = dict[str, object]

ACCEPTED_BASELINE_COMMIT = "12d16bac22dee790bd0696ca92a814a797dc728b"
COMPATIBILITY_PATH = (
    REPO_ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "assets"
    / "2026-07-14-oklab-centered-color-system"
    / "color_v5_compatibility.json"
)
COMPATIBILITY_SHA256 = (
    "bc0b9fa8a5d888b60808de48dbdadb1ff25690e435a7bcc44aa63d31ce742818"
)
DEFAULT_OUTPUT = COMPATIBILITY_PATH.with_name("color_v5_quality.json")
ORACLE_PATH = ORACLE_DIRECTORY / "_compatibility_metrics.py"
SOURCE_HASHES = {
    "docs/superpowers/specs/assets/2026-07-03-color-system-v5/"
    "color_v5_ssot.json": (
        "a75bd08f2ae5606ec3076a01877ba813b9f2899a96b95739a44e5d3493b68518"
    ),
    "src/dartwork_mpl/_colors/_curated.py": (
        "ee570b840323015db427e1bb36f500eb4f12d67027aa3894f9b7ba02caa295f5"
    ),
    "src/dartwork_mpl/_colors/_generated.py": (
        "999950452b2f2d8e2d58449af7c7fa043d918c922719be68939f765f5f762d54"
    ),
    "src/dartwork_mpl/asset/color/ant_colors.json": (
        "9cad970d63064bfd35c122a03e9ee0d53d5e90754fea2e3dbaa911fa1f09fa7c"
    ),
    "src/dartwork_mpl/asset/color/chakra_colors.json": (
        "fd5c54c87c532a3448edab06c870407ec9616f93cb18eeacab933a34237af6f9"
    ),
    "src/dartwork_mpl/asset/color/material_colors.json": (
        "cce34cc9f41ed4562524ab03e26d1bbcb27f3f81e1e3c9ae22acb0d372817888"
    ),
    "src/dartwork_mpl/asset/color/opencolor.txt": (
        "8210fd90139d05ab38b34a2b62a5968adeabe9999f5f12607054c9c630728ad7"
    ),
    "src/dartwork_mpl/asset/color/primer_colors.json": (
        "91f269a580137ea58da44075b4cd732062aef3ea8b17a5cf20f3f339b78dab94"
    ),
    "src/dartwork_mpl/asset/color/tailwind_colors.json": (
        "281d2942d14d55d8dcabe389054757d2b898c9ab467ba1d752dbdef0f881436f"
    ),
}

DIRECT_PREVIEW_PROBE = r"""import json
import sys
from pathlib import Path

archive_root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(archive_root / "src"))

import dartwork_mpl
from dartwork_mpl._colors._cmaps import compile_cmaps
from dartwork_mpl._colors._generate import compile_palette

package_path = Path(dartwork_mpl.__file__).resolve()
if not package_path.is_relative_to(archive_root):
    raise RuntimeError(f"baseline import escaped archive: {package_path}")

palette = compile_palette()
previews = compile_cmaps(palette, n=32)
if len(previews) != 43 or any(len(row) != 32 for row in previews.values()):
    raise RuntimeError("archived compiler did not produce literal 43x32 previews")
print(json.dumps(previews, allow_nan=False, separators=(",", ":"), sort_keys=True))
"""


def _run_git(*args: str) -> bytes:
    """Run Git at the repository root and return raw standard output."""
    process = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, check=False, capture_output=True
    )
    if process.returncode != 0:
        stderr = process.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {stderr}")
    return process.stdout


def _resolve_baseline(revision: str) -> str:
    """Resolve and require the one accepted baseline commit."""
    resolved = (
        _run_git("rev-parse", "--verify", f"{revision}^{{commit}}")
        .decode("ascii")
        .strip()
    )
    if resolved != ACCEPTED_BASELINE_COMMIT:
        raise ValueError(
            "baseline commit must resolve to "
            f"{ACCEPTED_BASELINE_COMMIT}; got {resolved}"
        )
    return resolved


def _verify_baseline_sources(commit: str) -> None:
    """Reject baseline Git objects whose accepted source blobs drifted."""
    for path, expected in SOURCE_HASHES.items():
        raw = _run_git("show", f"{commit}:{path}")
        actual = hashlib.sha256(raw).hexdigest()
        if actual != expected:
            raise RuntimeError(
                f"raw source hash mismatch for {path}: "
                f"expected {expected}, got {actual}"
            )


def _load_compatibility(commit: str) -> JsonMap:
    """Load only the raw-SHA-pinned Task 1 compatibility fixture."""
    raw = COMPATIBILITY_PATH.read_bytes()
    actual_hash = hashlib.sha256(raw).hexdigest()
    if actual_hash != COMPATIBILITY_SHA256:
        raise RuntimeError(
            "compatibility fixture raw SHA-256 mismatch: "
            f"expected {COMPATIBILITY_SHA256}, got {actual_hash}"
        )
    decoded = json.loads(raw)
    if not isinstance(decoded, dict):
        raise RuntimeError("compatibility fixture must decode to an object")
    payload = cast(JsonMap, decoded)
    if payload.get("schema") != "dartwork-mpl.color-compatibility/v1":
        raise RuntimeError("compatibility fixture schema mismatch")
    if payload.get("baseline_commit") != commit:
        raise RuntimeError("compatibility fixture baseline commit mismatch")
    if payload.get("source_hashes") != SOURCE_HASHES:
        raise RuntimeError("compatibility fixture source hashes drifted")
    return payload


def _archived_direct_previews(commit: str) -> JsonMap:
    """Compile direct-32 LUTs only inside an isolated baseline archive."""
    archive_bytes = _run_git("archive", "--format=tar", commit)
    with tempfile.TemporaryDirectory(prefix="dartwork-mpl-v5-quality-") as temp:
        archive_root = Path(temp)
        with tarfile.open(
            fileobj=io.BytesIO(archive_bytes), mode="r:"
        ) as archive:
            archive.extractall(archive_root)
        environment = os.environ.copy()
        environment["MPLBACKEND"] = "Agg"
        environment["MPLCONFIGDIR"] = str(archive_root / ".mplconfig")
        environment["PYTHONNOUSERSITE"] = "1"
        process = subprocess.run(
            [
                sys.executable,
                "-I",
                "-c",
                DIRECT_PREVIEW_PROBE,
                str(archive_root),
            ],
            cwd=archive_root,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
    if process.returncode != 0:
        raise RuntimeError(
            "isolated direct-preview probe failed:\n"
            f"stdout:\n{process.stdout}\n"
            f"stderr:\n{process.stderr}"
        )
    decoded = json.loads(process.stdout)
    if not isinstance(decoded, dict):
        raise RuntimeError("direct-preview probe returned a non-object")
    return cast(JsonMap, decoded)


def _build_payload(commit: str) -> JsonMap:
    """Build the immutable quality payload from pinned baseline inputs."""
    _verify_baseline_sources(commit)
    compatibility = _load_compatibility(commit)
    previews = _archived_direct_previews(commit)
    oracle_hash = hashlib.sha256(ORACLE_PATH.read_bytes()).hexdigest()
    return cast(
        JsonMap,
        oracle.build_quality_payload(
            compatibility,
            previews,
            baseline_commit=commit,
            compatibility_path=str(COMPATIBILITY_PATH.relative_to(REPO_ROOT)),
            compatibility_sha256=COMPATIBILITY_SHA256,
            oracle_path=str(ORACLE_PATH.relative_to(REPO_ROOT)),
            oracle_sha256=oracle_hash,
        ),
    )


def _serialize(payload: JsonMap) -> str:
    """Serialize deterministic finite pretty JSON with one final newline."""
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


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


def _write_output(output: Path, text: str) -> None:
    """Write a quality fixture atomically."""
    output.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(output, text)


def _parse_args() -> argparse.Namespace:
    """Parse required baseline and optional output arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline-commit",
        required=True,
        help="Pinned v5 commit (must resolve to the accepted full identifier)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Quality fixture destination (default: {DEFAULT_OUTPUT})",
    )
    return parser.parse_args()


def main() -> int:
    """Generate the pinned v5 quality fixture, returning process status."""
    try:
        args = _parse_args()
        commit = _resolve_baseline(cast(str, args.baseline_commit))
        payload = _build_payload(commit)
        output = cast(Path, args.output).resolve()
        _write_output(output, _serialize(payload))
    except (
        json.JSONDecodeError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
        oracle.OracleValidationError,
    ) as error:
        print(f"quality baseline error: {error}", file=sys.stderr)
        return 2
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
