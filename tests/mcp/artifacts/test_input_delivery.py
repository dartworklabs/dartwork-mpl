"""Real paired publication preserves pinned receipts and refuses failed barriers."""

import asyncio
import hashlib
import json
import os
from contextlib import contextmanager
from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace

import pytest
from test_input_recovery import STATES, seed
from test_input_store import NOW, fixture, identity, selection

from dartwork_mpl.mcp import execution
from dartwork_mpl.mcp.artifacts import (
    AbsentInputs,
    ArtifactMember,
    ArtifactStore,
    ConfigurationError,
    CorruptArtifact,
    DeletedInputs,
    Expired,
    InputMetadata,
    InputsDisabled,
    InputStore,
    InputTransaction,
    InvalidRequest,
    Manifest,
    NotFound,
    PublicationError,
    RenderRequest,
    RetainedInput,
    Revision,
    StoredBundle,
    configure_store,
    delivery,
    input_cleanup,
    register_artifacts,
    render_artifact,
)
from dartwork_mpl.mcp.artifacts import store as disk

FIGURE = """import matplotlib.pyplot as plt
import dartwork_mpl as dm
dm.style.use('scientific')
fig, ax = plt.subplots(figsize=dm.figsize('6cm', 'square'))
ax.plot([1, 2], [3, 4], linewidth=dm.lw(0))
dm.simple_layout(fig)
"""


@pytest.fixture
def rig(owned_input_root):
    """Own a genuine temporary grant/store and close pins before fixture removal."""
    storage, source, grant, artifacts, _ = fixture(owned_input_root)
    inputs = InputStore.open(grant, NOW)
    assert isinstance(inputs, InputStore)
    try:
        yield SimpleNamespace(
            root=owned_input_root,
            storage=storage,
            source=source,
            artifacts=artifacts,
            inputs=inputs,
        )
    finally:
        inputs.close()
        grant.close()


def render(rig, code=FIGURE, *, specs=None, parent=None, clock=lambda: NOW):
    """Send parsed selections through the public delivery use case and real runner."""
    revision = Revision(parent, tuple(specs)) if specs is not None else None
    return render_artifact(
        rig.artifacts,
        RenderRequest(code),
        clock,
        revision=revision,
        inputs=rig.inputs,
    )


def receipt(bundle):
    """Read only the child-owned public immutable report resource."""
    assert isinstance(bundle, StoredBundle), bundle
    return json.loads(bundle.contents[ArtifactMember.REPORT])["provenance"]


def delete_api(inputs, artifact_id):
    """Assert the missing public use case meaningfully during preimplementation RED."""
    assert hasattr(delivery, "delete_inputs"), (
        "delete_inputs use case is missing"
    )
    return delivery.delete_inputs(inputs, artifact_id)


def test_legacy_bytes_and_optin_mapping(rig, monkeypatch):
    """One controlled ExportedPlot keeps legacy source/report/log/envelope bytes."""
    import fastmcp

    # Obtain real image bytes once; only this explicit controlled-result oracle
    # substitutes the exporter. It never pretends to prove subprocess behavior.
    stem = rig.root / "oracle"
    real = execution.export_plot(FIGURE, "fig", 20, None, output_stem=stem)
    assert isinstance(real, execution.ExportedPlot)
    images = {
        suffix: stem.with_suffix(suffix).read_bytes()
        for suffix in (".png", ".pdf")
    }
    report = deepcopy(real.report)
    report.update(stdout="  한글 stdout\n", stderr=" stderr \n")
    controlled = execution.ExportedPlot(report)
    pristine = deepcopy(report)
    code = '# exact café 한글\r\nvalue = "unchanged"  \r\n'
    monkeypatch.setattr(
        disk, "uuid4", lambda: SimpleNamespace(hex=identity(800).value)
    )
    expected_store = configure_store(str(rig.root / "oracle-artifacts"))
    assert isinstance(expected_store, ArtifactStore)
    with expected_store.staging() as stage:
        for suffix, data in images.items():
            stage.output_stem.with_suffix(suffix).write_bytes(data)
        expected = expected_store.publish(stage, code.encode(), report, NOW)
    assert isinstance(expected, StoredBundle)

    def controlled_export(*args, output_stem, **kwargs):
        """The legacy arm must not add even an empty input_paths keyword."""
        assert args == (code, "fig", 20.0, None)
        assert not kwargs
        for suffix, data in images.items():
            output_stem.with_suffix(suffix).write_bytes(data)
        return controlled

    monkeypatch.setattr(delivery, "export_plot", controlled_export)
    actual = render(rig, code)
    assert isinstance(actual, StoredBundle)
    assert actual.contents == expected.contents
    assert report == pristine and "provenance" not in report
    assert actual.contents[ArtifactMember.SOURCE] == code.encode()
    assert (
        json.loads(actual.contents[ArtifactMember.REPORT])["stdout"]
        == "  한글 stdout\n"
    )

    async def envelope(store):
        """Observe real MCP serialization via the public registration surface."""
        server = fastmcp.FastMCP("controlled-legacy-envelope")
        register_artifacts(server, store)
        async with fastmcp.Client(server) as client:
            result = await client.call_tool(
                "get_plot_artifact", {"artifact_id": identity(800).value}
            )
            assert not result.is_error
            return result.structured_content, [
                block.model_dump(mode="json") for block in result.content
            ]

    assert asyncio.run(envelope(rig.artifacts)) == asyncio.run(
        envelope(expected_store)
    )


@pytest.mark.parametrize("policy", [InputsDisabled(), ConfigurationError()])
def test_parent_only_needs_no_input_policy_or_mapping(rig, policy):
    """A live parent gets pinned with disabled/broken retention and no injected global."""
    parent = render_artifact(rig.artifacts, RenderRequest(FIGURE), lambda: NOW)
    assert isinstance(parent, StoredBundle)
    code = "assert 'dartwork_inputs' not in globals()\n" + FIGURE
    child = render_artifact(
        rig.artifacts,
        RenderRequest(code),
        lambda: NOW,
        revision=Revision(parent.manifest.artifact_id, ()),
        inputs=policy,
    )
    assert receipt(child) == {
        "schema_version": 1,
        "parent": {
            "artifact_id": parent.manifest.artifact_id.value,
            "manifest_sha256": hashlib.sha256(
                parent.contents[ArtifactMember.MANIFEST]
            ).hexdigest(),
            "source_sha256": hashlib.sha256(
                parent.contents[ArtifactMember.SOURCE]
            ).hexdigest(),
        },
        "inputs": [],
        "reproducibility": "not_claimed",
    }
    assert set(rig.storage.iterdir()) == {rig.storage / ".lock"}
    assert child.contents[ArtifactMember.SOURCE] == code.encode()


@pytest.mark.parametrize("state", ["missing", "expired", "corrupt"])
def test_parent_failure_precedes_execution(rig, state):
    """An unlive/invalid parent cannot execute code or publish even with no inputs."""
    parent = render_artifact(rig.artifacts, RenderRequest(FIGURE), lambda: NOW)
    assert isinstance(parent, StoredBundle)
    parent_id = parent.manifest.artifact_id
    at = NOW
    refusal = NotFound
    if state == "missing":
        parent_id = identity(900)
    elif state == "expired":
        at += timedelta(days=7)
        refusal = Expired
    else:
        (rig.root / "artifacts" / parent_id.value / "source.py").write_bytes(
            b"corrupt"
        )
        refusal = CorruptArtifact
    marker = rig.root / "must-not-execute"
    code = f"from pathlib import Path\nPath({str(marker)!r}).touch()\n" + FIGURE
    result = render(rig, code, specs=(), parent=parent_id, clock=lambda: at)
    assert isinstance(result, refusal), result
    assert not marker.exists()
    assert set(rig.storage.iterdir()) == {rig.storage / ".lock"}


@pytest.mark.parametrize("policy", [InputsDisabled(), ConfigurationError()])
def test_inputs_require_grant_before_execution(rig, policy):
    """Copy and Retained both fail closed; paths and basenames are not diagnostic data."""
    spec = selection(rig.source, path="private-original.csv")
    for chosen in (
        spec,
        RetainedInput("sample", identity(1), "sample", spec.sha256),
    ):
        marker = rig.root / "denied-execution"
        result = render_artifact(
            rig.artifacts,
            RenderRequest(
                f"from pathlib import Path\nPath({str(marker)!r}).touch()\n"
                + FIGURE
            ),
            lambda: NOW,
            revision=Revision(None, (chosen,)),
            inputs=policy,
        )
        assert isinstance(result, ConfigurationError), result
        assert not marker.exists()
        assert str(rig.root) not in repr(
            result
        ) and "private-original.csv" not in repr(result)


def test_paired_commit_and_postcheck(rig, monkeypatch):
    """Shared admission pins parent once; postcheck precedes new UTC clock and both commits."""
    parent = render_artifact(rig.artifacts, RenderRequest(FIGURE), lambda: NOW)
    assert isinstance(parent, StoredBundle)
    admitted = NOW + timedelta(days=6, hours=23)
    completed = NOW + timedelta(days=8)
    events, loaded = [], []
    active = {"transaction": False, "artifact": False}
    original_tx, original_stage = InputStore.transaction, ArtifactStore.staging
    original_load, original_check = ArtifactStore.load, InputTransaction.check
    original_commit, original_publish = (
        InputTransaction.commit,
        ArtifactStore.publish,
    )
    original_observe, original_settle = (
        ArtifactStore.observe_commit,
        InputTransaction.settle,
    )
    times = iter((admitted, completed))

    @contextmanager
    def transaction(self):
        """Observe the public resource contract while retaining the real transaction."""
        with original_tx(self) as tx:
            active["transaction"] = True
            try:
                yield tx
            finally:
                active["transaction"] = False

    @contextmanager
    def staging(self):
        """The complete artifact stage must be nested within transaction ownership."""
        assert active["transaction"]
        with original_stage(self) as stage:
            active["artifact"] = True
            try:
                yield stage
            finally:
                active["artifact"] = False
        events.append("stage-exited")

    def load(self, artifact_id, now):
        """The sole full parent load records admission, rather than completion time."""
        loaded.append((artifact_id, now))
        return original_load(self, artifact_id, now)

    def check(self, stage):
        """Complete the actual worker postcheck before allowing a publication clock."""
        result = original_check(self, stage)
        assert result is None
        events.append("checked")
        return result

    def clock():
        """The second sample must be strictly after the completed postcheck."""
        assert active["transaction"], (
            "admission clock sampled before serialization"
        )
        now = next(times)
        if now == completed:
            assert events == ["checked"]
        return now

    def commit(self, stage, created_at):
        """The real input commit establishes ID and instant before bundle publication."""
        assert events == ["checked"]
        assert created_at == completed
        result = original_commit(self, stage, created_at)
        assert isinstance(result, InputMetadata)
        events.append(("inputs", result))
        return result

    def publish(self, stage, source, report, now):
        """The artifact receives exactly the already committed input identity/time."""
        metadata = events[-1][1]
        assert metadata.artifact_id == stage.artifact_id
        assert metadata.created_at == now == completed
        assert metadata.expires_at == now + timedelta(days=7)
        result = original_publish(self, stage, source, report, now)
        events.append("bundle")
        return result

    def observe(self, artifact_id):
        """Observation happens only after artifact exit and within input serialization."""
        assert active == {"transaction": True, "artifact": False}
        assert events[-1] == "stage-exited"
        events.append("observed")
        return original_observe(self, artifact_id)

    def settle(self, stage, observation):
        """Settlement consumes the real read-only observation under retained ownership."""
        assert active == {"transaction": True, "artifact": False}
        assert isinstance(observation, Manifest)
        result = original_settle(self, stage, observation)
        events.append("settled")
        return result

    monkeypatch.setattr(InputStore, "transaction", transaction)
    monkeypatch.setattr(ArtifactStore, "staging", staging)
    monkeypatch.setattr(ArtifactStore, "load", load)
    monkeypatch.setattr(InputTransaction, "check", check)
    monkeypatch.setattr(InputTransaction, "commit", commit)
    monkeypatch.setattr(ArtifactStore, "publish", publish)
    monkeypatch.setattr(ArtifactStore, "observe_commit", observe)
    monkeypatch.setattr(InputTransaction, "settle", settle)
    spec = selection(rig.source)
    child = render(
        rig, specs=(spec,), parent=parent.manifest.artifact_id, clock=clock
    )
    pinned = receipt(child)["parent"]
    assert loaded == [(parent.manifest.artifact_id, admitted)]
    assert (
        pinned["manifest_sha256"]
        == hashlib.sha256(parent.contents[ArtifactMember.MANIFEST]).hexdigest()
    )
    assert (
        pinned["source_sha256"]
        == hashlib.sha256(parent.contents[ArtifactMember.SOURCE]).hexdigest()
    )
    assert child.manifest.created_at == completed
    assert events[-4:] == ["bundle", "stage-exited", "observed", "settled"]
    print(
        "paired-publication",
        [
            (e[0], e[1].to_bytes().decode()) if isinstance(e, tuple) else e
            for e in events
        ],
    )


@pytest.mark.parametrize("mode", ["unused", "reverted", "mapping"])
def test_only_bounded_copy_evidence_and_exact_source(rig, mode):
    """Unused/restored copies make no consumption claim; actual child mapping is read-only."""
    content = b"x,y\n2,20\n4,40\n"
    spec = selection(rig.source, content, path="private-original.csv")
    code = FIGURE
    if mode == "reverted":
        code = (
            "from pathlib import Path\np = Path(dartwork_inputs['sample'])\nold = p.read_bytes()\np.write_bytes(b'changed')\np.write_bytes(old)\n"
            + code
        )
    elif mode == "mapping":
        code = (
            """import csv
from pathlib import Path
from types import MappingProxyType
assert isinstance(dartwork_inputs, MappingProxyType)
try:
    dartwork_inputs['sample'] = 'forbidden'
except TypeError:
    pass
else:
    raise AssertionError('mutable mapping')
rows = list(csv.DictReader(Path(dartwork_inputs['sample']).open()))
"""
            + FIGURE
            + "ax.clear()\nax.plot([int(r['x']) for r in rows], [int(r['y']) for r in rows], linewidth=dm.lw(0))\nassert list(ax.lines[0].get_xdata()) == [2, 4]\nassert list(ax.lines[0].get_ydata()) == [20, 40]\ndm.simple_layout(fig)\n"
        )
    code = "# exact café 한글\r\n" + code + "\n# trailing spaces  \n"
    child = render(rig, code, specs=(spec,))
    expected = {
        "schema_version": 1,
        "parent": None,
        "inputs": [
            {
                "name": "sample",
                "sha256": hashlib.sha256(content).hexdigest(),
                "size_bytes": len(content),
                "retained": {
                    "artifact_id": child.manifest.artifact_id.value,
                    "name": "sample",
                },
                "selection": {"kind": "copy"},
                "evidence": "copied_and_boundary_checked",
            }
        ],
        "reproducibility": "not_claimed",
    }
    assert receipt(child) == expected
    assert child.contents[ArtifactMember.SOURCE] == code.encode()
    assert str(rig.root) not in json.dumps(
        expected
    ) and "private-original.csv" not in json.dumps(expected)
    assert isinstance(
        rig.artifacts.load(child.manifest.artifact_id, NOW), StoredBundle
    )


def test_postcheck_mutation_refuses_publication_after_real_execution(rig):
    """Code may run, but a changed copied file yields no bundle or input set."""
    spec = selection(rig.source)
    marker = rig.root / "executed"
    code = (
        f"from pathlib import Path\nPath({str(marker)!r}).touch()\nPath(dartwork_inputs['sample']).write_bytes(b'changed')\n"
        + FIGURE
    )
    result = render(rig, code, specs=(spec,))
    assert isinstance(result, InvalidRequest), result
    assert marker.exists()
    assert set(rig.storage.iterdir()) == {rig.storage / ".lock"}
    assert not list((rig.root / "artifacts").iterdir())


def test_copy_mismatch_and_retained_never_fall_back(rig):
    """Expected digest mismatch and unavailable explicit Retained stop before export."""
    spec = selection(rig.source)
    parent = render(rig, specs=(spec,))
    assert isinstance(parent, StoredBundle)
    (rig.source / spec.relative_path).write_bytes(b"new bytes")
    marker = rig.root / "no-fallback"
    code = f"from pathlib import Path\nPath({str(marker)!r}).touch()\n" + FIGURE
    assert isinstance(render(rig, code, specs=(spec,)), InvalidRequest)
    assert delete_api(rig.inputs, parent.manifest.artifact_id) == DeletedInputs(
        parent.manifest.artifact_id
    )
    selected = RetainedInput(
        "sample", parent.manifest.artifact_id, "sample", spec.sha256
    )
    assert isinstance(render(rig, code, specs=(selected,)), NotFound)
    assert not marker.exists()
    assert isinstance(
        rig.artifacts.load(parent.manifest.artifact_id, NOW), StoredBundle
    )


def test_mixed_selection_child_independent_of_parent_and_original(rig):
    """Closed selection points backward; locators, bytes and receipt belong to the child."""
    spec = selection(rig.source, b"A")
    parent = render(rig, specs=(spec,))
    assert isinstance(parent, StoredBundle)
    at = NOW + timedelta(days=6)
    fresh = selection(rig.source, b"B", name="fresh")
    prior = RetainedInput(
        "prior", parent.manifest.artifact_id, "sample", spec.sha256
    )
    code = (
        "from pathlib import Path\nassert Path(dartwork_inputs['prior']).read_bytes() == b'A'\nassert Path(dartwork_inputs['fresh']).read_bytes() == b'B'\n"
        + FIGURE
    )
    child = render(
        rig,
        code,
        specs=(prior, fresh),
        parent=parent.manifest.artifact_id,
        clock=lambda: at,
    )
    old_receipt = child.contents[ArtifactMember.REPORT]
    entries = receipt(child)["inputs"]
    assert entries[0]["selection"] == {
        "kind": "retained",
        "artifact_id": parent.manifest.artifact_id.value,
        "input_name": "sample",
    }
    assert entries[1]["selection"] == {"kind": "copy"}
    assert all(
        e["retained"]["artifact_id"] == child.manifest.artifact_id.value
        for e in entries
    )
    assert delete_api(rig.inputs, parent.manifest.artifact_id) == DeletedInputs(
        parent.manifest.artifact_id
    )
    (rig.source / fresh.relative_path).unlink()
    # Mutate the independently owned ancestor member, then cross its expiry.
    (
        rig.root / "artifacts" / parent.manifest.artifact_id.value / "source.py"
    ).write_bytes(b"damaged ancestor")
    later = NOW + timedelta(days=8)
    assert isinstance(
        rig.artifacts.load(parent.manifest.artifact_id, later), CorruptArtifact
    )
    assert rig.artifacts.load(child.manifest.artifact_id, later) == child
    again = RetainedInput(
        "sample", child.manifest.artifact_id, "prior", spec.sha256
    )
    grandchild = render(
        rig,
        "from pathlib import Path\nassert Path(dartwork_inputs['sample']).read_bytes() == b'A'\n"
        + FIGURE,
        specs=(again,),
        clock=lambda: later,
    )
    assert isinstance(grandchild, StoredBundle)
    assert delete_api(rig.inputs, child.manifest.artifact_id) == DeletedInputs(
        child.manifest.artifact_id
    )
    readback = rig.artifacts.load(child.manifest.artifact_id, later)
    assert readback.contents[ArtifactMember.REPORT] == old_receipt
    assert isinstance(
        render(rig, specs=(again,), clock=lambda: later), NotFound
    )


@pytest.mark.parametrize("state", STATES)
def test_delete_inputs_all_six_states_through_public_usecase(rig, state):
    """Deletion needs a grant and safe owned files, never valid metadata or a bundle."""
    folder, spec, _ = seed(rig.storage, rig.source, rig.inputs, state)
    original = (rig.source / spec.relative_path).read_bytes()
    assert delete_api(rig.inputs, identity()) == DeletedInputs(identity())
    assert not folder.exists()
    assert delete_api(rig.inputs, identity()) == AbsentInputs(identity())
    assert (rig.source / spec.relative_path).read_bytes() == original


@pytest.mark.parametrize("policy", [InputsDisabled(), ConfigurationError()])
def test_delete_inputs_denies_without_grant(rig, policy):
    """No source or retained file is touched when deletion lacks authorized capability."""
    folder, spec, _ = seed(rig.storage, rig.source, rig.inputs, "live")
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    assert isinstance(delete_api(policy, identity()), ConfigurationError)
    assert {p.name: p.read_bytes() for p in folder.iterdir()} == before
    assert (rig.source / spec.relative_path).exists()


def test_delete_inputs_no_success_on_failed_barrier(rig, monkeypatch):
    """The public use case passes through failed durability without inventing success."""
    folder, _, _ = seed(rig.storage, rig.source, rig.inputs, "live")

    def fault(point):
        """Refuse real marker persistence, leaving actual payload bytes intact."""
        if point == "marker_fsync":
            raise OSError("owned marker fault")

    monkeypatch.setattr(input_cleanup, "_fault", fault)
    assert isinstance(delete_api(rig.inputs, identity()), PublicationError)
    assert (folder / "000.bin").exists()


@pytest.mark.parametrize(
    "failure", ["execution", "no_figure", "export", "timeout", "cancel"]
)
def test_failed_or_cancelled_export_releases_owned_work(
    rig, monkeypatch, failure
):
    """No postcheck/publication follows rejected export; synchronous work is reaped first."""
    spec = selection(rig.source)
    marker = rig.root / "child-pid"
    code = f"import os\nfrom pathlib import Path\nPath({str(marker)!r}).write_text(str(os.getpid()))\n"
    if failure == "execution":
        code += "raise RuntimeError('owned failure')\n"
    elif failure == "no_figure":
        code += "value = 1\n"
    elif failure == "timeout":
        code += "import time\ntime.sleep(5)\n" + FIGURE
    else:
        code += FIGURE
        if failure == "export":
            code += "def fail_export(*args, **kwargs):\n    raise OSError('owned export failure')\nfig.savefig = fail_export\n"
    original_export = delivery.export_plot
    checked = []
    original_check = InputTransaction.check

    def check(self, stage):
        """Record the public barrier without replacing its real implementation."""
        checked.append(stage)
        return original_check(self, stage)

    def export(*args, **kwargs):
        """Cancel only after real synchronous export has returned/reaped its child."""
        result = original_export(*args, **kwargs)
        if failure == "cancel":
            raise asyncio.CancelledError()
        return result

    monkeypatch.setattr(delivery, "export_plot", export)
    monkeypatch.setattr(InputTransaction, "check", check)
    request = RenderRequest(
        code, timeout_seconds=2 if failure == "timeout" else 20
    )
    if failure == "cancel":
        with pytest.raises(asyncio.CancelledError):
            render_artifact(
                rig.artifacts,
                request,
                lambda: NOW,
                revision=Revision(None, (spec,)),
                inputs=rig.inputs,
            )
    else:
        result = render_artifact(
            rig.artifacts,
            request,
            lambda: NOW,
            revision=Revision(None, (spec,)),
            inputs=rig.inputs,
        )
        expected = (
            execution.ExportRejected
            if failure == "export"
            else execution.ExecutionRejected
        )
        assert isinstance(result, expected), result
        if failure == "timeout":
            assert result.report["status"] == "timeout"
    assert marker.exists(), "real child did not reach its marker"
    pid = int(marker.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)
    assert not checked
    assert set(rig.storage.iterdir()) == {rig.storage / ".lock"}
    assert not list((rig.root / "artifacts").iterdir())
    # A real subsequent admission proves released transaction/stage capacity.
    monkeypatch.setattr(delivery, "export_plot", original_export)
    assert isinstance(render(rig, specs=(spec,)), StoredBundle)
    print("export-failure", failure, "reaped-pid", pid)


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
def test_failed_input_commit_never_publishes_bundle(rig, monkeypatch, point):
    """Every input publication barrier can fail; proven artifact miss permits rollback."""
    spec = selection(rig.source)
    touched = []

    def fault(label):
        """Raise at the existing owned input adapter before its actual barrier."""
        if label == point:
            touched.append(label)
            raise OSError("owned input publication fault")

    with monkeypatch.context() as patch:
        patch.setattr(input_cleanup, "_fault", fault)
        result = render(rig, specs=(spec,))
    assert isinstance(result, PublicationError), result
    assert touched == [point]
    assert set(rig.storage.iterdir()) == {rig.storage / ".lock"}
    assert not list((rig.root / "artifacts").iterdir())
    assert isinstance(render(rig, specs=(spec,)), StoredBundle)
    print("input-barrier", point, "rolled-back")


@pytest.mark.parametrize("barrier", ["rename", "set_fsync", "root_fsync"])
@pytest.mark.parametrize("cleanup_fails", [False, True])
def test_artifact_barrier_failure_settles_only_after_exit(
    rig, monkeypatch, barrier, cleanup_fails
):
    """Real rename/fsync failure rolls back proven misses and preserves ambiguous commits."""
    spec = selection(rig.source)
    original_rename, original_sync = disk.os.rename, disk.os.fsync
    original_cleanup = disk._remove_owned
    failed, stages, observations = [], [], []
    original_stage = ArtifactStore.staging
    original_observe = ArtifactStore.observe_commit
    stage_live = []

    @contextmanager
    def staging(self):
        """Record actual stage lifetime, including its cleanup and descriptor close."""
        with original_stage(self) as stage:
            stages.append(stage.artifact_id)
            stage_live.append(True)
            try:
                yield stage
            finally:
                stage_live.pop()

    def rename(src, dst, **kwargs):
        """Fail only the artifact owner's final manifest rename, never input rename."""
        if barrier == "rename" and src == ".manifest.pending":
            failed.append("rename")
            raise OSError("owned artifact rename fault")
        return original_rename(src, dst, **kwargs)

    def fsync(fd):
        """Select the actual artifact directory/root inode at its durability syscall."""
        info = os.fstat(fd)
        root = rig.root / "artifacts"
        target = root if barrier == "root_fsync" else root / stages[-1].value
        if (
            barrier != "rename"
            and target.exists()
            and (info.st_dev, info.st_ino)
            == (target.stat().st_dev, target.stat().st_ino)
        ):
            failed.append(barrier)
            raise OSError("owned artifact fsync fault")
        return original_sync(fd)

    def cleanup(*args, **kwargs):
        """A failed actual cleanup must preserve visible commit ambiguity."""
        if cleanup_fails:
            raise OSError("owned artifact cleanup fault")
        return original_cleanup(*args, **kwargs)

    def observe(self, artifact_id):
        """Read the genuine public manifest evidence only after stage closure."""
        assert not stage_live
        result = original_observe(self, artifact_id)
        observations.append(result)
        return result

    with monkeypatch.context() as patch:
        patch.setattr(ArtifactStore, "staging", staging)
        patch.setattr(ArtifactStore, "observe_commit", observe)
        patch.setattr(disk.os, "rename", rename)
        patch.setattr(disk.os, "fsync", fsync)
        patch.setattr(disk, "_remove_owned", cleanup)
        result = render(rig, specs=(spec,))
    assert isinstance(result, PublicationError), result
    assert failed and len(stages) == 1 and len(observations) == 1
    preserved = cleanup_fails and barrier != "rename"
    assert isinstance(observations[0], Manifest if preserved else NotFound)
    folder = rig.storage / stages[0].value
    assert folder.exists() == preserved
    if preserved:
        assert (folder / "000.bin").read_bytes() == (
            rig.source / spec.relative_path
        ).read_bytes()
        metadata = (folder / "inputs.json").read_bytes()
        assert stages[0].value.encode() in metadata
    assert isinstance(render(rig, specs=(spec,)), StoredBundle)
    print(
        "artifact-barrier",
        barrier,
        "cleanup-fails",
        cleanup_fails,
        "observed",
        type(observations[0]).__name__,
        "preserved",
        preserved,
    )


@pytest.mark.parametrize(
    "observation", ["matching", "corrupt", "unobservable", "raises"]
)
def test_failed_input_commit_stays_failed_despite_ambiguous_observation(
    rig, monkeypatch, observation
):
    """A failed input-root fsync is never Ready; uncertainty preserves its counted bytes."""
    spec = selection(rig.source)
    original_commit = InputTransaction.commit
    original_stage = ArtifactStore.staging
    metadata, child_ids = [], []
    observed = []

    @contextmanager
    def staging(self):
        """Keep a real artifact stage while retaining only its public identity."""
        with original_stage(self) as stage:
            child_ids.append(stage.artifact_id)
            yield stage

    def commit(self, stage, at):
        """Observe metadata just before the actual root barrier fails."""
        result = original_commit(self, stage, at)
        assert isinstance(result, PublicationError)
        metadata.append(
            InputMetadata(
                child_ids[-1], at, at + timedelta(days=7), stage.files
            )
        )
        return result

    def fault(point):
        """Raise after real input rename, leaving a committed independent set."""
        if point == "input_root_fsync":
            raise OSError("owned post-rename failure")

    def observe(self, artifact_id):
        """Model the permitted public observer's matching or ambiguous outcomes."""
        observed.append(artifact_id)
        if observation == "raises":
            raise OSError("owned observer failure")
        if observation == "matching":
            # Use a real bundle to construct the valid public observation value;
            # this is observer uncertainty, not an actual second publication.
            from test_input_store import manifest

            return manifest(metadata[-1])
        return (
            CorruptArtifact()
            if observation == "corrupt"
            else PublicationError()
        )

    with monkeypatch.context() as patch:
        patch.setattr(InputTransaction, "commit", commit)
        patch.setattr(ArtifactStore, "staging", staging)
        patch.setattr(ArtifactStore, "observe_commit", observe)
        patch.setattr(input_cleanup, "_fault", fault)
        result = render(rig, specs=(spec,))
    assert isinstance(result, PublicationError), result
    assert observed == child_ids and len(child_ids) == 1
    folder = rig.storage / child_ids[0].value
    assert (folder / "000.bin").read_bytes() == (
        rig.source / spec.relative_path
    ).read_bytes()
    assert not list((rig.root / "artifacts").iterdir())
    # Explicit authorized delete can remove ambiguity; it does not fabricate Ready.
    assert delete_api(rig.inputs, child_ids[0]) == DeletedInputs(child_ids[0])
    print("ambiguous-input-commit", observation, "preserved")


@pytest.mark.parametrize(
    "phase", ["export", "input_commit", "bundle_commit", "stage_exit"]
)
def test_cancellation_and_exception_settlement_preserves_committed_bytes(
    rig, monkeypatch, phase
):
    """Synchronous cancellation after commit still observes/settles outside artifact stage."""
    spec = selection(rig.source)
    original_export = delivery.export_plot
    original_commit, original_publish = (
        InputTransaction.commit,
        ArtifactStore.publish,
    )
    original_stage, original_observe = (
        ArtifactStore.staging,
        ArtifactStore.observe_commit,
    )
    ids, observations, live = [], [], []

    @contextmanager
    def staging(self):
        """Inject an exit error after the actual resource context has finished."""
        with original_stage(self) as stage:
            ids.append(stage.artifact_id)
            live.append(True)
            try:
                yield stage
            finally:
                live.pop()
        if phase == "stage_exit":
            raise OSError("owned stage exit failure")

    def export(*args, **kwargs):
        """Real synchronous export has reaped its child before cancellation injection."""
        result = original_export(*args, **kwargs)
        if phase == "export":
            raise asyncio.CancelledError()
        return result

    def commit(self, stage, at):
        """Cancel after the real input rename/root barrier has succeeded."""
        result = original_commit(self, stage, at)
        if phase == "input_commit":
            assert isinstance(result, InputMetadata)
            raise asyncio.CancelledError()
        return result

    def publish(self, *args, **kwargs):
        """Cancel only after the actual bundle's final durable marker exists."""
        result = original_publish(self, *args, **kwargs)
        if phase == "bundle_commit":
            assert isinstance(result, StoredBundle)
            raise asyncio.CancelledError()
        return result

    def observe(self, artifact_id):
        """No cancellation path may observe the still-active artifact stage."""
        assert not live
        result = original_observe(self, artifact_id)
        observations.append(result)
        return result

    with monkeypatch.context() as patch:
        patch.setattr(ArtifactStore, "staging", staging)
        patch.setattr(delivery, "export_plot", export)
        patch.setattr(InputTransaction, "commit", commit)
        patch.setattr(ArtifactStore, "publish", publish)
        patch.setattr(ArtifactStore, "observe_commit", observe)
        if phase == "stage_exit":
            assert isinstance(render(rig, specs=(spec,)), PublicationError)
        else:
            with pytest.raises(asyncio.CancelledError):
                render(rig, specs=(spec,))
    assert len(observations) == 1
    preserved = phase in {"bundle_commit", "stage_exit"}
    assert isinstance(observations[0], Manifest if preserved else NotFound)
    assert (rig.storage / ids[0].value).exists() == preserved
    assert isinstance(
        rig.artifacts.load(ids[0], NOW), StoredBundle if preserved else NotFound
    )
    assert isinstance(render(rig, specs=(spec,)), StoredBundle)
    print(
        "settled-cancellation-or-exception",
        phase,
        type(observations[0]).__name__,
    )


def test_parent_bytes_pinned_before_child_can_change_ancestor(rig):
    """Live admission digests survive real ancestor corruption during execution."""
    parent = render_artifact(rig.artifacts, RenderRequest(FIGURE), lambda: NOW)
    assert isinstance(parent, StoredBundle)
    source = (
        rig.root / "artifacts" / parent.manifest.artifact_id.value / "source.py"
    )
    code = (
        f"from pathlib import Path\nPath({str(source)!r}).write_bytes(b'changed during child')\n"
        + FIGURE
    )
    child = render(
        rig,
        code,
        specs=(selection(rig.source),),
        parent=parent.manifest.artifact_id,
    )
    pinned = receipt(child)["parent"]
    assert (
        pinned["source_sha256"]
        == hashlib.sha256(parent.contents[ArtifactMember.SOURCE]).hexdigest()
    )
    assert (
        pinned["manifest_sha256"]
        == hashlib.sha256(parent.contents[ArtifactMember.MANIFEST]).hexdigest()
    )
    assert isinstance(
        rig.artifacts.load(parent.manifest.artifact_id, NOW), CorruptArtifact
    )
    assert rig.artifacts.load(child.manifest.artifact_id, NOW) == child


@pytest.mark.parametrize(
    "barrier",
    [
        "postcheck",
        "settle",
        "settle_raises",
        "observe_miss",
        "observe_mismatch",
    ],
)
def test_no_ready_on_postcheck_or_settlement_refusal(rig, monkeypatch, barrier):
    """Even successful export/commits cannot override a failed final evidence barrier."""
    from dataclasses import replace

    spec = selection(rig.source)
    checked, observed, clock_reads = [], [], []
    original_check = InputTransaction.check
    original_settle = InputTransaction.settle
    original_observe = ArtifactStore.observe_commit

    def check(self, stage):
        """Finish the genuine postcheck before injecting an operational refusal."""
        checked.append(stage)
        result = original_check(self, stage)
        assert result is None
        return PublicationError() if barrier == "postcheck" else result

    def observe(self, artifact_id):
        """Missing/mismatching public evidence cannot authorize Ready."""
        result = original_observe(self, artifact_id)
        observed.append((artifact_id, result))
        if barrier == "observe_miss":
            return NotFound()
        if barrier == "observe_mismatch":
            assert isinstance(result, Manifest)
            return replace(
                result,
                created_at=NOW + timedelta(hours=1),
                expires_at=NOW + timedelta(days=7, hours=1),
            )
        return result

    def settle(self, stage, observation):
        """Exercise the real settlement before an owned adapter failure is reported."""
        result = original_settle(self, stage, observation)
        if barrier == "settle":
            return PublicationError()
        if barrier == "settle_raises":
            raise OSError("owned settlement I/O fault")
        return result

    def clock():
        """Completion time must not be sampled after a rejected postcheck."""
        clock_reads.append(NOW)
        return NOW

    monkeypatch.setattr(InputTransaction, "check", check)
    monkeypatch.setattr(InputTransaction, "settle", settle)
    monkeypatch.setattr(ArtifactStore, "observe_commit", observe)
    result = render(rig, specs=(spec,), clock=clock)
    assert isinstance(result, PublicationError), result
    assert len(checked) == 1 and len(observed) == 1
    assert len(clock_reads) == (1 if barrier == "postcheck" else 2)
    preserved = barrier in {"settle", "settle_raises", "observe_mismatch"}
    assert (rig.storage / observed[0][0].value).exists() == preserved
    print("final-barrier", barrier, "copies-preserved", preserved)
