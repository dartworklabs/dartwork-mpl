"""
Likert Survey Chart
===================

Visualize 5-point Likert scale survey results using
``dm.plot_diverging_bar``. This ready-made function handles the
diverging layout, value labels, and legend automatically.
"""

import matplotlib.pyplot as plt
import numpy as np

import dartwork_mpl as dm

dm.style.use("presentation")

# %%
# Employee satisfaction survey
# -----------------------------
# Using ``dm.plot_diverging_bar()`` with custom labels and data.
labels = [
    "Work-life balance",
    "Career growth",
    "Compensation",
    "Team culture",
    "Management",
    "Learning opportunities",
]

# Negative = dissatisfied, Positive = satisfied
neg_values = np.array([-12, -25, -30, -8, -18, -15])
pos_values = np.array([72, 55, 45, 82, 60, 68])

fig, ax = dm.plot_diverging_bar(
    labels=labels,
    neg_values=neg_values,
    pos_values=pos_values,
    add_total=True,
    title="Employee Satisfaction Survey 2025",
    neg_label="Dissatisfied",
    pos_label="Satisfied",
    colors={"neg": "oc.red5", "pos": "oc.teal5"},
)

plt.show()

# %%
# Product feedback scores
# ------------------------
# A simpler example with default styling.
products = ["Product A", "Product B", "Product C", "Product D"]

neg = np.array([-15, -22, -8, -35])
pos = np.array([65, 48, 80, 42])

fig, ax = dm.plot_diverging_bar(
    labels=products,
    neg_values=neg,
    pos_values=pos,
    add_total=False,
    title="Product Satisfaction Scores",
    neg_label="Negative feedback",
    pos_label="Positive feedback",
)

plt.show()
