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

if TYPE_CHECKING:
    from ._param import ParamModel
    from .ui import run

__all__ = ["ParamModel", "run"]


def __getattr__(name: str) -> Any:
    """Lazy-load submodules that require the optional ``ui`` extra.

    Importing ``dartwork_mpl.ui`` itself must not pull in ``pydantic``
    or ``fastapi`` — the ``dartwork-mpl-ui`` scaffold command imports
    this package (via ``dartwork_mpl.ui.__main__``) on a *base* install
    where those extras aren't present. ``ParamModel`` (needs pydantic)
    and ``run`` (needs fastapi/uvicorn) are therefore imported only on
    first attribute access, which is exactly when the optional dep is
    actually required.
    """
    if name == "ParamModel":
        from ._param import ParamModel

        return ParamModel
    if name == "run":
        from .ui import run

        return run
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
