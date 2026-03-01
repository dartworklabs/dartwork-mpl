Icon Font System
================

dartwork-mpl bundles icon fonts from **Material Design Icons (MDI)** and
**Font Awesome 6 (FA6)** in ``asset/icon/``. They are auto-registered with
matplotlib on import, so you can render icons directly with ``ax.text()``.

``icon_font(name='mdi')``
   - Parameters:
     - ``name``: icon font identifier (``'mdi'``, ``'fa-solid'``, ``'fa-regular'``, ``'fa-brands'``).
   - Returns:
     - ``matplotlib.font_manager.FontProperties`` ready for ``ax.text()``.

``icon_font_path(name='mdi')``
   - Parameters:
     - ``name``: icon font identifier.
   - Returns:
     - ``pathlib.Path`` to the font file on disk.

``list_icon_fonts()``
   - Returns:
     - sorted list of available icon font identifiers.

Bundled Icon Fonts
------------------

.. list-table::
   :header-rows: 1
   :widths: 15 35 15 35

   * - Identifier
     - Font
     - Icons
     - Style
   * - ``mdi``
     - Material Design Icons (Templarian)
     - 7,448+
     - Filled + Outline
   * - ``fa-solid``
     - Font Awesome 6 Free Solid
     - 2,000+
     - Filled
   * - ``fa-regular``
     - Font Awesome 6 Free Regular
     - 160+
     - Outline
   * - ``fa-brands``
     - Font Awesome 6 Brands
     - 460+
     - Brand logos

Example
-------

.. code-block:: python

   import dartwork_mpl as dm

   # Load icon font
   mdi = dm.icon_font('mdi')
   fa  = dm.icon_font('fa-solid')

   fig, ax = plt.subplots()

   # Render MDI thermometer icon
   ax.text(0.5, 0.5, "\U000F050F",
           fontproperties=mdi, fontsize=24,
           ha='center', va='center', color='tw.teal500')

   # Get font file path directly
   path = dm.icon_font_path('mdi')
   print(path)  # .../asset/icon/materialdesignicons-webfont.ttf

.. automodule:: dartwork_mpl.icon
   :members:
   :undoc-members:
   :show-inheritance:
