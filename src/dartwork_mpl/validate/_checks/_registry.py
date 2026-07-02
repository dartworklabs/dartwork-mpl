"""Decorator-based registry for visual-validation checks.

Each check self-registers with ``@register_check(id, order=...)`` so the
check id, its call site, and its run order all live in the check module
itself — instead of being hand-mirrored in a dict inside the
orchestrator, where a new or renamed check could silently drift out of
sync with its id (and, worse, run *zero* checks while reporting a figure
clean).

Mirrors the ``register_fix`` registry in
:mod:`dartwork_mpl.validate_fixes` and the ``Rule`` registry in
:mod:`dartwork_mpl.lint` — one decorator per unit, all discoverable
through a single dispatcher.

Every check is invoked uniformly as ``fn(fig, renderer)`` and returns a
``list[VisualWarning]``. Checks that don't need the renderer
(``check_empty_axes``) accept it as an unused parameter, exactly as
``check_pie_label_offset`` already does — so the orchestrator never has
to special-case a signature.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from .._types import VisualWarning

# Identity-decorator TypeVar: registering a check returns the *same*
# function with its exact signature preserved (so ``check_overflow``
# stays typed as ``(Figure, RendererBase) -> list[VisualWarning]`` for
# any direct caller), while the registry stores it under the loose
# ``Callable[..., list[VisualWarning]]`` the orchestrator invokes.
CheckFn = TypeVar("CheckFn", bound="Callable[..., list[VisualWarning]]")


@dataclass(frozen=True)
class RegisteredCheck:
    """A registered check: its id, run order, and callable."""

    check_id: str
    order: int
    fn: Callable[..., list[VisualWarning]]


_REGISTRY: dict[str, RegisteredCheck] = {}


def register_check(
    check_id: str, *, order: int
) -> Callable[[CheckFn], CheckFn]:
    """Register a visual-validation check under ``check_id``.

    Parameters
    ----------
    check_id : str
        The public id reported in ``VisualWarning.check_id`` and accepted
        by ``validate_figure(checks=...)``. Must be unique.
    order : int
        Deterministic run/report position — lower runs first. The
        historical order is ``10, 20, ... 90`` in steps of ten, leaving
        room to slot a new check between two existing ones.

    Duplicate ids raise, keeping the dispatch table unambiguous — the
    same contract ``register_fix`` enforces.
    """

    def deco(fn: CheckFn) -> CheckFn:
        if check_id in _REGISTRY:
            raise RuntimeError(f"Duplicate check registered for {check_id!r}")
        _REGISTRY[check_id] = RegisteredCheck(check_id, order, fn)
        return fn

    return deco


def registered_checks() -> list[RegisteredCheck]:
    """Every registered check, ordered by ``(order, check_id)``.

    Sorting by id as a tie-breaker keeps the sequence stable even if two
    checks were ever registered at the same ``order``.
    """
    return sorted(_REGISTRY.values(), key=lambda c: (c.order, c.check_id))
