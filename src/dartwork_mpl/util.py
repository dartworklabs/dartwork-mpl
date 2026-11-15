"""Deprecated: names that used to live in ``dartwork_mpl.util``.

Each function now lives in the slice that owns it (ADR 0005). Until removal
(0.10 or later, docs/development/api-stability.md) this module holds no
names of its own: a module ``__getattr__`` (PEP 562) imports the owner's
object on every access and warns with a ``DeprecationWarning`` pointing at
the accessing line, so ``from dartwork_mpl.util import X`` and
``dartwork_mpl.util.X`` warn each time and return the owner's own object
(``dartwork_mpl.util.X is <owner>.X``). Importing the module alone does not
warn. Import from the owner instead; the table is in docs/migration.md.
tests/contracts/test_util.py pins the identity and the warning.
"""

from __future__ import annotations

import importlib
import warnings
from typing import Any

_OWNERS = {
    "arrow_axis": "dartwork_mpl.annotation",
    "fs": "dartwork_mpl.scale",
    "fw": "dartwork_mpl.scale",
    "get_bounding_box": "dartwork_mpl.layout",
    "label_axes": "dartwork_mpl.annotation",
    "lw": "dartwork_mpl.scale",
    "make_offset": "dartwork_mpl.annotation",
    "mix_colors": "dartwork_mpl",
    "pseudo_alpha": "dartwork_mpl",
    "save_and_show": "dartwork_mpl.io",
    "save_formats": "dartwork_mpl.io",
    "set_decimal": "dartwork_mpl.formatting",
    "show": "dartwork_mpl.io",
    "simple_layout": "dartwork_mpl.layout",
}


# Names bound nowhere in this module: __getattr__ supplies them.
__all__ = [  # noqa: F822
    "arrow_axis",
    "fs",
    "fw",
    "get_bounding_box",
    "label_axes",
    "lw",
    "make_offset",
    "mix_colors",
    "pseudo_alpha",
    "save_and_show",
    "save_formats",
    "set_decimal",
    "show",
    "simple_layout",
]


def __getattr__(name: str) -> Any:
    owner = _OWNERS.get(name)
    if owner is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    warnings.warn(
        f"dartwork_mpl.util.{name} is deprecated in 0.7.1 and may be removed "
        f"in 0.10 or later; use `from {owner} import {name}`.",
        DeprecationWarning,
        stacklevel=2,
    )
    return getattr(importlib.import_module(owner), name)


def __dir__() -> list[str]:
    return sorted({*globals(), *__all__})
