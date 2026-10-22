"""Guide text for the MCP guide/API resources and the two MCP prompts.

``guide_text``, ``anti_pattern_catalog`` and ``migration_pointer`` are the
guide resources' replies; ``api_index`` and ``api_entry`` describe a public
namespace; ``create_plot_text`` and ``style_review_text`` render the prompts.
"""

from .api import api_entry, api_index
from .corpus import anti_pattern_catalog, guide_text, migration_pointer
from .prompts import create_plot_text, style_review_text

__all__ = [
    "anti_pattern_catalog",
    "api_entry",
    "api_index",
    "create_plot_text",
    "guide_text",
    "migration_pointer",
    "style_review_text",
]
