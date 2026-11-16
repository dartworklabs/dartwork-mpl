"""지역별 연매출 막대: 만·억 눈금을 손으로 쓴 formatter, 모든 막대에 값, 제목이 축을 되풀이한다."""

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

import dartwork_mpl as dm

dm.style.use("report-kr")

sales = {
    "서울": 1250000000,
    "인천": 705000000,
    "부산": 820000000,
    "대구": 610000000,
    "대전": 455000000,
    "광주": 380000000,
}
regions = sorted(sales, key=sales.get, reverse=True)
values = [sales[r] for r in regions]


def fmt(v, _=None):
    if v >= 1e8:
        return f"{v / 1e8:g}억"
    if v >= 1e4:
        return f"{v / 1e4:g}만"
    return f"{v:g}"


fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(regions, values, color="#4C72B0")
ax.yaxis.set_major_formatter(FuncFormatter(fmt))
for b, v in zip(bars, values, strict=True):
    ax.text(
        b.get_x() + b.get_width() / 2,
        v,
        fmt(v),
        ha="center",
        va="bottom",
        fontsize=10,
    )
ax.set_ylabel("연매출 (원)")
ax.set_title("지역별 연매출")

dm.simple_layout(fig)
dm.save_formats(fig, "output/korean_report_units", formats=("png",))
