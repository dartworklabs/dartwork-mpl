"""dartwork_mpl.util is a deprecated compatibility module (warned in 0.8).

util once held these functions; they now live in the slices that own them
(ADR 0005). During the warning window util re-exports them unchanged, so
``from dartwork_mpl.util import X`` still works but warns once on import.
Removal is no earlier than 0.10 (docs/development/api-stability.md). The
behaviour tests live with each owner.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
import textwrap
import warnings
from types import ModuleType

import pytest

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


def _fresh_import() -> tuple[ModuleType, list[warnings.WarningMessage]]:
    """Import dartwork_mpl.util as if for the first time; return warnings."""
    import dartwork_mpl

    sys.modules.pop("dartwork_mpl.util", None)
    if hasattr(dartwork_mpl, "util"):
        delattr(dartwork_mpl, "util")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        module = importlib.import_module("dartwork_mpl.util")
    return module, [w for w in caught if w.category is DeprecationWarning]


def test_util_lists_exactly_the_compatibility_names() -> None:
    """util's surface is the historical name set, no more and no less."""
    util, _ = _fresh_import()
    assert set(util.__all__) == set(_OWNERS)


@pytest.mark.parametrize("name", sorted(_OWNERS))
def test_util_name_is_the_owners_object(name: str) -> None:
    """A util name is the owning slice's function itself, not a copy."""
    util, _ = _fresh_import()
    owner = importlib.import_module(_OWNERS[name])
    assert getattr(util, name) is getattr(owner, name)


def test_importing_util_warns_exactly_once_naming_the_owners() -> None:
    _, caught = _fresh_import()
    assert len(caught) == 1
    text = str(caught[0].message)
    assert "dartwork_mpl.util" in text
    assert "0.10" in text
    for owner in set(_OWNERS.values()):
        assert owner in text


def test_warning_points_at_the_importing_user_code() -> None:
    """stacklevel reports the user's import line, not importlib or util."""
    code = textwrap.dedent(
        """
        import warnings
        warnings.simplefilter("always")
        from dartwork_mpl.util import save_formats
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    lines = [
        ln for ln in result.stderr.splitlines() if "DeprecationWarning" in ln
    ]
    assert len(lines) == 1
    assert lines[0].startswith("<string>:4:")


def test_from_import_and_plain_import_each_warn_once() -> None:
    for stmt in (
        "import dartwork_mpl.util",
        "from dartwork_mpl.util import fs",
    ):
        code = (
            "import warnings\nwarnings.simplefilter('always')\n" + stmt + "\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stderr.count("DeprecationWarning") == 1, stmt


def test_package_import_alone_does_not_warn() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-W",
            "error::DeprecationWarning:dartwork_mpl",
            "-c",
            "import dartwork_mpl as dm; dm.style.use('scientific')",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
