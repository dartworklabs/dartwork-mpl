"""Shared fixtures for the retained-input tests: real granted roots, selections and committed sets.

These helpers build state through the genuine policy, store and publication surfaces; they assert on the
way so a broken surface fails inside the test that needed it. Imported by ``test_input_store``,
``test_input_recovery`` and ``test_input_delivery``; not collected (no ``test_`` prefix).
"""

import hashlib
import importlib
import json
from datetime import datetime, timedelta, timezone

from dartwork_mpl.mcp.artifacts import (
    ArtifactId,
    ConfigurationError,
    CopyInput,
    InputMetadata,
    Manifest,
    NotFound,
    configure_store,
)
from dartwork_mpl.mcp.artifacts.input_access import InputGrant, authorize_inputs
from dartwork_mpl.mcp.artifacts.policy import (
    DATA_MEMBERS,
    FileEntry,
    ValidationSummary,
)

NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)


def api():
    """Missing production surfaces fail as assertions during the required RED."""
    package = importlib.import_module("dartwork_mpl.mcp.artifacts")
    assert hasattr(package, "InputStore"), "input store surface is missing"
    return package


def identity(n=1):
    """Generate deterministic distinct valid UUID4 identities for disk fixtures."""
    return ArtifactId(f"{n:012x}40008000000000000000")


def fixture(root):
    """Authorize disposable canonical roots through the genuine policy boundary."""
    storage, source = root / "storage", root / "source"
    storage.mkdir(mode=0o700)
    source.mkdir(mode=0o700)
    policy = root / "policy.json"
    policy.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "storage_dir": str(storage),
                "copy_roots": {"data": str(source)},
            }
        )
    )
    policy.chmod(0o600)
    artifacts = configure_store(str(root / "artifacts"))
    assert not isinstance(artifacts, ConfigurationError)
    grant = authorize_inputs(str(policy), artifacts.check_input_roots)
    assert isinstance(grant, InputGrant), grant
    return storage, source, grant, artifacts, policy


def selection(source, content=b"a,b\n1,2\n", name="sample", path="data.csv"):
    """Write actual input bytes and declare their exact expected identity."""
    (source / path).write_bytes(content)
    return CopyInput(name, "data", path, hashlib.sha256(content).hexdigest())


def manifest(metadata):
    """Build a valid commit observation without interpreting artifact storage."""
    return Manifest(
        metadata.artifact_id,
        metadata.created_at,
        metadata.expires_at,
        tuple(
            FileEntry(member, 0, hashlib.sha256(b"").hexdigest())
            for member in DATA_MEMBERS
        ),
        ValidationSummary("ok", True, ()),
    )


def publish(store, artifact_id, specs, at=NOW, observe=lambda _: NotFound()):
    """Exercise real copy, postcheck, input commit and explicit paired settlement."""
    with store.transaction() as tx:
        stage = tx.prepare(artifact_id, specs, at, observe)
        assert isinstance(stage, api().InputStage), stage
        assert tx.check(stage) is None
        metadata = tx.commit(stage, at)
        assert isinstance(metadata, InputMetadata), metadata
        assert tx.settle(stage, manifest(metadata)) is None
        return metadata


STATES = ("live", "expired", "revoked", "corrupt", "pending", "unknown")


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
