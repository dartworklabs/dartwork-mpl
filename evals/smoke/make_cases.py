"""Recreate the small, synthetic smoke inputs without random state or downloads."""

import csv
import json
import math
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent / "cases"


def case(name, kind, lang, prompt, header, rows, followups=None):
    folder = ROOT / name
    folder.mkdir(parents=True, exist_ok=True)
    meta = {"id": name, "kind": kind, "lang": lang, "request": prompt}
    if followups:
        # A series: the changes asked for afterwards, one per turn, in order.
        meta["followups"] = followups
    (folder / "case.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n"
    )
    with (folder / "data.csv").open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)
    return folder


def main():
    case(
        "g01-single-column",
        "generate",
        "en",
        "For a journal paper, plot response against elapsed time from data.csv. This must fit an 8.5 cm single column; use 7 pt axis and tick text. Show measured and predicted as separate lines with a readable legend, keeping their units. Save PNG and PDF and leave the runnable script here.",
        ["elapsed_time_s", "measured_mV", "predicted_mV"],
        [
            (
                i,
                round(2 + math.sin(i / 3) + i / 20, 3),
                round(2 + 0.9 * math.sin(i / 3) + i / 20, 3),
            )
            for i in range(25)
        ],
    )
    case(
        "g02-panel-ratios",
        "generate",
        "en",
        "Make a 17 cm wide paper figure from data.csv: a 2 by 2 panel grid, with column widths 2:1 and row heights 3:2. Rows are North and South, columns are response and residual; plot both treatments in every panel. Label the panels (a) through (d), put units on the axes and use one shared legend for the whole figure. Keep all observations. Save PNG, PDF and a runnable script.",
        ["region", "time_s", "treatment", "response_mV", "residual_mV"],
        [
            (
                r,
                i,
                t,
                round(3 + math.sin(i / 3 + j) + k, 3),
                round(0.15 * math.cos(i + j), 3),
            )
            for k, r in enumerate(["North", "South"])
            for j, t in enumerate(["Control", "Treatment"])
            for i in range(15)
        ],
    )
    case(
        "g03-korean-labels",
        "generate",
        "ko",
        "기관 보고서에 넣을 막대그래프를 data.csv로 그려 주세요. 가로축 이름은 '장기 현장 실증 시험을 수행한 건물 및 운영 조건', 세로축 이름은 '기준 운전 대비 연간 냉난방 에너지 절감률 (%)'로 하고 범주명도 CSV의 한국어를 그대로 써 주세요. 폭은 14 cm이고 긴 글자가 잘리거나 서로 겹치지 않아야 합니다. PNG와 PDF, 실행 가능한 스크립트를 남겨 주세요.",
        ["건물 및 운영 조건", "절감률_pct"],
        [
            (f"{s} 공공청사 {t} 실증 운영 조건", 8 + i * 2)
            for i, (s, t) in enumerate(
                zip(
                    ["서울", "부산", "대전", "광주", "울산", "춘천"],
                    [
                        "야간 축열",
                        "주간 연속",
                        "외기 냉방",
                        "수요 반응",
                        "주말 간헐",
                        "혼합 환기",
                    ],
                    strict=True,
                )
            )
        ],
    )
    case(
        "g04-twin-units",
        "generate",
        "ko",
        "실험 보고서용으로 data.csv의 경과 시간에 따른 열유속과 표면 온도를 한 그림에 보여 주세요. 열유속은 왼쪽 y축 W/m², 온도는 오른쪽 y축 °C로 나누고 두 계열의 범례는 하나로 합쳐 주세요. 축과 범례는 한국어로 쓰고 단위가 혼동되지 않게 해 주세요. PNG와 PDF 및 스크립트를 남겨 주세요.",
        ["경과시간_s", "열유속_W_m2", "표면온도_C"],
        [
            (
                i * 10,
                round(120 * (1 - math.exp(-i / 8)), 2),
                round(20 + 4 * math.sin(i / 12), 2),
            )
            for i in range(30)
        ],
    )
    case(
        "g05-date-gaps",
        "generate",
        "en",
        "For a monitoring report, plot daily demand from data.csv against calendar date. Blank readings and omitted calendar days mean the sensor was offline: keep visible breaks in the line at both kinds of gap, without interpolation. Include the month boundary in the date labels. Keep the 12 cm width and save PNG, PDF and a runnable script.",
        ["date", "demand_kWh"],
        [
            (
                (date(2026, 1, 20) + timedelta(days=i)).isoformat(),
                "" if i in [7, 8, 20] else round(30 + 5 * math.sin(i), 2),
            )
            for i in range(35)
            if i not in [14, 15, 16]
        ],
    )
    case(
        "g06-many-categories",
        "generate",
        "ko",
        "data.csv는 24개 실증 현장의 연간 전력 사용량입니다. 보고서 한 페이지에 넣을 비교 그림을 만들어 주세요. 현장 이름은 한국어 원문 전체를 보여 주고, 입력 순서와 값을 그대로 유지해 주세요. 17 cm 폭 안에서 모든 현장을 알아볼 수 있게 하고 축 단위는 MWh로 적어 주세요. PNG와 PDF, 스크립트도 주세요.",
        ["실증 현장", "연간전력_MWh"],
        [
            (
                f"제{i:02d}권역 복합연구시설 저탄소운영 실증동",
                70 + (i * 37) % 110,
            )
            for i in range(1, 25)
        ],
    )
    case(
        "g07-slide-heatmap",
        "generate",
        "en",
        "Create a single 16:9 presentation figure with two panels from data.csv: on the left show all nine controllers' hourly efficiency curves with a readable legend using their full names; on the right show the same values as a controller-by-hour heatmap, annotate every cell to one decimal place and include a labelled colorbar. Use all six hours, keep values unchanged, and make text readable on a slide. Save PNG, PDF and the script.",
        ["controller", "hour", "efficiency_pct"],
        [
            (
                f"Controller {j}: predictive horizon {j * 2} h",
                i * 4,
                round(70 + j + 4 * math.sin(i + j), 1),
            )
            for j in range(1, 10)
            for i in range(6)
        ],
    )
    case(
        "g08-slide-grouped-bars",
        "generate",
        "ko",
        "발표 슬라이드의 제목 아래에 넣을 그림을 data.csv로 만들어 주세요. 여섯 개 건물 유형마다 세 가지 제어 방식의 절감률을 나란히 비교하는 막대그래프이고, 막대마다 값을 적어 주세요. 강의실 뒤에서도 읽혀야 합니다. PNG와 PDF, 실행 가능한 스크립트를 남겨 주세요.",
        ["건물 유형", "제어 방식", "절감률_pct"],
        [
            (b, c, round(6 + 2.5 * i + 1.7 * j + ((i * 3 + j) % 4) * 0.6, 1))
            for i, b in enumerate(
                ["사무동", "강의동", "실험동", "도서관", "기숙사", "체육관"]
            )
            for j, c in enumerate(["규칙 기반", "모델 예측", "강화 학습"])
        ],
    )
    case(
        "g09-slide-two-charts",
        "generate",
        "en",
        "I need one figure for a 16:9 slide that already has a title: two charts side by side from data.csv. Left: weekly load for the four sites as lines. Right: each site's mean load as bars, in the same site colours. Put the units on the axes and keep the text large enough for a slide. Save PNG, PDF and the script.",
        ["week", "site", "load_MWh"],
        [
            (w, s, round(40 + 6 * k + 8 * math.sin(w / 2 + k), 1))
            for k, s in enumerate(
                ["Harbour campus", "Hill campus", "North annex", "Data hall"]
            )
            for w in range(1, 13)
        ],
    )
    case(
        "g10-twelve-series",
        "generate",
        "en",
        "For a technical report, plot all twelve sensors in data.csv against time in one 14 cm wide figure. A reader must be able to tell which line is which sensor by its full name, and the names must not cover the lines. Keep every value. Save PNG, PDF and a runnable script.",
        ["time_min", "sensor", "temperature_C"],
        [
            (
                t * 5,
                f"Zone {z:02d} supply air temperature",
                round(18 + 0.35 * z + 1.5 * math.sin(t / 4 + z / 2), 2),
            )
            for z in range(1, 13)
            for t in range(25)
        ],
    )
    edits = [
        (
            "e01-ylabel-only",
            "ko",
            "논문용 plot.py에서 왼쪽 y축 문구 'Response (mV)'만 'Sensor response (mV)'로 바꿔 주세요. 데이터, 오른쪽 패널, 글자 크기, 색, 범례, 그림 크기와 배치는 모두 그대로 두세요. 수정본 스크립트와 PNG, PDF를 원본과 별도로 남겨 주세요.",
        ),
        (
            "e02-line-color-only",
            "en",
            "In this report's plot.py, change only the colour of the Model line in the left panel to #C44E52; its legend entry should show the new colour too. Keep everything else unchanged: the Measured line, the right panel, data, text, sizes and layout. Leave the original and save the revision as a new script, PNG and PDF.",
        ),
        (
            "e03-width-only",
            "ko",
            "보고서 그림 plot.py의 전체 폭만 14 cm에서 17 cm로 바꿔 주세요. 높이는 7 cm 그대로이고 데이터, 축 범위, 문구, 글자 크기, 선과 색, 범례 및 명시된 배치 인자는 모두 유지해 주세요. 원본을 보존하고 수정본 스크립트, PNG와 PDF를 따로 저장해 주세요.",
        ),
    ]
    base = '''"""Existing two-panel report figure; edit only the requested target."""

import csv

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("report")
with open("data.csv") as stream:
    rows = list(csv.DictReader(stream))
x = [float(r["time_s"]) for r in rows]
y = [float(r["measured_mV"]) for r in rows]
z = [float(r["model_mV"]) for r in rows]
fig, (left, right) = plt.subplots(
    1, 2, figsize=dm.figsize("14cm", "7cm"), gridspec_kw={"wspace": 0.5}
)
left.plot(x, y, label="Measured")
left.plot(x, z, label="Model")
left.set(xlabel="Time (s)", ylabel="Response (mV)", title="Response")
dm.place_legend(left)
right.plot(x, [a - b for a, b in zip(y, z, strict=True)])
right.set(xlabel="Time (s)", ylabel="Residual (mV)", title="Residual")
dm.simple_layout(fig)
dm.save_formats(fig, "out/base", formats=("png", "pdf"))
'''
    for name, lang, request in edits:
        folder = case(
            name,
            "edit",
            lang,
            request,
            ["time_s", "measured_mV", "model_mV"],
            [
                (
                    i,
                    round(math.sin(i / 3) + 2, 3),
                    round(0.9 * math.sin(i / 3) + 2, 3),
                )
                for i in range(15)
            ],
        )
        (folder / "plot.py").write_text(base)
    folder = case(
        "e04-paper-to-slide",
        "edit",
        "ko",
        "plot.py는 보고서용 그림입니다. 같은 그림을 16:9 발표 슬라이드 한 장을 가득 채우는 그림으로 바꿔 주세요. 데이터, 두 패널의 구성, 계열 이름과 색은 그대로 두세요. 원본을 보존하고 수정본 스크립트, PNG와 PDF를 따로 저장해 주세요.",
        ["time_s", "measured_mV", "model_mV"],
        [
            (
                i,
                round(math.sin(i / 3) + 2, 3),
                round(0.9 * math.sin(i / 3) + 2, 3),
            )
            for i in range(15)
        ],
    )
    (folder / "plot.py").write_text(base)
    folder = case(
        "e05-add-series",
        "edit",
        "en",
        "data.csv has a third column, baseline_mV, that plot.py does not draw. Add it to the left panel as a grey dashed line named Baseline, with a legend entry. Change nothing else: the other lines, the right panel, text, sizes and layout stay as they are. Leave the original and save the revision as a new script, PNG and PDF.",
        ["time_s", "measured_mV", "model_mV", "baseline_mV"],
        [
            (
                i,
                round(math.sin(i / 3) + 2, 3),
                round(0.9 * math.sin(i / 3) + 2, 3),
                round(2 + i / 40, 3),
            )
            for i in range(15)
        ],
    )
    (folder / "plot.py").write_text(base)
    round3()
    round4()
    round5()


def wobble(i, k=0):
    """A repeatable stand-in for noise in [-1, 1]; no random state."""
    return math.sin(12.9898 * (i + 1) + 78.233 * (k + 1)) * math.cos(
        4.1414 * (i + 1) * (k + 2)
    )


REPAIR_HEAD = '''"""A colleague's figure for the report."""

import csv

import matplotlib.pyplot as plt

import dartwork_mpl as dm

'''

# Each base runs and saves, and carries one kind of defect the validator
# reports as a WARNING. No repaired version is kept in this repository.
REPAIR = {
    "r01-legend-on-data": REPAIR_HEAD
    + """dm.style.use("report")
with open("data.csv") as stream:
    rows = list(csv.DictReader(stream))
names = list(dict.fromkeys(r["control"] for r in rows))
fig, ax = plt.subplots(figsize=dm.figsize("12cm", "7cm"))
for name in names:
    part = [r for r in rows if r["control"] == name]
    ax.plot(
        [float(r["week"]) for r in part],
        [float(r["load_MWh"]) for r in part],
        label=name,
    )
ax.set(xlabel="Week", ylabel="Load (MWh)")
ax.legend(loc="center")
dm.simple_layout(fig)
dm.save_formats(fig, "out/base", formats=("png", "pdf"))
""",
    "r02-turned-ticks": REPAIR_HEAD
    + """dm.style.use("report-kr")
with open("data.csv") as stream:
    rows = list(csv.DictReader(stream))
fig, ax = plt.subplots(figsize=dm.figsize("10cm", "6cm"))
ax.bar([r["건물"] for r in rows], [float(r["연간전력_MWh"]) for r in rows])
ax.set(xlabel="건물", ylabel="연간 전력 사용량 (MWh)")
dm.simple_layout(fig)
plt.setp(ax.get_xticklabels(), rotation=15)
dm.save_formats(fig, "out/base", formats=("png", "pdf"))
""",
    "r03-value-labels": REPAIR_HEAD
    + """dm.style.use("report")
with open("data.csv") as stream:
    rows = list(csv.DictReader(stream))
x = [float(r["time_h"]) for r in rows]
measured = [float(r["measured_C"]) for r in rows]
model = [float(r["model_C"]) for r in rows]
fig, ax = plt.subplots(figsize=dm.figsize("12cm", "7cm"))
ax.plot(x, measured, marker="o", label="Measured")
ax.plot(x, model, marker="s", label="Model")
for i in range(0, len(x), 2):
    ax.text(
        x[i],
        measured[i],
        f"{measured[i]:.2f}",
        fontsize=4,
        ha="center",
        va="center",
    )
ax.set(xlabel="Time (h)", ylabel="Temperature (°C)")
dm.place_legend(ax)
dm.simple_layout(fig)
dm.save_formats(fig, "out/base", formats=("png", "pdf"))
""",
    "r04-panel-gaps": REPAIR_HEAD
    + """dm.style.use("report-kr")
with open("data.csv") as stream:
    rows = list(csv.DictReader(stream))
zones = list(dict.fromkeys(r["구역"] for r in rows))
fig, axs = plt.subplots(
    2,
    2,
    figsize=dm.figsize("14cm", "9cm"),
    gridspec_kw={"hspace": 0.05, "wspace": 0.05},
)
for ax, zone in zip(axs.flat, zones, strict=True):
    part = [r for r in rows if r["구역"] == zone]
    ax.plot(
        [float(r["경과시간_s"]) for r in part],
        [float(r["응답_mV"]) for r in part],
    )
    ax.set(xlabel="경과 시간 (s)", ylabel="응답 (mV)", title=zone)
dm.simple_layout(fig)
dm.save_formats(fig, "out/base", formats=("png", "pdf"))
""",
}


def round3():
    """Axes the first two rounds never touched, and four figures to repair."""
    case(
        "g11-scatter-fit",
        "generate",
        "en",
        "For a journal paper, plot cooling power against outdoor temperature from data.csv as a scatter, with the two buildings told apart. Add a least-squares line for each building and write each line's slope and R² on the figure where they do not cover the points. Single column, 9 cm wide. Save PNG, PDF and a runnable script.",
        ["outdoor_temp_C", "cooling_power_kW", "building"],
        [
            (
                round(18 + 0.45 * i + 1.5 * wobble(i, k), 1),
                round(
                    (12 + 9 * k)
                    + (2.1 + 0.9 * k) * (0.45 * i + 1.5 * wobble(i, k))
                    + (5 + 3 * k) * wobble(i, k + 5),
                    1,
                ),
                b,
            )
            for k, b in enumerate(["Library", "Laboratory"])
            for i in range(40)
        ],
    )
    case(
        "g12-distributions",
        "generate",
        "ko",
        "보고서에 넣을 그림입니다. data.csv에는 세 가지 제어 방식의 일별 에너지 절감률이 60일씩 있습니다. 왼쪽에는 세 방식의 히스토그램을 한 축에 겹쳐 그리고, 오른쪽에는 같은 세 방식을 바이올린과 그 안의 상자그림으로 비교해 주세요. 두 패널에서 방식별 색은 같게 하고 폭은 17 cm입니다. PNG와 PDF, 실행 가능한 스크립트를 남겨 주세요.",
        ["제어 방식", "일차", "절감률_pct"],
        [
            (
                c,
                d + 1,
                round(
                    8
                    + 3.5 * k
                    + (2.2 + 0.8 * k)
                    * (wobble(d, k) + wobble(d, k + 3) + wobble(d, k + 7)),
                    2,
                ),
            )
            for k, c in enumerate(["규칙 기반", "모델 예측", "강화 학습"])
            for d in range(60)
        ],
    )
    case(
        "g13-error-bars",
        "generate",
        "en",
        "For a report, compare the three heat pumps in data.csv: mean COP against outdoor temperature, one line per heat pump, with error bars of plus and minus one standard deviation. Where the pumps are close, their error bars must still be told apart. 14 cm wide. Save PNG, PDF and a runnable script.",
        ["heat_pump", "outdoor_temp_C", "cop_mean", "cop_sd", "n_tests"],
        [
            (
                p,
                t,
                round(
                    2.6 + 0.12 * k + 0.045 * (t + 15) + 0.05 * wobble(j, k), 2
                ),
                round(0.16 + 0.05 * abs(wobble(j, k + 2)) + 0.03 * k, 2),
                6 + (j * 3 + k) % 5,
            )
            for k, p in enumerate(
                ["Air-source A", "Air-source B", "Ground-source"]
            )
            for j, t in enumerate(range(-15, 20, 5))
        ],
    )
    case(
        "g14-stacked-share",
        "generate",
        "ko",
        "data.csv는 2017년부터 2024년까지의 에너지원별 발전량(TWh)입니다. 보고서용으로 왼쪽에는 연도별 발전량 누적 막대를, 오른쪽에는 같은 자료를 연도별 비율(합계 100%)로 바꾼 누적 막대를 그려 주세요. 비율 그림에는 구간마다 % 값을 적고, 에너지원의 순서와 색은 두 패널에서 같게 해 주세요. 폭은 17 cm입니다. PNG와 PDF, 스크립트를 남겨 주세요.",
        ["연도", "에너지원", "발전량_TWh"],
        [
            (
                2017 + y,
                s,
                round(
                    [230 - 11 * y, 120 + 4 * y, 150 + 3 * y, 30 + 9 * y, 9 - y][
                        k
                    ]
                    + 4 * wobble(y, k),
                    1,
                ),
            )
            for y in range(8)
            for k, s in enumerate(
                ["석탄", "가스", "원자력", "재생에너지", "기타"]
            )
        ],
    )
    case(
        "g15-log-axes",
        "generate",
        "en",
        "For a paper, plot particle number concentration against particle diameter for the four samples in data.csv. Both quantities span several orders of magnitude, so use logarithmic axes. Draw the limit of 1000 particles per cm³ as a horizontal line with its name next to it. 12 cm wide. Save PNG, PDF and a runnable script.",
        ["diameter_nm", "sample", "concentration_per_cm3"],
        [
            (
                round(10 ** (1 + 0.25 * i), 1),
                s,
                round(
                    10
                    ** (
                        5.4
                        - 0.3 * k
                        - (0.34 + 0.03 * k) * i
                        + 0.12 * wobble(i, k)
                    ),
                    2,
                ),
            )
            for k, s in enumerate(
                ["Roadside", "Urban background", "Indoor office", "Clean room"]
            )
            for i in range(13)
        ],
    )
    notes = {
        7: "냉동기 1호기 기동",
        9: "냉동기 2호기 추가 기동",
        14: "피크 부하 제어 시작",
        31: "정전 후 복구",
        38: "축열조 방열 전환",
        40: "수요 반응 지시 수신",
        55: "외기 냉방 전환",
        63: "야간 설정 온도 적용",
    }
    case(
        "g16-annotated-events",
        "generate",
        "ko",
        "data.csv는 사흘간의 시간별 전력 부하이고, 일부 행의 '비고' 열에 그 시각에 있었던 일이 적혀 있습니다. 운영 보고서용으로 부하 곡선을 그리고, 비고가 있는 여덟 시점을 화살표와 함께 그 문구 그대로 표시해 주세요. 문구가 곡선이나 다른 문구를 가리면 안 됩니다. 폭은 17 cm입니다. PNG와 PDF, 실행 가능한 스크립트를 남겨 주세요.",
        ["시각", "부하_kW", "비고"],
        [
            (
                f"2026-06-{15 + h // 24:02d} {h % 24:02d}:00",
                round(
                    420
                    + 180 * max(0.0, math.sin((h % 24 - 6) / 24 * 2 * math.pi))
                    + 25 * wobble(h),
                    1,
                ),
                notes.get(h, ""),
            )
            for h in range(72)
        ],
    )
    # A logger export as it arrives: blank readings, two days missing, two
    # dates logged twice, one reading a hundred times its neighbours, and a
    # block of rows out of order. The request says nothing about any of it.
    days = [
        (date(2026, 3, 1) + timedelta(days=i), round(31 + 4 * wobble(i), 2))
        for i in range(45)
        if i not in (22, 23)
    ]
    export = []
    for i, (day, value) in enumerate(days):
        text = "" if i in (5, 6, 30) else f"{value}"
        if i == 17:
            text = "3120.4"
        export.append((day.isoformat(), text))
        if i in (11, 34):
            export.append((day.isoformat(), f"{round(value + 1.7, 2)}"))
    export = export[:25] + export[32:] + export[25:32]
    case(
        "g17-raw-export",
        "generate",
        "en",
        "For the facility report, plot the daily energy use in data.csv against date, 14 cm wide. The file is a raw export from the logger. Save PNG, PDF and a runnable script.",
        ["date", "energy_kWh"],
        export,
    )
    case(
        "g18-wide-magnitudes",
        "generate",
        "ko",
        "data.csv는 여덟 개 시·군의 인구입니다. 보고서용 막대그래프로 그리고 막대마다 값을 적어 주세요. 축 눈금은 만 단위로 읽히게 해 주세요. 가장 작은 군도 이름과 값을 알아볼 수 있어야 합니다. 폭은 14 cm입니다. PNG와 PDF, 실행 가능한 스크립트를 남겨 주세요.",
        ["시군", "인구_명"],
        list(
            zip(
                [
                    "한빛특별시",
                    "새별광역시",
                    "가람시",
                    "누리시",
                    "다온시",
                    "마루군",
                    "소담군",
                    "아라군",
                ],
                [9411000, 3293000, 1452000, 652000, 213000, 48700, 21300, 8900],
                strict=True,
            )
        ),
    )
    ask_en = "plot.py is a colleague's figure for our report. Validate it and fix what is wrong with it. The data and what the figure shows stay the same{keep}. Leave the original and save the revision as a new script, PNG and PDF."
    ask_ko = "plot.py는 동료가 만든 보고서 그림입니다. 그림을 검증해서 문제가 있으면 고쳐 주세요. 데이터와 그림이 보여 주는 내용은 그대로 두세요{keep}. 원본을 보존하고 수정본 스크립트, PNG와 PDF를 따로 저장해 주세요."
    repairs = [
        (
            "r01-legend-on-data",
            "en",
            ask_en.format(keep=""),
            ["week", "control", "load_MWh"],
            [
                (w, c, round(40 + 6 * k + 8 * math.sin(w / 4 + k), 1))
                for k, c in enumerate(
                    [
                        "Rule-based control",
                        "Model predictive control",
                        "Reinforcement learning",
                    ]
                )
                for w in range(30)
            ],
        ),
        (
            "r02-turned-ticks",
            "ko",
            ask_ko.format(keep=""),
            ["건물", "연간전력_MWh"],
            list(
                zip(
                    [
                        "서울 본관",
                        "부산 연구동",
                        "대전 실험동",
                        "광주 도서관",
                        "울산 기숙사",
                        "춘천 체육관",
                        "제주 연수원",
                        "인천 물류동",
                        "수원 강의동",
                        "청주 전산동",
                    ],
                    [182, 141, 236, 97, 158, 74, 66, 203, 129, 251],
                    strict=True,
                )
            ),
        ),
        (
            "r03-value-labels",
            "en",
            ask_en.format(
                keep=", and the Measured line keeps its value labels"
            ),
            ["time_h", "measured_C", "model_C"],
            [
                (
                    i,
                    round(20 + 5 * math.sin(i / 3), 2),
                    round(21 + 5 * math.sin(i / 3 + 0.4), 2),
                )
                for i in range(30)
            ],
        ),
        (
            "r04-panel-gaps",
            "ko",
            ask_ko.format(
                keep=". 네 패널과 패널마다의 제목, 축 이름도 유지합니다"
            ),
            ["구역", "경과시간_s", "응답_mV"],
            [
                (f"{z}구역", i, round(2000 + 1000 * math.sin(i / 3 + z), 1))
                for z in range(1, 5)
                for i in range(30)
            ],
        ),
    ]
    for name, lang, request, header, rows in repairs:
        folder = case(name, "repair", lang, request, header, rows)
        (folder / "plot.py").write_text(REPAIR[name])


def round4():
    """One figure changed several times in one conversation."""
    case(
        "s01-line-to-slide",
        "series",
        "en",
        "Plot monthly electricity use for the three buildings in data.csv as lines, for a report. Save PNG, PDF and a runnable script.",
        ["month", "Office_MWh", "Laboratory_MWh", "Library_MWh"],
        [
            (
                f"2025-{m + 1:02d}",
                round(
                    118
                    + 22 * math.cos((m - 7) / 12 * 2 * math.pi)
                    + 4 * wobble(m, 0),
                    1,
                ),
                round(
                    112
                    + 18 * math.cos((m - 6.5) / 12 * 2 * math.pi)
                    + 4 * wobble(m, 1),
                    1,
                ),
                round(
                    74
                    + 12 * math.cos((m - 0.5) / 12 * 2 * math.pi)
                    + 3 * wobble(m, 2),
                    1,
                ),
            )
            for m in range(12)
        ],
        [
            "Name the y axis 'Electricity use (MWh)' and take the axis down to zero.",
            "Write each building's value at its highest month next to that point.",
            "I am putting this on a slide now. Make it a slide figure.",
        ],
    )
    case(
        "s02-bars-refine",
        "series",
        "ko",
        "data.csv의 지역별 태양광 설치용량을 막대그래프로 그려 주세요. 보고서에 넣을 그림입니다. PNG와 PDF, 실행 가능한 스크립트를 남겨 주세요.",
        ["지역", "설치용량_MW"],
        # Deliberately not in order of size: the second turn asks for that.
        list(
            zip(
                [
                    "경기",
                    "강원",
                    "충북",
                    "충남",
                    "전북",
                    "전남",
                    "경북",
                    "경남",
                    "제주",
                    "인천",
                ],
                [
                    151.2,
                    164.9,
                    139.7,
                    301.4,
                    388.1,
                    412.6,
                    296.8,
                    187.3,
                    82.4,
                    37.5,
                ],
                strict=True,
            )
        ),
        [
            "용량이 큰 지역부터 차례로 놓아 주세요.",
            "막대마다 값을 적어 주세요.",
            "상위 세 지역만 눈에 띄게 해 주세요.",
        ],
    )
    case(
        "s03-split-and-undo",
        "series",
        "en",
        "Plot measured and model supply temperature against time from data.csv, for a report. Save PNG, PDF and a runnable script.",
        ["time_h", "measured_C", "model_C"],
        [
            (
                i / 2,
                round(42 + 6 * math.sin(i / 7) + 0.6 * wobble(i, 0), 2),
                round(
                    42.4 + 5.4 * math.sin(i / 7 - 0.15) + 0.2 * wobble(i, 1), 2
                ),
            )
            for i in range(96)
        ],
        [
            "Split it into two panels: the two series on top and model minus measured below.",
            "Draw a dashed line at zero in the lower panel and shade the hours where the difference is above 1 °C.",
            "Take the shading out again. Keep the zero line.",
        ],
    )


def day(h, start=6.0):
    """A daytime hump in [0, 1]: zero at night, one in mid-afternoon."""
    return max(0.0, math.sin((h - start) / 24 * 2 * math.pi))


GRID_HEAD = '''"""Existing four-panel report figure; edit only the requested target."""

import csv

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("report")
with open("data.csv") as stream:
    rows = list(csv.DictReader(stream))
'''

# Clean bases: each runs, saves and carries no validator WARNING.
EDIT5 = {
    "e06-panel-gap": GRID_HEAD
    + """zones = list(dict.fromkeys(r["zone"] for r in rows))
fig, axs = plt.subplots(2, 2, figsize=dm.figsize_for(nrows=2, ncols=2))
for ax, zone in zip(axs.flat, zones, strict=True):
    part = [r for r in rows if r["zone"] == zone]
    hours = [float(r["hour"]) for r in part]
    ax.plot(hours, [float(r["supply_temp_C"]) for r in part], label="Supply")
    ax.plot(hours, [float(r["return_temp_C"]) for r in part], label="Return")
    ax.set(xlabel="Hour of day", ylabel="Temperature (°C)", title=zone)
dm.label_axes(axs)
dm.figure_legend(fig)
dm.simple_layout(fig)
dm.save_formats(fig, "out/base", formats=("png", "pdf"))
""",
    "e07-add-panel-letters": GRID_HEAD
    + """seasons = list(dict.fromkeys(r["season"] for r in rows))
fig, axs = plt.subplots(
    2, 2, figsize=dm.figsize_for(nrows=2, ncols=2), sharex=True, sharey=True
)
for ax, season in zip(axs.flat, seasons, strict=True):
    part = [r for r in rows if r["season"] == season]
    hours = [float(r["hour"]) for r in part]
    ax.plot(hours, [float(r["office_kW"]) for r in part], label="Office")
    ax.plot(
        hours, [float(r["laboratory_kW"]) for r in part], label="Laboratory"
    )
    ax.set_title(season)
for ax in axs[:, 0]:
    ax.set_ylabel("Electric load (kW)")
for ax in axs[-1]:
    ax.set_xlabel("Hour of day")
dm.figure_legend(fig)
dm.simple_layout(fig)
dm.save_formats(fig, "out/base", formats=("png", "pdf"))
""",
}


def round5():
    """Stacked panels, grids, panel letters, long axis names and panel gaps."""
    halves = [i / 2 for i in range(48)]
    case(
        "g19-stacked-two",
        "generate",
        "en",
        "For a report, show one day of the chilled-water plant from data.csv in two panels, one above the other, on a shared time axis: supply and return temperature on top, cooling load below. Mark the panels (a) and (b). Save PNG, PDF and a runnable script.",
        ["hour", "supply_temp_C", "return_temp_C", "cooling_load_kW"],
        [
            (
                h,
                round(6.6 + 0.5 * day(h) + 0.12 * wobble(i, 0), 2),
                round(10.2 + 2.6 * day(h) + 0.2 * wobble(i, 1), 2),
                round(360 + 540 * day(h) + 28 * wobble(i, 2), 1),
            )
            for i, h in enumerate(halves)
        ],
    )
    case(
        "g20-stacked-three-kr",
        "generate",
        "ko",
        "보고서에 넣을 그림입니다. data.csv의 하루치 측정값을 위아래 세 단으로 나눠 그려 주세요. 위에서부터 실내 이산화탄소 농도, 외기 도입 풍량, 공조기 소비 전력이고 시간축은 함께 씁니다. 그림의 글자는 한국어로 하고 축 이름에는 단위를 붙여 주세요. 패널마다 (a), (b), (c)를 달아 주세요. PNG와 PDF, 실행 가능한 스크립트를 남겨 주세요.",
        [
            "시각_h",
            "실내 이산화탄소 농도_ppm",
            "외기 도입 풍량_m3_h",
            "공조기 소비 전력_kW",
        ],
        [
            (
                h,
                round(430 + 520 * day(h, 7) + 22 * wobble(i, 3), 0),
                round(1800 + 5400 * day(h, 6.5) + 160 * wobble(i, 4), 0),
                round(3.4 + 13.5 * day(h, 6.5) + 0.5 * wobble(i, 5), 2),
            )
            for i, h in enumerate(halves)
        ],
    )
    case(
        "g21-grid-long-names",
        "generate",
        "en",
        "For a journal paper, make a figure from data.csv with one panel per air-handling unit, in two rows of three. Each panel plots supply air volumetric flow rate against duct static pressure setpoint. Every panel carries both axis names with their units, the unit's name as its title and a panel letter, (a) to (f). Save PNG, PDF and a runnable script.",
        [
            "unit",
            "duct_static_pressure_setpoint_Pa",
            "supply_air_volumetric_flow_rate_m3_h",
        ],
        [
            (
                u,
                p,
                round(
                    (3100 + 650 * k) * math.sqrt(p / 100)
                    + 90 * wobble(j, k + 6),
                    0,
                ),
            )
            for k, u in enumerate(
                [
                    "AHU-1 East wing",
                    "AHU-2 West wing",
                    "AHU-3 Laboratory",
                    "AHU-4 Auditorium",
                    "AHU-5 Library",
                    "AHU-6 Atrium",
                ]
            )
            for j, p in enumerate(range(100, 425, 25))
        ],
    )
    case(
        "g22-two-groups",
        "generate",
        "ko",
        "기관 보고서용 그림입니다. data.csv에는 두 건물(본관, 연구동)의 여름철 냉방 부하와 겨울철 난방 부하가 시간별로 있습니다. 그림을 왼쪽·오른쪽 두 묶음으로 나누고 묶음마다 건물 이름을 제목으로 달아 주세요. 각 묶음 안에는 위에 냉방 부하, 아래에 난방 부하를 시각에 대해 그립니다. 두 건물이 따로 읽히도록 묶음 사이는 묶음 안의 패널 사이보다 넓게 띄우고, 네 패널에 (a)부터 (d)까지 달아 주세요. 그림의 글자는 한국어로 써 주세요. PNG와 PDF, 스크립트를 남겨 주세요.",
        ["건물", "시각_h", "여름철 냉방 부하_kW", "겨울철 난방 부하_kW"],
        [
            (
                b,
                h,
                round((210 + 160 * k) * day(h, 7) + 38 + 9 * wobble(h, k), 1),
                round(
                    (150 + 120 * k) * (1 - 0.75 * day(h, 8))
                    + 20
                    + 8 * wobble(h, k + 2),
                    1,
                ),
            )
            for k, b in enumerate(["본관", "연구동"])
            for h in range(24)
        ],
    )
    folder = case(
        "e06-panel-gap",
        "edit",
        "ko",
        "plot.py는 보고서용 네 패널 그림입니다. 패널들이 서로 너무 붙어 보입니다. 이웃한 패널의 내용(눈금 글자, 축 이름, 제목) 사이가 가로세로 모두 8 mm 떨어지게 해 주세요. 그 밖의 것(데이터, 문구, 글자 크기, 색, 그림 크기, 패널 글자, 범례)은 그대로 두세요. 원본을 보존하고 수정본 스크립트, PNG와 PDF를 따로 저장해 주세요.",
        ["zone", "hour", "supply_temp_C", "return_temp_C"],
        [
            (
                z,
                h,
                round(13.5 + 0.4 * k + 1.1 * day(h) + 0.15 * wobble(h, k), 2),
                round(
                    21.5 + 0.6 * k + 2.4 * day(h) + 0.2 * wobble(h, k + 4), 2
                ),
            )
            for k, z in enumerate(
                ["North office", "South office", "Core laboratory", "Atrium"]
            )
            for h in range(24)
        ],
    )
    (folder / "plot.py").write_text(EDIT5["e06-panel-gap"])
    folder = case(
        "e07-add-panel-letters",
        "edit",
        "en",
        "plot.py is a four-panel figure for our report. Add panel letters, (a) to (d), in bold. Change nothing else: data, text, sizes, colours, the legend and the figure size stay as they are. Leave the original and save the revision as a new script, PNG and PDF.",
        ["season", "hour", "office_kW", "laboratory_kW"],
        [
            (
                s,
                h,
                round(60 + (150 + 45 * k) * day(h, 6.5) + 6 * wobble(h, k), 1),
                round(
                    150 + (70 + 25 * k) * day(h, 5) + 8 * wobble(h, k + 4), 1
                ),
            )
            for k, s in enumerate(["Spring", "Summer", "Autumn", "Winter"])
            for h in range(24)
        ],
    )
    (folder / "plot.py").write_text(EDIT5["e07-add-panel-letters"])
    case(
        "s04-grid-to-slide",
        "series",
        "en",
        "Plot the hourly indoor temperature of the four zones in data.csv, one panel per zone, for a report. Save PNG, PDF and a runnable script.",
        ["hour", "zone", "indoor_temp_C"],
        [
            (
                h,
                z,
                round(
                    21.2
                    + 0.5 * k
                    + (2.2 + 0.4 * k) * day(h, 8)
                    + 0.2 * wobble(h, k + 8),
                    2,
                ),
            )
            for k, z in enumerate(
                ["Open office", "Meeting rooms", "Server room", "Lobby"]
            )
            for h in range(24)
        ],
        [
            "Add panel letters, a to d.",
            "The panels sit too close together. Leave about a centimetre of clear space between neighbouring panels.",
            "This goes on a slide now. Make it a slide figure.",
        ],
    )
    case(
        "s05-stack-grow",
        "series",
        "ko",
        "data.csv의 하루치 실내 온도와 상대 습도를 위아래 두 패널로 그려 주세요. 보고서에 넣을 그림이고 그림의 글자는 한국어로 해 주세요. PNG와 PDF, 실행 가능한 스크립트를 남겨 주세요.",
        ["시각_h", "실내 온도_C", "상대 습도_pct", "이산화탄소 농도_ppm"],
        [
            (
                h,
                round(22.4 + 2.1 * day(h, 8) + 0.15 * wobble(i, 9), 2),
                round(52 - 11 * day(h, 8) + 1.2 * wobble(i, 10), 1),
                round(440 + 470 * day(h, 7) + 20 * wobble(i, 11), 0),
            )
            for i, h in enumerate(halves)
        ],
        [
            "아래에 이산화탄소 농도 패널을 하나 더 추가해 주세요.",
            "패널마다 (a), (b), (c)를 달아 주세요.",
            "y축 이름을 위에서부터 '거주 구역 평균 실내 온도 (°C)', '거주 구역 평균 상대 습도 (%)', '거주 구역 평균 이산화탄소 농도 (ppm)'로 바꿔 주세요.",
        ],
    )


if __name__ == "__main__":
    main()
