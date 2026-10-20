"""Actual shipped stdio restarts pin input identity, recovery and client guidance.

Only fixture-owned private roots are authorized. Optional test evidence is copied
outside those disposable roots; it is neither product configuration nor a grant.
"""

import asyncio
import base64
import hashlib
import io
import json
import os
import random
import shutil
import subprocess
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from importlib.metadata import version
from pathlib import Path
from types import SimpleNamespace

import matplotlib.image as mpimg
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from dartwork_mpl.mcp.artifacts import (
    ArtifactMember,
    ArtifactStore,
    CopyInput,
    InputGrant,
    InputStore,
    KnownProvenance,
    RenderRequest,
    RetainedInput,
    Revision,
    StoredBundle,
    authorize_inputs,
    classify_provenance,
    configure_store,
    render_artifact,
)

CSV_A = b"x,y,include\n2,20,1\n1,,1\n3,30,0\n4,40,1\n"
CSV_B = b"x,y,include\n2,200,1\n1,,1\n3,300,0\n4,400,1\n"
NAME = "measurements"
BASENAME = "operator-private-original.csv"
MEMBERS = {member.value for member in ArtifactMember}
MANIFEST_KEYS = {
    "schema_version",
    "artifact_id",
    "created_at",
    "expires_at",
    "files",
    "validation",
}
SOURCE = """# Resource recovery witness: preserved custom baseline source.
import csv
import json
import os
import matplotlib.pyplot as plt
import dartwork_mpl as dm
dm.style.use("scientific")
fig, ax = plt.subplots(figsize=dm.figsize("8cm", "square"))
for name, path in dartwork_inputs.items():
    with open(path, newline="") as stream:
        rows = list(csv.DictReader(stream))
    rows = [row for row in rows if row["y"] != ""]
    rows = [row for row in rows if row["include"] != "0"]
    ax.plot([float(row["x"]) for row in rows],
            [float(row["y"]) for row in rows],
            label=name, linewidth=dm.lw(0), color="C0")
ax.set(xlim=(0, 5), ylim=(0, 450), xlabel="x", ylabel="y")
dm.simple_layout(fig)
print(json.dumps({"artists": [
    {"name": line.get_label(), "x": line.get_xdata().tolist(),
     "y": line.get_ydata().tolist(), "color": line.get_color()}
    for line in ax.lines], "pid": os.getpid(), "server_pid": os.getppid(),
    "cwd": os.getcwd()}))
"""


def digest(data):
    """Hash actual fixture/resource bytes without substituting identity evidence."""
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    """Persist raw wire/observation evidence with real newlines on all outcomes."""
    path.write_text(json.dumps(value, indent=2, default=str) + "\n")


@pytest.fixture
def journey(owned_input_root, request):
    """Own canonical roots, a stable copy grant and disposable process cwd files."""
    root = owned_input_root
    copy_root, storage = root / "copy-root", root / "retained"
    for path in (copy_root, storage):
        path.mkdir(mode=0o700)
    workspace = copy_root / "original-workspace"
    workspace.mkdir(mode=0o700)
    csv = workspace / BASENAME
    csv.write_bytes(CSV_A)
    policy = root / "policy.json"
    write_json(
        policy,
        {
            "schema_version": 1,
            "storage_dir": str(storage),
            "copy_roots": {"data": str(copy_root)},
        },
    )
    policy.chmod(0o600)
    evidence_root = Path(
        os.environ.get("DARTWORK_MPL_TASK7_EVIDENCE", root / "evidence")
    )
    evidence = evidence_root / request.node.name
    evidence.mkdir(parents=True, exist_ok=True)
    write_json(
        evidence / "versions.json",
        {
            "python": sys.version,
            "executable": sys.executable,
            **{
                name: version(name) for name in ("fastmcp", "mcp", "matplotlib")
            },
        },
    )
    return SimpleNamespace(
        root=root,
        copy_root=copy_root,
        storage=storage,
        workspace=workspace,
        csv=csv,
        policy=policy,
        artifacts=root / "artifacts",
        evidence=evidence,
        starts=0,
        pids=[],
    )


def copy_spec(journey, data=CSV_A, name=NAME):
    """Declare the explicit original descendant, never an inferred file lookup."""
    return {
        "kind": "copy",
        "name": name,
        "root_id": "data",
        "relative_path": f"original-workspace/{BASENAME}",
        "sha256": digest(data),
    }


def retained_spec(entry, name=None):
    """Use only a report's public child locator/digest for the next request."""
    return {
        "kind": "retained",
        "name": name or entry["name"],
        "artifact_id": entry["retained"]["artifact_id"],
        "input_name": entry["retained"]["name"],
        "sha256": entry["sha256"],
    }


def process_alive(pid):
    """Check a real owned process has disappeared after the SDK context exits."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


@asynccontextmanager
async def stdio(journey, *, artifact_root=None, home=None):
    """Start the shipped module with this interpreter and a fresh cwd/client.

    Capture stderr, actual server PID and clean SDK teardown; the SDK does not
    expose the subprocess return code through its public context interface.
    """
    journey.starts += 1
    label = f"process-{journey.starts}"
    cwd = journey.root / label
    cwd.mkdir(mode=0o700)
    env = {
        **os.environ,
        "DARTWORK_MPL_INPUT_POLICY": str(journey.policy),
        "PYTHONPATH": os.pathsep.join(str(p) for p in sys.path),
        "MPLBACKEND": "Agg",
    }
    if artifact_root == "default":
        env.pop("DARTWORK_MPL_ARTIFACT_DIR", None)
    else:
        env["DARTWORK_MPL_ARTIFACT_DIR"] = str(
            artifact_root or journey.artifacts
        )
    if home is not None:
        env["HOME"] = str(home)
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "dartwork_mpl.mcp.server"],
        cwd=str(cwd),
        env=env,
    )
    info = {
        "command": [params.command, *params.args],
        "cwd": str(cwd),
        "sdk_context_closed": False,
    }
    pid = None
    try:
        with (journey.evidence / f"{label}.stderr").open("w+") as errlog:
            async with stdio_client(params, errlog=errlog) as (reader, writer):
                async with ClientSession(reader, writer) as client:
                    await client.initialize()
                    rows = subprocess.check_output(
                        ["ps", "-ax", "-o", "pid=,ppid=,command="], text=True
                    )
                    matches = [
                        int(parts[0])
                        for row in rows.splitlines()
                        if len(parts := row.split(None, 2)) == 3
                        and parts[1] == str(os.getpid())
                        and "-m dartwork_mpl.mcp.server" in parts[2]
                    ]
                    assert len(matches) == 1, matches
                    pid = matches[0]
                    assert pid not in journey.pids
                    journey.pids.append(pid)
                    info["server_pid"] = pid
                    yield client
            info["sdk_context_closed"] = True
            assert not process_alive(pid), pid
            errlog.seek(0)
            stderr = errlog.read()
            info["known_authlib_deprecation"] = (
                "AuthlibDeprecationWarning" in stderr
            )
            # Existing Task6 deliberate-disconnect noise is not expected in
            # these normal sessions; leave any new traceback visible as failure.
            info["unexpected_diagnostics"] = [
                line
                for line in stderr.splitlines()
                if (
                    "Traceback (most recent call last)" in line
                    or "ClosedResourceError" in line
                    or "ResourceWarning" in line
                )
            ]
            assert not info["unexpected_diagnostics"], stderr
    finally:
        info["process_absent"] = pid is not None and not process_alive(pid)
        write_json(journey.evidence / f"{label}.json", info)


async def call(client, journey, label, tool, arguments, error=None):
    """Record SDK camelCase framing and require exact native error/ready arms."""
    result = await client.call_tool(tool, arguments)
    write_json(
        journey.evidence / f"{label}.wire.json", result.model_dump(mode="json")
    )
    value = json.loads(result.content[-1].text)
    assert result.structuredContent == value
    assert result.isError == (error is not None), value
    if error:
        assert value["delivery_status"] == "error"
        assert value["error_code"] == error
        assert "artifact_id" not in value and "files" not in value
        assert [block.type for block in result.content] == ["text"]
    return value


async def render(client, journey, label, code, specs, parent=None, error=None):
    """Execute actual supplied source; there is no client-side fallback path."""
    revision = {"schema_version": 1, "inputs": specs}
    if parent:
        revision["parent_artifact_id"] = parent
    return await call(
        client,
        journey,
        label,
        "render_plot",
        {"code": code, "revision": revision},
        error,
    )


async def recover(client, journey, label, artifact_id):
    """Read/hash all five resource members without re-executing source."""
    value = await call(
        client,
        journey,
        label,
        "get_plot_artifact",
        {"artifact_id": artifact_id},
    )
    assert value["delivery_status"] == "ready"
    bodies = {}
    folder = journey.evidence / label
    folder.mkdir(exist_ok=True)
    for entry in value["files"]:
        resource = await client.read_resource(entry["uri"])
        write_json(
            folder / f"{entry['name']}.resource.json",
            resource.model_dump(mode="json"),
        )
        assert len(resource.contents) == 1
        block = resource.contents[0]
        data = (
            base64.b64decode(block.blob)
            if hasattr(block, "blob")
            else block.text.encode()
        )
        assert block.mimeType == entry["mime_type"]
        assert len(data) == entry["size_bytes"]
        if "sha256" in entry:
            assert digest(data) == entry["sha256"]
        bodies[entry["name"]] = data
        (folder / entry["name"]).write_bytes(data)
    assert set(bodies) == MEMBERS
    manifest = json.loads(bodies["manifest.json"])
    assert set(manifest) == MANIFEST_KEYS
    assert datetime.fromisoformat(
        manifest["expires_at"]
    ) - datetime.fromisoformat(
        manifest["created_at"].replace("Z", "+00:00")
    ) == timedelta(days=7)
    write_json(
        folder / "hashes.json",
        {name: digest(data) for name, data in bodies.items()},
    )
    return bodies


def artists(bodies, expected, *, cwd=None, color="C0"):
    """Compare literal expected values to native artist arrays emitted by execution.

    Do not derive the oracle by re-filtering the CSV with the plotting algorithm.
    """
    report = json.loads(bodies["report.json"])
    observed = json.loads(report["stdout"])
    assert [
        (line["name"], line["x"], line["y"]) for line in observed["artists"]
    ] == expected
    assert all(line["color"] == color for line in observed["artists"])
    assert not process_alive(observed["pid"])
    if cwd:
        assert observed["cwd"] == str(cwd)
    return report["provenance"], observed


def receipt(bodies, expected):
    """Check closed typed receipt, exact selections and current child locators."""
    provenance = json.loads(bodies["report.json"])["provenance"]
    assert isinstance(
        classify_provenance({"provenance": provenance}), KnownProvenance
    )
    artifact_id = json.loads(bodies["manifest.json"])["artifact_id"]
    assert len(provenance["inputs"]) == len(expected)
    for entry, (name, data, selection) in zip(
        provenance["inputs"], expected, strict=True
    ):
        assert entry == {
            "name": name,
            "sha256": digest(data),
            "size_bytes": len(data),
            "retained": {"artifact_id": artifact_id, "name": name},
            "selection": selection,
            "evidence": "copied_and_boundary_checked",
        }
    assert provenance["reproducibility"] == "not_claimed"
    return provenance


def private_snapshot(storage):
    """Observe owned bytes without interpreting the input-store metadata layout."""
    return {
        str(path.relative_to(storage)): path.read_bytes()
        for path in storage.rglob("*")
        if path.is_file()
    }


def test_deleted_csv_revision_survives_new_stdio_process(journey):
    """Deleted originals recover from resources; real style revision preserves parent."""

    async def workflow():
        """Use distinct process, cwd, client and actual resource-derived source."""
        async with stdio(journey) as client:
            parent = await render(
                client,
                journey,
                "parent",
                SOURCE.replace(
                    "dm.simple_layout(fig)",
                    'ax.set_title("Recovered source witness")\ndm.simple_layout(fig)',
                ),
                [copy_spec(journey)],
            )
            before = await recover(
                client, journey, "parent-before", parent["artifact_id"]
            )
            provenance, first = artists(
                before,
                [(NAME, [2, 4], [20, 40])],
                cwd=journey.root / "process-1",
            )
            receipt(before, [(NAME, CSV_A, {"kind": "copy"})])
            assert first["server_pid"] == journey.pids[-1]
        shutil.rmtree(journey.workspace)
        assert journey.copy_root.is_dir() and not journey.csv.exists()
        async with stdio(journey) as client:
            recovered = await recover(
                client, journey, "parent-recovered", parent["artifact_id"]
            )
            assert recovered == before
            recovered_source = recovered["source.py"].decode()
            code = recovered_source.replace('color="C0"', 'color="C1"')
            assert code != recovered_source
            child = await render(
                client,
                journey,
                "child",
                code,
                [retained_spec(provenance["inputs"][0])],
                parent["artifact_id"],
            )
            after = await recover(
                client, journey, "child", child["artifact_id"]
            )
            _, second = artists(
                after,
                [(NAME, [2, 4], [20, 40])],
                cwd=journey.root / "process-2",
                color="C1",
            )
            assert (
                second["server_pid"] == journey.pids[-1] != first["server_pid"]
            )
            assert after["source.py"] == recovered["source.py"].replace(
                b'color="C0"', b'color="C1"'
            )
            selected = {
                "kind": "retained",
                "artifact_id": parent["artifact_id"],
                "input_name": NAME,
            }
            child_receipt = receipt(after, [(NAME, CSV_A, selected)])
            assert child_receipt["parent"] == {
                "artifact_id": parent["artifact_id"],
                "manifest_sha256": digest(before["manifest.json"]),
                "source_sha256": digest(before["source.py"]),
            }
            parent_after = await recover(
                client, journey, "parent-after", parent["artifact_id"]
            )
            assert parent_after == before
            baseline, revised = (
                mpimg.imread(io.BytesIO(body["plot.png"]))
                for body in (before, after)
            )
            assert (
                baseline.shape == revised.shape and (baseline != revised).any()
            )
            write_json(
                journey.evidence / "parent-preservation.json",
                {
                    name: {
                        "before": digest(data),
                        "after": digest(parent_after[name]),
                    }
                    for name, data in before.items()
                },
            )

    asyncio.run(workflow())


def test_changed_csv_selection_and_restart_receipts(journey):
    """Stale Copy never falls back; explicit B, retained A and mixed choices survive."""

    async def workflow():
        """Observe literal B/A artists and reconnect through child-owned locators."""
        async with stdio(journey) as client:
            parent = await render(
                client, journey, "parent", SOURCE, [copy_spec(journey)]
            )
            before = await recover(
                client, journey, "parent", parent["artifact_id"]
            )
            parent_receipt, _ = artists(before, [(NAME, [2, 4], [20, 40])])
            journey.csv.write_bytes(CSV_B)
            manifests = set(journey.artifacts.glob("*/manifest.json"))
            retained_before = private_snapshot(journey.storage)
            marker = journey.root / "must-not-execute"
            stale_source = (
                SOURCE
                + f"\nfrom pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n"
            )
            stale = await render(
                client,
                journey,
                "stale-copy",
                stale_source,
                [copy_spec(journey)],
                error="invalid_request",
            )
            assert not marker.exists()
            assert set(journey.artifacts.glob("*/manifest.json")) == manifests
            assert private_snapshot(journey.storage) == retained_before
            copied = await render(
                client,
                journey,
                "explicit-B",
                SOURCE,
                [copy_spec(journey, CSV_B)],
                parent["artifact_id"],
            )
            copied_body = await recover(
                client, journey, "explicit-B", copied["artifact_id"]
            )
            artists(copied_body, [(NAME, [2, 4], [200, 400])])
            receipt(copied_body, [(NAME, CSV_B, {"kind": "copy"})])
            retained = await render(
                client,
                journey,
                "deliberate-A",
                SOURCE,
                [retained_spec(parent_receipt["inputs"][0])],
                parent["artifact_id"],
            )
            retained_body = await recover(
                client, journey, "deliberate-A", retained["artifact_id"]
            )
            artists(retained_body, [(NAME, [2, 4], [20, 40])])
            mixed = await render(
                client,
                journey,
                "mixed",
                SOURCE,
                [
                    copy_spec(journey, CSV_B, "current"),
                    retained_spec(parent_receipt["inputs"][0], "snapshot"),
                ],
                parent["artifact_id"],
            )
            mixed_body = await recover(
                client, journey, "mixed-before", mixed["artifact_id"]
            )
            artists(
                mixed_body,
                [
                    ("current", [2, 4], [200, 400]),
                    ("snapshot", [2, 4], [20, 40]),
                ],
            )
            mixed_receipt = receipt(
                mixed_body,
                [
                    ("current", CSV_B, {"kind": "copy"}),
                    (
                        "snapshot",
                        CSV_A,
                        {
                            "kind": "retained",
                            "artifact_id": parent["artifact_id"],
                            "input_name": NAME,
                        },
                    ),
                ],
            )
            # F5 applies to NEW evidence/errors/locators. Exact source/stdout are
            # intentionally separate and can retain caller paths (the cwd here).
            for value in (stale, mixed_receipt, mixed["files"]):
                encoded = json.dumps(value)
                for secret in (
                    str(journey.root),
                    str(journey.policy),
                    str(journey.copy_root),
                    str(journey.storage),
                    BASENAME,
                ):
                    assert secret not in encoded
            assert (
                str(journey.root)
                in json.loads(mixed_body["report.json"])["stdout"]
            )
            assert (
                await recover(
                    client, journey, "parent-after", parent["artifact_id"]
                )
                == before
            )
        async with stdio(journey) as client:
            restored = await recover(
                client, journey, "mixed-reconnected", mixed["artifact_id"]
            )
            assert restored == mixed_body
            parsed = json.loads(restored["report.json"])["provenance"]
            next_child = await render(
                client,
                journey,
                "next-child",
                restored["source.py"].decode(),
                [retained_spec(entry) for entry in parsed["inputs"]],
            )
            next_body = await recover(
                client, journey, "next-child", next_child["artifact_id"]
            )
            artists(
                next_body,
                [
                    ("current", [2, 4], [200, 400]),
                    ("snapshot", [2, 4], [20, 40]),
                ],
            )
            receipt(
                next_body,
                [
                    (
                        name,
                        data,
                        {
                            "kind": "retained",
                            "artifact_id": mixed["artifact_id"],
                            "input_name": name,
                        },
                    )
                    for name, data in (("current", CSV_B), ("snapshot", CSV_A))
                ],
            )

    asyncio.run(workflow())


def direct_pair(journey, parent_at, child_at):
    """Publish real parent/child through delivery's injected clock, then close pins."""
    store = configure_store(str(journey.artifacts))
    assert isinstance(store, ArtifactStore)
    grant = authorize_inputs(str(journey.policy), store.check_input_roots)
    assert isinstance(grant, InputGrant)
    inputs = InputStore.open(grant, parent_at)
    assert isinstance(inputs, InputStore)
    try:
        parent = render_artifact(
            store,
            RenderRequest(SOURCE),
            lambda: parent_at,
            revision=Revision(
                None,
                (
                    CopyInput(
                        NAME,
                        "data",
                        f"original-workspace/{BASENAME}",
                        digest(CSV_A),
                    ),
                ),
            ),
            inputs=inputs,
        )
        assert isinstance(parent, StoredBundle), parent
        parent_id = parent.manifest.artifact_id
        instants = iter((child_at - timedelta(seconds=3), child_at))
        child = render_artifact(
            store,
            RenderRequest(SOURCE),
            lambda: next(instants),
            revision=Revision(
                parent_id,
                (RetainedInput(NAME, parent_id, NAME, digest(CSV_A)),),
            ),
            inputs=inputs,
        )
        assert isinstance(child, StoredBundle), child
        for label, bundle in (
            ("direct-parent", parent),
            ("direct-child", child),
        ):
            folder = journey.evidence / label
            folder.mkdir()
            for member, data in bundle.contents.items():
                (folder / member.value).write_bytes(data)
        assert child.manifest.created_at == child_at
        assert child.manifest.expires_at == child_at + timedelta(days=7)
        assert parent.manifest.created_at == parent_at
        assert parent.manifest.expires_at == parent_at + timedelta(days=7)
        child_bodies = {
            member.value: data for member, data in child.contents.items()
        }
        artists(child_bodies, [(NAME, [2, 4], [20, 40])])
        provenance = receipt(
            child_bodies,
            [
                (
                    NAME,
                    CSV_A,
                    {
                        "kind": "retained",
                        "artifact_id": parent_id.value,
                        "input_name": NAME,
                    },
                )
            ],
        )
        assert set(provenance) == {
            "schema_version",
            "parent",
            "inputs",
            "reproducibility",
        }
        assert set(child_bodies) == MEMBERS
        write_json(
            journey.evidence / "clock.json",
            {
                "parent_publication": parent_at,
                "child_admission": child_at - timedelta(seconds=3),
                "child_publication": child_at,
                "child_expiry": child.manifest.expires_at,
                "sha256": digest(CSV_A),
            },
        )
        return parent_id.value, child.manifest.artifact_id.value, child_bodies
    finally:
        inputs.close()
        grant.close()


@pytest.mark.parametrize("damage", ["deleted", "expired", "corrupt"])
def test_child_reuse_survives_parent_damage_and_actual_restart(journey, damage):
    """Independent child bytes/inputs survive ancestor lookup failure after restart."""
    now = datetime.now(timezone.utc)
    parent_at = now - timedelta(days=8 if damage == "expired" else 2)
    child_at = now - timedelta(days=2 if damage == "expired" else 1)
    parent_id, child_id, child_bodies = direct_pair(
        journey, parent_at, child_at
    )

    async def workflow():
        """Delete through MCP first; corrupt only owned ancestor fixture bytes."""
        if damage == "deleted":
            async with stdio(journey) as client:
                parent_bodies = await recover(
                    client, journey, "parent-before-delete", parent_id
                )
                entry = json.loads(parent_bodies["report.json"])["provenance"][
                    "inputs"
                ][0]
                deleted = await call(
                    client,
                    journey,
                    "delete-inputs",
                    "delete_plot_inputs",
                    {"artifact_id": parent_id},
                )
                assert deleted == {
                    "schema_version": 1,
                    "artifact_id": parent_id,
                    "state": "deleted",
                }
                assert (
                    await recover(
                        client, journey, "historical-after-delete", parent_id
                    )
                    == parent_bodies
                )
                await render(
                    client,
                    journey,
                    "denied-deleted-input",
                    SOURCE,
                    [retained_spec(entry)],
                    error="not_found",
                )
            shutil.rmtree(journey.artifacts / parent_id)
        elif damage == "corrupt":
            source = journey.artifacts / parent_id / "source.py"
            source.write_bytes(source.read_bytes() + b"#")
        shutil.rmtree(journey.workspace)
        async with stdio(journey) as client:
            await call(
                client,
                journey,
                "ancestor-lookup",
                "get_plot_artifact",
                {"artifact_id": parent_id},
                error={
                    "deleted": "not_found",
                    "expired": "expired",
                    "corrupt": "corrupt",
                }[damage],
            )
            recovered = await recover(
                client, journey, "independent-child", child_id
            )
            assert recovered == child_bodies
            entry = json.loads(recovered["report.json"])["provenance"][
                "inputs"
            ][0]
            next_child = await render(
                client,
                journey,
                "independent-reuse",
                recovered["source.py"].decode(),
                [retained_spec(entry)],
            )
            next_bodies = await recover(
                client, journey, "independent-reuse", next_child["artifact_id"]
            )
            artists(next_bodies, [(NAME, [2, 4], [20, 40])])
            receipt(
                next_bodies,
                [
                    (
                        NAME,
                        CSV_A,
                        {
                            "kind": "retained",
                            "artifact_id": child_id,
                            "input_name": NAME,
                        },
                    )
                ],
            )
            assert (
                await recover(client, journey, "child-after-reuse", child_id)
                == child_bodies
            )

    asyncio.run(workflow())


def test_restart_root_home_missing_and_restoration_preserve_committed_bytes(
    journey,
):
    """Unavailable artifact roots/HOME preserve all committed inputs for restoration."""
    now = datetime.now(timezone.utc)
    _, child_id, child_bodies = direct_pair(
        journey, now - timedelta(days=2), now - timedelta(days=1)
    )
    before = private_snapshot(journey.storage)
    original = journey.artifacts
    hidden = original.rename(journey.root / "unmounted-artifacts")

    async def workflow():
        """Start three truly fresh runtimes, then restore the original before expiry."""
        try:
            for index, root in enumerate(
                (original, journey.root / "different-missing-root", "default")
            ):
                home = journey.root / f"other-home-{index}"
                home.mkdir(mode=0o700)
                async with stdio(
                    journey, artifact_root=root, home=home
                ) as client:
                    assert private_snapshot(journey.storage) == before
                    unavailable_root = (
                        (home / ".cache" / "dartwork-mpl" / "artifacts")
                        if root == "default"
                        else root
                    )
                    assert not unavailable_root.exists()
                    await call(
                        client,
                        journey,
                        f"root-{index}-lookup",
                        "get_plot_artifact",
                        {"artifact_id": child_id},
                        error="not_found",
                    )
                    await render(
                        client,
                        journey,
                        f"root-{index}-retained-denied",
                        SOURCE,
                        [
                            retained_spec(
                                json.loads(child_bodies["report.json"])[
                                    "provenance"
                                ]["inputs"][0]
                            )
                        ],
                        error="not_found",
                    )
                    assert private_snapshot(journey.storage) == before
                assert private_snapshot(journey.storage) == before
                # Legacy get/staging can create an empty artifact root. Only
                # the input commit observer/startup promises no root creation.
                assert not list(unavailable_root.rglob("manifest.json"))
        finally:
            if original.exists():
                original.rmdir()
            hidden.rename(original)
        async with stdio(journey) as client:
            recovered = await recover(
                client, journey, "restored-child", child_id
            )
            assert recovered == child_bodies
            entry = json.loads(recovered["report.json"])["provenance"][
                "inputs"
            ][0]
            result = await render(
                client,
                journey,
                "restored-reuse",
                recovered["source.py"].decode(),
                [retained_spec(entry)],
            )
            artists(
                await recover(
                    client, journey, "restored-reuse", result["artifact_id"]
                ),
                [(NAME, [2, 4], [20, 40])],
            )
            after = private_snapshot(journey.storage)
            assert all(after[name] == value for name, value in before.items())
            write_json(
                journey.evidence / "committed-preservation.json",
                {
                    name: {
                        "before": digest(value),
                        "after": digest(after[name]),
                    }
                    for name, value in before.items()
                },
            )

    asyncio.run(workflow())


def compare_receipts(parent, child):
    """Deterministic CLIENT example: compare exact logical names and byte hashes.

    Typed historical receipts permit comparison, not current availability or
    automatic selection. No basename/row-count/source matching or LLM claim.
    """
    if not isinstance(parent, KnownProvenance) or not isinstance(
        child, KnownProvenance
    ):
        return "unavailable", "ask_for_input_selection"
    prior = {entry.name: entry.sha256 for entry in parent.inputs}
    current = {entry.name: entry.sha256 for entry in child.inputs}
    if not prior or prior.keys() != current.keys():
        return "unavailable", "ask_for_input_selection"
    if prior != current:
        return "different", "confirm_changed_bytes"
    return "same", "snapshot_origin_unverified"


SELECTION_CASES = json.loads(
    (
        Path(__file__).parent / "fixtures" / "input_selection_cases.json"
    ).read_text()
)


@pytest.mark.parametrize("case", SELECTION_CASES, ids=lambda case: case["name"])
def test_client_guidance_compares_typed_historical_receipts(case):
    """Literal guide cases require actual typed comparison, never expected-label echo."""
    actual = compare_receipts(
        classify_provenance(case["parent_report"]),
        classify_provenance(case["child_report"]),
    )
    assert actual == (case["expected_comparison"], case["expected_guidance"])


def test_client_comparison_is_invariant_to_order_but_not_identity():
    """Seeded permutations preserve exact-name comparison, never guess renames."""
    rng = random.Random(20261021)
    original = SELECTION_CASES[-1]["parent_report"]
    parent = classify_provenance(original)
    for _ in range(32):
        shuffled = json.loads(json.dumps(original))
        rng.shuffle(shuffled["provenance"]["inputs"])
        assert compare_receipts(parent, classify_provenance(shuffled)) == (
            "same",
            "snapshot_origin_unverified",
        )
        index = rng.randrange(2)
        shuffled["provenance"]["inputs"][index]["sha256"] = rng.randbytes(
            32
        ).hex()
        assert compare_receipts(parent, classify_provenance(shuffled)) == (
            "different",
            "confirm_changed_bytes",
        )
        item = shuffled["provenance"]["inputs"][index]
        item["name"] = item["retained"]["name"] = "renamed"
        assert compare_receipts(parent, classify_provenance(shuffled)) == (
            "unavailable",
            "ask_for_input_selection",
        )
