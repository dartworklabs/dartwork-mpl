"""``dartwork_mpl.ui`` — Interactive figure viewer.

Provides a FastAPI-powered web UI that auto-generates parameter
controls from function signatures or Pydantic models and renders
matplotlib figures in real-time.

Quick start::

    from dartwork_mpl.ui import ParamModel, run

    def my_plot(n: int = 100, alpha: float = 0.5):
        ...
        return fig

    run(my_plot)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ._param import ParamModel

if TYPE_CHECKING:
    from .ui import run

__all__ = ["ParamModel", "run"]


def __getattr__(name: str) -> Any:
    """Lazy-load heavy submodules that require optional deps."""
    if name == "run":
        from .ui import run

        return run
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
