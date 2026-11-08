"""VALUE_LABEL_ON_DATA over the shipped plot templates, the code agents copy.

``save_formats`` validates every figure it saves, so a check that fires on
correct figures prints noise on every save. Run on each template as shipped
(its own preset), the check stays quiet except on the known defects below,
which are real: a value label with a line or markers drawn through it.

The user decided on 2026-11-08 to add the check first and fix these
templates afterwards, each with its own before/after PoC. A template fixed
then fails here as "no longer reports": remove its entry in the same change.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm

_TEMPLATES = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "dartwork_mpl"
    / "asset"
    / "prompt"
    / "05-templates"
)
_ALL = sorted(_TEMPLATES.glob("*.py")) + sorted(
    (_TEMPLATES / "advanced").glob("*.py")
)

# template -> the first covering label the check names, and what covers it
KNOWN = {
    "advanced/boxplot": "+0.75",  # mean labels over whiskers and points
    "advanced/small_multiples": "Δ -10",  # panel d's change under its line
    "advanced/twin_axis": "Target = $115",  # target note under the price
}


def _name(path: Path) -> str:
    return (
        f"advanced/{path.stem}" if path.parent.name == "advanced" else path.stem
    )


@pytest.mark.parametrize("path", _ALL, ids=_name)
def test_template_reports_only_its_known_defect(
    path: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(dm, "save_formats", lambda *_a, **_k: None)
    monkeypatch.setattr(dm, "validate_with_fixes", lambda *_a, **_k: ([], []))
    plt.close("all")
    try:
        source = path.read_text(encoding="utf-8")
        exec(compile(source, str(path), "exec"), {"__name__": "__main__"})
        found = [
            w
            for num in plt.get_fignums()
            for w in dm.validate_figure(
                plt.figure(num), checks=("VALUE_LABEL_ON_DATA",), quiet=True
            )
        ]
    finally:
        plt.close("all")
        dm.style.use("report")
    known = KNOWN.get(_name(path))
    if known is None:
        assert found == [], [w.message for w in found]
    else:
        assert found, f"{_name(path)} no longer reports; drop it from KNOWN"
        assert found[0].detail["example"] == known, found[0].message
