"""Importing dartwork_mpl rebinds no matplotlib class or function (D7).

Up to 0.7, ``import dartwork_mpl`` replaced ``matplotlib.axes.Axes.twinx``
with a wrapper that showed the twin's right spine. From 0.8 that spine shows
at ``dm.simple_layout`` (``dartwork_mpl.formatting._twin_spines``). A fresh
interpreter imports matplotlib, records what it can see, then imports and
reloads the package twice and checks after each step:

* every attribute of the contract classes, inherited ones included, looked
  up statically (``dir`` + ``inspect.getattr_static``), so rebinding
  ``Artist.set_visible`` or ``FigureBase.add_subplot`` shows on ``Spine`` and
  ``Figure``;
* the own namespace of every class in their MRO;
* every class and module-level callable of the matplotlib modules already
  imported.

Registering colours, colormaps and fonts adds entries to matplotlib's
registries; it rebinds none of these names, so it is outside this contract.
"""

from __future__ import annotations

import subprocess
import sys

_PROBE = """
import importlib
import inspect
import sys
import types

import matplotlib

matplotlib.use("Agg")
import matplotlib.artist
import matplotlib.axes
import matplotlib.axis
import matplotlib.figure
import matplotlib.legend
import matplotlib.lines
import matplotlib.pyplot
import matplotlib.spines
import matplotlib.text
import matplotlib.ticker

CONTRACT = (
    matplotlib.axes.Axes,
    matplotlib.figure.Figure,
    matplotlib.figure.SubFigure,
    matplotlib.axis.XAxis,
    matplotlib.axis.YAxis,
    matplotlib.spines.Spine,
    matplotlib.text.Text,
    matplotlib.lines.Line2D,
    matplotlib.legend.Legend,
)
ABSENT = object()


def static(cls):
    out = {}
    for name in dir(cls):
        try:
            out[name] = inspect.getattr_static(cls, name)
        except AttributeError:
            out[name] = ABSENT
    return out


def modules():
    out = {}
    for name, module in list(sys.modules.items()):
        if not (name == "matplotlib" or name.startswith("matplotlib.")):
            continue
        if not isinstance(module, types.ModuleType):
            continue
        for attr, value in list(vars(module).items()):
            if isinstance(value, type) or callable(value):
                out[(name, attr)] = value
    return out


def rebound(was, now):
    return sorted(
        str(k) for k in was.keys() | now.keys()
        if was.get(k, ABSENT) is not now.get(k, ABSENT)
    )


statics = [static(cls) for cls in CONTRACT]
mro = {cls: dict(vars(cls)) for c in CONTRACT for cls in c.__mro__}
before = modules()
assert len(mro) > len(CONTRACT) and len(before) > 1000

import dartwork_mpl

for step in ("import", "reload 1", "reload 2"):
    if step != "import":
        importlib.reload(dartwork_mpl)
    for cls, was in zip(CONTRACT, statics):
        assert not rebound(was, static(cls)), (step, cls.__name__, rebound(was, static(cls)))
    for cls, was in mro.items():
        assert not rebound(was, dict(vars(cls))), (step, cls.__qualname__)
    now = modules()
    gone = [k for k in before if k not in now or now[k] is not before[k]]
    assert not gone, (step, gone[:10])
print("untouched", len(CONTRACT), len(mro), len(before))
"""


def test_import_and_reload_rebind_no_matplotlib_name() -> None:
    result = subprocess.run(
        [sys.executable, "-c", _PROBE],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("untouched")
