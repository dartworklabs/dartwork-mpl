"""Real granted files exercise bounded independent input-set transactions."""

import asyncio
import importlib
import json
import os
import random
import select
import subprocess
import sys
import threading
from datetime import timedelta
from pathlib import Path

import pytest

from dartwork_mpl.mcp.artifacts.input_policy import (
    InputMetadata,
    RetainedInput,
    can_reserve,
)
from dartwork_mpl.mcp.artifacts.policy import (
    ConfigurationError,
    CorruptArtifact,
    Expired,
    InvalidRequest,
    NotFound,
    PublicationError,
)
from tests.mcp.artifacts.input_fixtures import (
    NOW,
    api,
    fixture,
    identity,
    manifest,
    publish,
    selection,
)

MIB = 1024 * 1024
RESERVATION = 32 * MIB + 16 * 1024 + 1


def test_budget_and_independent_expiry(owned_input_root):
    """Children own bytes/new clocks, reads do not renew, admitted work pins expiry."""
    storage, source, grant, _, _ = fixture(owned_input_root)
    store = api().InputStore.open(grant, NOW)
    assert isinstance(store, api().InputStore)
    try:
        spec = selection(source)
        parent = publish(store, identity(), (spec,))
        retained = RetainedInput("child", identity(), "sample", spec.sha256)
        with store.transaction() as tx:
            stage = tx.prepare(
                identity(2),
                (retained,),
                NOW + timedelta(days=6),
                lambda _: manifest(parent),
            )
            assert isinstance(stage, api().InputStage), stage
            path = stage.execution_inputs["child"]
            with open(path, "rb") as stream:
                assert stream.read() == b"a,b\n1,2\n"
            with pytest.raises(TypeError):
                stage.execution_inputs["child"] = "bad"
            assert tx.check(stage) is None
            child = tx.commit(stage, NOW + timedelta(days=8))
            assert isinstance(child, InputMetadata)
            assert child.expires_at == NOW + timedelta(days=15)
            assert tx.settle(stage, manifest(child)) is None
        assert not (storage / identity().value).exists()
        assert (
            storage / identity(2).value / "000.bin"
        ).read_bytes() == b"a,b\n1,2\n"
        assert isinstance(store.delete(identity()), api().AbsentInputs)
        source.rename(source.with_name("lost-source"))
        publish(
            store,
            identity(3),
            (RetainedInput("again", identity(2), "child", spec.sha256),),
            NOW + timedelta(days=9),
            lambda _: manifest(child),
        )
        assert child.created_at == NOW + timedelta(days=8)
        assert isinstance(store.delete(identity(2)), api().DeletedInputs)
        assert (storage / identity(3).value / "000.bin").exists()
        assert store.maintain(NOW + timedelta(days=17)) is None
        assert not (storage / identity(3).value).exists()
    finally:
        store.close()
        grant.close()


@pytest.mark.parametrize(
    "observation", [NotFound(), CorruptArtifact(), PublicationError()]
)
def test_retained_admission_returns_commit_observation(
    owned_input_root, observation
):
    """Missing/damaged/unobservable commits deny reuse without deleting bytes."""
    storage, source, grant, _, _ = fixture(owned_input_root)
    store = api().InputStore.open(grant, NOW)
    try:
        spec = selection(source)
        publish(store, identity(), (spec,))
        with store.transaction() as tx:
            result = tx.prepare(
                identity(2),
                (RetainedInput("x", identity(), "sample", spec.sha256),),
                NOW,
                lambda _: observation,
            )
            assert isinstance(result, type(observation)), result
        assert (storage / identity().value / "000.bin").exists()
    finally:
        store.close()
        grant.close()


def test_expired_admission_precedes_operation_maintenance(owned_input_root):
    """Requested expired-unswept input returns Expired before after-work sweeping."""
    storage, source, grant, _, _ = fixture(owned_input_root)
    store = api().InputStore.open(grant, NOW)
    try:
        spec = selection(source)
        parent = publish(store, identity(), (spec,))
        with store.transaction() as tx:
            result = tx.prepare(
                identity(2),
                (RetainedInput("x", identity(), "sample", spec.sha256),),
                parent.expires_at,
                lambda _: manifest(parent),
            )
            assert result == Expired(parent.expires_at)
        assert not (storage / identity().value).exists()
    finally:
        store.close()
        grant.close()


@pytest.mark.parametrize(
    "sizes",
    [
        (0,) * 8,
        (0,) * 9,
        (8 * MIB,),
        (8 * MIB,) * 4,
        (8 * MIB + 1,),
        (8 * MIB,) * 5,
    ],
)
def test_real_copy_boundaries(owned_input_root, sizes):
    """Eight files, 8MiB/file and 32MiB aggregate are measured from real bytes."""
    storage, source, grant, _, _ = fixture(owned_input_root)
    store = api().InputStore.open(grant, NOW)
    try:
        specs = tuple(
            selection(source, b"x" * size, f"n{i}", f"f{i}")
            for i, size in enumerate(sizes)
        )
        with store.transaction() as tx:
            stage = tx.prepare(identity(), specs, NOW, lambda _: NotFound())
            if len(sizes) > 8 or max(sizes) > 8 * MIB or sum(sizes) > 32 * MIB:
                assert isinstance(stage, InvalidRequest), stage
            else:
                assert isinstance(stage, api().InputStage), stage
                assert sum(f.size_bytes for f in stage.files) == sum(sizes)
                assert tx.check(stage) is None
        assert not any(p.is_dir() for p in storage.iterdir())
    finally:
        store.close()
        grant.close()


@pytest.mark.parametrize("mutation", ["replace", "hardlink", "mode", "content"])
def test_pinned_stage_namespace_guards(owned_input_root, mutation):
    """Execution cannot substitute an entry, relax ownership or mutate copied bytes."""
    storage, source, grant, _, _ = fixture(owned_input_root)
    store = api().InputStore.open(grant, NOW)
    try:
        with store.transaction() as tx:
            stage = tx.prepare(
                identity(), (selection(source),), NOW, lambda _: NotFound()
            )
            assert isinstance(stage, api().InputStage)
            path = next(iter(stage.execution_inputs.values()))
            if mutation == "replace":
                os.unlink(path)
                with open(path, "wb") as stream:
                    stream.write(b"a,b\n1,2\n")
                os.chmod(path, 0o600)
            elif mutation == "hardlink":
                os.link(path, storage / "outside-link")
            elif mutation == "mode":
                os.chmod(path, 0o644)
            else:
                with open(path, "wb") as stream:
                    stream.write(b"changed")
            assert isinstance(
                tx.check(stage), (InvalidRequest, PublicationError)
            )
    finally:
        store.close()
        grant.close()


def test_capacity_counts_reservations_metadata_pending_and_revoked(
    owned_input_root,
):
    """Actual residue plus full reservation refuses over 512MiB without eviction."""
    storage, source, grant, _, _ = fixture(owned_input_root)
    store = api().InputStore.open(grant, NOW)
    try:
        spec = selection(source, b"")
        # Real allocated file bytes, no sparse/truncate-only substitute for quota.
        residue = storage / identity(99).value
        residue.mkdir(mode=0o700)
        with (residue / "000.bin").open("wb") as stream:
            chunk = b"x" * MIB
            for _ in range(479):
                stream.write(chunk)
            stream.write(b"x" * (MIB - 32770))
        (residue / "000.bin").chmod(0o600)
        (residue / "inputs.json").write_bytes(b"m" * 16384)
        (residue / "inputs.json").chmod(0o600)
        (residue / ".revoked").write_bytes(b"1")
        (residue / ".revoked").chmod(0o600)
        actual = sum(path.stat().st_size for path in residue.iterdir())
        assert actual + RESERVATION == 512 * MIB
        with store.transaction() as tx:
            stage = tx.prepare(identity(), (spec,), NOW, lambda _: NotFound())
            assert isinstance(stage, api().InputStage), stage
            # A second admission must not reuse the live reservation.
            assert isinstance(
                tx.prepare(identity(2), (spec,), NOW, lambda _: NotFound()),
                PublicationError,
            )
        with (residue / "000.bin").open("ab") as stream:
            stream.write(b"x")
        with store.transaction() as tx:
            assert isinstance(
                tx.prepare(identity(), (spec,), NOW, lambda _: NotFound()),
                PublicationError,
            )
        assert (residue / "000.bin").stat().st_size > 470 * MIB
        print(
            json.dumps(
                {
                    "phase": "quota",
                    "actual_residue_bytes": actual,
                    "reservation_bytes": RESERVATION,
                    "boundary_bytes": actual + RESERVATION,
                    "one_extra_byte_refused": True,
                    "evicted_live_sets": 0,
                }
            )
        )
    finally:
        store.close()
        grant.close()


@pytest.mark.parametrize("residue_state", ["committed", "pending", "revoked"])
def test_128_sets_and_one_startup_lock(owned_input_root, residue_state):
    """Unknown committed sets consume all slots; a second real server is refused."""
    storage, source, grant, _, _ = fixture(owned_input_root)
    store = api().InputStore.open(grant, NOW)
    try:
        assert isinstance(api().InputStore.open(grant, NOW), ConfigurationError)
        spec = selection(source, b"")
        for n in range(1, 129):
            (storage / identity(n).value).mkdir(mode=0o700)
        last = storage / identity(128).value
        if residue_state == "pending":
            last = last.rename(storage / (".pending-" + identity(128).value))
            (last / "unknown").write_bytes(
                b"retain/count unsafe pending residue"
            )
        elif residue_state == "revoked":
            (last / ".revoked").write_bytes(b"1")
            (last / ".revoked").chmod(0o600)
        with store.transaction() as tx:
            assert isinstance(
                tx.prepare(identity(200), (spec,), NOW, lambda _: NotFound()),
                PublicationError,
            )
        if residue_state == "pending":
            assert (last / "unknown").exists()
            (last / "unknown").unlink()
        assert isinstance(store.delete(identity(128)), api().DeletedInputs)
        publish(store, identity(200), (spec,))
        assert len([p for p in storage.iterdir() if p.is_dir()]) == 128
    finally:
        store.close()
        store.close()
        reopened = api().InputStore.open(grant, NOW)
        assert isinstance(reopened, api().InputStore)
        reopened.close()
        grant.close()


def test_seeded_capacity_sequences():
    """Reservations/releases obey both fixed bounds over generated operation paths."""
    rng = random.Random(4004)
    reservations = []
    for _ in range(1000):
        used = sum(reservations)
        if rng.randrange(3) and can_reserve(
            used, len(reservations), RESERVATION
        ):
            reservations.append(RESERVATION)
        elif reservations:
            reservations.pop(rng.randrange(len(reservations)))
        assert sum(reservations) <= 512 * MIB
        assert len(reservations) <= 128
    assert can_reserve(512 * MIB - RESERVATION, 127, RESERVATION)
    assert not can_reserve(512 * MIB - RESERVATION + 1, 127, RESERVATION)
    assert not can_reserve(0, 128, RESERVATION)


def test_seeded_set_sequences_against_independent_state_model(owned_input_root):
    """Copy/reuse/delete/clock sequences preserve independently modeled live bytes."""
    storage, source, grant, _, _ = fixture(owned_input_root)
    store = api().InputStore.open(grant, NOW)
    rng = random.Random(4004004)
    facts, live = {}, {}
    at = NOW
    spec = selection(source)
    try:
        for n in range(70):
            operation = rng.choice(("copy", "reuse", "delete", "advance"))
            target = rng.choice(tuple(facts)) if facts else identity(999)
            new_id = identity(1000 + n)
            if operation == "copy":
                live[new_id] = publish(store, new_id, (spec,), at)
                facts[new_id] = live[new_id]
            elif operation == "reuse":
                retained = RetainedInput(
                    "sample", target, "sample", spec.sha256
                )
                if target in live:
                    live[new_id] = publish(
                        store,
                        new_id,
                        (retained,),
                        at,
                        lambda selected: manifest(facts[selected]),
                    )
                    facts[new_id] = live[new_id]
                else:
                    with store.transaction() as tx:
                        assert isinstance(
                            tx.prepare(
                                new_id,
                                (retained,),
                                at,
                                lambda selected: manifest(facts[selected]),
                            ),
                            NotFound,
                        )
            elif operation == "delete":
                expected = (
                    api().DeletedInputs
                    if target in live
                    else api().AbsentInputs
                )
                assert isinstance(store.delete(target), expected)
                live.pop(target, None)
            else:
                at += timedelta(days=rng.randrange(1, 4))
            assert store.maintain(at) is None
            live = {
                key: value
                for key, value in live.items()
                if at < value.expires_at
            }
            assert {p.name for p in storage.iterdir() if p.is_dir()} == {
                key.value for key in live
            }
            for key, value in live.items():
                assert (
                    storage / key.value / "000.bin"
                ).read_bytes() == b"a,b\n1,2\n"
                assert (
                    storage / key.value / "inputs.json"
                ).read_bytes() == value.to_bytes()
    finally:
        store.close()
        grant.close()


def test_real_second_process_cannot_take_startup_lock(owned_input_root):
    """A genuinely separate interpreter cannot become the same store's second owner."""
    _, _, grant, _, policy = fixture(owned_input_root)
    store = api().InputStore.open(grant, NOW)
    code = """
import sys
from datetime import datetime
from dartwork_mpl.mcp.artifacts import configure_store
from dartwork_mpl.mcp.artifacts.input_access import InputGrant, authorize_inputs
from dartwork_mpl.mcp.artifacts.inputs import InputStore
from dartwork_mpl.mcp.artifacts.policy import ConfigurationError
artifacts = configure_store(sys.argv[2])
grant = authorize_inputs(sys.argv[1], artifacts.check_input_roots)
assert isinstance(grant, InputGrant)
assert isinstance(InputStore.open(grant, datetime.fromisoformat(sys.argv[3])), ConfigurationError)
grant.close()
print("second-owner-refused")
"""
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)}
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                code,
                str(policy),
                str(owned_input_root / "artifacts"),
                NOW.isoformat(),
            ],
            text=True,
            capture_output=True,
            timeout=15,
            env=env,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "second-owner-refused" in result.stdout
    finally:
        store.close()
        grant.close()


def test_close_and_delete_wait_for_active_stage(owned_input_root):
    """Serial deletion cannot run while admitted execution still owns its stage."""
    _, source, grant, _, _ = fixture(owned_input_root)
    store = api().InputStore.open(grant, NOW)
    done = threading.Event()
    started = threading.Event()

    def delete():
        """Expose completion only after the transaction releases the serial lock."""
        started.set()
        assert isinstance(store.delete(identity()), api().AbsentInputs)
        done.set()

    try:
        with store.transaction() as tx:
            stage = tx.prepare(
                identity(), (selection(source),), NOW, lambda _: NotFound()
            )
            assert isinstance(stage, api().InputStage)
            thread = threading.Thread(target=delete)
            thread.start()
            assert started.wait(2)
            assert not done.wait(0.05)
        thread.join(5)
        assert done.is_set()
    finally:
        store.close()
        grant.close()


def test_failed_postcheck_cannot_be_retried(owned_input_root):
    """A refused postcheck consumes its sole data pass, even if bytes are restored."""
    _, source, grant, _, _ = fixture(owned_input_root)
    store = api().InputStore.open(grant, NOW)
    try:
        with store.transaction() as tx:
            stage = tx.prepare(
                identity(), (selection(source),), NOW, lambda _: NotFound()
            )
            assert isinstance(stage, api().InputStage)
            path = Path(stage.execution_inputs["sample"])
            path.write_bytes(b"changed")
            assert isinstance(tx.check(stage), InvalidRequest)
            path.write_bytes(b"a,b\n1,2\n")
            assert isinstance(tx.check(stage), PublicationError)
            assert isinstance(tx.commit(stage, NOW), PublicationError)
    finally:
        store.close()
        grant.close()


def test_replaced_stage_directory_is_not_this_calls_rollback(owned_input_root):
    """An active stage's replacement is denied/preserved instead of guessed owned."""
    storage, source, grant, _, _ = fixture(owned_input_root)
    store = api().InputStore.open(grant, NOW)
    try:
        with store.transaction() as tx:
            stage = tx.prepare(
                identity(), (selection(source),), NOW, lambda _: NotFound()
            )
            assert isinstance(stage, api().InputStage)
            pending = Path(stage.execution_inputs["sample"]).parent
            pending.rename(storage / "displaced-stage")
            pending.mkdir(mode=0o700)
            (pending / "000.bin").write_bytes(b"replacement must survive")
            (pending / "000.bin").chmod(0o600)
            assert isinstance(tx.check(stage), PublicationError)
        assert (pending / "000.bin").read_bytes() == b"replacement must survive"
        assert (
            storage / "displaced-stage" / "000.bin"
        ).read_bytes() == b"a,b\n1,2\n"
    finally:
        store.close()
        grant.close()


@pytest.mark.parametrize("mutation", ["mode", "hardlink", "entry", "set"])
def test_retained_source_guards_surround_the_single_copy_pass(
    owned_input_root, monkeypatch, mutation
):
    """Retained owner/mode/link/exact namespace checks survive worker-boundary races."""
    storage, source, grant, _, _ = fixture(owned_input_root)
    store = api().InputStore.open(grant, NOW)
    io = importlib.import_module("dartwork_mpl.mcp.artifacts.input_io")
    original_wait = io._wait_worker
    try:
        spec = selection(source)
        parent = publish(store, identity(), (spec,))
        folder = storage / identity().value

        def change_after_copy(process, payload, seconds):
            """Complete a genuine worker, then mutate the retained namespace once."""
            result = original_wait(process, payload, seconds)
            path = folder / "000.bin"
            if mutation == "mode":
                path.chmod(0o644)
            elif mutation == "hardlink":
                os.link(path, source / "alias")
            elif mutation == "entry":
                path.rename(folder / "001.bin")
                path.write_bytes(b"a,b\n1,2\n")
                path.chmod(0o600)
            else:
                folder.rename(storage / "renamed-parent")
            return result

        monkeypatch.setattr(io, "_wait_worker", change_after_copy)
        with store.transaction() as tx:
            result = tx.prepare(
                identity(2),
                (RetainedInput("x", identity(), "sample", spec.sha256),),
                NOW,
                lambda _: manifest(parent),
            )
            assert isinstance(result, PublicationError), result
        assert not (storage / identity(2).value).exists()
    finally:
        store.close()
        grant.close()


def test_store_keeps_lock_and_capacity_until_real_worker_reap(
    owned_input_root, monkeypatch
):
    """Cancellation reaps an actually blocked child before cleanup/close releases pins."""
    storage, source, grant, _, _ = fixture(owned_input_root)
    baseline = len(os.listdir("/dev/fd"))
    store = api().InputStore.open(grant, NOW)
    spec = selection(source)
    io = importlib.import_module("dartwork_mpl.mcp.artifacts.input_io")
    ready_r, ready_w = os.pipe()
    blocked_r, blocked_w = os.pipe()
    processes = []
    ready, cancel, closed = (
        threading.Event(),
        threading.Event(),
        threading.Event(),
    )
    errors = []

    def spawn(fds):
        """Use the existing owned adapter to block a real explicitly passed FD."""
        process = subprocess.Popen(
            [
                sys.executable,
                "-I",
                "-S",
                "-c",
                f"import os; os.write({ready_w}, b'R'); os.read({blocked_r}, 1);\n"
                + io._worker_code(),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            pass_fds=(*fds, ready_w, blocked_r),
        )
        processes.append(process)
        return process

    def wait(process, payload, seconds):
        """Cancel only after the test observes held stage/lock and a blocked closer."""
        assert select.select([ready_r], [], [], 3)[0]
        assert os.read(ready_r, 1) == b"R"
        ready.set()
        assert cancel.wait(5)
        raise asyncio.CancelledError()

    def run():
        """Own a real transaction whose cancellation exits only after worker cleanup."""
        try:
            with store.transaction() as tx:
                tx.prepare(identity(), (spec,), NOW, lambda _: NotFound())
        except asyncio.CancelledError:
            assert processes[0].returncode is not None
        except BaseException as error:
            errors.append(error)

    def close():
        """A closer waits for the transaction to reap and release its reservation."""
        store.close()
        closed.set()

    monkeypatch.setattr(io, "_spawn_worker", spawn)
    monkeypatch.setattr(io, "_wait_worker", wait)
    worker = threading.Thread(target=run)
    closer = threading.Thread(target=close)
    try:
        worker.start()
        assert ready.wait(5)
        assert (storage / (".pending-" + identity().value) / "000.bin").exists()
        assert isinstance(api().InputStore.open(grant, NOW), ConfigurationError)
        closer.start()
        assert not closed.wait(0.05)
        assert processes[0].poll() is None
        cancel.set()
        worker.join(5)
        closer.join(5)
        assert closed.is_set() and not errors
        assert not any(p.is_dir() for p in storage.iterdir())
        assert processes[0].returncode is not None
        with pytest.raises(ProcessLookupError):
            os.kill(processes[0].pid, 0)
        print(
            json.dumps(
                {
                    "phase": "store_cancel",
                    "pid": processes[0].pid,
                    "returncode": processes[0].returncode,
                    "pending_remaining": 0,
                    "fd_baseline": baseline,
                }
            )
        )
    finally:
        cancel.set()
        worker.join(5)
        if closer.ident is not None:
            closer.join(5)
        store.close()
        for fd in (ready_r, ready_w, blocked_r, blocked_w):
            os.close(fd)
        assert len(os.listdir("/dev/fd")) == baseline
        grant.close()
