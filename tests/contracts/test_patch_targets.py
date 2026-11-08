"""Pin the modules tests patch: a patched name must live where its caller reads it.

``monkeypatch.setattr(module, name, fake)`` only takes effect when the function
that calls ``name`` looks it up in ``module``'s namespace. After a split, a
helper imported into the caller's module (``from ._x import name``) is
patched in ``_x`` and the caller still holds the old binding: the test then
passes (or fails) for the wrong reason. Each row names the module a test
patches, the patched name and the function that calls it, and asserts the
caller is defined in that very module, so its global lookups go there.

This is a namespace check, not proof that the caller calls the name: a caller
that reaches the helper another way (``other_module.name(...)``) still passes.
The behaviour tests that patch these names catch that. A caller may be a
dotted attribute path (a method); decorators are unwrapped to the defining
function. Rows whose modules need FastMCP live in ``test_patch_targets_mcp``.
"""

from __future__ import annotations

import importlib
import inspect
from functools import reduce

import pytest

# (module the test patches, patched name, module of the caller, caller)
PATCH_TARGETS = [
    (
        "dartwork_mpl.annotation._legend_entries",
        "_entry_signatures",
        "dartwork_mpl.annotation._legend_entries",
        "_rebuildable",
    ),
    (
        "dartwork_mpl.layout._reservations",
        "_reservation_edge",
        "dartwork_mpl.layout._reservations",
        "_figure_artist_reservations",
    ),
    (
        # formatting/tests/test_twin_spines.py turns the spine step off to
        # re-enact 0.7 (install_07); simple_layout must still read it here.
        "dartwork_mpl.layout._simple_layout",
        "_show_twin_spines",
        "dartwork_mpl.layout._simple_layout",
        "simple_layout",
    ),
]


def assert_caller_reads_from(
    module: str, name: str, caller_module: str, caller: str
) -> None:
    """Assert ``caller`` is defined in ``module`` and sees ``module.name``."""
    target = importlib.import_module(module)
    function = inspect.unwrap(
        reduce(
            getattr, caller.split("."), importlib.import_module(caller_module)
        )
    )

    assert function.__globals__ is vars(target)
    assert function.__globals__[name] is getattr(target, name)


@pytest.mark.parametrize(
    ("module", "name", "caller_module", "caller"),
    PATCH_TARGETS,
    ids=[f"{row[0]}.{row[1]}" for row in PATCH_TARGETS],
)
def test_caller_reads_the_patched_name_from_the_patched_module(
    module: str, name: str, caller_module: str, caller: str
) -> None:
    """``caller`` looks ``name`` up in the module the test patches."""
    assert_caller_reads_from(module, name, caller_module, caller)
