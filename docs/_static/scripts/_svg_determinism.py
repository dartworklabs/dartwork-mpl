"""Pin matplotlib's SVG output so docs assets regenerate byte-identically.

Mirrors docs/conf.py: SOURCE_DATE_EPOCH fixes the <dc:date>, svg.hashsalt
fixes element ids. Setting hashsalt on rcParamsDefault too means it
survives dm.style.use(...) resets. Call BEFORE importing dartwork_mpl /
pyplot in any standalone asset generator.
"""

from __future__ import annotations

import os

import matplotlib

SOURCE_DATE_EPOCH = "1735689600"  # 2025-01-01 UTC - matches docs/conf.py
HASHSALT = "dartwork-mpl-docs"


def apply_svg_determinism() -> None:
    os.environ.setdefault("SOURCE_DATE_EPOCH", SOURCE_DATE_EPOCH)
    matplotlib.rcParams["svg.hashsalt"] = HASHSALT
    matplotlib.rcParamsDefault["svg.hashsalt"] = HASHSALT


def reset_svg_render_state() -> None:
    """Reset matplotlib style state without losing deterministic SVG IDs."""
    matplotlib.rcdefaults()
    apply_svg_determinism()
