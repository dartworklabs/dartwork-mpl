"""The presentation preset is the scientific one with every point size x 2.6.

Decisions 1-A, 2-A and 5-A (2026-11-03, review page 2026-11-02-choices): a
slide chart looks like a journal-column chart enlarged as a vector to the
slide body, so text, lines, markers, tick lengths and pads all grow by the
same factor, 23.4 / 9 = 2.6, and one ``dm.fs`` / ``dm.lw`` step grows with
them. Before this, only text was 1.3x the report's and lines, markers and
ticks stayed at paper size; on the 23.4 cm slide canvas that left 0.45 pt of
text per cm against 0.66 in a 9 cm column.
"""

from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm
from dartwork_mpl.style import SLIDE_SCALE, step_pt

# The one non-size key on which the presentation preset keeps its own value:
# slide titles (when asked for) stay regular weight, paper titles are bold.
_OWN_VALUES = {"axes.titleweight"}


def _is_point_size(key: str, value: object) -> bool:
    """True for an rcParam measured in points that a vector enlargement scales.

    The rule the approved captures were drawn with: numeric keys whose last
    part ends in size, linewidth, width, pad, markeredgewidth or capsize.
    Figure, savefig, legend, agg and axes3d keys are canvas sizes, ratios or
    spacings in font-size units, except their font sizes.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if key.startswith(
        ("figure.", "savefig.", "legend.", "agg.", "axes3d.")
    ) and not key.endswith(("titlesize", "labelsize", "fontsize")):
        return False
    return key.rsplit(".", 1)[-1].endswith(
        ("size", "linewidth", "width", "pad", "markeredgewidth", "capsize")
    )


def _rc(preset: str) -> dict[str, object]:
    plt.rcdefaults()
    dm.style.use(preset)
    return dict(mpl.rcParams)


@pytest.mark.parametrize(
    ("paper", "slides"),
    [("scientific", "presentation"), ("scientific-kr", "presentation-kr")],
)
class TestPresentationIsScientificTimesK:
    """Each point size is 2.6x scientific; every other value is scientific's."""

    def test_every_point_size_is_k_times(self, paper: str, slides: str) -> None:
        sci, pre = _rc(paper), _rc(slides)
        keys = [k for k, v in sci.items() if _is_point_size(k, v)]
        # Text, lines, markers, ticks, pads, grid, spines, boxplots.
        assert len(keys) >= 39
        wrong = {
            k: (sci[k], pre[k])
            for k in keys
            if pre[k] != pytest.approx(sci[k] * SLIDE_SCALE, abs=1e-9)  # type: ignore[operator]
        }
        assert wrong == {}, f"(scientific, presentation) off by 2.6: {wrong}"

    def test_everything_else_is_scientific(
        self, paper: str, slides: str
    ) -> None:
        sci, pre = _rc(paper), _rc(slides)
        differ = {
            k
            for k, v in sci.items()
            if not _is_point_size(k, v) and pre[k] != v
        }
        assert differ == _OWN_VALUES


def test_slide_scale_is_slide_body_over_column() -> None:
    assert SLIDE_SCALE == 2.6
    width_cm = dm.figsize_for("slide")[0] * 2.54
    assert width_cm / 9.0 == pytest.approx(SLIDE_SCALE)


class TestStepPt:
    """One fs / lw step is 2.6 pt while a presentation preset is in force."""

    @pytest.mark.parametrize("preset", ["presentation", "presentation-kr"])
    def test_slides_step_k_points(self, preset: str) -> None:
        dm.style.use(preset)
        assert step_pt() == SLIDE_SCALE

    @pytest.mark.parametrize(
        "preset", ["scientific", "report", "poster", "web", "dark", "report-kr"]
    )
    def test_other_presets_step_one_point(self, preset: str) -> None:
        dm.style.use(preset)
        assert step_pt() == 1.0

    def test_last_preset_of_a_list_decides(self) -> None:
        dm.style.use(["scientific", "presentation"])
        assert step_pt() == SLIDE_SCALE
        dm.style.use(["presentation", "scientific"])
        assert step_pt() == 1.0

    def test_bare_stack_after_slides_drops_the_slide_step(self) -> None:
        dm.style.use("scientific")
        paper_small = dm.fs(-1)
        dm.style.use("presentation")
        dm.style.stack(["base", "font-scientific"])
        assert step_pt() == 1.0
        assert dm.fs(-1) == paper_small
        dm.style.use("presentation")
        assert step_pt() == SLIDE_SCALE

    def test_native_reset_drops_the_slide_step(self) -> None:
        dm.style.use("presentation")
        plt.rcdefaults()
        assert step_pt() == 1.0

    def test_context_steps_inside_and_restores_after(self) -> None:
        dm.style.use("report")
        with dm.style.context("presentation"):
            assert step_pt() == SLIDE_SCALE
        assert step_pt() == 1.0

    def test_caller_font_override_keeps_the_step(self) -> None:
        dm.style.use("presentation", font_size=14)
        assert step_pt() == SLIDE_SCALE
