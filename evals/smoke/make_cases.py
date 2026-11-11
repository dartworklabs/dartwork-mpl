"""Recreate the small, synthetic smoke inputs without random state or downloads."""

import csv
import json
import math
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent / "cases"


def case(name, kind, lang, prompt, header, rows):
    folder = ROOT / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "case.json").write_text(
        json.dumps(
            {"id": name, "kind": kind, "lang": lang, "request": prompt},
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
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


if __name__ == "__main__":
    main()
