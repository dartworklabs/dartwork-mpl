"""Deprecated: names that used to live in ``dartwork_mpl.util``.

Each function now lives in the slice that owns it (ADR 0005). Until removal
(0.10 at the earliest, docs/development/api-stability.md) this module only
re-exports them unchanged, so ``from dartwork_mpl.util import X`` keeps
working and ``dartwork_mpl.util.X is <owner>.X``. Importing it warns once
with a ``DeprecationWarning`` naming each owner. Import from the owner
instead; the table is in docs/migration.md.
tests/contracts/test_util.py pins the identity and the warning.
"""

from __future__ import annotations

import warnings

from ._colors.blend import mix_colors, pseudo_alpha
from .annotation import arrow_axis, label_axes, make_offset
from .formatting import set_decimal
from .io import save_and_show, save_formats, show
from .layout import get_bounding_box, simple_layout
from .prompt import copy_prompt, get_prompt, list_prompts, prompt_path
from .scale import fs, fw, lw

__all__ = [
    "arrow_axis",
    "copy_prompt",
    "fs",
    "fw",
    "get_bounding_box",
    "get_prompt",
    "label_axes",
    "list_prompts",
    "lw",
    "make_offset",
    "mix_colors",
    "prompt_path",
    "pseudo_alpha",
    "save_and_show",
    "save_formats",
    "set_decimal",
    "show",
    "simple_layout",
]

_OWNERS = {
    "arrow_axis": "dartwork_mpl.annotation",
    "copy_prompt": "dartwork_mpl.prompt",
    "fs": "dartwork_mpl.scale",
    "fw": "dartwork_mpl.scale",
    "get_bounding_box": "dartwork_mpl.layout",
    "get_prompt": "dartwork_mpl.prompt",
    "label_axes": "dartwork_mpl.annotation",
    "list_prompts": "dartwork_mpl.prompt",
    "lw": "dartwork_mpl.scale",
    "make_offset": "dartwork_mpl.annotation",
    "mix_colors": "dartwork_mpl",
    "prompt_path": "dartwork_mpl.prompt",
    "pseudo_alpha": "dartwork_mpl",
    "save_and_show": "dartwork_mpl.io",
    "save_formats": "dartwork_mpl.io",
    "set_decimal": "dartwork_mpl.formatting",
    "show": "dartwork_mpl.io",
    "simple_layout": "dartwork_mpl.layout",
}


def _warning_text() -> str:
    by_owner: dict[str, list[str]] = {}
    for name, owner in _OWNERS.items():
        by_owner.setdefault(owner, []).append(name)
    table = "; ".join(
        f"{owner}: {', '.join(sorted(names))}"
        for owner, names in sorted(by_owner.items())
    )
    return (
        "dartwork_mpl.util is deprecated since 0.8 and will be removed no "
        "earlier than 0.10; import each name from its owner instead "
        f"({table})."
    )


# stacklevel=2 is the importing line: the warnings module skips the
# importlib frames between this module body and the user's import statement.
warnings.warn(_warning_text(), DeprecationWarning, stacklevel=2)
