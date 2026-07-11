"""Measured font-system invariants for the typography registry."""

# ruff: noqa: RUF001

from __future__ import annotations

import io
import re
import runpy
import warnings
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

import dartwork_mpl as dm
from dartwork_mpl import font

matplotlib.use("Agg")  # headless-safe; must precede any figure creation

_REPO = Path(__file__).resolve().parents[1]
_BASE_MPLSTYLE = (
    _REPO / "src" / "dartwork_mpl" / "asset" / "mplstyle" / "base.mplstyle"
)
_TYPOGRAPHY_MATRIX_BUILDER = (
    _REPO / "docs" / "_static" / "scripts" / "build_typography_matrix.py"
)
_TYPOGRAPHY_MATRIX = _REPO / "docs" / "_static" / "typography_matrix.html"
_FONT_DOCS = _REPO / "docs" / "fonts"
_FONT_ASSETS = _REPO / "src" / "dartwork_mpl" / "asset" / "font"
_FONT_LICENSES = _FONT_ASSETS / "licenses"
_GRID_WEIGHTS = frozenset(range(100, 1000, 100))
_LICENSES = {"Apache-2.0", "OFL-1.1"}
_RESOLVER_PROBES = tuple("−×±→°μσΔ") + tuple("0123456789") + ("한",)
_BASE_CHAIN = (
    "Roboto",
    "Inter",
    "Paperlogy",
    "Noto Sans CJK KR",
    "Pretendard",
    "Noto Sans Math",
    "Noto Sans Symbols",
    "Noto Sans Symbols 2",
    "sans-serif",
)
_RESOLVER_GOLDEN = {
    "−": "Roboto",
    "×": "Roboto",
    "±": "Roboto",
    "→": "Inter",
    "°": "Roboto",
    "μ": "Roboto",
    "σ": "Roboto",
    "Δ": "Roboto",
    "0": "Roboto",
    "1": "Roboto",
    "2": "Roboto",
    "3": "Roboto",
    "4": "Roboto",
    "5": "Roboto",
    "6": "Roboto",
    "7": "Roboto",
    "8": "Roboto",
    "9": "Roboto",
    "한": "Paperlogy",
}


def _base_font_family_chain() -> tuple[str, ...]:
    for line in _BASE_MPLSTYLE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("font.family:"):
            return tuple(
                item.strip()
                for item in stripped.partition(":")[2].split(",")
                if item.strip()
            )
    raise AssertionError("font.family not found in base.mplstyle")


def test_registry_matches_registered_matplotlib_families() -> None:
    registered = set(font.list_registered())
    registry = font.font_families()

    assert len(registry) == 20
    assert set(registry) == registered
    assert set(font.FONTS) == registered
    for family in registry.values():
        assert family.name in registered
        assert family.job.endswith(".")


def test_serif_families_cross_reference_each_other() -> None:
    registry = font.font_families()
    serif_families = ("Source Serif 4", "Noto Serif", "IBM Plex Serif")

    for family in serif_families:
        assert registry[family].alternates == tuple(
            alternate for alternate in serif_families if alternate != family
        )


def test_os2_weights_are_grid_values_or_named_exceptions() -> None:
    unexpected: list[tuple[str, str, int]] = []
    for family, record in font.font_families().items():
        exceptions = set(record.weight_exceptions)
        if exceptions:
            assert record.quirks, family
        for face in font._measure(family).files:
            if face.weight in _GRID_WEIGHTS:
                continue
            if face.weight not in exceptions:
                unexpected.append((family, face.file, face.weight))

    assert not unexpected


def test_numeric_axis_recommendation_requires_default_digits_or_fixed_width() -> (
    None
):
    numeric_false = set()
    for family, record in font.font_families().items():
        measurement = font._measure(family)
        measured_numeric = (
            measurement.default_digit_widths_uniform or measurement.fixed_pitch
        )
        assert record.numeric_axes is measured_numeric
        if record.numeric_axes:
            assert (
                measurement.default_digit_widths_uniform
                or measurement.fixed_pitch
            )
        else:
            numeric_false.add(family)

    assert numeric_false == {"Inter", "Inter Display", "Pretendard"}


def test_numeric_axis_flips_and_tnum_available_are_pinned() -> None:
    expected = {
        "Inter": (False, True),
        "Pretendard": (False, True),
        "IBM Plex Sans": (True, False),
        "Source Sans 3": (True, False),
        "Paperlogy": (True, False),
    }

    for family, (numeric_axes, tnum_available) in expected.items():
        record = font.font_families()[family]
        measurement = font._measure(family)
        assert record.numeric_axes is numeric_axes
        assert record.tnum_available is tnum_available
        assert measurement.tnum_available is tnum_available


def test_base_chain_chart_glyph_resolver_is_pinned() -> None:
    chain = _base_font_family_chain()
    assert chain == _BASE_CHAIN

    resolved: dict[str, str] = {}
    for char in _RESOLVER_PROBES:
        for family in chain:
            assert family != "sans-serif", f"{char!r} fell through to DejaVu"
            if ord(char) in font._family_codepoints(family):
                resolved[char] = family
                break

    assert resolved == _RESOLVER_GOLDEN


def test_every_file_license_is_allowed() -> None:
    for family in font.font_families():
        measurement = font._measure(family)
        assert set(measurement.licenses) <= _LICENSES
        for face in measurement.files:
            assert face.license in _LICENSES


def test_registry_flags_match_measured_truth() -> None:
    for family, record in font.font_families().items():
        measurement = font._measure(family)
        assert record.hangul is measurement.hangul
        assert record.italic is measurement.italic
        assert record.mono is measurement.fixed_pitch


def test_measurement_is_deterministic() -> None:
    first = {family: font._measure(family) for family in font.font_families()}
    second = {family: font._measure(family) for family in font.font_families()}

    assert first == second


def test_bundled_registration_is_idempotent() -> None:
    font._add_fonts()
    font._measure.cache_clear()

    assert len(font._measure("Roboto").files) == 18
    assert len(font._measure("Roboto Mono").files) == 14
    assert (
        sum(len(font._measure(family).files) for family in font.font_families())
        == 262
    )


def test_typography_matrix_matches_builder() -> None:
    built = runpy.run_path(str(_TYPOGRAPHY_MATRIX_BUILDER))["build"]()
    committed = _TYPOGRAPHY_MATRIX.read_text(encoding="utf-8")

    assert built == committed
    assert "<style" not in committed
    assert committed.count("<tr><td>") == 20


def test_docs_font_counts_match_reality() -> None:
    font_files = sorted(
        path
        for path in _FONT_ASSETS.iterdir()
        if path.suffix.lower() in {".ttf", ".otf"}
    )
    actual = {
        "text font files": len(font_files),
        "documented file groups": len(
            {path.stem.split("-", 1)[0] for path in font_files}
        ),
        "matplotlib family names": len(font.list_registered()),
    }

    for doc_name in ("index.md", "families.md"):
        text = (_FONT_DOCS / doc_name).read_text(encoding="utf-8")
        for label, count in actual.items():
            label_pattern = re.escape(label).replace(r"\ ", r"\s+")
            match = re.search(
                rf"\*\*(\d+)\s+{label_pattern}\*\*", text, re.DOTALL
            )
            assert match is not None, (doc_name, label)
            assert int(match.group(1)) == count, (doc_name, label)

    utilities = (_FONT_DOCS / "utilities.md").read_text(encoding="utf-8")
    bundled = re.search(r"all\s+(\d+)\s+bundled fonts", utilities)
    assert bundled is not None
    assert int(bundled.group(1)) == actual["text font files"]


def test_completed_font_corpus_is_pinned() -> None:
    font_files = tuple(
        path
        for path in _FONT_ASSETS.iterdir()
        if path.suffix.lower() in {".ttf", ".otf"}
    )
    roboto = font._measure("Roboto")
    roboto_mono = font._measure("Roboto Mono")
    noto_serif = font._measure("Noto Serif")
    ibm_plex_serif = font._measure("IBM Plex Serif")

    assert len(font_files) == 262
    assert len(roboto.files) == 18
    assert roboto.weights == tuple(range(100, 1000, 100))
    assert roboto.licenses == ("OFL-1.1",)
    assert len(roboto_mono.files) == 14
    assert roboto_mono.weights == tuple(range(100, 800, 100))
    assert roboto_mono.licenses == ("OFL-1.1",)
    assert len(noto_serif.files) == 18
    assert noto_serif.weights == tuple(range(100, 1000, 100))
    assert noto_serif.italic is True
    assert noto_serif.licenses == ("OFL-1.1",)
    assert len(ibm_plex_serif.files) == 14
    assert ibm_plex_serif.weights == tuple(range(100, 800, 100))
    assert ibm_plex_serif.italic is True
    assert ibm_plex_serif.licenses == ("OFL-1.1",)
    assert (_FONT_LICENSES / "LICENSE-NotoSerif.txt").is_file()


def test_every_family_has_license_file() -> None:
    license_by_group = {
        "Roboto": "LICENSE-Roboto.txt",
        "RobotoMono": "LICENSE-RobotoMono.txt",
        "Inter": "LICENSE-Inter.txt",
        "InterDisplay": "LICENSE-Inter.txt",
        "IBMPlexSans": "LICENSE-IBMPlex.txt",
        "IBMPlexMono": "LICENSE-IBMPlex.txt",
        "IBMPlexSerif": "LICENSE-IBMPlex.txt",
        "SourceSans3": "LICENSE-SourceSans3.txt",
        "SourceSerif4": "LICENSE-SourceSerif4.txt",
        "NotoSerif": "LICENSE-NotoSerif.txt",
        "SourceCodePro": "LICENSE-SourceCodePro.txt",
        "JetBrainsMono": "LICENSE-JetBrainsMono.txt",
        "NotoSans": "LICENSE-NotoSans.txt",
        "NotoSans_Condensed": "LICENSE-NotoSans.txt",
        "NotoSans_SemiCondensed": "LICENSE-NotoSans.txt",
        "NotoSansCJK": "LICENSE-NotoSansCJK.txt",
        "NotoSansMath": "LICENSE-NotoSans.txt",
        "NotoSansSymbols": "LICENSE-NotoSans.txt",
        "NotoSansSymbols2": "LICENSE-NotoSans.txt",
        "Paperlogy": "LICENSE-Paperlogy.txt",
        "Pretendard": "LICENSE-Pretendard.txt",
        "D2Coding": "LICENSE-D2Coding.txt",
    }
    disk_groups = {
        path.stem.split("-", 1)[0]
        for path in _FONT_ASSETS.iterdir()
        if path.suffix.lower() in {".ttf", ".otf"}
    }
    disk_licenses = {
        path.name for path in _FONT_LICENSES.iterdir() if path.is_file()
    }

    assert set(license_by_group) == disk_groups
    assert set(license_by_group.values()) == disk_licenses
    assert all(
        (_FONT_LICENSES / name).is_file() for name in license_by_group.values()
    )


# --- P0-1 mathtext coherence gate ---------------------------------------
# The custom mathtext fontset in base.mplstyle matches the body family, so a
# math segment must NOT leak matplotlib's DejaVu default. Render the label
# to an SVG with the glyphs kept as text (svg.fonttype: none) so the
# font-family attributes are inspectable, then assert no DejaVu leaks and the
# body family shows up. `mathtext.default: regular` makes bare mathtext use
# the body face, so scientific renders R/m/digits in Roboto and report-kr
# renders them in Paperlogy while the Greek falls to STIX (never DejaVu).
_MATH_LABEL = r"$R^2 \mu m 10^3$"


def _math_svg_font_families(preset: str) -> tuple[list[str], list[str]]:
    """Render the math label under ``preset`` into a text-embedded SVG.

    Returns the SVG's ``font-family`` attribute values and any matplotlib
    "missing from font" (tofu) warning messages.
    """
    dm.style.use(preset)
    plt.rcParams["svg.fonttype"] = "none"
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    try:
        ax.text(0.5, 0.5, _MATH_LABEL, ha="center", va="center")
        buf = io.BytesIO()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            fig.savefig(buf, format="svg")
    finally:
        plt.close(fig)
    svg = buf.getvalue().decode("utf-8")
    families = re.findall(r"font-family:\s*([^;\"]+)", svg)
    missing = [
        str(w.message) for w in caught if "missing from font" in str(w.message)
    ]
    return families, missing


def test_mathtext_scientific_matches_body_without_dejavu() -> None:
    families, missing = _math_svg_font_families("scientific")
    assert families, "no font-family attributes in the SVG"
    assert all("DejaVu" not in value for value in families), (
        f"mathtext leaked DejaVu under 'scientific': {families}"
    )
    assert any("Roboto" in value for value in families), (
        f"body family Roboto absent from mathtext SVG: {families}"
    )
    assert not missing, f"tofu warnings under 'scientific': {missing}"


def test_mathtext_kr_stays_latin_without_dejavu() -> None:
    families, missing = _math_svg_font_families("report-kr")
    assert families, "no font-family attributes in the SVG"
    assert all("DejaVu" not in value for value in families), (
        f"mathtext leaked DejaVu under 'report-kr': {families}"
    )
    assert any("Paperlogy" in value for value in families), (
        f"body family Paperlogy absent from mathtext SVG: {families}"
    )
    assert not missing, f"tofu warnings under 'report-kr': {missing}"
