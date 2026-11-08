"""Patch-target rows for the MCP artifact store (see ``test_patch_targets``).

The artifact tests (``test_artifact_store.py``, ``test_input_commit_observer.py``,
``test_input_delivery.py``) patch these names as ``store.<name>``. The
filesystem primitives among them live in ``_store_fs``; the patch still
reaches the store methods below, which read them from store's globals.

These rows need FastMCP, so the module skips as a whole without it. That
keeps the all-extras JUnit gate honest: ``scripts/check_integration_junit.py``
requires this module to contribute a passed case, rejects a module whose cases
all skip, and rejects an import skip, so the rows cannot silently drop out of
the full run. A namespace check only; see ``test_patch_targets`` for its limit.
"""

from __future__ import annotations

import pytest

from tests.contracts.test_patch_targets import assert_caller_reads_from

pytest.importorskip("fastmcp")

_STORE = "dartwork_mpl.mcp.artifacts.store"

# (module the test patches, patched name, module of the caller, caller)
PATCH_TARGETS = [
    (_STORE, "_write_file", _STORE, "ArtifactStore.publish"),
    (_STORE, "_root_ancestry", _STORE, "ArtifactStore.check_input_roots"),
    (_STORE, "_remove_owned", _STORE, "ArtifactStore.load"),
    (_STORE, "_remove_owned", _STORE, "ArtifactStore.publish"),
    (_STORE, "_remove_owned", _STORE, "ArtifactStore._staging"),
    (_STORE, "_cleanup_expired", _STORE, "ArtifactStore.load"),
    (_STORE, "_cleanup_expired", _STORE, "ArtifactStore.publish"),
    (_STORE, "uuid4", _STORE, "ArtifactStore._staging"),
]


@pytest.mark.parametrize(
    ("module", "name", "caller_module", "caller"),
    PATCH_TARGETS,
    ids=[f"{row[1]}@{row[3]}" for row in PATCH_TARGETS],
)
def test_store_caller_reads_the_patched_name_from_store(
    module: str, name: str, caller_module: str, caller: str
) -> None:
    """``caller`` looks ``name`` up in the store module the tests patch."""
    assert_caller_reads_from(module, name, caller_module, caller)
