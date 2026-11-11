"""Every gallery example and shipped template draws a figure the validator passes.

``dm.validate_figure`` is the judge an agent uses in its render -> look ->
revise loop, and these scripts are what the library shows as known-good
output. In November 2026 an audit ran the validator over them and found 70
real, visible defects in 28 gallery scripts (a title cut off at the canvas
edge, a legend over the data, a white title on a white canvas), all live on
the docs site: the ``presentation`` preset had been made 2.6 times larger and
no test ran the gallery (``test_docs_figures_validate`` covers the docs
*generators*, not ``docs/examples_source``).

Each script runs here as the gallery runs it and every figure it leaves open
must have no finding of severity WARNING or above. A script that shows a
finding on purpose is listed in ``INTENDED`` with the checks it trips and
why; an entry whose checks no longer fire fails too, so the list cannot go
stale. ``CHECK_FAILED`` (a check that could not run) is never allowed.
"""

from __future__ import annotations

import runpy
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm
from dartwork_mpl.validate import Severity

_ROOT = Path(__file__).resolve().parents[2]
_GALLERY = _ROOT / "docs" / "examples_source"
_TEMPLATES = (
    _ROOT / "src" / "dartwork_mpl" / "asset" / "prompt" / "05-templates"
)

GALLERY_SCRIPTS = sorted(_GALLERY.rglob("*.py"))
TEMPLATE_SCRIPTS = sorted(_TEMPLATES.rglob("*.py"))

# Scripts that show a finding on purpose: the checks each must trip, and why.
INTENDED: dict[str, tuple[frozenset[str], str]] = {
    "docs/examples_source/05_helpers_api/plot_helpers_quality.py": (
        frozenset({"OVERLAP"}),
        "demonstrates the quality checker on two labels drawn over each other",
    ),
    "docs/examples_source/06_chart_recipes/plot_mcmc_posterior_ridge.py": (
        frozenset({"MARGIN_ASYMMETRY"}),
        "hand-packed ridgeline: the parameter names fill the left margin",
    ),
}


def _relative(script: Path) -> str:
    return script.relative_to(_ROOT).as_posix()


def _warning_ids(
    script: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> set[str]:
    """Run ``script`` as the gallery does; the WARNING-or-worse check ids of its figures."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)
    runpy.run_path(str(script), run_name="__main__")
    figures = [plt.figure(number) for number in plt.get_fignums()]
    assert figures, f"{_relative(script)} left no open figure to check"
    return {
        warning.check_id
        for figure in figures
        for warning in dm.validate_figure(figure, quiet=True)
        if warning.severity is not Severity.INFO
    }


def test_the_corpus_is_found() -> None:
    """A moved directory must not turn the checks below into zero tests."""
    assert len(GALLERY_SCRIPTS) >= 90
    assert len(TEMPLATE_SCRIPTS) == 36
    missing = [name for name in INTENDED if not (_ROOT / name).is_file()]
    assert not missing, missing


@pytest.mark.parametrize(
    "script", GALLERY_SCRIPTS + TEMPLATE_SCRIPTS, ids=_relative
)
def test_script_draws_figures_without_warnings(
    script: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The script's figures trip exactly the checks ``INTENDED`` lists for it: none, usually."""
    intended, _why = INTENDED.get(_relative(script), (frozenset(), ""))

    found = _warning_ids(script, tmp_path, monkeypatch)

    assert found == intended
