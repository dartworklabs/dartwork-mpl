Formatting Utilities
====================

Functions for formatting axis tick labels, rotating labels, and displaying
numeric values in common formats.

Overview
--------

The formatting module provides utilities for presenting numeric data in
readable, publication-quality formats. These functions handle common
formatting needs like percentages, thousands separators, currency, and
scientific notation.

Key Features
------------

- **Automatic formatting**: Convert raw numbers to human-readable formats
- **Locale support**: Format numbers according to regional conventions
- **Scientific notation**: SI prefixes and engineering notation
- **Currency-style formats**: Symbols, thousands separators, millions, billions with appropriate suffixes
- **Label rotation**: Rotate tick labels for better readability

API Reference
-------------

Numeric Formatting
^^^^^^^^^^^^^^^^^^

.. autofunction:: dartwork_mpl.format_axis_percent

.. autofunction:: dartwork_mpl.format_axis_thousands

.. autofunction:: dartwork_mpl.format_axis_millions

.. autofunction:: dartwork_mpl.format_axis_billions

.. autofunction:: dartwork_mpl.format_axis_currency

.. autofunction:: dartwork_mpl.format_axis_si

Label Management
^^^^^^^^^^^^^^^^

.. autofunction:: dartwork_mpl.rotate_tick_labels

Examples
--------

Percentage Formatting
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import dartwork_mpl as dm
   import matplotlib.pyplot as plt
   import numpy as np

   fig, ax = plt.subplots()

   # Data as fractions (0 to 1)
   x = np.arange(5)
   y = np.array([0.15, 0.32, 0.45, 0.28, 0.52])

   ax.bar(x, y)

   # Format y-axis as percentages
   dm.format_axis_percent(ax, axis='y')  # Shows: 15%, 32%, 45%, etc.

   # With custom decimal places
   dm.format_axis_percent(ax, axis='y', decimals=1)  # Shows: 15.0%, 32.0%, etc.

Large Number Formatting
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Thousands separator
   fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(12, 4))

   # Sample counts in thousands
   sample_counts = np.array([125000, 248000, 392000, 516000, 687000])
   ax1.plot(sample_counts)
   dm.format_axis_thousands(ax1, axis='y')  # Shows: 125,000, 248,000, etc.
   ax1.set_title('Sample Count')

   # Dataset size in millions of rows
   dataset_rows = np.array([1.2e6, 2.5e6, 4.8e6, 8.3e6])
   ax2.bar(range(len(dataset_rows)), dataset_rows)
   dm.format_axis_millions(ax2, axis='y')  # Shows: 1.2M, 2.5M, etc.
   ax2.set_title('Dataset Rows')

   # World population in billions
   population = np.array([1.8e9, 2.1e9, 2.4e9, 2.7e9])
   ax3.plot(population)
   dm.format_axis_billions(ax3, axis='y', suffix='B')  # Shows: 1.8B, 2.1B, etc.
   ax3.set_title('Population')

Currency Formatting
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

   prices = np.array([19.99, 34.50, 78.25, 124.00, 259.99])

   # US Dollars
   ax1.bar(range(len(prices)), prices)
   dm.format_axis_currency(ax1, axis='y', symbol='$', position='prefix')
   ax1.set_title('Product Prices (USD)')

   # Euros (suffix style)
   ax2.bar(range(len(prices)), prices * 0.85)  # Convert to EUR
   dm.format_axis_currency(ax2, axis='y', symbol='€', position='suffix')
   ax2.set_title('Product Prices (EUR)')

Scientific Notation with SI Prefixes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

   # Frequency data
   freq = np.logspace(3, 9, 50)  # 1kHz to 1GHz
   response = -20 * np.log10(freq / 1e6)

   ax1.semilogx(freq, response)
   dm.format_axis_si(ax1, axis='x')  # Shows: 1k, 10k, 100k, 1M, 10M, 100M, 1G
   ax1.set_xlabel('Frequency (Hz)')
   ax1.set_ylabel('Response (dB)')

   # Power measurements
   power = np.array([1e-9, 1e-6, 1e-3, 1, 1e3])  # nW to kW
   ax2.bar(range(len(power)), power)
   ax2.set_yscale('log')
   dm.format_axis_si(ax2, axis='y')  # Shows: 1n, 1μ, 1m, 1, 1k
   ax2.set_ylabel('Power (W)')

Rotating Labels
^^^^^^^^^^^^^^^

.. code-block:: python

   fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(12, 4))

   # Long category names
   categories = ['Category A with Long Name',
                 'Category B with Even Longer Name',
                 'Category C Short',
                 'Category D Medium Length',
                 'Category E Final']

   values = np.random.randn(len(categories))

   # Default rotation (45 degrees)
   ax1.bar(range(len(categories)), values)
   ax1.set_xticks(range(len(categories)))
   ax1.set_xticklabels(categories)
   dm.rotate_tick_labels(ax1, axis='x')
   ax1.set_title('45° Rotation (Default)')

   # Vertical rotation
   ax2.bar(range(len(categories)), values)
   ax2.set_xticks(range(len(categories)))
   ax2.set_xticklabels(categories)
   dm.rotate_tick_labels(ax2, axis='x', rotation=90, ha='right')
   ax2.set_title('90° Rotation')

   # Angled with custom alignment
   ax3.bar(range(len(categories)), values)
   ax3.set_xticks(range(len(categories)))
   ax3.set_xticklabels(categories)
   dm.rotate_tick_labels(ax3, axis='x', rotation=30, ha='right')
   ax3.set_title('30° Rotation')

   dm.simple_layout(fig)

Complete Example: Multi-format Dashboard
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A 2×2 dashboard that exercises all four numeric formatters side by
side (thousands, percent, currency, billions). The metrics are a
neutral mix — sample count, efficiency, unit price, cumulative energy
— so the page reads as a *formatter* showcase rather than a finance
template.

.. code-block:: python

   import dartwork_mpl as dm
   import matplotlib.pyplot as plt
   import numpy as np

   # Create sample measurement data
   periods = ['T1', 'T2', 'T3', 'T4', 'T5']
   samples = np.array([125_000, 248_000, 392_000, 516_000, 687_000])
   efficiency = np.array([0.62, 0.68, 0.73, 0.71, 0.76])
   unit_price = np.array([45.20, 52.30, 61.50, 58.40, 67.80])
   cumulative_energy = np.array([1.8e9, 3.9e9, 6.3e9, 9.0e9, 11.8e9])

   # Create dashboard
   fig = plt.figure(figsize=(12, 8))
   gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

   # Sample count (top-left) — thousands formatter
   ax1 = fig.add_subplot(gs[0, 0])
   ax1.bar(periods, samples, color='oc.green5')
   dm.format_axis_thousands(ax1, axis='y')
   ax1.set_title('Sample Count')
   ax1.set_ylabel('Samples')
   dm.rotate_tick_labels(ax1, axis='x', rotation=45)

   # Efficiency (top-right) — percent formatter
   ax2 = fig.add_subplot(gs[0, 1])
   ax2.plot(periods, efficiency, 'o-', color='oc.blue5', lw=2)
   dm.format_axis_percent(ax2, axis='y')
   ax2.set_title('Efficiency')
   ax2.set_ylabel('Ratio')
   ax2.set_ylim(0, 1.0)
   dm.rotate_tick_labels(ax2, axis='x', rotation=45)

   # Unit price (bottom-left) — currency formatter
   ax3 = fig.add_subplot(gs[1, 0])
   ax3.plot(periods, unit_price, 's-', color='oc.purple5', lw=2)
   dm.format_axis_currency(ax3, axis='y', symbol='$')
   ax3.set_title('Unit Price')
   ax3.set_ylabel('Price per unit')
   dm.rotate_tick_labels(ax3, axis='x', rotation=45)

   # Cumulative energy (bottom-right) — billions formatter
   ax4 = fig.add_subplot(gs[1, 1])
   ax4.bar(periods, cumulative_energy, color='oc.orange5')
   dm.format_axis_billions(ax4, axis='y', suffix='B')
   ax4.set_title('Cumulative Energy')
   ax4.set_ylabel('Joules')
   dm.rotate_tick_labels(ax4, axis='x', rotation=45)

   # Style all axes — inline minimal-axes + light y-grid recipe
   for ax in [ax1, ax2, ax3, ax4]:
       ax.spines["top"].set_visible(False)
       ax.spines["right"].set_visible(False)
       ax.grid(True, axis='y', alpha=0.2, color='oc.gray3', linewidth=0.5)
       ax.set_axisbelow(True)

   dm.simple_layout(fig)
   plt.show()

Custom Number Formats
^^^^^^^^^^^^^^^^^^^^^

For formats not covered by the built-in functions, you can create custom formatters:

.. code-block:: python

   from matplotlib.ticker import FuncFormatter

   # Custom formatter for displaying as fractions
   def format_as_fraction(x, pos):
       from fractions import Fraction
       return str(Fraction(x).limit_denominator(10))

   ax.yaxis.set_major_formatter(FuncFormatter(format_as_fraction))

   # Custom formatter for log scale with superscript
   def format_log_scale(x, pos):
       exponent = int(np.log10(x))
       return f'$10^{{{exponent}}}$'

   ax.xaxis.set_major_formatter(FuncFormatter(format_log_scale))

International Number Formats
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # European style (comma as decimal separator)
   def format_european(x, pos):
       return f'{x:.2f}'.replace('.', ',')

   # Indian numbering system (lakhs and crores)
   def format_indian(x, pos):
       if x >= 1e7:
           return f'{x/1e7:.1f}Cr'  # Crores
       elif x >= 1e5:
           return f'{x/1e5:.1f}L'   # Lakhs
       else:
           return f'{x:.0f}'

Best Practices
--------------

1. **Choose appropriate units**: Use millions/billions for large numbers to avoid too many digits
2. **Decimal places**: Use 0-1 decimals for general audiences, 2-3 for technical or currency values
3. **Consistency**: Use the same format across related charts
4. **Label rotation**: Use 45° for moderate-length labels, 90° for very long labels
5. **SI prefixes**: Prefer for scientific/engineering contexts
6. **Currency**: Place symbol according to local convention (prefix for USD, suffix for EUR)

Common Patterns
---------------

Currency & Percent Reports
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Typical mix: large counts, a growth ratio, and a unit price
   dm.format_axis_millions(ax_count, axis='y', suffix='M')
   dm.format_axis_percent(ax_growth, axis='y', decimals=1)
   dm.format_axis_currency(ax_price, axis='y', symbol='$')

Scientific Papers
^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Scientific notation with SI units
   dm.format_axis_si(ax_frequency, axis='x')  # Hz
   dm.format_axis_si(ax_power, axis='y')      # W
   dm.format_axis_percent(ax_efficiency, axis='y', decimals=2)

Web Analytics
^^^^^^^^^^^^^

.. code-block:: python

   # User metrics
   dm.format_axis_thousands(ax_users, axis='y', sep=',')
   dm.format_axis_percent(ax_conversion, axis='y', decimals=1)
   dm.format_axis_millions(ax_pageviews, axis='y', suffix='M')

Integration with Themes
-----------------------

Formatting utilities work seamlessly with dartwork-mpl themes:

.. code-block:: python

   # Apply theme first
   dm.style.use('scientific')
   fig, ax = plt.subplots(figsize=dm.figsize('13cm', 'standard'))

   # Plot data
   ax.plot(data)

   # Format based on data type
   if data_type == 'currency':
       dm.format_axis_currency(ax, axis='y', symbol='$')
   elif data_type == 'percentage':
       dm.format_axis_percent(ax, axis='y')
   elif data_type == 'scientific':
       dm.format_axis_si(ax, axis='y')

See Also
--------

- :doc:`helpers` - AI helper utilities including formatting
- :doc:`../usage_guide/quickstart` - Getting started guide