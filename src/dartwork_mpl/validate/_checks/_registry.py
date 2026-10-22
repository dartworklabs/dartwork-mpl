"""Decorator-based registry for visual-validation checks and their fixes.

Each check self-registers with ``@register_check(id, order=...)`` so the
check id, its call site, and its run order all live in the check module
itself — instead of being hand-mirrored in a dict inside the
orchestrator, where a new or renamed check could silently drift out of
sync with its id (and, worse, run *zero* checks while reporting a figure
clean).

Each check's fix-suggestion handler registers here too, with
``@register_fix(id)`` next to the check in the same module (re-exported
as :func:`dartwork_mpl.validate_fixes.register_fix`), so a check and the
fix that reads its ``detail`` change in one file.

Every check is invoked uniformly as ``fn(fig, renderer)`` and returns a
``list[VisualWarning]``. Checks that don't need the renderer
(``check_empty_axes``) accept it as an unused parameter, exactly as
``check_pie_label_offset`` already does — so the orchestrator never has
to special-case a signature.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

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


# ───────────────────────────────────────────────────────
# Per-check fix-handler registry
# ───────────────────────────────────────────────────────
#
# Each handler takes the VisualWarning and returns a list of code-snippet
# strings the agent (or human reader) can apply. Handlers are pure —
# no side-effects, no figure mutation. A check's handler sits next to the
# check in its module under ``@register_fix("MY_CHECK_ID")``; no edits to
# ``get_fix_suggestions``, no edits to ``check_agent_requirements`` aside
# from optionally tracking the new check in its severity grouping.

FixHandler = Callable[[VisualWarning], list[str]]

_FIX_HANDLERS: dict[str, FixHandler] = {}


def register_fix(check_id: str) -> Callable[[FixHandler], FixHandler]:
    """Decorator: register a fix-suggestion handler under ``check_id``.

    The handler runs only when ``get_fix_suggestions(warning)`` is called
    with a warning whose ``check_id`` matches. Multiple registrations
    under the same ID raise — the dispatch table must stay
    deterministic.
    """

    def deco(fn: FixHandler) -> FixHandler:
        if check_id in _FIX_HANDLERS:
            raise RuntimeError(
                f"Duplicate fix handler registered for {check_id!r}"
            )
        _FIX_HANDLERS[check_id] = fn
        return fn

    return deco
