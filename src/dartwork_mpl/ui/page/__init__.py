"""The viewer's single HTML page: markup, CSS and JS, served at ``/``.

The JS reads the ``/api/descriptors`` keys and calls every route, so this
package is the client half of the wire contract. Surface: ``get_html``.
"""

from ._template import get_html

__all__ = ["get_html"]
