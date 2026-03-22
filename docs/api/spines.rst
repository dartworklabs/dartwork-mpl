Spine and Grid Utilities
=========================

Functions for customizing plot spines (borders), grids, and axes appearance.

Overview
--------

The spine utilities provide fine-grained control over plot boundaries and grids,
enabling creation of minimalist, publication-quality figures. These functions
support various visualization styles from minimal Tufte-style plots to fully
framed scientific figures.

Key Concepts
------------

**Spines** are the lines that form the border of the plot area. In matplotlib,
there are four spines: 'top', 'bottom', 'left', and 'right'.

**Grids** are the lines that help readers estimate values. They can be major
or minor, and can appear on the x-axis, y-axis, or both.

API Reference
-------------

Spine Control
^^^^^^^^^^^^^

.. autofunction:: dartwork_mpl.hide_spines

.. autofunction:: dartwork_mpl.hide_all_spines

.. autofunction:: dartwork_mpl.show_only_spines

.. autofunction:: dartwork_mpl.style_spines

.. autofunction:: dartwork_mpl.add_frame

Grid Control
^^^^^^^^^^^^

.. autofunction:: dartwork_mpl.add_grid

.. autofunction:: dartwork_mpl.remove_grid

Convenience Functions
^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: dartwork_mpl.minimal_axes

Examples
--------

Creating Minimal Axes
^^^^^^^^^^^^^^^^^^^^^

The most common use case is creating clean, minimal axes:

.. code-block:: python

   import dartwork_mpl as dm
   import matplotlib.pyplot as plt
   import numpy as np

   fig, ax = plt.subplots(figsize=(6, 4))

   # Plot data
   x = np.linspace(0, 10, 100)
   ax.plot(x, np.sin(x), color='oc.blue5', lw=dm.lw(1))

   # Apply minimal style (shows only left and bottom spines)
   dm.minimal_axes(ax)

   ax.set_xlabel('Time (s)')
   ax.set_ylabel('Amplitude')

Custom Spine Visibility
^^^^^^^^^^^^^^^^^^^^^^^

Control which spines are visible:

.. code-block:: python

   # Hide specific spines
   dm.hide_spines(ax, ['top', 'right'])

   # Show only specific spines
   dm.show_only_spines(ax, ['left', 'bottom'])

   # Hide all spines for a floating plot
   dm.hide_all_spines(ax)

   # Add a complete frame
   dm.add_frame(ax, color='black', linewidth=1)

Styling Spines
^^^^^^^^^^^^^^

Customize spine appearance:

.. code-block:: python

   # Change color and width of all spines
   dm.style_spines(ax, color='gray', linewidth=0.5)

   # Style only specific spines
   dm.style_spines(ax, color='red', linewidth=2, which=['left', 'right'])

   # Create a thick frame
   dm.add_frame(ax, color='oc.blue8', linewidth=2)

Grid Customization
^^^^^^^^^^^^^^^^^^

Add and customize grids:

.. code-block:: python

   # Add basic grid
   dm.add_grid(ax)

   # Add only horizontal grid lines
   dm.add_grid(ax, axis='y')

   # Add subtle grid
   dm.add_grid(ax, alpha=0.2, linestyle='--', linewidth=0.5)

   # Add only major gridlines
   dm.add_grid(ax, which='major')

   # Add both major and minor gridlines
   dm.add_grid(ax, which='both')

   # Remove all grids
   dm.remove_grid(ax)

Complete Example: Scientific Plot
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import dartwork_mpl as dm
   import matplotlib.pyplot as plt
   import numpy as np

   # Create figure with scientific style
   fig, (ax1, ax2) = dm.subplots(1, 2, style='scientific', figsize=(8, 4))

   # Generate data
   x = np.linspace(0, 4*np.pi, 100)
   y1 = np.sin(x) + 0.1*np.random.randn(100)
   y2 = np.cos(x) + 0.1*np.random.randn(100)

   # Left plot: minimal style
   ax1.plot(x, y1, color='oc.blue5', lw=dm.lw(1))
   dm.minimal_axes(ax1)
   dm.add_grid(ax1, alpha=0.2, linestyle='-', linewidth=0.5)
   ax1.set_title('Minimal Style')
   ax1.set_xlabel('x')
   ax1.set_ylabel('sin(x)')

   # Right plot: framed style
   ax2.plot(x, y2, color='oc.red5', lw=dm.lw(1))
   dm.add_frame(ax2, color='black', linewidth=0.8)
   dm.add_grid(ax2, which='major', alpha=0.3)
   ax2.set_title('Framed Style')
   ax2.set_xlabel('x')
   ax2.set_ylabel('cos(x)')

   dm.simple_layout(fig)
   plt.show()

Tufte-Style Minimalism
^^^^^^^^^^^^^^^^^^^^^^^

Create Edward Tufte-inspired minimal plots:

.. code-block:: python

   fig, ax = plt.subplots(figsize=(6, 4))

   # Plot data
   x = np.arange(10)
   y = np.random.randn(10).cumsum()
   ax.plot(x, y, 'o-', color='black', markersize=4, lw=1)

   # Remove top and right spines
   dm.minimal_axes(ax)

   # Remove all ticks except min/max
   ax.set_xticks([x.min(), x.max()])
   ax.set_yticks([y.min(), y.max()])

   # No grid for maximum data-ink ratio
   dm.remove_grid(ax)

Publication Styles
^^^^^^^^^^^^^^^^^^

Different publication venues have different preferences:

.. code-block:: python

   # Nature/Science style: minimal with no top/right spines
   dm.hide_spines(ax, ['top', 'right'])
   dm.add_grid(ax, alpha=0.2, axis='y', linestyle='-')

   # IEEE style: full frame with grid
   dm.add_frame(ax, color='black', linewidth=0.5)
   dm.add_grid(ax, which='major', alpha=0.3, linestyle=':')

   # Economics journals: often prefer full frame, no grid
   dm.add_frame(ax, color='black', linewidth=1)
   dm.remove_grid(ax)

   # Web/presentation: minimal spines, subtle grid
   dm.minimal_axes(ax)
   dm.add_grid(ax, alpha=0.1, linestyle='-', color='gray')

Dark Theme Support
^^^^^^^^^^^^^^^^^^

Spine utilities work well with dark themes:

.. code-block:: python

   dm.style.use('theme-dark')
   fig, ax = dm.subplots()

   # Plot data
   ax.plot(np.random.randn(100).cumsum())

   # Light spines on dark background
   dm.style_spines(ax, color='#CCCCCC', linewidth=0.8)
   dm.add_grid(ax, alpha=0.2, color='white', linestyle=':')

Best Practices
--------------

1. **Consistency**: Use the same spine style throughout a document
2. **Minimalism**: Remove unnecessary spines to reduce visual clutter
3. **Grid subtlety**: Keep grids light (alpha=0.2-0.3) to avoid competing with data
4. **Frame usage**: Use frames sparingly, mainly for emphasis or journal requirements
5. **Color coordination**: Match spine colors to your overall color scheme

Common Patterns
---------------

Minimal Scientific Plot
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Standard pattern for scientific publications
   dm.minimal_axes(ax)  # Keep only left and bottom
   dm.add_grid(ax, alpha=0.2, axis='y')  # Subtle y-axis grid

Dashboard Panel
^^^^^^^^^^^^^^^

.. code-block:: python

   # For multi-panel dashboards
   dm.hide_all_spines(ax)  # Clean, borderless
   dm.add_grid(ax, alpha=0.1, which='major')  # Very subtle grid

Framed Presentation Slide
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # For presentations with impact
   dm.add_frame(ax, color='oc.blue8', linewidth=2)  # Bold frame
   dm.remove_grid(ax)  # No grid for clarity

Integration with Themes
-----------------------

Spine utilities respect and complement dartwork-mpl themes:

.. code-block:: python

   # Apply theme first
   dm.style.use('scientific')
   fig, ax = dm.subplots()

   # Then customize spines as needed
   dm.minimal_axes(ax)  # Works with any theme

   # Theme colors are available
   dm.style_spines(ax, color='dc.charcoal8', linewidth=0.8)

See Also
--------

- :doc:`layout` - Layout utilities for spacing
- :doc:`../usage_guide/quickstart` - Getting started guide
- :doc:`../philosophy/utilities_not_wrappers` - Design philosophy