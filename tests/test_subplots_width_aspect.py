"""Tests for dm.subplots() width=/aspect= API (0.4+)."""

from __future__ import annotations

import math
import warnings

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


class TestFigsizeDeprecation:
    def test_figsize_emits_deprecation(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            fig, _ = dm.subplots(figsize=(5, 3))
            try:
                pass
            finally:
                _close(fig)
        msgs = [
            str(w.message)
            for w in caught
            if issubclass(w.category, DeprecationWarning)
        ]
        assert any("figsize" in m for m in msgs), msgs

    def test_dpi_emits_deprecation(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            fig, _ = dm.subplots(dpi=150)
            try:
                pass
            finally:
                _close(fig)
        msgs = [
            str(w.message)
            for w in caught
            if issubclass(w.category, DeprecationWarning)
        ]
        assert any("dpi" in m for m in msgs)

    def test_width_and_figsize_both_specified_warns_and_figsize_wins(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            fig, _ = dm.subplots(width="9cm", figsize=(7, 4))
            try:
                w, h = fig.get_size_inches()
            finally:
                _close(fig)
        # figsize wins for backward compat during 0.4.x.
        assert math.isclose(w, 7, rel_tol=1e-6)
        assert math.isclose(h, 4, rel_tol=1e-6)
        # And a warning is emitted.
        assert any(issubclass(c.category, DeprecationWarning) for c in caught)


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

    def test_figsize_emits_deprecation(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            fig = dm.figure(figsize=(5, 3))
            try:
                pass
            finally:
                _close(fig)
        msgs = [
            str(w.message)
            for w in caught
            if issubclass(w.category, DeprecationWarning)
        ]
        assert any("figsize" in m for m in msgs), msgs

    def test_dpi_emits_deprecation(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            fig = dm.figure(dpi=150)
            try:
                pass
            finally:
                _close(fig)
        msgs = [
            str(w.message)
            for w in caught
            if issubclass(w.category, DeprecationWarning)
        ]
        assert any("dpi" in m for m in msgs)
