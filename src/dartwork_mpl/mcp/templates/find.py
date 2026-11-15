"""The ``find_template`` reply: bundled templates ranked against a free-text intent."""

from typing import Any

from dartwork_mpl import guide


def find(intent: str, top_k: int, tier: str | None) -> list[dict[str, Any]]:
    """``dm.guide.search`` over the templates of ``tier`` (basic, advanced or all)."""
    if top_k < 1:
        return []
    wanted = {"basic"} if tier in (None, "basic") else {tier}
    if tier not in (None, "basic", "advanced"):
        wanted = {"basic", "advanced"}
    hits: list[dict[str, Any]] = []
    for ref in guide.search(intent, limit=len(guide.references())):
        if not ref.id.startswith("template/"):
            continue
        name = ref.id.removeprefix("template/")
        hit_tier = "advanced" if name.startswith("advanced/") else "basic"
        if hit_tier in wanted:
            hits.append(
                {
                    "template_id": name.removeprefix("advanced/"),
                    "tier": hit_tier,
                    "id": ref.id,
                    "title": ref.title,
                    "use_case": ref.summary,
                }
            )
    return hits[:top_k]
