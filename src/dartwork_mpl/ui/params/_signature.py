"""Find the ParamModel a figure function declares for its one parameter.

Surface (through the ``params`` package): ``extract_param_model``.
"""

from collections.abc import Callable
from typing import Any

from matplotlib.figure import Figure

from ._model import ParamModel


def extract_param_model(fn: Callable[..., Any]) -> type[ParamModel]:
    """Extract the ParamModel subclass from a figure function's signature.

    Validates that ``fn`` has exactly one parameter whose annotation
    is a ``ParamModel`` subclass.

    Raises
    ------
    TypeError
        If the signature does not match expectations.
    """
    import typing

    try:
        hints = typing.get_type_hints(fn)
    except Exception:  # noqa: BLE001
        hints = dict(fn.__annotations__)

    ret = hints.pop("return", None)

    if len(hints) == 0:
        raise TypeError(
            f"{fn.__name__}() has no type annotations. "
            "Expected signature: (params: YourParamModel) -> Figure"
        )

    if len(hints) > 1:
        raise TypeError(
            f"{fn.__name__}() has {len(hints)} annotated parameters, "
            "expected exactly 1. "
            "Expected signature: (params: YourParamModel) -> Figure"
        )

    param_name, param_type = next(iter(hints.items()))

    if not (
        isinstance(param_type, type) and issubclass(param_type, ParamModel)
    ):
        raise TypeError(
            f"{fn.__name__}({param_name}: {param_type!r}) — "
            f"annotation must be a ParamModel subclass"
        )

    # Optional: warn if return type is not Figure
    if ret is not None and ret is not Figure:
        import warnings

        warnings.warn(
            f"{fn.__name__}() return type is annotated as {ret!r}, "
            f"expected Figure.",
            stacklevel=3,
        )

    return param_type
