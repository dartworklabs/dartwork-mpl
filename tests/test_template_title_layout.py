"""Advanced-template titles stay on the canvas under three presets (#523).

Renders every bundled advanced template under scientific, report and
presentation. Each title ends inside the canvas, or it cannot fit there
(wider than the room its anchor leaves), is reported by validate_figure,
and re-running the template's last simple_layout call without it does not
widen the axes, which shows the layout did not chase it.
"""

from __future__ import annotations

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm

ADVANCED = (
    Path(dm.__file__).parent / "asset" / "prompt" / "05-templates" / "advanced"
)
PRESETS = ("scientific", "report", "presentation")
TOL_PX = 0.5


def _extent(fig, artist):
    fig.canvas.draw()
    return artist.get_window_extent(fig.canvas.get_renderer())


def _outside_canvas(fig, artist) -> bool:
    ext = _extent(fig, artist)
    canvas = fig.bbox
    return bool(
        ext.x0 < canvas.x0 - TOL_PX
        or ext.y0 < canvas.y0 - TOL_PX
        or ext.x1 > canvas.x1 + TOL_PX
        or ext.y1 > canvas.y1 + TOL_PX
    )


def _flagged(fig, text: str) -> bool:
    """Whether validate_figure names ``text`` in an overflow finding."""
    found = dm.validate_figure(
        fig, checks=("OVERFLOW", "CLIPPED_TEXT"), quiet=True
    )
    return any(w.detail.get("text") == text for w in found)


_TITLE_ATTRS = {
    "center": "title",
    "left": "_left_title",
    "right": "_right_title",
}


def _titles(fig):
    """Yield ``(axes, loc, text)`` per non-empty title; suptitle axes None.

    Enumerated independently of the adapter under test.
    """
    for ax in fig.axes:
        for loc, attr in _TITLE_ATTRS.items():
            text = getattr(ax, attr)
            if ax.get_title(loc=loc).strip():
                assert text.get_text() == ax.get_title(loc=loc)
                yield ax, loc, text
    suptitle = getattr(fig, "_suptitle", None)
    if suptitle is not None and suptitle.get_text().strip():
        yield None, "center", suptitle


def _room_px(fig, ax, loc: str) -> float:
    """Widest title the canvas can hold given where it is anchored."""
    canvas = fig.bbox
    if ax is None or loc == "center":
        return canvas.width
    box = _extent(fig, ax)
    return canvas.x1 - box.x0 if loc == "left" else box.x1 - canvas.x0


def _run_template(path: Path, preset: str, monkeypatch, tmp_path):
    source = path.read_text(encoding="utf-8")
    source, count = re.subn(
        r'dm\.style\.use\("[^"]+"\)', f'dm.style.use("{preset}")', source
    )
    assert count == 1, f"{path.name}: expected one dm.style.use call"
    calls = []
    real_layout = dm.simple_layout

    def recording_layout(*args, **kwargs):
        calls.append((args, kwargs))
        return real_layout(*args, **kwargs)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(dm, "save_formats", lambda *_a, **_k: None)
    monkeypatch.setattr(dm, "simple_layout", recording_layout)
    plt.close("all")
    exec(compile(source, str(path), "exec"), {"__name__": "__main__"})
    figures = [plt.figure(num) for num in plt.get_fignums()]
    return figures, calls, real_layout


@pytest.mark.parametrize("preset", PRESETS)
@pytest.mark.parametrize(
    "template", sorted(ADVANCED.glob("*.py")), ids=lambda p: p.stem
)
def test_advanced_template_titles_stay_on_canvas(
    template: Path, preset: str, monkeypatch, tmp_path
) -> None:
    """On main 10/18 (scientific, report) and 11/18 (presentation) failed.

    A title may end outside the canvas only when it is wider than the room
    its anchor leaves; then the checks must report it and re-running the
    layout without it must not widen the axes (it was not chased).
    """
    figures, calls, relayout = _run_template(
        template, preset, monkeypatch, tmp_path
    )
    assert figures, f"{template.name} left no open figure"
    try:
        for fig in figures:
            for ax, loc, title in list(_titles(fig)):
                if not _outside_canvas(fig, title):
                    continue
                text, where = title.get_text(), f"{template.stem}[{preset}]"
                width = _extent(fig, title).width
                assert width > _room_px(fig, ax, loc), f"{where}: {text!r}"
                assert _flagged(fig, text), f"{where}: unreported {text!r}"
                assert calls, f"{where}: not laid out by simple_layout"
                before = [a.get_position().width for a in fig.axes]
                title.set_text("")
                relayout(*calls[-1][0], **calls[-1][1])
                title.set_text(text)
                after = [a.get_position().width for a in fig.axes]
                assert after == pytest.approx(before, abs=1e-3), where
    finally:
        plt.close("all")
