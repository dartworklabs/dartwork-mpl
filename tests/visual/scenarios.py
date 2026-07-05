from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from matplotlib.figure import Figure

import dartwork_mpl as dm

_TIMES = "\u00d7"
_PLUS_MINUS = "\u00b1"
_ARROW = "\u2192"
_SPECIAL_CHARS = f"{_TIMES} {_PLUS_MINUS} {_ARROW}"


@dataclass(frozen=True)
class Expectations:
    n_axes: int = 1
    min_lines: int = 0
    min_patches: int = 0
    min_images: int = 0
    min_collections: int = 0
    texts_contain: tuple[str, ...] = ()
    palette: tuple[str, ...] = ()
    require_ylabel: bool = True
    tolerance: float = 20.0


@dataclass(frozen=True)
class Scenario:
    name: str
    build: Callable[[], Figure]
    expect: Expectations


def _blue_tokens(count: int | None = None) -> tuple[str, ...]:
    tokens = tuple(dm.get_palette("blue"))
    return tokens if count is None else tokens[:count]


def _build_preset_report_line() -> Figure:
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    x = np.arange(1, 9)
    palette = _blue_tokens(3)

    series = (
        ("Revenue", np.array([9.2, 9.8, 10.1, 10.8, 11.6, 12.0, 12.4, 13.1])),
        ("Margin", np.array([6.1, 6.3, 6.5, 6.7, 7.0, 7.2, 7.4, 7.8])),
        ("Retention", np.array([4.8, 5.0, 5.2, 5.1, 5.5, 5.8, 6.0, 6.3])),
    )
    for (label, values), color in zip(series, palette, strict=True):
        ax.plot(
            x, values, marker="o", color=color, linewidth=dm.lw(0), label=label
        )

    ax.set_xlabel("Quarter", fontsize=dm.fs(0))
    ax.set_ylabel("Index", fontsize=dm.fs(0))
    ax.set_title("Report KPI Signals", fontsize=dm.fs(1), fontweight=dm.fw(1))
    ax.grid(True, axis="y", color="dc.blue1", alpha=0.16, linewidth=0.5)
    ax.legend()
    dm.simple_layout(fig)
    return fig


def _build_preset_report_kr_bars() -> Figure:
    dm.style.use("report-kr")
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "wide"))
    categories = ["매출", "이익", "고객", "유지율"]
    values = [128, 74, 96, 88]
    palette = _blue_tokens(4)

    bars = ax.bar(categories, values, color=palette)
    for bar, value in zip(bars, values, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{value}",
            ha="center",
            va="bottom",
            fontsize=dm.fs(-1),
        )

    ax.set_xlabel("지표", fontsize=dm.fs(0))
    ax.set_ylabel("매출 지수", fontsize=dm.fs(0))
    ax.set_title("분기별 매출 요약", fontsize=dm.fs(1), fontweight=dm.fw(1))
    dm.simple_layout(fig)
    return fig


def _build_preset_scientific_scatter() -> Figure:
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "square"))
    rng = np.random.default_rng(3)
    x = np.linspace(-2.5, 2.5, 56)
    y = 1.45 * x + rng.normal(0, 0.42, size=x.size)
    palette = _blue_tokens(2)

    ax.scatter(x, y, s=34, color=palette[0], alpha=0.72, label="Samples")
    slope, intercept = np.polyfit(x, y, 1)
    x_line = np.linspace(x.min(), x.max(), 120)
    ax.plot(
        x_line,
        slope * x_line + intercept,
        color=palette[1],
        linestyle="--",
        linewidth=dm.lw(0),
        label=f"fit = {slope:.2f}x + {intercept:.2f}",
    )

    ax.set_xlabel("Input", fontsize=dm.fs(0))
    ax.set_ylabel("Response", fontsize=dm.fs(0))
    ax.set_title("Scientific Scatter Fit", fontsize=dm.fs(1))
    ax.grid(True, color="dc.blue1", alpha=0.14, linewidth=0.5)
    ax.legend()
    dm.simple_layout(fig)
    return fig


def _build_preset_scientific_kr_hist() -> Figure:
    dm.style.use("scientific-kr")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    rng = np.random.default_rng(11)
    data = rng.normal(64, 7, 360)
    palette = _blue_tokens(2)

    ax.hist(
        data,
        bins=18,
        density=True,
        color=palette[0],
        alpha=0.72,
        edgecolor="white",
        linewidth=0.5,
        label="관측값",
    )
    mean = data.mean()
    std = data.std()
    xx = np.linspace(data.min(), data.max(), 160)
    pdf = (1.0 / (std * np.sqrt(2 * np.pi))) * np.exp(
        -0.5 * ((xx - mean) / std) ** 2
    )
    ax.plot(xx, pdf, color=palette[1], linewidth=dm.lw(0), label="정규 적합")

    ax.set_xlabel("측정값", fontsize=dm.fs(0))
    ax.set_ylabel("확률 밀도", fontsize=dm.fs(0))
    ax.set_title("분포 분석", fontsize=dm.fs(1))
    ax.legend()
    dm.simple_layout(fig)
    return fig


def _build_line_signals() -> Figure:
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    x = np.linspace(0, 10, 100)
    y1 = np.sin(x) * 1e6
    y2 = np.cos(x) * 1e6
    palette = _blue_tokens(2)

    ax.plot(x, y1, label="Signal A", color=palette[0], linewidth=dm.lw(0))
    ax.plot(x, y2, label="Signal B", color=palette[1], linewidth=dm.lw(0))
    dm.format_axis_si(ax, axis="y")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(
        True,
        axis="y",
        color="dc.indigo1",
        alpha=0.2,
        linestyle="--",
        linewidth=0.5,
    )
    ax.set_axisbelow(True)
    for spine_name in ("bottom", "left"):
        ax.spines[spine_name].set_color("dc.indigo3")
        ax.spines[spine_name].set_linewidth(0.5)
    ax.grid(True, axis="x", color="dc.indigo1", alpha=0.2, linewidth=0.5)
    ax.set_xlabel("Time (s)", fontsize=dm.fs(0))
    ax.set_ylabel("Amplitude", fontsize=dm.fs(0))
    ax.set_title("Signal Analysis", fontsize=dm.fs(1))
    ax.legend()
    dm.simple_layout(fig)
    return fig


def _build_bar_value_labels() -> Figure:
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "wide"))
    categories = ["Group A", "Group B", "Group C", "Group D"]
    values = [1_200_000, 1_450_000, 1_380_000, 1_620_000]
    palette = _blue_tokens(4)

    bars = ax.bar(categories, values, color=palette)
    dm.format_axis_millions(ax, axis="y")
    for bar, value in zip(bars, values, strict=True):
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{value / 1e6:.2f}M",
            ha="center",
            va="bottom",
            fontsize=dm.fs(-1),
        )

    for spine_name in ("top", "right"):
        ax.spines[spine_name].set_visible(False)
    ax.set_ylabel("Count", fontsize=dm.fs(0))
    ax.set_title("Grouped Count Comparison", fontsize=dm.fs(1))
    dm.simple_layout(fig)
    return fig


def _build_scatter_fit() -> Figure:
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "square"))
    rng = np.random.default_rng(42)
    x = rng.standard_normal(50)
    y = 2 * x + rng.standard_normal(50) * 0.5
    palette = _blue_tokens(2)

    ax.scatter(x, y, alpha=0.6, s=50, color=palette[0], label="Samples")
    slope, intercept = np.polyfit(x, y, 1)
    x_line = np.linspace(x.min(), x.max(), 100)
    ax.plot(
        x_line,
        slope * x_line + intercept,
        color=palette[1],
        linestyle="--",
        alpha=0.8,
        linewidth=dm.lw(0),
        label=f"y = {slope:.2f}x + {intercept:.2f}",
    )
    ax.grid(True, color="dc.indigo1", alpha=0.15, linewidth=0.5)
    ax.set_axisbelow(True)
    ax.set_xlabel("X Variable", fontsize=dm.fs(0))
    ax.set_ylabel("Y Variable", fontsize=dm.fs(0))
    ax.set_title("Correlation Analysis", fontsize=dm.fs(1))
    ax.legend()
    dm.simple_layout(fig)
    return fig


def _build_histogram_normal_fit() -> Figure:
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    rng = np.random.default_rng(42)
    data = rng.normal(100, 15, 1000)
    palette = _blue_tokens(2)

    ax.hist(
        data,
        bins=30,
        density=True,
        alpha=0.7,
        color=palette[0],
        edgecolor="black",
        linewidth=0.5,
    )
    mean = data.mean()
    std = data.std()
    xmin, xmax = ax.get_xlim()
    xx = np.linspace(xmin, xmax, 100)
    pdf = (1.0 / (std * np.sqrt(2 * np.pi))) * np.exp(
        -0.5 * ((xx - mean) / std) ** 2
    )
    ax.plot(
        xx,
        pdf,
        color=palette[1],
        linewidth=dm.lw(0),
        label=f"Normal fit\nmean={mean:.1f}, std={std:.1f}",
    )

    ax.yaxis.set_major_formatter(ticker.PercentFormatter(1.0, decimals=0))
    ax.set_xlabel("Value", fontsize=dm.fs(0))
    ax.set_ylabel("Density", fontsize=dm.fs(0))
    ax.set_title("Distribution Analysis", fontsize=dm.fs(1))
    ax.legend()
    dm.simple_layout(fig)
    return fig


def _build_heatmap() -> Figure:
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "square"))
    rng = np.random.default_rng(0)
    data = rng.standard_normal((10, 10))

    image = ax.imshow(data, cmap="dc.blue_red", aspect="auto", vmin=-2, vmax=2)
    cbar = plt.colorbar(image, ax=ax)
    cbar.set_label("Value", rotation=270, labelpad=15, fontsize=dm.fs(0))
    ax.set_xlabel("Column", fontsize=dm.fs(0))
    ax.set_ylabel("Row", fontsize=dm.fs(0))
    ax.set_title("Heatmap Example", fontsize=dm.fs(1))
    ax.set_xticks(np.arange(10))
    ax.set_yticks(np.arange(10))
    dm.simple_layout(fig)
    return fig


def _build_donut_composition() -> Figure:
    dm.style.use("report-kr")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "square"))
    sizes = [35, 30, 20, 10, 5]
    labels = ["범주 A", "범주 B", "범주 C", "범주 D", "기타"]
    colors = _blue_tokens(5)

    _wedges, _texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        colors=colors,
        autopct="%1.1f%%",
        startangle=90,
        pctdistance=0.85,
    )
    circle = plt.Circle((0, 0), 0.70, fc="white")
    ax.add_artist(circle)
    ax.text(
        0,
        0,
        "구성 비율",
        ha="center",
        va="center",
        fontsize=dm.fs(1),
        fontweight=dm.fw(1),
    )
    for autotext in autotexts:
        autotext.set_color("white")
        autotext.set_fontsize(dm.fs(-1))
        autotext.set_fontweight(dm.fw(1))
    ax.set_title("범주별 구성", fontsize=dm.fs(1))
    dm.simple_layout(fig)
    return fig


def _build_dual_axis_timeseries() -> Figure:
    dm.style.use("report-kr")
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "wide"))
    dates = np.arange("2024-01", "2025-01", dtype="datetime64[M]")
    primary = np.array(
        [120, 135, 128, 142, 155, 148, 162, 175, 168, 182, 195, 210]
    )
    rng = np.random.default_rng(0)
    secondary = primary * 0.15 + rng.standard_normal(12) * 5
    palette = _blue_tokens(2)

    ax.bar(dates, primary, alpha=0.3, label="주 계열", color=palette[0])
    ax.set_xlabel("월", fontsize=dm.fs(0))
    ax.set_ylabel("주 계열 (단위)", color=palette[0], fontsize=dm.fs(0))
    ax.tick_params(axis="y", labelcolor=palette[0])

    ax2 = ax.twinx()
    ax2.plot(
        dates,
        secondary,
        color=palette[1],
        marker="o",
        linewidth=dm.lw(0),
        label="보조 계열",
    )
    ax2.set_ylabel("보조 계열 (단위)", color=palette[1], fontsize=dm.fs(0))
    ax2.tick_params(axis="y", labelcolor=palette[1])
    ax.set_title("월별 이중 축 계열", fontsize=dm.fs(1))
    ax.grid(True, alpha=0.3, linewidth=0.5)

    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, loc="upper left")
    dm.simple_layout(fig)
    return fig


def _build_palette_swatch() -> Figure:
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "wide"))
    palette = _blue_tokens()
    positions = np.arange(len(palette))

    ax.bar(positions, np.ones(len(palette)), color=palette, width=0.82)
    ax.set_xticks(positions)
    ax.set_xticklabels([f"T{i}" for i in positions])
    ax.set_yticks([])
    ax.set_xlabel("Trustworthy palette token", fontsize=dm.fs(0))
    ax.set_ylabel("Swatch", fontsize=dm.fs(0))
    ax.set_title("Trustworthy Palette Swatches", fontsize=dm.fs(1))
    for spine_name in ("top", "right", "left"):
        ax.spines[spine_name].set_visible(False)
    dm.simple_layout(fig)
    return fig


def _build_colormap_strip() -> Figure:
    dm.style.use("scientific")
    fig, axes = plt.subplots(2, 1, figsize=dm.figsize("13cm", "standard"))
    gradient = np.linspace(0, 1, 256).reshape(1, -1)
    specs = (
        ("dc.blue", "Sequential blue"),
        ("dc.blue_red", "Diverging blue-red"),
    )

    for ax, (cmap, label) in zip(axes, specs, strict=True):
        ax.imshow(gradient, aspect="auto", cmap=cmap)
        ax.set_yticks([])
        ax.set_xticks([])
        ax.set_ylabel(label, fontsize=dm.fs(0))
        for spine in ax.spines.values():
            spine.set_linewidth(0.5)

    fig.suptitle("Dartwork Colormap Strips", fontsize=dm.fs(1))
    dm.simple_layout(fig)
    return fig


def _build_kr_math_labels() -> Figure:
    dm.style.use("scientific-kr")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    x = np.linspace(0, 4, 80)
    palette = _blue_tokens(1)

    ax.plot(
        x,
        np.exp(-x / 3) * np.sin(2.4 * x),
        color=palette[0],
        linewidth=dm.lw(0),
    )
    ax.set_title(
        r"한글 수식 검증: $\alpha^2 + \beta$",
        fontsize=dm.fs(1),
        fontweight=dm.fw(1),
    )
    ax.set_xlabel(
        f"시간 {_TIMES} 단계 {_PLUS_MINUS} 오차 {_ARROW} 결과",
        fontsize=dm.fs(0),
    )
    ax.set_ylabel("응답값", fontsize=dm.fs(0))
    ax.text(
        0.05,
        0.9,
        f"특수문자 {_SPECIAL_CHARS}",
        transform=ax.transAxes,
        fontsize=dm.fs(-1),
    )
    ax.grid(True, alpha=0.18, linewidth=0.5)
    dm.simple_layout(fig)
    return fig


def all_scenarios() -> list[Scenario]:
    blue_palette = _blue_tokens()
    return [
        Scenario(
            "preset_report_line",
            _build_preset_report_line,
            Expectations(min_lines=3, palette=blue_palette[:3]),
        ),
        Scenario(
            "preset_report_kr_bars",
            _build_preset_report_kr_bars,
            Expectations(
                min_patches=4,
                texts_contain=("매출",),
                palette=blue_palette[:4],
                tolerance=22.0,
            ),
        ),
        Scenario(
            "preset_scientific_scatter",
            _build_preset_scientific_scatter,
            Expectations(
                min_lines=1, min_collections=1, palette=blue_palette[:2]
            ),
        ),
        Scenario(
            "preset_scientific_kr_hist",
            _build_preset_scientific_kr_hist,
            Expectations(
                min_lines=1,
                min_patches=5,
                texts_contain=("확률 밀도",),
                palette=blue_palette[:2],
                tolerance=22.0,
            ),
        ),
        Scenario(
            "line_signals",
            _build_line_signals,
            Expectations(min_lines=2, palette=blue_palette[:2]),
        ),
        Scenario(
            "bar_value_labels",
            _build_bar_value_labels,
            Expectations(
                min_patches=4,
                texts_contain=("1.20M",),
                palette=blue_palette[:4],
            ),
        ),
        Scenario(
            "scatter_fit",
            _build_scatter_fit,
            Expectations(
                min_lines=1, min_collections=1, palette=blue_palette[:2]
            ),
        ),
        Scenario(
            "histogram_normal_fit",
            _build_histogram_normal_fit,
            Expectations(
                min_lines=1,
                min_patches=5,
                texts_contain=("Normal fit",),
                palette=blue_palette[:2],
            ),
        ),
        Scenario(
            "heatmap",
            _build_heatmap,
            Expectations(n_axes=2, min_images=1, texts_contain=("Value",)),
        ),
        Scenario(
            "donut_composition",
            _build_donut_composition,
            Expectations(
                min_patches=3,
                texts_contain=("구성",),
                palette=blue_palette[:5],
                require_ylabel=False,
                tolerance=24.0,
            ),
        ),
        Scenario(
            "dual_axis_timeseries",
            _build_dual_axis_timeseries,
            Expectations(
                n_axes=2,
                min_lines=1,
                min_patches=12,
                texts_contain=("보조 계열",),
                palette=blue_palette[:2],
                tolerance=24.0,
            ),
        ),
        Scenario(
            "palette_swatch",
            _build_palette_swatch,
            Expectations(min_patches=8, palette=blue_palette),
        ),
        Scenario(
            "colormap_strip",
            _build_colormap_strip,
            Expectations(n_axes=2, min_images=2, require_ylabel=False),
        ),
        Scenario(
            "kr_math_labels",
            _build_kr_math_labels,
            Expectations(
                min_lines=1,
                texts_contain=("한글", _SPECIAL_CHARS),
                palette=blue_palette[:1],
                tolerance=25.0,
            ),
        ),
    ]
