"""Public API stability contract tests."""

from __future__ import annotations

import inspect

import pytest

import dartwork_mpl as dm
from dartwork_mpl import _DEPRECATED_NAMES, _REMOVED_NAMES, _Deprecation


def test_deprecated_and_removed_are_disjoint() -> None:
    assert set(_DEPRECATED_NAMES) & set(_REMOVED_NAMES) == set()


def test_deprecated_names_not_advertised() -> None:
    assert set(_DEPRECATED_NAMES) & set(dm.__all__) == set()


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


def test_soft_deprecation_mechanism(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_name = "legacy_figsize_for_test"
    monkeypatch.setitem(
        _DEPRECATED_NAMES,
        fake_name,
        _Deprecation(
            target="figsize", since="0.6", removed_in="0.8", hint="dm.figsize"
        ),
    )

    with pytest.warns(DeprecationWarning, match="dm.legacy_figsize_for_test"):
        alias = getattr(dm, fake_name)

    assert alias is dm.figsize
