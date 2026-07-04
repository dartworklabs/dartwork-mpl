"""Categorical cycles — 스펙 §8 전수 탐색 결과의 동결 스펙.

탐색(ΔE00 게이트 + 라인 안전 대역)은 설계 단계에서 끝났다. 여기서는 (family,
step) 좌표만 동결하고, 빌드가 팔레트에 적용해 hex를 얻은 뒤 게이트를 재검증한다.
"""

from __future__ import annotations

__all__ = ["CYCLE_SPECS", "cycle_hexes"]

CYCLE_SPECS: dict[str, tuple[tuple[str, int], ...]] = {
    # 기본 7 chromatic — 라인 안전(L* 42~78, CR>=2.2), 공통-CVD dE00 10.3 · tritan 9.0 (BVM).
    # gray는 격자·기준선용으로 예약(멤버 아님 — 스펙 §8).
    "default": (
        ("blue", 6),
        ("orange", 9),
        ("green", 5),
        ("pink", 3),
        ("amber", 7),
        ("violet", 8),
        ("cyan", 8),
    ),
    # 인쇄 8색 — 명도 분산(전쌍 dL* >= 6.1), 공통-CVD dE00 13.5 · tritan 8.5 (BVM).
    "print": (
        ("blue", 9),
        ("orange", 2),
        ("green", 9),
        ("pink", 6),
        ("amber", 6),
        ("purple", 5),
        ("cyan", 3),
        ("gray", 8),
    ),
}


def cycle_hexes(name: str, palette: dict[str, list[str]]) -> list[str]:
    return [palette[fam][step] for fam, step in CYCLE_SPECS[name]]
