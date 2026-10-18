"""Real disk contracts for private, atomic and restart-readable artifact bundles."""

import hashlib
import json
import os
import stat
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Event
from typing import Any

import pytest

pytest.importorskip("fastmcp")

from dartwork_mpl.mcp.artifacts import (
    ArtifactBytes,
    ArtifactId,
    ArtifactMember,
    ArtifactStore,
    ArtifactTooLarge,
    ConfigurationError,
    CorruptArtifact,
    Expired,
    NotFound,
    PublicationError,
    StoredBundle,
    configure_store,
    parse_artifact_id,
)
from dartwork_mpl.mcp.artifacts import store as disk

NOW = datetime(2026, 10, 18, 3, 4, 5, 123456, tzinfo=timezone.utc)
SOURCE = '# exact submitted source\nlabel = "한글 café"\n'
REPORT = {
    "status": "ok",
    "validation_complete": True,
    "failed_checks": [],
    "stdout": "원본 로그\n",
    "stderr": "",
    "visual_warnings": ["retained"],
}
LIMIT = 32 * 1024 * 1024


@pytest.fixture(scope="module")
def plots(tmp_path_factory: pytest.TempPathFactory) -> tuple[bytes, bytes]:
    """Render native PNG/PDF fixtures with the project's real export API."""
    import matplotlib.pyplot as plt

    import dartwork_mpl as dm

    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("5cm", "standard"))
    ax.plot([0, 1], [0, 1], linewidth=dm.lw(0))
    dm.simple_layout(fig)
    stem = tmp_path_factory.mktemp("real-plots") / "fixture"
    dm.save_formats(fig, stem, formats=("png", "pdf"), validate=False)
    plt.close(fig)
    return stem.with_suffix(".png").read_bytes(), stem.with_suffix(
        ".pdf"
    ).read_bytes()


def configured(root: Path) -> ArtifactStore:
    """Obtain a real server-bound handle and fail loudly on fixture errors."""
    store = configure_store(str(root))
    assert isinstance(store, ArtifactStore), store
    return store


def export_files(stage: Any, plots: tuple[bytes, bytes]) -> None:
    """Represent trusted export by writing real rendered fixture bytes."""
    stage.output_stem.with_suffix(".png").write_bytes(plots[0])
    stage.output_stem.with_suffix(".pdf").write_bytes(plots[1])


def published(
    store: ArtifactStore,
    plots: tuple[bytes, bytes],
    source: str = SOURCE,
    now: datetime = NOW,
    report: dict[str, Any] | None = None,
) -> StoredBundle:
    """Publish one independently staged bundle through the declared API."""
    with store.staging() as stage:
        export_files(stage, plots)
        result = store.publish(
            stage,
            source.encode("utf-8"),
            REPORT if report is None else report,
            now,
        )
    assert isinstance(result, StoredBundle), result
    return result


def test_bundle_is_complete_private_and_restart_readable(
    tmp_path: Path, plots: tuple[bytes, bytes]
) -> None:
    """Exactly five private contents and their immutable expiry survive restart."""
    root = tmp_path / "new" / "artifacts"
    store = configured(root)
    assert not root.exists()
    result = published(store, plots)
    identity = result.manifest.artifact_id
    folder = root / identity.value
    assert {p.name for p in folder.iterdir()} == {
        member.value for member in ArtifactMember
    }
    for path in [root.parent, root, folder]:
        assert stat.S_IMODE(path.stat().st_mode) == 0o700
    for member, data in result.contents.items():
        path = folder / member.value
        assert path.read_bytes() == data
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert result.contents[ArtifactMember.PNG] == plots[0]
    assert result.contents[ArtifactMember.PDF] == plots[1]
    assert result.contents[ArtifactMember.SOURCE] == SOURCE.encode("utf-8")
    assert json.loads(result.contents[ArtifactMember.REPORT]) == REPORT
    assert result.manifest.expires_at == NOW + timedelta(days=7)
    for entry in result.manifest.files:
        data = result.contents[entry.member]
        assert (entry.size_bytes, entry.sha256) == (
            len(data),
            hashlib.sha256(data).hexdigest(),
        )
    restarted = configured(root)
    assert restarted.load(identity, NOW + timedelta(days=1)) == result
    for member in ArtifactMember:
        assert restarted.read_member(identity, member, NOW) == ArtifactBytes(
            result.contents[member], member.mime_type
        )
    with pytest.raises(TypeError):
        result.contents[ArtifactMember.SOURCE] = b"changed"


def test_repeats_and_threads_cannot_overwrite(
    tmp_path: Path, plots: tuple[bytes, bytes]
) -> None:
    """Concurrent real publications reserve different IDs and retain all payloads."""
    store = configured(tmp_path / "artifacts")

    def publish_index(index: int) -> StoredBundle:
        """Give each concurrent publication an independently observable payload."""
        return published(store, plots, f"# source {index}\n")

    with ThreadPoolExecutor(max_workers=6) as pool:
        bundles = list(pool.map(publish_index, range(18)))
    assert len({bundle.manifest.artifact_id for bundle in bundles}) == 18
    for index, bundle in enumerate(bundles):
        readback = store.load(bundle.manifest.artifact_id, NOW)
        assert isinstance(readback, StoredBundle)
        assert (
            readback.contents[ArtifactMember.SOURCE]
            == f"# source {index}\n".encode()
        )


def test_invalid_root_does_not_create_or_leak_paths(tmp_path: Path) -> None:
    """Refused configuration neither creates a root nor exposes raw paths."""
    file = tmp_path / "private-file"
    file.write_text("sentinel")
    folder = tmp_path / "private-folder"
    folder.mkdir(mode=0o700)
    link = tmp_path / "linked"
    link.symlink_to(folder, target_is_directory=True)
    unsafe = tmp_path / "public"
    unsafe.mkdir(mode=0o755)
    for root in [
        "",
        "relative",
        str(file),
        str(link),
        str(link / "nested"),
        str(unsafe),
    ]:
        result = configure_store(root)
        assert isinstance(result, ConfigurationError), root
        assert str(tmp_path) not in repr(result)
        assert root not in repr(result) if root else True
    assert file.read_text() == "sentinel"
    assert not (folder / "nested").exists()


def test_partial_publication_never_becomes_readable(
    tmp_path: Path, plots: tuple[bytes, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Uncommitted export and injected disk failure publish no readable marker."""
    root = tmp_path / "artifacts"
    store = configured(root)
    unknown = tmp_path / "unknown"
    unknown.mkdir()
    (unknown / "keep").write_text("sentinel")
    with store.staging() as stage:
        export_files(stage, plots)
        folder = stage.output_stem.parent
        identity = parse_artifact_id(folder.name)
        assert isinstance(identity, ArtifactId)
        assert isinstance(store.load(identity, NOW), NotFound)
        original = disk._write_file

        def fail_report(fd: int, name: str, data: bytes) -> None:
            """Inject a real mid-publication failure after source has been written."""
            if name == "report.json":
                assert not (folder / "manifest.json").exists()
                raise OSError("unsafe /outside/path must not escape")
            original(fd, name, data)

        monkeypatch.setattr(disk, "_write_file", fail_report)
        result = store.publish(stage, SOURCE.encode(), REPORT, NOW)
        assert isinstance(result, PublicationError)
        assert "/outside" not in repr(result)
        assert not (folder / "manifest.json").exists()
        assert isinstance(store.load(identity, NOW), NotFound)
    assert not folder.exists()
    assert (unknown / "keep").read_text() == "sentinel"


def test_process_killed_staging_is_unavailable_and_not_swept(
    tmp_path: Path,
) -> None:
    """A killed writer leaves unavailable staging that another operation preserves."""
    root = tmp_path / "artifacts"
    script = """
import sys
from dartwork_mpl.mcp.artifacts import configure_store
store = configure_store(sys.argv[1])
with store.staging() as stage:
    stage.output_stem.with_suffix('.png').write_bytes(b'partial')
    print(stage.output_stem.parent.name, flush=True)
    sys.stdin.read()
"""
    process = subprocess.Popen(
        [sys.executable, "-c", script, str(root)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert process.stdout is not None
        raw = process.stdout.readline().strip()
        identity = parse_artifact_id(raw)
        assert isinstance(identity, ArtifactId), raw
        process.kill()
        process.communicate(timeout=10)
        store = configured(root)
        assert isinstance(
            store.load(identity, NOW + timedelta(days=8)), NotFound
        )
        with store.staging():
            pass
        assert (root / raw / "plot.png").read_bytes() == b"partial"
        assert not (root / raw / "manifest.json").exists()
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=10)


def test_commit_marker_follows_last_data_write(
    tmp_path: Path, plots: tuple[bytes, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The final source/report write cannot observe a ready manifest."""
    store = configured(tmp_path / "artifacts")
    original = disk._write_file
    with store.staging() as stage:
        export_files(stage, plots)

        def observe_write(fd: int, name: str, data: bytes) -> None:
            """Observe persisted visibility at the last data write boundary."""
            if name == "report.json":
                assert not (stage.output_stem.parent / "manifest.json").exists()
            original(fd, name, data)

        monkeypatch.setattr(disk, "_write_file", observe_write)
        assert isinstance(
            store.publish(stage, SOURCE.encode(), REPORT, NOW), StoredBundle
        )


def test_expiry_race_preserves_unknown_directories(
    tmp_path: Path, plots: tuple[bytes, bytes]
) -> None:
    """Expiry denies exactly at the boundary; cleanup preserves unknown/corrupt data."""
    root = tmp_path / "artifacts"
    store = configured(root)
    bundle = published(store, plots)
    expiry = bundle.manifest.expires_at
    identity = bundle.manifest.artifact_id
    unknown = root / "not-an-artifact"
    unknown.mkdir()
    (unknown / "keep").write_text("unknown")
    corrupt_id = ArtifactId("00000000000040008000000000000001")
    corrupt = root / corrupt_id.value
    corrupt.mkdir(mode=0o700)
    (corrupt / "manifest.json").write_text("not JSON")
    assert store.load(identity, expiry - timedelta(microseconds=1)) == bundle
    assert store.load(identity, expiry) == Expired(expiry)
    assert not (root / identity.value).exists()
    assert isinstance(
        store.read_member(identity, ArtifactMember.PNG, expiry), NotFound
    )
    # A publication can finish after an earlier bundle expires; cleanup cannot
    # mistake the already reserved unpublished directory for an expired bundle.
    ready = Event()
    continue_write = Event()

    def delayed_publication() -> StoredBundle:
        """Hold a real reserved directory across another publication's cleanup."""
        with store.staging() as stage:
            export_files(stage, plots)
            ready.set()
            assert continue_write.wait(timeout=10)
            result = store.publish(stage, SOURCE.encode(), REPORT, expiry)
            assert isinstance(result, StoredBundle)
            return result

    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(delayed_publication)
        assert ready.wait(timeout=10)
        later = published(store, plots, now=expiry)
        continue_write.set()
        delayed = pending.result(timeout=10)
    assert store.load(later.manifest.artifact_id, expiry) == later
    assert store.load(delayed.manifest.artifact_id, expiry) == delayed
    assert (unknown / "keep").read_text() == "unknown"
    assert (corrupt / "manifest.json").read_text() == "not JSON"


@pytest.mark.parametrize(
    "damage",
    [
        "member_symlink",
        "directory_symlink",
        "fifo",
        "missing_manifest",
        "bad_manifest",
        "truncation",
        "same_size_tamper",
        "extra_file",
        "oversize_member",
        "manifest_symlink",
        "hardlink",
    ],
)
def test_opened_files_are_confined_and_verified(
    tmp_path: Path, plots: tuple[bytes, bytes], damage: str
) -> None:
    """No symlink, special file, oversized body or unverified bytes are returned."""
    root = tmp_path / "artifacts"
    store = configured(root)
    bundle = published(store, plots)
    identity = bundle.manifest.artifact_id
    folder = root / identity.value
    sentinel = tmp_path / "outside-sentinel"
    sentinel.write_bytes(b"outside secret")
    outside = tmp_path / "outside-directory"
    outside.mkdir(mode=0o700)
    (outside / "manifest.json").write_bytes(
        bundle.contents[ArtifactMember.MANIFEST]
    )
    png = folder / "plot.png"
    if damage == "member_symlink":
        png.unlink()
        png.symlink_to(sentinel)
    elif damage == "directory_symlink":
        folder.rename(root / "moved")
        folder.symlink_to(outside, target_is_directory=True)
    elif damage == "fifo":
        png.unlink()
        os.mkfifo(png, mode=0o600)
    elif damage == "missing_manifest":
        (folder / "manifest.json").unlink()
    elif damage == "bad_manifest":
        (folder / "manifest.json").write_bytes(b'{"schema_version": 2}')
    elif damage == "truncation":
        png.write_bytes(b"short")
    elif damage == "same_size_tamper":
        png.write_bytes(b"x" * len(plots[0]))
    elif damage == "extra_file":
        (folder / "unknown").write_text("keep")
    elif damage == "oversize_member":
        with png.open("wb") as file:
            file.truncate(LIMIT + 1)
    elif damage == "manifest_symlink":
        (folder / "manifest.json").unlink()
        (folder / "manifest.json").symlink_to(sentinel)
    elif damage == "hardlink":
        png.unlink()
        os.link(sentinel, png)
    result = store.read_member(identity, ArtifactMember.PNG, NOW)
    expected = (
        NotFound
        if damage == "missing_manifest"
        else ArtifactTooLarge
        if damage == "oversize_member"
        else CorruptArtifact
    )
    assert isinstance(result, expected), (damage, result)
    assert str(tmp_path) not in repr(result)
    assert sentinel.read_bytes() == b"outside secret"
    store.load(identity, NOW + timedelta(days=8))
    assert sentinel.read_bytes() == b"outside secret"
    assert (outside / "manifest.json").read_bytes() == bundle.contents[
        ArtifactMember.MANIFEST
    ]
    if damage == "extra_file":
        assert (folder / "unknown").read_text() == "keep"


def test_root_and_member_swaps_are_checked_at_open(
    tmp_path: Path, plots: tuple[bytes, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A deterministic path replacement at open cannot follow an outside object."""
    root = tmp_path / "artifacts"
    store = configured(root)
    bundle = published(store, plots)
    identity = bundle.manifest.artifact_id
    png = root / identity.value / "plot.png"
    sentinel = tmp_path / "sentinel"
    sentinel.write_bytes(b"secret")
    real_open = disk.os.open
    swapped = False

    def swap_before_open(
        path: Any, flags: int, mode: int = 0o777, *, dir_fd: int | None = None
    ) -> int:
        """Swap the literal member just before the real descriptor-relative open."""
        nonlocal swapped
        if path == "plot.png" and dir_fd is not None and not swapped:
            swapped = True
            png.unlink()
            png.symlink_to(sentinel)
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(disk.os, "open", swap_before_open)
    assert isinstance(
        store.read_member(identity, ArtifactMember.PNG, NOW), CorruptArtifact
    )
    assert swapped
    monkeypatch.setattr(disk.os, "open", real_open)
    root.rename(tmp_path / "previous-root")
    root.symlink_to(tmp_path, target_is_directory=True)
    assert isinstance(store.load(identity, NOW), CorruptArtifact)
    assert sentinel.read_bytes() == b"secret"


def test_oversize_report_and_combined_bytes_are_refused(
    tmp_path: Path, plots: tuple[bytes, bytes]
) -> None:
    """Source, complete report and combined sizes are bounded without clipping."""
    root = tmp_path / "artifacts"
    store = configured(root)
    for kind in ["report", "combined", "source", "nonfinite_report"]:
        with store.staging() as stage:
            export_files(stage, plots)
            report = dict(REPORT)
            source = SOURCE.encode()
            if kind == "report":
                report["stdout"] = "x" * LIMIT
            elif kind == "combined":
                with stage.output_stem.with_suffix(".png").open("wb") as file:
                    file.truncate(LIMIT)
            elif kind == "source":
                source = b"x" * (512 * 1024 + 1)
            else:
                report["score"] = float("nan")
            result = store.publish(stage, source, report, NOW)
            assert isinstance(
                result,
                PublicationError
                if kind == "nonfinite_report"
                else ArtifactTooLarge,
            )
            assert not (stage.output_stem.parent / "manifest.json").exists()
        assert not stage.output_stem.parent.exists()


def test_stage_lifecycle_is_owned_and_single_use(
    tmp_path: Path, plots: tuple[bytes, bytes]
) -> None:
    """Only the creating store can publish a live stage, exactly once."""
    store = configured(tmp_path / "artifacts")
    other = configured(tmp_path / "other")
    with store.staging() as stage:
        export_files(stage, plots)
        assert isinstance(
            other.publish(stage, SOURCE.encode(), REPORT, NOW), PublicationError
        )
        result = store.publish(stage, SOURCE.encode(), REPORT, NOW)
        assert isinstance(result, StoredBundle)
        assert isinstance(
            store.publish(stage, b"changed", REPORT, NOW), PublicationError
        )
    assert isinstance(
        store.publish(stage, SOURCE.encode(), REPORT, NOW), PublicationError
    )
    assert store.load(result.manifest.artifact_id, NOW) == result
    with store.staging() as unknown_stage:
        unknown = unknown_stage.output_stem.parent / "unknown"
        unknown.write_bytes(b"keep")
    assert unknown.read_bytes() == b"keep"


def test_committed_success_survives_ancillary_cleanup_failure(
    tmp_path: Path, plots: tuple[bytes, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A committed bundle remains a success if unrelated expiry cleanup fails."""
    store = configured(tmp_path / "artifacts")

    def failed_cleanup(*args: Any, **kwargs: Any) -> None:
        """Inject an infrastructure failure at the store-owned cleanup boundary."""
        raise OSError("sensitive /root/path")

    with monkeypatch.context() as patch:
        patch.setattr(disk, "_cleanup_expired", failed_cleanup)
        result = published(store, plots)
    assert store.load(result.manifest.artifact_id, NOW) == result


def test_uuid_collision_cannot_overwrite_existing_bundle(
    tmp_path: Path, plots: tuple[bytes, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exclusive reservation retries an actual collision and retains old bytes."""
    from uuid import UUID, uuid4

    store = configured(tmp_path / "artifacts")
    original = published(store, plots)
    fresh = uuid4()
    candidates = iter([UUID(original.manifest.artifact_id.value), fresh])
    monkeypatch.setattr(disk, "uuid4", lambda: next(candidates))
    next_bundle = published(store, plots, "# second source\n")
    assert next_bundle.manifest.artifact_id == ArtifactId(fresh.hex)
    assert store.load(original.manifest.artifact_id, NOW) == original
    assert store.load(next_bundle.manifest.artifact_id, NOW) == next_bundle


def test_manifest_commit_sync_failure_rolls_back_before_return(
    tmp_path: Path, plots: tuple[bytes, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A directory sync failure after rename leaves no ready marker on refusal."""
    store = configured(tmp_path / "artifacts")
    real_sync = disk.os.fsync

    def fail_directory_sync(fd: int) -> None:
        """Fail only the real final directory sync, after data file syncs finish."""
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError("private /storage/path")
        real_sync(fd)

    with store.staging() as stage:
        export_files(stage, plots)
        identity = parse_artifact_id(stage.output_stem.parent.name)
        assert isinstance(identity, ArtifactId)
        monkeypatch.setattr(disk.os, "fsync", fail_directory_sync)
        assert isinstance(
            store.publish(stage, SOURCE.encode(), REPORT, NOW), PublicationError
        )
        assert not (stage.output_stem.parent / "manifest.json").exists()
        assert isinstance(store.load(identity, NOW), NotFound)


@pytest.mark.parametrize("trigger", ["access", "publication"])
def test_lazy_cleanup_requires_fully_validated_expired_bundles(
    tmp_path: Path, plots: tuple[bytes, bytes], trigger: str
) -> None:
    """Both lazy cleanup paths remove expired owned data and preserve corruption."""
    root = tmp_path / "artifacts"
    store = configured(root)
    expired = published(store, plots)
    corrupt = published(store, plots)
    corrupt_folder = root / corrupt.manifest.artifact_id.value
    (corrupt_folder / "plot.png").write_bytes(b"tampered")
    live = published(store, plots, now=NOW + timedelta(days=6))
    later = NOW + timedelta(days=7)
    if trigger == "access":
        assert store.load(live.manifest.artifact_id, later) == live
    else:
        assert isinstance(published(store, plots, now=later), StoredBundle)
    assert not (root / expired.manifest.artifact_id.value).exists()
    assert (corrupt_folder / "plot.png").read_bytes() == b"tampered"
    assert isinstance(
        store.load(corrupt.manifest.artifact_id, later), CorruptArtifact
    )


@pytest.mark.parametrize("operation", ["load", "read_member", "publish"])
def test_unexpired_cleanup_reads_only_unrelated_manifests(
    tmp_path: Path,
    plots: tuple[bytes, bytes],
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    """Retained payloads add no read cost to another bundle's access/publication."""
    root = tmp_path / "artifacts"
    store = configured(root)
    large_plots = (plots[0].ljust(1024 * 1024, b"\0"), plots[1])
    bundles = [published(store, large_plots, "# live!\n") for _ in range(12)]
    selected = bundles[0]
    selected_id = selected.manifest.artifact_id
    identities = {}
    for bundle in bundles:
        for member in ArtifactMember:
            info = (
                root / bundle.manifest.artifact_id.value / member.value
            ).stat()
            identities[(info.st_dev, info.st_ino)] = (
                bundle.manifest.artifact_id,
                member,
            )
    reads: list[tuple[ArtifactId, ArtifactMember, int]] = []
    real_read = disk.os.read

    def observe_read(fd: int, count: int) -> bytes:
        """Measure actual OS bytes without replacing any managed file contents."""
        info = os.fstat(fd)
        data = real_read(fd, count)
        identity = identities.get((info.st_dev, info.st_ino))
        if identity is not None and data:
            reads.append((*identity, len(data)))
        return data

    with monkeypatch.context() as patch:
        patch.setattr(disk.os, "read", observe_read)
        if operation == "load":
            assert store.load(selected_id, NOW) == selected
        elif operation == "read_member":
            assert store.read_member(
                selected_id, ArtifactMember.SOURCE, NOW
            ) == ArtifactBytes(b"# live!\n", ArtifactMember.SOURCE.mime_type)
        else:
            created = published(store, plots)
            assert created.contents[ArtifactMember.PNG] == plots[0]
            assert created.contents[ArtifactMember.SOURCE] == SOURCE.encode()
    unrelated = [
        (identity, member, size)
        for identity, member, size in reads
        if operation == "publish" or identity != selected_id
    ]
    print(
        f"{operation}: retained-store reads={len(reads)}, "
        f"bytes={sum(size for _, _, size in reads)}, "
        f"unrelated payload bytes="
        f"{sum(size for _, member, size in unrelated if member != ArtifactMember.MANIFEST)}"
    )
    assert all(member == ArtifactMember.MANIFEST for _, member, _ in unrelated)
    if operation != "publish":
        assert {
            member for identity, member, _ in reads if identity == selected_id
        } == set(ArtifactMember)
    assert all(
        (root / bundle.manifest.artifact_id.value).is_dir()
        for bundle in bundles
    )


def test_cleanup_rechecks_expiry_after_manifest_preflight(
    tmp_path: Path, plots: tuple[bytes, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A now-live manifest substituted after preflight cannot authorize deletion."""
    root = tmp_path / "artifacts"
    store = configured(root)
    expired = published(store, plots)
    live = published(store, plots, now=NOW + timedelta(days=1))
    folder = root / expired.manifest.artifact_id.value
    info = folder.stat()
    renewed = replace(
        expired.manifest,
        created_at=expired.manifest.created_at + timedelta(days=1),
        expires_at=expired.manifest.expires_at + timedelta(days=1),
    )
    real_open = disk.os.open
    manifest_opens = 0

    def replace_before_verification(
        path: Any, flags: int, mode: int = 0o777, *, dir_fd: int | None = None
    ) -> int:
        """Replace real metadata between its preflight and complete bundle reads."""
        nonlocal manifest_opens
        if path == "manifest.json" and dir_fd is not None:
            opened = os.fstat(dir_fd)
            if (opened.st_dev, opened.st_ino) == (info.st_dev, info.st_ino):
                manifest_opens += 1
                if manifest_opens == 2:
                    (folder / "manifest.json").write_bytes(renewed.to_bytes())
        return real_open(path, flags, mode, dir_fd=dir_fd)

    with monkeypatch.context() as patch:
        patch.setattr(disk.os, "open", replace_before_verification)
        assert (
            store.load(live.manifest.artifact_id, NOW + timedelta(days=7))
            == live
        )
    assert manifest_opens >= 2
    assert folder.is_dir()
    assert (folder / "manifest.json").read_bytes() == renewed.to_bytes()
    assert (folder / "plot.png").read_bytes() == plots[0]
    readback = store.load(expired.manifest.artifact_id, NOW + timedelta(days=7))
    assert isinstance(readback, StoredBundle)
    assert readback.manifest == renewed


@pytest.mark.parametrize(
    "damage",
    [
        "malformed",
        "id_mismatch",
        "oversize",
        "symlink",
        "hardlink",
        "permissions",
    ],
)
def test_cleanup_preserves_invalid_manifest_preflight(
    tmp_path: Path, plots: tuple[bytes, bytes], damage: str
) -> None:
    """Unsafe or invalid expired metadata never authorizes incidental removal."""
    root = tmp_path / "artifacts"
    store = configured(root)
    candidate = published(store, plots)
    live = published(store, plots, now=NOW + timedelta(days=1))
    folder = root / candidate.manifest.artifact_id.value
    manifest = folder / "manifest.json"
    outside = tmp_path / "outside-manifest"
    outside.write_bytes(candidate.manifest.to_bytes())
    outside.chmod(0o600)
    if damage == "malformed":
        manifest.write_bytes(b"not JSON")
    elif damage == "id_mismatch":
        manifest.write_bytes(
            replace(
                candidate.manifest, artifact_id=live.manifest.artifact_id
            ).to_bytes()
        )
    elif damage == "oversize":
        with manifest.open("wb") as file:
            file.truncate(disk.MAX_MANIFEST_BYTES + 1)
    elif damage == "symlink":
        manifest.unlink()
        manifest.symlink_to(outside)
    elif damage == "hardlink":
        manifest.unlink()
        os.link(outside, manifest)
    else:
        manifest.chmod(0o644)
    before = manifest.read_bytes()
    assert (
        store.load(live.manifest.artifact_id, NOW + timedelta(days=7)) == live
    )
    assert manifest.read_bytes() == before
    assert (folder / "plot.png").read_bytes() == plots[0]
    assert outside.read_bytes() == candidate.manifest.to_bytes()


def test_default_root_is_selected_once_and_initialized_lazily(
    tmp_path: Path, plots: tuple[bytes, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The default uses configuration-time home and never follows later changes."""
    first_home = tmp_path / "first-home"
    first_home.mkdir(mode=0o700)
    monkeypatch.setenv("HOME", str(first_home))
    store = configure_store(None)
    assert isinstance(store, ArtifactStore)
    root = first_home / ".cache" / "dartwork-mpl" / "artifacts"
    assert not root.exists()
    monkeypatch.setenv("HOME", str(tmp_path / "other-home"))
    bundle = published(store, plots)
    assert (
        root / bundle.manifest.artifact_id.value / "manifest.json"
    ).is_file()
    assert not (tmp_path / "other-home").exists()


def test_directory_swap_at_open_cannot_follow_outside_target(
    tmp_path: Path, plots: tuple[bytes, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bundle directory replaced exactly at open is rejected without traversal."""
    root = tmp_path / "artifacts"
    store = configured(root)
    bundle = published(store, plots)
    identity = bundle.manifest.artifact_id
    folder = root / identity.value
    outside = tmp_path / "outside"
    outside.mkdir(mode=0o700)
    sentinel = outside / "sentinel"
    sentinel.write_bytes(b"secret")
    real_open = disk.os.open
    swapped = False

    def swap_before_open(
        path: Any, flags: int, mode: int = 0o777, *, dir_fd: int | None = None
    ) -> int:
        """Replace the bundle name at the actual no-follow open effect."""
        nonlocal swapped
        if path == identity.value and dir_fd is not None and not swapped:
            swapped = True
            folder.rename(root / "previous-bundle")
            folder.symlink_to(outside, target_is_directory=True)
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(disk.os, "open", swap_before_open)
    assert isinstance(store.load(identity, NOW), CorruptArtifact)
    assert swapped
    assert sentinel.read_bytes() == b"secret"
    assert {item.name for item in outside.iterdir()} == {"sentinel"}


@pytest.mark.parametrize("missing", ["O_NOFOLLOW", "link"])
def test_missing_descriptor_support_refuses_only_new_capability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    """Unsupported hosts refuse configuration without creating an unsafe store."""
    root = tmp_path / "artifacts"
    monkeypatch.delattr(disk.os, missing)
    assert isinstance(configure_store(str(root)), ConfigurationError)
    assert not root.exists()


@pytest.mark.parametrize(
    "boundary",
    [
        "after_validation",
        "after_validation_same_bytes",
        "before_isolation",
        "same_bytes",
        "before_unlink",
    ],
)
def test_expired_cleanup_preserves_replaced_members(
    tmp_path: Path,
    plots: tuple[bytes, bytes],
    monkeypatch: pytest.MonkeyPatch,
    boundary: str,
) -> None:
    """External same-user replacement survives validation and deletion boundaries."""
    root = tmp_path / "artifacts"
    store = configured(root)
    bundle = published(store, plots)
    folder = root / bundle.manifest.artifact_id.value
    png = folder / "plot.png"
    replacement = (
        plots[0]
        if boundary in {"same_bytes", "after_validation_same_bytes"}
        else b"unvalidated replacement"
    )
    changed = False

    def replace_png() -> None:
        """Retain the old inode and install an independently identifiable object."""
        nonlocal changed
        folder.mkdir(mode=0o700, exist_ok=True)
        if png.exists():
            png.rename(tmp_path / "previous-png")
        png.write_bytes(replacement)
        png.chmod(0o600)
        changed = True

    if boundary in {"after_validation", "after_validation_same_bytes"}:
        original_remove = disk._remove_owned

        def replace_before_cleanup(
            root_fd: int, name: str, directory_fd: int, *, ready: bool
        ) -> None:
            """Change a member immediately after the complete outer validation."""
            if ready and not changed:
                replace_png()
            original_remove(root_fd, name, directory_fd, ready=ready)

        monkeypatch.setattr(disk, "_remove_owned", replace_before_cleanup)
    elif boundary in {"before_isolation", "same_bytes"}:
        original_rename = disk.os.rename

        def replace_at_isolation(
            source: Any,
            target: Any,
            *,
            src_dir_fd: int | None = None,
            dst_dir_fd: int | None = None,
        ) -> None:
            """Swap the candidate at its atomic rename instead of a sleep race."""
            if source == "plot.png" and not changed:
                replace_png()
            original_rename(
                source, target, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd
            )

        monkeypatch.setattr(disk.os, "rename", replace_at_isolation)
    else:
        original_unlink = disk.os.unlink

        def replace_at_unlink(path: Any, *, dir_fd: int | None = None) -> None:
            """Install a replacement at the former stat-to-unlink boundary."""
            if path == "plot.png" and not changed:
                replace_png()
            original_unlink(path, dir_fd=dir_fd)

        monkeypatch.setattr(disk.os, "unlink", replace_at_unlink)
    outcome = store.load(bundle.manifest.artifact_id, NOW + timedelta(days=7))
    assert outcome == Expired(bundle.manifest.expires_at)
    assert changed, boundary
    assert png.exists(), boundary
    assert png.read_bytes() == replacement, boundary


def test_optional_fastmcp_absence_skips_both_artifact_modules() -> None:
    """A core-only installation collects optional artifact tests as two skips."""
    script = """
import importlib.abc
import sys
import pytest

class BlockFastMCP(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "fastmcp" or fullname.startswith("fastmcp."):
            raise ModuleNotFoundError("No module named 'fastmcp'", name="fastmcp")

sys.meta_path.insert(0, BlockFastMCP())
code = pytest.main([
    "--collect-only", "--no-cov", "-q",
    "tests/mcp/artifacts/test_artifact_policy.py",
    "tests/mcp/artifacts/test_artifact_store.py",
])
assert code == pytest.ExitCode.NO_TESTS_COLLECTED, code
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "2 skipped" in result.stdout, result.stdout
    assert "ERROR collecting" not in result.stdout


def test_cleanup_restore_collision_keeps_both_replacements(
    tmp_path: Path, plots: tuple[bytes, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A colliding restoration keeps the isolated and newly installed objects."""
    root = tmp_path / "artifacts"
    store = configured(root)
    bundle = published(store, plots)
    folder = root / bundle.manifest.artifact_id.value
    png = folder / "plot.png"
    rename = disk.os.rename
    changed = False

    def substitute_and_collide(
        source: Any,
        target: Any,
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        """Atomically isolate one substituted object and install another at home."""
        nonlocal changed
        if source == "plot.png" and not changed:
            changed = True
            png.rename(tmp_path / "original-png")
            png.write_bytes(b"first replacement")
            png.chmod(0o600)
            rename(source, target, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)
            png.write_bytes(b"second replacement")
            png.chmod(0o600)
            return
        rename(source, target, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    with monkeypatch.context() as patch:
        patch.setattr(disk.os, "rename", substitute_and_collide)
        assert store.load(
            bundle.manifest.artifact_id, NOW + timedelta(days=7)
        ) == Expired(bundle.manifest.expires_at)
    assert changed
    assert png.read_bytes() == b"second replacement"
    quarantines = [
        path for path in root.iterdir() if path.name.startswith(".cleanup-")
    ]
    assert len(quarantines) == 1
    preserved = quarantines[0] / "plot.png"
    assert preserved.read_bytes() == b"first replacement"
    assert stat.S_IMODE(quarantines[0].stat().st_mode) == 0o700
    assert stat.S_IMODE(preserved.stat().st_mode) == 0o600
    published(store, plots, now=NOW + timedelta(days=8))
    assert preserved.read_bytes() == b"first replacement"
    assert png.read_bytes() == b"second replacement"
