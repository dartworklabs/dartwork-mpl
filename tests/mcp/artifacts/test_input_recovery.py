"""Common deletion barriers and genuine process restart preserve uncertain sets."""

import importlib
import os
import stat
import subprocess
import sys
from datetime import timedelta

import pytest
from test_input_store import (
    NOW,
    api,
    fixture,
    identity,
    manifest,
    publish,
    selection,
)

from dartwork_mpl.mcp.artifacts import (
    InputMetadata,
    NotFound,
    PublicationError,
    RetainedInput,
)

STATES = ("live", "expired", "revoked", "corrupt", "pending", "unknown")
BARRIERS = (
    "marker_create",
    "marker_write",
    "marker_fsync",
    "set_marked_fsync",
    *(f"payload_unlink:{index:03d}.bin" for index in range(8)),
    "metadata_unlink",
    "set_empty_fsync",
    "marker_unlink",
    "rmdir",
    "root_fsync",
)


def seed(storage, source, store, state):
    """Create all six deletion targets using real committed bytes or owned pending."""
    spec = selection(source)
    specs = (
        spec,
        *(
            type(spec)(
                f"extra{index}", spec.root_id, spec.relative_path, spec.sha256
            )
            for index in range(1, 8)
        ),
    )
    metadata = publish(store, identity(), specs)
    folder = storage / identity().value
    if state == "expired":
        metadata = InputMetadata(
            identity(),
            NOW - timedelta(days=8),
            NOW - timedelta(days=1),
            metadata.files,
        )
        (folder / "inputs.json").write_bytes(metadata.to_bytes())
    elif state == "revoked":
        (folder / ".revoked").write_bytes(b"1")
        (folder / ".revoked").chmod(0o600)
    elif state == "corrupt":
        (folder / "inputs.json").unlink()
    elif state == "pending":
        folder = folder.rename(storage / (".pending-" + identity().value))
    return folder, spec, metadata


@pytest.mark.parametrize("state", STATES)
@pytest.mark.parametrize("barrier", (None, *BARRIERS))
def test_delete_all_six_states_and_barriers(
    owned_input_root, monkeypatch, state, barrier
):
    """No success precedes every durability barrier; retries use safe absence."""
    storage, source, grant, _, _ = fixture(owned_input_root)
    store = api().InputStore.open(grant, NOW)
    try:
        folder, spec, metadata = seed(storage, source, store, state)
        cleanup = importlib.import_module(
            "dartwork_mpl.mcp.artifacts.input_cleanup"
        )
        visited = []
        synced, unlinked = [], []
        real_sync, real_unlink = cleanup.os.fsync, cleanup.os.unlink
        root_inode = storage.stat().st_ino

        def sync(fd):
            """Observe and execute the real adapter syscall, detecting omitted fsyncs."""
            info = os.fstat(fd)
            result = real_sync(fd)
            synced.append(
                "root"
                if info.st_ino == root_inode
                else "set"
                if stat.S_ISDIR(info.st_mode)
                else "file"
            )
            return result

        def unlink(name, **kwargs):
            """Observe actual fixed-name removals, retaining their real effects/errors."""
            result = real_unlink(name, **kwargs)
            unlinked.append(name)
            return result

        def fault(point):
            """Fail this owned adapter barrier once while all other I/O stays real."""
            visited.append(point)
            if point == barrier and (
                point != "root_fsync" or not folder.exists()
            ):
                raise OSError("injected owned filesystem failure")

        with monkeypatch.context() as patch:
            patch.setattr(cleanup, "_fault", fault)
            patch.setattr(cleanup.os, "fsync", sync)
            patch.setattr(cleanup.os, "unlink", unlink)
            result = store.delete(identity())
        if barrier is None:
            assert isinstance(result, api().DeletedInputs), result
            assert visited.index("marker_fsync") < visited.index(
                "payload_unlink:000.bin"
            )
            assert (
                visited.index("set_empty_fsync")
                < visited.index("marker_unlink")
                < visited.index("rmdir")
                < len(visited) - 1
            )
            assert visited[-1] == "root_fsync"
            assert synced == (
                ["root", "file", "set", "set", "root"]
                if state == "pending"
                else ["file", "set", "set", "root", "root"]
            )
            assert unlinked == [
                *(f"{index:03d}.bin" for index in range(8)),
                *([] if state == "corrupt" else ["inputs.json"]),
                ".revoked",
            ]
        else:
            # Missing members still pass their unlink barrier; marker retries
            # pass create even when a marker already exists.
            assert isinstance(result, PublicationError), (
                state,
                barrier,
                result,
            )
            if barrier in BARRIERS[:4]:
                assert (folder / "000.bin").exists()
            if folder.exists() and barrier != "marker_create":
                assert (folder / ".revoked").exists()
            with store.transaction() as tx:
                result = tx.prepare(
                    identity(2),
                    (RetainedInput("x", identity(), "sample", spec.sha256),),
                    NOW,
                    lambda _: manifest(metadata),
                )
                assert isinstance(result, NotFound), result
        retry = store.delete(identity())
        assert isinstance(retry, (api().DeletedInputs, api().AbsentInputs))
        assert isinstance(store.delete(identity()), api().AbsentInputs)
        assert not folder.exists()
    finally:
        store.close()
        grant.close()


@pytest.mark.parametrize(
    "unsafe", ["unknown", "symlink", "hardlink", "directory"]
)
def test_unsafe_residue_is_untouched_denied_and_counted(
    owned_input_root, unsafe
):
    """Unknown or unsafe names survive fixed-namespace deletion with a marker."""
    storage, source, grant, _, _ = fixture(owned_input_root)
    store = api().InputStore.open(grant, NOW)
    try:
        folder, spec, metadata = seed(storage, source, store, "live")
        sentinel = source / "sentinel"
        sentinel.write_bytes(b"preserve")
        if unsafe == "unknown":
            (folder / "foreign").write_bytes(b"preserve")
        elif unsafe == "symlink":
            (folder / "000.bin").unlink()
            (folder / "000.bin").symlink_to(sentinel)
        elif unsafe == "hardlink":
            os.link(folder / "000.bin", sentinel.with_name("alias"))
        else:
            (folder / "nested").mkdir()
            (folder / "nested" / "foreign").write_bytes(b"preserve")
        assert isinstance(store.delete(identity()), PublicationError)
        assert sentinel.read_bytes() == b"preserve"
        assert (folder / ".revoked").read_bytes() == b"1"
        with store.transaction() as tx:
            assert isinstance(
                tx.prepare(
                    identity(2),
                    (RetainedInput("x", identity(), "sample", spec.sha256),),
                    NOW,
                    lambda _: manifest(metadata),
                ),
                NotFound,
            )
        assert folder.exists()
    finally:
        store.close()
        grant.close()


def restart(policy, artifact_path, now, script="", home=None):
    """Run a fresh interpreter with genuine authorization/store/observer surfaces."""
    code = (
        """
import json, sys
from datetime import datetime
from dartwork_mpl.mcp.artifacts import *
from dartwork_mpl.mcp.artifacts.input_access import authorize_inputs, InputGrant
policy, artifact_path, instant = sys.argv[1:]
artifacts = configure_store(None if artifact_path == "__default__" else artifact_path)
grant = authorize_inputs(policy, artifacts.check_input_roots)
assert isinstance(grant, InputGrant), grant
store = InputStore.open(grant, datetime.fromisoformat(instant))
assert isinstance(store, InputStore), store
"""
        + script
        + """
store.close()
grant.close()
print("restart-ok")
"""
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    if home:
        env["HOME"] = str(home)
    return subprocess.run(
        [
            sys.executable,
            "-c",
            code,
            str(policy),
            str(artifact_path),
            now.isoformat(),
        ],
        text=True,
        capture_output=True,
        timeout=20,
        env=env,
    )


def test_restart_preserves_committed_sets_when_artifact_root_changes(
    owned_input_root,
):
    """Real restart/HOME/missing roots cannot prove committed inputs unpublished."""
    storage, source, grant, artifacts, policy = fixture(owned_input_root)
    store = api().InputStore.open(grant, NOW)
    spec = selection(source)
    # Both capabilities publish via their public surfaces; input storage never
    # interprets or creates a foreign commit marker.
    with store.transaction() as tx:
        with artifacts.staging() as artifact_stage:
            parent_id = artifact_stage.artifact_id
            stage = tx.prepare(
                parent_id, (spec,), NOW, artifacts.observe_commit
            )
            assert isinstance(stage, api().InputStage)
            assert tx.check(stage) is None
            metadata = tx.commit(stage, NOW)
            assert isinstance(metadata, InputMetadata)
            artifact_stage.output_stem.with_suffix(".png").write_bytes(b"png")
            artifact_stage.output_stem.with_suffix(".pdf").write_bytes(b"pdf")
            bundle = artifacts.publish(
                artifact_stage,
                b"# source",
                {
                    "status": "ok",
                    "validation_complete": True,
                    "failed_checks": [],
                },
                NOW,
            )
            assert isinstance(bundle, api().StoredBundle), bundle
        assert tx.settle(stage, artifacts.observe_commit(parent_id)) is None
    store.close()
    grant.close()
    folder = storage / parent_id.value
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    original = owned_input_root / "artifacts"
    hidden = original.rename(owned_input_root / "unmounted-artifacts")
    for artifact_path in (
        original,
        owned_input_root / "absent-artifacts",
        "__default__",
    ):
        result = restart(
            policy,
            artifact_path,
            NOW + timedelta(days=1),
            f'''\nwith store.transaction() as tx:
    result = tx.prepare(ArtifactId("{identity(2).value}"),
        (RetainedInput("x", ArtifactId("{parent_id.value}"), "sample", "{spec.sha256}"),),
        datetime.fromisoformat(instant), artifacts.observe_commit)
    assert isinstance(result, PublicationError), result
''',
            home=owned_input_root / "other-home",
        )
        assert result.returncode == 0, result.stdout + result.stderr
        if artifact_path != "__default__":
            assert not artifact_path.exists()
        assert not (
            owned_input_root
            / "other-home"
            / ".cache"
            / "dartwork-mpl"
            / "artifacts"
        ).exists()
        assert before == {p.name: p.read_bytes() for p in folder.iterdir()}
    hidden.rename(original)
    result = restart(
        policy,
        original,
        NOW + timedelta(days=2),
        f'''
with store.transaction() as tx:
    stage = tx.prepare(ArtifactId("{identity(3).value}"),
        (RetainedInput("x", ArtifactId("{parent_id.value}"), "sample", "{spec.sha256}"),),
        datetime.fromisoformat(instant), artifacts.observe_commit)
    assert isinstance(stage, InputStage), stage
    assert tx.check(stage) is None
''',
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert before == {p.name: p.read_bytes() for p in folder.iterdir()}
    # A valid own expiry, unlike a missing artifact root, permits cleanup.
    result = restart(policy, owned_input_root / "missing", metadata.expires_at)
    assert result.returncode == 0, result.stderr
    assert not folder.exists()


@pytest.mark.parametrize("crash", ["pending", "renamed", "response"])
def test_real_crash_recovery(owned_input_root, crash):
    """Process death removes owned pending only; committed unknown sets survive."""
    storage, source, grant, _, policy = fixture(owned_input_root)
    spec = selection(source)
    grant.close()
    script = f'''
import os
from dartwork_mpl.mcp.artifacts import input_cleanup
def crash_at(point):
    """Exit at the real requested barrier before normal transaction cleanup."""
    if point == "{"pending_created" if crash == "pending" else "input_root_fsync" if crash == "renamed" else "never"}":
        os._exit(42)
input_cleanup._fault = crash_at
with store.transaction() as tx:
    stage = tx.prepare(ArtifactId("{identity().value}"),
        (CopyInput("sample", "data", "data.csv", "{spec.sha256}"),),
        datetime.fromisoformat(instant), artifacts.observe_commit)
    assert isinstance(stage, InputStage), stage
'''
    if crash != "pending":
        script += """    assert tx.check(stage) is None
    metadata = tx.commit(stage, datetime.fromisoformat(instant))
    assert isinstance(metadata, InputMetadata), metadata
"""
    if crash == "response":
        script += (
            "    # Input commit succeeded, response/paired outcome is lost.\n"
        )
    script += "    os._exit(42)\n"
    result = restart(policy, owned_input_root / "absent", NOW, script)
    assert result.returncode == 42, result.stdout + result.stderr
    result = restart(
        policy, owned_input_root / "changed", NOW + timedelta(days=1)
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (storage / (".pending-" + identity().value)).exists()
    assert (storage / identity().value).exists() == (crash != "pending")


@pytest.mark.parametrize(
    "point",
    [
        "input_payload_fsync",
        "input_metadata_write",
        "input_metadata_fsync",
        "input_set_fsync",
        "input_rename",
        "input_root_fsync",
    ],
)
def test_commit_fault_settlement_after_stage_exit(
    owned_input_root, monkeypatch, point
):
    """Owned unpublished rollback requires explicit observer result after exit."""
    storage, source, grant, _, _ = fixture(owned_input_root)
    store = api().InputStore.open(grant, NOW)
    cleanup = importlib.import_module(
        "dartwork_mpl.mcp.artifacts.input_cleanup"
    )
    try:
        with store.transaction() as tx:
            stage = tx.prepare(
                identity(), (selection(source),), NOW, lambda _: NotFound()
            )
            assert isinstance(stage, api().InputStage)
            assert tx.check(stage) is None

            def fail(barrier):
                """Fail a commit durability step inside this capability only."""
                if barrier == point:
                    raise OSError("injected")

            with monkeypatch.context() as patch:
                patch.setattr(cleanup, "_fault", fail)
                assert isinstance(tx.commit(stage, NOW), PublicationError)
            assert tx.settle(stage, PublicationError()) == PublicationError()
        if point == "input_root_fsync":
            assert (storage / identity().value).exists()
        assert isinstance(
            store.delete(identity()), (api().DeletedInputs, api().AbsentInputs)
        )
    finally:
        store.close()
        grant.close()


def test_own_unpublished_set_rolls_back_after_actual_artifact_stage_exit(
    owned_input_root,
):
    """Only the caller's post-exit public NotFound observation releases its set."""
    storage, source, grant, artifacts, _ = fixture(owned_input_root)
    store = api().InputStore.open(grant, NOW)
    try:
        with store.transaction() as tx:
            with artifacts.staging() as artifact_stage:
                artifact_id = artifact_stage.artifact_id
                stage = tx.prepare(
                    artifact_id,
                    (selection(source),),
                    NOW,
                    artifacts.observe_commit,
                )
                assert isinstance(stage, api().InputStage)
                assert tx.check(stage) is None
                assert isinstance(tx.commit(stage, NOW), InputMetadata)
                assert (storage / artifact_id.value / "inputs.json").exists()
            observed = artifacts.observe_commit(artifact_id)
            assert isinstance(observed, NotFound)
            assert tx.settle(stage, observed) is None
            assert not (storage / artifact_id.value).exists()
    finally:
        store.close()
        grant.close()


def test_absent_still_requires_root_barrier(owned_input_root, monkeypatch):
    """A root fsync failure cannot turn even a safely missing set into success."""
    _, _, grant, _, _ = fixture(owned_input_root)
    store = api().InputStore.open(grant, NOW)
    cleanup = importlib.import_module(
        "dartwork_mpl.mcp.artifacts.input_cleanup"
    )

    def fail(point):
        """Leave all real names untouched and fail only this durability barrier."""
        if point == "root_fsync":
            raise OSError("injected")

    try:
        with monkeypatch.context() as patch:
            patch.setattr(cleanup, "_fault", fail)
            assert isinstance(store.delete(identity()), PublicationError)
        assert isinstance(store.delete(identity()), api().AbsentInputs)
    finally:
        store.close()
        grant.close()


@pytest.mark.parametrize("damage", ["missing", "corrupt", "unsafe"])
def test_restart_preserves_unknown_committed_residue(owned_input_root, damage):
    """Committed metadata loss/damage cannot be mistaken for an owned orphan."""
    storage, source, grant, _, policy = fixture(owned_input_root)
    store = api().InputStore.open(grant, NOW)
    publish(store, identity(), (selection(source),))
    folder = storage / identity().value
    if damage == "missing":
        (folder / "inputs.json").unlink()
    elif damage == "corrupt":
        (folder / "inputs.json").write_bytes(b"{invalid")
    else:
        (folder / "000.bin").chmod(0o644)
        (folder / "inputs.json").unlink()
    store.close()
    grant.close()
    before = {
        p.name: (p.stat().st_mode, p.read_bytes()) for p in folder.iterdir()
    }
    result = restart(
        policy, owned_input_root / "missing", NOW + timedelta(days=30)
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert before == {
        p.name: (p.stat().st_mode, p.read_bytes()) for p in folder.iterdir()
    }
