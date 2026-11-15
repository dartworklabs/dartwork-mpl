"""Public API stability contract tests."""

from __future__ import annotations

import inspect

import dartwork_mpl as dm


def test_all_public_names_are_importable() -> None:
    for name in dm.__all__:
        getattr(dm, name)


def test_public_callables_have_docstrings() -> None:
    missing: list[str] = []
    for name in dm.__all__:
        obj = getattr(dm, name)
        if (inspect.isfunction(obj) or inspect.isclass(obj)) and (
            obj.__doc__ is None or not obj.__doc__.strip()
        ):
            missing.append(name)

    assert missing == []


def test_experimental_subset_of_public() -> None:
    for name in dm.EXPERIMENTAL:
        getattr(dm, name)
