"""Tests for dm.subplots() width=/aspect= API (0.4+)."""

from __future__ import annotations

import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm


def _close(fig):
    plt.close(fig)


class TestWidthAspect:
    def test_width_string_cm(self):
        fig, _ = dm.subplots(width="13cm", aspect="standard")
        try:
            w, h = fig.get_size_inches()
            assert math.isclose(w, 13 / 2.54, rel_tol=1e-6)
            assert math.isclose(h / w, 3 / 4, rel_tol=1e-6)
        finally:
            _close(fig)

    def test_width_string_inch(self):
        fig, _ = dm.subplots(width="6.7in", aspect="square")
        try:
            w, h = fig.get_size_inches()
            assert math.isclose(w, 6.7, rel_tol=1e-6)
            assert math.isclose(h, w, rel_tol=1e-6)
        finally:
            _close(fig)

    def test_width_with_dm_cm(self):
        fig, _ = dm.subplots(width=dm.cm(11.3), aspect="wide")
        try:
            w, h = fig.get_size_inches()
            assert math.isclose(w, 11.3 / 2.54, rel_tol=1e-6)
            assert math.isclose(h / w, 2 / 3, rel_tol=1e-6)
        finally:
            _close(fig)

    def test_width_raw_int_is_cm(self):
        fig, _ = dm.subplots(width=13)
        try:
            w, _h = fig.get_size_inches()
            assert math.isclose(w, 13 / 2.54, rel_tol=1e-6)
        finally:
            _close(fig)

    def test_aspect_default_is_standard(self):
        fig, _ = dm.subplots(width="9cm")
        try:
            w, h = fig.get_size_inches()
            assert math.isclose(h / w, 3 / 4, rel_tol=1e-6)
        finally:
            _close(fig)

    def test_aspect_numeric(self):
        fig, _ = dm.subplots(width="10cm", aspect=0.5)
        try:
            w, h = fig.get_size_inches()
            assert math.isclose(h / w, 0.5, rel_tol=1e-6)
        finally:
            _close(fig)


class TestFigsizeRemoval:
    """``figsize=``/``dpi=`` were deprecated in 0.4.0 and removed in 0.4.x.

    Passing them now raises ``TypeError`` so callers get a clear signal
    instead of a silent legacy code path.
    """

    def test_figsize_raises_type_error(self):
        with pytest.raises(TypeError, match="figsize="):
            dm.subplots(figsize=(5, 3))

    def test_dpi_raises_type_error(self):
        with pytest.raises(TypeError, match="dpi="):
            dm.subplots(dpi=150)

    def test_width_and_figsize_both_raises(self):
        """Even if ``width=`` is given, supplying ``figsize=`` still raises."""
        with pytest.raises(TypeError, match="figsize="):
            dm.subplots(width="9cm", figsize=(7, 4))


class TestErrors:
    def test_invalid_width_unit(self):
        with pytest.raises(ValueError):
            dm.subplots(width="3foot")

    def test_invalid_aspect(self):
        with pytest.raises(ValueError, match="aspect"):
            dm.subplots(width="9cm", aspect="ultra")

    def test_negative_width(self):
        with pytest.raises(ValueError, match="positive"):
            dm.subplots(width="-1cm")


class TestFigureWidthAspect:
    """dm.figure() must mirror dm.subplots() width/aspect behaviour."""

    def test_width_string_cm(self):
        fig = dm.figure(width="13cm", aspect="standard")
        try:
            w, h = fig.get_size_inches()
            assert math.isclose(w, 13 / 2.54, rel_tol=1e-6)
            assert math.isclose(h / w, 3 / 4, rel_tol=1e-6)
        finally:
            _close(fig)

    def test_aspect_default_is_standard(self):
        fig = dm.figure(width="9cm")
        try:
            w, h = fig.get_size_inches()
            assert math.isclose(h / w, 3 / 4, rel_tol=1e-6)
        finally:
            _close(fig)

    def test_figsize_raises_type_error(self):
        with pytest.raises(TypeError, match="figsize="):
            dm.figure(figsize=(5, 3))

    def test_dpi_raises_type_error(self):
        with pytest.raises(TypeError, match="dpi="):
            dm.figure(dpi=150)

    def test_width_and_figsize_both_raises(self):
        with pytest.raises(TypeError, match="figsize="):
            dm.figure(width="9cm", figsize=(7, 4))
