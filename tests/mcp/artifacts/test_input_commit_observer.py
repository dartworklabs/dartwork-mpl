"""Real-file commit observations preserve uncertain publication and root identity."""

import errno
import json
import os
import random
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

pytest.importorskip("fastmcp")

from dartwork_mpl.mcp.artifacts import (
    ArtifactId,
    ArtifactStore,
    ConfigurationError,
    CorruptArtifact,
    Manifest,
    NotFound,
    PublicationError,
    StoredBundle,
    configure_store,
)
from dartwork_mpl.mcp.artifacts import store as disk

NOW = datetime(2026, 10, 20, 1, 2, 3, 456789, tzinfo=timezone.utc)
MANIFEST_LIMIT = 512 * 1024
REPORT = {"status": "ok", "validation_complete": True, "failed_checks": []}


def configured(root: Path) -> ArtifactStore:
    """Configure a real private store without creating its absent root."""
    result = configure_store(str(root))
    assert isinstance(result, ArtifactStore), result
    return result


def export_files(stage: Any) -> None:
    """Write owned exporter outputs; observation never decodes image payloads."""
    stage.output_stem.with_suffix(".png").write_bytes(b"opaque PNG payload")
    stage.output_stem.with_suffix(".pdf").write_bytes(b"opaque PDF payload")


def published(store: ArtifactStore, now: datetime = NOW) -> StoredBundle:
    """Produce a committed bundle using the unchanged staging/publish contract."""
    with store.staging() as stage:
        export_files(stage)
        result = store.publish(stage, b"# exact source\n", REPORT, now)
    assert isinstance(result, StoredBundle), result
    return result


def snapshot(root: Path) -> dict[str, tuple[int, int, int, bytes | None]]:
    """Capture names, object identity, mode and bytes without access-time noise."""
    paths = [root, *sorted(root.rglob("*"))]
    return {
        str(path.relative_to(root)): (
            path.stat().st_dev,
            path.stat().st_ino,
            path.stat().st_mode,
            path.read_bytes() if path.is_file() else None,
        )
        for path in paths
    }


def test_stage_identity_is_read_only_and_survives_exit(tmp_path: Path) -> None:
    """The public ID is typed and immutable without exposing stage ownership."""
    store = configured(tmp_path / "artifacts")
    with store.staging() as stage:
        assert getattr(stage, "artifact_id", None) == ArtifactId(
            stage.output_stem.parent.name
        )
        identity = stage.artifact_id
        with pytest.raises(AttributeError):
            stage.artifact_id = ArtifactId(uuid4().hex)
    assert stage.artifact_id == identity


def test_observer_never_creates_or_cleans(tmp_path: Path) -> None:
    """Absent roots stay absent, expired siblings persist, oversize is corruption."""
    absent = tmp_path / "absent" / "artifacts"
    store = configured(absent)
    identity = ArtifactId(uuid4().hex)
    assert isinstance(store.observe_commit(identity), PublicationError)
    assert not absent.parent.exists()

    root = tmp_path / "artifacts"
    store = configured(root)
    old = published(store, NOW - timedelta(days=8))
    target = published(store, NOW - timedelta(days=7))
    # The second publication is still earlier than the first bundle's expiry.
    before = snapshot(root)
    assert store.observe_commit(old.manifest.artifact_id) == old.manifest
    assert store.observe_commit(target.manifest.artifact_id) == target.manifest
    assert isinstance(store.observe_commit(identity), NotFound)
    assert snapshot(root) == before

    manifest_path = root / target.manifest.artifact_id.value / "manifest.json"
    manifest_path.write_bytes(b" " * (MANIFEST_LIMIT + 1))
    before = snapshot(root)
    assert isinstance(
        store.observe_commit(target.manifest.artifact_id), CorruptArtifact
    )
    assert snapshot(root) == before


@pytest.mark.parametrize("failure", ["rename", "set_fsync", "root_fsync"])
@pytest.mark.parametrize("cleanup_fails", [False, True])
def test_observer_sees_post_stage_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    cleanup_fails: bool,
) -> None:
    """After context exit, surviving rename markers remain observable on errors."""
    root = tmp_path / "artifacts"
    store = configured(root)
    real_rename, real_sync = disk.os.rename, disk.os.fsync
    with store.staging() as stage:
        export_files(stage)
        identity = stage.artifact_id
        folder = stage.output_stem.parent
        set_object = folder.stat().st_ino
        root_object = root.stat().st_ino

        def fail_rename(src: str, dst: str, **kwargs: Any) -> None:
            """Fail the store-owned final rename before its namespace effect."""
            if failure == "rename" and dst == "manifest.json":
                raise OSError(errno.EIO, "private path must not escape")
            real_rename(src, dst, **kwargs)

        def fail_sync(fd: int) -> None:
            """Fail one actual directory barrier while preserving file fsyncs."""
            info = os.fstat(fd)
            failed_inode = set_object if failure == "set_fsync" else root_object
            if failure != "rename" and info.st_ino == failed_inode:
                raise OSError(errno.EIO, "private path must not escape")
            real_sync(fd)

        def fail_cleanup(*args: Any, **kwargs: Any) -> None:
            """Leave actual owned bytes behind when cleanup itself is unavailable."""
            raise OSError(errno.EIO, "private cleanup path")

        monkeypatch.setattr(disk.os, "rename", fail_rename)
        monkeypatch.setattr(disk.os, "fsync", fail_sync)
        if cleanup_fails:
            monkeypatch.setattr(disk, "_remove_owned", fail_cleanup)
        result = store.publish(stage, b"# exact source\n", REPORT, NOW)
        assert isinstance(result, PublicationError)
    observed = store.observe_commit(identity)
    if cleanup_fails and failure != "rename":
        assert isinstance(observed, Manifest)
        assert observed.artifact_id == identity
        assert (observed.created_at, observed.expires_at) == (
            NOW,
            NOW + timedelta(days=7),
        )
        assert (folder / "manifest.json").exists()
    else:
        assert isinstance(observed, NotFound)
        assert folder.exists() == cleanup_fails
    assert str(tmp_path) not in repr(observed)


@pytest.mark.parametrize(
    "damage,expected",
    [
        ("missing_manifest", NotFound),
        ("bad_json", CorruptArtifact),
        ("wrong_id", CorruptArtifact),
        ("invalid_times", CorruptArtifact),
        ("manifest_symlink", CorruptArtifact),
        ("manifest_hardlink", CorruptArtifact),
        ("manifest_fifo", CorruptArtifact),
        ("manifest_mode", CorruptArtifact),
        ("directory_symlink", CorruptArtifact),
        ("directory_mode", CorruptArtifact),
        ("read_error", PublicationError),
    ],
)
def test_observer_distinguishes_safe_absence_corruption_and_io_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str, expected: type
) -> None:
    """Unsafe objects never become safe misses or leak diagnostic path strings."""
    root = tmp_path / "artifacts"
    store = configured(root)
    bundle = published(store)
    identity = bundle.manifest.artifact_id
    folder = root / identity.value
    manifest = folder / "manifest.json"
    outside = tmp_path / "outside"
    outside.mkdir(mode=0o700)
    sentinel = outside / "sentinel"
    sentinel.write_bytes(bundle.manifest.to_bytes())
    sentinel.chmod(0o600)
    original = sentinel.read_bytes()
    if damage == "missing_manifest":
        manifest.unlink()
    elif damage == "bad_json":
        manifest.write_bytes(b"not JSON")
    elif damage in {"wrong_id", "invalid_times"}:
        payload = json.loads(manifest.read_bytes())
        if damage == "wrong_id":
            payload["artifact_id"] = uuid4().hex
        else:
            payload["expires_at"] = payload["created_at"]
        manifest.write_text(json.dumps(payload))
    elif damage == "manifest_mode":
        manifest.chmod(0o644)
    elif damage.startswith("manifest_"):
        manifest.unlink()
        if damage == "manifest_symlink":
            manifest.symlink_to(sentinel)
        elif damage == "manifest_hardlink":
            os.link(sentinel, manifest)
        else:
            os.mkfifo(manifest, mode=0o600)
    elif damage == "directory_symlink":
        folder.rename(root / "saved")
        folder.symlink_to(outside, target_is_directory=True)
    elif damage == "directory_mode":
        folder.chmod(0o755)
    else:

        def fail_read(fd: int, count: int) -> bytes:
            """Force an operational read failure on an otherwise owned file."""
            raise OSError(errno.EIO, "private source /secret/path")

        monkeypatch.setattr(disk.os, "read", fail_read)
    result = store.observe_commit(identity)
    assert isinstance(result, expected), result
    assert str(tmp_path) not in repr(result)
    assert sentinel.read_bytes() == original


@pytest.mark.parametrize("replacement", ["missing", "directory", "symlink"])
def test_observer_rejects_replaced_roots_until_original_restored(
    tmp_path: Path, replacement: str
) -> None:
    """A missing/replaced pinned root is unobservable; restoration recovers it."""
    root = tmp_path / "artifacts"
    store = configured(root)
    bundle = published(store)
    saved = tmp_path / "saved-root"
    root.rename(saved)
    if replacement == "directory":
        root.mkdir(mode=0o700)
    elif replacement == "symlink":
        root.symlink_to(saved, target_is_directory=True)
    before = snapshot(saved)
    assert isinstance(
        store.observe_commit(bundle.manifest.artifact_id), PublicationError
    )
    assert snapshot(saved) == before
    if replacement == "directory":
        assert list(root.iterdir()) == []
        root.rmdir()
    elif replacement == "symlink":
        root.unlink()
    else:
        assert not root.exists()
    saved.rename(root)
    assert store.observe_commit(bundle.manifest.artifact_id) == bundle.manifest


def test_observer_is_manifest_only_and_leaves_time_matching_to_caller(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only manifest bytes are read, with valid differing timestamps returned raw."""
    root = tmp_path / "artifacts"
    store = configured(root)
    bundle = published(store)
    folder = root / bundle.manifest.artifact_id.value
    changed = replace(
        bundle.manifest,
        created_at=NOW + timedelta(seconds=1),
        expires_at=NOW + timedelta(days=7, seconds=1),
    )
    (folder / "manifest.json").write_bytes(changed.to_bytes())
    # Missing or hostile payloads are outside commit observation's authority.
    for member in ("plot.png", "plot.pdf", "source.py", "report.json"):
        (folder / member).unlink()
        os.mkfifo(folder / member, mode=0o600)
    total = 0
    real_read = disk.os.read

    def count_read(fd: int, count: int) -> bytes:
        """Count real returned bytes and reject attempts to read other objects."""
        nonlocal total
        assert os.fstat(fd).st_ino == (folder / "manifest.json").stat().st_ino
        data = real_read(fd, count)
        total += len(data)
        return data

    monkeypatch.setattr(disk.os, "read", count_read)
    assert store.observe_commit(bundle.manifest.artifact_id) == changed
    assert total == len(changed.to_bytes()) <= MANIFEST_LIMIT + 1
    assert set(json.loads(changed.to_bytes())) == {
        "schema_version",
        "artifact_id",
        "created_at",
        "expires_at",
        "files",
        "validation",
    }


def test_observer_detects_growth_with_one_overrun_byte(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A manifest growing after fstat never consumes more than 512 KiB plus one."""
    root = tmp_path / "artifacts"
    store = configured(root)
    bundle = published(store)
    manifest = root / bundle.manifest.artifact_id.value / "manifest.json"
    real_read = disk.os.read
    total = 0

    def grow_then_read(fd: int, count: int) -> bytes:
        """Grow a real manifest after preflight and measure its bounded read."""
        nonlocal total
        if total == 0:
            with manifest.open("ab") as file:
                file.write(b" " * (MANIFEST_LIMIT + 10))
        data = real_read(fd, count)
        total += len(data)
        return data

    monkeypatch.setattr(disk.os, "read", grow_then_read)
    assert isinstance(
        store.observe_commit(bundle.manifest.artifact_id), CorruptArtifact
    )
    assert total == MANIFEST_LIMIT + 1


def test_observer_rechecks_root_after_manifest_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Root replacement during a valid manifest read remains an ambiguous commit."""
    root = tmp_path / "artifacts"
    store = configured(root)
    bundle = published(store)
    real_read = disk.os.read
    replaced = False

    def replace_then_read(fd: int, count: int) -> bytes:
        """Replace the actual root while the read still holds its original inode."""
        nonlocal replaced
        if not replaced:
            replaced = True
            root.rename(tmp_path / "saved")
            root.mkdir(mode=0o700)
        return real_read(fd, count)

    monkeypatch.setattr(disk.os, "read", replace_then_read)
    assert isinstance(
        store.observe_commit(bundle.manifest.artifact_id), PublicationError
    )
    assert replaced
    assert list(root.iterdir()) == []


def test_input_roots_reject_overlap_without_creating_directories(
    tmp_path: Path,
) -> None:
    """Storage cannot equal, contain or descend from artifact/copy roots."""
    root = tmp_path / "artifacts"
    root.mkdir(mode=0o700)
    storage = tmp_path / "inputs"
    copy = tmp_path / "copies"
    copy.mkdir(mode=0o700)
    nested_copy = copy / "nested"
    nested_copy.mkdir(mode=0o700)
    store = configured(root)
    for candidate in (root, root / "new", tmp_path):
        assert isinstance(
            store.check_input_roots(candidate, (copy,)), ConfigurationError
        )
    for candidate in (copy, nested_copy, copy / "missing"):
        assert isinstance(
            store.check_input_roots(candidate, (copy,)), ConfigurationError
        )
    assert isinstance(
        store.check_input_roots(storage, (storage / "new",)), ConfigurationError
    )
    storage.mkdir(mode=0o700)
    before = snapshot(tmp_path)
    assert store.check_input_roots(storage, (copy, nested_copy)) is None
    assert snapshot(tmp_path) == before
    assert not (root / "new").exists()
    root.rmdir()
    assert isinstance(
        store.check_input_roots(storage, (copy,)), ConfigurationError
    )


def test_input_roots_check_absent_artifact_path_and_aliases(
    tmp_path: Path,
) -> None:
    """Unresolved roots and symlinks cannot authorize input storage separation."""
    root = tmp_path / "artifacts"
    store = configured(root)
    storage = tmp_path / "inputs"
    copy = tmp_path / "copies"
    copy.mkdir(mode=0o700)
    link = tmp_path / "alias"
    link.symlink_to(copy, target_is_directory=True)
    for candidate, copies in [
        (root, (copy,)),
        (root / "nested", (copy,)),
        (storage, (link,)),
        (link / "nested", (copy,)),
        (Path("relative"), (copy,)),
        (storage, (copy / ".." / "other",)),
    ]:
        assert isinstance(
            store.check_input_roots(candidate, copies), ConfigurationError
        )
    before = snapshot(tmp_path)
    assert isinstance(
        store.check_input_roots(storage, (copy,)), ConfigurationError
    )
    assert snapshot(tmp_path) == before
    assert not root.exists()
    assert not storage.exists()


@pytest.mark.parametrize("missing", ["storage", "copy"])
def test_input_roots_refuse_unresolved_separation_without_writes(
    tmp_path: Path, missing: str
) -> None:
    """Missing storage/copy roots supply no identity proving safe separation."""
    roots = {
        "artifact": tmp_path / "artifacts",
        "storage": tmp_path / "inputs",
        "copy": tmp_path / "copies",
    }
    for name, path in roots.items():
        if name != missing:
            path.mkdir(mode=0o700)
    store = configured(roots["artifact"])
    before = snapshot(tmp_path)
    result = store.check_input_roots(roots["storage"], (roots["copy"],))
    assert snapshot(tmp_path) == before
    assert isinstance(result, ConfigurationError)


def test_input_roots_accept_absent_artifact_sibling_of_existing_input_roots(
    tmp_path: Path,
) -> None:
    """Safe existing input roots preserve lazy creation of a missing artifact root."""
    root = tmp_path / "future" / "artifacts"
    storage = tmp_path / "inputs"
    storage.mkdir(mode=0o700)
    copy = tmp_path / "copies"
    copy.mkdir(mode=0o700)
    store = configured(root)
    before = snapshot(tmp_path)
    assert store.check_input_roots(storage, (copy,)) is None
    assert snapshot(tmp_path) == before
    assert not root.parent.exists()


@pytest.mark.parametrize("alias", [False, True])
def test_input_roots_check_absent_artifact_under_case_variant_storage(
    tmp_path: Path, alias: bool
) -> None:
    """Real storage aliases overlap; distinct case siblings keep artifacts lazy."""
    storage = tmp_path / "inputs"
    storage.mkdir(mode=0o700)
    parent = storage.with_name("INPUTS") if alias else storage
    if not parent.exists():
        parent.mkdir(mode=0o700)
    same_storage = parent.samefile(storage)
    root = parent / "missing" / "artifacts"
    store = configured(root)
    before = snapshot(tmp_path)
    result = store.check_input_roots(storage, ())
    if same_storage:
        assert isinstance(result, ConfigurationError)
    else:
        assert result is None
    assert snapshot(tmp_path) == before
    assert not root.parent.exists()


@pytest.mark.parametrize("other_root", ["artifact", "copy"])
@pytest.mark.parametrize(
    "relation", ["equal", "storage_parent", "storage_child"]
)
def test_input_roots_check_absent_case_variant_overlap(
    tmp_path: Path, other_root: str, relation: str
) -> None:
    """Missing inputs refuse; provisioned case variants follow object ancestry."""
    probe = tmp_path / "CaseProbe"
    probe.mkdir(mode=0o700)
    probe_alias = tmp_path / "CASEPROBE"
    if not probe_alias.exists():
        probe_alias.mkdir(mode=0o700)
    case_aliases = probe.samefile(probe_alias)

    root = tmp_path / ("artifacts" if other_root == "artifact" else "copies")
    storage = root.with_name(root.name.upper())
    if relation == "storage_parent":
        root /= "nested"
    elif relation == "storage_child":
        storage /= "nested"
    if other_root == "artifact":
        store = configured(root)
        copies: tuple[Path, ...] = ()
    else:
        artifact_root = tmp_path / "artifacts"
        artifact_root.mkdir(mode=0o700)
        store = configured(artifact_root)
        copies = (root,)

    before = snapshot(tmp_path)
    result = store.check_input_roots(storage, copies)
    assert snapshot(tmp_path) == before
    assert not root.exists()
    assert not storage.exists()

    # Both filesystems refuse unresolved input roots, without creating anything.
    assert isinstance(result, ConfigurationError)
    # Provision afterwards to distinguish actual aliases from distinct objects.
    storage.mkdir(mode=0o700, parents=True)
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if relation == "equal":
        overlaps = root.samefile(storage)
    elif relation == "storage_parent":
        overlaps = root.parent.samefile(storage)
    else:
        overlaps = storage.parent.samefile(root)
    assert overlaps == case_aliases
    before = snapshot(tmp_path)
    result = store.check_input_roots(storage, copies)
    if overlaps:
        assert isinstance(result, ConfigurationError)
    else:
        assert result is None
    assert snapshot(tmp_path) == before


def test_input_roots_distinguish_objects_with_distinct_case_paths(
    tmp_path: Path,
) -> None:
    """Case aliases are denied; independently opened case siblings are separate."""
    root = tmp_path / "artifacts"
    root.mkdir(mode=0o700)
    alias = root.with_name("ARTIFACTS")
    if not alias.exists():
        alias.mkdir(mode=0o700)
    same_root = root.samefile(alias)
    # Existing distinct directories and their descendants must remain usable.
    if not same_root:
        (alias / "new").mkdir(mode=0o700)
    store = configured(root)
    before = snapshot(tmp_path)
    for candidate in (alias, alias / "new"):
        result = store.check_input_roots(candidate, ())
        if same_root:
            assert isinstance(result, ConfigurationError)
        else:
            assert result is None
    assert snapshot(tmp_path) == before
    storage = tmp_path / "inputs"
    storage.mkdir(mode=0o700)
    copy = storage.with_name("INPUTS")
    if not copy.exists():
        copy.mkdir(mode=0o700)
    before = snapshot(tmp_path)
    result = store.check_input_roots(storage, (copy,))
    if storage.samefile(copy):
        assert isinstance(result, ConfigurationError)
    else:
        assert result is None
    assert snapshot(tmp_path) == before


def test_input_root_overlap_is_symmetric_for_seeded_descendants(
    tmp_path: Path,
) -> None:
    """Generated ancestor/descendant storage pairs are always denied both ways."""
    rng = random.Random(20261020)
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir(mode=0o700)
    store = configured(artifact_root)
    for _ in range(32):
        ancestor = tmp_path / "inputs" / f"root-{rng.randrange(1000)}"
        descendant = ancestor.joinpath(
            *(f"n{rng.randrange(1000)}" for _ in range(rng.randint(1, 4)))
        )
        descendant.mkdir(mode=0o700, parents=True, exist_ok=True)
        before = snapshot(tmp_path)
        assert isinstance(
            store.check_input_roots(ancestor, (descendant,)), ConfigurationError
        )
        assert isinstance(
            store.check_input_roots(descendant, (ancestor,)), ConfigurationError
        )
        assert snapshot(tmp_path) == before


def test_input_roots_reject_artifact_root_replacement_during_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An overlap result cannot authorize a root replaced during observation."""
    root = tmp_path / "artifacts"
    root.mkdir(mode=0o700)
    storage = tmp_path / "inputs"
    storage.mkdir(mode=0o700)
    store = configured(root)
    real_ancestry = disk._root_ancestry

    def replace_after_walk(
        path: Path, *, allow_missing: bool = False
    ) -> dict[tuple[int, int], tuple[str, ...]]:
        """Replace the real root after reading its actual ancestry evidence."""
        result = real_ancestry(path, allow_missing=allow_missing)
        if path == root:
            root.rename(tmp_path / "original-root")
            root.mkdir(mode=0o700)
        return result

    monkeypatch.setattr(disk, "_root_ancestry", replace_after_walk)
    assert isinstance(store.check_input_roots(storage, ()), ConfigurationError)
    assert list(root.iterdir()) == []
    assert list((tmp_path / "original-root").iterdir()) == []


def test_input_root_observation_closes_descriptors_on_initial_fstat_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Even the first ancestry fstat failure closes every newly opened handle."""
    store = configured(tmp_path / "artifacts")
    real_open, real_close, real_stat = (
        disk.os.open,
        disk.os.close,
        disk.os.fstat,
    )
    anchor = Path("/").stat()
    opened: set[int] = set()

    def track_open(
        path: Any, flags: int, mode: int = 0o777, *, dir_fd: int | None = None
    ) -> int:
        """Keep real descriptor ownership observable while exercising error exit."""
        fd = real_open(path, flags, mode, dir_fd=dir_fd)
        opened.add(fd)
        return fd

    def track_close(fd: int) -> None:
        """Observe real close effects rather than claiming a cleanup call suffices."""
        real_close(fd)
        opened.discard(fd)

    def fail_anchor_stat(fd: int) -> os.stat_result:
        """Fail only ancestry's root-object fstat, after a real successful open."""
        info = real_stat(fd)
        if (info.st_dev, info.st_ino) == (anchor.st_dev, anchor.st_ino):
            raise OSError(errno.EIO, "private root error")
        return info

    with monkeypatch.context() as patch:
        patch.setattr(disk.os, "open", track_open)
        patch.setattr(disk.os, "close", track_close)
        patch.setattr(disk.os, "fstat", fail_anchor_stat)
        result = store.check_input_roots(tmp_path / "inputs", ())
    try:
        assert isinstance(result, ConfigurationError)
        assert opened == set()
    finally:
        for fd in opened:
            real_close(fd)
