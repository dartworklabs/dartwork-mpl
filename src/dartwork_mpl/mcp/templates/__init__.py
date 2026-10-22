"""The bundled plot templates and styles behind the MCP template tools and resources.

``find`` ranks templates for an intent, ``render_basic`` / ``render_advanced``
execute one to PNG, ``compose`` returns one with its annotation-layer
checklist, ``exists`` tells whether a template stem exists in a tier, and the
``*_list`` / ``*_source`` functions are the template and style resource
replies.
"""

from .bundled import (
    advanced_template_source,
    exists,
    style_list,
    style_source,
    template_list,
    template_source,
)
from .compose import compose
from .find import find
from .render import render_advanced, render_basic

__all__ = [
    "advanced_template_source",
    "compose",
    "exists",
    "find",
    "render_advanced",
    "render_basic",
    "style_list",
    "style_source",
    "template_list",
    "template_source",
]
