"""Guide text for the MCP guide/API resources and the two MCP prompts.

``guide_text`` is the guide resources' reply; ``api_index`` and ``api_entry`` describe a public
namespace; ``create_plot_text`` and ``style_review_text`` render the prompts.
"""

from .api import api_entry, api_index
from .corpus import guide_text
from .prompts import create_plot_text, style_review_text

__all__ = [
    "api_entry",
    "api_index",
    "create_plot_text",
    "guide_text",
    "style_review_text",
]
