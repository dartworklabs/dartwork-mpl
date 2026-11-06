"""Public API stability contract tests."""

from __future__ import annotations

import inspect

import dartwork_mpl as dm


def test_removed_names_are_not_advertised() -> None:
    from dartwork_mpl._compat import _REMOVED_NAMES

    assert set(_REMOVED_NAMES) & set(dm.__all__) == set()


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
