"""Legacy dc.* freeze + opt-in v5 remap (스펙 §11).

기본값: 구 토큰은 동결 hex 반환(시각 결과 불변, silent recolor 금지).
`set_palette_version(5)` 호출 시에만 충돌 토큰이 v5 로 remap 된다.
레거시 전용 토큰은 접근 시 1회 DeprecationWarning (최소 2 minor 후 제거).
"""

from __future__ import annotations

import warnings
from importlib.resources import files

import matplotlib.colors as mcolors

from ._loader import _load_json_palette, v5_collision_tokens

__all__ = ["LEGACY_TOKEN_NAMES", "set_palette_version", "warn_if_legacy"]


def _legacy_tokens() -> dict[str, str]:
    root = files("dartwork_mpl") / "asset" / "color"
    return _load_json_palette(root, "dc_palettes.json", "dc")


LEGACY_TOKEN_NAMES: frozenset[str] = frozenset(_legacy_tokens())
_COLLISIONS: dict[str, str] = v5_collision_tokens()  # token -> v5 hex
_FROZEN: dict[str, str] = {
    k: v for k, v in _legacy_tokens().items() if k in _COLLISIONS
}
_warned: set[str] = set()
_version: int = 4


def set_palette_version(v: int) -> None:
    """dc.* 충돌 토큰의 해석 버전 전환 — 4(동결 레거시, 기본) 또는 5(v5 remap).

    Parameters
    ----------
    v : int
        Target palette version. ``4`` restores the frozen legacy hex for
        every colliding ``dc.teal*``/``dc.indigo*``/``dc.gray*`` (0-7)
        token (matplotlib's default, visually unchanged). ``5`` remaps
        those same tokens to their v5 hex, updating matplotlib's named
        colour mapping in place (``dc.`` and the mirrored ``dm.`` alias).

    Raises
    ------
    ValueError
        If ``v`` is not ``4`` or ``5``.
    """
    global _version
    if v not in (4, 5):
        raise ValueError(f"palette version must be 4 or 5, got {v!r}")
    mapping = mcolors.get_named_colors_mapping()
    src = _COLLISIONS if v == 5 else _FROZEN
    for token, hexval in src.items():
        mapping[token] = hexval
        mapping["dm." + token[3:]] = hexval
    _version = v


def get_palette_version() -> int:
    """Return the active dc.* collision-token version (``4`` or ``5``).

    Internal accessor (not part of the public ``dm.`` surface) consumed
    by :func:`dartwork_mpl.helpers.colors.get_palette` to decide whether
    the legacy-curated ``teal``/``indigo``/``gray`` bare names return the
    frozen 8-step legacy ramp (default, v4) or the coherent 10-step v5
    ramp (after :func:`set_palette_version` (5)) — see spec §11 / Task 11.

    Returns
    -------
    int
        ``4`` (default) or ``5``.
    """
    return _version


def warn_if_legacy(name: str) -> None:
    """레거시 전용 dc.* 토큰 접근 시 1회 경고 (dm.color() 경로에서 호출).

    Parameters
    ----------
    name : str
        Fully-qualified ``dc.`` token name (e.g. ``"dc.vivid3"``). Tokens
        that also exist in v5 (the ``teal``/``indigo``/``gray`` 0-7
        collisions in :data:`_COLLISIONS`) are reachable via
        :func:`set_palette_version` and therefore do *not* warn — only
        legacy-only tokens with no v5 counterpart do.
    """
    if (
        name in LEGACY_TOKEN_NAMES
        and name not in _COLLISIONS
        and name not in _warned
    ):
        _warned.add(name)
        warnings.warn(
            f"color token {name!r} is a frozen v4 legacy token and will be "
            "removed after two minor releases; see the v5 migration guide.",
            DeprecationWarning,
            stacklevel=3,
        )
