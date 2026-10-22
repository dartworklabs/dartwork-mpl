"""The font list behind the ``dartwork-mpl://palette/fonts`` resource."""

import json

from matplotlib import font_manager


def font_names() -> str:
    """JSON array of the distinct font family names matplotlib has registered, sorted."""
    fonts = sorted({f.name for f in font_manager.fontManager.ttflist})
    return json.dumps(fonts, indent=2)
