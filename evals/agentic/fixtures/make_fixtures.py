"""Regenerate the eval CSV fixtures (deterministic; provenance only).

The committed CSVs under ``data/`` are the frozen inputs. Case oracles in
``../cases/*.yaml`` were computed from them; if you regenerate, re-check
every oracle. Values are synthetic, not real statistics.

    uv run python evals/agentic/fixtures/make_fixtures.py
"""

from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent / "data"


def _write(name: str, header: list[str], rows: list[list[object]]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def _r(x: float, nd: int = 1) -> float:
    return round(float(x), nd)


def gdp_growth() -> None:
    data = {
        "Korea": [2.4, 3.2, 3.2, 2.8, 2.9, 3.2, 2.9, 2.2, -0.7, 4.3, 2.6, 1.4],
        "Japan": [1.4, 2.0, 0.3, 1.6, 0.8, 1.7, 0.6, -0.4, -4.1, 2.6, 1.0, 1.9],
        "United States": [
            2.3,
            2.1,
            2.5,
            2.9,
            1.8,
            2.5,
            3.0,
            2.5,
            -2.2,
            6.1,
            2.5,
            2.9,
        ],
        "Germany": [
            0.4,
            0.4,
            2.2,
            1.5,
            None,
            2.7,
            1.0,
            1.1,
            -3.8,
            3.2,
            1.8,
            -0.3,
        ],
        "France": [0.3, 0.6, 1.0, 1.1, 1.1, 2.3, 1.9, 1.8, -7.5, 6.4, 2.5, 0.9],
    }
    rows = []
    for i, year in enumerate(range(2012, 2024)):
        rows.append(
            [year] + ["" if v[i] is None else v[i] for v in data.values()]
        )
    _write("gdp_growth.csv", ["year", *data], rows)


def quarterly_sales() -> None:
    rev = {
        "North": [1250, 1340, 1415, 1580],
        "South": [980, 1045, 1120, 1210],
        "East": [1430, 1395, 1510, 1655],
        "West": [760, 845, 910, 1030],
    }
    rows = [
        [region, f"Q{q + 1}", f"{v[q]:,}"]
        for region, v in rev.items()
        for q in range(4)
    ]
    _write("quarterly_sales.csv", ["region", "quarter", "revenue"], rows)


def survey_scores() -> None:
    items = [
        ("Search", 82.4),
        ("Checkout", 76.1),
        ("Onboarding", 64.8),
        ("Notifications", 58.3),
        ("Dark mode", 71.9),
        ("Offline mode", None),
        ("Sharing", 69.5),
        ("Settings", 55.2),
        ("Help center", 61.7),
        ("Profile", 73.6),
        ("Payments", 79.0),
        ("Export", 48.9),
    ]
    rows = [
        [k, "" if v is None else v, 120 + 7 * i]
        for i, (k, v) in enumerate(items)
    ]
    _write("survey_scores.csv", ["feature", "score", "responses"], rows)


def plants() -> None:
    rng = np.random.RandomState(7)
    rows = []
    for sp, (mx, slope, icpt) in {
        "Alpine": (4.0, 0.45, 0.6),
        "Coastal": (5.5, 0.30, 1.4),
        "Desert": (7.0, 0.20, 0.9),
    }.items():
        for _ in range(30):
            length = mx + rng.normal(0, 0.6)
            width = icpt + slope * length + rng.normal(0, 0.15)
            rows.append([sp, _r(length, 2), _r(width, 2)])
    rows[33][2] = ""  # Coastal
    rows[71][2] = ""  # Desert
    _write("plants.csv", ["species", "leaf_length_cm", "leaf_width_cm"], rows)


def sensors() -> None:
    rng = np.random.RandomState(11)
    n = 150
    temp = rng.normal(22, 4, n)
    humidity = 80 - 1.6 * temp + rng.normal(0, 4, n)
    pressure = 1013 + rng.normal(0, 5, n)
    wind = 3 + 0.3 * (1013 - pressure) / 5 + rng.gamma(2, 1, n)
    pm25 = 40 - 3.5 * wind + 0.2 * humidity + rng.normal(0, 4, n)
    noise = 55 + 0.4 * temp + rng.normal(0, 3, n)
    cols = [temp, humidity, pressure, wind, pm25, noise]
    rows = [[_r(c[i], 2) for c in cols] for i in range(n)]
    _write(
        "sensors.csv",
        [
            "temperature",
            "humidity",
            "pressure",
            "wind_speed",
            "pm25",
            "noise_db",
        ],
        rows,
    )


def response_times() -> None:
    rng = np.random.RandomState(3)
    a = np.exp(rng.normal(np.log(220), 0.35, 200))
    b = np.exp(rng.normal(np.log(185), 0.30, 200))
    rows = [["A", _r(v, 1)] for v in a] + [["B", _r(v, 1)] for v in b]
    _write("response_times.csv", ["variant", "response_ms"], rows)


def exam_scores() -> None:
    rng = np.random.RandomState(5)
    rows = []
    for sec, (mu, sd) in {
        "A": (72, 9),
        "B": (68, 12),
        "C": (79, 7),
        "D": (64, 14),
    }.items():
        rows += [
            [sec, int(np.clip(round(rng.normal(mu, sd)), 0, 100))]
            for _ in range(40)
        ]
    rows[57][1] = ""  # one missing score in section B
    _write("exam_scores.csv", ["section", "score"], rows)


def energy_mix() -> None:
    rows = []
    for i, year in enumerate(range(2000, 2024)):
        coal = 520 - 9.0 * i
        gas = 210 + 4.0 * i
        nuclear = 150 + 1.5 * i - (0.08 * i * i)
        hydro = 60 + 0.5 * (i % 4)
        wind_solar = 2 + 0.55 * i * i
        rows.append(
            [year, *(_r(v, 1) for v in (coal, gas, nuclear, hydro, wind_solar))]
        )
    _write(
        "energy_mix.csv",
        ["year", "coal", "gas", "nuclear", "hydro", "wind_solar"],
        rows,
    )


def city_temps() -> None:
    base = {
        "Seoul": 12.5,
        "Busan": 15.0,
        "Daegu": 14.6,
        "Gwangju": 14.2,
        "Daejeon": 13.3,
        "Incheon": 12.4,
    }
    amp = {
        "Seoul": 14.5,
        "Busan": 10.5,
        "Daegu": 13.5,
        "Gwangju": 12.8,
        "Daejeon": 13.8,
        "Incheon": 13.5,
    }
    rng = np.random.RandomState(9)
    rows = []
    for city in base:
        for k in range(36):
            y, m = 2021 + k // 12, k % 12 + 1
            t = (
                base[city]
                - amp[city] * np.cos(2 * np.pi * (m - 1.3) / 12)
                + rng.normal(0, 0.6)
            )
            rows.append([f"{y}-{m:02d}-01", city, _r(t, 1)])
    _write("city_temps.csv", ["month", "city", "temp_c"], rows)


def kpi_monthly() -> None:
    rows = []
    for m in range(1, 13):
        revenue = 42.0 + 2.1 * m + (1.5 if m in (11, 12) else 0)
        users = 18000 + 950 * m - (600 if m == 8 else 0)
        churn = 4.8 - 0.12 * m + (0.6 if m == 8 else 0)
        nps = 31 + m + (-4 if m == 8 else 0)
        rows.append([f"2024-{m:02d}", _r(revenue, 1), users, _r(churn, 2), nps])
    _write(
        "kpi_monthly.csv",
        ["month", "revenue_musd", "active_users", "churn_pct", "nps"],
        rows,
    )


def climate_monthly() -> None:
    temp = [-2.4, 0.6, 5.8, 12.4, 17.8, 22.3, 25.1, 25.8, 21.2, 14.6, 7.2, 0.3]
    precip = [17, 26, 45, 72, 103, 134, 395, 349, 141, 48, 50, 22]
    months = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]
    _write(
        "climate_monthly.csv",
        ["month", "temp_c", "precip_mm"],
        [[m, t, p] for m, t, p in zip(months, temp, precip, strict=True)],
    )


def _bdays(start: date, end: date) -> list[date]:
    out, d = [], start
    while d <= end:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def stock_prices() -> None:
    rng = np.random.RandomState(21)
    days = _bdays(date(2024, 1, 2), date(2024, 6, 28))
    price, rows = 100.0, []
    for d in days:
        drift = -1.1 if date(2024, 3, 11) <= d <= date(2024, 3, 22) else 0.12
        price = max(20.0, price + drift + rng.normal(0, 1.2))
        rows.append(
            [d.isoformat(), _r(price, 2), int(rng.uniform(0.8, 1.6) * 1e6)]
        )
    rows[40][1] = ""  # one missing close
    _write("stock_prices.csv", ["date", "close", "volume"], rows)


def plant_output() -> None:
    rng = np.random.RandomState(13)
    rows = []
    for k in range(90):
        d = date(2024, 4, 1) + timedelta(days=k)
        out = 1200 + 3 * k + rng.normal(0, 40) - (250 if 50 <= k <= 54 else 0)
        defect = 1.8 + rng.normal(0, 0.25) + (1.5 if 50 <= k <= 54 else 0)
        rows.append([d.isoformat(), int(out), _r(defect, 2)])
    _write(
        "plant_output.csv", ["date", "output_units", "defect_rate_pct"], rows
    )


def korea_monthly_sales() -> None:
    sales = [
        1180,
        1095,
        1320,
        1405,
        1460,
        1390,
        1515,
        1600,
        1550,
        1680,
        1745,
        1910,
    ]
    profit = [96, 81, 118, 131, 140, 122, 150, 163, 149, 171, 182, 205]
    rows = [
        [f"2024-{m:02d}", f"{s:,}", p]
        for m, s, p in zip(range(1, 13), sales, profit, strict=True)
    ]
    _write(
        "korea_monthly_sales.csv",
        ["월", "매출액(억원)", "영업이익(억원)"],
        rows,
    )


def sido_population() -> None:
    pop = [
        ("서울특별시", 9386),
        ("부산광역시", 3293),
        ("대구광역시", 2374),
        ("인천광역시", 3000),
        ("광주광역시", 1419),
        ("대전광역시", 1442),
        ("울산광역시", 1103),
        ("세종특별자치시", 386),
        ("경기도", 13631),
        ("강원특별자치도", 1527),
        ("충청북도", 1591),
        ("충청남도", 2130),
        ("전북특별자치도", 1754),
        ("전라남도", 1804),
        ("경상북도", 2554),
        ("경상남도", 3251),
        ("제주특별자치도", 675),
    ]
    _write(
        "sido_population.csv",
        ["시도", "인구(천명)"],
        [[k, f"{v:,}"] for k, v in pop],
    )


def dose_response() -> None:
    doses = [0.1, 0.3, 1, 3, 10, 30, 100]
    mean = [4.1, 7.9, 18.6, 41.2, 68.4, 84.9, 90.3]
    sem = [0.9, 1.2, 2.1, 3.4, 3.9, 2.8, 2.2]
    _write(
        "dose_response.csv",
        ["dose_uM", "response_pct", "sem"],
        [[d, m, s] for d, m, s in zip(doses, mean, sem, strict=True)],
    )


def web_traffic() -> None:
    rng = np.random.RandomState(17)
    rows = []
    for w in range(52):
        d = date(2024, 1, 1) + timedelta(weeks=w)
        sessions = int(
            24000
            + 180 * w
            + 3000 * np.sin(w / 52 * 2 * np.pi)
            + rng.normal(0, 900)
        )
        signups = int(sessions * (0.031 + rng.normal(0, 0.002)))
        rows.append([d.isoformat(), sessions, signups])
    rows[30][2] = ""  # one missing signup count
    _write("web_traffic.csv", ["week_start", "sessions", "signups"], rows)


def market_share() -> None:
    share = [
        ("Alpha", 31.5),
        ("Bravo", 22.8),
        ("Charlie", 17.4),
        ("Delta", 11.9),
        ("Echo", 9.1),
        ("Others", 7.3),
    ]
    _write(
        "market_share.csv", ["company", "share_pct"], [[k, v] for k, v in share]
    )


def visitors_daily() -> None:
    rng = np.random.RandomState(19)
    rows = []
    for k in range(60):
        d = date(2024, 1, 1) + timedelta(days=k)
        v = int(
            3200
            + 25 * k
            + (900 if d.weekday() >= 5 else 0)
            + rng.normal(0, 150)
        )
        rows.append([d.strftime("%Y.%m.%d"), "" if k == 23 else v])
    _write("visitors_daily.csv", ["날짜", "방문자수"], rows)


def user_growth() -> None:
    rows = []
    for m in range(24):
        y, mm = 2023 + m // 12, m % 12 + 1
        a = 120 * 1.32**m
        b = 900 * 1.12**m
        rows.append([f"{y}-{mm:02d}", int(a), int(b)])
    _write(
        "user_growth.csv", ["month", "app_alpha_users", "app_beta_users"], rows
    )


def country_stats() -> None:
    rows = [
        ("Korea", 51.7, 34.2),
        ("Japan", 124.5, 33.8),
        ("United States", 334.9, 80.4),
        ("Germany", 84.5, 52.7),
        ("France", 68.2, 46.3),
        ("India", 1428.6, 2.5),
        ("Brazil", 216.4, 10.0),
        ("Iceland", 0.39, 78.8),
        ("Nigeria", 223.8, 1.6),
        ("Vietnam", 98.9, 4.3),
        ("Norway", 5.5, 87.9),
        ("Chile", 19.6, 17.1),
    ]
    _write(
        "country_stats.csv",
        ["country", "population_m", "gdp_per_capita_kusd"],
        [list(r) for r in rows],
    )


if __name__ == "__main__":
    for fn in (
        gdp_growth,
        quarterly_sales,
        survey_scores,
        plants,
        sensors,
        response_times,
        exam_scores,
        energy_mix,
        city_temps,
        kpi_monthly,
        climate_monthly,
        stock_prices,
        plant_output,
        korea_monthly_sales,
        sido_population,
        dose_response,
        web_traffic,
        market_share,
        visitors_daily,
        user_growth,
        country_stats,
    ):
        fn()
    print("wrote", sorted(p.name for p in OUT.glob("*.csv")))
