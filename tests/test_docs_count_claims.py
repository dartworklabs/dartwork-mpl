"""Numeric asset-count claims in docs must equal the mechanical count (G4).

The color and font asset surfaces have split into a few user-facing
categories: colormaps, font files vs. documented file groups vs.
registered matplotlib family names. Each entry pairs a claim-regex with
the callable that computes the true number — and the regex MUST match,
so rewording a claim can't silently disable its check.
"""

from __future__ import annotations

import ast
import inspect
import json
import re
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from typing import get_args

import pytest

_REPO = Path(__file__).resolve().parents[1]
_ASSET = _REPO / "src" / "dartwork_mpl" / "asset"


@lru_cache(maxsize=1)
def _color_authority() -> dict[str, object]:
    path = _ASSET / "color" / "color_v6_ssot.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _n_chromatic_families() -> int:
    recipe = _color_authority()["recipe"]
    assert isinstance(recipe, dict)
    family_order = recipe["family_order"]
    assert isinstance(family_order, list)
    return len(family_order)


def _n_single_hue_families() -> int:
    from dartwork_mpl._colors._generated import PALETTE

    return len(PALETTE)


def _n_recipe_bookkeeping_slots() -> int:
    """Count named recipe slots, never derived values or MCP APIs."""
    recipe = _color_authority()["recipe"]
    assert isinstance(recipe, dict)
    family_order = recipe["family_order"]
    fourier = recipe["fourier"]
    constants = recipe["constants"]
    assert isinstance(family_order, list)
    assert isinstance(fourier, dict)
    assert isinstance(constants, dict)
    family_free_slots = len(family_order) * 4  # h0, dh, gamma, tp
    fourier_slots = sum(len(coefficients) for coefficients in fourier.values())
    # The v6 authority also stores the L*->tone derivation grid so the
    # migration is reproducible. It is derived policy, not one of the 107
    # named bookkeeping slots inherited from the audited v5 authority.
    constant_slots = set(constants) - {"TONE_DERIVATION_GRID"}
    return family_free_slots + fourier_slots + len(constant_slots)


def _numeric_leaves(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return 1
    if isinstance(value, list):
        return sum(_numeric_leaves(item) for item in value)
    if isinstance(value, dict):
        return sum(_numeric_leaves(item) for item in value.values())
    return 0


def _n_recipe_scalar_leaves() -> int:
    recipe = _color_authority()["recipe"]
    assert isinstance(recipe, dict)
    family_order = recipe["family_order"]
    fourier = recipe["fourier"]
    constants = recipe["constants"]
    assert isinstance(family_order, list)
    assert isinstance(fourier, dict)
    assert isinstance(constants, dict)
    family_free_inputs = len(family_order) * 4
    fourier_inputs = sum(len(values) for values in fourier.values())
    constant_leaves = sum(
        _numeric_leaves(value)
        for key, value in constants.items()
        if key != "TONE_DERIVATION_GRID"
    )
    return family_free_inputs + fourier_inputs + constant_leaves


def _n_v5_cmaps() -> int:
    # The v5 continuous colormap surface — generated maps excluding cycles.
    from dartwork_mpl._colors._generated import CMAPS_256

    return len(CMAPS_256)


def _n_qualitative_cmaps() -> int:
    from dartwork_mpl._colors._families import QUALITATIVE

    return len(QUALITATIVE)


def _n_listed_colormaps() -> int:
    import dartwork_mpl as dm

    return len(dm.list_colors())


def _n_registrations() -> int:
    from dartwork_mpl._colors._families import QUALITATIVE
    from dartwork_mpl._colors._generated import CMAPS_256

    return 2 * len(CMAPS_256) + len(QUALITATIVE)


def _n_typing_colors() -> int:
    from dartwork_mpl._colors._typing import DartworkColor

    return len(get_args(DartworkColor))


def _n_typing_colormaps() -> int:
    from dartwork_mpl._colors._typing import DartworkColormap

    return len(get_args(DartworkColormap))


def _n_font_files() -> int:
    return len(
        [
            p
            for p in (_ASSET / "font").iterdir()
            if p.suffix.lower() in {".ttf", ".otf"}
        ]
    )


def _n_font_file_groups() -> int:
    # File group = filename prefix before the first "-" (the grouping
    # both font-gallery generators use). Pretendard and Noto Sans CJK
    # ship as .otf, so the ".ttf"/".otf" filter must match — see
    # test_fonts_generator_parity.
    return len(
        {
            p.stem.split("-")[0]
            for p in (_ASSET / "font").iterdir()
            if p.suffix.lower() in {".ttf", ".otf"}
        }
    )


def _n_registered_font_families() -> int:
    from dartwork_mpl import font

    return len(font.list_registered())


def _n_presets() -> int:
    presets = json.loads(
        (_ASSET / "mplstyle" / "presets.json").read_text(encoding="utf-8")
    )
    return len(presets)


def _n_curated_palettes() -> int:
    """Hand-tuned qualitative sets on the categorical explorer rail."""
    from dartwork_mpl._colors._curated import CURATED_QUALITATIVE_ORDER

    return len(CURATED_QUALITATIVE_ORDER)


def _n_qualitative_rail_palettes() -> int:
    """Categorical explorer rail choices: curated qualitative sets + cycles."""
    from dartwork_mpl._colors._curated import CURATED_QUALITATIVE_ORDER
    from dartwork_mpl._colors._generated import CYCLES

    return len(CURATED_QUALITATIVE_ORDER) + len(CYCLES)


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
        "docs/color_system/design-rationale.md",
        r"bookkeeping total is \*\*(\d+) named slots\*\*",
        _n_recipe_bookkeeping_slots,
    ),
    (
        "docs/color_system/design-rationale.md",
        r"corresponds to \*\*(\d+) scalar numeric leaves\*\*",
        _n_recipe_scalar_leaves,
    ),
    (
        "docs/color_system/design-rationale.md",
        r"(\d+) chromatic families × four free",  # noqa: RUF001
        _n_chromatic_families,
    ),
    (
        "docs/color_system/colors.md",
        r"\*\*(\d+) single-hue families\*\*",
        _n_single_hue_families,
    ),
    (
        "docs/color_system/colors.md",
        r"(\d+) chromatic ramps plus gray",
        _n_chromatic_families,
    ),
    (
        "docs/color_system/colormaps.md",
        r"\*\*(\d+) continuous colormaps\*\*",
        _n_v5_cmaps,
    ),
    (
        "docs/color_system/colormaps.md",
        r"\*\*(\d+) qualitative colormaps\*\*",
        _n_qualitative_cmaps,
    ),
    (
        "docs/color_system/colormaps.md",
        r"returns the\s+(\d+)\s+Model B family records",
        _n_listed_colormaps,
    ),
    (
        "docs/color_system/colormaps.md",
        r"Explore the (\d+)-map continuous v5 catalog",
        _n_v5_cmaps,
    ),
    (
        "docs/design_system/index.md",
        r"(\d+) perceptually-designed colormaps",
        _n_v5_cmaps,
    ),
    (
        "docs/fonts/index.md",
        r"bundles \*\*(\d+) text font files\*\* organized into "
        r"\*\*\d+ documented\s+file\s+groups\*\*",
        _n_font_files,
    ),
    (
        "docs/fonts/index.md",
        r"text font files\*\* organized into \*\*(\d+) documented\s+"
        r"file\s+groups\*\*",
        _n_font_file_groups,
    ),
    (
        "docs/fonts/index.md",
        r"registers those files as \*\*(\d+) matplotlib family names\*\*",
        _n_registered_font_families,
    ),
    (
        "docs/fonts/families.md",
        r"bundles \*\*(\d+) text font files\*\* across \*\*\d+ "
        r"documented\s+file\s+groups\*\*",
        _n_font_files,
    ),
    (
        "docs/fonts/families.md",
        r"text font files\*\* across \*\*(\d+) documented\s+file\s+"
        r"groups\*\*",
        _n_font_file_groups,
    ),
    (
        "docs/fonts/families.md",
        r"assets as \*\*(\d+) matplotlib family names\*\*",
        _n_registered_font_families,
    ),
    (
        "docs/fonts/utilities.md",
        r"all (\d+) bundled fonts are automatically",
        _n_font_files,
    ),
    (
        "docs/design_system/index.md",
        r"(\d+) publication-ready fonts \(\d+ files across \d+ file groups\)",
        _n_registered_font_families,
    ),
    (
        "docs/design_system/index.md",
        r"publication-ready fonts \((\d+) files across \d+ file groups\)",
        _n_font_files,
    ),
    (
        "docs/design_system/index.md",
        r"publication-ready fonts \(\d+ files across (\d+) file groups\)",
        _n_font_file_groups,
    ),
    (
        "docs/usage_guide/styles.md",
        r"giving \*\*(\d+) presets\*\* total",
        _n_presets,
    ),
    (
        "docs/color_system/palettes.md",
        r"and (\d+) curated qualitative sets",
        _n_curated_palettes,
    ),
    (
        "docs/color_system/palettes.md",
        r"The rail has (\d+) qualitative choices",
        _n_qualitative_rail_palettes,
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


def test_recipe_count_claim_numeric_leaves_are_recursive() -> None:
    """Count nested numeric leaves while excluding booleans and metadata."""
    nested_value = {
        "scalar": 1,
        "profile": [0.1, 0.2, {"tail": 3.0}],
        "metadata": {"enabled": True, "label": "not numeric"},
    }

    assert _numeric_leaves(nested_value) == 4


@pytest.mark.parametrize(
    ("claim_re", "expected"),
    [
        (r"bookkeeping total is \*\*(\d+) named slots\*\*", "107"),
        (r"corresponds to \*\*(\d+) scalar numeric leaves\*\*", "116"),
    ],
)
def test_recipe_count_claim_is_statically_present(
    claim_re: str, expected: str
) -> None:
    """Keep both recipe count claims checkable without loading authority."""
    text = (_REPO / "docs" / "color_system" / "design-rationale.md").read_text(
        encoding="utf-8"
    )

    assert re.findall(claim_re, text) == [expected]


_APPROVED_RECIPE_COUNT_CONTEXTS: dict[str, tuple[str, ...]] = {
    "107": (
        "107 named slots",
        "107 named bookkeeping slots",
        "107 is not the input count",
    ),
    "116": ("116 scalar numeric leaves",),
}


def _normalize_recipe_count_text(text: str) -> str:
    """Normalize Markdown, case, hyphenation, and whitespace in count prose."""
    normalized = re.sub(r"[*_`]+", "", text.casefold())
    normalized = re.sub(r"[-\u2010-\u2015]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _recipe_count_unit_violations(text: str) -> list[str]:
    """Find every 107 or 116 occurrence outside an approved count context."""
    normalized = _normalize_recipe_count_text(text)
    violations: list[str] = []
    for match in re.finditer(r"(?<!\d)(107|116)(?!\d)", normalized):
        count = match.group(1)
        candidate = normalized[match.start() :]
        approved_contexts = _APPROVED_RECIPE_COUNT_CONTEXTS[count]
        if any(
            re.match(rf"{re.escape(context)}\b", candidate)
            for context in approved_contexts
        ):
            continue
        violations.append(candidate[:80])
    return violations


def test_recipe_count_language_has_named_units_throughout_rationale() -> None:
    """Require approved units for every 107 and 116 in the rationale."""
    text = (_REPO / "docs" / "color_system" / "design-rationale.md").read_text(
        encoding="utf-8"
    )

    assert _recipe_count_unit_violations(text) == []


@pytest.mark.parametrize(
    "ambiguous_claim",
    [
        "**107** recipe inputs",
        "107 recipe-input numbers",
        "107 recipe input values",
        "107 input numbers",
        "107 Recipe Inputs",
        "**116** numeric leaves",
        "116 scalar numeric values",
    ],
)
def test_recipe_count_language_rejects_unapproved_contexts(
    ambiguous_claim: str,
) -> None:
    """Reject emphasis, case, hyphenation, and wording evasions."""
    assert _recipe_count_unit_violations(ambiguous_claim)


@pytest.mark.parametrize(
    "approved_claim",
    [
        "**107** Named Slots",
        "107 named-bookkeeping slots",
        "107 is not the input-count",
        "**116** Scalar-Numeric Leaves",
    ],
)
def test_recipe_count_language_accepts_normalized_approved_contexts(
    approved_claim: str,
) -> None:
    """Allow normalized forms of only the approved count contexts."""
    assert _recipe_count_unit_violations(approved_claim) == []


def test_recipe_count_language_checks_every_occurrence() -> None:
    """Inspect every count even when approved and ambiguous claims mix."""
    text = (
        "107 named slots; 107 input numbers; "
        "116 scalar numeric leaves; 116 values"
    )

    assert len(_recipe_count_unit_violations(text)) == 2


def test_color_and_discovery_contract_counts_are_exact() -> None:
    """Keep unlike counts named so 107 can never be mistaken for MCP tools."""
    assert {
        "chromatic_families": _n_chromatic_families(),
        "single_hue_total": _n_single_hue_families(),
        "continuous_families": _n_v5_cmaps(),
        "qualitative_families": _n_qualitative_cmaps(),
        "public_families": _n_listed_colormaps(),
        "recipe_bookkeeping_slots": _n_recipe_bookkeeping_slots(),
        "recipe_scalar_leaves": _n_recipe_scalar_leaves(),
        "registrations": _n_registrations(),
        "typing_colors": _n_typing_colors(),
        "typing_colormaps": _n_typing_colormaps(),
        "mcp_tools": _n_mcp_tools(),
        "mcp_resources": _n_mcp_resources(),
        "mcp_resource_templates": _n_mcp_resource_templates(),
        "mcp_prompts": _n_mcp_prompts(),
    } == {
        "chromatic_families": 19,
        "single_hue_total": 20,
        "continuous_families": 43,
        "qualitative_families": 13,
        "public_families": 56,
        "recipe_bookkeeping_slots": 107,
        "recipe_scalar_leaves": 116,
        "registrations": 99,
        "typing_colors": 1272,
        "typing_colormaps": 99,
        "mcp_tools": 16,
        "mcp_resources": 10,
        "mcp_resource_templates": 4,
        "mcp_prompts": 2,
    }


def test_public_color_list_order_values_and_signatures_remain_frozen() -> None:
    """Task-9 prose/comment edits must not alter the public Model-B surface."""
    import dartwork_mpl as dm
    from dartwork_mpl._colors._catalog import load_v5_snapshot

    baseline = load_v5_snapshot()
    assert dm.list_colors() == [
        dict(record) for record in baseline.public_inventory
    ]
    assert {
        name: str(inspect.signature(getattr(dm, name)))
        for name in ("colors", "set_colors", "list_colors", "show_colors")
    } == {
        "colors": "(name: 'str', n: 'int | None' = None, *, reverse: 'bool' = False) -> 'mcolors.Colormap | list[str]'",
        "set_colors": "(name_or_list: 'str | Iterable[str] | None' = None, *, ax: 'Axes | None' = None, n: 'int | None' = None, styles: 'bool' = False) -> 'None'",
        "list_colors": "(kind: \"Literal['sequential', 'multi-hue', 'diverging', 'cyclic', 'qualitative'] | str | None\" = None) -> 'list[dict[str, object]]'",
        "show_colors": "(kind: \"Literal['sequential', 'multi-hue', 'diverging', 'cyclic', 'qualitative'] | str | None\" = None, names: 'Iterable[str] | None' = None, n: 'int | None' = None) -> 'Figure'",
    }
