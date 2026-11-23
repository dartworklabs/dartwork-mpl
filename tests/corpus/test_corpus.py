"""Every corpus script runs from an empty directory without raising, and
``TEXT_CONTRAST`` points at the scripts whose text is faint and no others."""

from __future__ import annotations

import runpy
from pathlib import Path

import matplotlib.pyplot as plt
import pytest
from matplotlib.figure import Figure

import dartwork_mpl as dm

HERE = Path(__file__).resolve().parent
SCRIPTS = sorted([*HERE.glob("charts/*.py"), *HERE.glob("rough/*.py")])

#: The corpus figures with ink under 3:1 on what is behind it, each looked
#: at: white or pale numbers on pale cells and bars. The rule reads every
#: pixel of a text's ink, so a new name here is a figure to look at before
#: it is added, and a missing one a defect the rule stopped seeing.
FAINT_TEXT = frozenset(
    {
        "rough/heatmap_annotations",
        "rough/heatmap_corr",
        "rough/korean_slide_trend",
        "rough/low_contrast_bar_text",
        "rough/low_contrast_heatmap_text",
    }
)


@pytest.mark.parametrize(
    "script", SCRIPTS, ids=[f"{p.parent.name}/{p.stem}" for p in SCRIPTS]
)
def test_script_runs(
    script: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The script runs, and its figures have faint text exactly when it is
    one of :data:`FAINT_TEXT`. Each figure is checked when it is saved,
    while the script's rcParams still hold."""
    monkeypatch.chdir(tmp_path)
    save = dm.save_formats
    faint: dict[Figure, bool] = {}

    def checked(fig: Figure, *args: object, **kwargs: object) -> object:
        faint[fig] = "TEXT_CONTRAST" in dm.check(fig).rules
        return save(fig, *args, **kwargs)

    monkeypatch.setattr(dm, "save_formats", checked)
    try:
        with plt.rc_context():
            runpy.run_path(str(script), run_name="__main__")
            for number in plt.get_fignums():
                fig = plt.figure(number)
                if fig not in faint:
                    faint[fig] = "TEXT_CONTRAST" in dm.check(fig).rules
    finally:
        plt.close("all")
    name = f"{script.parent.name}/{script.stem}"
    assert any(faint.values()) == (name in FAINT_TEXT)
