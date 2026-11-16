"""Budget by department as vertical bars whose long department names have to share a 9 cm width."""

import matplotlib.pyplot as plt

import dartwork_mpl as dm

dm.style.use("report")

departments = [
    "Research and Development",
    "Sales and Marketing",
    "Customer Success",
    "Finance and Accounting",
    "Human Resources",
    "Information Technology",
]
budget = [4.2, 3.1, 1.4, 0.9, 0.7, 2.3]

fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
ax.bar(departments, budget)
ax.set_ylabel("Budget (USD m)")

dm.simple_layout(fig)
dm.save_formats(fig, "output/long_category_names", formats=("png",))
