"""The API reference resources: the public-name index and one name's signature summary.

Both describe the namespace the caller passes in (the package root), so this
module imports no package entry point itself.
"""

import inspect
import json
from collections.abc import Iterable
from types import ModuleType


def api_index(public_names: Iterable[str]) -> str:
    """JSON array of ``public_names``, sorted."""
    return json.dumps(sorted(public_names), indent=2)


def api_entry(dm: ModuleType, name: str) -> str:
    """``name``'s signature and first docstring paragraph in namespace ``dm``, or not-found text."""
    if not hasattr(dm, name):
        return f"No public name {name!r}. See dartwork-mpl://api/index."
    obj = getattr(dm, name)
    try:
        sig = str(inspect.signature(obj))
    except (TypeError, ValueError):
        sig = "(...)"
    doc = inspect.getdoc(obj) or ""
    first_para = doc.split("\n\n", 1)[0]
    return f"{name}{sig}\n\n{first_para}"
