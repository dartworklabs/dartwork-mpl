"""Regression test for the docs asset generators' figsize invariant.

Guards the root cause of the long-standing ``viz_example`` docs-build
failure (#235): a ``Length`` from ``dm.cm(...)`` passed straight to
``fig.set_size_inches`` built an object-dtype size array and raised
``ufunc 'isfinite' not supported``. ``dm.figsize(...)`` returns plain
inch floats, which is the contract this test pins.

(``viz_example`` itself was retired, so there is no static SVG asset to render
here anymore.)
"""

from __future__ import annotations


def test_set_size_inches_accepts_figsize_floats() -> None:
    """The root cause: dm.figsize returns plain floats; dm.cm a Length.

    Passing the Length to set_size_inches is what tripped numpy's
    isfinite on an object array.
    """
    import dartwork_mpl as dm

    w, h = dm.figsize("15cm", "10cm")
    assert isinstance(w, float) and isinstance(h, float)
