"""Each named fix to the font table: on hand-made tables, then on matplotlib's."""

import shutil
from dataclasses import replace
from pathlib import Path

import pytest
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties

import dartwork_mpl as dm
from dartwork_mpl.edgecase import settle
from dartwork_mpl.font import apply, measure
from dartwork_mpl.font.decide import table_plan
from dartwork_mpl.font.edges import EDGES
from dartwork_mpl.font.model import Face, Table, Weight

SYSTEM = Face("Roboto-Regular.ttf", "Roboto", Weight(400), False)
BUNDLED = Face("Roboto-Regular.ttf", "Roboto", Weight(400), True)
THIN = Face("Paperlogy-1Thin.ttf", "Paperlogy", Weight(250), True)
EXTRA_LIGHT = Face("Paperlogy-2ExtraLight.ttf", "Paperlogy", Weight(250), True)


def _settle(*faces, files=100):
    table = Table(faces, files)
    return settle(table, table_plan(table), EDGES)


def test_system_font_tie_moves_bundled_faces_first_and_is_a_fixed_point():
    settled = _settle(SYSTEM, BUNDLED, BUNDLED)
    assert settled.fired == ("system-font-tie",)
    assert settled.plan.order == (1, 2, 0)
    assert _settle(BUNDLED, BUNDLED, SYSTEM).fired == ()


def test_paperlogy_weight_250_gets_the_weight_its_name_says():
    settled = _settle(THIN, EXTRA_LIGHT)
    assert settled.fired == ("paperlogy-weight-250",)
    assert settled.plan.weights == (Weight(100), Weight(200))
    assert _settle(replace(THIN, bundled=False)).fired == ()


def test_emptied_bundle_warns_once():
    settled = _settle(BUNDLED, files=1)
    assert settled.fired == ("emptied-bundle",)
    assert "only 1 bundled font file" in (settled.plan.warning or "")
    with (
        pytest.warns(UserWarning, match="bundled font"),
        pytest.MonkeyPatch.context() as mp,
    ):
        mp.setattr(measure, "bundled_files", lambda: [])
        apply.register()


def _resolve(prop: FontProperties) -> Path:
    return Path(font_manager.findfont(prop, fallback_to_default=False))


def test_system_font_tie_flips_a_primed_lookup(monkeypatch, tmp_path):
    manager = font_manager.fontManager
    bundled = dm.font.get_font_dir() / "Roboto-Regular.ttf"
    regular = next(e for e in manager.ttflist if Path(e.fname) == bundled)
    copy = tmp_path / "Roboto-Regular.ttf"
    shutil.copy(bundled, copy)
    monkeypatch.setattr(
        manager,
        "ttflist",
        [replace(regular, fname=str(copy)), *manager.ttflist],
    )
    prop = FontProperties(family="Roboto", size=11.111)
    assert _resolve(prop) == copy  # the earlier system copy wins, and is cached
    apply.install(_settle_now())
    assert _resolve(prop) == bundled


def _settle_now():
    facts = measure.table(len(measure.bundled_files()))
    return settle(facts, table_plan(facts), EDGES).plan
