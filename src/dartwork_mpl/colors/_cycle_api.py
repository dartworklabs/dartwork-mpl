"""Categorical cycle API — hex 접근 + 선스타일 병행 cycler (스펙 §8)."""

from __future__ import annotations

from cycler import Cycler, cycler

from ._generated import CYCLES

__all__ = ["cycle", "cycle_cycler"]

_ALIASES = {"default": "octave", "print": "octave_print"}


def _canonical_name(name: str) -> str:
    return _ALIASES.get(name, name)


def cycle(name: str = "octave") -> list[str]:
    """Return the hex color list for a named categorical cycle.

    Parameters
    ----------
    name : str
        Cycle name. ``"octave"`` is the 8-color screen/PDF cycle;
        ``"octave_print"`` is the 8-color CVD-verified variant tuned for
        print reproduction. The legacy names ``"default"`` and
        ``"print"`` are silent aliases for ``"octave"`` and
        ``"octave_print"``.

    Returns
    -------
    list[str]
        Hex color strings, in cycle order. A fresh list is returned on
        each call, so callers may mutate it without affecting the
        registered cycle.

    Raises
    ------
    KeyError
        If ``name`` is not a registered cycle.
    """
    key = _canonical_name(name)
    if key not in CYCLES:
        raise KeyError(f"unknown cycle {name!r} — available: {sorted(CYCLES)}")
    return list(CYCLES[key])


def cycle_cycler(
    name: str = "octave", linestyles: tuple[str, ...] = ("-", "--", ":")
) -> Cycler[str, str]:
    """색이 먼저 순환하고, 색 재사용이 시작되는 시리즈부터 선스타일이 바뀐다."""
    return cycler(linestyle=list(linestyles)) * cycler(color=cycle(name))
