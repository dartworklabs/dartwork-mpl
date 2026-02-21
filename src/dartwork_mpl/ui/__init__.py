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

from ._param import ParamModel
from .ui import run

__all__ = ["ParamModel", "run"]
