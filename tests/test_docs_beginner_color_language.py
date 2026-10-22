"""Guard misleading color claims and behavior-bearing documentation markup."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


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


RUNTIME_COLOR_LANGUAGE_PATHS = (
    "src/dartwork_mpl/_colors/_comparison.py",
    "src/dartwork_mpl/_colors/_curated.py",
    "src/dartwork_mpl/mcp/prompts.py",
    "src/dartwork_mpl/mcp/resources.py",
    "src/dartwork_mpl/mcp/tools.py",
    # The bodies the three MCP wiring tables delegate to (ADR 0005 M3-M6).
    "src/dartwork_mpl/mcp/catalog/discovery.py",
    "src/dartwork_mpl/mcp/catalog/fonts.py",
    "src/dartwork_mpl/mcp/catalog/info.py",
    "src/dartwork_mpl/mcp/colors/lookup.py",
    "src/dartwork_mpl/mcp/docs_fetch/raw_github.py",
    "src/dartwork_mpl/mcp/guides/api.py",
    "src/dartwork_mpl/mcp/guides/corpus.py",
    "src/dartwork_mpl/mcp/guides/prompts.py",
    "src/dartwork_mpl/mcp/lint/linter.py",
    "src/dartwork_mpl/mcp/plot_data/validate.py",
    "src/dartwork_mpl/mcp/plot_data/validators.py",
    "src/dartwork_mpl/mcp/recommend/chart_type.py",
    "src/dartwork_mpl/mcp/templates/bundled.py",
    "src/dartwork_mpl/mcp/templates/compose.py",
    "src/dartwork_mpl/mcp/templates/find.py",
    "src/dartwork_mpl/mcp/templates/render.py",
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
    """Read one documentation surface with whitespace normalized."""
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


@pytest.mark.parametrize(
    "relpath",
    (
        "docs/superpowers/specs/"
        "2026-07-14-oklab-centered-color-system-design.md",
        "docs/superpowers/plans/2026-07-14-oklab-centered-color-system.md",
    ),
    ids=("accepted-design", "active-plan"),
)
def test_normative_docs_reject_stale_report_authority_claims(
    relpath: str,
) -> None:
    """Reject instructions that infer current success from an old report."""
    text = _page(relpath)

    for stale_claim in (
        "CI는 JSON의 `passed`가 `true`인지 검사한다",
        "JSON이 자동화 SSOT다",
        "`report.json` as the machine authority",
    ):
        assert stale_claim not in text


def test_beginner_routes_avoid_undefined_internal_color_vocabulary() -> None:
    """Keep internal-only color terminology out of the beginner entry points."""
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


def test_rationale_rejects_output_and_accessibility_overclaims() -> None:
    """Reject claims that promote model diagnostics to output guarantees."""
    text = _page("docs/color_system/design-rationale.md")

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

    assert not re.search(pattern, text, re.I)


def test_rationale_limits_wcag_to_pairwise_contrast() -> None:
    """A WCAG ratio checks contrast and does not establish legibility."""
    text = _page("docs/color_system/design-rationale.md")

    assert "legibility for the tested pair" not in text


def test_rationale_rejects_universal_color_system_claims() -> None:
    """Keep shipped yellow observations from becoming universal claims."""
    text = _page("docs/color_system/design-rationale.md")

    assert "true of every color system" not in text


def test_rationale_rejects_observer_guarantees() -> None:
    """Reject claims that speak for every observer."""
    text = _page("docs/color_system/design-rationale.md")

    assert "clear colors in normal vision" not in text


def test_gamut_docs_reject_global_appearance_optimum_claims() -> None:
    """Reject perceptual-optimum and exact-appearance guarantees."""

    for relpath in (
        "docs/color_system/design-rationale.md",
        "docs/color_system/colormaps.md",
    ):
        text = _page(relpath)
        for stale_claim in (
            "Local-MINDE",
            "globally optimal",
            "preserves appearance exactly",
        ):
            assert stale_claim not in text, (
                f"{stale_claim!r} remains in {relpath}"
            )


def test_a1_rejects_unqualified_requested_lh_preservation() -> None:
    """Reject unbounded L/h preservation claims in the A1 contract."""
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
        "mapping holds the requested OKLCH `L` and `h` while reducing `C`"
        not in a1
    )


def test_colormap_docs_reject_universal_registered_reversal_claims() -> None:
    """Reject registered reversal claims that include qualitative maps."""

    for relpath in (
        "docs/color_system/design-rationale.md",
        "docs/color_system/colormaps.md",
    ):
        text = _page(relpath)
        for stale_claim in (
            "Reverse any map with `_r`",
            "Add `_r` to reverse any map",
        ):
            assert stale_claim not in text, (
                f"{stale_claim!r} remains in {relpath}"
            )


def test_colormap_hue_sources_are_not_limited_to_family_anchors() -> None:
    """Treat family anchors as identities and waypoints, not a closed set."""

    for relpath in (
        "docs/color_system/design-rationale.md",
        "docs/color_system/colormaps.md",
    ):
        text = _page(relpath)
        for stale_claim in (
            "only hue vocabulary",
            "chosen only at family anchors",
        ):
            assert stale_claim not in text, (
                f"{stale_claim!r} remains in {relpath}"
            )


def test_colormap_docs_reject_globally_shared_range_claims() -> None:
    """Reject claims that every map shares one comparable range."""

    for relpath in (
        "docs/color_system/design-rationale.md",
        "docs/color_system/colormaps.md",
    ):
        text = _page(relpath)
        for stale_claim in ("globally shared range", "one shared range"):
            assert stale_claim not in text, (
                f"{stale_claim!r} remains in {relpath}"
            )


def test_colormap_docs_reject_unqualified_robustness_claims() -> None:
    """Reject robustness guarantees inferred from modeled Y ordering."""
    text = _page("docs/color_system/colormaps.md")

    assert "which makes them robust" not in text


def test_colormap_docs_reject_universal_equalization_claims() -> None:
    """Reject equalization claims that apply one algorithm to every topology."""
    detailed_pages = (
        "docs/color_system/colormaps.md",
        "docs/color_system/design-rationale.md",
    )

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


def test_gray_docs_reject_universal_ladder_equalization_claims() -> None:
    """Keep the directly sampled gray ladder outside equalization claims."""
    for relpath in (
        "docs/color_system/palettes.md",
        "docs/_static/dartwork-discrete-palette-rationale.md",
    ):
        text = _page(relpath)
        assert "10 ΔEOK-equalized steps per family" not in text

    migration = _page("docs/migration.md")
    assert "20 families × 10 perceptually equalized" not in migration  # noqa: RUF001


def test_rationale_rejects_equalization_zeroing_every_metric() -> None:
    """Reject claims that equalizing one distance also zeros every ruler."""
    text = _page("docs/color_system/design-rationale.md")

    assert "drives every ruler to zero" not in text


def test_catalog_docs_reject_physical_relative_y_claims() -> None:
    """Reject descriptions of calculated relative Y as measured output."""
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
        assert not re.search(physical_pattern, text, re.I), relpath


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

    palettes = _page("docs/color_system/palettes.md")

    assert "Named-model color-vision diagnostics" not in palettes


def test_rationale_rejects_task_dependent_y_measurement_claims() -> None:
    """Keep task-dependent suitability distinct from measured map properties."""
    text = _page("docs/color_system/design-rationale.md")

    assert "Non-monotonic modeled relative Y is task-dependent" not in text


def test_rationale_rejects_universal_rendering_reproducibility() -> None:
    """Reject unconditional byte-reproducibility guarantees across machines."""
    text = _page("docs/color_system/design-rationale.md")

    assert "renders the same on every machine" not in text


def test_rationale_rejects_axiomatic_generation_wording() -> None:
    """Keep catalog design rules from becoming universal axioms."""
    text = _page("docs/color_system/design-rationale.md")

    assert "Each axiom answers" not in text


def test_rationale_keeps_a2_judgment_out_of_evidence() -> None:
    """Treat the muddy review as design history unless a protocol exists."""
    text = _page("docs/color_system/design-rationale.md")
    a2 = text[text.index("### A2") : text.index("### A3")]
    evidence = a2[a2.index("Evidence.") : a2.index("Limits.")]

    assert "looked muddy" not in evidence


def test_rationale_keeps_a6_membership_in_implementation() -> None:
    """Do not present gray's stored parameters as benefit evidence."""
    text = _page("docs/color_system/design-rationale.md")
    a6 = text[text.index("### A6") : text.index("### A7")]
    evidence = a6[a6.index("Evidence.") : a6.index("Limits.")]

    for phrase in ("small nonzero chroma", "not part of Octave"):
        assert phrase not in evidence


def test_color_authority_gate_table_excludes_wcag() -> None:
    """Keep WCAG pairwise contrast outside catalog construction gates."""
    raw = (ROOT / "docs/color_system/design-rationale.md").read_text(
        encoding="utf-8"
    )
    raw_a7 = raw[raw.index("### A7") : raw.index("### A8")]
    table = "\n".join(
        line for line in raw_a7.splitlines() if line.startswith("|")
    )

    assert "WCAG" not in table


def test_rationale_rejects_current_shared_10_8_gate_wording() -> None:
    """Keep the 10/8 floors historical everywhere, not only inside A7."""
    text = _page("docs/color_system/design-rationale.md")

    for stale_claim in (
        "The validation gate is tiered",
        "common deficiencies are held to ≥ 10",
    ):
        assert stale_claim not in text


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
    ("relpath", "minimum_callouts"),
    [
        ("docs/color_system/palettes.md", 2),
        ("docs/color_system/colormaps.md", 1),
        ("docs/color_system/color-class.md", 1),
    ],
    ids=("palettes", "colormaps", "color-class"),
)
def test_technical_callouts_use_semantic_dropdown_directives(
    relpath: str, minimum_callouts: int
) -> None:
    """Keep technical callouts on the semantic dropdown directive."""
    text = (ROOT / relpath).read_text(encoding="utf-8")
    assert text.count(":::{dropdown}") >= minimum_callouts
    assert ":class: dropdown" not in text


def test_typography_matrix_has_responsive_wrapper_in_source_and_artifact() -> (
    None
):
    """Keep generated typography tables in the same responsive wrapper."""
    wrapper = '<div id="dm-typography-matrix" class="yue table-wrapper">'

    for relpath in (
        "docs/_static/scripts/build_typography_matrix.py",
        "docs/_static/typography_matrix.html",
    ):
        text = (ROOT / relpath).read_text(encoding="utf-8")
        assert wrapper in text, relpath


def test_validation_docs_reject_stale_report_success_instructions() -> None:
    """Reject instructions that infer current success from report presence."""
    text = _page("docs/color_system/validation.md")
    assert "generation commit marker" not in text
    assert "`report.json` is the machine authority" not in text
    assert "Automation reads `report.json`" not in text
