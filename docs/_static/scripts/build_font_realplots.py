#!/usr/bin/env python3
"""Render real matplotlib chart SVGs for the font explorer."""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[2]
OUT = SCRIPT_DIR.parent / "realplots"
_CACHE_ROOT = ROOT / "docs" / "_build" / "font_realplots_cache"
_CACHE_ROOT.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("MPLCONFIGDIR", str(_CACHE_ROOT / "mplconfig"))
os.environ.setdefault("XDG_CACHE_HOME", str(_CACHE_ROOT / "xdg"))
os.environ.setdefault("SOURCE_DATE_EPOCH", "1735689600")

import matplotlib  # noqa: E402

matplotlib.use("Agg")
matplotlib.rcParams["svg.hashsalt"] = "dartwork-mpl-font-realplots"
matplotlib.rcParamsDefault["svg.hashsalt"] = "dartwork-mpl-font-realplots"

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

import dartwork_mpl as dm  # noqa: E402
from dartwork_mpl import font  # noqa: E402

QUARTERS = ("Q1", "Q2", "Q3", "Q4", "Q1", "Q2")
ENTERPRISE = (1234, 2368, 3152, 4026, 4890, 5678)
CONSUMER = (1048, 1880, 2550, 3188, 3820, 4515)
Y_TICKS = (1234, 2034, 2834, 3634, 4434, 5234, 6034)
EN_TITLE = "Quarterly revenue by segment"
KR_TITLE = "분기별 부문 매출"
MANIFEST = "_manifest.json"


def slug_for_family(name: str) -> str:
    """Return the shared explorer/realplot slug for a family name."""
    import re

    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _thousands(value: float, _pos: int) -> str:
    return f"{int(value):,}"


def _script_hash() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _resolved_path(path: str) -> Path | None:
    try:
        return Path(path).resolve()
    except (OSError, ValueError):
        return None


def _family_font_entries(family: str) -> list[font_manager.FontEntry]:
    font.ensure_loaded()
    bundle_dir = font.get_font_dir().resolve()
    entries: list[font_manager.FontEntry] = []
    for entry in font_manager.fontManager.ttflist:
        if entry.name != family:
            continue
        path = _resolved_path(entry.fname)
        if path is None:
            continue
        if path.is_relative_to(bundle_dir):
            entries.append(entry)
    if not entries:
        raise KeyError(f"bundled font family not found: {family}")
    return sorted(entries, key=lambda entry: str(entry.fname))


def _cache_key(family: str) -> dict[str, Any]:
    font_files = []
    for entry in _family_font_entries(family):
        path = Path(entry.fname)
        stat = path.stat()
        font_files.append(
            {
                "name": path.name,
                "mtime_ns": stat.st_mtime_ns,
                "size": stat.st_size,
            }
        )
    return {
        "family": family,
        "script": _script_hash(),
        "fonts": font_files,
        "source_date_epoch": os.environ.get("SOURCE_DATE_EPOCH", ""),
    }


def _load_manifest(out_dir: Path) -> dict[str, Any]:
    path = out_dir / MANIFEST
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_manifest(out_dir: Path, manifest: dict[str, Any]) -> None:
    (out_dir / MANIFEST).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _title_for_family(family: str) -> str:
    return KR_TITLE if font.FONTS[family].hangul else EN_TITLE


def render_chart(path: Path, family: str) -> None:
    """Render one deterministic chart for ``family`` to ``path``."""
    dm.style.use("scientific")
    family_chain = list(plt.rcParams["font.family"])
    plt.rcParams["font.family"] = [
        family,
        *[item for item in family_chain if item != family],
    ]
    plt.rcParams["svg.hashsalt"] = "dartwork-mpl-font-realplots"

    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    try:
        x = range(len(QUARTERS))
        ax.plot(
            x,
            ENTERPRISE,
            marker="o",
            markersize=4.2,
            linewidth=dm.lw(1),
            color="#1d6fd1",
            label="Enterprise",
        )
        ax.scatter(
            x,
            CONSUMER,
            s=34,
            linewidth=0.5,
            edgecolor="#ffffff",
            color="#d1495b",
            label="Consumer",
            zorder=3,
        )
        ax.set_title(
            _title_for_family(family),
            fontsize=dm.fs(2),
            fontweight=dm.fw(1),
            pad=10,
        )
        ax.set_ylabel("Revenue (bn KRW)", fontsize=dm.fs(0))
        ax.set_xticks(list(x))
        ax.set_xticklabels(QUARTERS)
        ax.set_ylim(900, 6300)
        ax.set_yticks(Y_TICKS)
        ax.yaxis.set_major_formatter(FuncFormatter(_thousands))
        ax.grid(axis="y", linewidth=0.5, alpha=0.45)
        ax.legend(loc="upper left", frameon=True, fontsize=dm.fs(-1), ncols=2)
        ax.annotate(
            r"$R^2 = 0.94$",
            xy=(5, ENTERPRISE[-1]),
            xytext=(3.85, 5900),
            arrowprops={
                "arrowstyle": "->",
                "linewidth": 0.5,
                "color": "#555555",
            },
            fontsize=dm.fs(0),
            color="#333333",
        )
        ax.margins(x=0.05)
        dm.simple_layout(fig)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, format="svg")
    finally:
        plt.close(fig)


def build_realplots(
    out_dir: str | Path = OUT,
    *,
    family_names: tuple[str, ...] | list[str] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Render fresh realplot SVGs and skip unchanged cached outputs."""
    started = time.perf_counter()
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    manifest = _load_manifest(out_path)
    families = (
        tuple(family_names)
        if family_names is not None
        else tuple(font.list_registered())
    )
    rendered: list[str] = []
    skipped: list[str] = []

    for family in families:
        slug = slug_for_family(family)
        svg = out_path / f"{slug}.svg"
        key = _cache_key(family)
        fresh = (
            not force
            and svg.is_file()
            and svg.stat().st_size > 5_000
            and manifest.get(slug) == key
        )
        if fresh:
            skipped.append(slug)
            continue
        render_chart(svg, family)
        manifest[slug] = key
        rendered.append(slug)

    _write_manifest(out_path, manifest)
    elapsed = time.perf_counter() - started
    return {
        "rendered": rendered,
        "skipped": skipped,
        "families": len(families),
        "seconds": elapsed,
        "out_dir": str(out_path),
    }


def main() -> None:
    result = build_realplots()
    print(
        "font realplots: "
        f"{len(result['rendered'])} rendered, "
        f"{len(result['skipped'])} cached, "
        f"{result['seconds']:.2f}s"
    )


if __name__ == "__main__":
    main()
