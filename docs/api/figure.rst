Figure Creation
===============

Enhanced figure and subplot creation functions that integrate with
dartwork-mpl's style system and the 0.4 width / aspect API.

Overview
--------

The figure creation functions in dartwork-mpl provide drop-in
replacements for matplotlib's ``plt.figure()`` and ``plt.subplots()``
with additional features:

- **Free-form width**: ``width="13cm"`` / ``width=dm.cm(11.3)`` /
  ``width=dm.col1`` instead of fixed tokens.
- **Aspect tokens**: six named ratios (``square`` / ``portrait`` /
  ``standard`` / ``golden`` / ``wide`` / ``cinema``) plus arbitrary
  positive floats.
- **Style integration**: apply styles directly during figure creation.
- **GridSpec support**: built-in support for complex layouts with
  ratio control.
- **Consistent defaults**: sensible defaults for publication-quality
  figures.

Width and aspect (0.4)
----------------------

Pass ``width`` (any unit-suffixed string, ``Inches`` helper, or bare
number interpreted as cm) and ``aspect`` (named token or
height/width float) to control figure size:

.. code-block:: python

   import dartwork_mpl as dm

   # Single-column report figure with the default 3:4 aspect
   fig, ax = dm.subplots(width="9cm", aspect="standard")

   # Double-column figure, custom aspect
   fig, ax = dm.subplots(width=dm.col2, aspect=0.4)

   # With a style
   fig, ax = dm.subplots(width="13cm", style='scientific')

The legacy ``figsize=`` and ``dpi=`` arguments were **removed in
0.4.0** — passing either to :func:`dartwork_mpl.subplots` or
:func:`dartwork_mpl.figure` now raises :class:`TypeError`. See
:doc:`../migration` for the full mapping from the 0.3 width tokens.

API Reference
-------------

.. autofunction:: dartwork_mpl.subplots

.. autofunction:: dartwork_mpl.figure

Examples
--------

Basic Usage
^^^^^^^^^^^

.. code-block:: python

   import dartwork_mpl as dm
   import numpy as np

   # Create figure with scientific style
   fig, ax = dm.subplots(style='scientific')

   # Plot data
   x = np.linspace(0, 10, 100)
   ax.plot(x, np.sin(x))
   ax.set_xlabel('x')
   ax.set_ylabel('sin(x)')

   dm.simple_layout(fig)
   plt.show()

Multiple Subplots
^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Create 2x2 grid with shared axes
   fig, axes = dm.subplots(2, 2,
                           style='report',
                           sharex=True,
                           sharey=True)

   for i, ax in enumerate(axes.flat):
       ax.plot(np.random.randn(100))
       ax.set_title(f'Panel {i+1}')

   dm.simple_layout(fig)

Complex Layouts with Ratios
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Create subplots with custom width and height ratios
   fig, axes = dm.subplots(2, 3,
                           style='presentation',
                           width_ratios=[1, 2, 1],
                           height_ratios=[2, 1])

   # axes is a 2x3 array
   # First row has twice the height of second row
   # Middle column has twice the width of side columns

Stacking Multiple Styles
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Apply multiple styles in sequence
   fig, ax = dm.subplots(style=['font-libertine', 'theme-dark', 'preset-slides'])

   # Equivalent to:
   # dm.style.use(['font-libertine', 'theme-dark', 'preset-slides'])
   # fig, ax = plt.subplots()

Style-Specific Figure Sizes
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Each style preset ships with a sensible default width, but the
0.4 API lets you set width / aspect explicitly per call:

.. code-block:: python

   # Scientific papers — single column
   fig, ax = dm.subplots(width=dm.col1, style='scientific')

   # Reports
   fig, ax = dm.subplots(width="13cm", style='report')

   # Presentations — wider aspect
   fig, ax = dm.subplots(width=dm.col2, aspect="wide", style='presentation')

Integration with Layout Functions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The figure creation functions work seamlessly with dartwork-mpl's layout utilities:

.. code-block:: python

   fig, axes = dm.subplots(2, 2, style='scientific')

   for ax in axes.flat:
       ax.plot(np.random.randn(100))
       ax.set_xlabel('Time')
       ax.set_ylabel('Value')

   # Apply consistent layout
   dm.simple_layout(fig)

   # Or use auto-layout for content-aware margins
   dm.auto_layout(fig)

GridSpec Integration
^^^^^^^^^^^^^^^^^^^^

For advanced layouts, GridSpec parameters are fully supported:

.. code-block:: python

   fig, axes = dm.subplots(3, 3,
                           style='report',
                           gridspec_kw={
                               'hspace': 0.3,
                               'wspace': 0.4,
                               'left': 0.1,
                               'right': 0.95
                           })

Figure-Only Creation
^^^^^^^^^^^^^^^^^^^^

Use ``dm.figure()`` when you need a figure without subplots:

.. code-block:: python

   # Create empty figure with style
   fig = dm.figure(style='scientific')

   # Add custom axes manually
   ax1 = fig.add_subplot(2, 1, 1)
   ax2 = fig.add_subplot(2, 1, 2)

   # Or use add_axes for precise control
   ax = fig.add_axes([0.1, 0.1, 0.8, 0.8])

Best Practices
--------------

1. **Always use style parameter** for consistency:

   .. code-block:: python

      # Good: style applied at creation
      fig, ax = dm.subplots(style='scientific')

      # Less ideal: style applied separately
      dm.style.use('scientific')
      fig, ax = plt.subplots()

2. **Pick width and aspect explicitly** so the figure size is
   reproducible across machines and CI runs:

   .. code-block:: python

      # Default: style's width with the standard 3:4 aspect
      fig, ax = dm.subplots(style='report')

      # Or set both
      fig, ax = dm.subplots(width="13cm", aspect=0.5, style='report')

3. **Use width/height ratios** instead of manual GridSpec for simple cases:

   .. code-block:: python

      # Simple and clear
      fig, axes = dm.subplots(1, 3, width_ratios=[1, 2, 1])

      # More complex, only when needed
      gs = fig.add_gridspec(1, 3, width_ratios=[1, 2, 1])
      axes = [fig.add_subplot(gs[0, i]) for i in range(3)]

Differences from Matplotlib
---------------------------

The main differences from matplotlib's figure creation functions:

1. **Style parameter**: apply styles directly during creation.
2. **Width / aspect API**: free-form ``width=`` plus ``aspect=``
   token / float instead of a raw ``figsize`` tuple.
3. **Enhanced defaults**: better default spacing and margins.
4. **Automatic imports**: no need to import ``matplotlib.pyplot``.

Migration from Matplotlib
^^^^^^^^^^^^^^^^^^^^^^^^^

Migrating from matplotlib is straightforward:

.. code-block:: python

   # Matplotlib approach
   import matplotlib.pyplot as plt

   plt.style.use('seaborn')
   fig, ax = plt.subplots(figsize=(8, 6), dpi=100)

   # dartwork-mpl approach
   import dartwork_mpl as dm

   fig, ax = dm.subplots(width="20cm", aspect=6/8, style='scientific')

See Also
--------

- :doc:`layout` - Layout utilities for optimal spacing
- :doc:`../usage_guide/quickstart` - Getting started guide
- :doc:`../philosophy/utilities_not_wrappers` - Design philosophy