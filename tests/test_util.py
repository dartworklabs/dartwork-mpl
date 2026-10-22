"""dartwork_mpl.util stays a compatibility module: each name it lists is its owner's object.

util once held these functions; they now live in the slices that own them
(ADR 0005) and util re-exports them unchanged, so ``from dartwork_mpl.util
import X`` keeps working. The behaviour tests live with each owner.
"""

from __future__ import annotations

import importlib

import pytest

from dartwork_mpl import util

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
    "mix_colors": "dartwork_mpl._colors.blend",
    "prompt_path": "dartwork_mpl.prompt",
    "pseudo_alpha": "dartwork_mpl._colors.blend",
    "save_and_show": "dartwork_mpl.io",
    "save_formats": "dartwork_mpl.io",
    "set_decimal": "dartwork_mpl.formatting",
    "show": "dartwork_mpl.io",
    "simple_layout": "dartwork_mpl.layout",
}


def test_util_lists_exactly_the_compatibility_names() -> None:
    """util's surface is the historical name set, no more and no less."""
    assert set(util.__all__) == set(_OWNERS)


@pytest.mark.parametrize("name", sorted(_OWNERS))
def test_util_name_is_the_owners_object(name: str) -> None:
    """A util name is the owning slice's function itself, not a copy."""
    owner = importlib.import_module(_OWNERS[name])
    assert getattr(util, name) is getattr(owner, name)
