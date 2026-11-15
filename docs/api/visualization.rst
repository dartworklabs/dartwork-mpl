Asset Diagnostics
=================

:func:`dartwork_mpl.plot_fonts` renders the registered font families with
their weight spectrum and a pangram, without calling ``plt.show()``, so it
composes with your normal save / display pipeline. For colours,
``dm.list_colors()`` lists the ``dc.*`` families and ``dm.colors(name, n=...)``
returns one family's designed colours; browse the token sheets in
:doc:`Colors <../color_system/colors>` and the continuous maps in the
:doc:`Colormaps <../color_system/colormaps>` catalog.

.. code-block:: python

   import dartwork_mpl as dm

   fig = dm.plot_fonts(font_size=11, ncols=3)   # are my CJK fonts registered?
   [f["name"] for f in dm.list_colors("diverging")]

API
---

.. autofunction:: dartwork_mpl.plot_fonts
   :no-index:
