"""Defaults and override behaviour of the tick-year / unit config fields."""

from __future__ import annotations

import pytest

import dartwork_mpl as dm


def test_new_fields_defaults_and_override() -> None:
    assert dm.config.tick_years == 2
    assert dm.config.date_style == "period"
    assert dm.config.number_ladder == "auto"

    with dm.config.override(
        tick_years=4, date_style="concise", number_ladder="si"
    ):
        assert dm.config.tick_years == 4
        assert dm.config.date_style == "concise"
        assert dm.config.number_ladder == "si"

    assert dm.config.tick_years == 2
    assert dm.config.date_style == "period"
    assert dm.config.number_ladder == "auto"

    with pytest.raises(AttributeError):
        with dm.config.override(tick_year=4):
            pass
