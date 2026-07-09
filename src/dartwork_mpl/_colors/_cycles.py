"""Categorical cycles — 스펙 §8 전수 탐색 결과의 동결 스펙.

탐색(ΔE00 게이트 + 라인 안전 대역)은 설계 단계에서 끝났다. 여기서는 (family,
step) 좌표만 동결하고, 빌드가 팔레트에 적용해 hex를 얻은 뒤 게이트를 재검증한다.
"""

from __future__ import annotations

__all__ = ["CYCLE_SPECS", "cycle_hexes"]

CYCLE_SPECS: dict[str, tuple[tuple[str, int], ...]] = {
    # Octave: 기본 8 chromatic — 라인 안전(L* 42~78, CR>=2.2), 공통-CVD dE00 10.3 · tritan 8.3 (BVM).
    # gray는 격자·기준선용으로 예약(멤버 아님 — 스펙 §8).
    "octave": (
        ("blue", 6),
        ("orange", 9),
        ("green", 5),
        ("pink", 3),
        ("amber", 7),
        ("violet", 8),
        ("cyan", 8),
        ("rose", 8),
    ),
    # Octave Print: 인쇄 8색 — Octave와 hue-parallel(6번 violet 일치, 8번 gray anchor).
    # 명도 분산(전쌍 dL* >= 7.7), 공통-CVD dE00 10.4 · tritan 9.8 (BVM).
    "octave_print": (
        ("blue", 5),
        ("orange", 8),
        ("green", 1),
        ("pink", 2),
        ("amber", 5),
        ("violet", 9),
        ("cyan", 8),
        ("gray", 9),
    ),
}


def cycle_hexes(name: str, palette: dict[str, list[str]]) -> list[str]:
    return [palette[fam][step] for fam, step in CYCLE_SPECS[name]]
