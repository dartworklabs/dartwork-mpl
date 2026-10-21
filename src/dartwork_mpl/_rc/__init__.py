"""The one lock around dartwork-mpl's writes to matplotlib's process-global rcParams.

Platform code (ADR 0005): style presets and the colour-cycle setter both
mutate ``matplotlib.rcParams``; holding this lock while they do keeps
concurrent writers from interleaving a half-applied state. It imports no
slice. Not part of the public API.
"""

from __future__ import annotations

import threading

__all__ = ["rc_lock"]

#: Held by every dartwork-mpl write to ``matplotlib.rcParams``. Without it,
#: concurrent ``dm.style.use(...)`` / ``dm.set_colors(...)`` calls from
#: several threads can interleave rcParams updates and corrupt the style.
rc_lock: threading.Lock = threading.Lock()
