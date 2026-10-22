"""The ``find_template`` reply: bundled templates ranked against a free-text intent."""

from typing import Any


def find(intent: str, top_k: int, tier: str | None) -> list[dict[str, Any]]:
    """``dm.prompt.find_template(intent, top_k=top_k, tier=tier)`` (imported at call time)."""
    from dartwork_mpl.prompt import find_template as _find_template

    return _find_template(intent, top_k=top_k, tier=tier)
