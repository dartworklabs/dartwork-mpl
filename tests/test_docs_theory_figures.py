"""Pin the theory-figure generator and its tracked output contract."""

import ast
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests._docs_color_oracles import chroma_r_squared

_ROOT = Path(__file__).resolve().parents[1]
_GENERATOR = _ROOT / "docs" / "color_system" / "generate_theory_figures.py"
_THEORY = _GENERATOR.parent / "theory_figures"
_ASSET_SUFFIXES = frozenset({".html", ".svg"})


def _theory_assets() -> tuple[Path, ...]:
    """Return every existing tracked theory SVG/HTML in filename order."""
    result = subprocess.run(
        ["git", "ls-files", "--", str(_THEORY.relative_to(_ROOT))],
        cwd=_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return tuple(
        sorted(
            _ROOT / relative
            for relative in result.stdout.splitlines()
            if (_ROOT / relative).is_file()
            and (_ROOT / relative).suffix in _ASSET_SUFFIXES
        )
    )


def _generator_contract_violations() -> tuple[str, ...]:
    """Return static violations that make running the generator unsafe."""
    source = _GENERATOR.read_text(encoding="utf-8")
    strings = {
        node.value
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    violations: list[str] = []
    if "/private/tmp" in source:
        violations.append("personal /private/tmp preview path is forbidden")
    if "--output-dir" not in strings:
        violations.append("missing generator-relative --output-dir")
    if "--check" not in strings:
        violations.append("missing non-writing --check mode")
    return tuple(violations)


def _require_hermetic_generator() -> None:
    """Skip behavioral checks until the unsafe legacy CLI is removed."""
    violations = _generator_contract_violations()
    if violations:
        pytest.skip("; ".join(violations))


def _run_generator(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run the real theory generator against the source checkout."""
    env = os.environ.copy()
    source_path = str(_ROOT / "src")
    prior_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{source_path}{os.pathsep}{prior_pythonpath}"
        if prior_pythonpath
        else source_path
    )
    return subprocess.run(
        [sys.executable, str(_GENERATOR), *args],
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def _asset_state() -> dict[str, tuple[bytes, int]]:
    """Capture content and modification time for every theory asset."""
    return {
        path.name: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in _theory_assets()
    }


def _normalized_labels(text: str) -> str:
    """Normalize punctuation and multiline Matplotlib SVG labels."""
    # With ``svg.fonttype = "path"``, Matplotlib emits each visual line as a
    # separate XML comment with glyph paths between the comments. Add the
    # comments in document order so a two-line label remains searchable as
    # one phrase without weakening the assertion to disconnected words.
    comments = " ".join(re.findall(r"<!--(.*?)-->", text, flags=re.DOTALL))
    normalized = (
        f"{text} {comments}".lower().replace("_", " ").replace("-", " ")
    )
    for codepoint in range(0x2010, 0x2016):
        normalized = normalized.replace(chr(codepoint), " ")
    return " ".join(normalized.split())


def test_theory_svgs_have_no_embedded_date() -> None:
    """Keep committed SVG metadata free of wall-clock timestamps."""
    svgs = sorted(_THEORY.glob("theory_*.svg"))
    assert svgs, "no theory-figure SVGs found"
    dated = [
        path.name
        for path in svgs
        if "<dc:date" in path.read_text(encoding="utf-8")
    ]
    assert not dated, f"non-deterministic theory SVGs: {dated}"


def test_theory_generator_has_hermetic_cli() -> None:
    """Require relative output control and remove the personal preview."""
    violations = _generator_contract_violations()
    assert not violations, "\n".join(violations)


def test_theory_chroma_generator_has_no_stale_claims() -> None:
    """Keep the chroma fit and family-parameter labels catalog-derived."""
    source = _GENERATOR.read_text(encoding="utf-8")
    assert "R²=0.945" not in source
    assert "only {TP} varies" not in source
    assert "warp is opt-in" not in source
    assert "In-sample R²={r_squared:.3f}" in source
    assert not re.search(r"In-sample R²=\d", source)


def test_theory_generator_uses_bounded_modeled_labels() -> None:
    """Pin model-scoped source labels and reject every retired variant."""
    source = _GENERATOR.read_text(encoding="utf-8")
    folded = " ".join(source.casefold().split())

    required = (
        "modeled relative CIE Y from nominal D65 sRGB",
        "modeled relative Y",
        "authored hue-specific dark endpoint",
        "Design rule A3",
        "Design rule A4",
        "authored catalog drift",
        "authored cyan minimum",
        "unsimulated nominal sRGB",
        "named deutan simulation",
        "above historical\\nsearch criterion",
        "below historical\\nsearch criterion",
        "historical Octave search criterion 10",
        "not a current shared gate",
        "Model-specific CIEDE2000 regression diagnostic",
    )
    for label in required:
        assert label in source

    retired = (
        "physical-relative-y",
        "physical relative y",
        "physical-y",
        "physical y",
        "only as dark as the hue survives",
        "axiom a3",
        "axiom a4",
        "warm hues rotate like flame",
        "srgb is stingy with cyan",
        "normal vision",
        "two clearly different colors",
        "looks safe",
        "correctly\\nfails",
        "gate threshold 10",
    )
    for label in retired:
        assert label not in folded


def test_theory_spacing_generator_names_the_only_shipped_policy() -> None:
    """Keep the A5 source label fixed and free of an advertised warp API."""
    source = _GENERATOR.read_text(encoding="utf-8")
    spacing = source[
        source.index("def fig_spacing") : source.index("def fig_metric")
    ]

    assert "A5 — step spacing: fixed ΔEOK arc-length equalization" in spacing
    assert "Axiom A5" not in spacing
    assert "warp" not in spacing.lower()


def test_theory_spacing_figure_names_the_only_shipped_policy() -> None:
    """Expose a stale rendered A5 label until generator-only regeneration."""
    path = _THEORY / "theory_5_spacing.svg"
    labels = _normalized_labels(path.read_text(encoding="utf-8"))

    assert "a5 step spacing: fixed δeok arc length equalization" in labels
    assert "warp is opt in" not in labels


def test_theory_chroma_figure_has_catalog_derived_labels() -> None:
    """Render the independently checked fit and truthful A3 parameter label."""
    path = _THEORY / "theory_4_chroma.svg"
    labels = _normalized_labels(path.read_text(encoding="utf-8"))
    match = re.search(r"in sample r²=(\d\.\d{3})", labels)

    assert match, f"{path}: missing rendered in-sample R² label"
    assert round(float(match.group(1)), 3) == round(chroma_r_squared(), 3)
    assert "family parameters vary" in labels


@pytest.mark.parametrize(
    ("name", "required", "retired"),
    [
        (
            "theory_1_lightness_weber.svg",
            (
                "modeled relative cie y from nominal d65 srgb",
                "even modeled relative y steps",
            ),
            ("physical relative y",),
        ),
        (
            "theory_2_floor.svg",
            ("authored hue specific dark endpoint", "modeled relative y"),
            ("only as dark as the hue survives", "physical relative y"),
        ),
        (
            "theory_3_drift.svg",
            ("design rule a4", "authored catalog drift"),
            ("axiom a4", "warm hues rotate like flame"),
        ),
        (
            "theory_4_chroma.svg",
            ("design rule a3", "authored cyan minimum"),
            ("axiom a3", "srgb is stingy with cyan"),
        ),
        (
            "theory_6_metric.svg",
            (
                "unsimulated nominal srgb",
                "above historical search criterion",
                "below historical search criterion",
                "not a current shared gate",
                "model specific ciede2000 regression diagnostic",
            ),
            (
                "normal vision",
                "two clearly different colors",
                "looks safe",
                "correctly fails",
                "gate threshold 10",
            ),
        ),
        (
            "theory_7_dcseq.svg",
            ("modeled relative y",),
            ("physical relative y",),
        ),
        (
            "theory_8_anatomy.svg",
            ("modeled relative y",),
            ("physical relative y",),
        ),
    ],
    ids=(
        "theory-1",
        "theory-2",
        "theory-3",
        "theory-4",
        "theory-6",
        "theory-7",
        "theory-8",
    ),
)
def test_theory_figure_labels_are_bounded_and_modeled(
    name: str, required: tuple[str, ...], retired: tuple[str, ...]
) -> None:
    """Keep tracked figure labels aligned with the bounded generator copy."""
    path = _THEORY / name
    labels = _normalized_labels(path.read_text(encoding="utf-8"))
    missing = [label for label in required if label not in labels]
    stale = [label for label in retired if label in labels]

    assert not missing and not stale, (
        f"{path}: missing bounded labels {missing}; retired labels {stale}"
    )


def test_theory_catalog_names_every_public_family() -> None:
    """Show all 20 single-hue and all 13 qualitative families."""
    from dartwork_mpl._colors._curated import CURATED_QUALITATIVE_ORDER
    from dartwork_mpl._colors._generated import CYCLES
    from dartwork_mpl._colors._recipe import FAMILIES

    single_hue = (*FAMILIES, "gray")
    qualitative = (*CURATED_QUALITATIVE_ORDER, *CYCLES)
    assert len(single_hue) == 20
    assert len(qualitative) == 13

    catalog_assets = sorted(_THEORY.glob("theory_9_*.svg"))
    assert len(catalog_assets) == 1
    catalog = catalog_assets[0].read_text(encoding="utf-8")
    missing_single = [
        name for name in single_hue if f"<!-- {name} -->" not in catalog
    ]
    missing_qualitative = [
        name for name in qualitative if f"<!-- {name} -->" not in catalog
    ]
    assert not missing_single, f"missing single-hue families: {missing_single}"
    assert not missing_qualitative, (
        f"missing qualitative families: {missing_qualitative}"
    )
    assert "Single-hue 20" in catalog
    assert "Qualitative 13" in catalog


def test_theory_labels_use_the_accepted_metric_split() -> None:
    """Label construction with tone, modeled Y, and actual OKLab L."""
    rendered = "\n".join(
        path.read_text(encoding="utf-8") for path in _theory_assets()
    )
    labels = _normalized_labels(rendered)
    required = ("neutral tone", "modeled relative y", "actual oklab l")
    missing = [label for label in required if label not in labels]
    assert not missing, f"missing accepted-model labels: {missing}"

    stale_construction_claims = (
        "why the lightness axis is cielab l*",
        "even steps in cielab l*",
        "cielab l* (lightness)",
        "wide l* range",
        "l* (blue)",
    )
    stale = [claim for claim in stale_construction_claims if claim in labels]
    assert not stale, f"stale construction Lab-L claims: {stale}"
    assert "physical relative y" not in labels


def test_theory_generator_renders_every_asset_byte_identically(
    tmp_path: Path,
) -> None:
    """Render to a caller-owned directory with tracked byte parity."""
    _require_hermetic_generator()
    output_dir = tmp_path / "rendered"

    result = _run_generator("--output-dir", str(output_dir), cwd=tmp_path)

    assert result.returncode == 0, result.stderr or result.stdout
    expected = {path.name: path.read_bytes() for path in _theory_assets()}
    generated_paths = tuple(
        sorted(path for path in output_dir.iterdir() if path.is_file())
    )
    generated = {path.name: path.read_bytes() for path in generated_paths}
    assert generated == expected


def test_theory_generator_check_is_nonwriting_and_fresh(tmp_path: Path) -> None:
    """Check every tracked asset from any cwd without touching it."""
    _require_hermetic_generator()
    before = _asset_state()

    result = _run_generator("--check", cwd=tmp_path)

    assert result.returncode == 0, result.stderr or result.stdout
    assert _asset_state() == before
