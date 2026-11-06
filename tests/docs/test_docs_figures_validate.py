"""Every figure the docs generators draw passes the layout checks.

The colour-system, usage-guide, API and font-comparison generators
re-render their figures on every docs build (``docs/_ext/build_hooks.generate_gallery_assets``). In
November 2026 the ``presentation`` preset became ``scientific`` x 2.6, and
the generators that drew it on 10-17 cm canvases started publishing figures
whose labels ran over each other and off the canvas, with no test noticing.
This test runs those generators without writing a file: each figure is
checked with ``dm.validate_figure`` at the moment it would be saved, and any
OVERFLOW / overlap / clipped-text finding fails, so a preset or canvas
change cannot silently break the docs again.

A few figures show a defect on purpose (matplotlib's own output beside the
library's, the validator's OVERFLOW demonstration); each is listed in
``DEMONSTRATES`` with the checks it is allowed to trip and why.
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import matplotlib
import matplotlib.pyplot as plt
import pytest
from matplotlib.figure import Figure

import dartwork_mpl as dm

_DOCS = Path(__file__).resolve().parents[2] / "docs"
# The validator's checks for text that leaves the canvas or meets other text.
CHECKS = (
    "OVERFLOW",
    "CLIPPED_TEXT",
    "OVERLAP",
    "CROSS_AXES_OVERLAP",
    "LEGEND_OVERFLOW",
    "LEGEND_OVERLAP",
    "TICK_CROWD",
)
# Figures that show a problem on purpose: the checks each may trip.
DEMONSTRATES: dict[str, tuple[frozenset[str], str]] = {
    "validation_example": (
        frozenset({"OVERFLOW", "CLIPPED_TEXT"}),
        "save_export.md's OVERFLOW demonstration: a y label cut off",
    )
}


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def findings(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[dict[str, list[str]]]:
    """Each docs figure's findings, keyed by the name it is saved under.

    ``Figure.savefig`` is replaced for the run: it validates the figure and
    writes nothing (the name is the ``svg.hashsalt`` every generator sets
    per file, ``preset_compare_<preset>`` for the widget's panels).
    """
    found: dict[str, list[str]] = {}

    def check_instead_of_saving(
        fig: Figure, *args: object, **kwargs: object
    ) -> None:
        name = str(matplotlib.rcParams["svg.hashsalt"])
        warnings = dm.validate_figure(fig, checks=CHECKS, quiet=True)
        found[name] = [f"{w.check_id}: {w.message}" for w in warnings]

    paths = [str(_DOCS), str(_DOCS / "_static" / "scripts")]
    sys.path[:0] = paths
    mp = pytest.MonkeyPatch()
    mp.setattr(Figure, "savefig", check_instead_of_saving)
    try:
        with matplotlib.rc_context():
            usage = _load(
                "docs_usage_assets",
                _DOCS / "usage_guide" / "generate_assets.py",
            )
            colors = _load(
                "docs_color_assets",
                _DOCS / "color_system" / "generate_assets.py",
            )
            api = _load("docs_api_assets", _DOCS / "api" / "generate_assets.py")
            fonts = _load(
                "docs_font_comparison",
                _DOCS / "fonts" / "generate_comparison_assets.py",
            )
            tmp = tmp_path_factory.mktemp("docs-figures")  # widget HTML only
            colors.build_gallery_assets(base_dir=tmp)
            usage.build_usage_guide_assets(base_dir=tmp)
            api.build_api_assets(base_dir=tmp)
            fonts.generate_before_after()
            fonts.generate_chart_context()
        yield found
    finally:
        mp.undo()
        for path in paths:
            sys.path.remove(path)
        plt.close("all")
        dm.style.use("report")


# The figures the docs build publishes; each must be drawn and checked.
EXPECTED = {
    "color_space_creation",
    "color_space_conversion",
    "color_space_interpolation",
    "color_space_colormap_sequential",
    "color_space_colormap_diverging",
    "quickstart_first_figure",
    "quickstart_multi_panel",
    "layout_tight",
    "layout_simple",
    "layout_gridspec",
    "layout_typography",
    "label_axes_vanilla",
    "label_axes_dm",
    "set_decimal_vanilla",
    "set_decimal_dm",
    "arrow_axis_example",
    "validation_example",
    "save_scientific",
    "save_diverging_bar",
    "evolution_step1",
    "evolution_step2",
    "evolution_step3",
    "evolution_step4",
    "layout_example",
    "icon_example",
    "font_example",
    "xplot_example",
    "before_default",
    "after_dartwork",
    "chart_context",
    *(
        f"preset_compare_{preset}"
        for preset in (
            "scientific",
            "report",
            "presentation",
            "poster",
            "web",
            "minimal",
            "dark",
        )
    ),
}


def test_every_docs_figure_is_drawn(findings):
    missing = EXPECTED - set(findings)
    assert not missing, sorted(missing)


def test_every_drawn_docs_figure_passes(findings):
    """Every figure drawn, listed in EXPECTED or not, has no finding."""
    failing = {}
    for name, found in sorted(findings.items()):
        allowed, _why = DEMONSTRATES.get(name, (frozenset(), ""))
        unexpected = [f for f in found if f.split(":")[0] not in allowed]
        if unexpected:
            failing[name] = unexpected
    assert failing == {}, failing
