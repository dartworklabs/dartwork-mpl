"""Colour lookups behind the colour tools and the ``dartwork-mpl://palette/colors`` resource.

Each function returns the tool's exact reply string; lookup and blending
failures become messages, not exceptions.
"""

import json
import math
from collections.abc import Sequence

import matplotlib.colors as mcolors


def color_value(name: str) -> str:
    """Hex code of a registered colour name, or a not-found message naming up to five similar names."""
    try:
        return mcolors.to_hex(mcolors.get_named_colors_mapping()[name])
    except KeyError:
        # Suggest similar colors
        all_names = list(mcolors.get_named_colors_mapping().keys())
        suggestions = [n for n in all_names if name.lower() in n.lower()][:5]
        msg = f"Color '{name}' not found."
        if suggestions:
            msg += f" Similar: {suggestions}"
        return msg


def mix(color1: str, color2: str, ratio: float) -> str:
    """Hex code of ``dm.mix_colors(color1, color2, alpha=ratio)``.

    A non-finite ratio, one outside [0, 1], or an unknown colour returns an
    ``Error ...`` message instead.
    """
    # Validate ``ratio`` up front: an out-of-[0, 1] or non-finite
    # weight extrapolates beyond the two endpoints, yielding RGB
    # outside [0, 1] and a malformed hex. Reject it with an
    # actionable message instead of leaking matplotlib's downstream
    # "RGBA values should be within 0-1 range" / NaN errors.
    if not math.isfinite(ratio):
        return (
            "Error: ratio must be a finite number between 0.0 and 1.0 "
            f"(weight of color1), got {ratio!r}."
        )
    if not 0.0 <= ratio <= 1.0:
        return (
            "Error: ratio must be between 0.0 and 1.0 "
            f"(weight of color1), got {ratio!r}."
        )
    from ..._colors.blend import mix_colors as _mix_oklab

    try:
        return mcolors.to_hex(_mix_oklab(color1, color2, alpha=ratio))
    except (ValueError, KeyError, TypeError) as e:
        # ``to_rgb`` (inside the public helper) raises ``ValueError``
        # for unknown / malformed colors and ``KeyError`` for missing
        # names; ``TypeError`` for non-string inputs. We intentionally
        # do not surface the full traceback to the agent — the
        # message is enough.
        return f"Error blending colors: {e}"


def list_families(libraries: Sequence[tuple[str, str, str, str]]) -> str:
    """JSON object of registered colours per library prefix: count and first five samples.

    ``libraries`` are ``(key, prefix, source, label)`` rows in display order;
    prefixes with no registered colour are omitted.
    """
    mapping = mcolors.get_named_colors_mapping()
    prefixes = [prefix for _key, prefix, _fn, _label in libraries]
    families = {}
    for prefix in prefixes:
        colors = {
            k: mcolors.to_hex(v)
            for k, v in mapping.items()
            if k.startswith(prefix)
        }
        if colors:
            sample = dict(list(colors.items())[:5])
            families[prefix.rstrip(".")] = {
                "count": len(colors),
                "sample": sample,
            }
    return json.dumps(families, indent=2)


def palette(libraries: Sequence[tuple[str, str, str, str]]) -> str:
    """JSON object of every registered colour under a library prefix: name -> hex.

    ``libraries`` are ``(key, prefix, source, label)`` rows
    (``dartwork-mpl://palette/colors``).
    """
    prefixes = [prefix for _key, prefix, _fn, _label in libraries]
    colors = {
        k: mcolors.to_hex(v)
        for k, v in mcolors.get_named_colors_mapping().items()
        if any(k.startswith(prefix) for prefix in prefixes)
    }
    return json.dumps(colors, indent=2)
