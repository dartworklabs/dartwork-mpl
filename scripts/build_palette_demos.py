"""Palette demo renders for the interactive picker on the colors page.

Renders **one demo PoC** in every cataloged palette so the
`usage_guide/colors.md` page can swap between them with a single click.
The demo is a 1x2 panel that exercises every palette color:

- **Left** — six staggered sine series so the eye can compare adjacent
  hues for line-chart legibility.
- **Right** — six categorical bars so the same six colors are visible
  in solid-fill form (the use case where a palette breaks down first).

Palette catalog is grouped by namespace so the picker UI can show
section headers (dc, oc, tw, md, ad, cu, pr).

Each render reuses the `_draw_palette_demo` helper below so chart
content is byte-identical across palettes — only the `axes.prop_cycle`
override changes between renders.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
# Deterministic SVG output — fixed hash salt yields stable element IDs so
# regenerating this demo set produces byte-identical SVGs, not a diff.
matplotlib.rcParams["svg.hashsalt"] = "dartwork-mpl"

import matplotlib.pyplot as plt

import dartwork_mpl as dm

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

# Reuse the canonical sizing from the main PoC builder.
from build_landing_pocs import LANDING_W_DM

OUT = ROOT / "docs" / "_static" / "palette_demo"
OUT.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Palette catalog
# ---------------------------------------------------------------------------
#
# Each entry: { id, label, namespace, swatch (display hint), colors (prop_cycle) }
#
# - `dc.*` 8 mood families ship as light→dark ramps inside one hue
#   family, so the categorical view here picks the most readable
#   shades from the ramp.
# - Third-party namespaces (oc/tw/md/ad/cu/pr) have many hues but only
#   shade ramps within each hue. To make them categorical we mix
#   hues at a single shade level. Six hues each.

PALETTES: list[dict] = [
    # ---- dc.* curated (8 representative palettes) ----
    {
        "id": "dc.vivid",
        "label": "dc.vivid",
        "namespace": "dc",
        "colors": [
            "dc.vivid1",
            "dc.vivid3",
            "dc.vivid0",
            "dc.vivid5",
            "dc.vivid2",
            "dc.vivid4",
        ],
    },
    {
        "id": "dc.teal",
        "label": "dc.teal",
        "namespace": "dc",
        "colors": [
            "dc.teal3",
            "dc.teal1",
            "dc.teal5",
            "dc.teal0",
            "dc.teal2",
            "dc.teal4",
        ],
    },
    {
        "id": "dc.forest",
        "label": "dc.forest",
        "namespace": "dc",
        "colors": [
            "dc.forest3",
            "dc.forest1",
            "dc.forest5",
            "dc.forest0",
            "dc.forest2",
            "dc.forest4",
        ],
    },
    {
        "id": "dc.earth",
        "label": "dc.earth",
        "namespace": "dc",
        "colors": [
            "dc.earth2",
            "dc.earth4",
            "dc.earth0",
            "dc.earth5",
            "dc.earth1",
            "dc.earth3",
        ],
    },
    {
        "id": "dc.dusty",
        "label": "dc.dusty",
        "namespace": "dc",
        "colors": [
            "dc.dusty3",
            "dc.dusty1",
            "dc.dusty5",
            "dc.dusty0",
            "dc.dusty2",
            "dc.dusty4",
        ],
    },
    {
        "id": "dc.jewel",
        "label": "dc.jewel",
        "namespace": "dc",
        "colors": [
            "dc.jewel3",
            "dc.jewel1",
            "dc.jewel5",
            "dc.jewel0",
            "dc.jewel2",
            "dc.jewel4",
        ],
    },
    {
        "id": "dc.neon",
        "label": "dc.neon",
        "namespace": "dc",
        "colors": [
            "dc.neon3",
            "dc.neon1",
            "dc.neon5",
            "dc.neon0",
            "dc.neon2",
            "dc.neon4",
        ],
    },
    {
        "id": "dc.teal_indigo",
        "label": "dc.teal_indigo",
        "namespace": "dc",
        "colors": [
            "dc.teal_indigo3",
            "dc.teal_indigo1",
            "dc.teal_indigo5",
            "dc.teal_indigo0",
            "dc.teal_indigo2",
            "dc.teal_indigo4",
        ],
    },
    # ---- oc.* (OpenColor) categorical mixes ----
    {
        "id": "oc.classic",
        "label": "oc.classic",
        "namespace": "oc",
        "colors": [
            "oc.blue6",
            "oc.red6",
            "oc.green6",
            "oc.orange6",
            "oc.violet6",
            "oc.teal6",
        ],
    },
    {
        "id": "oc.cool",
        "label": "oc.cool",
        "namespace": "oc",
        "colors": [
            "oc.blue6",
            "oc.cyan6",
            "oc.teal6",
            "oc.green6",
            "oc.indigo6",
            "oc.violet6",
        ],
    },
    {
        "id": "oc.warm",
        "label": "oc.warm",
        "namespace": "oc",
        "colors": [
            "oc.red6",
            "oc.orange6",
            "oc.yellow6",
            "oc.pink6",
            "oc.grape6",
            "oc.lime6",
        ],
    },
    {
        "id": "oc.muted",
        "label": "oc.muted",
        "namespace": "oc",
        "colors": [
            "oc.blue4",
            "oc.red4",
            "oc.green4",
            "oc.orange4",
            "oc.violet4",
            "oc.teal4",
        ],
    },
    # ---- tw.* (Tailwind) categorical mixes ----
    {
        "id": "tw.modern",
        "label": "tw.modern",
        "namespace": "tw",
        "colors": [
            "tw.indigo500",
            "tw.rose500",
            "tw.emerald500",
            "tw.amber500",
            "tw.violet500",
            "tw.cyan500",
        ],
    },
    {
        "id": "tw.muted",
        "label": "tw.muted",
        "namespace": "tw",
        "colors": [
            "tw.slate500",
            "tw.zinc500",
            "tw.stone500",
            "tw.neutral500",
            "tw.slate400",
            "tw.zinc400",
        ],
    },
    {
        "id": "tw.bold",
        "label": "tw.bold",
        "namespace": "tw",
        "colors": [
            "tw.blue600",
            "tw.red600",
            "tw.green600",
            "tw.purple600",
            "tw.orange600",
            "tw.pink600",
        ],
    },
    # ---- md.* (Material) ----
    {
        "id": "md.material",
        "label": "md.material",
        "namespace": "md",
        "colors": [
            "md.blue500",
            "md.red500",
            "md.green500",
            "md.orange500",
            "md.purple500",
            "md.teal500",
        ],
    },
    {
        "id": "md.bright",
        "label": "md.bright",
        "namespace": "md",
        "colors": [
            "md.lightBlue400",
            "md.pink400",
            "md.lightGreen400",
            "md.amber400",
            "md.deepPurple400",
            "md.cyan400",
        ],
    },
    # ---- ad.* (Ant Design) ----
    {
        "id": "ad.classic",
        "label": "ad.classic",
        "namespace": "ad",
        "colors": [
            "ad.blue6",
            "ad.red6",
            "ad.green6",
            "ad.orange6",
            "ad.purple6",
            "ad.cyan6",
        ],
    },
    # ---- cu.* (Chakra UI) ----
    {
        "id": "cu.brand",
        "label": "cu.brand",
        "namespace": "cu",
        "colors": [
            "cu.blue500",
            "cu.red500",
            "cu.green500",
            "cu.orange500",
            "cu.purple500",
            "cu.teal500",
        ],
    },
    # ---- pr.* (Primer / GitHub) ----
    {
        "id": "pr.brand",
        "label": "pr.brand",
        "namespace": "pr",
        "colors": [
            "pr.blue5",
            "pr.red5",
            "pr.green5",
            "pr.orange5",
            "pr.purple5",
            "pr.pink5",
        ],
    },
]


def _resolve_hex(name: str) -> str:
    """Resolve a dartwork-mpl color string to a `#RRGGBB` hex."""
    import matplotlib.colors as mc

    try:
        return mc.to_hex(mc.to_rgba(name))
    except Exception:  # noqa: BLE001  (one-off PoC tooling, any failure → fallback)
        return "#cccccc"


def _apply_palette(colors: list[str]) -> None:
    from cycler import cycler

    matplotlib.rcParams["axes.prop_cycle"] = cycler(color=colors)


def _draw_palette_demo(axes) -> None:
    """Two-panel demo that exercises *all six* palette colors.

    Left panel: six staggered sine curves (one per color) so the
    full prop_cycle is visible as a series of legend-ready lines.
    Right panel: six categorical bars (one per color) for a flat
    side-by-side comparison of saturation and value. Same six
    colors drive both panels via the active prop_cycle, so every
    palette renders the same chart structure.
    """
    import numpy as np

    ax_line, ax_bar = axes

    # Left — six sine series, deterministic data
    x = np.linspace(0, 8, 80)
    rng = np.random.default_rng(13)
    for k in range(6):
        y = np.sin(x + k * 0.55) + 0.04 * rng.normal(size=x.size)
        ax_line.plot(x, y + k * 0.5, label=f"s{k + 1}")
    ax_line.set_title("6 series")
    ax_line.set_xlabel("Time")
    ax_line.set_ylabel("Value")
    ax_line.set_xlim(0, 8)
    ax_line.set_ylim(-1.5, 4.5)
    ax_line.set_xticks([0, 2, 4, 6, 8])
    ax_line.set_yticks([-1, 0, 1, 2, 3, 4])
    ax_line.legend(loc="upper left", ncol=2, fontsize=dm.fs(-2))

    # Right — six categorical bars, each picking the next prop_cycle color
    labels = ["A", "B", "C", "D", "E", "F"]
    values = [42, 67, 55, 78, 49, 62]
    # bar() doesn't auto-cycle colors per bar, so iterate explicitly
    # against the active cycle.
    cycle = matplotlib.rcParams["axes.prop_cycle"].by_key()["color"]
    for i, (lab, v) in enumerate(zip(labels, values, strict=True)):
        ax_bar.bar(lab, v, color=cycle[i % len(cycle)])
    ax_bar.set_title("6 categories")
    ax_bar.set_xlabel("Group")
    ax_bar.set_ylabel("Count")
    ax_bar.set_ylim(0, 90)
    ax_bar.set_yticks([0, 30, 60, 90])


def _clean_output_dir() -> None:
    for path in OUT.glob("demo_bar_*.*"):
        if path.suffix in {".png", ".svg"}:
            path.unlink()


def _save_palette_demo(fig: plt.Figure, name: str) -> None:
    out_svg = OUT / f"{name}.svg"
    with matplotlib.rc_context({"svg.hashsalt": name}):
        fig.savefig(out_svg, format="svg", metadata={"Date": None})

    out_png = OUT / f"{name}.png"
    fig.savefig(out_png, format="png", dpi=140, metadata={"Software": None})
    plt.close(fig)


def render_one(palette: dict) -> None:
    dm.style.use("report")
    _apply_palette(palette["colors"])
    fig, axes = plt.subplots(
        1,
        2,
        figsize=dm.figsize(LANDING_W_DM, 0.55),
        gridspec_kw={"wspace": 0.35},
    )
    _draw_palette_demo(axes)
    dm.simple_layout(fig, margin="2mm")
    _save_palette_demo(fig, f"demo_bar_{palette['id'].replace('.', '_')}")


def main():
    _clean_output_dir()
    manifest_entries = []
    for p in PALETTES:
        try:
            render_one(p)
            swatch = [_resolve_hex(c) for c in p["colors"]]
            manifest_entries.append(
                {
                    "id": p["id"],
                    "label": p["label"],
                    "namespace": p["namespace"],
                    "swatch": swatch,
                    "file": f"demo_bar_{p['id'].replace('.', '_')}.svg",
                }
            )
            print(f"  ✓ {p['id']}")
        except Exception as e:  # noqa: BLE001, PERF203  (PoC tool, log + continue)
            print(f"  ✗ {p['id']}: {e}")

    # Group manifest entries by namespace for the picker UI.
    by_ns: dict[str, list] = {}
    for e in manifest_entries:
        by_ns.setdefault(e["namespace"], []).append(e)

    manifest = {
        "groups": [
            {"namespace": ns, "entries": entries}
            for ns, entries in by_ns.items()
        ],
        "demo": "demo_bar",
        "demo_caption": "Same grouped-bar chart, same data — only the prop_cycle changes.",
    }
    manifest_path = OUT / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"\nWrote {manifest_path}")
    print(f"Total palettes: {len(manifest_entries)}")


if __name__ == "__main__":
    main()
