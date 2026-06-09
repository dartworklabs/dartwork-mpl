"""Visual validation tools for Matplotlib figures.

Detects common rendering issues (label overlap, margin overflow, etc.)
that are invisible in console-only (stdout) environments such as AI
agent pipelines. Every check emits structured ``[VISUAL]`` log lines
so that agents can grep for them and attempt automated fixes.

The implementation was split out of a single 870-line ``validate.py``
in v0.6.x. Each ``_check_*`` from the historical module now lives in
its own file under :mod:`dartwork_mpl.validate._checks`; the
orchestrator lives in :mod:`dartwork_mpl.validate._orchestrator`. The
public surface (``Severity``, ``VisualWarning``, ``validate_figure``)
is identical to the old module so external callers don't need to
change anything.

Usage
-----
>>> import dartwork_mpl as dm
>>> fig, ax = plt.subplots()
>>> ax.plot([1, 2, 3])
>>> warnings = dm.validate_figure(fig)
>>> # Console output: [VISUAL] ✅ No visual issues detected.
"""

from __future__ import annotations

from ._orchestrator import validate_figure
from ._types import Severity, VisualWarning

__all__ = ["Severity", "VisualWarning", "validate_figure"]
