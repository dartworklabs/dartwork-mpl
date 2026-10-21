"""Pydantic-based parameter model for declarative UI specification.

This module provides the ``ParamModel`` base class that users can
subclass to define figure-generator parameters with rich metadata
(ranges, step sizes, choices, widget hints) that the UI module
translates into Streamlit widgets automatically.
"""

from __future__ import annotations

from pydantic import BaseModel


class ParamModel(BaseModel):
    """Base class for declarative parameter UI specification.

    Subclass this and use ``pydantic.Field`` to declare parameters
    with constraints that map to Streamlit widgets:

    * ``ge`` / ``le`` → slider min/max
    * ``gt`` / ``lt`` → number_input bounds (exclusive)
    * ``Literal[...]`` type → selectbox
    * ``json_schema_extra={"widget": "color"}`` → color_picker
    * ``description`` → widget label

    Examples
    --------
    >>> from pydantic import Field
    >>> from typing import Literal
    >>>
    >>> class PlotParams(ParamModel):
    ...     n_points: int = Field(
    ...         default=100, ge=10, le=1000,
    ...         description="Number of data points",
    ...     )
    ...     alpha: float = Field(
    ...         default=0.5, ge=0.0, le=1.0,
    ...         description="Transparency",
    ...     )
    ...     style: Literal["solid", "dashed", "dotted"] = Field(
    ...         default="solid",
    ...     )
    ...     color: str = Field(
    ...         default="#1f77b4",
    ...         json_schema_extra={"widget": "color"},
    ...     )
    """

    model_config = {"arbitrary_types_allowed": True}
