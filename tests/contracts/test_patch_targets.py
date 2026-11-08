"""Pin the modules tests patch: a patched name must be the one its caller reads.

``monkeypatch.setattr(module, name, fake)`` only takes effect when the function
that calls ``name`` looks it up in ``module``'s namespace. After a split, a
helper imported into the caller's module (``from ._x import name``) is
patched in ``_x`` and the caller still holds the old binding: the test then
passes (or fails) for the wrong reason. Each row names the module a test
patches, the patched name and the function that calls it, and asserts the
caller reads its globals from that very module. A caller may be a dotted
attribute path (a method); decorators are unwrapped to the defining function.
"""

from __future__ import annotations

import importlib
import inspect
from functools import reduce

import pytest

_STORE = "dartwork_mpl.mcp.artifacts.store"

# (module the test patches, patched name, module of the caller, caller)
PATCH_TARGETS = [
    (
        "dartwork_mpl.annotation._legend_entries",
        "_entry_signatures",
        "dartwork_mpl.annotation._legend_entries",
        "_rebuildable",
    ),
    (
        "dartwork_mpl.layout",
        "_reservation_edge",
        "dartwork_mpl.layout",
        "_figure_artist_reservations",
    ),
    (
        # formatting/tests/test_twin_spines.py turns the spine step off to
        # re-enact 0.7 (install_07); simple_layout must still read it here.
        "dartwork_mpl.layout",
        "_show_twin_spines",
        "dartwork_mpl.layout",
        "simple_layout",
    ),
    # The artifact tests (test_artifact_store.py, test_input_commit_observer.py,
    # test_input_delivery.py) patch these names as ``store.<name>``. The
    # filesystem primitives among them live in ``_store_fs``; the patch still
    # reaches the store methods below, which read them from store's globals.
    (_STORE, "_write_file", _STORE, "ArtifactStore.publish"),
    (_STORE, "_root_ancestry", _STORE, "ArtifactStore.check_input_roots"),
    (_STORE, "_remove_owned", _STORE, "ArtifactStore.load"),
    (_STORE, "_remove_owned", _STORE, "ArtifactStore.publish"),
    (_STORE, "_remove_owned", _STORE, "ArtifactStore._staging"),
    (_STORE, "_cleanup_expired", _STORE, "ArtifactStore.load"),
    (_STORE, "_cleanup_expired", _STORE, "ArtifactStore.publish"),
    (_STORE, "uuid4", _STORE, "ArtifactStore._staging"),
]


def _row_id(row: tuple[str, str, str, str]) -> str:
    """Keep the historical ``module.name`` id; name the caller when one name has several."""
    shared = sum(other[:2] == row[:2] for other in PATCH_TARGETS) > 1
    return f"{row[0]}.{row[1]}" + (f"@{row[3]}" if shared else "")


@pytest.mark.parametrize(
    ("module", "name", "caller_module", "caller"),
    PATCH_TARGETS,
    ids=[_row_id(row) for row in PATCH_TARGETS],
)
def test_caller_reads_the_patched_name_from_the_patched_module(
    module: str, name: str, caller_module: str, caller: str
) -> None:
    """Patching ``module.name`` changes what ``caller`` calls."""
    if module.startswith("dartwork_mpl.mcp"):
        pytest.importorskip("fastmcp")
    target = importlib.import_module(module)
    function = inspect.unwrap(
        reduce(
            getattr, caller.split("."), importlib.import_module(caller_module)
        )
    )

    assert function.__globals__ is vars(target)
    assert function.__globals__[name] is getattr(target, name)
