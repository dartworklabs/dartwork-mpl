"""dartwork color system — design-theory figures for the docs site.

Ten self-contained vector figures that explain the generation design rules
visually. Every data point is computed live from the shipped package: OKLab /
OKLCH construction, the optional modeled-relative-Y compatibility lock, and
the independent validation metrics. The figures are evidence of the theory
rather than decoration.

Run::

    PYTHONPATH=src python docs/color_system/generate_theory_figures.py

Output: ``docs/color_system/theory_figures/theory_*.svg`` (tracked static
assets referenced by ``docs/color_system/design-rationale.md``). Relative
``--output-dir`` values are resolved against this generator's directory;
``--check`` renders into a temporary directory and never writes tracked files.
"""

from __future__ import annotations

import argparse
import base64
import io
import math
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from tempfile import TemporaryDirectory

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap

import dartwork_mpl as dm
from dartwork_mpl._colors import _conversion as CONV
from dartwork_mpl._colors import _curated as CUR
from dartwork_mpl._colors import _gates as GA
from dartwork_mpl._colors import _generate as GEN
from dartwork_mpl._colors import _generated as G
from dartwork_mpl._colors import _metrics as M
from dartwork_mpl._colors import _recipe as R
from dartwork_mpl._colors import _tone as TONE

HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = HERE / "theory_figures"
FIGURE_NAMES: tuple[str, ...] = (
    "theory_1_lightness_weber",
    "theory_2_floor",
    "theory_3_drift",
    "theory_4_chroma",
    "theory_5_spacing",
    "theory_6_metric",
    "theory_7_dcseq",
    "theory_8_anatomy",
    "theory_9_cmap_catalog",
    "theory_10_cyclic_demo",
)

# Pretendard (report-kr preset) gives full Latin + Greek + subscript coverage
# for the mathtext labels; the labels themselves are English. This generator
# runs only when the SSOT changes — the committed SVGs are the docs assets.
dm.style.use("report-kr")
# report-kr renders bold titles in Paperlogy, which lacks Greek / super- and
# subscripts; Pretendard covers the full Latin + Greek + sub/superscript set
# the design-rule labels need. Lead the fallback chain with Pretendard so titles
# resolve Δ / γ / ² / ₀ without dropping the math/symbol/CJK fallbacks.
family_chain = plt.rcParams["font.family"]
plt.rcParams["font.family"] = [
    "Pretendard",
    *[family for family in family_chain if family != "Pretendard"],
]
# The cmap catalog labels its gradients with `family="monospace"`, which
# resolves to font.monospace[0]. Left unpinned that is whatever monospace the
# build machine happens to win (macOS Andale Mono vs. CI DejaVu Sans Mono),
# baking machine-dependent glyph paths into theory_9_cmap_catalog.svg. Pin it
# to DejaVu Sans Mono — it ships inside matplotlib, so every machine renders
# the identical bytes.
plt.rcParams["font.monospace"] = ["DejaVu Sans Mono"]
plt.rcParams["svg.fonttype"] = "path"

PALETTE = G.PALETTE  # fam -> [10 hex]
CMAPS = G.CMAPS_256  # name -> [256 hex]
CYCLES = G.CYCLES  # 'default' -> [8 hex], 'print' -> [8 hex]
PARAMS = R.FAMILY_PARAMS  # fam -> FamilyParams (19 chromatic)
FOURIER = R.FOURIER

# ── metric helpers over hex (thin wrappers on the shipped kernel) ──────────


def rgb(h: str) -> tuple[float, float, float]:
    """Parse one shipped hex color through the canonical conversion kernel."""
    return CONV._parse_hex(h)


def oklab_l(h: str) -> float:
    """Return actual OKLab L in its native unit interval."""
    return CONV._srgb_to_oklab(rgb(h))[0]


def relative_y(h: str) -> float:
    """Return modeled relative CIE Y from nominal D65 sRGB for one color."""
    return CONV.relative_y_srgb_d65(rgb(h))


def neutral_tone(h: str) -> float:
    """Return the reversible catalog output coordinate, cube-root modeled Y."""
    return float(TONE.tone_from_relative_y(relative_y(h)))


def de_ok(a: str, b: str) -> float:
    return (
        math.dist(CONV._srgb_to_oklab(rgb(a)), CONV._srgb_to_oklab(rgb(b)))
        * 100
    )


def de2000(a: str, b: str) -> float:
    return M.de2000_hex(a, b)


def de76(a: str, b: str) -> float:
    la = M.lab_from_rgb(M.rgb_from_hex(a))
    lb = M.lab_from_rgb(M.rgb_from_hex(b))
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(la, lb, strict=True)))


def cvd(h: str, kind: str) -> str:
    return M.hex_from_rgb(M.cvd_rgb(M.rgb_from_hex(h), kind))


def oklch(h: str) -> tuple[float, float, float]:
    return CONV._oklab_to_oklch_degrees(*CONV._srgb_to_oklab(rgb(h)))


def neutral_hex_from_y(value: float) -> str:
    """Encode a neutral whose nominal-sRGB modeled Y equals ``value``."""
    channel = float(CONV._linear_to_srgb(value))
    return CONV._rgb_to_hex(channel, channel, channel)


def coefficient_of_determination(
    observed: Sequence[float], fitted: Sequence[float]
) -> float:
    """Return ordinary in-sample R² for paired observations and fits."""
    if len(observed) != len(fitted) or not observed:
        raise ValueError(
            "observed and fitted must be equally sized and non-empty"
        )
    mean = sum(observed) / len(observed)
    total = sum((value - mean) ** 2 for value in observed)
    if total == 0:
        raise ValueError("R² is undefined when observed values are constant")
    residual = sum(
        (actual - predicted) ** 2
        for actual, predicted in zip(observed, fitted, strict=True)
    )
    return 1.0 - residual / total


# ── style tokens ──────────────────────────────────────────────────────────


def _C(t: str) -> str:
    return dm.color(t).to_hex()


INK = _C("oc.gray8")
MUT = _C("oc.gray6")
ACC = PALETTE["blue"][6]

# Greek / subscripts as Unicode (Pretendard covers Δ γ ² ₀ ₚ) — no mathtext,
# so no separate math-font resolution.
GAM, DH, H0, C0, CE, TP, CMAX = "γ", "Δh", "h₀", "c₀", "c_end", "t_p", "C_max"


def title(fig, text, top=0.84, y=0.965, fs=2.3, **adj):
    fig.subplots_adjust(top=top, **adj)
    fig.suptitle(
        text, fontsize=dm.fs(fs), fontweight="bold", x=0.012, ha="left", y=y
    )


def save(fig, name: str, output_dir: Path) -> None:
    """Apply project layout and save one deterministic tracked SVG."""
    # Run the project layout pass after plotting, then retain the intentional
    # editorial grid set by each figure's title helper. Several panels place
    # explanatory text outside their axes; preserving those explicit GridSpec
    # gaps prevents the generic fitter from collapsing a panel to satisfy one
    # long annotation. ``bbox_inches='tight'`` still includes every artist.
    subplotpars = fig.subplotpars
    editorial_layout = {
        "left": subplotpars.left,
        "right": subplotpars.right,
        "bottom": subplotpars.bottom,
        "top": subplotpars.top,
        "wspace": subplotpars.wspace,
        "hspace": subplotpars.hspace,
    }
    grid_spec = fig.axes[0].get_gridspec()
    dm.simple_layout(fig)
    fig.subplots_adjust(**editorial_layout)
    grid_spec.update(**editorial_layout)
    dm.save_formats(
        fig,
        str(output_dir / name),
        formats=("svg",),
        bbox_inches="tight",
        pad_inches=0.08,
        transparent=True,
        validate=False,
    )
    # Matplotlib indents multiline path data with a space before each newline.
    # Strip that serialization-only whitespace so generated assets also pass
    # the repository-wide ``git diff --check`` contract.
    svg_path = output_dir / f"{name}.svg"
    raw = svg_path.read_bytes()
    cleaned = b"\n".join(line.rstrip(b" \t") for line in raw.split(b"\n"))
    if cleaned != raw:
        svg_path.write_bytes(cleaned)
    plt.close(fig)
    print(f"  {name}.svg")


# ══════════════════════════════════════════════ 1 · neutral tone and modeled Y
def fig_lightness_weber(output_dir: Path) -> None:
    fig, axs = plt.subplots(2, 1, figsize=dm.figsize("15cm", 0.42))
    n = 12
    tones = np.linspace(0.18, 0.98, n)
    tone_row = [neutral_hex_from_y(float(tone**3)) for tone in tones]
    y_values = np.linspace(float(tones[0] ** 3), float(tones[-1] ** 3), n)
    y_row = [neutral_hex_from_y(float(value)) for value in y_values]
    rows = [
        (
            axs[0],
            tone_row,
            "Even neutral tone steps (T)",
            "T is the reversible neutral output coordinate: "
            "T = ∛(modeled relative CIE Y from nominal D65 sRGB)",
        ),
        (
            axs[1],
            y_row,
            "Even modeled relative Y steps",
            "Y is a nominal-sRGB model coordinate; it is not the OKLab "
            "authoring lightness axis or a display measurement",
        ),
    ]
    for ax, row, htitle, sub in rows:
        for i, h in enumerate(row):
            ax.add_patch(
                plt.Rectangle((i, 0), 1, 1, color=h, ec="white", lw=0.8)
            )
        ax.set_xlim(0, n)
        ax.set_ylim(0, 1)
        ax.set_title(htitle, fontsize=dm.fs(1), loc="left", pad=3)
        ax.text(
            0,
            -0.30,
            sub,
            fontsize=dm.fs(-1.5),
            color=MUT,
            transform=ax.get_yaxis_transform(),
            va="top",
        )
        ax.axis("off")
    title(
        fig,
        "Neutral tone and modeled relative Y — one reversible catalog contract",
        top=0.80,
        y=0.95,
        hspace=1.15,
    )
    save(fig, "theory_1_lightness_weber", output_dir)


# ══════════════════════════════════════════════ 2 · hue-specific output floor
def fig_floor(output_dir: Path) -> None:
    fams = [
        "yellow",
        "orange",
        "lime",
        "green",
        "teal",
        "cyan",
        "blue",
        "violet",
        "pink",
        "red",
    ]
    fig, ax = plt.subplots(figsize=dm.figsize("15cm", 0.62))
    for xi, fam in enumerate(fams):
        row = PALETTE[fam]
        for h in row:
            tone = neutral_tone(h)
            ax.add_patch(
                plt.Rectangle(
                    (xi - 0.4, tone - 0.012),
                    0.8,
                    0.024,
                    color=h,
                    ec="white",
                    lw=0.5,
                )
            )
        floor = neutral_tone(row[9])
        ax.plot([xi - 0.46, xi + 0.46], [floor, floor], color=INK, lw=1.0)
        ax.text(
            xi,
            floor - 0.025,
            f"T {floor:.3f}\nY {relative_y(row[9]):.3f}",
            ha="center",
            va="top",
            fontsize=dm.fs(-2),
            color=INK,
            fontweight="bold",
        )
    ax.set_xticks(range(len(fams)))
    ax.set_xticklabels(fams, fontsize=dm.fs(-1.5), rotation=32, ha="right")
    ax.set_ylabel("NeutralTone T = ∛Y", fontsize=dm.fs(0))
    ax.set_ylim(0.40, 1.0)
    ax.set_xlim(-0.8, len(fams) - 0.2)
    modeled_axis = ax.secondary_yaxis(
        "right", functions=(lambda value: np.asarray(value) ** 3, np.cbrt)
    )
    modeled_axis.set_ylabel("modeled relative Y", fontsize=dm.fs(0))
    top = float(R.TONE_TOP)
    ax.text(
        len(fams) - 0.3,
        top,
        f"shared output start T={top:.3f}\n"
        f"(modeled Y={float(TONE.relative_y_from_tone(R.TONE_TOP)):.3f})",
        ha="right",
        va="top",
        fontsize=dm.fs(-2),
        color=MUT,
    )
    ax.annotate(
        "Yellow stops earlier\n(darker turns olive)",
        xy=(0, float(PARAMS["yellow"].tone_floor)),
        xytext=(1.7, 0.78),
        fontsize=dm.fs(-2),
        color=INK,
        arrowprops={"arrowstyle": "->", "color": MUT, "lw": 0.9},
    )
    ax.set_title(
        "Optional output lock — authored hue-specific dark endpoint",
        fontsize=dm.fs(2.5),
        fontweight="bold",
        loc="left",
        pad=8,
    )
    save(fig, "theory_2_floor", output_dir)


# ══════════════════════════════════════════════ 3 · drift power law
def fig_drift(output_dir: Path) -> None:
    fig, axs = plt.subplots(
        1,
        2,
        figsize=dm.figsize("15cm", 0.44),
        gridspec_kw={"width_ratios": [1.15, 1]},
    )
    ax = axs[0]
    show = [
        ("yellow", "oc.yellow7"),
        ("orange", "oc.orange7"),
        ("blue", "oc.blue7"),
        ("cyan", "oc.cyan7"),
    ]
    ts = np.linspace(0, 1, 50)
    for fam, tok in show:
        p = PARAMS[fam]
        hs = [(p.h0 + p.dh * t**p.gamma) for t in ts]
        ax.plot(
            ts,
            hs,
            color=_C(tok),
            lw=dm.lw(0.5),
            label=f"{fam} ({DH} {p.dh:+.0f}°, {GAM} {p.gamma:.2f})",
        )
    ax.set_xlabel(
        "Ladder position t (0 = light → 1 = dark)", fontsize=dm.fs(-0.5)
    )
    ax.set_ylabel("OKLCH hue angle h (°)", fontsize=dm.fs(-0.5))
    ax.legend(fontsize=dm.fs(-2.5), loc="center left", frameon=False)
    ax.set_title("Hue rotation curves", fontsize=dm.fs(0.5), loc="left")

    ax2 = axs[1]
    for xi, (fam, _t) in enumerate(show):
        for k, h in enumerate(PALETTE[fam]):
            ax2.add_patch(
                plt.Rectangle(
                    (xi, 9 - k), 0.92, 0.95, color=h, ec="white", lw=0.5
                )
            )
    ax2.set_xlim(0, len(show))
    ax2.set_ylim(0, 10)
    ax2.set_xticks([i + 0.46 for i in range(len(show))])
    ax2.set_xticklabels([f for f, _ in show], fontsize=dm.fs(-2))
    ax2.set_yticks([])
    ax2.set_title("The result, in color", fontsize=dm.fs(0.5), loc="left")
    for s in ax2.spines.values():
        s.set_visible(False)
    title(
        fig,
        "Design rule A4 — authored catalog drift along each hue path",
        top=0.82,
        y=0.955,
        wspace=0.28,
    )
    save(fig, "theory_3_drift", output_dir)


# ══════════════════════════════════════════════ 4 · chroma fingerprint
def fig_chroma(output_dir: Path) -> None:
    fig, axs = plt.subplots(1, 2, figsize=dm.figsize("15cm", 0.46))
    ax = axs[0]
    coefficients = FOURIER["cmax_k3"]
    hh = np.linspace(0, 360, 361)
    cc = [R.fourier_eval(coefficients, h) for h in hh]
    family_points = [
        (family, params, R.mid_hue(params)) for family, params in PARAMS.items()
    ]
    observed = [params.cmax for _, params, _ in family_points]
    fitted = [R.fourier_eval(coefficients, hue) for _, _, hue in family_points]
    r_squared = coefficient_of_determination(observed, fitted)
    ax.plot(hh, cc, color=INK, lw=dm.lw(0.3), zorder=2)
    for fam, p, hm in family_points:
        ax.scatter(
            [hm],
            [p.cmax],
            s=22,
            color=PALETTE[fam][6],
            ec="white",
            lw=0.6,
            zorder=3,
        )
    ax.annotate(
        "authored cyan minimum",
        xy=(202, 0.113),
        xytext=(150, 0.15),
        fontsize=dm.fs(-2.5),
        color=MUT,
        arrowprops={"arrowstyle": "->", "color": MUT, "lw": 0.8},
    )
    ax.annotate(
        "violet peak",
        xy=(298, 0.228),
        xytext=(300, 0.17),
        fontsize=dm.fs(-2.5),
        color=MUT,
        arrowprops={"arrowstyle": "->", "color": MUT, "lw": 0.8},
    )
    ax.set_xlabel("OKLCH hue angle h (°)", fontsize=dm.fs(-0.5))
    ax.set_ylabel(f"peak chroma {CMAX}", fontsize=dm.fs(-0.5))
    ax.set_xlim(0, 360)
    ax.set_xticks([0, 90, 180, 270, 360])
    ax.set_title(
        f"Chroma fingerprint {CMAX}(h)  (In-sample R²={r_squared:.3f})",
        fontsize=dm.fs(-0.5),
        loc="left",
    )

    ax2 = axs[1]
    ts = np.linspace(0, 1, 100)
    for fam, tok in [
        ("red", "oc.red6"),
        ("yellow", "oc.yellow7"),
        ("teal", "oc.teal6"),
    ]:
        p = PARAMS[fam]
        ys = [GEN.shape(t, p.tp, p.c0, p.cend) for t in ts]
        ax2.plot(
            ts,
            ys,
            color=_C(tok),
            lw=dm.lw(0.5),
            label=f"{fam} ({TP} {p.tp:.2f})",
        )
        ax2.scatter([p.tp], [1.0], s=16, color=_C(tok), zorder=3)
    ax2.set_xlabel("Ladder position t", fontsize=dm.fs(-0.5))
    ax2.set_ylabel(f"chroma ratio C / {CMAX}", fontsize=dm.fs(-0.5))
    ax2.legend(fontsize=dm.fs(-2.5), loc="lower center", frameon=False)
    ax2.set_title(
        "Shared functional form; family parameters vary",
        fontsize=dm.fs(-0.5),
        loc="left",
    )
    title(
        fig,
        "Design rule A3 — chroma: hue fingerprint × shared shape",
        top=0.82,
        y=0.955,
        wspace=0.34,
    )
    save(fig, "theory_4_chroma", output_dir)


# ══════════════════════════════════════════════ 5 · step spacing
def fig_spacing(output_dir: Path) -> None:
    fig, axs = plt.subplots(
        2,
        1,
        figsize=dm.figsize("15cm", 0.5),
        gridspec_kw={"height_ratios": [1, 1.1]},
    )
    p = PARAMS["blue"]
    equalized = PALETTE["blue"]
    naive = [M.hex_from_rgb(GEN.swatch(p, i / 9)) for i in range(10)]
    ax = axs[0]
    for yi, (row, lbl) in enumerate(
        [(equalized, "equalized (default)"), (naive, "naive linear-t")]
    ):
        for k, h in enumerate(row):
            ax.add_patch(
                plt.Rectangle(
                    (k, 1 - yi), 0.95, 0.9, color=h, ec="white", lw=0.5
                )
            )
        ax.text(
            -0.3,
            1 - yi + 0.45,
            lbl,
            ha="right",
            va="center",
            fontsize=dm.fs(-1.5),
            color=INK,
        )
    ax.set_xlim(-4, 10)
    ax.set_ylim(0, 2)
    ax.axis("off")
    ax.set_title(
        "Same dc.blue recipe, two step-placement policies",
        fontsize=dm.fs(0.5),
        loc="left",
    )

    ax2 = axs[1]
    for row, lbl, tok in [
        (equalized, "equalized (default)", "oc.blue6"),
        (naive, "naive linear-t", "oc.gray6"),
    ]:
        des = [de_ok(row[i], row[i + 1]) for i in range(9)]
        ax2.plot(
            range(1, 10),
            des,
            marker="o",
            ms=2.8,
            lw=dm.lw(0.3),
            color=_C(tok),
            label=lbl,
        )
    ax2.set_xlabel("step transition (k → k+1)", fontsize=dm.fs(-0.5))
    ax2.set_ylabel("neighbor ΔEOK", fontsize=dm.fs(-0.5))
    ax2.legend(fontsize=dm.fs(-2), frameon=False, loc="upper center", ncol=2)
    ax2.set_title(
        "Only equalization flattens neighbor ΔEOK — step "
        "arithmetic becomes meaningful",
        fontsize=dm.fs(0),
        loc="left",
    )
    title(
        fig,
        "A5 — step spacing: fixed ΔEOK arc-length equalization",
        top=0.82,
        y=0.955,
        hspace=0.65,
    )
    save(fig, "theory_5_spacing", output_dir)


# ══════════════════════════════════════════════ 6 · metric reform
def fig_metric(output_dir: Path) -> None:
    a, b = PALETTE["blue"][7], PALETTE["violet"][7]
    fig, axs = plt.subplots(
        1,
        2,
        figsize=dm.figsize("15cm", 0.44),
        gridspec_kw={"width_ratios": [1, 1.15]},
    )
    ax = axs[0]
    pairs = [
        ("unsimulated nominal sRGB", a, b),
        (
            "named deutan simulation\n(full severity)",
            cvd(a, "deutan"),
            cvd(b, "deutan"),
        ),
    ]
    for yi, (lbl, ca, cb) in enumerate(pairs):
        y = 1 - yi
        ax.add_patch(
            plt.Rectangle((0, y), 1.3, 0.8, color=ca, ec="white", lw=1)
        )
        ax.add_patch(
            plt.Rectangle((1.35, y), 1.3, 0.8, color=cb, ec="white", lw=1)
        )
        ax.text(
            -0.15,
            y + 0.4,
            lbl,
            ha="right",
            va="center",
            fontsize=dm.fs(-1.5),
            color=INK,
        )
    ax.text(0.65, 1.88, "blue7", ha="center", fontsize=dm.fs(-2.5), color=MUT)
    ax.text(2.0, 1.88, "violet7", ha="center", fontsize=dm.fs(-2.5), color=MUT)
    ax.set_xlim(-1.6, 2.75)
    ax.set_ylim(-0.15, 2.1)
    ax.axis("off")
    ax.set_title(
        "Nominal rendering and one named simulation",
        fontsize=dm.fs(0),
        loc="left",
    )

    ax2 = axs[1]
    d76 = de76(cvd(a, "deutan"), cvd(b, "deutan"))
    d00 = de2000(cvd(a, "deutan"), cvd(b, "deutan"))
    bars = [
        (
            "ΔE76",
            d76,
            _C("oc.red6"),
            "above historical\nsearch criterion",
            "white",
            8.5,
        ),
        (
            "ΔE00",
            d00,
            _C("oc.teal7"),
            "below historical\nsearch criterion",
            INK,
            6.2,
        ),
    ]
    for xi, (_lbl, val, col, note, ncol, ny) in enumerate(bars):
        ax2.bar(xi, val, 0.52, color=col)
        ax2.text(
            xi,
            val + 0.5,
            f"{val:.1f}",
            ha="center",
            fontsize=dm.fs(0.5),
            fontweight="bold",
        )
        ax2.text(
            xi,
            ny,
            note,
            ha="center",
            fontsize=dm.fs(-2),
            color=ncol,
            va="center",
        )
    ax2.axhline(10, color=INK, lw=dm.lw(-0.3), ls="--")
    ax2.text(
        1.48,
        10.5,
        "historical Octave search criterion 10\n(not a current shared gate)",
        fontsize=dm.fs(-2.5),
        color=INK,
        ha="right",
    )
    ax2.set_xticks([0, 1])
    ax2.set_xticklabels(["ΔE76", "ΔE00"], fontsize=dm.fs(0))
    ax2.set_ylabel(
        "color distance after named deutan simulation", fontsize=dm.fs(-0.5)
    )
    ax2.set_ylim(0, 20)
    ax2.set_xlim(-0.6, 1.6)
    ax2.set_title(
        "…judged oppositely by two metrics", fontsize=dm.fs(0), loc="left"
    )
    title(
        fig,
        "Model-specific CIEDE2000 regression diagnostic — "
        "named deutan simulation",
        top=0.80,
        y=0.95,
        wspace=0.3,
        fs=2.2,
    )
    save(fig, "theory_6_metric", output_dir)


# ══════════════════════════════════════ 7 · sequential OKLab L and modeled Y
def fig_dcseq(output_dir: Path) -> None:
    import matplotlib as mpl

    seq = [CMAPS["aurora"][round(i * 255 / 31)] for i in range(32)]
    vir = [
        mpl.colors.to_hex(mpl.colormaps["viridis"](i / 31)) for i in range(32)
    ]
    # Measure the two swatch strips the figure actually renders with the same
    # gate used elsewhere. The printed numbers report the values reproduced by
    # this named 32-stop protocol. NOTE: aurora here is the shipped 256-LUT,
    # not the SSOT's direct-render swatches_32; only about half of their samples
    # overlap, so this is a same-protocol comparison with viridis.
    g_seq = GA.gate_seq_cmap(seq)
    g_vir = GA.gate_seq_cmap(vir)
    fig, axs = plt.subplots(
        2,
        1,
        figsize=dm.figsize("15cm", 0.5),
        gridspec_kw={"height_ratios": [1, 1.2]},
    )
    ax = axs[0]
    for k, h in enumerate(seq):
        ax.add_patch(plt.Rectangle((k, 1.1), 0.98, 0.9, color=h, ec="none"))
    for k, h in enumerate(vir):
        ax.add_patch(plt.Rectangle((k, 0), 0.98, 0.9, color=h, ec="none"))
    ax.text(
        -0.5,
        1.55,
        "aurora",
        ha="right",
        va="center",
        fontsize=dm.fs(-1),
        color=INK,
        fontweight="bold",
    )
    ax.text(
        -0.5,
        0.45,
        "viridis",
        ha="right",
        va="center",
        fontsize=dm.fs(-1),
        color=MUT,
    )
    ax.set_xlim(-6, 32)
    ax.set_ylim(0, 2)
    ax.axis("off")
    ax.set_title(
        "aurora (anchor path violet→indigo→sky→teal→lime→yellow) vs viridis",
        fontsize=dm.fs(0.5),
        loc="left",
    )

    ax2 = axs[1]
    ls_dc = [oklab_l(h) for h in seq]
    ls_vir = [oklab_l(h) for h in vir]
    ys_dc = [relative_y(h) for h in seq]
    ys_vir = [relative_y(h) for h in vir]
    xx = np.linspace(0, 1, 32)
    ax2.plot(
        xx,
        ls_dc,
        color=ACC,
        lw=dm.lw(0.5),
        marker="o",
        ms=2.2,
        label="aurora — actual OKLab L",
    )
    ax2.plot(
        xx,
        ys_dc,
        color=ACC,
        lw=dm.lw(0.3),
        ls="--",
        label="aurora — modeled relative Y",
    )
    ax2.plot(
        xx, ls_vir, color=MUT, lw=dm.lw(0.3), label="viridis — actual OKLab L"
    )
    ax2.plot(
        xx,
        ys_vir,
        color=MUT,
        lw=dm.lw(0.3),
        ls="--",
        label="viridis — modeled relative Y",
    )
    ax2.set_xlabel("cmap position", fontsize=dm.fs(-0.5))
    ax2.set_ylabel("actual OKLab L / modeled relative Y", fontsize=dm.fs(-0.5))
    ax2.set_ylim(0, 1)
    ax2.legend(fontsize=dm.fs(-3), frameon=False, loc="upper left", ncol=2)
    ax2.text(
        0.98,
        0.04,
        f"aurora: ΔEOK CV {g_seq['cv']:.3f} · "
        f"L span {max(ls_dc) - min(ls_dc):.3f} · "
        f"Y span {max(ys_dc) - min(ys_dc):.3f}\n"
        f"viridis: ΔEOK CV {g_vir['cv']:.3f} · "
        f"L span {max(ls_vir) - min(ls_vir):.3f} · "
        f"Y span {max(ys_vir) - min(ys_vir):.3f}",
        ha="right",
        va="bottom",
        fontsize=dm.fs(-2.5),
        color=MUT,
    )
    ax2.set_title(
        "Modeled relative Y carries the catalog ordering contract; "
        "actual OKLab L is a result profile",
        fontsize=dm.fs(0),
        loc="left",
    )
    title(
        fig,
        "Sequential maps — ΔEOK spacing plus distinct OKLab-L / "
        "modeled-relative-Y profiles",
        top=0.82,
        y=0.955,
        hspace=0.55,
        fs=2.0,
    )
    save(fig, "theory_7_dcseq", output_dir)


# ══════════════════════════════════════════════ 8 · recipe anatomy
def fig_anatomy(output_dir: Path) -> None:
    fam = "yellow"
    p = PARAMS[fam]
    row = PALETTE[fam]
    fig, axs = plt.subplots(
        1,
        3,
        figsize=dm.figsize("16cm", 0.34),
        gridspec_kw={"width_ratios": [0.7, 1, 1]},
    )
    ax = axs[0]
    for k, h in enumerate(row):
        ax.add_patch(
            plt.Rectangle((0, 9 - k), 1, 0.95, color=h, ec="white", lw=0.6)
        )
        ax.text(
            1.15,
            9 - k + 0.47,
            f"{fam}{k}",
            va="center",
            fontsize=dm.fs(-3),
            color=MUT,
        )
    ax.set_xlim(0, 2.4)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title("yellow ladder", fontsize=dm.fs(-0.5), loc="left")

    ax2 = axs[1]
    ls = [oklab_l(h) for h in row]
    ys = [relative_y(h) for h in row]
    cs = [oklch(h)[1] for h in row]
    ax2.plot(
        range(10),
        ls,
        color=ACC,
        lw=dm.lw(0.3),
        marker="o",
        ms=2.4,
        label="actual OKLab L",
    )
    ax2.plot(
        range(10),
        ys,
        color=MUT,
        lw=dm.lw(0.3),
        ls="--",
        marker=".",
        ms=2.4,
        label="modeled relative Y",
    )
    ax2.set_ylabel("actual OKLab L / modeled relative Y", fontsize=dm.fs(-1))
    ax2.set_ylim(0, 1)
    output_floor_y = float(TONE.relative_y_from_tone(p.tone_floor))
    ax2.axhline(output_floor_y, color=MUT, ls=":", lw=dm.lw(-0.3))
    ax2.text(
        9,
        output_floor_y - 0.025,
        f"output floor T={float(p.tone_floor):.3f}\nY={output_floor_y:.3f}",
        ha="right",
        va="top",
        fontsize=dm.fs(-3),
        color=MUT,
    )
    ax2b = ax2.twinx()
    ax2b.plot(
        range(10), cs, color=_C("oc.pink6"), lw=dm.lw(0.3), marker="s", ms=2.4
    )
    ax2b.set_ylabel("chroma C", fontsize=dm.fs(-1), color=_C("oc.pink6"))
    ax2b.axvline(p.tp * 9, color=_C("oc.pink6"), ls=":", lw=dm.lw(-0.3))
    ax2b.text(
        p.tp * 9 + 0.2,
        min(cs),
        f"{TP} {p.tp:.2f}",
        fontsize=dm.fs(-3),
        color=_C("oc.pink6"),
    )
    ax2.set_xlabel("step k", fontsize=dm.fs(-1))
    ax2.set_title(
        "profiles: L blue · Y gray · C pink", fontsize=dm.fs(-1), loc="left"
    )

    ax3 = axs[2]
    hs = [oklch(h)[2] for h in row]
    ax3.plot(
        range(10), hs, color=_C("oc.orange6"), lw=dm.lw(0.3), marker="^", ms=2.6
    )
    ax3.set_xlabel("step k", fontsize=dm.fs(-1))
    ax3.set_ylabel("hue h (°)", fontsize=dm.fs(-1))
    ax3.text(
        0.35,
        hs[0] + 2.0,
        f"{H0} {p.h0:.0f}°",
        fontsize=dm.fs(-3),
        color=_C("oc.orange6"),
    )
    ax3.annotate(
        "",
        xy=(9, hs[9]),
        xytext=(9, hs[0]),
        arrowprops={"arrowstyle": "<->", "color": MUT, "lw": 0.8},
    )
    ax3.text(
        8.4,
        (hs[0] + hs[9]) / 2,
        f"{DH} {p.dh:+.0f}°\n{GAM} {p.gamma:.2f}",
        ha="right",
        va="center",
        fontsize=dm.fs(-3),
        color=INK,
    )
    ax3.set_title("hue drift", fontsize=dm.fs(-0.5), loc="left")
    title(
        fig,
        f"Recipe anatomy — {fam}: OKLCH construction + optional "
        "modeled-relative-Y lock",
        top=0.76,
        y=0.95,
        wspace=0.78,
        fs=1.8,
    )
    save(fig, "theory_8_anatomy", output_dir)


# ══════════════════════════════════════════════ 9 · catalog
def _grad(ax, hexes, y, label, h=0.82):
    ax.imshow(
        [list(range(len(hexes)))],
        aspect="auto",
        cmap=ListedColormap(hexes),
        extent=(0, 10, y, y + h),
    )
    ax.text(
        -0.15,
        y + h / 2,
        label,
        ha="right",
        va="center",
        fontsize=dm.fs(-1.5),
        family="monospace",
        color=INK,
    )


def fig_catalog(output_dir: Path) -> None:
    groups = [
        ("Single-hue 20 — family name as-is", [*R.FAMILIES, "gray"]),
        (
            "Multi-hue 9 — natural-light scenes (light metaphor: low = dark)",
            [
                "aurora",
                "afterglow",
                "blaze",
                "lava",
                "lagoon",
                "glacier",
                "canopy",
                "haze",
                "iris",
            ],
        ),
        (
            "Diverging 11 — bipolar pair (ink metaphor)",
            [
                "blue_red",
                "blue_orange",
                "teal_rose",
                "green_purple",
                "purple_orange",
                "cyan_red",
                "teal_amber",
                "violet_lime",
                "indigo_amber",
                "gray_blue",
                "gray_red",
            ],
        ),
        ("Cyclic 3 — circular light phenomena", ["hue", "halo", "corona"]),
    ]
    fig, ax = plt.subplots(figsize=dm.figsize("16cm", 1.95))
    y = 0.0
    for gtitle, names in groups:
        ax.text(
            -0.15,
            y + 0.4,
            gtitle,
            ha="right",
            va="center",
            fontsize=dm.fs(0),
            fontweight="bold",
            color=INK,
        )
        y += 1.0
        for name in names:
            _grad(ax, CMAPS[name], y, name)
            y += 1.0
        y += 0.3
    # qualitative — 11 curated sets plus two registered cycle surfaces
    ax.text(
        -0.15,
        y + 0.4,
        "Qualitative 13 — 11 curated sets + 2 registered cycles",
        ha="right",
        va="center",
        fontsize=dm.fs(0),
        fontweight="bold",
        color=INK,
    )
    y += 1.0
    qualitative = [
        *((name, CUR.CURATED[name]) for name in CUR.CURATED_QUALITATIVE_ORDER),
        *((name, CYCLES[name]) for name in CYCLES),
    ]
    for name, hexes in qualitative:
        _grad(ax, hexes, y, name)
        y += 1.0
    ax.set_xlim(-4.4, 10.2)
    ax.set_ylim(y, -0.3)
    ax.axis("off")
    save(fig, "theory_9_cmap_catalog", output_dir)


# ══════════════════════════════════════════════ 10 · cyclic demo
def fig_cyclic_demo(output_dir: Path) -> None:
    xx, yy = np.meshgrid(np.linspace(-3, 3, 220), np.linspace(-2, 2, 150))
    phase = (np.arctan2(yy, xx) + 0.6 * np.sin(np.hypot(xx, yy) * 1.5)) % (
        2 * np.pi
    )
    phase = phase / (2 * np.pi)
    fig, axs = plt.subplots(1, 3, figsize=dm.figsize("16cm", 0.34))
    panels = [
        (
            axs[0],
            CMAPS["aurora"],
            "ordinary sequential (aurora)",
            "false seam\n(phantom discontinuity)",
        ),
        (
            axs[1],
            CMAPS["halo"],
            "dark-center cyclic (halo)",
            "smooth seam\ndark center",
        ),
        (
            axs[2],
            CMAPS["hue"],
            "cyclic (hue)",
            "isoluminant cycle\nphase = hue",
        ),
    ]
    for ax, hexes, ptitle, sub in panels:
        ax.imshow(
            phase, aspect="auto", cmap=ListedColormap(hexes), vmin=0, vmax=1
        )
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(ptitle, fontsize=dm.fs(-0.5), loc="left")
        ax.text(
            0.5,
            -0.08,
            sub,
            transform=ax.transAxes,
            ha="center",
            va="top",
            fontsize=dm.fs(-2.5),
            color=MUT,
        )
    fig.subplots_adjust(top=0.80, wspace=0.12)
    fig.suptitle(
        "Why cyclic colormaps — angle / phase data (0° = 360°)",
        fontsize=dm.fs(2.0),
        fontweight="bold",
        x=0.012,
        ha="left",
        y=0.98,
    )
    save(fig, "theory_10_cyclic_demo", output_dir)


def render_all(output_dir: Path) -> None:
    """Render the complete ten-figure inventory into ``output_dir``."""
    print("rendering theory figures ...")
    fig_lightness_weber(output_dir)
    fig_floor(output_dir)
    fig_drift(output_dir)
    fig_chroma(output_dir)
    fig_spacing(output_dir)
    fig_metric(output_dir)
    fig_dcseq(output_dir)
    fig_anatomy(output_dir)
    fig_catalog(output_dir)
    fig_cyclic_demo(output_dir)
    print(f"done → {output_dir}")


def _resolve_output_dir(value: str) -> Path:
    """Resolve relative CLI paths against the generator, not the caller cwd."""
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate
    return HERE / candidate


def _svg_inventory(directory: Path) -> dict[str, bytes]:
    """Read tracked-format theory assets without creating ``directory``."""
    if not directory.is_dir():
        return {}
    return {
        path.name: path.read_bytes()
        for path in sorted(directory.glob("theory_*.svg"))
        if path.is_file()
    }


# Two of the ten figures rasterise their gradients, so matplotlib embeds them
# as base64 PNG; the other eight are pure vector and reproduce byte-identically
# anywhere. PNG is zlib-compressed and its pixels come from antialiased float
# math, so two machines can render the same picture into different bytes. This
# check exists to ask whether the committed asset is still the picture the
# generator produces, not whether two machines agree on a compressed stream.
# Matplotlib wraps the payload across lines, so whitespace is part of it.
_DATA_URI = re.compile(rb"data:image/png;base64,([A-Za-z0-9+/=\s]+?)\"")

# One 8-bit level. A real change to a figure moves pixels far more than this;
# cross-machine antialiasing noise does not.
_PIXEL_TOLERANCE = 1


def _split_rasters(svg: bytes) -> tuple[bytes, list[np.ndarray]]:
    """Return the SVG with image payloads elided, plus their decoded pixels."""
    from PIL import Image

    images: list[np.ndarray] = []

    def collect(match: re.Match[bytes]) -> bytes:
        payload = base64.b64decode(b"".join(match.group(1).split()))
        with Image.open(io.BytesIO(payload)) as opened:
            images.append(np.asarray(opened.convert("RGBA"), dtype=np.int16))
        return b'data:image/png;base64,<elided>"'

    return _DATA_URI.sub(collect, svg), images


def _svg_mismatch(tracked: bytes, generated: bytes) -> str | None:
    """Return why two theory SVGs differ in content, or None if they agree.

    The reason is reported rather than swallowed: when this check fails on a
    machine that is not the author's, "stale" alone says nothing about whether
    the picture changed, the surrounding markup changed, or only the
    compression did.
    """
    if tracked == generated:
        return None
    tracked_text, tracked_images = _split_rasters(tracked)
    generated_text, generated_images = _split_rasters(generated)
    if tracked_text != generated_text:
        for index, (left, right) in enumerate(
            zip(tracked_text, generated_text, strict=False)
        ):
            if left != right:
                excerpt = tracked_text[max(0, index - 40) : index + 40]
                return (
                    f"markup differs at byte {index} of "
                    f"{len(tracked_text)}/{len(generated_text)}: "
                    f"{excerpt!r} -> {generated_text[max(0, index - 40) : index + 40]!r}"
                )
        return (
            f"markup length differs: {len(tracked_text)} vs "
            f"{len(generated_text)}"
        )
    if len(tracked_images) != len(generated_images):
        return (
            f"raster count differs: {len(tracked_images)} vs "
            f"{len(generated_images)}"
        )
    for index, (left, right) in enumerate(
        zip(tracked_images, generated_images, strict=True)
    ):
        if left.shape != right.shape:
            return f"raster {index} shape {left.shape} vs {right.shape}"
        worst = int(np.abs(left - right).max(initial=0))
        if worst > _PIXEL_TOLERANCE:
            differing = int((np.abs(left - right) > _PIXEL_TOLERANCE).sum())
            return (
                f"raster {index} differs by up to {worst} levels "
                f"({differing} of {left.size} samples beyond tolerance)"
            )
    return None


def check(output_dir: Path) -> int:
    """Render hermetically and compare every expected SVG without writing."""
    with TemporaryDirectory(prefix="dartwork-mpl-theory-") as temporary:
        generated_dir = Path(temporary)
        render_all(generated_dir)
        generated = _svg_inventory(generated_dir)

    tracked = _svg_inventory(output_dir)
    expected_names = {f"{name}.svg" for name in FIGURE_NAMES}
    tracked_names = set(tracked)
    generated_names = set(generated)
    missing = sorted(expected_names - tracked_names)
    extra = sorted(tracked_names - expected_names)
    incomplete = sorted(expected_names - generated_names)
    reasons = {}
    for name in sorted(expected_names & tracked_names & generated_names):
        reason = _svg_mismatch(tracked[name], generated[name])
        if reason is not None:
            reasons[name] = reason
    stale = sorted(reasons)
    if missing or extra or incomplete or stale:
        for label, names in (
            ("missing", missing),
            ("extra", extra),
            ("not generated", incomplete),
            ("stale", stale),
        ):
            if names:
                print(f"{label}: {', '.join(names)}", file=sys.stderr)
        for name, reason in reasons.items():
            print(f"  {name}: {reason}", file=sys.stderr)
        return 1
    print(f"theory assets are fresh: {output_dir}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default="theory_figures",
        help="output directory (relative paths resolve beside this generator)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="render temporarily and fail if tracked SVG bytes differ",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run normal generation or the non-writing deterministic check."""
    args = _parser().parse_args(argv)
    output_dir = _resolve_output_dir(args.output_dir)
    if args.check:
        return check(output_dir)
    render_all(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
