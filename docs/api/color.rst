Color Utilities
===============

Importing ``dartwork_mpl`` registers a large catalog of named colors with
matplotlib (``oc.*`` plus Tailwind ``tw.``, Material ``md.``, Ant Design
``ad.``, Chakra ``cu.``, and Primer ``pr.`` prefixes). In addition to the
named palette, a ``Color`` class provides perceptually uniform color
manipulation across OKLab, OKLCH, RGB, and hex color spaces.

Example
-------

.. code-block:: python

   import matplotlib.pyplot as plt
   import dartwork_mpl as dm

   # Named colors
   plt.plot(x, y, color="dc.corporate2", label="Series A")
   lighter = dm.mix_colors("dc.corporate2", "white", alpha=0.35)
   muted_line = dm.pseudo_alpha("dc.corporate3", alpha=0.6)

   # Color class — perceptual manipulation
   color = dm.oklch(0.7, 0.15, 150)
   color.oklch.C *= 1.2                  # boost chroma
   print(color.to_hex())                 # '#...'

   # Interpolation
   palette = dm.cspace('#FF6B6B', '#4ECDC4', n=5, space='oklch')
   for i, c in enumerate(palette):
       ax.bar(i, 1, color=c.to_hex())

``cspace('#FF6B6B', '#4ECDC4', n=8, space='oklch')`` interpolates perceptually
through OKLCH — hover a step for its hex:

.. raw:: html

   <div style="display:flex;gap:4px;margin:8px 0 4px;flex-wrap:wrap;font-family:ui-monospace,Menlo,monospace">
     <span title="#FF6B6B" style="width:40px;height:40px;border-radius:6px;background:#FF6B6B;box-shadow:inset 0 0 0 1px rgba(127,127,127,.22)"></span>
     <span title="#F97D38" style="width:40px;height:40px;border-radius:6px;background:#F97D38;box-shadow:inset 0 0 0 1px rgba(127,127,127,.22)"></span>
     <span title="#E59300" style="width:40px;height:40px;border-radius:6px;background:#E59300;box-shadow:inset 0 0 0 1px rgba(127,127,127,.22)"></span>
     <span title="#CAA701" style="width:40px;height:40px;border-radius:6px;background:#CAA701;box-shadow:inset 0 0 0 1px rgba(127,127,127,.22)"></span>
     <span title="#A7B945" style="width:40px;height:40px;border-radius:6px;background:#A7B945;box-shadow:inset 0 0 0 1px rgba(127,127,127,.22)"></span>
     <span title="#7FC575" style="width:40px;height:40px;border-radius:6px;background:#7FC575;box-shadow:inset 0 0 0 1px rgba(127,127,127,.22)"></span>
     <span title="#5CCCA0" style="width:40px;height:40px;border-radius:6px;background:#5CCCA0;box-shadow:inset 0 0 0 1px rgba(127,127,127,.22)"></span>
     <span title="#4ECDC4" style="width:40px;height:40px;border-radius:6px;background:#4ECDC4;box-shadow:inset 0 0 0 1px rgba(127,127,127,.22)"></span>
   </div>
   <p style="font-size:12px;color:var(--dm-text-muted,#8a90a0);margin:2px 0 0">
   Named colours, <code>mix_colors</code>, and <code>pseudo_alpha</code> compose
   the same way — see the snippet above.</p>

API
---

Color Manipulation
^^^^^^^^^^^^^^^^^^

.. automodule:: dartwork_mpl.colors
   :members:
   :undoc-members:
   :show-inheritance:

.. note::

   ``mix_colors`` and ``pseudo_alpha`` are defined in the ``util`` module
   but re-exported from the top-level ``dartwork_mpl`` namespace for
   convenience alongside other color helpers.

.. autofunction:: dartwork_mpl.mix_colors
.. autofunction:: dartwork_mpl.pseudo_alpha

Color Interpolation
^^^^^^^^^^^^^^^^^^^

.. autofunction:: dartwork_mpl.cspace

Palette Discovery
^^^^^^^^^^^^^^^^^

.. autofunction:: dartwork_mpl.list_palettes
.. autofunction:: dartwork_mpl.list_colormaps
.. autofunction:: dartwork_mpl.show_palette

Visualization Tools
^^^^^^^^^^^^^^^^^^^^

.. autofunction:: dartwork_mpl.plot_colors
.. autofunction:: dartwork_mpl.plot_colormaps
.. autofunction:: dartwork_mpl.classify_colormap
