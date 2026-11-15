"""The guide resources' text: the bundled guidance files, by topic."""

from dartwork_mpl import guide


def guide_text(name: str) -> str:
    """The guidance file ``guide/<name>`` (``skill``, ``recipes``, ``anti-patterns`` ...)."""
    return guide.read(f"guide/{name}")
