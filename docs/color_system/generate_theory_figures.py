"""dartwork color system v5 — design-theory figures for the docs site.

Ten self-contained vector figures that explain each generation axiom
visually. Every data point is computed live from the *shipped* v5 package
(``dartwork_mpl.colors``) — the palette, the recipe parameters, and the
perceptual metrics — so the figures are evidence of the theory rather than
decoration.

Run::

    PYTHONPATH=src python docs/color_system/generate_theory_figures.py

Output: ``docs/color_system/theory_figures/theory_*.svg`` (tracked static
assets referenced by ``docs/color_system/design.md``). The figures only need
to be regenerated when the 91-parameter SSOT changes.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap

import dartwork_mpl as dm
from dartwork_mpl.colors import Color
from dartwork_mpl.colors import _gates as GA
from dartwork_mpl.colors import _generate as GEN
from dartwork_mpl.colors import _generated as G
from dartwork_mpl.colors import _metrics as M
from dartwork_mpl.colors import _recipe as R

HERE = Path(__file__).resolve().parent
OUTDIR = HERE / "theory_figures"
OUTDIR.mkdir(parents=True, exist_ok=True)
PREVIEW = Path(
    "/private/tmp/claude-501/-Users-wonjun-Codes-company-analysis"
    "/1cc38d4a-93c3-4c1f-a3c6-13cabee5ffdd/scratchpad/theory_prev"
)
PREVIEW.mkdir(parents=True, exist_ok=True)

# Pretendard (report-kr preset) gives full Latin + Greek + subscript coverage
# for the mathtext labels; the labels themselves are English. This generator
# runs only when the SSOT changes — the committed SVGs are the docs assets.
dm.style.use("report-kr")
# report-kr renders bold titles in Paperlogy, which lacks Greek / super- and
# subscripts; Pretendard covers the full Latin + Greek + sub/superscript set
# the axiom labels need. Lead the fallback chain with Pretendard so titles
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
PARAMS = R.FAMILY_PARAMS  # fam -> FamilyParams (15 chromatic)
FOURIER = R.FOURIER

# ── metric helpers over hex (thin wrappers on the shipped kernel) ──────────


def lab_l(h: str) -> float:
    return M.lab_l_hex(h)


def de_ok(a: str, b: str) -> float:
    return M.de_ok_rgb(M.rgb_from_hex(a), M.rgb_from_hex(b))


def de2000(a: str, b: str) -> float:
    return M.de2000_hex(a, b)


def de76(a: str, b: str) -> float:
    la = M.lab_from_rgb(M.rgb_from_hex(a))
    lb = M.lab_from_rgb(M.rgb_from_hex(b))
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(la, lb, strict=True)))


def cvd(h: str, kind: str) -> str:
    return M.hex_from_rgb(M.cvd_rgb(M.rgb_from_hex(h), kind))


def oklch(h: str) -> tuple[float, float, float]:
    return Color(h).to_oklch()


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


def save(fig, name):
    # Deterministic SVG: a fixed per-figure hashsalt keeps the clip-path /
    # gradient element ids stable across runs, and ``metadata={"Date": None}``
    # drops the embedded timestamp — so re-rendering yields a byte-identical
    # file unless the plotted data actually changed. That keeps "the pictures
    # are the proof" honest: a number correction is a one-line diff, not a full
    # re-serialization from churned ids + a new date.
    matplotlib.rcParams["svg.hashsalt"] = name
    fig.savefig(
        OUTDIR / f"{name}.svg",
        bbox_inches="tight",
        pad_inches=0.08,
        transparent=True,
        metadata={"Date": None},
    )
    fig.savefig(
        PREVIEW / f"{name}.png", bbox_inches="tight", pad_inches=0.08, dpi=120
    )
    plt.close(fig)
    print(f"  {name}.svg")


# ══════════════════════════════════════════════ 1 · why L* + OKLCH
def fig_lightness_weber():
    fig, axs = plt.subplots(2, 1, figsize=dm.figsize("15cm", 0.42))
    n = 12
    ys = np.linspace(0.02, 1.0, n)
    phys = [
        "#{0:02x}{0:02x}{0:02x}".format(round(M._delin(y) * 255)) for y in ys
    ]
    ls = np.linspace(12, 97, n)
    perc = []
    for L in ls:
        fy = (L + 16) / 116
        yy = fy**3 if fy**3 > 216 / 24389 else (116 * fy - 16) * 27 / 24389
        perc.append("#{0:02x}{0:02x}{0:02x}".format(round(M._delin(yy) * 255)))
    rows = [
        (
            axs[0],
            phys,
            "Even steps in physical luminance (Y)",
            "The light end bunches up — vision compresses lightness "
            "logarithmically (Weber–Fechner)",
        ),
        (
            axs[1],
            perc,
            "Even steps in CIELAB L*",
            "A perceptually even staircase — L* already performs that log "
            "compression",
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
        "Why the lightness axis is CIELAB L* — "
        "“log spacing” is already built in",
        top=0.80,
        y=0.95,
        hspace=1.15,
    )
    save(fig, "theory_1_lightness_weber")


# ══════════════════════════════════════════════ 2 · hue-specific floor
def fig_floor():
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
            L = lab_l(h)
            ax.add_patch(
                plt.Rectangle(
                    (xi - 0.4, L - 2.1), 0.8, 4.2, color=h, ec="white", lw=0.5
                )
            )
        floor = lab_l(row[9])
        ax.plot([xi - 0.46, xi + 0.46], [floor, floor], color=INK, lw=1.0)
        ax.text(
            xi,
            floor - 4.2,
            f"{floor:.0f}",
            ha="center",
            va="top",
            fontsize=dm.fs(-2),
            color=INK,
            fontweight="bold",
        )
    ax.set_xticks(range(len(fams)))
    ax.set_xticklabels(fams, fontsize=dm.fs(-1.5), rotation=32, ha="right")
    ax.set_ylabel("CIELAB L* (lightness)", fontsize=dm.fs(0))
    ax.set_ylim(30, 100)
    ax.set_xlim(-0.8, len(fams) - 0.2)
    ax.axhspan(30, 40, color=_C("oc.gray2"), alpha=0.35, zorder=0)
    ax.text(
        len(fams) - 0.3,
        96,
        "Lightness cap L*96\n(shared start for every family)",
        ha="right",
        va="top",
        fontsize=dm.fs(-2),
        color=MUT,
    )
    ax.annotate(
        "Yellow stops at L*60\n(darker turns olive)",
        xy=(0, 60),
        xytext=(1.7, 78),
        fontsize=dm.fs(-2),
        color=INK,
        arrowprops={"arrowstyle": "->", "color": MUT, "lw": 0.9},
    )
    ax.annotate(
        "Violet reaches L*37\n(stays violet when dark)",
        xy=(7, 37),
        xytext=(4.3, 46),
        fontsize=dm.fs(-2),
        color=INK,
        arrowprops={"arrowstyle": "->", "color": MUT, "lw": 0.9},
    )
    ax.set_title(
        "Axiom A2 — hue-specific lightness floor: "
        "“only as dark as the hue survives”",
        fontsize=dm.fs(2.5),
        fontweight="bold",
        loc="left",
        pad=8,
    )
    save(fig, "theory_2_floor")


# ══════════════════════════════════════════════ 3 · drift power law
def fig_drift():
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
        "Axiom A4 — drift power law: warm hues rotate like flame as "
        "they darken",
        top=0.82,
        y=0.955,
        wspace=0.28,
    )
    save(fig, "theory_3_drift")


# ══════════════════════════════════════════════ 4 · chroma fingerprint
def fig_chroma():
    fig, axs = plt.subplots(1, 2, figsize=dm.figsize("15cm", 0.46))
    ax = axs[0]
    hh = np.linspace(0, 360, 361)
    cc = [R.fourier_eval(FOURIER["cmax_k3"], h) for h in hh]
    ax.plot(hh, cc, color=INK, lw=dm.lw(0.3), zorder=2)
    for fam, p in PARAMS.items():
        hm = R.mid_hue(p)
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
        "cyan valley\n(sRGB is stingy with cyan)",
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
        f"Chroma fingerprint {CMAX}(h)  (R²=0.945)",
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
        f"Shared shape template (only {TP} varies)",
        fontsize=dm.fs(-0.5),
        loc="left",
    )
    title(
        fig,
        "Axiom A3 — chroma: hue fingerprint × shared shape",
        top=0.82,
        y=0.955,
        wspace=0.34,
    )
    save(fig, "theory_4_chroma")


# ══════════════════════════════════════════════ 5 · step spacing
def fig_spacing():
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
    ax2.set_ylabel("neighbor ΔE (OKLab)", fontsize=dm.fs(-0.5))
    ax2.legend(fontsize=dm.fs(-2), frameon=False, loc="upper center", ncol=2)
    ax2.set_title(
        "Only equalization flattens neighbor ΔE — step "
        "arithmetic becomes meaningful",
        fontsize=dm.fs(0),
        loc="left",
    )
    title(
        fig,
        "Axiom A5 — step spacing: perceptual even-spacing by default "
        "(warp is opt-in)",
        top=0.82,
        y=0.955,
        hspace=0.65,
    )
    save(fig, "theory_5_spacing")


# ══════════════════════════════════════════════ 6 · metric reform
def fig_metric():
    a, b = PALETTE["blue"][7], PALETTE["violet"][7]
    fig, axs = plt.subplots(
        1,
        2,
        figsize=dm.figsize("15cm", 0.44),
        gridspec_kw={"width_ratios": [1, 1.15]},
    )
    ax = axs[0]
    pairs = [
        ("normal vision", a, b),
        (
            "deuteranopia\n(deutan) simulation",
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
    ax.set_title("Two clearly different colors…", fontsize=dm.fs(0), loc="left")

    ax2 = axs[1]
    d76 = de76(cvd(a, "deutan"), cvd(b, "deutan"))
    d00 = de2000(cvd(a, "deutan"), cvd(b, "deutan"))
    bars = [
        ("ΔE76", d76, _C("oc.red6"), "looks safe\n→ collapses", "white", 8.5),
        ("ΔE00", d00, _C("oc.teal7"), "correctly\nfails", INK, 6.2),
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
        "gate threshold 10",
        fontsize=dm.fs(-2.5),
        color=INK,
        ha="right",
    )
    ax2.set_xticks([0, 1])
    ax2.set_xticklabels(["ΔE76", "ΔE00"], fontsize=dm.fs(0))
    ax2.set_ylabel("color distance after deutan sim", fontsize=dm.fs(-0.5))
    ax2.set_ylim(0, 20)
    ax2.set_xlim(-0.6, 1.6)
    ax2.set_title(
        "…judged oppositely by two metrics", fontsize=dm.fs(0), loc="left"
    )
    title(
        fig,
        "Metric reform — ΔE76 inflates high-chroma distances",
        top=0.80,
        y=0.95,
        wspace=0.3,
        fs=2.2,
    )
    save(fig, "theory_6_metric")


# ══════════════════════════════════════════════ 7 · cmap wide L*
def fig_dcseq():
    import matplotlib as mpl

    seq = [CMAPS["aurora"][round(i * 255 / 31)] for i in range(32)]
    vir = [
        mpl.colors.to_hex(mpl.colormaps["viridis"](i / 31)) for i in range(32)
    ]
    # Measure the two swatch strips the figure actually renders, with the same
    # gate the rest of the system uses — so the printed numbers ARE the number
    # the picture proves (the page's "pictures are the proof" principle). NOTE:
    # aurora here is the shipped 256-LUT sampled at 32 stops, NOT the SSOT's
    # direct-render swatches_32 — those differ (only ~half overlap), so this cv
    # is the honest same-protocol figure vs viridis.
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
    ls_dc = [lab_l(h) for h in seq]
    ls_vir = [lab_l(h) for h in vir]
    xx = np.linspace(0, 1, 32)
    ax2.plot(
        xx, ls_dc, color=ACC, lw=dm.lw(0.5), marker="o", ms=2.2, label="aurora"
    )
    ax2.plot(xx, ls_vir, color=MUT, lw=dm.lw(0.3), ls="--", label="viridis")
    ax2.plot(
        [0, 1],
        [ls_dc[0], ls_dc[-1]],
        color=INK,
        lw=dm.lw(-0.3),
        ls=":",
        label="perfectly linear ref",
    )
    ax2.set_xlabel("cmap position", fontsize=dm.fs(-0.5))
    ax2.set_ylabel("CIELAB L*", fontsize=dm.fs(-0.5))
    ax2.legend(fontsize=dm.fs(-2.5), frameon=False, loc="upper left")
    ax2.text(
        0.98,
        20,
        f"aurora: ΔE cv {g_seq['cv']:.3f} · L* range {g_seq['L_span']}\n"
        f"viridis: cv {g_vir['cv']:.3f} · {g_vir['L_span']}"
        "  (same 32-stop measurement)",
        ha="right",
        va="bottom",
        fontsize=dm.fs(-2.5),
        color=MUT,
    )
    ax2.set_title(
        "Monotonic, near-linear L* — order preserved even in grayscale print",
        fontsize=dm.fs(0),
        loc="left",
    )
    title(
        fig,
        "Axiom A8 — heatmap cmaps use a wide L* range, not the palette floors",
        top=0.82,
        y=0.955,
        hspace=0.55,
        fs=2.0,
    )
    save(fig, "theory_7_dcseq")


# ══════════════════════════════════════════════ 8 · recipe anatomy
def fig_anatomy():
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
    ls = [lab_l(h) for h in row]
    cs = [oklch(h)[1] for h in row]
    ax2.plot(range(10), ls, color=ACC, lw=dm.lw(0.3), marker="o", ms=2.4)
    ax2.set_ylabel("L*", fontsize=dm.fs(-1), color=ACC)
    ax2.axhline(p.floor, color=ACC, ls=":", lw=dm.lw(-0.3))
    ax2.text(
        9,
        p.floor + 2,
        f"floor {p.floor:.0f}",
        ha="right",
        fontsize=dm.fs(-3),
        color=ACC,
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
        "L* (blue) · chroma (pink) trajectory", fontsize=dm.fs(-0.5), loc="left"
    )

    ax3 = axs[2]
    hs = [oklch(h)[2] for h in row]
    ax3.plot(
        range(10), hs, color=_C("oc.orange6"), lw=dm.lw(0.3), marker="^", ms=2.6
    )
    ax3.set_xlabel("step k", fontsize=dm.fs(-1))
    ax3.set_ylabel("hue h (°)", fontsize=dm.fs(-1))
    ax3.text(
        0.3,
        hs[0],
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
        f"Recipe anatomy — {fam}: 8 numbers  [{H0} {p.h0:.0f} · "
        f"{DH} {p.dh:+.0f} · {GAM} {p.gamma:.2f} · {TP} "
        f"{p.tp:.2f} · {CMAX} {p.cmax:.3f} · floor "
        f"{p.floor:.0f} · {C0} {p.c0:.2f} · {CE} {p.cend:.2f}]",
        top=0.80,
        y=0.95,
        wspace=0.78,
        fs=1.4,
    )
    save(fig, "theory_8_anatomy")


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


def fig_catalog():
    groups = [
        (
            "Single-hue 20 — family name as-is",
            [
                "red",
                "rose",
                "orange",
                "amber",
                "yellow",
                "lime",
                "green",
                "teal",
                "cyan",
                "sky",
                "blue",
                "indigo",
                "violet",
                "purple",
                "pink",
                "gray",
            ],
        ),
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
    fig, ax = plt.subplots(figsize=dm.figsize("16cm", 1.45))
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
    # qualitative — discrete cycle swatches
    ax.text(
        -0.15,
        y + 0.4,
        "Qualitative 2 — palette cycle registration",
        ha="right",
        va="center",
        fontsize=dm.fs(0),
        fontweight="bold",
        color=INK,
    )
    y += 1.0
    for name, hexes in [
        ("octave", CYCLES["octave"]),
        ("octave_print", CYCLES["octave_print"]),
    ]:
        _grad(ax, hexes, y, name)
        y += 1.0
    ax.set_xlim(-4.4, 10.2)
    ax.set_ylim(y, -0.3)
    ax.axis("off")
    dm.simple_layout(fig)
    matplotlib.rcParams["svg.hashsalt"] = "theory_9_cmap_catalog"
    fig.savefig(
        OUTDIR / "theory_9_cmap_catalog.svg",
        bbox_inches="tight",
        pad_inches=0.08,
        transparent=True,
        metadata={"Date": None},
    )
    fig.savefig(
        PREVIEW / "theory_9_cmap_catalog.png",
        bbox_inches="tight",
        pad_inches=0.08,
        dpi=115,
    )
    plt.close(fig)
    print("  theory_9_cmap_catalog.svg")


# ══════════════════════════════════════════════ 10 · cyclic demo
def fig_cyclic_demo():
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
            "false discontinuity at the 0↔1 seam (phantom shear line)",
        ),
        (axs[1], CMAPS["halo"], "cyclic (halo)", "0 = 1 joins smoothly"),
        (
            axs[2],
            CMAPS["hue"],
            "cyclic (hue)",
            "isoluminant hue wheel — phase = hue",
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
            -0.10,
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
    matplotlib.rcParams["svg.hashsalt"] = "theory_10_cyclic_demo"
    fig.savefig(
        OUTDIR / "theory_10_cyclic_demo.svg",
        bbox_inches="tight",
        pad_inches=0.08,
        transparent=True,
        metadata={"Date": None},
    )
    fig.savefig(
        PREVIEW / "theory_10_cyclic_demo.png",
        bbox_inches="tight",
        pad_inches=0.08,
        dpi=115,
    )
    plt.close(fig)
    print("  theory_10_cyclic_demo.svg")


def main():
    print("rendering theory figures ...")
    fig_lightness_weber()
    fig_floor()
    fig_drift()
    fig_chroma()
    fig_spacing()
    fig_metric()
    fig_dcseq()
    fig_anatomy()
    fig_catalog()
    fig_cyclic_demo()
    print(f"done → {OUTDIR}")


if __name__ == "__main__":
    main()
