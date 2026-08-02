from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

MODELED_Y_FIRST_USE = (
    "Modeled relative CIE Y (`relative_y`) is calculated from nominal D65 "
    "sRGB; it is not a measurement of a particular display, perceived "
    "brightness, or OKLab `L`."
)

PUBLIC_COLOR_LANGUAGE_PATHS = (
    "docs/usage_guide/colors.md",
    "docs/design_system/index.md",
    "docs/integrations/mcp_server.md",
    "docs/color_system/color-class.md",
    "docs/color_system/colormaps.md",
    "docs/color_system/colors.md",
    "docs/color_system/design-rationale.md",
    "docs/color_system/palettes.md",
    "docs/color_system/validation.md",
    "docs/adr/0001-oklab-centered-color-construction.md",
    "docs/superpowers/specs/2026-07-14-oklab-centered-color-system-design.md",
    "docs/superpowers/specs/2026-07-17-beginner-friendly-color-docs-design.md",
    "docs/superpowers/specs/2026-07-21-color-rationale-accuracy-design.md",
    "src/dartwork_mpl/asset/prompt/00-index.md",
    "src/dartwork_mpl/asset/prompt/01-policy.md",
    "src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml",
)

MODELED_Y_STANDALONE_PATHS = (
    "docs/usage_guide/colors.md",
    "docs/design_system/index.md",
    "docs/integrations/mcp_server.md",
    "docs/color_system/color-class.md",
    "docs/color_system/colormaps.md",
    "docs/color_system/design-rationale.md",
    "docs/color_system/palettes.md",
    "docs/color_system/validation.md",
    "docs/adr/0001-oklab-centered-color-construction.md",
    "src/dartwork_mpl/asset/prompt/00-index.md",
    "src/dartwork_mpl/asset/prompt/01-policy.md",
    "src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml",
)

RUNTIME_COLOR_LANGUAGE_PATHS = (
    "src/dartwork_mpl/_colors/_comparison.py",
    "src/dartwork_mpl/_colors/_curated.py",
    "src/dartwork_mpl/mcp/prompts.py",
    "src/dartwork_mpl/mcp/resources.py",
    "src/dartwork_mpl/mcp/tools.py",
    "src/dartwork_mpl/validate/_checks/grayscale_safety.py",
)

MODELED_Y_SOURCE_PATHS = (
    "src/dartwork_mpl/_colors/_conversion.py",
    "src/dartwork_mpl/_colors/_discrete.py",
    "src/dartwork_mpl/asset/mplstyle/theme-dark.mplstyle",
    "src/dartwork_mpl/_colors/_cycles.py",
)

PHYSICAL_OUTPUT_PATTERN = re.compile(
    r"\b(?:physical(?:[- ]+(?:relative[- ]?)?Y|[- ]+output|\s+light\s+output)"
    r"|rendered(?:\s+sRGB)?\s+light[- ]output|light[- ]output|"
    r"output[- ]light|물리\s*(?:휘도|Y|출력)|실제\s*출력량|휘도\s*잠금)\b",
    re.IGNORECASE,
)

UNQUALIFIED_OUTPUT_CLAIM_PATTERNS = (
    PHYSICAL_OUTPUT_PATTERN,
    re.compile(
        r"\b(?:print[- ]safe|safe\s+(?:for\s+)?(?:B&W\s+)?print|"
        r"survive\s+grayscale(?:\s*/\s*print)?|grayscale\s+collapse|"
        r"collapse\s+in\s+grayscale|indistinguishable\s+in\s+grayscale|"
        r"grayscale\s+separation)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bpublished\b[^.!?]{0,120}\b(?:CVD|"
        r"color[- ]vision[- ]deficiency)\b[^.!?]{0,80}"
        r"\b(?:reference\s+)?(?:vectors?|cases?)\b|"
        r"\b(?:CVD|color[- ]vision[- ]deficiency)\b[^.!?]{0,80}"
        r"\bpublished\b[^.!?]{0,120}\b(?:vectors?|cases?)\b",
        re.IGNORECASE,
    ),
)

NEGATED_NEEDLE_PREFIX = re.compile(
    r"(?:\bdo\s+not\b|\bdoes\s+not\b|\bnever\b|\bavoid\b|\breject\b|"
    r"\breplace\b|\bretir(?:e|ed)\b|\bmisleading\b|\bstale\b|"
    r"\bnot\s+(?:call|describe|claim|label|use)\b)[^.!?]{0,100}$",
    re.IGNORECASE,
)


def _page(relpath: str) -> str:
    text = (ROOT / relpath).read_text(encoding="utf-8")
    return re.sub(r"\s+", " ", text)


def _python_string_literals(relpath: str) -> str:
    """Return user-visible candidate strings without source comments."""
    source = (ROOT / relpath).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=relpath)
    strings = (
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    )
    return "\n".join(strings)


def _source_prose(relpath: str) -> str:
    """Normalize adjacent source-comment lines for wording assertions."""
    text = (ROOT / relpath).read_text(encoding="utf-8")
    return re.sub(r"\s+", " ", re.sub(r"\n\s*#\s?", " ", text))


def _unqualified_language_claims(text: str) -> list[str]:
    """Find misleading positive claims while ignoring explicit negatives."""
    findings: list[str] = []
    for pattern in UNQUALIFIED_OUTPUT_CLAIM_PATTERNS:
        for match in pattern.finditer(text):
            sentence_start = max(
                text.rfind(".", 0, match.start()),
                text.rfind("!", 0, match.start()),
                text.rfind("?", 0, match.start()),
            )
            prefix = text[sentence_start + 1 : match.start()]
            if NEGATED_NEEDLE_PREFIX.search(prefix):
                continue
            line = text.count("\n", 0, match.start()) + 1
            findings.append(f"line {line}: {match.group(0)!r}")
    return findings


def _assert_modeled_y_first_use(relpath: str) -> None:
    """Require the canonical limitation before standalone Y shorthand."""
    text = _page(relpath)
    assert MODELED_Y_FIRST_USE in text, relpath
    first_semantic_use = re.search(
        r"\b(?:modeled[- ]relative(?:\s+CIE)?\s+Y|relative_y|relative\s+Y)\b",
        text,
        re.IGNORECASE,
    )
    assert first_semantic_use is not None, relpath
    assert first_semantic_use.start() == text.index(MODELED_Y_FIRST_USE), (
        relpath
    )


def _assert_first_use_is_explained(
    text: str, term: str, explanation: str
) -> None:
    assert explanation in text
    explanation_start = text.index(explanation)
    assert (
        explanation_start
        <= text.index(term)
        < (explanation_start + len(explanation))
    )


def test_claim_inventory_uses_descriptive_destinations_for_all_rows() -> None:
    """Require a stable anchor or section description for every claim group."""
    inventory = (
        ROOT
        / "docs/superpowers/specs/assets/2026-07-17-beginner-friendly-color-docs"
        / "claim-inventory.md"
    ).read_text(encoding="utf-8")
    rows: list[str] = [
        line
        for line in inventory.splitlines()
        if re.match(r"\| [A-Z]\d{2} \|", line)
    ]
    bare_destinations: list[str] = []

    assert len(rows) == 27
    for row in rows:
        claim_id, source, _, destination, _ = (
            cell.strip() for cell in row.strip("|").split("|")
        )
        if destination == source or re.fullmatch(r"\S+\.md", destination):
            bare_destinations.append(f"{claim_id}: {destination}")

    assert not bare_destinations, bare_destinations


def test_usage_guide_starts_with_a_task_chooser() -> None:
    text = _page("docs/usage_guide/colors.md")
    for phrase in (
        "one mark",
        "separate series or categories",
        "numeric values",
        "create or adjust a color",
    ):
        assert phrase in text
    assert text.index("What should I use?") < text.index("OKLab")


def test_usage_guide_defines_beginner_color_vocabulary() -> None:
    text = _page("docs/usage_guide/colors.md")
    for phrase in (
        "Hue is the color family",
        "Lightness describes the light-to-dark direction",
        "Chroma describes how colorful or muted a color is",
        "A palette is a finite list of colors",
        "A colormap turns numeric values into colors",
        "Sequential",
        "Diverging",
        "Cyclic",
        "Qualitative",
    ):
        assert phrase in text


def test_usage_guide_defines_contrast_with_a_chart_example() -> None:
    text = _page("docs/usage_guide/colors.md")
    assert (
        "Contrast describes how strongly two neighboring colors stand apart"
    ) in text
    assert "For example, a dark annotation on a white chart background" in text


def test_usage_guide_explains_the_color_construction_job() -> None:
    text = _page("docs/usage_guide/colors.md")
    assert "OKLab and OKLCH are used to construct and adjust colors" in text
    assert "Construction uses ΔEOK to space neighboring steps" in text
    assert "ΔEOK is a color-distance ruler: larger means more different" in text


def test_usage_guide_explains_the_modeled_relative_y_job() -> None:
    text = _page("docs/usage_guide/colors.md")
    assert MODELED_Y_FIRST_USE in text
    assert "records nominal output ordering" in text


def test_usage_guide_explains_the_independent_validation_job() -> None:
    text = _page("docs/usage_guide/colors.md")
    assert (
        "CIELAB, ΔE00, and color-vision deficiency (CVD) simulation are "
        "independent validation checks only"
    ) in text
    assert "do not construct colors or define modeled relative Y" in text


def test_current_color_language_rejects_unqualified_output_claims() -> None:
    """Reject measurement, CVD-vector, print, and grayscale guarantees."""
    findings: list[str] = []
    for relpath in PUBLIC_COLOR_LANGUAGE_PATHS:
        text = (ROOT / relpath).read_text(encoding="utf-8")
        findings.extend(
            f"{relpath}:{finding}"
            for finding in _unqualified_language_claims(text)
        )

    assert not findings, findings


def test_runtime_human_strings_reject_unqualified_output_claims() -> None:
    """Keep runtime labels honest without scanning compatibility symbols."""
    findings: list[str] = []
    for relpath in RUNTIME_COLOR_LANGUAGE_PATHS:
        text = _python_string_literals(relpath)
        findings.extend(
            f"{relpath}:{finding}"
            for finding in _unqualified_language_claims(text)
        )

    assert not findings, findings


def test_active_source_comments_bound_modeled_y_and_print_names() -> None:
    """Comments must not turn computed Y or a legacy name into a guarantee."""
    findings: list[str] = []
    stale_phrases = (
        "Physical linear-sRGB D65 relative-Y row",
        "normalized physical D65 relative Y",
        "normalized physical relative_y output contract",
        "인쇄 8색",
    )
    for relpath in MODELED_Y_SOURCE_PATHS:
        text = (ROOT / relpath).read_text(encoding="utf-8")
        findings.extend(
            f"{relpath}: {phrase!r}"
            for phrase in stale_phrases
            if phrase in text
        )

    assert not findings, findings

    required_by_path = {
        "src/dartwork_mpl/_colors/_conversion.py": (
            "Nominal D65 sRGB modeled-relative-CIE-Y row",
            "not a measurement of a display or print process",
        ),
        "src/dartwork_mpl/_colors/_discrete.py": (
            "modeled relative CIE Y calculated from nominal D65 sRGB",
        ),
        "src/dartwork_mpl/asset/mplstyle/theme-dark.mplstyle": (
            "modeled relative CIE Y (`relative_y`) calculated from nominal "
            "D65 sRGB",
            "Neither modeled quantity measures a display or print process",
        ),
        "src/dartwork_mpl/_colors/_cycles.py": (
            '"Octave Print" is a historical identifier',
            "does not guarantee behavior for a particular printer",
        ),
    }
    for relpath, phrases in required_by_path.items():
        text = _source_prose(relpath)
        for phrase in phrases:
            assert phrase in text, f"{phrase!r} missing from {relpath}"

    compatibility = _source_prose(
        "src/dartwork_mpl/_colors/_compatibility_metrics.py"
    )
    assert "``physical_y`` is a compatibility identifier" in compatibility
    assert (
        "calculated from nominal encoded sRGB, not measured from a particular "
        "display or print process" in compatibility
    )


def test_validation_and_inventory_pin_all_eighteen_exact_surfaces() -> None:
    """Keep the public validation scope aligned with the vendor-value gate."""
    validation = _page("docs/color_system/validation.md")
    inventory = _page(
        "docs/superpowers/specs/assets/2026-07-17-beginner-friendly-color-docs/"
        "claim-inventory.md"
    )

    assert "All 18 frozen public surfaces" in validation
    assert "18. all 892 vendor token name → hex values." in validation
    assert "all 18 exact surfaces" in inventory
    assert "all 892 vendor token name → hex values" in inventory


def test_accepted_design_pins_vendor_values_and_source_provenance() -> None:
    """Make the 18th exact surface independently reproducible from sources."""
    design = _page(
        "docs/superpowers/specs/"
        "2026-07-14-oklab-centered-color-system-design.md"
    )

    assert "18. `vendor_colors`" in design
    assert "all 892 vendor token name → lowercase `#rrggbb` values" in design
    assert (
        "`6dc6053c4f8c66adb9d7deb746c3e7eee0295c27cc107b37c872b46f83f79a72`"
        in design
    )
    for source_mapping in (
        "`opencolor.txt` → `oc.*`",
        "`tailwind_colors.json` → `tw.*`",
        "`material_colors.json` → `md.*`",
        "`ant_colors.json` → `ad.*`",
        "`chakra_colors.json` → `cu.*`",
        "`primer_colors.json` → `pr.*`",
    ):
        assert source_mapping in design


@pytest.mark.parametrize(
    "relpath",
    (
        "docs/superpowers/specs/"
        "2026-07-14-oklab-centered-color-system-design.md",
        "docs/superpowers/plans/2026-07-14-oklab-centered-color-system.md",
    ),
    ids=("accepted-design", "active-plan"),
)
def test_normative_comparison_docs_define_invocation_authority(
    relpath: str,
) -> None:
    """Separate the live process decision from a completed-run artifact."""
    text = _page(relpath)

    assert (
        "The comparator process exit code is the authority for the current "
        "invocation."
    ) in text
    assert (
        "`report.json` is a completed-run gate record and last-write evidence"
        in text
    )
    assert "file presence alone" in text
    for stale_claim in (
        "CI는 JSON의 `passed`가 `true`인지 검사한다",
        "JSON이 자동화 SSOT다",
        "`report.json` as the machine authority",
    ):
        assert stale_claim not in text


def test_validation_assigns_invalid_data_to_the_correct_exit_domain() -> None:
    """Distinguish reportable leaves from source and schema failures."""
    text = _page("docs/color_system/validation.md")
    reportable = text.index(
        "A representable invalid hex leaf already present in a constructed "
        "candidate snapshot belongs to exit `1`"
    )
    exit_one = text.index("the report can represent and explain it", reportable)
    source_failure = text.index(
        "A source parse or schema failure—including a malformed bundled vendor "
        "asset—belongs to exit `2`"
    )

    assert reportable < exit_one < source_failure


@pytest.mark.parametrize("relpath", MODELED_Y_STANDALONE_PATHS)
def test_standalone_color_surfaces_define_modeled_y_at_first_use(
    relpath: str,
) -> None:
    """Make each independently opened surface state the model limitation."""
    _assert_modeled_y_first_use(relpath)


def test_mcp_and_comparison_strings_include_the_modeled_y_limitation() -> None:
    """Define the metric in independently consumed runtime descriptions."""
    for relpath in (
        "src/dartwork_mpl/_colors/_comparison.py",
        "src/dartwork_mpl/mcp/prompts.py",
        "src/dartwork_mpl/mcp/resources.py",
    ):
        assert MODELED_Y_FIRST_USE in _python_string_literals(relpath), relpath


def test_cvd_evidence_sources_are_described_independently() -> None:
    """Do not present project-derived CVD cases as published vectors."""
    required = (
        "published Sharma et al. CIEDE2000 reference pairs",
        "source-pinned Machado (2009) matrices",
        "project-adapted Brettel–Viénot–Mollon (1997) matrices",  # noqa: RUF001
        "project-derived CVD regression cases",
    )
    for relpath in (
        "docs/color_system/design-rationale.md",
        "docs/color_system/validation.md",
    ):
        text = _page(relpath)
        for phrase in required:
            assert phrase in text, f"{phrase!r} missing from {relpath}"


def test_usage_guide_explains_the_text_contrast_job() -> None:
    text = _page("docs/usage_guide/colors.md")
    assert (
        "Web Content Accessibility Guidelines (WCAG) contrast is a separate "
        "check for text against a known background"
    ) in text
    assert "does not certify an entire palette" in text


def test_beginner_routes_avoid_undefined_internal_color_vocabulary() -> None:
    for relpath in (
        "docs/usage_guide/colors.md",
        "docs/design_system/index.md",
    ):
        text = _page(relpath)
        for phrase in (
            "Model B",
            "physical-Y topology",
            "topology gates",
            "validation gates",
        ):
            assert phrase not in text, f"{phrase!r} remains in {relpath}"


def test_rationale_explains_the_decision_before_the_metrics() -> None:
    text = _page("docs/color_system/design-rationale.md")
    decision = text.index("The decision in plain language")
    introduction = text.index(
        "pictures are reproducible evidence for the named build"
    )
    principles = text.index("## Four principles")
    metrics = text.index("The construction foundation")
    assert introduction < decision < principles < metrics
    assert (
        "A new, intentionally incompatible color system could use direct OKLCH"
        in text
    )
    assert "compatibility promise, not a law of color theory" in text


def test_rationale_moves_bookkeeping_to_family_anatomy() -> None:
    """Open with purpose and the decision, not inventory bookkeeping."""
    text = _page("docs/color_system/design-rationale.md")
    anatomy_start = text.index("## Anatomy of a family")
    opening = text[:anatomy_start]
    anatomy = text[anatomy_start : text.index("## The metric system")]

    for phrase in ("107 named slots", "116 scalar numeric leaves", "MCP"):
        assert phrase not in opening
        assert phrase in anatomy
    assert text.index("The decision in plain language") < anatomy_start


def test_rationale_defines_the_four_rulers_in_plain_language() -> None:
    text = _page("docs/color_system/design-rationale.md")
    explanation = text.index("Four rulers, four different jobs")
    first_formula = text.index("neutral_tone = cbrt(relative_y)")

    assert explanation < first_formula
    required = (
        "OKLab and OKLCH are two coordinate views",
        "ΔEOK×100",  # noqa: RUF001
        "0 means nominal black and 1 means nominal reference white",
        "closely related decoded-sRGB Y-like calculations",
        "separately pinned coefficient conventions",
        "WCAG adds a pairwise contrast ratio",
    )
    for phrase in required:
        assert phrase in text


def test_rationale_separates_fact_contract_choice_evidence_and_limits() -> None:
    text = _page("docs/color_system/design-rationale.md")
    for phrase in (
        "Design choice",
        "Implementation",
        "Evidence",
        "Limits",
        "modeled relative CIE Y calculated from nominal D65 sRGB",
        "not a measurement of a particular display",
        "100 times the raw Euclidean distance in Oklab",
        "specified foreground/background pair",
        "model-specific regression diagnostic",
    ):
        assert phrase in text

    for phrase in (
        "physical light output",
        "independent oracles",
        "accessibility oracle",
        "CIEDE2000 correctly fails",
    ):
        assert phrase not in text


def test_rationale_rejects_physical_relative_y_variants() -> None:
    """Keep calculated relative-Y prose distinct from measurements."""
    text = _page("docs/color_system/design-rationale.md")
    pattern = r"\bphysical(?:[- ]+relative[- ]?Y\b|[- ]+`relative_y`|[- ]Y\b)"

    assert re.search(pattern, "physical `relative_y`", re.I)
    assert not re.search(pattern, text, re.I)


def test_rationale_limits_wcag_to_pairwise_contrast() -> None:
    """A WCAG ratio checks contrast and does not establish legibility."""
    text = _page("docs/color_system/design-rationale.md")

    assert "tested pairwise contrast ratio and threshold" in text
    assert "legibility for the tested pair" not in text


def test_rationale_scopes_yellow_contrast_to_shipped_identity() -> None:
    """Keep the yellow contrast limit local to the shipped bright ramp."""
    text = _page("docs/color_system/design-rationale.md")

    assert "shipped yellow ramp" in text
    assert "bright-yellow identity" in text
    assert (
        "marks the first shipped step that passes its stated contrast check, "
        "or explicitly reports that no shipped step passes"
    ) in text
    assert "true of every color system" not in text


def test_rationale_describes_nominal_rendering_without_observer_claim() -> None:
    """Describe the unsimulated colors without speaking for observers."""
    text = _page("docs/color_system/design-rationale.md")

    assert "distinct in their unsimulated nominal-sRGB rendering" in text
    assert "clear colors in normal vision" not in text


def test_rationale_explains_local_evidence_vocabulary() -> None:
    """Define each specialist aid before its detailed evidence."""
    text = _page("docs/color_system/design-rationale.md")

    for phrase in (
        "sRGB cannot display every OKLCH request",
        "pre-quantization bisection holds `L` and `h` constant while "
        "reducing `C`",
        "Bisection repeatedly halves the remaining search range",
        "Single-hue sequential: low values are light",
        "Multi-hue sequential: low values are dark",
        "Diverging: two poles around a light center",
        "Cyclic: no low/high direction",
        "Qualitative: unordered",
        "The seam is the join between a cyclic map's end and start",
        "Isoluminant means designed to keep `relative_y` constant",
        "Lower CV means more even neighboring distances",
        "R² = 1 means a perfect fit to the specified model",
        "wRMSE is weighted fit error, so lower is better",
        "Protan and deutan are red-green deficiency classes",
        "tritan is a blue-yellow deficiency class",
        "not a guarantee for every individual observer",
        "A lookup table (LUT) is the ordered 256 colors shipped behind one "
        "continuous map",
    ):
        assert phrase in text

    assert text.index("What these statistics mean") < text.index("R² of 0.997")
    assert text.index("What LUT means") < text.index("43×256 LUTs")  # noqa: RUF001


def test_shipped_gamut_mapping_contract_is_bounded() -> None:
    """Pin the shipped boundary policy without an appearance-optimum claim."""
    required = (
        "For requests whose OKLCH `L` is in range and chroma is non-negligible",
        "pre-quantization bisection holds `L` and `h` constant while "
        "reducing `C`",
        "Near neutral, hue is powerless as a coordinate and numerically "
        "unstable",
        "boundary search stops at the implementation's numeric tolerance",
        "final residual channel clamp and 8-bit serialization can perturb "
        "reconstructed OKLCH coordinates",
        "Out-of-range achromatic lightness maps to black or white",
        "not a perceptual minimum-difference or global appearance optimization",
        "does not preserve appearance exactly",
    )

    for relpath in (
        "docs/color_system/design-rationale.md",
        "docs/color_system/colormaps.md",
    ):
        text = _page(relpath)
        for phrase in required:
            assert phrase in text, f"{phrase!r} missing from {relpath}"
        for stale_claim in (
            "Local-MINDE",
            "globally optimal",
            "preserves appearance exactly",
        ):
            assert stale_claim not in text, (
                f"{stale_claim!r} remains in {relpath}"
            )


def test_a1_locally_qualifies_the_constant_lh_gamut_policy() -> None:
    """Do not let a bounded note mask an unqualified A1 contract."""
    raw = (ROOT / "docs/color_system/design-rationale.md").read_text(
        encoding="utf-8"
    )
    a1_start = raw.index("> **A1**")
    a1_end = raw.index(":::{note}", a1_start)
    a1_lines = (
        line.removeprefix("> ") for line in raw[a1_start:a1_end].splitlines()
    )
    a1 = re.sub(r"\s+", " ", " ".join(a1_lines))

    assert (
        "For requests whose OKLCH `L` is in range and chroma is "
        "non-negligible, pre-quantization gamut mapping holds `L` and `h` "
        "constant while reducing `C`."
    ) in a1
    assert (
        "mapping holds the requested OKLCH `L` and `h` while reducing `C`"
        not in a1
    )


def test_colormap_direction_contracts_are_class_specific() -> None:
    """Keep ordered directions separate from nonordered map topologies."""
    required = (
        "For forward/default registrations",
        "Single-hue sequential: low values are light and high values are dark",
        "Multi-hue sequential: low values are dark and high values are light",
        "Diverging: two poles around a light center; no one monotonic "
        "low-to-high direction applies",
        "Cyclic: no low/high direction; the generating path closes",
        "Qualitative: unordered",
        "`_r` swaps the endpoint assignment",
    )

    for relpath in (
        "docs/color_system/design-rationale.md",
        "docs/color_system/colormaps.md",
    ):
        text = _page(relpath)
        for phrase in required:
            assert phrase in text, f"{phrase!r} missing from {relpath}"


def test_cyclic_path_and_stored_lut_have_distinct_closure_contracts() -> None:
    """A closed recipe path must not imply duplicated LUT endpoints."""
    required = (
        "the shipped 256-entry LUT is endpoint-exclusive",
        "first and last stored entries differ by one ordinary wrap step",
        "not duplicate endpoints",
    )

    for relpath in (
        "docs/color_system/design-rationale.md",
        "docs/color_system/colormaps.md",
    ):
        text = _page(relpath)
        for phrase in required:
            assert phrase in text, f"{phrase!r} missing from {relpath}"


def test_colormap_reversal_distinguishes_continuous_and_qualitative_maps() -> (
    None
):
    """Reserve registered ``_r`` names for the continuous catalog."""
    required = (
        "`_r` is registered only for continuous maps",
        "`dm.colors(..., reverse=True)`",
    )

    for relpath in (
        "docs/color_system/design-rationale.md",
        "docs/color_system/colormaps.md",
    ):
        text = _page(relpath)
        for phrase in required:
            assert phrase in text, f"{phrase!r} missing from {relpath}"
        for stale_claim in (
            "Reverse any map with `_r`",
            "Add `_r` to reverse any map",
        ):
            assert stale_claim not in text, (
                f"{stale_claim!r} remains in {relpath}"
            )


def test_colormap_hue_sources_are_not_limited_to_family_anchors() -> None:
    """Treat family anchors as identities and waypoints, not a closed set."""
    required = (
        "The 19 chromatic `h₀` anchors describe palette identity and "
        "multi-hue scene waypoints",
        "not the only hue source",
        "Diverging recipes may use rendered poles",
        "cyclic recipes may traverse a full hue circle",
    )

    for relpath in (
        "docs/color_system/design-rationale.md",
        "docs/color_system/colormaps.md",
    ):
        text = _page(relpath)
        for phrase in required:
            assert phrase in text, f"{phrase!r} missing from {relpath}"
        for stale_claim in (
            "only hue vocabulary",
            "chosen only at family anchors",
        ):
            assert stale_claim not in text, (
                f"{stale_claim!r} remains in {relpath}"
            )


def test_colormap_range_and_benchmark_claims_are_bounded() -> None:
    """Keep range and comparison evidence local to class and protocol."""
    required = (
        "class- and scene-specific",
        "Cross-panel comparison of the same variable requires the same "
        "colormap, direction, and normalization",
        "identical limits or the same `Normalize` object",
        "Different maps are not one comparable color scale",
        "bounded same-protocol benchmark",
    )

    for relpath in (
        "docs/color_system/design-rationale.md",
        "docs/color_system/colormaps.md",
    ):
        text = _page(relpath)
        for phrase in required:
            assert phrase in text, f"{phrase!r} missing from {relpath}"
        for stale_claim in ("globally shared range", "one shared range"):
            assert stale_claim not in text, (
                f"{stale_claim!r} remains in {relpath}"
            )


def test_colormap_scene_names_are_mnemonic_art_direction() -> None:
    """Do not turn scene-label mnemonics into colorimetric claims."""
    required = (
        "Scene names are mnemonic art-direction labels that evoke "
        "natural-light scenes; they do not claim colorimetric fidelity to "
        "those phenomena."
    )

    for relpath in (
        "docs/color_system/design-rationale.md",
        "docs/color_system/colormaps.md",
    ):
        assert required in _page(relpath), relpath


def test_colormap_modeled_y_ordering_is_a_bounded_cue() -> None:
    """Describe modeled Y as one nominal-model cue, not robustness proof."""
    text = _page("docs/color_system/colormaps.md")

    assert (
        "Modeled-relative-Y ordering supplies a non-hue ordering cue in the "
        "nominal-sRGB model; actual robustness depends on observer, display, "
        "and viewing conditions."
    ) in text
    assert "which makes them robust" not in text


def test_colormap_docs_scope_equalization_by_topology() -> None:
    """Match each public construction claim to the compiler path that uses it."""
    detailed_pages = (
        "docs/color_system/colormaps.md",
        "docs/color_system/design-rationale.md",
    )
    required = (
        "chromatic single-hue, continuous gray, and multi-hue sequential paths",
        "11 diverging maps use pointwise symmetric arm construction",
        "`hue` samples equal hue angles",
        "`halo` and `corona` use closed-path ΔEOK arc-length resampling",
    )
    for relpath in detailed_pages:
        text = _page(relpath)
        for phrase in required:
            assert phrase in text, f"{phrase!r} missing from {relpath}"

    for relpath in (
        *detailed_pages,
        "docs/usage_guide/colors.md",
        "docs/design_system/index.md",
        "src/dartwork_mpl/asset/prompt/00-index.md",
        "src/dartwork_mpl/asset/prompt/01-policy.md",
    ):
        text = _page(relpath)
        for overclaim in (
            "Every continuous map uses",
            "Continuous paths use ΔEOK equalization",
            "constructed in OKLab/OKLCH with ΔEOK-equalized spacing",
        ):
            assert overclaim not in text, f"{overclaim!r} remains in {relpath}"


def test_discrete_gray_docs_distinguish_sampling_from_equalization() -> None:
    """Keep gray's measured near-evenness without inventing a compiler pass."""
    for relpath in (
        "docs/color_system/palettes.md",
        "docs/_static/dartwork-discrete-palette-rationale.md",
    ):
        text = _page(relpath)
        assert (
            "19 chromatic family ladders use ΔEOK arc-length equalization"
            in text
        )
        assert (
            "gray ladder directly samples ten evenly spaced neutral-tone positions"
            in text
        )
        assert (
            "resulting neighbor ΔEOK near-evenness is measured and protected by "
            "frozen non-regression gates"
        ) in text
        assert "10 ΔEOK-equalized steps per family" not in text

    migration = _page("docs/migration.md")
    assert (
        "19 arc-length-equalized chromatic ladders plus one directly sampled gray ladder"
        in migration
    )
    assert "20 families × 10 perceptually equalized" not in migration  # noqa: RUF001


def test_rationale_names_what_delta_eok_equalization_does_not_equalize() -> (
    None
):
    """Name the three distinct downstream rulers instead of a zero metaphor."""
    text = _page("docs/color_system/design-rationale.md")

    assert (
        "Equalizing ΔEOK steps does not simultaneously equalize CIEDE2000 "
        "distances, modeled-relative-Y increments, or separations after a "
        "named CVD simulation."
    ) in text
    assert "drives every ruler to zero" not in text


def test_catalog_validation_language_is_modeled_and_model_specific() -> None:
    """Separate modeled Y, diagnostic models, and pair-specific contrast."""
    physical_pattern = (
        r"\bphysical(?:[- ]+relative[- ]?Y\b|[- ]+`relative_y`|"
        r"[- ]+Y\b|[- ]+output\b)"
    )

    for relpath in (
        "docs/color_system/colormaps.md",
        "docs/color_system/palettes.md",
        "docs/color_system/validation.md",
    ):
        text = _page(relpath)
        assert (
            "Modeled relative CIE Y (`relative_y`) is calculated from nominal "
            "D65 sRGB"
        ) in text
        assert (
            "CIEDE2000 and the named CVD simulations are model-specific "
            "collision/regression diagnostics"
        ) in text
        assert not re.search(physical_pattern, text, re.I), relpath

    for relpath in (
        "docs/color_system/colormaps.md",
        "docs/color_system/palettes.md",
    ):
        text = _page(relpath)
        assert (
            "Web Content Accessibility Guidelines (WCAG) check pair-specific "
            "text contrast for a named foreground/background pair; this is "
            "not palette certification."
        ) in text
        assert text.count("pair-specific text contrast") == 1
        assert "not palette certification" in text


def test_scoped_docs_reject_certification_like_cvd_labels() -> None:
    """Use model-specific diagnostic terms instead of certification labels."""
    for relpath in (
        "docs/color_system/design-rationale.md",
        "docs/color_system/colormaps.md",
        "docs/color_system/palettes.md",
        "docs/color_system/validation.md",
    ):
        text = _page(relpath).casefold()
        for stale_claim in (
            "colorblind-mandatory",
            "accessibility chips",
            "accessibility checks",
        ):
            assert stale_claim not in text, (
                f"{stale_claim!r} remains in {relpath}"
            )

    colormaps = _page("docs/color_system/colormaps.md")
    palettes = _page("docs/color_system/palettes.md")
    float_source = (ROOT / "tests/test_docs_float_claims.py").read_text(
        encoding="utf-8"
    )

    assert "model-diagnostic chips" in colormaps
    assert "model-specific CVD/CIEDE2000 diagnostics" in colormaps
    assert (
        "Qualitative categories where distinction under the named CVD "
        "simulations matters"
    ) in palettes
    assert "Named-model color-vision diagnostics" not in palettes
    assert "CVD-safe palette" not in float_source
    assert "accessibility benchmark" not in float_source


def test_blocked_float_contract_accepts_valid_negated_uniformity_prose() -> (
    None
):
    """Statically guard the float assertion while package imports are blocked."""
    source = (ROOT / "tests/test_docs_float_claims.py").read_text(
        encoding="utf-8"
    )

    assert 'assert "universal perceptual uniformity" not in flat' not in source
    assert '"does not prove universal perceptual uniformity" in flat' in source
    assert '"not a claim of perfect uniformity" in flat' in source


def test_rationale_treats_nonmonotonic_y_as_a_map_property() -> None:
    """Separate a map property from task-dependent suitability and effects."""
    text = _page("docs/color_system/design-rationale.md")

    for phrase in (
        "Non-monotonic modeled relative Y is a map property",
        "Its suitability and its tendency to create ordering ambiguity or "
        "emphasize variation are task-dependent",
        "does not mean that all apparent detail is invented",
    ):
        assert phrase in text

    assert "Non-monotonic modeled relative Y is task-dependent" not in text


def test_rationale_bounds_typography_byte_reproducibility() -> None:
    """Keep byte reproducibility conditional on glyph and renderer bounds."""
    text = _page("docs/color_system/design-rationale.md")

    assert (
        "Byte reproducibility is bounded to bundled glyph coverage and a "
        "pinned rendering environment"
    ) in text
    assert "renders the same on every machine" not in text


def test_rationale_gives_one_practical_question_per_generation_rule() -> None:
    """Route A2–A8 through seven bounded design questions."""
    text = _page("docs/color_system/design-rationale.md")
    guide = text.index("How to read A2–A8")  # noqa: RUF001

    assert "Each design rule answers one practical question:" in text
    assert "Each axiom answers" not in text
    for phrase in (
        "How dark may each hue family go while retaining its identity?",
        "How colorful should each hue become, and where should it peak?",
        "How should hue turn as a family gets darker?",
        "Where should the ten named steps sit along the path?",
        "What changes for gray, which has no chromatic identity?",
        "What must pass before an output can be released?",
        "Why are colormap ranges chosen per topology and scene?",
    ):
        assert phrase in text

    assert "The generation design rules (A2–A8)" in text  # noqa: RUF001
    assert guide < text.index("### A2")


def test_rationale_generation_rules_separate_contract_layers() -> None:
    """Keep evidence distinct from the explicitly bounded A8 illustration."""
    text = _page("docs/color_system/design-rationale.md")
    rules = text[text.index("### A2") : text.index("## Anatomy of a family")]

    assert rules.count("Design intent.") == 7
    assert rules.count("Implementation.") == 7
    assert rules.count("Evidence.") == 6
    assert rules.count("Illustration.") == 1
    assert rules.count("Limits.") == 7


def test_rationale_bounds_catalog_art_direction_and_chroma_form() -> None:
    """Keep A2–A4 catalog choices distinct from psychophysical laws."""
    text = _page("docs/color_system/design-rationale.md")
    a2 = text[text.index("### A2") : text.index("### A3")]
    a3 = text[text.index("### A3") : text.index("### A4")]
    a4 = text[text.index("### A4") : text.index("### A5")]

    assert "catalog art direction, not a psychophysical law" in a2
    assert "shares a functional form, not every parameter" in a3
    assert "catalog art direction, not a psychophysical law" in a4


def test_rationale_keeps_a2_judgment_out_of_evidence() -> None:
    """Treat the muddy review as design history unless a protocol exists."""
    text = _page("docs/color_system/design-rationale.md")
    a2 = text[text.index("### A2") : text.index("### A3")]
    evidence = a2[a2.index("Evidence.") : a2.index("Limits.")]

    assert "design history and judgment, not measured evidence" in a2
    assert "looked muddy" not in evidence


def test_rationale_keeps_a6_membership_in_implementation() -> None:
    """Do not present gray's stored parameters as benefit evidence."""
    text = _page("docs/color_system/design-rationale.md")
    a6 = text[text.index("### A6") : text.index("### A7")]
    implementation = a6[a6.index("Implementation.") : a6.index("Evidence.")]
    evidence = a6[a6.index("Evidence.") : a6.index("Limits.")]

    for phrase in ("small nonzero chroma", "not part of Octave"):
        assert phrase in implementation
        assert phrase not in evidence
    assert "No user-study or task-performance protocol" in evidence


def test_rationale_documents_fixed_spacing_and_near_neutral_gray() -> None:
    """State the only shipped A5 policy and the deliberate A6 tint."""
    text = _page("docs/color_system/design-rationale.md")
    a5 = text[text.index("### A5") : text.index("### A6")]
    a6 = text[text.index("### A6") : text.index("### A7")]

    assert (
        "only shipped placement policy is fixed `ΔEOK` arc-length equalization"
    ) in a5
    assert "no public `ease`, `exp`, `log`, or spacing-warp option" in a5
    assert "near-neutral, with a deliberate cool tint" in a6
    assert "not perfectly achromatic" in a6


def test_rationale_scopes_current_release_gates_and_cvd_pipeline() -> None:
    """Describe per-asset gates, historical floors, and the pinned CVD path."""
    raw = (ROOT / "docs/color_system/design-rationale.md").read_text(
        encoding="utf-8"
    )
    text = re.sub(r"\s+", " ", raw)
    a7 = text[text.index("### A7") : text.index("### A8")]
    raw_a7 = raw[raw.index("### A7") : raw.index("### A8")]
    table = "\n".join(
        line for line in raw_a7.splitlines() if line.startswith("|")
    )

    for phrase in (
        "per-asset frozen-baseline non-regression checks",
        "historical Octave search criteria",
        "not universal categorical minima",
        "nominal sRGB",
        "full-severity",
        "clamp",
        "re-encode",
        "catalog's 8-bit hex quantization convention",
        "CIELAB",
        "CIEDE2000",
        "WCAG remains outside the color-authority compile-gate table",
    ):
        assert phrase in a7

    assert "WCAG" not in table


def test_rationale_rejects_current_shared_10_8_gate_wording() -> None:
    """Keep the 10/8 floors historical everywhere, not only inside A7."""
    text = _page("docs/color_system/design-rationale.md")
    section = text[
        text.index("The CVD validation model") : text.index(
            "Octave Print is hue-parallel"
        )
    ]

    assert (
        "The common-CVD 10 and tritan 8 floors were historical Octave "
        "selection criteria, not current shared release gates."
    ) in section
    for stale_claim in (
        "The validation gate is tiered",
        "common deficiencies are held to ≥ 10",
    ):
        assert stale_claim not in text


def test_rationale_uses_topology_specific_colormap_ranges() -> None:
    """Keep A8 ranges independent of floors without implying comparability."""
    text = _page("docs/color_system/design-rationale.md")
    a8 = text[text.index("### A8") : text.index("## Anatomy of a family")]

    for phrase in (
        "palette-floor-independent",
        "class- and scene-specific",
        "the same colormap, direction, and normalization",
        "identical limits or the same `Normalize` object",
    ):
        assert phrase in a8


def test_rationale_rejects_unbounded_generation_rule_claims() -> None:
    """Prevent retired APIs, shared ranges, and universal gate claims."""
    text = _page("docs/color_system/design-rationale.md")
    prohibited = (
        "ease/exp/log remain available",
        "left open as a warp option",
        "shared, wider output range",
        "universal hue identity",
        "WCAG/ΔE00/CVD-validated seven-color cycle",
    )

    for phrase in prohibited:
        assert phrase not in text


@pytest.mark.parametrize(
    ("relpath", "phrase"),
    [
        (
            "docs/color_system/colors.md",
            "Use this page when you want to color one mark",
        ),
        (
            "docs/color_system/palettes.md",
            "Use this page when separate series or categories need distinct colors",
        ),
        (
            "docs/color_system/colormaps.md",
            "Use this page when numeric values should become colors",
        ),
        (
            "docs/color_system/color-class.md",
            "Most plots do not need the Color class",
        ),
    ],
    ids=("colors", "palettes", "colormaps", "color-class"),
)
def test_catalog_page_leads_with_user_task(relpath: str, phrase: str) -> None:
    assert phrase in _page(relpath)


def test_color_class_starts_with_optional_beginner_path() -> None:
    text = _page("docs/color_system/color-class.md")
    opening = (
        "# Color class Most plots do not need the Color class: a named token, "
        "palette, or colormap is usually enough."
    )
    quick_path = (
        "color = dm.oklch(0.7, 0.15, 150) "
        "color.oklch.C *= 1.2 "
        "hex_value = color.to_hex()"
    )

    assert text.startswith(opening)
    assert quick_path in text
    assert "`L` is the model's lightness coordinate" in text
    assert "`C` controls how colorful or muted the color is" in text
    assert "`h` chooses the hue angle" in text
    assert "not a promise that every equal distance looks exactly equal" in text


def test_color_class_explains_oklab_and_oklch_as_coordinate_views() -> None:
    text = _page("docs/color_system/color-class.md")
    explanation = (
        "OKLab and OKLCH are two coordinate views of the same underlying "
        "model, not two competing construction rules."
    )

    assert explanation in text
    assert "OKLab's `a` and `b` are rectangular map axes" in text
    assert "distance from the center `C` and angle `h`" in text
    assert text.index(explanation) < text.index("## Color object")


def test_color_class_keeps_custom_endpoint_caveat_as_technical_detail() -> None:
    text = _page("docs/color_system/color-class.md")
    detail = text.index(":::{dropdown} Technical detail")
    caveat = text.index(
        "arbitrary custom endpoints are not automatically gated"
    )
    validation = text.index("[Validation](validation.md)")

    assert detail < caveat < validation


def test_color_class_retains_advanced_reference_surfaces() -> None:
    text = _page("docs/color_system/color-class.md")
    for phrase in (
        "dm-constructor-widget",
        "dm-conv-widget",
        "dm-cmap-builder",
        "images/color_space_interpolation.svg",
        "### From OKLab coordinates",
        "### From OKLCH coordinates",
        "### From RGB values",
        "### From hex strings",
        "### From matplotlib color names",
        "### Using conversion methods",
        "### Using view objects (recommended)",
        "### Modifying color components",
        "### Copying colors",
        "color.oklab.L += 0.1",
        "brighter = color.copy()",
        "### Sequential colormaps",
        "### Diverging colormaps",
        "mpl.colormaps.register(cmap=cmap)",
        "## Quick reference",
        "## See also",
        "(../api/color.rst)",
    ):
        assert phrase in text


def test_palettes_explains_specialist_terms_at_first_local_use() -> None:
    text = _page("docs/color_system/palettes.md")
    for term, explanation in (
        ("OKLab", "OKLab and OKLCH are used to construct and adjust colors."),
        ("OKLCH", "OKLab and OKLCH are used to construct and adjust colors."),
        (
            "ΔEOK",
            "ΔEOK is a color-distance ruler: larger means more different.",
        ),
        ("relative_y", MODELED_Y_FIRST_USE),
        ("CIELAB", "CIELAB supplies coordinates for CIEDE2000 distance."),
        ("ΔE00", "CIEDE2000 distance is reported as ΔE00."),
        (
            "CVD",
            "Color-vision deficiency (CVD) simulations are named models used "
            "to diagnose potential color collisions, not observer "
            "guarantees.",
        ),
        (
            "WCAG",
            "Web Content Accessibility Guidelines (WCAG) check pair-specific "
            "text contrast for a named foreground/background pair; this is "
            "not palette certification.",
        ),
    ):
        _assert_first_use_is_explained(text, term, explanation)


def test_colormaps_explains_specialist_terms_at_first_local_use() -> None:
    text = _page("docs/color_system/colormaps.md")
    for term, explanation in (
        ("LUT", "256-entry lookup table (LUT)"),
        ("CVD", "color-vision deficiency (CVD)"),
        ("ΔE00", "CIEDE2000 distance is reported as ΔE00"),
        (
            "Model B",
            "Model B is the internal name for the shipped colormap-family catalog",
        ),
        ("OKLab", "OKLab and OKLCH are used to construct and adjust colors."),
        ("OKLCH", "OKLab and OKLCH are used to construct and adjust colors."),
        ("relative_y", MODELED_Y_FIRST_USE),
        ("CIELAB", "CIELAB supplies coordinates for CIEDE2000 distance."),
        (
            "WCAG",
            "Web Content Accessibility Guidelines (WCAG) check pair-specific "
            "text contrast for a named foreground/background pair; this is "
            "not palette certification.",
        ),
        (
            "topology gate",
            "A topology gate is an internal pass/fail check for a map's required "
            "ordering or endpoint structure.",
        ),
    ):
        _assert_first_use_is_explained(text, term, explanation)

    modeled_y = (
        "Modeled relative CIE Y (`relative_y`) is calculated from nominal D65 "
        "sRGB"
    )
    assert modeled_y in text
    assert text.index(modeled_y) < text.index("modeled-relative-Y ordering")
    assert "`dm.list_colors()` returns the 56 Model B family records" in text


@pytest.mark.parametrize(
    ("relpath", "titles"),
    [
        (
            "docs/color_system/palettes.md",
            ("Technical terms", "Technical detail"),
        ),
        ("docs/color_system/colormaps.md", ("Technical detail",)),
        ("docs/color_system/color-class.md", ("Technical detail",)),
    ],
    ids=("palettes", "colormaps", "color-class"),
)
def test_technical_callouts_use_semantic_dropdown_directives(
    relpath: str, titles: tuple[str, ...]
) -> None:
    text = (ROOT / relpath).read_text(encoding="utf-8")

    for title in titles:
        assert f":::{{dropdown}} {title}" in text
    assert ":class: dropdown" not in text


def test_typography_matrix_has_responsive_wrapper_in_source_and_artifact() -> (
    None
):
    wrapper = '<div id="dm-typography-matrix" class="yue table-wrapper">'

    for relpath in (
        "docs/_static/scripts/build_typography_matrix.py",
        "docs/_static/typography_matrix.html",
    ):
        text = (ROOT / relpath).read_text(encoding="utf-8")
        assert wrapper in text, relpath


def test_validation_explains_maintainer_terms() -> None:
    text = _page("docs/color_system/validation.md")
    for phrase in (
        "This page is for release maintainers",
        "Open `index.html` for human review",
        "`report.json` is the machine-readable gate record",
        "use the comparator process exit code to decide whether the step passed",
        "A 256-stop lookup table",
        "In the compatibility list, a surface is one public group being compared",
        "lower step CV means more even neighboring steps",
        "last-write completion marker",
    ):
        assert phrase in text
    assert "generation commit marker" not in text
    assert "`report.json` is the machine authority" not in text
    assert "Automation reads `report.json`" not in text


def test_validation_distinguishes_report_completion_from_green_result() -> None:
    text = _page("docs/color_system/validation.md")
    marker = text.index("last-write completion marker")
    completed = text.index(
        "The marker means that report generation completed successfully"
    )
    not_green = text.index("it does not mean that all gates passed")
    both_reports = text.index("Both exit codes `0` and `1` write `report.json`")
    not_current = text.index(
        "does not by itself prove that an arbitrary current invocation completed"
    )
    parsing = text.index(
        "Argument parsing happens before the selected output path is available"
    )
    green = text.index(
        "A green validation result requires `passed` to be `true` and the "
        "process exit code to be `0`"
    )

    assert marker < completed < not_green < both_reports < not_current
    assert not_current < parsing < green


def test_usage_guide_accessibility_terms_include_meaning() -> None:
    text = _page("docs/usage_guide/colors.md")
    for phrase in (
        "color-vision deficiency (CVD)",
        "Web Content Accessibility Guidelines (WCAG)",
        "ΔEOK is a color-distance ruler: larger means more different",
        "not a guarantee for every individual observer",
    ):
        assert phrase in text
