"""Parse a request's active parameters into the caller's ParamModel.

The browser sends parameter values as JSON; list fields may arrive as
comma-separated text and numeric ``Literal`` choices as strings. This module
applies that documented coercion once, then one complete native Pydantic
validation pass over an alias-free copy of the model graph. Surface (through
the ``params`` package): ``InvalidRequest`` and ``parse_active``.
"""

from __future__ import annotations

import types
from contextlib import suppress
from copy import copy
from dataclasses import dataclass
from functools import lru_cache
from typing import (
    Annotated,
    Any,
    ClassVar,
    ForwardRef,
    Union,
    cast,
    get_args,
    get_origin,
)

from pydantic import BaseModel, ValidationError, create_model

from ..platform.json_bounds import JsonValue, bounded
from ._descriptors import ParamDescriptor
from ._model import ParamModel


@dataclass(frozen=True)
class InvalidRequest:
    """A complete decoded request does not match the endpoint/model schema."""

    detail: str = "Input does not match the viewer request schema."
    status_code: ClassVar[int] = 422
    code: ClassVar[str] = "invalid_request"


@lru_cache(maxsize=128)
def _declared_model(model_cls: type[BaseModel]) -> type[BaseModel]:
    """Derive one alias-free model graph so nested hooks run only in native validation."""
    names: dict[type[BaseModel], str] = {}

    def collect(annotation: Any) -> None:
        """Name the finite model graph before resolving any recursive references."""
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            if annotation in names:
                return
            names[annotation] = f"{annotation.__name__}ViewerInput{len(names)}"
            for field in annotation.model_fields.values():
                collect(field.annotation)
        else:
            for arg in get_args(annotation):
                collect(arg)

    def rewrite(annotation: Any) -> Any:
        """Retain declared container/union semantics and defer model graph references."""
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return ForwardRef(names[annotation])
        origin, args = get_origin(annotation), get_args(annotation)
        if origin is Annotated:
            return Annotated[(rewrite(args[0]), *args[1:])]
        if origin in (Union, types.UnionType):
            return Union[tuple(rewrite(arg) for arg in args)]  # noqa: UP007 -- runtime union reconstruction
        if origin in (list, tuple, dict):
            return origin[tuple(rewrite(arg) for arg in args)]
        return annotation

    collect(model_cls)
    models: dict[str, type[BaseModel]] = {}
    for original_cls, name in names.items():
        fields: dict[str, Any] = {}
        for field_name, original in original_cls.model_fields.items():
            field = copy(original)
            field.alias = None
            field.validation_alias = None
            fields[field_name] = (rewrite(field.annotation), field)
        derived = create_model(
            name, __base__=original_cls, __module__=__name__, **fields
        )
        # Only the private class changes. Keep older Pydantic 2.x support
        # without its newer by_name/by_alias model_validate arguments.
        derived.model_config = {
            **derived.model_config,
            "extra": "forbid",
            "alias_generator": None,
        }
        for field in derived.model_fields.values():
            field.alias = None
            field.validation_alias = None
        models[name] = derived
    for derived in models.values():
        derived.model_rebuild(force=True, _types_namespace=models)
    return models[names[model_cls]]


def _nested(annotation: Any, value: Any) -> Any:
    """Check raw declared names without constructing or validating nested models."""
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is Annotated:
        return _nested(args[0], value)
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        if (
            not isinstance(value, dict)
            or value.keys() - annotation.model_fields.keys()
        ):
            raise ValueError("Parameters must use declared field names")
        return {
            name: _nested(annotation.model_fields[name].annotation, child)
            for name, child in value.items()
        }
    if origin in (Union, types.UnionType):
        for branch in args:
            # A nonmatching scalar arm must not pass a raw object on to an
            # extra-allowing model arm in Pydantic's later union selection.
            base = (
                get_args(branch)[0]
                if get_origin(branch) is Annotated
                else branch
            )
            shape = get_origin(base) or base
            if (
                isinstance(value, dict)
                and shape not in (dict, Any)
                and not (
                    isinstance(shape, type) and issubclass(shape, BaseModel)
                )
            ):
                continue
            if isinstance(value, (list, tuple)) and shape not in (
                list,
                tuple,
                Any,
            ):
                continue
            try:
                return _nested(branch, value)
            except (ValueError, TypeError):
                continue
        raise ValueError("No declared nested shape matches")
    if origin in (list, tuple) and isinstance(value, (list, tuple)):
        item_types = (
            args
            if origin is tuple and args and args[-1] is not Ellipsis
            else None
        )
        return [
            _nested(
                item_types[index]
                if item_types and index < len(item_types)
                else args[0]
                if args
                else Any,
                child,
            )
            for index, child in enumerate(value)
        ]
    if origin is dict and isinstance(value, dict) and len(args) == 2:
        return {key: _nested(args[1], child) for key, child in value.items()}
    return value


def _validate_model(model_cls: type[BaseModel], value: Any) -> BaseModel:
    """Check raw field names, then run one complete native Pydantic validation pass."""
    return _declared_model(model_cls).model_validate(_nested(model_cls, value))


def parse_active(
    value: JsonValue,
    model_cls: type[ParamModel],
    descriptors: list[ParamDescriptor],
) -> ParamModel | InvalidRequest:
    """Apply documented list-text and numeric-choice coercion once, then validate natively.

    A numeric ``Literal`` choice arrives from a browser select, or from state the
    base viewer saved, as text (``"2"``; JS renders ``1.0`` as ``"1"``). Such text
    gets the base viewer's single ``int()``/``float()`` conversion; text that does
    not convert stays unchanged so native validation rejects it. Membership,
    bounds, nonfinite values and the caller's validators remain native.
    """
    if not isinstance(value, dict):
        return InvalidRequest()
    coerced: dict[str, Any] = dict(value)
    try:
        for descriptor in descriptors:
            item = coerced.get(descriptor.name)
            if descriptor.type_name.startswith("list_") and isinstance(
                item, str
            ):
                convert = {
                    "list_int": int,
                    "list_float": float,
                    "list_str": str,
                }[descriptor.type_name]
                coerced[descriptor.name] = [
                    convert(part.strip())
                    for part in item.split(",")
                    if part.strip()
                ]
            elif (
                descriptor.choices
                and descriptor.type_name in ("int", "float")
                and isinstance(item, str)
                and item not in descriptor.choices
            ):
                with suppress(ValueError):
                    coerced[descriptor.name] = (
                        int if descriptor.type_name == "int" else float
                    )(item)
        model = _validate_model(model_cls, coerced)
        if bounded(model.model_dump(mode="json", by_alias=False)) is not None:
            return InvalidRequest(
                "Parameters must remain bounded finite JSON values."
            )
    except (
        ValidationError,
        ValueError,
        TypeError,
        OverflowError,
        RecursionError,
    ):
        return InvalidRequest(
            "Parameters must use declared names and satisfy their types and constraints."
        )
    return cast(ParamModel, model)
