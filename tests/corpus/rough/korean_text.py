"""월별 전력 사용량: 한글 그림에 영문 preset(report)을 써서 한글이 대체 글꼴로 나오고, 눈금은 만·억 대신 40M으로 찍힌다."""

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("report")

months = ["1월", "2월", "3월", "4월", "5월", "6월"]
usage = [41200000, 39800000, 35600000, 30100000, 28900000, 33400000]

fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
ax.bar(months, usage)
ax.set_title("월별 전력 사용량")
ax.set_ylabel("사용량 (kWh)")

dm.simple_layout(fig)
dm.save_formats(fig, "output/korean_text", formats=("png",))
