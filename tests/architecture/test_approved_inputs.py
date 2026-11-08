"""The approved-input manifest and reader: exact files, existing pins, refusals.

``tests.support.approved_inputs`` is the test-side reader for files below
``docs/superpowers``; its manifest lists the exact ten files the user approved
on 2026-11-08. The synthetic checks here run on a private root under
``tmp_path`` that holds files at manifest paths with decoys next to them, so
they need no approved input and prove only what the reader itself does.
``watch_access`` adds in-process evidence that a refused decoy is never
touched; it sees nothing in a child process (``tests.support.excluded_dirs``).
Only the ``approved_input`` test reads the real files.

None of this confines a test that bypasses the reader: product loaders and
child processes open their own paths. The sparse ``approved-inputs`` CI job,
which checks out only the listed files, is what surfaces such a read -- for
the tests that job runs.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from tests.support.approved_inputs import (
    REPO_ROOT,
    ApprovedInputPinError,
    UnapprovedInputError,
    approved_inputs,
    approved_path,
    existing_pin,
    load_manifest,
    read_approved_bytes,
    read_approved_text,
)
from tests.support.excluded_dirs import watch_access

# The exact list the user approved. Changing it is a new approval decision,
# not a test update.
AUTHORIZED_INPUTS = (
    "docs/superpowers/specs/assets/2026-07-14-oklab-centered-color-system/"
    "color_v5_compatibility.json",
    "docs/superpowers/specs/assets/2026-07-14-oklab-centered-color-system/"
    "color_v5_quality.json",
    "docs/superpowers/specs/assets/2026-07-03-color-system-v5/"
    "color_v5_ssot.json",
    "docs/superpowers/plans/2026-07-21-color-rationale-accuracy.md",
    "docs/superpowers/plans/2026-07-17-beginner-friendly-color-docs.md",
    "docs/superpowers/plans/2026-07-14-oklab-centered-color-system.md",
    "docs/superpowers/specs/2026-07-14-oklab-centered-color-system-design.md",
    "docs/superpowers/specs/2026-07-17-beginner-friendly-color-docs-design.md",
    "docs/superpowers/specs/2026-07-21-color-rationale-accuracy-design.md",
    "docs/superpowers/specs/assets/2026-07-17-beginner-friendly-color-docs/"
    "claim-inventory.md",
)
_DOCUMENT = "docs/superpowers/plans/2026-07-21-color-rationale-accuracy.md"
_PINNED = (
    "docs/superpowers/specs/assets/2026-07-14-oklab-centered-color-system/"
    "color_v5_quality.json"
)
_SIBLING_DECOY = "docs/superpowers/plans/2026-07-21-decoy.md"
_SPEC_DECOY = "docs/superpowers/specs/decoy-design.md"
_SCHEMA = "dartwork-mpl.approved-test-inputs/v1"
_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def _synthetic_root(root: Path) -> Path:
    """Write synthetic files at two manifest paths and decoys beside them.

    Returns the decoy outside ``docs/superpowers``.
    """
    for relative, text in (
        (_DOCUMENT, "# synthetic document\n"),
        (_PINNED, '{"synthetic": true}\n'),
        (_SIBLING_DECOY, "sibling decoy\n"),
        (_SPEC_DECOY, "spec decoy\n"),
        ("outside/decoy.md", "outside decoy\n"),
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root / "outside" / "decoy.md"


def _write_manifest(path: Path, inputs: list[object]) -> Path:
    """Write one synthetic manifest with the real schema."""
    path.write_text(
        json.dumps({"schema": _SCHEMA, "inputs": inputs}), encoding="utf-8"
    )
    return path


def test_manifest_lists_exactly_the_authorized_files() -> None:
    """Pin the manifest to the approved ten paths and their kinds."""
    entries = approved_inputs()

    assert tuple(entries) == AUTHORIZED_INPUTS
    assert [
        entry.path for entry in entries.values() if entry.kind == "pinned-json"
    ] == [path for path in AUTHORIZED_INPUTS if path.endswith(".json")]


def test_manifest_pins_are_the_existing_source_pins() -> None:
    """Resolve each JSON pin to the value its product loader already checks."""
    from dartwork_mpl._colors import _ssot
    from dartwork_mpl._colors.construction import _catalog
    from dartwork_mpl._colors.verify import _gates

    recipe_path, recipe_sha256 = _ssot._PINNED_BASELINES["recipe"]
    expected = {
        _catalog._V5_COMPAT_PATH.relative_to(REPO_ROOT).as_posix(): (
            _catalog._V5_COMPAT_SHA256
        ),
        _gates._QUALITY_PATH.relative_to(REPO_ROOT).as_posix(): (
            _gates.QUALITY_FIXTURE_SHA256
        ),
        recipe_path: recipe_sha256,
    }

    assert {
        path: existing_pin(entry)
        for path, entry in approved_inputs().items()
        if entry.kind == "pinned-json"
    } == expected


def test_reader_returns_a_listed_document_as_read_text_would(
    tmp_path: Path,
) -> None:
    """Synthetic positive control: a listed file reads like ``read_text``."""
    _synthetic_root(tmp_path)
    (tmp_path / _DOCUMENT).write_bytes(b"one\r\ntwo\rthree\n")

    assert approved_path(_DOCUMENT, root=tmp_path) == tmp_path / _DOCUMENT
    assert read_approved_text(_DOCUMENT, root=tmp_path) == (
        (tmp_path / _DOCUMENT).read_text(encoding="utf-8")
    )
    assert read_approved_bytes(_DOCUMENT, root=tmp_path) == (
        b"one\r\ntwo\rthree\n"
    )


@pytest.mark.parametrize(
    "relative",
    (
        _SIBLING_DECOY,
        _SPEC_DECOY,
        "outside/decoy.md",
        "docs/superpowers/plans",
        "docs/superpowers/plans/",
        "docs/superpowers/plans/*.md",
        f"./{_DOCUMENT}",
        _DOCUMENT.replace("/plans/", "//plans/"),
        _DOCUMENT.replace("/plans/", "/plans/../plans/"),
    ),
)
def test_reader_refuses_an_unlisted_path_before_touching_disk(
    tmp_path: Path, relative: str
) -> None:
    """Synthetic negative control: only exact manifest strings are read."""
    _synthetic_root(tmp_path)

    with watch_access(tmp_path / "docs", tmp_path / "outside") as accesses:
        with pytest.raises(UnapprovedInputError, match="not an approved"):
            read_approved_bytes(relative, root=tmp_path)

    assert accesses == []


def test_reader_refuses_an_absolute_path_to_a_listed_file(
    tmp_path: Path,
) -> None:
    """An absolute spelling of a listed file is not a manifest entry."""
    _synthetic_root(tmp_path)

    with watch_access(tmp_path / "docs") as accesses:
        with pytest.raises(UnapprovedInputError, match="not an approved"):
            read_approved_bytes(str(tmp_path / _DOCUMENT), root=tmp_path)

    assert accesses == []


def test_reader_refuses_a_symlinked_input_without_following_it(
    tmp_path: Path,
) -> None:
    """A listed path that is a symlink to a decoy is refused, not followed."""
    decoy = _synthetic_root(tmp_path)
    listed = tmp_path / _DOCUMENT
    listed.unlink()
    listed.symlink_to(decoy)

    with watch_access(decoy.parent) as accesses:
        with pytest.raises(UnapprovedInputError, match="symlink"):
            read_approved_bytes(_DOCUMENT, root=tmp_path)

    assert accesses == []


def test_reader_refuses_an_input_below_a_symlinked_directory(
    tmp_path: Path,
) -> None:
    """A symlinked parent directory is an alias too, so it is refused."""
    _synthetic_root(tmp_path)
    plans = tmp_path / "docs" / "superpowers" / "plans"
    elsewhere = tmp_path / "outside" / "plans"
    plans.rename(elsewhere)
    plans.symlink_to(elsewhere, target_is_directory=True)

    with watch_access(elsewhere) as accesses:
        with pytest.raises(UnapprovedInputError, match="symlink"):
            read_approved_bytes(_DOCUMENT, root=tmp_path)

    assert accesses == []


def test_reader_refuses_a_listed_path_that_is_not_a_regular_file(
    tmp_path: Path,
) -> None:
    """A directory at a listed path is refused before any open."""
    _synthetic_root(tmp_path)
    listed = tmp_path / _DOCUMENT
    listed.unlink()
    listed.mkdir()

    with pytest.raises(UnapprovedInputError, match="not a regular file"):
        read_approved_bytes(_DOCUMENT, root=tmp_path)


def test_reader_keeps_file_not_found_for_a_missing_listed_input(
    tmp_path: Path,
) -> None:
    """A missing listed file fails as ``read_text`` would, not as refused."""
    with pytest.raises(FileNotFoundError):
        read_approved_text(_DOCUMENT, root=tmp_path)


def test_reader_rejects_pinned_bytes_that_differ_from_the_existing_pin(
    tmp_path: Path,
) -> None:
    """Synthetic bytes at a pinned path fail the existing pin."""
    _synthetic_root(tmp_path)

    with pytest.raises(ApprovedInputPinError, match="SHA-256 mismatch"):
        read_approved_bytes(_PINNED, root=tmp_path)


def test_existing_pin_refuses_a_pin_recorded_for_another_path(
    tmp_path: Path,
) -> None:
    """A manifest cannot attach a listed file to another file's pin."""
    manifest = load_manifest(
        _write_manifest(
            tmp_path / "manifest.json",
            [
                {
                    "path": "docs/superpowers/specs/other.json",
                    "kind": "pinned-json",
                    "pin_source": "dartwork_mpl._colors._ssot._PINNED_BASELINES",
                    "pin_key": "quality",
                    "purpose": "synthetic",
                }
            ],
        )
    )

    with pytest.raises(ApprovedInputPinError, match="records"):
        existing_pin(manifest["docs/superpowers/specs/other.json"])


@pytest.mark.parametrize(
    ("entry", "message"),
    (
        ({"path": "docs/superpowers/plans/"}, "directory or pattern"),
        ({"path": "docs/superpowers/plans/*.md"}, "directory or pattern"),
        ({"path": "docs/superpowers/plans/[a]b.md"}, "directory or pattern"),
        ({"path": "docs/superpowers/plans/../x.md"}, "normalised"),
        ({"path": "docs/superpowers//x.md"}, "normalised"),
        ({"path": "docs/superpowers/./x.md"}, "normalised"),
        ({"path": "/docs/superpowers/x.md"}, "below"),
        ({"path": "docs/adr/x.md"}, "below"),
        ({"kind": "directory"}, "kind"),
        ({"purpose": ""}, "purpose"),
        ({"pin_key": "recipe"}, "keys"),
        ({"kind": "pinned-json"}, "pin_source"),
    ),
)
def test_manifest_loader_rejects_an_entry_that_is_not_one_exact_file(
    tmp_path: Path, entry: dict[str, object], message: str
) -> None:
    """Directory, glob, unnormalised and malformed entries are rejected."""
    base: dict[str, object] = {
        "path": "docs/superpowers/plans/x.md",
        "kind": "document",
        "purpose": "synthetic",
    }
    manifest = _write_manifest(tmp_path / "manifest.json", [base | entry])

    with pytest.raises(ValueError, match=message):
        load_manifest(manifest)


def test_manifest_loader_rejects_a_duplicate_entry(tmp_path: Path) -> None:
    """One file is listed once; a repeat is a manifest error."""
    entry = {
        "path": "docs/superpowers/plans/x.md",
        "kind": "document",
        "purpose": "synthetic",
    }
    manifest = _write_manifest(tmp_path / "manifest.json", [entry, entry])

    with pytest.raises(ValueError, match="listed twice"):
        load_manifest(manifest)


def test_ci_approved_input_route_checks_out_exactly_the_manifest() -> None:
    """The sparse CI job checks out the manifest files and nothing else below.

    The job runs the ``approved_input`` tests, so a test that reads any other
    ``docs/superpowers`` file fails there with a missing file.
    """
    workflow = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["approved-inputs"]["steps"]
    checkout = next(
        step
        for step in steps
        if str(step.get("uses", "")).startswith("actions/checkout@")
    )
    options = checkout["with"]

    assert options["sparse-checkout-cone-mode"] is False
    assert options["sparse-checkout"].split() == [
        "/*",
        "!/docs/superpowers/",
        *(f"/{path}" for path in approved_inputs()),
    ]
    commands = "\n".join(str(step.get("run", "")) for step in steps)
    assert "-m approved_input" in commands


@pytest.mark.approved_input
def test_approved_inputs_are_regular_files_with_their_existing_pins() -> None:
    """Read every listed input in this checkout through the reader once."""
    for relative, entry in approved_inputs().items():
        raw = read_approved_bytes(relative)

        assert raw, relative
        if entry.kind == "pinned-json":
            assert hashlib.sha256(raw).hexdigest() == existing_pin(entry)
            assert isinstance(json.loads(raw), dict), relative
