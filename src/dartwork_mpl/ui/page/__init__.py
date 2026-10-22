"""The viewer's single HTML page: markup, CSS and JS, served at ``/``.

The JS reads the ``/api/descriptors`` keys and calls every route, so this
package is the client half of the wire contract. Surface: ``get_html``,
``routes`` (the page, ``/api/meta`` and ``/api/health``) and ``GRANTS``.
"""

from ._routes import GRANTS, routes
from ._template import get_html

__all__ = ["GRANTS", "get_html", "routes"]
