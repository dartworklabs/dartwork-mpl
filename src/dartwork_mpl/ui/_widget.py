"""Type-to-widget resolver for UI generation.

Inspects Pydantic ``ParamModel`` field metadata and produces
JSON-serializable descriptors that the frontend uses to build
parameter controls.

Supported types
---------------
- ``int`` — slider (if ge/le) or number input
- ``float`` — slider (if ge/le) or number input
- ``str`` — text input, or color picker (via widget hint / name)
- ``bool`` — checkbox
- ``Literal[...]`` — select dropdown
- ``list[int]``, ``list[float]``, ``list[str]`` — comma-separated text input
- ``tuple[int, ...]``, ``tuple[float, ...]`` — comma-separated text input
"""

from __future__ import annotations

import typing
from dataclasses import asdict, dataclass, field
from typing import Any, get_args, get_origin, get_type_hints

from ._param import ParamModel


# ============================================================================
# Parameter descriptor
# ============================================================================


@dataclass
class ParamDescriptor:
    """Resolved metadata for a single parameter."""

    name: str
    label: str
    type_name: str  # "int", "float", "str", "bool", "list_int", "list_float", "list_str"
    default: Any = None
    min_value: Any = None
    max_value: Any = None
    step: Any = None
    choices: list[Any] | None = None
    widget_hint: str | None = None  # "color", "slider", etc.

    # Extra metadata from Pydantic json_schema_extra
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return asdict(self)


def _humanize(name: str) -> str:
    """Convert snake_case to Title Case label."""
    return name.replace("_", " ").title()


def _type_name(t: type) -> str:
    """Get a simple string name for a type."""
    simple = {int: "int", float: "float", str: "str", bool: "bool"}
    if t in simple:
        return simple[t]

    origin = get_origin(t)
    args = get_args(t)

    # list[X] or List[X]
    if origin is list:
        if args:
            inner = simple.get(args[0], "str")
            return f"list_{inner}"
        return "list_str"

    # tuple[X, ...] or Tuple[X, ...]
    if origin is tuple:
        if args:
            # tuple[float, ...] → list_float (variable-length)
            inner = simple.get(args[0], "str")
            return f"list_{inner}"
        return "list_str"

    return "str"


def _serialize_default(val: Any, type_name: str) -> Any:
    """Make default values JSON-safe for list/tuple types."""
    if val is None:
        return "" if type_name.startswith("list_") else val
    if isinstance(val, (list, tuple)):
        return ", ".join(str(v) for v in val)
    return val


# ============================================================================
# Extract from Pydantic ParamModel
# ============================================================================


def descriptors_from_model(
    model_cls: type[ParamModel],
) -> list[ParamDescriptor]:
    """Extract ``ParamDescriptor`` list from a Pydantic model class.

    Parameters
    ----------
    model_cls : type[ParamModel]
        A subclass of ``ParamModel``.

    Returns
    -------
    list[ParamDescriptor]
        One descriptor per model field.
    """
    descriptors: list[ParamDescriptor] = []

    for name, field_info in model_cls.model_fields.items():
        annotation = field_info.annotation
        if annotation is None:
            annotation = str

        # Resolve Literal
        origin = get_origin(annotation)
        choices: list[Any] | None = None
        resolved_type = annotation

        if origin is typing.Literal:
            choices = list(get_args(annotation))
            resolved_type = type(choices[0]) if choices else str

        # Compute type_name (handles list/tuple/scalar)
        tname = _type_name(resolved_type)

        # Pydantic metadata
        min_val: Any = None
        max_val: Any = None
        step: Any = None
        widget_hint: str | None = None
        extra: dict[str, Any] = {}

        # ge / le / gt / lt from Pydantic metadata list
        for m in field_info.metadata:
            if hasattr(m, "ge") and m.ge is not None:
                min_val = m.ge
            if hasattr(m, "le") and m.le is not None:
                max_val = m.le
            if hasattr(m, "gt") and m.gt is not None:
                min_val = m.gt
            if hasattr(m, "lt") and m.lt is not None:
                max_val = m.lt

        # json_schema_extra
        if field_info.json_schema_extra and isinstance(
            field_info.json_schema_extra, dict
        ):
            extra = dict(field_info.json_schema_extra)
            widget_hint = extra.get("widget")
            if "step" in extra:
                step = extra["step"]

        # Auto-detect color from name (for str fields only)
        if (
            widget_hint is None
            and tname == "str"
            and "color" in name.lower()
        ):
            widget_hint = "color"

        # Description as label
        label = field_info.description or _humanize(name)

        # Serialize default for list/tuple types
        default = _serialize_default(field_info.default, tname)

        descriptors.append(
            ParamDescriptor(
                name=name,
                label=label,
                type_name=tname,
                default=default,
                min_value=min_val,
                max_value=max_val,
                step=step,
                choices=choices,
                widget_hint=widget_hint,
                extra=extra,
            )
        )

    return descriptors
