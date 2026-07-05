Formatting Utilities
====================

Functions for formatting axis tick labels, rotating labels, and displaying
numeric values in common formats.

Overview
--------

The formatting module covers the four large-number formats that
matplotlib ships without a built-in answer — **millions**, **billions**,
**currency**, and **SI prefixes** — plus a label-rotation helper. For
plain percentages and thousands separators, lean on matplotlib's
``ticker.PercentFormatter`` and ``ticker.StrMethodFormatter`` directly.

API Reference
-------------

Numeric Formatting
^^^^^^^^^^^^^^^^^^

.. note::

   ``format_axis_percent`` and ``format_axis_thousands`` were removed in
   the 0.4 release. Use matplotlib's ``ticker.PercentFormatter`` and
   ``ticker.StrMethodFormatter`` directly — see the migration table in
   :doc:`../migration` for the per-call replacement. The two examples
   below show the canonical patterns.

.. autofunction:: dartwork_mpl.format_axis_millions

.. autofunction:: dartwork_mpl.format_axis_billions

.. autofunction:: dartwork_mpl.format_axis_currency

.. autofunction:: dartwork_mpl.format_axis_si

Label Management
^^^^^^^^^^^^^^^^

.. autofunction:: dartwork_mpl.rotate_tick_labels

Examples
--------

Percentages (matplotlib direct)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import dartwork_mpl as dm
   import matplotlib.pyplot as plt
   from matplotlib.ticker import PercentFormatter
   import numpy as np

   dm.style.use("scientific")
   fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))

   # Data as fractions (0 to 1)
   x = np.arange(5)
   y = np.array([0.15, 0.32, 0.45, 0.28, 0.52])
   ax.bar(x, y, color="dc.teal2")

   # Display as integer percentages — multiply 0–1 input by 100
   ax.yaxis.set_major_formatter(PercentFormatter(xmax=1.0, decimals=0))

   # Or one decimal place
   # ax.yaxis.set_major_formatter(PercentFormatter(xmax=1.0, decimals=1))

   dm.simple_layout(fig)

Thousands separator (matplotlib direct)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from matplotlib.ticker import StrMethodFormatter

   sample_counts = np.array([125000, 248000, 392000, 516000, 687000])
   fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
   ax.plot(sample_counts, color="dc.green2")

   # 125,000 / 248,000 / …
   ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
   dm.simple_layout(fig)

Millions and billions
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   fig, (ax1, ax2) = plt.subplots(
       1, 2, figsize=dm.figsize("17cm", "cinema")
   )

   # Dataset size in millions of rows
   dataset_rows = np.array([1.2e6, 2.5e6, 4.8e6, 8.3e6])
   ax1.bar(range(len(dataset_rows)), dataset_rows, color="dc.teal2")
   dm.format_axis_millions(ax1, axis="y")  # 1.2M, 2.5M, …
   ax1.set_title("Dataset rows")

   # World population in billions
   population = np.array([1.8e9, 2.1e9, 2.4e9, 2.7e9])
   ax2.plot(population, "o-", color="dc.violet2", lw=dm.lw(0))
   dm.format_axis_billions(ax2, axis="y", suffix="B")  # 1.8B, 2.1B, …
   ax2.set_title("Population")

   dm.simple_layout(fig)

Currency
^^^^^^^^

.. code-block:: python

   fig, (ax1, ax2) = plt.subplots(
       1, 2, figsize=dm.figsize("17cm", "cinema")
   )

   prices = np.array([19.99, 34.50, 78.25, 124.00, 259.99])

   # US dollars — prefix
   ax1.bar(range(len(prices)), prices, color="dc.green2")
   dm.format_axis_currency(ax1, axis="y", symbol="$", position="prefix")
   ax1.set_title("Product prices (USD)")

   # Euros — suffix
   ax2.bar(range(len(prices)), prices * 0.85, color="dc.teal2")
   dm.format_axis_currency(ax2, axis="y", symbol="€", position="suffix")
   ax2.set_title("Product prices (EUR)")

   dm.simple_layout(fig)

SI prefixes
^^^^^^^^^^^

.. code-block:: python

   fig, (ax1, ax2) = plt.subplots(
       1, 2, figsize=dm.figsize("17cm", "cinema")
   )

   # Frequency response — 1 kHz to 1 GHz
   freq = np.logspace(3, 9, 50)
   response = -20 * np.log10(freq / 1e6)
   ax1.semilogx(freq, response, color="dc.red2")
   dm.format_axis_si(ax1, axis="x")  # 1k, 10k, 100k, 1M, …
   ax1.set_xlabel("Frequency (Hz)")
   ax1.set_ylabel("Response (dB)")

   # Power measurements — nW to kW
   power = np.array([1e-9, 1e-6, 1e-3, 1, 1e3])
   ax2.bar(range(len(power)), power, color="dc.orange2")
   ax2.set_yscale("log")
   dm.format_axis_si(ax2, axis="y")  # 1n, 1μ, 1m, 1, 1k
   ax2.set_ylabel("Power (W)")

   dm.simple_layout(fig)

Rotating labels
^^^^^^^^^^^^^^^

.. code-block:: python

   fig, (ax1, ax2, ax3) = plt.subplots(
       1, 3, figsize=dm.figsize("17cm", "cinema")
   )

   categories = [
       "Category A with Long Name",
       "Category B with Even Longer Name",
       "Category C Short",
       "Category D Medium Length",
       "Category E Final",
   ]
   values = np.random.randn(len(categories))

   for ax, deg, ha in [(ax1, 45, "right"), (ax2, 90, "right"), (ax3, 30, "right")]:
       ax.bar(range(len(categories)), values, color="dc.indigo2")
       ax.set_xticks(range(len(categories)))
       ax.set_xticklabels(categories)
       dm.rotate_tick_labels(ax, axis="x", rotation=deg, ha=ha)
       ax.set_title(f"{deg}° rotation")

   dm.simple_layout(fig)

Complete example: multi-format dashboard
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A 2×2 dashboard that exercises all four numeric formatters side-by-side
(thousands via matplotlib, currency, millions, billions). The metrics
are a neutral mix — sample count, unit price, dataset rows, cumulative
energy — so the page reads as a *formatter* showcase rather than a
finance template.

.. code-block:: python

   import dartwork_mpl as dm
   import matplotlib.pyplot as plt
   from matplotlib.ticker import StrMethodFormatter
   import numpy as np

   dm.style.use("report")

   periods = ["T1", "T2", "T3", "T4", "T5"]
   samples = np.array([125_000, 248_000, 392_000, 516_000, 687_000])
   unit_price = np.array([45.20, 52.30, 61.50, 58.40, 67.80])
   dataset_rows = np.array([1.2e6, 3.4e6, 5.1e6, 7.8e6, 9.6e6])
   cumulative_energy = np.array([1.8e9, 3.9e9, 6.3e9, 9.0e9, 11.8e9])

   fig = plt.figure(figsize=dm.figsize("17cm", "wide"))
   gs = fig.add_gridspec(2, 2, hspace=0.45, wspace=0.30)

   ax1 = fig.add_subplot(gs[0, 0])
   ax1.bar(periods, samples, color="dc.green2")
   ax1.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
   ax1.set_title("Sample count")
   ax1.set_ylabel("Samples")

   ax2 = fig.add_subplot(gs[0, 1])
   ax2.plot(periods, unit_price, "o-", color="dc.teal2", lw=dm.lw(0))
   dm.format_axis_currency(ax2, axis="y", symbol="$")
   ax2.set_title("Unit price")

   ax3 = fig.add_subplot(gs[1, 0])
   ax3.bar(periods, dataset_rows, color="dc.teal2")
   dm.format_axis_millions(ax3, axis="y")
   ax3.set_title("Dataset rows")

   ax4 = fig.add_subplot(gs[1, 1])
   ax4.bar(periods, cumulative_energy, color="dc.orange2")
   dm.format_axis_billions(ax4, axis="y", suffix="B")
   ax4.set_title("Cumulative energy")
   ax4.set_ylabel("Joules")

   for ax in (ax1, ax2, ax3, ax4):
       ax.spines["top"].set_visible(False)
       ax.spines["right"].set_visible(False)
       ax.grid(True, axis="y", alpha=0.2, color="dc.indigo1", linewidth=dm.lw(0))
       ax.set_axisbelow(True)
       dm.rotate_tick_labels(ax, axis="x", rotation=45)

   dm.simple_layout(fig, gs=gs)

Custom formats via matplotlib
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For formats not covered by the helpers, lean on matplotlib's
``FuncFormatter`` directly:

.. code-block:: python

   from matplotlib.ticker import FuncFormatter

   # Fractions
   def _format_fraction(x, pos):
       from fractions import Fraction
       return str(Fraction(x).limit_denominator(10))

   ax.yaxis.set_major_formatter(FuncFormatter(_format_fraction))

   # Log-scale exponents
   def _format_log(x, pos):
       exponent = int(np.log10(x))
       return f"$10^{{{exponent}}}$"

   ax.xaxis.set_major_formatter(FuncFormatter(_format_log))

   # Indian numbering — lakhs and crores
   def _format_indian(x, pos):
       if x >= 1e7:
           return f"{x / 1e7:.1f}Cr"
       if x >= 1e5:
           return f"{x / 1e5:.1f}L"
       return f"{x:.0f}"

Best practices
--------------

1. **Pick the smallest unit that reads cleanly.** ``format_axis_millions``
   beats raw ``1,200,000`` on a tight axis.
2. **Decimal places.** 0–1 for general audiences, 2–3 for technical or
   currency values.
3. **Currency placement** follows local convention — prefix for USD,
   suffix for EUR.
4. **SI prefixes** belong in scientific / engineering contexts; mixing
   them with comma-grouped thousands looks inconsistent.

See also
--------

- :doc:`helpers` — AI helper utilities
- :doc:`../usage_guide/quickstart` — getting-started guide
