"""Categorical cycle API — hex 접근 + 선스타일 병행 cycler (스펙 §8)."""

from __future__ import annotations

from cycler import Cycler, cycler

from ._generated import CYCLES

__all__ = ["cycle", "cycle_cycler"]


def cycle(name: str = "default") -> list[str]:
    """Return the hex color list for a named categorical cycle.

    Parameters
    ----------
    name : str
        Cycle name. ``"default"`` is the 7-color screen/PDF cycle;
        ``"print"`` is the 8-color CVD-verified variant tuned for print
        reproduction.

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
    if name not in CYCLES:
        raise KeyError(f"unknown cycle {name!r} — available: {sorted(CYCLES)}")
    return list(CYCLES[name])


def cycle_cycler(
    name: str = "default", linestyles: tuple[str, ...] = ("-", "--", ":")
) -> Cycler[str, str]:
    """색이 먼저 순환하고, 색 재사용이 시작되는 시리즈부터 선스타일이 바뀐다."""
    return cycler(linestyle=list(linestyles)) * cycler(color=cycle(name))
