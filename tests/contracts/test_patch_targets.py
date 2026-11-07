"""Pin the modules tests patch: a patched name must be the one its caller reads.

``monkeypatch.setattr(module, name, fake)`` only takes effect when the function
that calls ``name`` looks it up in ``module``'s namespace. After a split, a
helper imported into the caller's module (``from ._x import name``) is
patched in ``_x`` and the caller still holds the old binding: the test then
passes (or fails) for the wrong reason. Each row names the module a test
patches, the patched name and the function that calls it, and asserts the
caller reads its globals from that very module.
"""

from __future__ import annotations

import importlib

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


@pytest.mark.parametrize(
    ("module", "name", "caller_module", "caller"),
    PATCH_TARGETS,
    ids=[f"{row[0]}.{row[1]}" for row in PATCH_TARGETS],
)
def test_caller_reads_the_patched_name_from_the_patched_module(
    module: str, name: str, caller_module: str, caller: str
) -> None:
    """Patching ``module.name`` changes what ``caller`` calls."""
    target = importlib.import_module(module)
    function = getattr(importlib.import_module(caller_module), caller)

    assert function.__globals__ is vars(target)
    assert function.__globals__[name] is getattr(target, name)
