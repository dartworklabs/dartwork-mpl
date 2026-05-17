"""Palette demo renders for the interactive picker on the colors page.

Renders **one demo PoC** in every cataloged palette so the
`usage_guide/colors.md` page can swap between them with a single click.
We pick L2 (grouped bar with value labels) as the demo because:

- it shows *two* series side by side → palette's first two colors are
  directly comparable;
- the values labels stay legible regardless of palette;
- bars don't have a dominant accent color the way scatter+line does,
  so the palette difference is the whole story.

Palette catalog is grouped by namespace so the picker UI can show
section headers (dc, oc, tw, md, ad, cu, pr).

Each render reuses the `_draw_l2` helper from build_landing_pocs.py
to guarantee byte-identical chart content across palettes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

import dartwork_mpl as dm

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

# Reuse the canonical helpers/data from the main PoC builder.
from build_landing_pocs import (  # noqa: E402  (sys.path injection)
    LANDING_W_DM,
    _draw_l2,
    save,
)

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
    # ---- dc.* moods (8) ----
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
        "id": "dc.ocean",
        "label": "dc.ocean",
        "namespace": "dc",
        "colors": [
            "dc.ocean3",
            "dc.ocean1",
            "dc.ocean5",
            "dc.ocean0",
            "dc.ocean2",
            "dc.ocean4",
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
        "id": "dc.sunset",
        "label": "dc.sunset",
        "namespace": "dc",
        "colors": [
            "dc.sunset2",
            "dc.sunset4",
            "dc.sunset0",
            "dc.sunset5",
            "dc.sunset1",
            "dc.sunset3",
        ],
    },
    {
        "id": "dc.autumn",
        "label": "dc.autumn",
        "namespace": "dc",
        "colors": [
            "dc.autumn3",
            "dc.autumn1",
            "dc.autumn5",
            "dc.autumn0",
            "dc.autumn2",
            "dc.autumn4",
        ],
    },
    {
        "id": "dc.cyber",
        "label": "dc.cyber",
        "namespace": "dc",
        "colors": [
            "dc.cyber3",
            "dc.cyber1",
            "dc.cyber5",
            "dc.cyber0",
            "dc.cyber2",
            "dc.cyber4",
        ],
    },
    {
        "id": "dc.pop",
        "label": "dc.pop",
        "namespace": "dc",
        "colors": [
            "dc.pop3",
            "dc.pop1",
            "dc.pop5",
            "dc.pop0",
            "dc.pop2",
            "dc.pop4",
        ],
    },
    {
        "id": "dc.nordic",
        "label": "dc.nordic",
        "namespace": "dc",
        "colors": [
            "dc.nordic3",
            "dc.nordic1",
            "dc.nordic5",
            "dc.nordic0",
            "dc.nordic2",
            "dc.nordic4",
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


def render_one(palette: dict) -> None:
    dm.style.use("report")
    _apply_palette(palette["colors"])
    fig, ax = plt.subplots(figsize=dm.figsize(LANDING_W_DM, 0.55))
    _draw_l2(ax)
    dm.simple_layout(fig, margin="2mm")
    save(fig, f"demo_bar_{palette['id'].replace('.', '_')}")


def main():
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

    # Move rendered files from the build_landing_pocs OUT (landing_pocs/)
    # over to palette_demo/. Easier: re-point save() output — but we
    # reuse build_landing_pocs.save() which writes to landing_pocs/. So
    # move them after the fact.
    src_dir = ROOT / "docs" / "_static" / "landing_pocs"
    for entry in manifest_entries:
        for ext in ("svg", "png"):
            stem = entry["file"].replace(".svg", "")
            src = src_dir / f"{stem}.{ext}"
            if src.exists():
                src.rename(OUT / f"{stem}.{ext}")

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
