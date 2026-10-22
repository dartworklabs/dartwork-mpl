"""Business-agnostic mechanism shared by the viewer's sub-slices (ADR 0005).

Four platform units, each its own surface: ``access`` (loopback binds and
per-request Host/Origin checks against a caller-supplied grant table),
``fs`` (startup directory handles and no-follow file primitives), ``http``
(bounded JSON request bodies and the detail/code refusal response) and
``json_bounds`` (the bounded JSON decoder and limits). None of them imports
a viewer slice. This package initializer only names them.
"""

__all__ = ["access", "fs", "http", "json_bounds"]
