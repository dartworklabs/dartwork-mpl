"""PIE_LABEL_OFFSET: donut chart label not centred in its wedge width."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .._types import Severity, VisualWarning

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure

__all__ = ["check_pie_label_offset"]

_TOLERANCE_RATIO = 0.15  # 15% deviation


def check_pie_label_offset(
    fig: Figure, _renderer: RendererBase
) -> list[VisualWarning]:
    """Detect donut chart labels that aren't centered in the wedge width.

    ``_renderer`` is accepted for signature parity with the other checks
    (so the orchestrator can call every handler uniformly) but is not
    used — donut label positions are read from axes-relative
    coordinates, no bbox measurement needed.
    """
    warnings: list[VisualWarning] = []

    for ax in fig.axes:
        # Identify pie wedges via theta1/theta2 attributes.
        wedges = [
            p
            for p in ax.patches
            if hasattr(p, "theta1") and hasattr(p, "theta2")
        ]
        if not wedges:
            continue

        # Outer radius of the pie. matplotlib Wedge patches carry ``.r``
        # (= the ``radius`` passed to ``ax.pie``); a hardcoded 1.0
        # misplaces the ideal for any non-unit pie and flags
        # geometrically-correct labels.
        radii = [getattr(w, "r", 1.0) or 1.0 for w in wedges]
        outer_r = sum(radii) / len(radii)

        # A filled pie has ``width=None`` (coerced to the outer radius);
        # a donut has a ring narrower than the radius. Compare as a
        # fraction of the radius so non-unit pies classify correctly.
        wedge_widths = [
            (getattr(w, "width", None) or r)
            for w, r in zip(wedges, radii, strict=False)
        ]
        if all(
            w >= 0.99 * r for w, r in zip(wedge_widths, radii, strict=False)
        ):
            continue  # regular pie, not a donut

        avg_width = sum(wedge_widths) / len(wedge_widths)
        # Ideal pctdistance = center of the donut ring.
        ideal_r = outer_r - avg_width / 2.0

        for txt in ax.texts:
            text_str = txt.get_text().strip()
            if not text_str.endswith("%"):
                continue
            x, y = txt.get_position()
            actual_r = (x**2 + y**2) ** 0.5
            if (
                ideal_r > 0
                and abs(actual_r - ideal_r) / ideal_r > _TOLERANCE_RATIO
            ):
                warnings.append(
                    VisualWarning(
                        severity=Severity.INFO,
                        check_id="PIE_LABEL_OFFSET",
                        message=(
                            f"Donut label '{text_str}' at r={actual_r:.2f}, "
                            f"ideal center of wedge: r={ideal_r:.2f}"
                        ),
                        detail={
                            "text": text_str,
                            "actual_r": round(actual_r, 2),
                            "ideal_r": round(ideal_r, 2),
                        },
                    )
                )
        break  # only check the first pie axes

    return warnings
