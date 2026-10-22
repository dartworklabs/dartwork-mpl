"""The viewer's complete local-only route grant table, composed from each sub-slice's ``GRANTS``.

The approved local-only policy grants these effects to native local clients.
Host and browser source checks (``platform.access``) constrain that grant;
they are not identity. Every registered route needs an entry here; the
framework's documentation routes and the explicit unmatched-read marker are
listed directly, as is the entry point's own ``/api/reload``.
"""

from . import page, params, render, script, state
from .platform.access import Grant

ROUTE_POLICY: dict[tuple[str, str], Grant] = {
    ("GET", "/openapi.json"): "local-read",
    ("HEAD", "/openapi.json"): "local-read",
    ("GET", "/docs"): "local-read",
    ("HEAD", "/docs"): "local-read",
    ("GET", "/docs/oauth2-redirect"): "local-read",
    ("HEAD", "/docs/oauth2-redirect"): "local-read",
    ("GET", "/redoc"): "local-read",
    ("HEAD", "/redoc"): "local-read",
    ("GET", "<unmatched>"): "local-read",
    ("HEAD", "<unmatched>"): "local-read",
    ("POST", "/api/reload"): "local-effect",
    **page.GRANTS,
    **params.GRANTS,
    **render.GRANTS,
    **script.GRANTS,
    **state.GRANTS,
}
