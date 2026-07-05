"""Numeric asset-count claims in docs must equal the mechanical count (G4).

"16 curated colormaps" survived in the flagship colormap page while 56
shipped; the font pages predate the #370 corpus expansion. Each entry
pairs a claim-regex with the callable that computes the true number —
and the regex MUST match, so rewording a claim can't silently disable
its check.
"""

from __future__ import annotations

import ast
import json
import re
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_ASSET = _REPO / "src" / "dartwork_mpl" / "asset"


def _n_v5_cmaps() -> int:
    # The v5 catalog (the default colormap surface) — 42 generated maps.
    # The legacy asset/cmap/*.txt bundle is a separate backward-compat set
    # and is no longer what the docs count.
    from dartwork_mpl.colors._generated import CMAPS_256

    return len(CMAPS_256)


def _n_font_files() -> int:
    return len(
        [
            p
            for p in (_ASSET / "font").iterdir()
            if p.suffix.lower() in {".ttf", ".otf"}
        ]
    )


def _n_font_families() -> int:
    # Family = filename prefix before the first "-" (the grouping both
    # font-gallery generators use). Pretendard and Noto Sans CJK ship as
    # .otf, so the ".ttf"/".otf" filter must match — see
    # test_fonts_generator_parity.
    return len(
        {
            p.stem.split("-")[0]
            for p in (_ASSET / "font").iterdir()
            if p.suffix.lower() in {".ttf", ".otf"}
        }
    )


def _n_presets() -> int:
    presets = json.loads(
        (_ASSET / "mplstyle" / "presets.json").read_text(encoding="utf-8")
    )
    return len(presets)


def _n_curated_palettes() -> int:
    from dartwork_mpl.colors._generated import PALETTE

    return len(PALETTE)


def _n_basic_templates() -> int:
    return len(list((_ASSET / "prompt" / "05-templates").glob("*.py")))


@lru_cache(maxsize=1)
def _mcp_decorator_counts() -> dict[str, int]:
    counts = {"tool": 0, "resource": 0, "resource_template": 0, "prompt": 0}
    for path in (_REPO / "src" / "dartwork_mpl" / "mcp").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for dec in node.decorator_list:
                target = dec.func if isinstance(dec, ast.Call) else dec
                if not (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "mcp"
                ):
                    continue
                if target.attr == "tool":
                    counts["tool"] += 1
                elif target.attr == "prompt":
                    counts["prompt"] += 1
                elif target.attr == "resource":
                    uri = ""
                    if (
                        isinstance(dec, ast.Call)
                        and dec.args
                        and isinstance(dec.args[0], ast.Constant)
                        and isinstance(dec.args[0].value, str)
                    ):
                        uri = dec.args[0].value
                    key = "resource_template" if "{" in uri else "resource"
                    counts[key] += 1
    return counts


def _n_mcp_tools() -> int:
    return _mcp_decorator_counts()["tool"]


def _n_mcp_resources() -> int:
    return _mcp_decorator_counts()["resource"]


def _n_mcp_resource_templates() -> int:
    return _mcp_decorator_counts()["resource_template"]


def _n_mcp_prompts() -> int:
    return _mcp_decorator_counts()["prompt"]


def _n_aspect_tokens() -> int:
    from dartwork_mpl.units import ASPECT_TOKENS

    return len(ASPECT_TOKENS)


def _n_prompt_guides() -> int:
    import dartwork_mpl as dm

    return len(dm.list_prompts())


_NUMBER_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


def _claim_to_int(value: str) -> int:
    if value.lower() in _NUMBER_WORDS:
        return _NUMBER_WORDS[value.lower()]
    return int(value)


_CLAIMS: list[tuple[str, str, Callable[[], int]]] = [
    (
        "docs/color_system/colormaps.md",
        r"ships \*\*(\d+) colormaps\*\*",
        _n_v5_cmaps,
    ),
    (
        "docs/color_system/colormaps.md",
        r"Explore all (\d+) built-in colormaps",
        _n_v5_cmaps,
    ),
    (
        "docs/design_system/index.md",
        r"(\d+) perceptually-designed colormaps",
        _n_v5_cmaps,
    ),
    (
        "docs/fonts/index.md",
        r"bundles \*\*(\d+) text font files across \d+ families\*\*",
        _n_font_files,
    ),
    (
        "docs/fonts/index.md",
        r"text font files across \*?\*?(\d+) families",
        _n_font_families,
    ),
    (
        "docs/fonts/families.md",
        r"bundles (\d+) professional font families",
        _n_font_families,
    ),
    ("docs/fonts/families.md", r"with a total of (\d+) font", _n_font_files),
    (
        "docs/fonts/utilities.md",
        r"all (\d+) bundled fonts are automatically",
        _n_font_files,
    ),
    (
        "docs/design_system/index.md",
        r"(\d+) publication-grade fonts from \d+ families",
        _n_font_files,
    ),
    (
        "docs/design_system/index.md",
        r"publication-grade fonts from (\d+) families",
        _n_font_families,
    ),
    (
        "docs/usage_guide/styles.md",
        r"giving \*\*(\d+) presets\*\* total",
        _n_presets,
    ),
    (
        "docs/color_system/categorical-palettes.md",
        r"curated (\d+)-palette system",
        _n_curated_palettes,
    ),
    (
        "docs/color_system/colors.md",
        r"\*\*(\d+)-palette categorical system\*\*",
        _n_curated_palettes,
    ),
    ("llms.txt", r"(\d+) ready-to-use scripts", _n_basic_templates),
    ("CLAUDE.md", r"(\d+) ready-to-use plot templates", _n_basic_templates),
    ("AGENTS.md", r"(\d+) ready-to-use plot templates", _n_basic_templates),
    ("CLAUDE.md", r"(\d+) tools", _n_mcp_tools),
    ("AGENTS.md", r"(\d+) tools", _n_mcp_tools),
    ("README.md", r"(\d+) tools", _n_mcp_tools),
    ("CLAUDE.md", r"(\d+) resources \+", _n_mcp_resources),
    ("AGENTS.md", r"(\d+) resources \+", _n_mcp_resources),
    ("README.md", r"(\d+) resources \+", _n_mcp_resources),
    ("CLAUDE.md", r"(\d+) resource templates", _n_mcp_resource_templates),
    ("AGENTS.md", r"(\d+) resource templates", _n_mcp_resource_templates),
    ("README.md", r"(\d+) resource templates", _n_mcp_resource_templates),
    ("CLAUDE.md", r"(\d+) prompts", _n_mcp_prompts),
    ("AGENTS.md", r"(\d+) prompts", _n_mcp_prompts),
    ("README.md", r"(\d+) prompts", _n_mcp_prompts),
    ("CLAUDE.md", r"(ten|\d+) aspect tokens", _n_aspect_tokens),
    ("AGENTS.md", r"(ten|\d+) aspect tokens", _n_aspect_tokens),
    ("README.md", r"(ten|\d+) aspect tokens", _n_aspect_tokens),
    ("llms.txt", r"(ten|\d+) aspect tokens", _n_aspect_tokens),
    ("docs/ai/index.md", r"Prompt corpus\*\* \((\d+) guides", _n_prompt_guides),
]


@pytest.mark.parametrize(
    ("relpath", "claim_re", "counter"),
    _CLAIMS,
    ids=[f"{c[0]}~{i}" for i, c in enumerate(_CLAIMS)],
)
def test_count_claim_matches_reality(
    relpath: str, claim_re: str, counter: Callable[[], int]
) -> None:
    text = (_REPO / relpath).read_text(encoding="utf-8")
    m = re.search(claim_re, text)
    assert m, (
        f"{relpath}: claim regex {claim_re!r} not found — if the prose "
        f"was reworded, update the regex so the check stays live"
    )
    actual = counter()
    claimed = _claim_to_int(m.group(1))
    assert claimed == actual, (
        f"{relpath}: claims {m.group(1)}, mechanical count is {actual}"
    )
