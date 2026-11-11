"""Slide canvas validation catches downscaled text without changing other presets."""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm
from dartwork_mpl.validate import Severity


def _findings(size, preset="presentation", *, subfigure=False):
    """Validate only the target finding on a real figure, optionally a SubFigure."""
    if preset is None:
        plt.rcdefaults()
    else:
        dm.style.use(preset)
    fig = plt.figure(figsize=size)
    target = fig.subfigures(1, 2)[0] if subfigure else fig
    try:
        return [
            w
            for w in dm.validate_figure(target, quiet=True)
            if w.check_id == "SLIDE_OVERSIZE"
        ]
    finally:
        plt.close(fig)


def test_smoke_reports_scale_and_action():
    """The 24 inch smoke canvas reports exactly one actionable WARNING."""
    findings = _findings((24, 13.5))
    assert len(findings) == 1
    finding = findings[0]
    assert finding.severity is Severity.WARNING
    assert "about 0.42x" in finding.message
    assert 'dm.figsize_for("full_slide")' in finding.message
    assert finding.detail == pytest.approx(
        {
            "width_cm": 60.96,
            "height_cm": 34.29,
            "scale": 10 / 24,
            "max_width_cm": 13.33 * 2.54,
            "max_height_cm": 7.5 * 2.54,
            "tolerance": 0.01,
        }
    )


@pytest.mark.parametrize("kind", ["full_slide", "slide"])
def test_recommended_slide_sizes_are_accepted(kind):
    """Both whole-slide and under-title recommendations stay silent."""
    dm.style.use("presentation")
    assert _findings(dm.figsize_for(kind)) == []


@pytest.mark.parametrize(
    "size, count",
    [
        ((13.33, 7.5), 0),
        ((13.33 * 1.01, 7.5 * 1.01), 0),
        ((13.33 * 1.0101, 7.5), 1),
        ((13.33, 7.5 * 1.0101), 1),
    ],
)
def test_standard_slide_boundary_includes_rounding_tolerance(size, count):
    """Either dimension must exceed the standard slide plus one percent."""
    assert len(_findings(size)) == count


def test_korean_presentation_is_checked():
    """The Korean slide preset has the same oversized-canvas warning."""
    assert len(_findings((24, 13.5), "presentation-kr")) == 1


@pytest.mark.parametrize("preset", ["report", "scientific", "poster", None])
def test_non_slide_presets_are_silent(preset):
    """Large figures under other presets or a native reset are accepted."""
    assert _findings(dm.figsize("61cm", "34cm"), preset) == []


def test_tall_slide_is_checked():
    """A standard width cannot hide an oversized height, nor its shrink factor.

    A 25.4 x 40 cm figure fits the slide's width as it is; its height is what
    forces it down to 14.29 / 40 of its size.
    """
    findings = _findings(dm.figsize("25.4cm", "40cm"))
    assert len(findings) == 1
    assert findings[0].detail["scale"] == pytest.approx(14.29 / 40)
    assert "about 0.36x" in findings[0].message


def test_subfigure_uses_root_canvas_once():
    """A SubFigure is measured against its shared root canvas."""
    assert len(_findings((24, 13.5), subfigure=True)) == 1


def test_increasing_an_oversized_canvas_keeps_warning():
    """Generated increases cannot make an already oversized slide valid."""
    from random import Random

    rng = Random(688)
    for _ in range(12):
        width = rng.uniform(14, 26)
        height = rng.uniform(8, 16)
        assert len(_findings((width, height))) == 1
