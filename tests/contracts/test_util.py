"""dartwork_mpl.util is a deprecated compatibility module (0.8).

util once held these functions; they now live in the slices that own them
(ADR 0005). During the warning window util re-exports them unchanged, so
``from dartwork_mpl.util import X`` still works but warns on every access.
Removal is no earlier than 0.10 (docs/development/api-stability.md). The
behaviour tests live with each owner.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
import warnings
from pathlib import Path

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


def _run(code: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "import warnings\nwarnings.simplefilter('always')\n" + code,
        ],
        capture_output=True,
        text=True,
    )


def _lines(result: subprocess.CompletedProcess[str]) -> list[str]:
    assert result.returncode == 0, result.stderr
    return [
        ln for ln in result.stderr.splitlines() if "DeprecationWarning" in ln
    ]


def test_util_lists_exactly_the_compatibility_names() -> None:
    from dartwork_mpl import util

    assert set(util.__all__) == set(_OWNERS)
    assert set(_OWNERS) <= set(dir(util))


@pytest.mark.parametrize("name", sorted(_OWNERS))
def test_util_name_is_the_owners_object_and_warns(name: str) -> None:
    from dartwork_mpl import util

    owner = importlib.import_module(_OWNERS[name])
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        value = getattr(util, name)
    assert value is getattr(owner, name)
    assert [w.category for w in caught] == [DeprecationWarning]
    assert caught[0].filename == __file__
    text = str(caught[0].message)
    assert f"util.{name}" in text and _OWNERS[name] in text
    assert "deprecated in 0.8" in text and "0.10 or later" in text


def test_unknown_name_raises_attribute_error() -> None:
    from dartwork_mpl import util

    with pytest.raises(AttributeError):
        util.not_a_name  # noqa: B018


def test_importing_the_module_alone_does_not_warn() -> None:
    for stmt in ("import dartwork_mpl.util", "from dartwork_mpl import util"):
        assert _lines(_run(stmt)) == [], stmt


def test_from_import_warns_at_the_user_line_each_time() -> None:
    code = (
        "from dartwork_mpl.util import save_formats\n"
        "from dartwork_mpl.util import save_formats as again\n"
        "import dartwork_mpl.io as io\n"
        "assert save_formats is io.save_formats is again\n"
    )
    lines = _lines(_run(code))
    assert len(lines) == 2
    assert lines[0].startswith("<string>:3:")
    assert lines[1].startswith("<string>:4:")


def test_attribute_access_warns_at_the_user_line_each_time() -> None:
    code = (
        "import dartwork_mpl, dartwork_mpl.util\n"
        "a = dartwork_mpl.util.fs\n"
        "b = dartwork_mpl.util.fs\n"
        "assert a is b is dartwork_mpl.fs\n"
    )
    lines = _lines(_run(code))
    assert len(lines) == 2
    assert lines[0].startswith("<string>:4:") and lines[1].startswith(
        "<string>:5:"
    )


def test_other_module_importing_util_warns_at_its_own_line(
    tmp_path: Path,
) -> None:
    (tmp_path / "consumer.py").write_text(
        "from dartwork_mpl.util import mix_colors\n", encoding="utf-8"
    )
    code = (
        f"import sys; sys.path.insert(0, {str(tmp_path)!r})\n"
        "import consumer\n"
        "import dartwork_mpl as dm\n"
        "assert consumer.mix_colors is dm.mix_colors\n"
    )
    lines = _lines(_run(code))
    assert len(lines) == 1
    assert "consumer.py:1:" in lines[0]


def test_error_filter_turns_access_into_an_error() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-W",
            "error::DeprecationWarning",
            "-c",
            "import dartwork_mpl.util\nimport dartwork_mpl.util as u\nu.fs",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "DeprecationWarning" in result.stderr


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
