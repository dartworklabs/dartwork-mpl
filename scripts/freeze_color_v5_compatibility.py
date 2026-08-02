"""Freeze the immutable v5 color-system compatibility manifest.

Static generated and curated values are parsed from a pinned Git object.
Computed v5 behavior is evaluated only inside a disposable archive of that
same commit, keeping the baseline independent from the candidate worktree.
"""

import argparse
import ast
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
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "assets"
    / "2026-07-14-oklab-centered-color-system"
    / "color_v5_compatibility.json"
)
ACCEPTED_BASELINE_COMMIT = "12d16bac22dee790bd0696ca92a814a797dc728b"
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
EXACT_SURFACES = (
    "palette",
    "cycles",
    "cmaps256",
    "curated_rows",
    "diverging_canonicals",
    "semantic_coordinates",
    "semantic_colors",
    "dark_cycle_coordinates",
    "dark_cycle",
    "taxonomy",
    "registrations",
    "typing_literals",
    "mcp_discovery",
    "public_inventory",
    "discrete_hex",
    "reverse_discrete_hex",
    "multi_hue_discrete_indices",
    "vendor_colors",
)
EXPECTED_INVENTORY = {
    "palette_positions": 200,
    "cycle_positions": 16,
    "cmap_positions": 11008,
    "qualitative_families": 13,
    "families": 56,
    "registered_colormaps": 99,
    "dc_tokens": 380,
    "vendor_tokens": 892,
}
EXPECTED_DISCOVERY_COUNTS = {
    "tool_names": 16,
    "resource_uris": 10,
    "resource_template_uris": 4,
    "prompt_names": 2,
}

JsonMap = dict[str, object]


RUNTIME_PROBE = r"""import json
import re
import sys
from pathlib import Path
from typing import get_args

archive_root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(archive_root / "src"))

import matplotlib as mpl
import dartwork_mpl
from dartwork_mpl._colors import _curated, _generated, _semantic
from dartwork_mpl._colors._discrete import (
    DIVERGING_CANONICALS,
    _candidate_data,
    discrete_colors,
)
from dartwork_mpl._colors._families import FAMILIES
from dartwork_mpl._colors._typing import DartworkColor, DartworkColormap

package_path = Path(dartwork_mpl.__file__).resolve()
if not package_path.is_relative_to(archive_root):
    raise RuntimeError(
        f"baseline import escaped archive: {package_path}"
    )


def max_n(family):
    if family.kind == "sequential":
        return 10
    if family.kind == "multi-hue":
        return 8
    if family.kind == "diverging":
        return 9
    if family.kind == "cyclic":
        return 24
    return int(family.discrete_size or 0)


def palette_coordinate(hex_color):
    matches = [
        [family, index]
        for family, row in _generated.PALETTE.items()
        for index, candidate in enumerate(row)
        if candidate == hex_color
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"semantic color has {len(matches)} palette coordinates: "
            f"{hex_color}"
        )
    return matches[0]


taxonomy = {
    name: family.kind for name, family in sorted(FAMILIES.items())
}
public_inventory = dartwork_mpl.list_colors()
discrete_hex = {}
reverse_discrete_hex = {}
multi_hue_discrete_indices = {}
for name, family in sorted(FAMILIES.items()):
    sizes = range(1, max_n(family) + 1)
    discrete_hex[name] = {
        str(n): discrete_colors(name, n) for n in sizes
    }
    reverse_discrete_hex[name] = {
        str(n): discrete_colors(name, n, reverse=True)
        for n in range(1, max_n(family) + 1)
    }
    if family.kind != "multi-hue":
        continue
    cmap = _generated.CMAPS_256[name]
    index_forms = {}
    for n in range(1, 9):
        data = _candidate_data(name)
        indices = []
        for color in discrete_hex[name][str(n)]:
            if data.hexes.count(color) != 1:
                raise RuntimeError(
                    f"multi-hue color is not unique for {name} n={n}: "
                    f"{color}"
                )
            candidate_position = data.hexes.index(color)
            cmap_index = data.indices[candidate_position]
            if cmap[cmap_index] != color:
                raise RuntimeError(
                    f"multi-hue index mismatch for {name} n={n}"
                )
            indices.append(cmap_index)
        index_forms[str(n)] = indices
    multi_hue_discrete_indices[name] = index_forms

semantic_values = {
    "default": {
        **_semantic._COMMON,
        **_semantic._MAPS["default"],
    },
    "kr": {
        **_semantic._COMMON,
        **_semantic._MAPS["kr"],
    },
}
semantic_colors = {
    locale: dict(sorted(values.items()))
    for locale, values in sorted(semantic_values.items())
}
semantic_coordinates = {
    locale: {
        token: palette_coordinate(hex_color)
        for token, hex_color in sorted(values.items())
    }
    for locale, values in sorted(semantic_values.items())
}

dark_style = (
    archive_root
    / "src"
    / "dartwork_mpl"
    / "asset"
    / "mplstyle"
    / "theme-dark.mplstyle"
).read_text(encoding="utf-8")
cycle_match = re.search(
    r"axes\.prop_cycle:\s*cycler\('color',\s*\[([^\]]+)\]",
    dark_style,
)
if cycle_match is None:
    raise RuntimeError("theme-dark cycle declaration not found")
dark_tokens = re.findall(r"'([^']+)'", cycle_match.group(1))
dark_cycle_coordinates = []
dark_cycle = []
for token in dark_tokens:
    token_match = re.fullmatch(r"dc\.([a-z_]+)(\d+)", token)
    if token_match is None:
        raise RuntimeError(f"unexpected dark-cycle token: {token}")
    family, index_text = token_match.groups()
    index = int(index_text)
    dark_cycle_coordinates.append([family, index])
    dark_cycle.append(_generated.PALETTE[family][index])

resources_source = (
    archive_root / "src" / "dartwork_mpl" / "mcp" / "resources.py"
).read_text(encoding="utf-8")
tools_source = (
    archive_root / "src" / "dartwork_mpl" / "mcp" / "tools.py"
).read_text(encoding="utf-8")
prompts_source = (
    archive_root / "src" / "dartwork_mpl" / "mcp" / "prompts.py"
).read_text(encoding="utf-8")
tool_names = re.findall(
    r"@mcp\.tool\([^)]*\)\s*\n\s*def\s+(\w+)\s*\(",
    tools_source,
    re.MULTILINE,
)
all_resource_uris = re.findall(
    r"@mcp\.resource\(\s*[\"']([^\"']+)[\"']",
    resources_source,
)
prompt_names = re.findall(
    r"@mcp\.prompt\([^)]*\)\s*\n\s*def\s+(\w+)\s*\(",
    prompts_source,
    re.MULTILINE,
)
mcp_discovery = {
    "tool_names": tool_names,
    "resource_uris": [
        uri for uri in all_resource_uris if "{" not in uri
    ],
    "resource_template_uris": [
        uri for uri in all_resource_uris if "{" in uri
    ],
    "prompt_names": prompt_names,
}

color_names = list(get_args(DartworkColor))
colormap_names = list(get_args(DartworkColormap))
vendor_names = sorted(name for name in color_names if not name.startswith("dc."))
named_colors = mpl.colors.get_named_colors_mapping()
vendor_colors = {
    name: mpl.colors.to_hex(named_colors[name], keep_alpha=False).lower()
    for name in vendor_names
}
if len(vendor_colors) != 892 or set(vendor_colors) != set(vendor_names):
    raise RuntimeError("archived vendor color mapping is incomplete")
if any(
    re.fullmatch(r"#[0-9a-f]{6}", value) is None
    for value in vendor_colors.values()
):
    raise RuntimeError("archived vendor color mapping is not normalized hex")
registrations = sorted(
    name for name in mpl.colormaps if name.startswith("dc.")
)
if registrations != colormap_names:
    raise RuntimeError("registered colormaps differ from the typing literal")

payload = {
    "dark_cycle": dark_cycle,
    "dark_cycle_coordinates": dark_cycle_coordinates,
    "discrete_hex": discrete_hex,
    "diverging_canonicals": {
        name: list(row)
        for name, row in sorted(DIVERGING_CANONICALS.items())
    },
    "inventory_runtime": {
        "qualitative_families": sum(
            family.kind == "qualitative" for family in FAMILIES.values()
        ),
        "families": len(FAMILIES),
        "registered_colormaps": len(registrations),
        "dc_tokens": sum(name.startswith("dc.") for name in color_names),
        "vendor_tokens": sum(
            not name.startswith("dc.") for name in color_names
        ),
    },
    "mcp_discovery": mcp_discovery,
    "multi_hue_discrete_indices": multi_hue_discrete_indices,
    "public_inventory": public_inventory,
    "registrations": registrations,
    "reverse_discrete_hex": reverse_discrete_hex,
    "semantic_colors": semantic_colors,
    "semantic_coordinates": semantic_coordinates,
    "taxonomy": taxonomy,
    "typing_literals": {
        "color_names": color_names,
        "colormap_names": colormap_names,
    },
    "vendor_colors": vendor_colors,
}
print(json.dumps(payload, ensure_ascii=False, allow_nan=False, sort_keys=True))
"""


def _run_git(*args: str) -> bytes:
    """Run Git in the repository and return its raw standard output.

    Parameters
    ----------
    *args : str
        Arguments following the ``git`` executable.

    Returns
    -------
    bytes
        Raw standard output from Git.

    Raises
    ------
    RuntimeError
        If Git exits unsuccessfully.
    """
    process = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, check=False, capture_output=True
    )
    if process.returncode != 0:
        stderr = process.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {stderr}")
    return process.stdout


def _resolve_baseline(revision: str) -> str:
    """Resolve and validate the explicitly requested baseline revision.

    Parameters
    ----------
    revision : str
        User-supplied Git commit or unambiguous prefix.

    Returns
    -------
    str
        Full accepted commit identifier.

    Raises
    ------
    ValueError
        If the revision does not resolve to the accepted v5 baseline.
    """
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


def _read_verified_sources(commit: str) -> dict[str, bytes]:
    """Read pinned Git sources after checking their accepted raw hashes.

    Parameters
    ----------
    commit : str
        Full accepted baseline commit.

    Returns
    -------
    dict[str, bytes]
        Source path to raw Git blob bytes.

    Raises
    ------
    RuntimeError
        If any raw source digest differs from the accepted specification.
    """
    sources: dict[str, bytes] = {}
    for path, accepted_hash in SOURCE_HASHES.items():
        raw = _run_git("show", f"{commit}:{path}")
        digest = hashlib.sha256(raw).hexdigest()
        if digest != accepted_hash:
            raise RuntimeError(
                f"raw source hash mismatch for {path}: "
                f"expected {accepted_hash}, got {digest}"
            )
        sources[path] = raw
    return sources


def _literal_assignment(source: bytes, name: str) -> object:
    """Extract one top-level literal assignment through Python's AST.

    Parameters
    ----------
    source : bytes
        Python source blob read with ``git show``.
    name : str
        Top-level assignment name to extract.

    Returns
    -------
    object
        Value accepted by :func:`ast.literal_eval`.

    Raises
    ------
    ValueError
        If no matching literal assignment exists.
    """
    tree = ast.parse(source.decode("utf-8"))
    for node in tree.body:
        value_node: ast.expr | None = None
        if isinstance(node, ast.Assign):
            if any(
                isinstance(target, ast.Name) and target.id == name
                for target in node.targets
            ):
                value_node = node.value
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
        ):
            value_node = node.value
        if value_node is not None:
            return ast.literal_eval(value_node)
    raise ValueError(f"literal assignment {name!r} not found")


def _archive_runtime_payload(commit: str) -> JsonMap:
    """Evaluate computed v5 behavior inside a disposable Git archive.

    Parameters
    ----------
    commit : str
        Full accepted baseline commit.

    Returns
    -------
    dict[str, object]
        JSON-compatible computed compatibility surfaces.

    Raises
    ------
    RuntimeError
        If archive extraction or the isolated probe fails.
    """
    archive_bytes = _run_git("archive", "--format=tar", commit)
    with tempfile.TemporaryDirectory(
        prefix="dartwork-mpl-v5-compat-"
    ) as temp_dir:
        archive_root = Path(temp_dir)
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:") as tar:
            tar.extractall(archive_root)
        environment = os.environ.copy()
        environment["MPLBACKEND"] = "Agg"
        environment["MPLCONFIGDIR"] = str(archive_root / ".mplconfig")
        environment["PYTHONNOUSERSITE"] = "1"
        process = subprocess.run(
            [sys.executable, "-I", "-c", RUNTIME_PROBE, str(archive_root)],
            cwd=archive_root,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
    if process.returncode != 0:
        raise RuntimeError(
            "isolated baseline probe failed:\n"
            f"stdout:\n{process.stdout}\n"
            f"stderr:\n{process.stderr}"
        )
    decoded = json.loads(process.stdout)
    if not isinstance(decoded, dict):
        raise RuntimeError("isolated baseline probe returned a non-object")
    return cast(JsonMap, decoded)


def _canonical_hash(value: object) -> str:
    """Return the compact canonical-JSON SHA-256 for one exact surface.

    Parameters
    ----------
    value : object
        JSON-compatible exact compatibility surface.

    Returns
    -------
    str
        Lowercase hexadecimal SHA-256 digest.
    """
    canonical = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _sequence_size(value: object) -> int:
    """Return the total length of rows in a string-keyed row mapping.

    Parameters
    ----------
    value : object
        Mapping whose values are list-like rows.

    Returns
    -------
    int
        Sum of row lengths.

    Raises
    ------
    TypeError
        If the decoded literal does not have the expected mapping shape.
    """
    if not isinstance(value, dict):
        raise TypeError("expected a row mapping")
    total = 0
    for row in value.values():
        if not isinstance(row, (list, tuple)):
            raise TypeError("expected list-like rows")
        total += len(row)
    return total


def _build_payload(commit: str) -> JsonMap:
    """Assemble and validate the complete frozen compatibility payload.

    Parameters
    ----------
    commit : str
        Full accepted baseline commit.

    Returns
    -------
    dict[str, object]
        Complete schema ``dartwork-mpl.color-compatibility/v1`` payload.

    Raises
    ------
    RuntimeError
        If an inventory or discovery count is incomplete.
    """
    sources = _read_verified_sources(commit)
    generated_path = "src/dartwork_mpl/_colors/_generated.py"
    curated_path = "src/dartwork_mpl/_colors/_curated.py"
    palette = _literal_assignment(sources[generated_path], "PALETTE")
    cycles = _literal_assignment(sources[generated_path], "CYCLES")
    cmaps256 = _literal_assignment(sources[generated_path], "CMAPS_256")
    curated_rows = _literal_assignment(sources[curated_path], "CURATED")
    runtime = _archive_runtime_payload(commit)
    runtime_inventory = runtime.pop("inventory_runtime")
    if not isinstance(runtime_inventory, dict):
        raise RuntimeError("baseline runtime inventory is not an object")
    inventory: JsonMap = {
        "palette_positions": _sequence_size(palette),
        "cycle_positions": _sequence_size(cycles),
        "cmap_positions": _sequence_size(cmaps256),
        **runtime_inventory,
    }
    if inventory != EXPECTED_INVENTORY:
        raise RuntimeError(f"unexpected baseline inventory: {inventory!r}")

    payload: JsonMap = {
        "schema": "dartwork-mpl.color-compatibility/v1",
        "baseline_commit": commit,
        "source_hashes": dict(SOURCE_HASHES),
        "inventory": inventory,
        "palette": palette,
        "cycles": cycles,
        "cmaps256": cmaps256,
        "curated_rows": curated_rows,
        **runtime,
    }
    discovery = payload.get("mcp_discovery")
    if not isinstance(discovery, dict):
        raise RuntimeError("MCP discovery payload is not an object")
    discovery_counts = {
        key: len(value) if isinstance(value, list) else -1
        for key, value in discovery.items()
    }
    if discovery_counts != EXPECTED_DISCOVERY_COUNTS:
        raise RuntimeError(
            f"unexpected MCP discovery inventory: {discovery_counts!r}"
        )
    missing = [surface for surface in EXACT_SURFACES if surface not in payload]
    if missing:
        raise RuntimeError(f"missing exact compatibility surfaces: {missing}")
    payload["canonical_hashes"] = {
        surface: _canonical_hash(payload[surface]) for surface in EXACT_SURFACES
    }
    return payload


def _serialize(payload: JsonMap) -> str:
    """Serialize a compatibility payload deterministically.

    Parameters
    ----------
    payload : dict[str, object]
        Complete compatibility payload.

    Returns
    -------
    str
        Stable pretty-printed JSON ending in exactly one newline.
    """
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
    """Write the manifest atomically at the requested path.

    Parameters
    ----------
    output : pathlib.Path
        Destination JSON path.
    text : str
        Deterministic serialized manifest.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(output, text)


def _parse_args() -> argparse.Namespace:
    """Parse the explicit baseline and optional output arguments.

    Returns
    -------
    argparse.Namespace
        Validated command-line argument namespace.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline-commit",
        required=True,
        help="Pinned v5 Git commit (required; must resolve to the accepted ID)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Manifest destination (default: {DEFAULT_OUTPUT})",
    )
    return parser.parse_args()


def main() -> None:
    """Generate the v5 compatibility manifest from the accepted baseline."""
    args = _parse_args()
    commit = _resolve_baseline(cast(str, args.baseline_commit))
    output = cast(Path, args.output).resolve()
    payload = _build_payload(commit)
    _write_output(output, _serialize(payload))
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
