"""A7 hard gates — 실패한 산출물은 출하 불가 (스펙 §5 A7·§9)."""

from __future__ import annotations

import math

from ._metrics import (
    cvd_rgb,
    de2000_hex,
    de_ok_rgb,
    hex_from_rgb,
    lab_l_hex,
    rgb_from_hex,
)

__all__ = [
    "check_all",
    "gate_cycle",
    "gate_cyclic_cmap",
    "gate_div_cmap",
    "gate_ladder",
    "gate_seq_cmap",
    "gate_topo_cmap",
]

_CVD_KINDS = ("protan", "deutan", "tritan")


def _cv(hexes: list[str]) -> float:
    rgbs = [rgb_from_hex(h) for h in hexes]
    d = [de_ok_rgb(rgbs[i], rgbs[i + 1]) for i in range(len(rgbs) - 1)]
    m = sum(d) / len(d)
    return math.sqrt(sum((x - m) ** 2 for x in d) / len(d)) / m


def _mono(ls: list[float], tol: float = 0.0) -> bool:
    return all(ls[i] > ls[i + 1] - tol for i in range(len(ls) - 1)) or all(
        ls[i] < ls[i + 1] + tol for i in range(len(ls) - 1)
    )


def gate_ladder(hexes: list[str]) -> dict[str, bool | float]:
    ls = [lab_l_hex(h) for h in hexes]
    return {
        "mono": all(ls[i] > ls[i + 1] for i in range(len(ls) - 1)),
        "cv": round(_cv(hexes), 4),
    }


def gate_cycle(hexes: list[str]) -> dict[str, float]:
    """Worst-case pairwise ΔE00 per vision type, reported separately.

    Tritan is gated on its own, lower floor. It is the rare S-cone deficiency,
    and the physiologically accurate Brettel-Viénot-Mollon (1997) model — used
    for tritan instead of Machado's fitted extrapolation — shows the achievable
    tritan separation for a 7-hue cycle tops out near 9, well below the common
    red-green floor. So ``common_min`` (normal + protan + deutan) is held to 10
    while ``tritan`` is held to a realistic 8; ``min00`` is the overall worst
    for reference.
    """
    per: dict[str, float] = {}
    for kind in ("normal", *_CVD_KINDS):
        if kind == "normal":
            sim = hexes
        else:
            sim = [hex_from_rgb(cvd_rgb(rgb_from_hex(h), kind)) for h in hexes]
        per[kind] = round(
            min(
                de2000_hex(sim[i], sim[j])
                for i in range(len(sim))
                for j in range(i + 1, len(sim))
            ),
            1,
        )
    per["common_min"] = min(per["normal"], per["protan"], per["deutan"])
    per["min00"] = min(per["common_min"], per["tritan"])
    return per


def gate_seq_cmap(hexes: list[str]) -> dict[str, bool | float]:
    """32-stop 직접 렌더 스와치 기준. 단조 허용오차 0.4 L* = 8-bit 그래뉼."""
    ls = [lab_l_hex(h) for h in hexes]
    gl = [
        lab_l_hex(hex_from_rgb(cvd_rgb(rgb_from_hex(h), "gray"))) for h in hexes
    ]
    return {
        "mono": _mono(ls, 0.4),
        "gray_mono": _mono(gl, 0.4),
        "cv": round(_cv(hexes), 3),
        "L_span": round(abs(ls[-1] - ls[0]), 1),
    }


def gate_div_cmap(hexes: list[str]) -> dict[str, float]:
    """Diverging: the brightest region must sit at the center (apex 50%).

    Reports the midpoint of the max-L* plateau (within 0.5 L* = one 8-bit
    granule), NOT a single argmax. A symmetric diverging sampled to an EVEN
    length has its true apex *between* the two center swatches (e.g. indices
    15/16 of a 32-stop), which are equally bright by construction — a single
    ``.index(max())`` biases to one side and reads 48.4%. The plateau midpoint
    lands at exactly 50% for a symmetric map of any parity, and drifts off 50%
    (flagging the gate) only when the arms are genuinely asymmetric.
    """
    ls = [lab_l_hex(h) for h in hexes]
    top = max(ls)
    plateau = [i for i, v in enumerate(ls) if v >= top - 0.5]
    apex = (plateau[0] + plateau[-1]) / 2
    return {"apex_pct": round(100 * apex / (len(ls) - 1), 1)}


def gate_topo_cmap(hexes: list[str]) -> dict[str, bool | float]:
    mid = len(hexes) // 2

    def half_mono(seg: list[str]) -> bool:
        return _mono([lab_l_hex(h) for h in seg], 0.4)

    return {
        "sea_mono": half_mono(hexes[:mid]),
        "land_mono": half_mono(hexes[mid:]),
        "coast_break_dL": round(
            abs(lab_l_hex(hexes[mid]) - lab_l_hex(hexes[mid - 1])), 1
        ),
    }


def gate_cyclic_cmap(hexes: list[str]) -> dict[str, float]:
    rgbs = [rgb_from_hex(h) for h in hexes]
    d = [de_ok_rgb(rgbs[i], rgbs[i + 1]) for i in range(len(rgbs) - 1)]
    seam = de_ok_rgb(rgbs[-1], rgbs[0])
    return {"seam_ratio": round(seam / (sum(d) / len(d)), 2)}


def check_all(
    palette: dict[str, list[str]],
    cycles: dict[str, list[str]],
    cmaps: dict[str, list[str]],
) -> list[str]:
    """빌드 게이트 러너 — 위반 메시지 리스트 반환 (빈 리스트 = 전부 통과)."""
    bad: list[str] = []
    for fam, row in palette.items():
        g = gate_ladder(row)
        if not g["mono"]:
            bad.append(f"palette {fam}: L* not monotone")
        if g["cv"] > 0.08:
            bad.append(f"palette {fam}: cv {g['cv']} > 0.08")
    for name, hexes in cycles.items():
        g_cycle = gate_cycle(hexes)
        if g_cycle["common_min"] < 10.0:
            bad.append(
                f"cycle {name}: common-CVD dE00 {g_cycle['common_min']} < 10"
            )
        if g_cycle["tritan"] < 8.0:
            bad.append(f"cycle {name}: tritan dE00 {g_cycle['tritan']} < 8")
    for name, hexes in cmaps.items():
        kind = name.split(".", 1)[0]
        if kind == "div":
            if gate_div_cmap(hexes)["apex_pct"] != 50.0:
                bad.append(f"cmap {name}: apex != 50%")
        elif kind == "topo":
            g_topo = gate_topo_cmap(hexes)
            if not (g_topo["sea_mono"] and g_topo["land_mono"]):
                bad.append(f"cmap {name}: half not monotone")
        elif kind == "cyc":
            if gate_cyclic_cmap(hexes)["seam_ratio"] > 1.5:
                bad.append(f"cmap {name}: seam ratio > 1.5")
        else:
            g_seq = gate_seq_cmap(hexes)
            if not (g_seq["mono"] and g_seq["gray_mono"]):
                bad.append(f"cmap {name}: mono/gray_mono fail")
    return bad
