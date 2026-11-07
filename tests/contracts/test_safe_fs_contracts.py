"""One condition matrix pins how each descriptor-confined file caller answers.

MCP artifacts and the UI viewer each open files through no-follow directory
handles, but their admission policies differ on purpose. ``CONTRACT`` below is
the decision record: every caller faces the same seven conditions and the
table states the current answer, accepted or refused. A change to any cell
is a security decision, not a test fix.

Why each caller's policy differs:

- store root: owned by the effective uid (files the process creates belong
  to it). Intermediate components are only no-follow directories, so a
  store under a group-writable (0775) parent is accepted. The root's
  (dev, ino) is pinned at configuration and compared at every later open, so
  whoever can write that parent and swaps the root by rename is refused.
- store member: owned, single-link, 0600 regular files only, read through the
  opened descriptor; identity, size, times and link count are compared after
  reading, so a name swapped mid-read (the old object loses its link) fails.
- input_access: every ancestor from ``/`` must be root- or euid-owned and not
  group/other writable, because the operator's authority comes from a policy
  file and the roots it names; a writable ancestor could swap that authority.
  Copy sources may have other hard links (no origin-uniqueness claim).
- input_cleanup: works below storage already vetted by input_access, so only
  its own fixed names are checked: euid-owned, 0700 sets, 0600 single-link
  members, each name re-bound to the pinned descriptor before every effect.
- ui saving: startup roots are trusted configuration (symlinks resolved once);
  request paths are pinned per component and outputs are create-only. Modes
  follow the umask like an ordinary save, so no mode is required.
- ui state: the two fixed names live directly under the user's own pinned
  root. Anyone who can write that root is already the same user, so hard
  links, foreign owners and loose modes are read as they are; symlinks and
  non-regular files are refused.

Outside the matrix: store capability detection refuses each missing
operation; UI modules import without ``os.O_NOFOLLOW`` (flags are computed
lazily); input capability detection does not list the dir_fd operations
``inputs.py`` uses, which is safe only because a store ConfigurationError
keeps the lifecycle from opening inputs at all.
"""

import io
import json
import os
import stat
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

pytest.importorskip("fastmcp")

from dartwork_mpl.mcp.artifacts import configure_store, input_access, lifecycle
from dartwork_mpl.mcp.artifacts import input_cleanup as cleanup
from dartwork_mpl.mcp.artifacts import store as disk
from dartwork_mpl.mcp.artifacts.input_policy import CopyInput
from dartwork_mpl.mcp.artifacts.policy import (
    ArtifactId,
    ArtifactMember,
    ConfigurationError,
    CorruptArtifact,
    InvalidRequest,
    PublicationError,
    StoredBundle,
)
from dartwork_mpl.mcp.artifacts.store import ArtifactStore
from dartwork_mpl.ui import saving
from dartwork_mpl.ui.platform import fs
from dartwork_mpl.ui.state import StateFile
from dartwork_mpl.ui.state import _store as state

ACCEPTED, REFUSED = "accepted", "refused"
NOW = datetime(2026, 11, 7, 1, 2, 3, tzinfo=UTC)
REPORT = {
    "status": "ok",
    "validation_complete": True,
    "failed_checks": [],
    "stdout": "",
    "stderr": "",
    "visual_warnings": [],
}

#: Conditions: final_link (last component is a symlink), parent_link (a
#: component above it is), nlink_2 (a second hard link), fifo, writable_parent
#: (a 0775 parent above the object), private_0755 (0755 where a private 0700
#: directory would be), replaced (the name is swapped after the caller opened
#: or pinned the object). Directory-only callers have no nlink_2 cell.
CONTRACT: dict[str, dict[str, str]] = {
    "store_root": {
        "final_link": REFUSED,
        "parent_link": REFUSED,
        "fifo": REFUSED,
        "writable_parent": ACCEPTED,
        "private_0755": REFUSED,
        "replaced": REFUSED,
    },
    "store_member": {
        "final_link": REFUSED,
        "parent_link": REFUSED,
        "nlink_2": REFUSED,
        "fifo": REFUSED,
        "writable_parent": ACCEPTED,
        "private_0755": REFUSED,
        "replaced": REFUSED,
    },
    "input_access": {
        "final_link": REFUSED,
        "parent_link": REFUSED,
        "nlink_2": ACCEPTED,
        "fifo": REFUSED,
        "writable_parent": REFUSED,
        "private_0755": REFUSED,
        "replaced": REFUSED,
    },
    "input_cleanup": {
        "final_link": REFUSED,
        "parent_link": REFUSED,
        "nlink_2": REFUSED,
        "fifo": REFUSED,
        "writable_parent": ACCEPTED,
        "private_0755": REFUSED,
        "replaced": REFUSED,
    },
    "ui_saving": {
        "final_link": REFUSED,
        "parent_link": REFUSED,
        "nlink_2": REFUSED,
        "fifo": REFUSED,
        "writable_parent": ACCEPTED,
        "private_0755": ACCEPTED,
        "replaced": REFUSED,
    },
    "ui_state": {
        "final_link": REFUSED,
        "parent_link": ACCEPTED,
        "nlink_2": ACCEPTED,
        "fifo": REFUSED,
        "writable_parent": ACCEPTED,
        "private_0755": ACCEPTED,
        "replaced": REFUSED,
    },
}


def directory(path: Path, mode: int) -> Path:
    """Create a directory with an exact mode, independent of the process umask."""
    path.mkdir()
    path.chmod(mode)
    return path


def regular(path: Path, data: bytes, mode: int = 0o600) -> Path:
    """Create a regular file with an exact mode, independent of the umask."""
    path.write_bytes(data)
    path.chmod(mode)
    return path


@pytest.fixture
def owned_root() -> Iterator[Path]:
    """Yield a 0700 folder whose every ancestor input_access would admit.

    Mirrors ``tests/mcp/artifacts/conftest.py``: runner checkouts and /tmp may
    have writable ancestors, so input admission is observed under home.
    """
    home = Path.home().resolve(strict=True)
    for ancestor in (home, *home.parents):
        info = ancestor.lstat()
        assert stat.S_ISDIR(info.st_mode) and not ancestor.is_symlink()
        assert info.st_uid in {0, os.geteuid()} and not info.st_mode & 0o022
    with tempfile.TemporaryDirectory(prefix="dmpl-safefs-", dir=home) as raw:
        yield Path(raw)


def configured(root: Path) -> ArtifactStore:
    """Configure a real store and fail loudly on fixture errors."""
    store = configure_store(str(root))
    assert isinstance(store, ArtifactStore), store
    return store


def published(store: ArtifactStore) -> StoredBundle:
    """Publish one bundle through the declared staging API."""
    with store.staging() as stage:
        stage.output_stem.with_suffix(".png").write_bytes(b"png bytes")
        stage.output_stem.with_suffix(".pdf").write_bytes(b"pdf bytes")
        result = store.publish(stage, b"source", REPORT, NOW)
    assert isinstance(result, StoredBundle), result
    return result


def probe_store_root(condition: str, base: Path) -> str:
    """Configure, then use, a store root prepared for one condition."""
    parent = directory(base / "parent", 0o755)
    root = parent / "artifacts"
    if condition == "final_link":
        real = directory(base / "real", 0o700)
        root.symlink_to(real, target_is_directory=True)
    elif condition == "parent_link":
        directory(directory(base / "real", 0o755) / "artifacts", 0o700)
        parent = base / "linked"
        parent.symlink_to(base / "real", target_is_directory=True)
        root = parent / "artifacts"
    elif condition == "fifo":
        os.mkfifo(root)
    elif condition == "writable_parent":
        parent.chmod(0o775)
        directory(root, 0o700)
    elif condition == "private_0755":
        directory(root, 0o755)
    else:
        directory(root, 0o700)
    store = configure_store(str(root))
    if isinstance(store, ConfigurationError):
        return REFUSED
    if condition == "replaced":
        root.rename(parent / "previous")
        directory(root, 0o700)
    try:
        published(store)
    except OSError:
        return REFUSED
    return ACCEPTED


def probe_store_member(
    condition: str, base: Path, monkeypatch: pytest.MonkeyPatch
) -> str:
    """Publish a real bundle, alter one member or its folder, then load it."""
    parent = directory(base / "parent", 0o755)
    if condition == "writable_parent":
        parent.chmod(0o775)
    store = configured(parent / "artifacts")
    bundle = published(store)
    identity = bundle.manifest.artifact_id
    folder = parent / "artifacts" / identity.value
    png = folder / ArtifactMember.PNG.value
    outside = directory(base / "outside", 0o700)
    if condition == "final_link":
        copy = regular(outside / "plot.png", png.read_bytes())
        png.unlink()
        png.symlink_to(copy)
    elif condition == "parent_link":
        twin = directory(outside / "twin", 0o700)
        for member in folder.iterdir():
            regular(twin / member.name, member.read_bytes())
        folder.rename(outside / "original")
        folder.symlink_to(twin, target_is_directory=True)
    elif condition == "nlink_2":
        os.link(png, outside / "alias")
    elif condition == "fifo":
        png.unlink()
        os.mkfifo(png, 0o600)
    elif condition == "private_0755":
        folder.chmod(0o755)
    replacement = regular(outside / "replacement", b"other bytes")
    real_open = os.open

    def swap_after_open(path, flags, mode=0o777, *, dir_fd=None):
        """Replace the member's name right after the store opened it."""
        fd = real_open(path, flags, mode, dir_fd=dir_fd)
        if path == ArtifactMember.PNG.value and replacement.exists():
            os.rename(replacement, png)
        return fd

    with monkeypatch.context() as patch:
        if condition == "replaced":
            patch.setattr(disk.os, "open", swap_after_open)
        result = store.load(identity, NOW)
    if isinstance(result, CorruptArtifact):
        return REFUSED
    assert isinstance(result, StoredBundle), result
    assert result.contents == bundle.contents
    return ACCEPTED


def write_policy(root: Path, storage: Path, source: Path) -> Path:
    """Write a private policy naming one storage and one copy root."""
    path = root / "policy.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "storage_dir": str(storage),
                "copy_roots": {"data": str(source)},
            }
        )
    )
    path.chmod(0o600)
    return path


def probe_input_access(condition: str, base: Path) -> str:
    """Authorize a policy laid out for one condition, then use the grant."""
    storage = base / "storage"
    source = directory(base / "source", 0o700)
    if condition == "writable_parent":
        storage = directory(base / "shared", 0o775) / "storage"
    directory(storage, 0o755 if condition == "private_0755" else 0o700)
    named = source
    if condition == "final_link":
        named = base / "source-link"
        named.symlink_to(source, target_is_directory=True)
    elif condition == "parent_link":
        directory(directory(base / "real", 0o700) / "source", 0o700)
        (base / "linked").symlink_to(base / "real", target_is_directory=True)
        named = base / "linked" / "source"
    store = configured(base / "artifacts")
    grant = input_access.authorize_inputs(
        str(write_policy(base, storage, named)), store.check_input_roots
    )
    if isinstance(grant, ConfigurationError):
        return REFUSED
    assert isinstance(grant, input_access.InputGrant), grant
    try:
        if condition == "replaced":
            storage.rename(base / "previous")
            directory(storage, 0o700)
            opened = grant.duplicate_storage()
        else:
            sample = source / "sample.csv"
            if condition == "fifo":
                os.mkfifo(sample, 0o600)
            else:
                regular(sample, b"x")
            if condition == "nlink_2":
                os.link(sample, source / "alias.csv")
            opened = grant.open_copy(
                CopyInput("s", "data", "sample.csv", "0" * 64)
            )
        if isinstance(opened, (ConfigurationError, InvalidRequest)):
            return REFUSED
        opened.close()
        return ACCEPTED
    finally:
        grant.close()


def probe_input_cleanup(condition: str, base: Path) -> str:
    """Open one fixed set and member, then re-bind the set as removal does."""
    root = directory(base / "storage", 0o700)
    if condition == "writable_parent":
        root.chmod(0o775)
    outside = directory(base / "outside", 0o700)
    folder = root / "set"
    if condition == "parent_link":
        folder.symlink_to(directory(outside / "set", 0o700))
        folder = outside / "set"
    else:
        directory(folder, 0o755 if condition == "private_0755" else 0o700)
    member = folder / "inputs.json"
    if condition == "final_link":
        member.symlink_to(regular(outside / "inputs.json", b"{}"))
    elif condition == "fifo":
        os.mkfifo(member, 0o600)
    else:
        regular(member, b"{}")
    if condition == "nlink_2":
        os.link(member, outside / "alias")
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        set_fd = cleanup.open_set(root_fd, "set")
        try:
            os.close(cleanup.open_member(set_fd, "inputs.json"))
            if condition == "replaced":
                (root / "set").rename(root / "previous")
                directory(root / "set", 0o700)
            cleanup.binding(root_fd, "set", set_fd, True)
        finally:
            os.close(set_fd)
    except OSError:
        return REFUSED
    finally:
        os.close(root_fd)
    return ACCEPTED


def opened_roots(root: Path, base: Path) -> fs.RootScope:
    """Open startup roots through the viewer's trusted configuration path."""
    scope = fs.open_roots(root, None, cwd=base)
    assert isinstance(scope, fs.RootScope), scope
    return scope


def probe_ui_saving(condition: str, base: Path) -> str:
    """Save one output into a primary root laid out for one condition."""
    parent = directory(
        base / "parent", 0o775 if condition == "writable_parent" else 0o755
    )
    root = directory(parent / "primary", 0o755)
    outside = directory(base / "outside", 0o755)
    name = "figure.png"
    target = root / name
    if condition == "final_link":
        target.symlink_to(regular(outside / "figure.png", b"old", 0o644))
    elif condition == "parent_link":
        (root / "sub").symlink_to(outside, target_is_directory=True)
        name = "sub/figure.png"
    elif condition == "nlink_2":
        os.link(regular(outside / "figure.png", b"old", 0o644), target)
    elif condition == "fifo":
        os.mkfifo(target, 0o644)
    elif condition == "writable_parent":
        root.chmod(0o775)
    with opened_roots(root, base) as scope:
        if condition == "replaced":
            root.rename(parent / "previous")
            directory(root, 0o755)
        output = saving.parse_output(name)
        assert isinstance(output, saving.RelativeOutput), output
        plan = saving.prepare_save(scope, output, include_copies=True)
        if not isinstance(plan, saving.PreparedSave):
            return REFUSED
        with plan:
            result = saving.commit_save(plan, io.BytesIO(b"new"))
    assert (
        not (outside / "figure.png").exists()
        or (outside / "figure.png").read_bytes() == b"old"
    )
    return ACCEPTED if isinstance(result, saving.SaveReceipt) else REFUSED


def probe_ui_state(condition: str, base: Path) -> str:
    """Read one fixed state name under a root laid out for one condition."""
    parent = directory(
        base / "parent", 0o775 if condition == "writable_parent" else 0o755
    )
    root = directory(parent / "primary", 0o700)
    configured_root = root
    target = root / StateFile.CONFIG.value
    outside = directory(base / "outside", 0o700)
    if condition == "final_link":
        target.symlink_to(regular(outside / "state.json", b"{}"))
    elif condition == "parent_link":
        configured_root = base / "linked"
        configured_root.symlink_to(root, target_is_directory=True)
        regular(target, b"{}")
    elif condition == "fifo":
        os.mkfifo(target, 0o600)
    elif condition == "private_0755":
        root.chmod(0o755)
        regular(target, b"{}", 0o644)
    else:
        regular(target, b"{}")
    if condition == "nlink_2":
        os.link(target, outside / "alias")
    if condition == "writable_parent":
        root.chmod(0o775)
    with opened_roots(configured_root, base) as scope:
        if condition == "replaced":
            root.rename(parent / "previous")
            directory(root, 0o700)
            regular(target, b"{}")
        result = state.FixedStateStore(scope).read(
            StateFile.CONFIG, max_bytes=64
        )
    return ACCEPTED if result == b"{}" else REFUSED


CASES = [
    (caller, condition, expected)
    for caller, row in CONTRACT.items()
    for condition, expected in row.items()
]


@pytest.mark.parametrize(
    ("caller", "condition", "expected"),
    CASES,
    ids=[f"{caller}-{condition}" for caller, condition, _ in CASES],
)
def test_condition_matrix_matches_recorded_contract(
    tmp_path: Path,
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
    caller: str,
    condition: str,
    expected: str,
) -> None:
    """Every caller still answers each shared condition as CONTRACT records."""
    probes: dict[str, Callable[[str, Path], str]] = {
        "store_root": probe_store_root,
        "store_member": lambda c, b: probe_store_member(c, b, monkeypatch),
        "input_access": probe_input_access,
        "input_cleanup": probe_input_cleanup,
        "ui_saving": probe_ui_saving,
        "ui_state": probe_ui_state,
    }
    base = (
        request.getfixturevalue("owned_root")
        if caller == "input_access"
        else directory(tmp_path / "case", 0o700)
    )
    assert probes[caller](condition, base) == expected


def test_store_tolerates_writable_parent_because_root_identity_is_pinned(
    tmp_path: Path, owned_root: Path
) -> None:
    """A 0775 parent is accepted; a rename swap through it is refused next open.

    input_access refuses the same layout outright, because its authority comes
    from the walked policy ancestry rather than one pinned root identity.
    """
    shared = directory(tmp_path / "shared", 0o775)
    root = directory(shared / "artifacts", 0o700)
    store = configured(root)
    bundle = published(store)
    root.rename(shared / "previous")
    directory(root, 0o700)
    with pytest.raises(OSError):
        published(store)
    unknown = ArtifactId(uuid4().hex)
    assert isinstance(store.observe_commit(unknown), PublicationError)
    assert isinstance(
        store.load(bundle.manifest.artifact_id, NOW), CorruptArtifact
    )
    assert list(root.iterdir()) == []
    assert (shared / "previous" / bundle.manifest.artifact_id.value).is_dir()
    held = directory(owned_root / "shared", 0o775)
    storage = directory(held / "storage", 0o700)
    source = directory(owned_root / "source", 0o700)
    grant = input_access.authorize_inputs(
        str(write_policy(owned_root, storage, source)),
        configured(owned_root / "artifacts").check_input_roots,
    )
    assert isinstance(grant, ConfigurationError)


STORE_CAPABILITIES = [
    ("attribute", "O_NOFOLLOW"),
    ("attribute", "O_DIRECTORY"),
    ("attribute", "O_NONBLOCK"),
    ("attribute", "geteuid"),
    ("attribute", "fchmod"),
    ("attribute", "fstat"),
    ("attribute", "fsync"),
    *(
        ("dir_fd", name)
        for name in (
            "open",
            "mkdir",
            "stat",
            "unlink",
            "rmdir",
            "rename",
            "link",
        )
    ),
    ("fd", "listdir"),
    ("follow_symlinks", "link"),
]


@pytest.mark.parametrize(
    ("kind", "name"),
    STORE_CAPABILITIES,
    ids=[f"{kind}-{name}" for kind, name in STORE_CAPABILITIES],
)
def test_store_refuses_each_missing_capability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str, name: str
) -> None:
    """Each operation the store uses is detected; a gap refuses configuration."""
    root = tmp_path / "artifacts"
    with monkeypatch.context() as patch:
        if kind == "attribute":
            patch.delattr(disk.os, name)
        else:
            supported = {
                "dir_fd": "supports_dir_fd",
                "fd": "supports_fd",
                "follow_symlinks": "supports_follow_symlinks",
            }[kind]
            remaining = getattr(os, supported) - {getattr(os, name)}
            patch.setattr(disk.os, supported, remaining)
        result = configure_store(str(root))
    assert isinstance(result, ConfigurationError)
    assert not root.exists()


@pytest.mark.parametrize("which", ["real_only", "effective_only"])
def test_store_ownership_follows_the_effective_uid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, which: str
) -> None:
    """Files the process creates belong to its effective uid; getuid is ignored.

    Only one of the two ids is moved to a foreign value. Moving the real uid
    keeps the store working; moving the effective uid refuses the same root.
    """
    root = directory(tmp_path / "artifacts", 0o700)
    foreign = os.geteuid() + 1
    with monkeypatch.context() as patch:
        if which == "real_only":
            patch.setattr(disk.os, "getuid", lambda: foreign)
            store = configured(root)
            bundle = published(store)
            loaded = store.load(bundle.manifest.artifact_id, NOW)
            assert isinstance(loaded, StoredBundle), loaded
        else:
            patch.setattr(disk.os, "geteuid", lambda: foreign)
            assert isinstance(configure_store(str(root)), ConfigurationError)


@pytest.mark.parametrize(
    "operation", ["mkdir", "rename", "unlink", "rmdir", "stat"]
)
def test_store_refusal_keeps_lifecycle_from_opening_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    """Input detection omits inputs.py's dir_fd operations; the store gate covers them.

    Without the operation the store refuses configuration, and the lifecycle
    then never authorizes a policy or opens the input store.
    """
    calls: list[str] = []

    def authorize(path: str, check: object) -> input_access.InputsDisabled:
        """Record authorization; return no authority so nothing is opened."""
        calls.append(path)
        return input_access.InputsDisabled()

    def never_open(*args: object) -> None:
        """The input store must not open while the store is refused."""
        raise AssertionError("input store opened")

    monkeypatch.setattr(lifecycle, "authorize_inputs", authorize)
    monkeypatch.setattr(lifecycle.InputStore, "open", never_open)
    working = lifecycle.ArtifactRuntime(configured(tmp_path / "ok"), "policy")
    working._open().close()
    assert calls == ["policy"]
    with monkeypatch.context() as patch:
        patch.setattr(
            disk.os,
            "supports_dir_fd",
            os.supports_dir_fd - {getattr(os, operation)},
        )
        assert input_access._platform_supported()
        store = configure_store(str(tmp_path / "artifacts"))
    assert isinstance(store, ConfigurationError)
    resources = lifecycle.ArtifactRuntime(store, "policy")._open()
    assert isinstance(resources.inputs, ConfigurationError)
    assert resources.grant is None
    assert calls == ["policy"]


def test_ui_modules_import_without_no_follow(tmp_path: Path) -> None:
    """A fresh interpreter lacking O_NOFOLLOW imports the UI and refuses roots."""
    script = """
import os, sys
from pathlib import Path
del os.O_NOFOLLOW
import dartwork_mpl.ui.platform.fs as fs
import dartwork_mpl.ui.state._store
import dartwork_mpl.ui.saving._plan
root = Path(sys.argv[1]) / "viewer"
result = fs.open_roots(root, None, cwd=root.parent)
assert isinstance(result, fs.UnsupportedFilesystem), result
assert not root.exists()
print("ui import available; persistence unsupported")
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "persistence unsupported" in result.stdout
