"""Owned startup, concurrent SDK RUNs and cancellation keep real pins until reap."""

import asyncio
import hashlib
import importlib
import json
import os
import random
import subprocess
import sys
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

fastmcp = pytest.importorskip("fastmcp")
from dartwork_mpl.mcp.artifacts import (  # noqa: E402
    configure_store,
    register_artifacts,
)
from dartwork_mpl.mcp.artifacts.delivery import render_artifact  # noqa: E402
from dartwork_mpl.mcp.artifacts.input_access import (  # noqa: E402
    InputGrant,
    authorize_inputs,
)
from dartwork_mpl.mcp.artifacts.input_policy import Revision  # noqa: E402
from dartwork_mpl.mcp.artifacts.inputs import InputStore  # noqa: E402
from dartwork_mpl.mcp.artifacts.policy import (  # noqa: E402
    ConfigurationError,
    RenderRequest,
)
from dartwork_mpl.mcp.artifacts.store import ArtifactStore  # noqa: E402

FIGURE = """import matplotlib.pyplot as plt
import dartwork_mpl as dm
dm.style.use('scientific')
fig, ax = plt.subplots(figsize=dm.figsize('6cm', 'square'))
ax.plot([1, 2], [3, 4], linewidth=dm.lw(0))
dm.simple_layout(fig)
"""


def api():
    """Require the public runtime with an assertion-visible preimplementation RED."""
    package = importlib.import_module("dartwork_mpl.mcp.artifacts")
    assert hasattr(package, "ArtifactRuntime"), (
        "owned input lifecycle is missing"
    )
    return importlib.import_module("dartwork_mpl.mcp.artifacts.lifecycle")


def fixture(root):
    """Supply only disposable operator-owned roots, never an installed policy."""
    storage, source = root / "inputs", root / "source"
    storage.mkdir(mode=0o700)
    source.mkdir(mode=0o700)
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
    store = configure_store(str(root / "artifacts"))
    assert isinstance(store, ArtifactStore)
    return path, storage, source, store


def fd_count():
    """Count genuine open descriptors without opening a descriptor directory."""
    count = 0
    for fd in range(512):
        try:
            os.fstat(fd)
            count += 1
        except OSError:  # noqa: PERF203 -- only fstat defines descriptor liveness
            pass
    return count


async def until(predicate):
    """Yield to owned work until an observable condition or a bounded test failure."""

    async def wait():
        """Poll only test observations, bounded by the outer deadline."""
        while not predicate():
            await asyncio.sleep(0.005)

    await asyncio.wait_for(wait(), 15)


def lock_available(path, store):
    """Test real startup-lock exclusion through public grants and store factories."""
    grant = authorize_inputs(str(path), store.check_input_roots)
    assert isinstance(grant, InputGrant)
    try:
        second = InputStore.open(grant, datetime.now(timezone.utc))
        if isinstance(second, InputStore):
            second.close()
            return True
        assert isinstance(second, ConfigurationError)
        return False
    finally:
        grant.close()


def value(result):
    """Compare structured and text envelopes including native isError semantics."""
    body = json.loads(result.content[-1].text)
    assert result.structured_content == body
    assert result.is_error == (body.get("delivery_status") == "error")
    return body


def revision(source):
    """Declare the bytes actually placed in the allowed source root."""
    data = b"x,y\n1,2\n"
    (source / "sample.csv").write_bytes(data)
    return {
        "schema_version": 1,
        "inputs": [
            {
                "kind": "copy",
                "name": "sample",
                "root_id": "data",
                "relative_path": "sample.csv",
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        ],
    }


def test_lifecycle_import_sessions_and_close(owned_input_root):
    """Construction is inert; overlapping owners and serial reopen retain one lock."""
    module = api()
    path, storage, _, store = fixture(owned_input_root)
    before = fd_count()
    runtime = module.ArtifactRuntime(store, str(path))
    assert fd_count() == before and list(storage.iterdir()) == []

    async def workflow():
        """Close one of two owners, then reopen after last-close and explicit close."""
        async with runtime.session():
            async with runtime.session():
                async with runtime.admission() as inputs:
                    assert isinstance(inputs, InputStore)
                assert not lock_available(path, store)
            assert not lock_available(path, store)
        assert lock_available(path, store)
        for _ in range(3):
            async with runtime.session():
                assert not lock_available(path, store)
                await runtime.close()
                await runtime.close()
                assert lock_available(path, store)
        async with runtime.admission() as inputs:
            assert isinstance(inputs, ConfigurationError)
        await runtime.close()

    asyncio.run(workflow())
    assert fd_count() == before


@pytest.mark.parametrize(
    "policy", ["unset", "invalid", "unsupported", "artifact_invalid"]
)
def test_disabled_or_invalid_startup_preserves_legacy(
    owned_input_root, monkeypatch, policy
):
    """Retention refusal never disables legacy render/get/resources or parent-only."""
    module = api()
    path, storage, source, store = fixture(owned_input_root)
    if policy == "invalid":
        path.write_text("{")
    if policy == "unsupported":
        import dartwork_mpl.mcp.artifacts.input_access as access

        monkeypatch.setattr(access, "_platform_supported", lambda: False)
    runtime = module.ArtifactRuntime(
        ConfigurationError() if policy == "artifact_invalid" else store,
        None if policy == "unset" else str(path),
    )
    instance = fastmcp.FastMCP("retention-refusal")
    register_artifacts(instance, store, runtime=runtime)
    spec = revision(source)
    before = fd_count()

    async def workflow():
        """Exercise actual protocol calls, including opt-in refusal and safe resources."""
        async with fastmcp.Client(instance) as client:
            result = value(
                await client.call_tool("render_plot", {"code": FIGURE})
            )
            assert result["delivery_status"] == "ready"
            parent = result["artifact_id"]
            parent_only = value(
                await client.call_tool(
                    "render_plot",
                    {
                        "code": FIGURE,
                        "revision": {
                            "schema_version": 1,
                            "parent_artifact_id": parent,
                        },
                    },
                )
            )
            assert parent_only["delivery_status"] == "ready"
            assert (
                value(
                    await client.call_tool(
                        "get_plot_artifact", {"artifact_id": parent}
                    )
                )
                == result
            )
            assert (await client.read_resource(result["files"][2]["uri"]))[
                0
            ].text == FIGURE
            for name, args in [
                ("render_plot", {"code": FIGURE, "revision": spec}),
                ("delete_plot_inputs", {"artifact_id": parent}),
            ]:
                assert (
                    value(
                        await client.call_tool(name, args, raise_on_error=False)
                    )["error_code"]
                    == "configuration_error"
                )
            assert len(await client.list_tools()) == 3
        await runtime.close()
        assert not any(p.is_dir() for p in storage.iterdir())

    asyncio.run(workflow())
    assert fd_count() == before


@pytest.mark.parametrize("policy", ["valid", "invalid", "unsupported", "unset"])
def test_fresh_import_never_reads_policy_or_opens_input_resources(
    owned_input_root, policy
):
    """Fresh shipped-server imports acquire no root FD, lock, task or storage path."""
    api()
    path, storage, _, _ = fixture(owned_input_root)
    if policy == "invalid":
        path.write_text("{")
    code = """import asyncio, os, sys
import dartwork_mpl
async def check():
    "Imports must not acquire any configured input resource or task."
    target = sys.argv[1]
    original = os.open
    def guarded(path, *args, **kwargs):
        "Refuse policy reads and lock acquisition at the actual OS open boundary."
        assert str(path) not in {target, os.path.basename(target)} and '.lock' not in str(path), ('input opened on import', path)
        return original(path, *args, **kwargs)
    os.open = guarded
    before = set(asyncio.all_tasks())
    if sys.argv[2] == 'unsupported':
        os.name = 'unsupported'
    import dartwork_mpl.mcp.server
    assert set(asyncio.all_tasks()) == before
asyncio.run(check())
"""
    env = dict(os.environ)
    if policy == "unset":
        env.pop("DARTWORK_MPL_INPUT_POLICY", None)
    else:
        env["DARTWORK_MPL_INPUT_POLICY"] = str(path)
    result = subprocess.run(
        [sys.executable, "-c", code, str(path), policy],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert list(storage.iterdir()) == []


def test_distinct_clients_overlap_startup_first_exit_and_reopen(
    owned_input_root,
):
    """Two distinct Client(mcp) contexts share one startup even when first exits first."""
    module = api()
    path, _, source, store = fixture(owned_input_root)
    runtime = module.ArtifactRuntime(store, str(path))
    instance = fastmcp.FastMCP("distinct-clients")
    register_artifacts(instance, store, runtime=runtime)
    spec = revision(source)
    before = fd_count()

    async def workflow():
        """Enter connections in separate tasks; keep second useful after first closes."""
        first_ready, second_ready, leave_first, first_gone, leave_second = [
            asyncio.Event() for _ in range(5)
        ]

        async def owner_one():
            """The first SDK RUN must not own the second connection's teardown."""
            async with fastmcp.Client(instance) as client:
                first_ready.set()
                await second_ready.wait()
                assert not lock_available(path, store)
                await leave_first.wait()
                assert len(await client.list_tools()) == 3
            first_gone.set()

        async def owner_two():
            """Retained Copy/delete remain usable after the first RUN has exited."""
            await first_ready.wait()
            async with fastmcp.Client(instance) as client:
                second_ready.set()
                leave_first.set()
                await first_gone.wait()
                assert not lock_available(path, store)
                rendered = value(
                    await client.call_tool(
                        "render_plot", {"code": FIGURE, "revision": spec}
                    )
                )
                assert rendered["delivery_status"] == "ready"
                result = value(
                    await client.call_tool(
                        "delete_plot_inputs",
                        {"artifact_id": rendered["artifact_id"]},
                    )
                )
                assert result == {
                    "schema_version": 1,
                    "artifact_id": rendered["artifact_id"],
                    "state": "deleted",
                }
                await leave_second.wait()

        first, second = (
            asyncio.create_task(owner_one()),
            asyncio.create_task(owner_two()),
        )
        await first
        assert not lock_available(path, store)
        leave_second.set()
        await second
        assert lock_available(path, store)
        async with fastmcp.Client(instance) as client:
            result = value(
                await client.call_tool(
                    "delete_plot_inputs", {"artifact_id": uuid4().hex}
                )
            )
            assert result["state"] == "absent"
        assert lock_available(path, store)

    asyncio.run(workflow())
    assert fd_count() == before


@pytest.mark.parametrize("phase", ["grant", "store"])
def test_cancelled_partial_startup_joins_late_open_and_closes(
    owned_input_root, monkeypatch, phase
):
    """A cancelled startup cannot discard a late thread's grant or open store."""
    module = api()
    path, _, _, store = fixture(owned_input_root)
    runtime = module.ArtifactRuntime(store, str(path))
    started, release = threading.Event(), threading.Event()
    pins = []
    original = module.authorize_inputs if phase == "grant" else InputStore.open

    def blocked(*args):
        """Block after real resource acquisition to expose late-result ownership."""
        result = original(*args)
        pins.append(result)
        started.set()
        assert release.wait(15)
        return result

    if phase == "grant":
        monkeypatch.setattr(module, "authorize_inputs", blocked)
    else:
        monkeypatch.setattr(InputStore, "open", blocked)
    before = fd_count()

    async def workflow():
        """Cancellation waits for opened resources to be handed back and closed."""

        async def session():
            """Start only; cancellation before yield must still reclaim everything."""
            async with runtime.session():
                pytest.fail("cancelled startup admitted a session")

        task = asyncio.create_task(session())
        await until(started.is_set)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        task.cancel()
        close = asyncio.create_task(runtime.close())
        await asyncio.sleep(0)
        assert not close.done()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        await close
        await runtime.close()

    try:
        asyncio.run(workflow())
    finally:
        release.set()
    if phase == "grant":
        assert isinstance(pins[0].duplicate_storage(), ConfigurationError)
    assert fd_count() == before
    # Restore the own seam before testing a fresh real startup.
    monkeypatch.undo()
    assert lock_available(path, store)


@pytest.mark.parametrize("blocked_phase", ["export", "copy", "legacy_export"])
def test_cancelled_call_and_final_close_keep_lock_fds_and_reap(
    owned_input_root, monkeypatch, blocked_phase
):
    """Cancellation and final close cannot release admission, pins or lock before reap."""
    module = api()
    path, storage, source, store = fixture(owned_input_root)
    runtime = module.ArtifactRuntime(store, str(path))
    spec = revision(source)
    from dartwork_mpl.mcp.artifacts.input_policy import parse_revision

    parsed = parse_revision(spec)
    assert isinstance(parsed, Revision)
    if blocked_phase == "legacy_export":
        parsed = None
    marker, release = owned_input_root / "pid", owned_input_root / "release"
    code = FIGURE
    if blocked_phase != "copy":
        code += f"import os, time\nfrom pathlib import Path\nPath({str(marker)!r}).write_text(str(os.getpid()))\nwhile not Path({str(release)!r}).exists(): time.sleep(0.01)\n"
    else:
        from dartwork_mpl.mcp.artifacts import input_io

        original = input_io._worker_code

        def worker_code():
            """Block the actual owned worker's first read, without weakening guards."""
            return original().replace(
                "return os.pread(fd, amount, offset)",
                f"\n    import time\n    from pathlib import Path\n    Path({str(marker)!r}).write_text(str(os.getpid()))\n    while not Path({str(release)!r}).exists(): time.sleep(0.01)\n    return os.pread(fd, amount, offset)",
            )

        monkeypatch.setattr(input_io, "_worker_code", worker_code)
    before = fd_count()

    async def workflow():
        """Observe a real child/stage before cancellation and competing close."""
        async with runtime.session():

            async def call():
                """Own blocking delivery and its admission until synchronous return."""
                async with runtime.admission() as inputs:
                    return await module.run_owned(
                        lambda: render_artifact(
                            store,
                            RenderRequest(code, timeout_seconds=20),
                            lambda: datetime.now(timezone.utc),
                            revision=parsed,
                            inputs=inputs,
                        )
                    )

            task = asyncio.create_task(call())
            try:
                await until(marker.exists)
                pid = int(marker.read_text())
                os.kill(pid, 0)
                if blocked_phase != "legacy_export":
                    assert any(storage.glob(".pending-*/000.bin"))
                pins = fd_count()
                task.cancel()
                await asyncio.sleep(0)
                task.cancel()
                close = asyncio.create_task(runtime.close())
                await until(lambda: not runtime.accepting)
                async with runtime.admission() as denied:
                    assert isinstance(denied, ConfigurationError)
                assert not task.done() and not close.done()
                assert fd_count() >= pins and not lock_available(path, store)
                release.touch()
                with pytest.raises(asyncio.CancelledError):
                    await task
                await close
                with pytest.raises(ProcessLookupError):
                    os.kill(pid, 0)
                assert not list(storage.glob(".pending-*"))
                assert lock_available(path, store)
                print(
                    json.dumps(
                        {
                            "phase": blocked_phase,
                            "pid": pid,
                            "reaped": True,
                            "held_fds": pins,
                            "before": before,
                            "after_close": fd_count(),
                        }
                    )
                )
            finally:
                release.touch()
                await asyncio.gather(task, return_exceptions=True)
                await runtime.close()

    asyncio.run(workflow())
    assert fd_count() == before


def test_operation_tail_and_periodic_maintenance_use_fresh_clocks(
    owned_input_root, monkeypatch
):
    """No prelookup sweep; fresh tail time and owned 60s tick remove only own expiry."""
    module = api()
    path, storage, _, store = fixture(owned_input_root)
    runtime = module.ArtifactRuntime(store, str(path))
    clocks = []
    original = InputStore.maintain

    def observe(self, at):
        """Record the public maintenance boundary while preserving real effects."""
        clocks.append(at)
        return original(self, at)

    monkeypatch.setattr(InputStore, "maintain", observe)
    # Only the runtime's own timer is accelerated; production interval stays 60s.
    tick = asyncio.Event()
    sleep_original = asyncio.sleep

    async def sleep(seconds):
        """Assert the actual scheduler interval and trigger it explicitly."""
        assert seconds == 60
        await tick.wait()
        tick.clear()

    monkeypatch.setattr(module, "_sleep", sleep)

    async def workflow():
        """An operation observes no maintenance before yield, then fresh tail/tick."""
        async with runtime.session():
            assert len(clocks) == 1
            started = datetime.now(timezone.utc)
            async with runtime.admission() as inputs:
                assert isinstance(inputs, InputStore)
                assert len(clocks) == 1
                await sleep_original(0.01)
            assert len(clocks) == 2 and clocks[-1] > started
            tick.set()
            await until(lambda: len(clocks) >= 3)
            assert clocks[-1] >= clocks[-2]
        previous = len(clocks)
        tick.set()
        await sleep_original(0)
        assert len(clocks) == previous and lock_available(path, store)
        assert not any(p.is_dir() for p in storage.iterdir())

    asyncio.run(workflow())


def test_unsupported_sdk_bridge_denies_only_retention(owned_input_root):
    """A future incompatible bridge cannot open retention or break direct legacy routes."""
    module = api()
    path, storage, _, store = fixture(owned_input_root)
    runtime = module.ArtifactRuntime(store, str(path))

    class Unknown:
        """An unsupported SDK shape deliberately lacks a composable lifespan."""

    assert runtime.bind(Unknown()) is False

    async def workflow():
        """Even an explicit session safely denies without acquiring root resources."""
        async with runtime.session():
            async with runtime.admission() as inputs:
                assert isinstance(inputs, ConfigurationError)
        assert list(storage.iterdir()) == []

    asyncio.run(workflow())


def test_stdio_shipped_global_runtime_and_repeated_process_ownership(
    owned_input_root,
):
    """Actual shipped stdio starts/closes retention and preserves wire delete/errors."""
    api()
    path, _, source, store = fixture(owned_input_root)
    spec = revision(source)
    from fastmcp.client.transports import PythonStdioTransport

    script = owned_input_root / "stdio_server.py"
    script.write_text(
        "from dartwork_mpl.mcp.server import mcp\nmcp.run(show_banner=False)\n"
    )
    env = {
        "DARTWORK_MPL_INPUT_POLICY": str(path),
        "DARTWORK_MPL_ARTIFACT_DIR": str(owned_input_root / "artifacts"),
    }

    async def workflow():
        """Use fresh server processes, not an in-memory surrogate for stdio."""
        identity = None
        for _ in range(2):
            transport = PythonStdioTransport(
                script_path=script,
                python_cmd=sys.executable,
                env=env,
                keep_alive=False,
            )
            async with fastmcp.Client(transport) as client:
                assert len(await client.list_tools()) == 19
                assert not lock_available(path, store)
                if identity is None:
                    rendered = value(
                        await client.call_tool(
                            "render_plot", {"code": FIGURE, "revision": spec}
                        )
                    )
                    assert rendered["delivery_status"] == "ready"
                    identity = rendered["artifact_id"]
                else:
                    assert (
                        value(
                            await client.call_tool(
                                "get_plot_artifact", {"artifact_id": identity}
                            )
                        )["artifact_id"]
                        == identity
                    )
                    for state in ("deleted", "absent"):
                        assert value(
                            await client.call_tool(
                                "delete_plot_inputs", {"artifact_id": identity}
                            )
                        ) == {
                            "schema_version": 1,
                            "artifact_id": identity,
                            "state": state,
                        }
                assert (
                    value(
                        await client.call_tool(
                            "delete_plot_inputs",
                            {"artifact_id": "../bad"},
                            raise_on_error=False,
                        )
                    )["error_code"]
                    == "invalid_request"
                )
            assert lock_available(path, store)

    asyncio.run(workflow())


def test_simultaneous_client_startups_authorize_once_and_preserve_sdk_context(
    owned_input_root, monkeypatch
):
    """Overlapping distinct connections cannot double-open; saved SDK context is exact."""
    module = api()
    path, _, _, store = fixture(owned_input_root)
    instance = fastmcp.FastMCP("simultaneous-start")
    original_lifespan = instance._mcp_server.lifespan
    contexts = []

    @asynccontextmanager
    async def original(server):
        """Retain the original framework context while proving identity preservation."""
        async with original_lifespan(server) as context:
            contexts.append(context)
            yield context

    instance._mcp_server.lifespan = original
    runtime = module.ArtifactRuntime(store, str(path))
    register_artifacts(instance, store, runtime=runtime)
    started, release = threading.Event(), threading.Event()
    calls = []
    authorize = module.authorize_inputs

    def blocked(*args):
        """Block the first real grant so all competing startups overlap it."""
        grant = authorize(*args)
        calls.append(grant)
        started.set()
        assert release.wait(15)
        return grant

    monkeypatch.setattr(module, "authorize_inputs", blocked)

    async def workflow():
        """Both real clients must initialize with one shared input-store owner."""
        all_ready, finish = asyncio.Event(), asyncio.Event()
        ready = []

        async def client():
            """Keep independently connected RUNs open until both have initialized."""
            async with fastmcp.Client(instance) as connected:
                assert len(await connected.list_tools()) == 3
                ready.append(True)
                if len(ready) == 2:
                    all_ready.set()
                await finish.wait()

        tasks = [asyncio.create_task(client()) for _ in range(2)]
        try:
            await until(started.is_set)
            await asyncio.sleep(0.01)
            assert len(calls) == 1
            release.set()
            await asyncio.wait_for(all_ready.wait(), 15)
            assert len(calls) == 1 and len(contexts) == 2
            assert not lock_available(path, store)
        finally:
            release.set()
            finish.set()
            await asyncio.gather(*tasks)
        assert lock_available(path, store)
        # SDK state sees the very same object yielded by the saved callback.
        async with instance._mcp_server.lifespan(
            instance._mcp_server
        ) as context:
            assert context is contexts[-1]

    asyncio.run(workflow())


def test_close_cancellation_and_maintenance_join_before_store_grant_close(
    owned_input_root, monkeypatch
):
    """A blocked owned sweep and repeated closer cancellation cannot drop the lock."""
    module = api()
    path, _, _, store = fixture(owned_input_root)
    runtime = module.ArtifactRuntime(store, str(path))
    started, release = threading.Event(), threading.Event()
    tick = asyncio.Event()
    original = InputStore.maintain
    count = []

    def maintain(self, at):
        """Block the second real maintenance call, leaving startup synchronous."""
        count.append(at)
        if len(count) == 2:
            started.set()
            assert release.wait(15)
        return original(self, at)

    async def sleep(seconds):
        """Explicitly trigger a production 60s tick without waiting for its timer."""
        assert seconds == 60
        await tick.wait()
        tick.clear()

    monkeypatch.setattr(InputStore, "maintain", maintain)
    monkeypatch.setattr(module, "_sleep", sleep)
    before = fd_count()

    async def workflow():
        """Observe stopped admission and held pins while the cancelled timer drains."""
        async with runtime.session():
            tick.set()
            await until(started.is_set)
            closer = asyncio.create_task(runtime.close())
            try:
                await until(lambda: not runtime.accepting)
                closer.cancel()
                await asyncio.sleep(0)
                closer.cancel()
                assert not closer.done() and not lock_available(path, store)
                release.set()
                with pytest.raises(asyncio.CancelledError):
                    await closer
                assert len(count) == 2
                assert lock_available(path, store)
            finally:
                release.set()
                await asyncio.gather(closer, return_exceptions=True)

    asyncio.run(workflow())
    assert fd_count() == before


def test_transport_closing_refuses_new_legacy_and_retention_work(
    owned_input_root,
):
    """Closed admission cannot launch untracked legacy or parent-only export work."""
    module = api()
    path, _, _, store = fixture(owned_input_root)
    runtime = module.ArtifactRuntime(store, str(path))
    instance = fastmcp.FastMCP("closing-wire")
    register_artifacts(instance, store, runtime=runtime)
    marker = owned_input_root / "must-not-execute"
    code = FIGURE + f"from pathlib import Path\nPath({str(marker)!r}).touch()\n"

    async def workflow():
        """Actual connected tools stay registered but refuse new work after close."""
        async with fastmcp.Client(instance) as client:
            await runtime.close()
            for name, args in [
                ("render_plot", {"code": code}),
                ("delete_plot_inputs", {"artifact_id": uuid4().hex}),
            ]:
                result = value(
                    await client.call_tool(name, args, raise_on_error=False)
                )
                assert result["error_code"] == "configuration_error"
            assert not marker.exists()

    asyncio.run(workflow())


def test_seeded_session_sequences_preserve_generation_ownership(
    owned_input_root,
):
    """Old context exits never release a reopened generation's lock or admission."""
    module = api()
    path, _, _, store = fixture(owned_input_root)
    runtime = module.ArtifactRuntime(store, str(path))
    before = fd_count()

    async def workflow():
        """Compare generated enter/exit/explicit-close transitions with a plain model."""
        rng = random.Random(6006006)
        owners, generation, current = [], 0, None
        try:
            for _ in range(45):
                action = rng.choice(
                    ("enter", "enter", "exit", "close", "admit")
                )
                if action == "enter":
                    if current is None:
                        generation += 1
                        current = generation
                    context = runtime.session()
                    await context.__aenter__()
                    owners.append((context, current))
                elif action == "exit" and owners:
                    context, stamp = owners.pop(rng.randrange(len(owners)))
                    await context.__aexit__(None, None, None)
                    if stamp == current and not any(
                        g == current for _, g in owners
                    ):
                        current = None
                elif action == "close":
                    await runtime.close()
                    current = None
                async with runtime.admission() as inputs:
                    assert isinstance(
                        inputs,
                        InputStore
                        if current is not None
                        else ConfigurationError,
                    )
                assert runtime.accepting == (current is not None)
                assert lock_available(path, store) == (current is None)
        finally:
            for context, _ in reversed(owners):
                await context.__aexit__(None, None, None)
            await runtime.close()

    asyncio.run(workflow())
    assert fd_count() == before


def test_incompatible_run_shape_keeps_actual_legacy_protocol(owned_input_root):
    """Unknown RUN signatures use direct legacy tools and cannot acquire input authority."""
    module = api()
    path, storage, source, store = fixture(owned_input_root)
    runtime = module.ArtifactRuntime(store, str(path))
    instance = fastmcp.FastMCP("unknown-run")
    original = instance._mcp_server.run

    async def run(*args, **kwargs):
        """A functional future SDK adapter with an unrecognized introspection shape."""
        return await original(*args, **kwargs)

    instance._mcp_server.run = run
    register_artifacts(instance, store, runtime=runtime)
    spec = revision(source)

    async def workflow():
        """Unsupported retention must never turn into a server-wide startup failure."""
        async with fastmcp.Client(instance) as client:
            rendered = value(
                await client.call_tool(
                    "render_plot", {"code": FIGURE}, raise_on_error=False
                )
            )
            assert rendered["delivery_status"] == "ready"
            assert (
                value(
                    await client.call_tool(
                        "get_plot_artifact",
                        {"artifact_id": rendered["artifact_id"]},
                    )
                )
                == rendered
            )
            assert (await client.read_resource(rendered["files"][2]["uri"]))[
                0
            ].text == FIGURE
            assert (
                value(
                    await client.call_tool(
                        "render_plot",
                        {"code": FIGURE, "revision": spec},
                        raise_on_error=False,
                    )
                )["error_code"]
                == "configuration_error"
            )
        assert list(storage.iterdir()) == []

    asyncio.run(workflow())


def test_client_cancellation_and_final_close_join_real_transport_delivery(
    owned_input_root,
):
    """An actual cancelled MCP request cannot let final-close abandon a live export."""
    module = api()
    path, storage, source, store = fixture(owned_input_root)
    runtime = module.ArtifactRuntime(store, str(path))
    instance = fastmcp.FastMCP("wire-cancellation")
    register_artifacts(instance, store, runtime=runtime)
    marker, release = owned_input_root / "pid", owned_input_root / "release"
    code = (
        FIGURE
        + f"import os, time\nfrom pathlib import Path\nPath({str(marker)!r}).write_text(str(os.getpid()))\nwhile not Path({str(release)!r}).exists(): time.sleep(0.01)\n"
    )
    spec = revision(source)
    before = fd_count()

    async def workflow():
        """Cancel at the client boundary while the server retains all cleanup ownership."""
        async with fastmcp.Client(instance) as client:
            request = asyncio.create_task(
                client.call_tool(
                    "render_plot", {"code": code, "revision": spec}
                )
            )
            closer = None
            try:
                await until(marker.exists)
                pid = int(marker.read_text())
                request.cancel()
                closer = asyncio.create_task(runtime.close())
                await until(lambda: not runtime.accepting)
                assert not closer.done() and not lock_available(path, store)
                os.kill(pid, 0)
                assert any(storage.glob(".pending-*/000.bin"))
                release.touch()
                await asyncio.gather(request, return_exceptions=True)
                await closer
                with pytest.raises(ProcessLookupError):
                    os.kill(pid, 0)
                assert not list(storage.glob(".pending-*"))
                assert lock_available(path, store)
                print(
                    json.dumps(
                        {
                            "phase": "actual_mcp_cancellation",
                            "pid": pid,
                            "reaped": True,
                        }
                    )
                )
            finally:
                release.touch()
                await asyncio.gather(request, return_exceptions=True)
                if closer is not None:
                    await closer

    asyncio.run(workflow())
    assert fd_count() == before


def test_stdio_disconnect_joins_blocked_export_before_lock_release(
    owned_input_root,
):
    """Real stdio disconnect drains the server's owned export before releasing pins."""
    api()
    path, storage, source, store = fixture(owned_input_root)
    marker, release = owned_input_root / "pid", owned_input_root / "release"
    code = (
        FIGURE
        + f"import os, time\nfrom pathlib import Path\nPath({str(marker)!r}).write_text(str(os.getpid()))\nwhile not Path({str(release)!r}).exists(): time.sleep(0.01)\n"
    )
    spec = revision(source)
    from fastmcp.client.transports import PythonStdioTransport

    script = owned_input_root / "stdio_server.py"
    script.write_text(
        "from dartwork_mpl.mcp.server import mcp\nmcp.run(show_banner=False)\n"
    )
    env = {
        "DARTWORK_MPL_INPUT_POLICY": str(path),
        "DARTWORK_MPL_ARTIFACT_DIR": str(owned_input_root / "artifacts"),
    }

    async def workflow():
        """Cancel a live request, close the actual transport and observe the real lock."""
        ready, disconnect = asyncio.Event(), asyncio.Event()

        async def owner():
            """The transport's close must keep server cleanup alive until export returns."""
            transport = PythonStdioTransport(
                script_path=script,
                python_cmd=sys.executable,
                env=env,
                keep_alive=False,
            )
            async with fastmcp.Client(transport) as client:
                request = asyncio.create_task(
                    client.call_tool(
                        "render_plot", {"code": code, "revision": spec}
                    )
                )
                try:
                    await until(marker.exists)
                    ready.set()
                    await disconnect.wait()
                    request.cancel()
                    await asyncio.gather(request, return_exceptions=True)
                finally:
                    request.cancel()
                    await asyncio.gather(request, return_exceptions=True)

        task = asyncio.create_task(owner())
        try:
            await asyncio.wait_for(ready.wait(), 20)
            pid = int(marker.read_text())
            disconnect.set()
            await asyncio.sleep(0.1)
            assert not task.done() and not lock_available(path, store)
            os.kill(pid, 0)
            assert any(storage.glob(".pending-*/000.bin"))
            release.touch()
            await asyncio.wait_for(task, 15)
            with pytest.raises(ProcessLookupError):
                os.kill(pid, 0)
            assert not list(storage.glob(".pending-*"))
            assert lock_available(path, store)
            print(
                json.dumps(
                    {"phase": "stdio_disconnect", "pid": pid, "reaped": True}
                )
            )
        finally:
            release.touch()
            disconnect.set()
            await asyncio.gather(task, return_exceptions=True)

    asyncio.run(workflow())


def test_expired_unswept_retained_wire_precedes_tail_maintenance(
    owned_input_root, monkeypatch
):
    """An expired existing set reports expired before a fresh operation-tail sweep."""
    module = api()
    path, storage, source, store = fixture(owned_input_root)
    runtime = module.ArtifactRuntime(store, str(path))
    instance = fastmcp.FastMCP("expired-unswept")
    register_artifacts(instance, store, runtime=runtime)
    spec = revision(source)
    import dartwork_mpl.mcp.artifacts.transport as wire

    async def workflow():
        """Advance both adapter clocks after creating actual paired input/artifact bytes."""
        async with fastmcp.Client(instance) as client:
            parent = value(
                await client.call_tool(
                    "render_plot", {"code": FIGURE, "revision": spec}
                )
            )["artifact_id"]
            assert (storage / parent / "000.bin").exists()
            future = datetime.now(timezone.utc) + timedelta(days=8)

            class FutureClock:
                """Provide only the owned adapters' fresh wall clock without a real wait."""

                @staticmethod
                def now(tz):
                    """Return the same post-expiry instant for lookup and tail maintenance."""
                    return future

            monkeypatch.setattr(module, "datetime", FutureClock)
            monkeypatch.setattr(wire, "datetime", FutureClock)
            retained = {
                "schema_version": 1,
                "inputs": [
                    {
                        "kind": "retained",
                        "name": "sample",
                        "artifact_id": parent,
                        "input_name": "sample",
                        "sha256": spec["inputs"][0]["sha256"],
                    }
                ],
            }
            result = value(
                await client.call_tool(
                    "render_plot",
                    {"code": FIGURE, "revision": retained},
                    raise_on_error=False,
                )
            )
            assert result["error_code"] == "expired"
            assert not (storage / parent).exists()
            assert (source / "sample.csv").read_bytes() == b"x,y\n1,2\n"

    asyncio.run(workflow())


def test_second_runtime_startup_refusal_closes_partial_grant_and_keeps_legacy(
    owned_input_root,
):
    """An actual flock refusal releases only the failed startup's grant and pins."""
    module = api()
    path, _, source, store = fixture(owned_input_root)
    first, second = (
        module.ArtifactRuntime(store, str(path)),
        module.ArtifactRuntime(store, str(path)),
    )
    one, two = fastmcp.FastMCP("first-owner"), fastmcp.FastMCP("refused-owner")
    register_artifacts(one, store, runtime=first)
    register_artifacts(two, store, runtime=second)
    spec = revision(source)
    before = fd_count()

    async def workflow():
        """The denied second server still renders/retrieves but cannot retain/delete."""
        async with fastmcp.Client(one):
            pins = fd_count()
            async with fastmcp.Client(two) as client:
                assert fd_count() == pins
                async with second.admission() as inputs:
                    assert isinstance(inputs, ConfigurationError)
                legacy = value(
                    await client.call_tool("render_plot", {"code": FIGURE})
                )
                assert legacy["delivery_status"] == "ready"
                for name, args in [
                    ("render_plot", {"code": FIGURE, "revision": spec}),
                    (
                        "delete_plot_inputs",
                        {"artifact_id": legacy["artifact_id"]},
                    ),
                ]:
                    assert (
                        value(
                            await client.call_tool(
                                name, args, raise_on_error=False
                            )
                        )["error_code"]
                        == "configuration_error"
                    )
            assert fd_count() == pins
            assert not lock_available(path, store)
        assert lock_available(path, store)

    asyncio.run(workflow())
    assert fd_count() == before


def test_internal_resource_pairing_rejects_invalid_construction(
    owned_input_root,
):
    """A resource generation cannot hold a store without a grant or a grant without store."""
    module = api()
    path, _, _, store = fixture(owned_input_root)
    grant = authorize_inputs(str(path), store.check_input_roots)
    assert isinstance(grant, InputGrant)
    inputs = InputStore.open(grant, datetime.now(timezone.utc))
    assert isinstance(inputs, InputStore)
    try:
        for value, owner in [
            (inputs, None),
            (ConfigurationError(), grant),
            (module.InputsDisabled(), grant),
            (object(), None),
        ]:
            with pytest.raises(ValueError, match="must be paired"):
                module._Resources(value, owner)
    finally:
        inputs.close()
        grant.close()
