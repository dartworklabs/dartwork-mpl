"""Importing dartwork_mpl rebinds nothing on matplotlib's classes (D7).

Up to 0.7, ``import dartwork_mpl`` replaced ``matplotlib.axes.Axes.twinx``
with a wrapper that showed the twin's right spine. From 0.8 that spine shows
at ``dm.simple_layout`` (``dartwork_mpl.formatting._twin_spines``), and
importing or reloading the package leaves every attribute of matplotlib's
Axes, Figure, Axis and Spine classes the object it was. A fresh interpreter
checks it, since this test session imported the package long ago.
"""

from __future__ import annotations

import subprocess
import sys

_PROBE = """
import importlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.axes
import matplotlib.axis
import matplotlib.figure
import matplotlib.spines

classes = (
    matplotlib.axes.Axes,
    matplotlib.figure.Figure,
    matplotlib.figure.SubFigure,
    matplotlib.axis.XAxis,
    matplotlib.axis.YAxis,
    matplotlib.spines.Spine,
)
before = [dict(vars(cls)) for cls in classes]
twinx, twiny = matplotlib.axes.Axes.twinx, matplotlib.axes.Axes.twiny

import dartwork_mpl

importlib.reload(dartwork_mpl)

assert matplotlib.axes.Axes.twinx is twinx
assert matplotlib.axes.Axes.twiny is twiny
for cls, was in zip(classes, before):
    now = dict(vars(cls))
    rebound = sorted(k for k in was.keys() | now.keys() if was.get(k) is not now.get(k))
    assert not rebound, (cls.__name__, rebound)
print("untouched")
"""


def test_import_and_reload_rebind_nothing_on_matplotlib_classes() -> None:
    result = subprocess.run(
        [sys.executable, "-c", _PROBE],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "untouched"
