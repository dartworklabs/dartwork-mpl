"""The approved-input manifest and reader: exact files, existing pins, refusals.

``tests.support.approved_inputs`` is the test-side reader for files below
``docs/superpowers``; its manifest lists the exact ten files the user approved
on 2026-11-08. The synthetic checks here run on a private root under
``tmp_path`` that holds files at manifest paths with decoys next to them, so
they need no approved input and prove only what the reader itself does:

* a refused path never reaches the filesystem (the ``os`` calls the reader
  could make are replaced by stand-ins that fail if called);
* a component swapped for a symlink at any point of a read -- after each of
  its filesystem calls in turn, the same way every time -- never yields the
  outside bytes;
* every descriptor the reader opens is closed, on success and on refusal.

Only the ``approved_input`` test reads the real files. None of this confines
a test that bypasses the reader: product loaders and child processes open
their own paths. The sparse ``approved-inputs`` CI job, which checks out only
the listed files and then removes its promisor remote, is what surfaces such
a read as a missing file -- for the tests that job runs.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import subprocess
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import cast

import pytest
import yaml

import tests.support.approved_inputs as reader
from tests.support.approved_inputs import (
    REPO_ROOT,
    ApprovedInputPinError,
    UnapprovedInputError,
    approved_inputs,
    existing_pin,
    load_manifest,
    read_approved_bytes,
    read_approved_text,
)

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
_APPROVED_BYTES = b"APPROVED SYNTHETIC\n"
_OUTSIDE_BYTES = b"UNAPPROVED SYNTHETIC\n"
# The filesystem calls a path-based or descriptor-bound reader can make.
_FS_CALLS = ("open", "stat", "lstat", "fstat", "scandir", "listdir")


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


def _under(path: object, root: Path) -> bool:
    """Whether ``path`` is ``root`` or below it, decided without disk access.

    Accepts ``str``, ``bytes`` and path-like arguments and compares them
    with ``os.path.abspath`` only (no symlink resolution). A descriptor is
    not a path, so it is never "under" anything here.
    """
    if isinstance(path, int) or not isinstance(path, str | bytes | os.PathLike):
        return False
    text = os.path.abspath(os.fsdecode(os.fspath(path)))
    base = os.path.abspath(root)
    return text == base or text.startswith(base + os.sep)


def _is_relative(path: object) -> bool:
    """Whether ``path`` is a relative path (resolved against the cwd)."""
    if isinstance(path, int) or not isinstance(path, str | bytes | os.PathLike):
        return False
    return not os.path.isabs(os.fsdecode(os.fspath(path)))


# The real excluded folder. A guarded call never reaches it: the check is
# lexical (``os.path.abspath``) and the call is refused before it runs.
_PROTECTED_DOCS = REPO_ROOT / "docs" / "superpowers"


def _touches(
    args: tuple[object, ...],
    kwargs: dict[str, object],
    root: Path,
    descriptors: list[int],
) -> bool:
    """Whether one ``os`` call could reach a test input or the excluded docs.

    It does when it is relative to a directory descriptor (``dir_fd``),
    when it acts on one of ``descriptors``, when its path is relative (so
    it resolves against the cwd, which may be the repository), or when its
    path is ``root``, ``docs/superpowers`` of this repository, or below
    either. Anything else -- the interpreter, site-packages, a coverage
    tracer canonicalising a code file by absolute path -- is not this
    test's input.
    """
    path = args[0] if args else kwargs.get("path", ".")
    if kwargs.get("dir_fd") is not None:
        return True
    if isinstance(path, int) and not isinstance(path, bool):
        return path in descriptors
    if _is_relative(path):
        return True
    return _under(path, root) or _under(path, _PROTECTED_DOCS)


@contextmanager
def _refusing_filesystem(
    monkeypatch: pytest.MonkeyPatch, root: Path
) -> Iterator[None]:
    """Fail on any filesystem call that ``_touches`` while the block runs.

    That is a call reaching ``root`` or this repository's
    ``docs/superpowers``, a relative path, a ``dir_fd`` call or a call on a
    descriptor. Other calls go to the real functions, so a tracer or the
    test runner that stats its own files by absolute path cannot fail the
    check.
    """
    originals = {name: getattr(os, name) for name in _FS_CALLS}

    def guard(name: str) -> Callable[..., object]:
        original = originals[name]

        def guarded(*args: object, **kwargs: object) -> object:
            if _touches(args, kwargs, root, []):
                raise AssertionError(
                    f"the filesystem was touched: os.{name}{args!r}"
                )
            return original(*args, **kwargs)

        return guarded

    for name in _FS_CALLS:
        monkeypatch.setattr(os, name, guard(name))
    try:
        yield
    finally:
        for name, original in originals.items():
            monkeypatch.setattr(os, name, original)


@contextmanager
def _after_each_call(
    monkeypatch: pytest.MonkeyPatch, root: Path, hook: Callable[[], None]
) -> Iterator[list[int]]:
    """Run ``hook`` after every call that reaches ``root``; yield opened fds.

    Calls that do not reach ``root`` are neither counted nor recorded, so a
    tracer's own filesystem calls cannot move a race's swap point.
    """
    opened: list[int] = []
    originals = {name: getattr(os, name) for name in _FS_CALLS}

    def wrap(name: str) -> Callable[..., object]:
        original = originals[name]

        def wrapped(*args: object, **kwargs: object) -> object:
            reaches = _touches(args, kwargs, root, opened)
            result = original(*args, **kwargs)
            if reaches:
                if name == "open":
                    opened.append(cast(int, result))
                hook()
            return result

        return wrapped

    for name in _FS_CALLS:
        monkeypatch.setattr(os, name, wrap(name))
    try:
        yield opened
    finally:
        for name, original in originals.items():
            monkeypatch.setattr(os, name, original)


def _assert_closed(descriptors: list[int]) -> None:
    """Every descriptor in ``descriptors`` is closed now."""
    for descriptor in descriptors:
        with pytest.raises(OSError) as error:
            os.fstat(descriptor)
        assert error.value.errno == errno.EBADF, descriptor


def test_refusing_guard_blocks_the_synthetic_root_and_nothing_else(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The guard refuses calls that reach the root, and passes the rest.

    A coverage tracer (``sys.monitoring`` on Python 3.12) canonicalises a
    newly run code file with ``os.path.realpath``; that ``lstat`` must not
    count as the reader touching its input.
    """
    (tmp_path / "inside").mkdir()
    descriptor = os.open(tmp_path, os.O_RDONLY)
    try:
        with _refusing_filesystem(monkeypatch, tmp_path):
            assert os.path.realpath(REPO_ROOT) == str(REPO_ROOT.resolve())
            os.lstat(REPO_ROOT)
            os.fstat(descriptor)  # a descriptor alone is not a path
            for path in (
                tmp_path,
                tmp_path / "inside",
                str(tmp_path / "inside" / "missing"),
                os.fsencode(tmp_path / "inside"),
                tmp_path / "inside" / ".." / "inside",
            ):
                with pytest.raises(AssertionError, match="was touched"):
                    os.stat(path)
            with pytest.raises(AssertionError, match="was touched"):
                os.stat("inside", dir_fd=descriptor)
            with pytest.raises(AssertionError, match="was touched"):
                os.open(tmp_path, os.O_RDONLY)
    finally:
        os.close(descriptor)


def test_refusing_guard_blocks_relative_and_excluded_docs_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Relative paths and this repository's docs/superpowers are refused.

    These paths must never reach the disk, so the guard here wraps a
    backstop in place of the real functions: the backstop records any such
    path that gets past the guard and returns without touching the disk,
    and the cwd is a synthetic folder. The assertions are that the guard
    raised and the backstop saw nothing.
    """
    work = tmp_path / "cwd"
    work.mkdir()
    monkeypatch.chdir(work)
    real = {name: getattr(os, name) for name in _FS_CALLS}
    protected = os.path.abspath(_PROTECTED_DOCS)
    leaked: list[tuple[str, object]] = []

    def backstop(name: str) -> Callable[..., object]:
        def call(*args: object, **kwargs: object) -> object:
            path = args[0] if args else kwargs.get("path", ".")
            if isinstance(path, str | bytes | os.PathLike):
                text = os.fsdecode(os.fspath(path))
                absolute = os.path.abspath(text)
                if (
                    not os.path.isabs(text)
                    or absolute == protected
                    or absolute.startswith(protected + os.sep)
                ):
                    leaked.append((name, path))
                    return None
            return real[name](*args, **kwargs)

        return call

    for name in _FS_CALLS:
        monkeypatch.setattr(os, name, backstop(name))
    forbidden: tuple[str | bytes | Path, ...] = (
        "docs/superpowers/specs/decoy-design.md",
        b"docs/superpowers/specs/decoy-design.md",
        Path("docs/superpowers/specs/decoy-design.md"),
        "outside/decoy.md",
        _PROTECTED_DOCS,
        _PROTECTED_DOCS / "specs" / "decoy-design.md",
        str(_PROTECTED_DOCS / "plans" / ".." / "specs" / "decoy-design.md"),
        os.fsencode(_PROTECTED_DOCS / "specs"),
    )

    with _refusing_filesystem(monkeypatch, tmp_path / "root"):
        for path in forbidden:
            for function in (os.stat, os.lstat):
                with pytest.raises(AssertionError, match="was touched"):
                    function(path)
        with pytest.raises(AssertionError, match="was touched"):
            os.listdir()
        os.lstat(REPO_ROOT / "docs")  # the parent folder is outside both

    assert leaked == []


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
        _DOCUMENT.upper(),
        _DOCUMENT + "\0",
    ),
)
def test_reader_refuses_an_unlisted_path_before_touching_disk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, relative: str
) -> None:
    """Synthetic negative control: only exact manifest strings are read."""
    _synthetic_root(tmp_path)

    with _refusing_filesystem(monkeypatch, tmp_path):
        with pytest.raises(UnapprovedInputError, match="not an approved"):
            read_approved_bytes(relative, root=tmp_path)


def test_reader_refuses_an_absolute_path_to_a_listed_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An absolute spelling of a listed file is not a manifest entry."""
    _synthetic_root(tmp_path)

    with _refusing_filesystem(monkeypatch, tmp_path):
        with pytest.raises(UnapprovedInputError, match="not an approved"):
            read_approved_bytes(str(tmp_path / _DOCUMENT), root=tmp_path)


def test_reader_refuses_a_platform_without_descriptor_relative_opens(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No fallback to a path-based walk where ``dir_fd`` is unavailable."""
    _synthetic_root(tmp_path)
    monkeypatch.setattr(
        reader, "MISSING_DESCRIPTOR_SUPPORT", ("os.open(dir_fd=...)",)
    )

    with _refusing_filesystem(monkeypatch, tmp_path):
        with pytest.raises(UnapprovedInputError, match="descriptor-relative"):
            read_approved_bytes(_DOCUMENT, root=tmp_path)


def test_this_platform_supports_the_descriptor_bound_walk() -> None:
    """The platforms the suite runs on have every capability the walk needs."""
    assert reader.MISSING_DESCRIPTOR_SUPPORT == ()


def test_reader_refuses_a_symlinked_input_without_following_it(
    tmp_path: Path,
) -> None:
    """A listed path that is a symlink to a decoy is refused, not followed."""
    decoy = _synthetic_root(tmp_path)
    listed = tmp_path / _DOCUMENT
    listed.unlink()
    listed.symlink_to(decoy)

    with pytest.raises(UnapprovedInputError, match="symlink"):
        read_approved_bytes(_DOCUMENT, root=tmp_path)


@pytest.mark.parametrize(
    "component", ["docs", "docs/superpowers", "docs/superpowers/plans"]
)
def test_reader_refuses_an_input_below_a_symlinked_directory(
    tmp_path: Path, component: str
) -> None:
    """A symlinked parent directory is an alias too, so it is refused."""
    _synthetic_root(tmp_path)
    directory = tmp_path / component
    elsewhere = tmp_path / "outside" / "moved"
    directory.rename(elsewhere)
    directory.symlink_to(elsewhere, target_is_directory=True)

    with pytest.raises(UnapprovedInputError, match="symlink"):
        read_approved_bytes(_DOCUMENT, root=tmp_path)


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


def _replace_parent_with_file(root: Path) -> None:
    """Put a regular file where the listed path needs a directory."""
    plans = root / "docs/superpowers/plans"
    for child in plans.iterdir():
        child.unlink()
    plans.rmdir()
    plans.write_text("not a directory\n", encoding="utf-8")


def _link_parent(root: Path) -> None:
    """Replace the listed file's directory with a symlink to it."""
    plans = root / "docs/superpowers/plans"
    plans.rename(root / "outside" / "plans")
    plans.symlink_to(root / "outside" / "plans", target_is_directory=True)


def _link_file(root: Path) -> None:
    """Replace the listed file with a symlink to the outside decoy."""
    (root / _DOCUMENT).unlink()
    (root / _DOCUMENT).symlink_to(root / "outside" / "decoy.md")


def _directory_file(root: Path) -> None:
    """Replace the listed file with a directory."""
    (root / _DOCUMENT).unlink()
    (root / _DOCUMENT).mkdir()


@pytest.mark.parametrize(
    ("relative", "arrange", "expected"),
    [
        (_DOCUMENT, lambda root: None, None),
        (
            _DOCUMENT,
            lambda root: (root / _DOCUMENT).unlink(),
            FileNotFoundError,
        ),
        (_DOCUMENT, _replace_parent_with_file, UnapprovedInputError),
        (_DOCUMENT, _link_parent, UnapprovedInputError),
        (_DOCUMENT, _link_file, UnapprovedInputError),
        (_DOCUMENT, _directory_file, UnapprovedInputError),
        (_PINNED, lambda root: None, ApprovedInputPinError),
    ],
    ids=[
        "read",
        "missing-file",
        "parent-is-a-file",
        "symlinked-parent",
        "symlinked-file",
        "directory-file",
        "pin-mismatch",
    ],
)
def test_reader_closes_every_descriptor_it_opens(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    relative: str,
    arrange: Callable[[Path], None],
    expected: type[Exception] | None,
) -> None:
    """Success and every refusal path leave no descriptor open."""
    _synthetic_root(tmp_path)
    arrange(tmp_path)

    with _after_each_call(monkeypatch, tmp_path, lambda: None) as opened:
        if expected is None:
            read_approved_bytes(relative, root=tmp_path)
        else:
            with pytest.raises(expected):
                read_approved_bytes(relative, root=tmp_path)

    assert opened
    _assert_closed(opened)


def _race_tree(base: Path) -> tuple[Path, Path]:
    """Create a root and an outside tree that both hold the listed path."""
    root, outside = base / "root", base / "outside"
    for tree, raw in ((root, _APPROVED_BYTES), (outside, _OUTSIDE_BYTES)):
        listed = tree / _DOCUMENT
        listed.parent.mkdir(parents=True)
        listed.write_bytes(raw)
    return root, outside


def _swap(root: Path, outside: Path, component: str) -> None:
    """Move ``component`` aside and put a symlink into ``outside`` there."""
    target = root / component
    is_directory = component != _DOCUMENT
    target.rename(target.with_name(target.name + ".moved"))
    target.symlink_to(outside / component, target_is_directory=is_directory)


def _outcome(root: Path) -> str:
    """Classify one read of the listed document below ``root``."""
    try:
        raw = read_approved_bytes(_DOCUMENT, root=root)
    except UnapprovedInputError:
        return "refused"
    except FileNotFoundError:
        return "missing"
    if raw == _APPROVED_BYTES:
        return "approved"
    return "OUTSIDE" if raw == _OUTSIDE_BYTES else "other"


def _race_sweep(
    base: Path, component: str, monkeypatch: pytest.MonkeyPatch
) -> list[str]:
    """Swap ``component`` after the k-th filesystem call, for every k.

    k = 0 swaps before the read; the largest k swaps after its last call.
    Each read must close every descriptor it opened.
    """
    calls = 0

    def count() -> None:
        nonlocal calls
        calls += 1

    root, _ = _race_tree(base / "count")
    with _after_each_call(monkeypatch, base, count):
        assert _outcome(root) == "approved"
    total = calls

    outcomes: list[str] = []
    for swap_after in range(total + 1):
        root, outside = _race_tree(base / f"swap-after-{swap_after}")
        seen = 0

        def maybe_swap(
            root: Path = root, outside: Path = outside, at: int = swap_after
        ) -> None:
            nonlocal seen
            seen += 1
            if seen == at:
                _swap(root, outside, component)

        if swap_after == 0:
            _swap(root, outside, component)
        with _after_each_call(monkeypatch, base, maybe_swap) as opened:
            outcomes.append(_outcome(root))
        _assert_closed(opened)
    return outcomes


@pytest.mark.parametrize(
    "component",
    ["docs", "docs/superpowers", "docs/superpowers/plans", _DOCUMENT],
    ids=["docs", "superpowers", "plans", "file"],
)
def test_a_component_swapped_mid_read_never_yields_outside_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, component: str
) -> None:
    """Deterministic race: swap after each filesystem call of one read.

    The swap point is fixed by call count, so two sweeps give the same
    outcomes. No swap point may return the outside bytes; a swap before the
    read is refused, and one after its last call leaves the read intact.
    """
    first = _race_sweep(tmp_path / "first", component, monkeypatch)
    second = _race_sweep(tmp_path / "second", component, monkeypatch)

    assert first == second
    assert "OUTSIDE" not in first, first
    assert (first[0], first[-1]) == ("refused", "approved"), first


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
    """The sparse CI job checks out the manifest files, then drops its remote.

    The job runs the ``approved_input`` tests, so a test that reads any other
    ``docs/superpowers`` file fails there with a missing file. Removing the
    promisor remote right after checkout keeps a missing blob from being
    fetched, whatever the Git version.
    """
    workflow = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["approved-inputs"]["steps"]
    runs = [str(step.get("run", "")) for step in steps]
    checkout_index = next(
        index
        for index, step in enumerate(steps)
        if str(step.get("uses", "")).startswith("actions/checkout@")
    )
    options = steps[checkout_index]["with"]
    removal_index = next(
        index
        for index, run in enumerate(runs)
        if "git remote remove origin" in run
    )
    test_index = next(
        index for index, run in enumerate(runs) if "-m approved_input" in run
    )

    assert options["sparse-checkout-cone-mode"] is False
    assert options["persist-credentials"] is False
    assert options["sparse-checkout"].split() == [
        "/*",
        "!/docs/superpowers/",
        *(f"/{path}" for path in approved_inputs()),
    ]
    assert removal_index == checkout_index + 1
    assert 'test -z "$(git remote)"' in runs[removal_index]
    assert removal_index < test_index


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    """Run Git with no user or system config and no lazy-fetch switch."""
    environment = {
        key: value
        for key, value in os.environ.items()
        if key != "GIT_NO_LAZY_FETCH"
    }
    environment |= {
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "synthetic",
        "GIT_AUTHOR_EMAIL": "synthetic@example.invalid",
        "GIT_COMMITTER_NAME": "synthetic",
        "GIT_COMMITTER_EMAIL": "synthetic@example.invalid",
    }
    return subprocess.run(
        ["git", *args], cwd=cwd, env=environment, capture_output=True
    )


def _sparse_partial_clone(source: Path, clone: Path) -> None:
    """Clone without blobs, then check out only ``kept.txt``."""
    for args in (
        (
            "clone",
            "-q",
            "--no-checkout",
            "--filter=blob:none",
            f"file://{source}",
            str(clone),
        ),
        ("-C", str(clone), "sparse-checkout", "set", "--no-cone", "/kept.txt"),
        ("-C", str(clone), "checkout", "-q", "main"),
    ):
        assert _git(clone.parent, *args).returncode == 0, args


def test_removing_the_promisor_remote_stops_lazy_fetch(tmp_path: Path) -> None:
    """Synthetic control for the CI step, independent of the Git version.

    In a blob-less sparse clone the excluded blob is missing. With the remote
    kept, reading it fetches it (positive control); once the remote is
    removed the same read fails and the blob stays missing. No lazy-fetch
    environment switch is set.
    """
    source = tmp_path / "source"
    (source / "excluded").mkdir(parents=True)
    (source / "kept.txt").write_text("kept\n", encoding="utf-8")
    (source / "excluded" / "decoy.txt").write_text("decoy\n", encoding="utf-8")
    for args in (
        ("init", "-q", "--initial-branch=main"),
        ("add", "--", "kept.txt", "excluded/decoy.txt"),
        ("commit", "-q", "--no-gpg-sign", "-m", "synthetic"),
        ("config", "uploadpack.allowFilter", "true"),
    ):
        assert _git(source, *args).returncode == 0, args
    decoy = _git(source, "rev-parse", "HEAD:excluded/decoy.txt")
    decoy_id = decoy.stdout.decode("ascii").strip()

    kept_remote = tmp_path / "kept-remote"
    _sparse_partial_clone(source, kept_remote)
    removed_remote = tmp_path / "removed-remote"
    _sparse_partial_clone(source, removed_remote)
    assert _git(removed_remote, "remote", "remove", "origin").returncode == 0
    assert _git(removed_remote, "remote").stdout == b""

    missing = _git(
        removed_remote, "rev-list", "--objects", "--missing=print", "HEAD"
    )
    assert f"?{decoy_id}".encode() in missing.stdout.split()
    assert (removed_remote / "kept.txt").read_text(encoding="utf-8") == "kept\n"

    fetched = _git(kept_remote, "cat-file", "-p", decoy_id)
    assert (fetched.returncode, fetched.stdout) == (0, b"decoy\n")

    refused = _git(removed_remote, "cat-file", "-p", decoy_id)
    assert refused.returncode != 0
    still_missing = _git(
        removed_remote, "rev-list", "--objects", "--missing=print", "HEAD"
    )
    assert f"?{decoy_id}".encode() in still_missing.stdout.split()


@pytest.mark.approved_input
def test_approved_inputs_are_regular_files_with_their_existing_pins() -> None:
    """Read every listed input in this checkout through the reader once."""
    for relative, entry in approved_inputs().items():
        raw = read_approved_bytes(relative)

        assert raw, relative
        if entry.kind == "pinned-json":
            assert hashlib.sha256(raw).hexdigest() == existing_pin(entry)
            assert isinstance(json.loads(raw), dict), relative
