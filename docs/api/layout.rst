Layout Utilities
================

Utilities for tightening layouts without juggling ``plt.subplots_adjust``.
``simple_layout`` optimizes margins with L-BFGS-B so axes fit inside a bounding
box; ``make_offset`` nudges text/legends in point units; ``label_axes`` adds
standardized panel labels; ``arrow_axis`` draws annotated bidirectional arrows;
and ``set_decimal``/``get_bounding_box`` provide quick helpers when formatting axes.

``simple_layout(fig, gs=None, margins=(0.15, 0.05, 0.05, 0.05), bbox=(0, 1, 0, 1), verbose=False, gtol=1e-2, bound_margin=0.2, use_all_axes=True, importance_weights=(1, 1, 1, 1))``
   - Parameters:
     - ``fig``: target figure (required).
     - ``gs``: GridSpec to adjust; ``None`` picks the first axes' GridSpec.
     - ``margins``: padding in inches ``(left, right, bottom, top)``.
     - ``bbox``: figure-relative target box; shrink to reserve space for headers.
     - ``importance_weights``: emphasize specific sides during optimization.
     - ``bound_margin``: how far each side may move away from ``bbox``.
     - ``gtol``: optimizer tolerance.
     - ``verbose``: toggle optimizer logging.
     - ``use_all_axes``: ``True`` considers every axes; ``False`` limits to ``gs``.
   - Returns:
     - ``scipy.optimize.OptimizeResult``; layout changes are applied in-place.

``make_offset(x, y, fig)``
   - Parameters:
     - ``x``: horizontal offset in points.
     - ``y``: vertical offset in points.
     - ``fig``: figure providing DPI scaling.
   - Returns:
     - ``matplotlib.transforms.ScaledTranslation`` to add to an axes transform.

``set_decimal(ax, xn=None, yn=None)``
   - Parameters:
     - ``ax``: axes object to update.
     - ``xn``: decimal places for x ticks; ``None`` leaves them unchanged.
     - ``yn``: decimal places for y ticks; ``None`` leaves them unchanged.
   - Returns:
     - ``None``; tick labels are replaced.

``get_bounding_box(boxes)``
   - Parameters:
     - ``boxes``: iterable with ``p0``, ``width``, ``height`` (e.g., from ``get_tightbbox``).
   - Returns:
     - tuple ``(min_x, min_y, width, height)`` covering them all.

``label_axes(axes, labels=None, fontsize=10, fontweight='bold', x='auto', y=1.05, **kwargs)``
   - Parameters:
     - ``axes``: list or ndarray of Axes objects.
     - ``labels``: custom labels; ``None`` uses lowercase alphabet (a, b, c, ...).
     - ``fontsize``: font size in points.  Default 10.
     - ``fontweight``: font weight.  Default ``'bold'``.
     - ``x``: x position in axes coordinates; ``'auto'`` uses ``-0.18`` for axes with
       a y-label, ``-0.02`` otherwise.
     - ``y``: y position in axes coordinates.  Default ``1.05``.
     - ``**kwargs``: forwarded to ``ax.text()``.

   - Returns:
     - list of ``Text`` objects.

``arrow_axis(ax, direction, label, *, offset=-0.05, low='Low', high='High', fontsize=None, fontsize_label=None, pad=-0.005, weight='normal', color='black', arrow_kw=None)``
   - Parameters:
     - ``ax``: target axes.
     - ``direction``: ``'x'`` (horizontal) or ``'y'`` (vertical).
     - ``label``: center axis label text.
     - ``offset``: axes-fraction distance from spine (negative = outside).
     - ``low``, ``high``: endpoint text labels.
     - ``fontsize``: size for low/high labels; ``None`` → ``fs(-1)``.
     - ``fontsize_label``: size for center label; ``None`` → ``fs(0)``.
     - ``pad``: axes-fraction gap between text and arrowheads.
     - ``weight``, ``color``: font weight and color for all elements.
     - ``arrow_kw``: override ``arrowprops`` dict.
   - Returns:
     - ``None``; arrows and labels drawn in-place.

Example
-------

.. code-block:: python

   import matplotlib.pyplot as plt
   import numpy as np
   import dartwork_mpl as dm

   fig, axes = plt.subplots(1, 3, figsize=(dm.DW, dm.DW * 0.35))
   for ax in axes:
       ax.plot(np.linspace(0, 1, 40), np.random.rand(40), color='oc.blue6')

   # Panel labels
   dm.label_axes(axes)  # adds a, b, c

   # Layout optimization
   dm.simple_layout(fig, margins=(0.08, 0.05, 0.1, 0.08))

   # Decimal formatting
   dm.set_decimal(axes[0], xn=2, yn=1)

   # Arrow annotations
   dm.arrow_axis(axes[1], 'x', 'Installation cost')
   dm.arrow_axis(axes[2], 'y', 'Information richness')

.. autofunction:: dartwork_mpl.simple_layout
.. autofunction:: dartwork_mpl.make_offset
.. autofunction:: dartwork_mpl.label_axes
.. autofunction:: dartwork_mpl.arrow_axis
.. autofunction:: dartwork_mpl.util.get_bounding_box
.. autofunction:: dartwork_mpl.util.set_decimal
