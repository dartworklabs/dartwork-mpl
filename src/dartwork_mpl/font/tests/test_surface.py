"""The bundled fonts through the public surface: what a preset names is shipped,
licensed, and drawn; matplotlib's intended weight misses stay quiet."""

import logging
import warnings
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pytest
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties

import dartwork_mpl as dm

FONT_DIR = dm.font.get_font_dir()
NOT_BUNDLED = {"sans-serif", "monospace", "STIXGeneral"}  # matplotlib's own
LICENSES = {  # file-name prefix -> licence text that covers it
    "Roboto-": "Roboto", "RobotoMono-": "RobotoMono", "Inter-": "Inter",
    "Paperlogy-": "Paperlogy", "Pretendard-": "Pretendard",
    "NotoSansCJK": "NotoSansCJK", "NotoSansMath-": "NotoSans",
    "NotoSansSymbols": "NotoSans", "D2Coding-": "D2Coding",
    "JetBrainsMono-": "JetBrainsMono", "IBMPlexMono-": "IBMPlex",
    "SourceCodePro-": "SourceCodePro",
}  # fmt: skip


def _named_families() -> set[str]:
    names = set()
    for preset in dm.style.presets:
        with dm.style.context(preset):
            rc = mpl.rcParams
            names |= {*rc["font.family"], *rc["font.monospace"]}
            names |= {
                rc[f"mathtext.{k}"].split(":")[0]
                for k in ("rm", "it", "bf", "sf", "tt", "cal")
            }
    return names - NOT_BUNDLED


def test_every_family_a_preset_names_is_bundled():
    for family in _named_families():
        path = font_manager.findfont(
            FontProperties(family=family), fallback_to_default=False
        )
        assert any(p.name == Path(path).name for p in FONT_DIR.iterdir()), (
            family
        )


def test_every_bundled_file_is_named_by_a_preset_and_licensed():
    families = _named_families()
    licenses = {
        p.stem.removeprefix("LICENSE-")
        for p in (FONT_DIR / "licenses").iterdir()
    }
    for path in FONT_DIR.glob("*.[ot]tf"):
        assert font_manager.get_font(path).family_name in families, path.name
        prefix = next(p for p in LICENSES if path.name.startswith(p))
        assert LICENSES[prefix] in licenses
    assert licenses == set(LICENSES.values())  # no orphan licence


@pytest.mark.parametrize(
    ("preset", "file"),
    [
        ("report-kr", "Paperlogy-2ExtraLight.ttf"),
        ("report", "Roboto-ExtraLight.ttf"),
    ],
)
def test_a_korean_chart_draws_every_glyph_in_the_bundled_face(preset, file):
    """A preset's "light" is matplotlib's 200: the ExtraLight file."""
    with dm.style.context(preset), warnings.catch_warnings():
        warnings.simplefilter("error")  # a missing glyph warns
        fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
        ax.plot([1, 2, 3], label="매출 (억원)")
        ax.set(title="분기별 매출 → 12.5% ± 3", xlabel="분기", ylabel="억원")
        ax.legend()
        fig.canvas.draw()
        plt.close(fig)
        found = font_manager.findfont(
            FontProperties(family=mpl.rcParams["font.family"][0])
        )
    assert Path(found) == FONT_DIR / file


def _emit(family: str, weight: str) -> list[str]:
    seen: list[str] = []
    handler = logging.Handler()
    handler.emit = lambda record: seen.append(record.getMessage())  # type: ignore[method-assign]
    logger = logging.getLogger("matplotlib.font_manager")
    logger.addHandler(handler)
    try:
        logger.warning(
            "findfont: Failed to find font weight %s for %s, now using %s.",
            weight,
            family,
            400,
        )
    finally:
        logger.removeHandler(handler)
    return seen


def test_the_preset_weight_miss_on_a_math_font_is_quiet_and_others_log():
    with dm.style.context("scientific"):
        assert _emit("STIXGeneral", "light") == []
        assert _emit("Roboto", "light")
