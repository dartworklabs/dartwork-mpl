"""The controls the page renders for a ``ParamModel``, and their ``/api/descriptors`` wire form.

Each model field becomes one ``Control`` variant chosen from its annotation:

- ``int`` / ``float`` — ``NumberControl`` (slider when bounded, else number input)
- ``bool`` — ``BoolControl`` (checkbox)
- ``Literal[...]`` — ``ChoiceControl`` (select)
- ``list[X]`` / ``tuple[X, ...]`` — ``ListControl`` (comma-separated text)
- ``str`` and every other annotation — ``TextControl`` (text input or colour picker)

``controls_wire`` is the one place the variants become the wire dicts the
page's JavaScript reads (``type_name``, ``min_value``, ``choices`` …); that
payload is a frozen interface. Surface (through the ``params`` package):
``Control``, ``controls_from_model`` and ``controls_wire``.
"""

import typing
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal, TypeAlias, get_args, get_origin

from ._model import ParamModel

# The scalar kinds a choice's values or a list's items can have.
Scalar: TypeAlias = Literal["int", "float", "str", "bool"]

_SCALARS: dict[object, Scalar] = {
    int: "int",
    float: "float",
    str: "str",
    bool: "bool",
}


@dataclass(frozen=True)
class _ControlBase:
    """What every control has, whatever its kind.

    ``default`` is the wire default (list defaults already joined as text).
    ``minimum`` / ``maximum`` are the field's declared ``ge``/``gt`` and
    ``le``/``lt`` (``None`` when undeclared); a field of any kind may declare
    them, and the page renders them for numbers. ``widget_hint`` is the
    ``widget`` entry of ``json_schema_extra`` or the automatic ``"color"`` of a
    text-valued field whose name contains ``color``. ``extra`` is the field's
    ``json_schema_extra`` dict, from which the wire ``step`` and ``group`` come.
    """

    name: str
    label: str
    default: Any
    minimum: Any
    maximum: Any
    widget_hint: Any
    extra: dict[str, Any]


@dataclass(frozen=True)
class NumberControl(_ControlBase):
    """An ``int`` or ``float`` field."""

    number: Literal["int", "float"]


@dataclass(frozen=True)
class BoolControl(_ControlBase):
    """A ``bool`` field."""


@dataclass(frozen=True)
class TextControl(_ControlBase):
    """A ``str`` field, or any annotation no other control covers."""


@dataclass(frozen=True)
class ChoiceControl(_ControlBase):
    """A ``Literal`` field: its members, and the kind of the first one (``str`` if unknown)."""

    choices: tuple[Any, ...]
    value_kind: Scalar


@dataclass(frozen=True)
class ListControl(_ControlBase):
    """A ``list[X]`` / ``tuple[X, ...]`` field edited as comma-separated text of ``item`` values."""

    item: Scalar


Control: TypeAlias = (
    NumberControl | BoolControl | TextControl | ChoiceControl | ListControl
)


def _humanize(name: str) -> str:
    """Convert a snake_case name to a Title Case label (``line_color`` -> ``Line Color``)."""
    return name.replace("_", " ").title()


def _list_item(annotation: object) -> Scalar | None:
    """The item kind of ``list[X]`` / ``tuple[X, ...]``, or ``None`` for other annotations.

    Unknown or missing item types read as ``str``; a bare ``list`` (no
    subscription) is not a list control.
    """
    if get_origin(annotation) not in (list, tuple):
        return None
    args = get_args(annotation)
    return _SCALARS.get(args[0], "str") if args else "str"


def _serialize_default(val: Any, is_list: bool) -> Any:
    """Convert a default to its wire form: sequences become ``", "``-joined text.

    A ``None`` default of a list control becomes ``""``; other values pass
    through unchanged.
    """
    if val is None:
        return "" if is_list else val
    if isinstance(val, (list, tuple)):
        return ", ".join(str(v) for v in val)
    return val


def _bounds(metadata: list[Any]) -> tuple[Any, Any]:
    """Return the declared (minimum, maximum); later ``ge``/``gt``/``le``/``lt`` entries win."""
    minimum: Any = None
    maximum: Any = None
    for m in metadata:
        if hasattr(m, "ge") and m.ge is not None:
            minimum = m.ge
        if hasattr(m, "le") and m.le is not None:
            maximum = m.le
        if hasattr(m, "gt") and m.gt is not None:
            minimum = m.gt
        if hasattr(m, "lt") and m.lt is not None:
            maximum = m.lt
    return minimum, maximum


def controls_from_model(model_cls: type[ParamModel]) -> list[Control]:
    """Return one control per field of ``model_cls``, in declaration order.

    The label is the field description or the humanized name. Pure; reads
    only the class's field metadata.
    """
    controls: list[Control] = []
    for name, field_info in model_cls.model_fields.items():
        annotation: Any = (
            field_info.annotation if field_info.annotation is not None else str
        )
        jse = field_info.json_schema_extra
        extra: dict[str, Any] = (
            dict(jse) if jse and isinstance(jse, dict) else {}
        )
        minimum, maximum = _bounds(field_info.metadata)
        label = field_info.description or _humanize(name)
        hint = extra.get("widget")

        def text_hint(hint: Any = hint, name: str = name) -> Any:
            """A text-valued field named ``*color*`` with no hint gets the colour picker."""
            return "color" if hint is None and "color" in name.lower() else hint

        if get_origin(annotation) is typing.Literal:
            choices = get_args(annotation)
            kind: Scalar = (
                _SCALARS.get(type(choices[0]), "str") if choices else "str"
            )
            controls.append(
                ChoiceControl(
                    name,
                    label,
                    _serialize_default(field_info.default, False),
                    minimum,
                    maximum,
                    text_hint() if kind == "str" else hint,
                    extra,
                    choices,
                    kind,
                )
            )
            continue
        scalar = _SCALARS.get(annotation)
        item = _list_item(annotation)
        default = _serialize_default(
            field_info.default, scalar is None and item is not None
        )
        common = (name, label, default, minimum, maximum)
        control: Control
        if scalar == "int" or scalar == "float":
            control = NumberControl(*common, hint, extra, scalar)
        elif scalar == "bool":
            control = BoolControl(*common, hint, extra)
        elif scalar is None and item is not None:
            control = ListControl(*common, hint, extra, item)
        else:
            control = TextControl(*common, text_hint(), extra)
        controls.append(control)
    return controls


def _wire(control: Control) -> dict[str, Any]:
    """Project one control onto the frozen ``/api/descriptors`` entry."""
    choices: list[Any] | None = None
    match control:
        case NumberControl(number=number):
            type_name: str = number
        case BoolControl():
            type_name = "bool"
        case TextControl():
            type_name = "str"
        case ChoiceControl(choices=members, value_kind=kind):
            type_name = kind
            choices = deepcopy(list(members))
        case ListControl(item=item):
            type_name = f"list_{item}"
    return {
        "name": control.name,
        "label": control.label,
        "type_name": type_name,
        "default": deepcopy(control.default),
        "min_value": deepcopy(control.minimum),
        "max_value": deepcopy(control.maximum),
        "step": deepcopy(control.extra.get("step")),
        "group": deepcopy(control.extra.get("group")),
        "choices": choices,
        "widget_hint": deepcopy(control.widget_hint),
        "extra": deepcopy(control.extra),
    }


def controls_wire(controls: list[Control]) -> list[dict[str, Any]]:
    """The ``/api/descriptors`` payload: one detached JSON-ready dict per control, in order."""
    return [_wire(control) for control in controls]
