Color Utilities
===============

Importing ``dartwork_mpl`` registers a large catalog of named colors with
matplotlib (``oc.*`` plus Tailwind ``tw.``, Material ``md.``, Ant Design
``ad.``, Chakra ``cu.``, and Primer ``pr.`` prefixes). In addition to the
named palette, a ``Color`` class provides perceptually uniform color
manipulation across OKLab, OKLCH, RGB, and hex color spaces.

Color Class
-----------

The ``Color`` class stores colors internally as OKLab coordinates for
perceptually uniform operations. Use class methods or convenience
constructors to create instances.

**Constructors (classmethods):**

- ``Color.from_oklab(L, a, b)`` — create from OKLab coordinates
- ``Color.from_oklch(L, C, h)`` — create from OKLCH (h in degrees)
- ``Color.from_rgb(r, g, b)`` — create from RGB (auto-detects 0–1 or 0–255)
- ``Color.from_hex(hex_str)`` — create from ``#RGB`` or ``#RRGGBB``
- ``Color.from_name(name)`` — create from matplotlib color name (incl. ``oc.*``, ``tw.*``)

**Convenience wrappers (module-level):**

- ``dm.oklab(L, a, b)`` → ``Color``
- ``dm.oklch(L, C, h)`` → ``Color``
- ``dm.rgb(r, g, b)`` → ``Color``
- ``dm.hex(hex_str)`` → ``Color``
- ``dm.named(name)`` → ``Color``

**Views (mutable references):**

- ``color.oklab`` → ``OklabView`` with ``.L``, ``.a``, ``.b`` (read/write)
- ``color.oklch`` → ``OklchView`` with ``.L``, ``.C``, ``.h`` (read/write)
- ``color.rgb`` → ``RgbView`` with ``.r``, ``.g``, ``.b`` (read/write)

All views support unpacking (``L, a, b = color.oklab``) and indexing
(``color.oklab[0]``).

**Conversion methods:**

- ``color.to_oklab()`` → ``(L, a, b)``
- ``color.to_oklch()`` → ``(L, C, h)``
- ``color.to_rgb()`` → ``(r, g, b)``
- ``color.to_hex()`` → ``str``
- ``color.copy()`` → ``Color``

Color Space Interpolation
-------------------------

``cspace(start_color, end_color, n, space='oklch')``

- Parameters:
  - ``start_color``, ``end_color``: ``Color`` instance or hex string.
  - ``n``: number of colors to generate (including endpoints).
  - ``space``: interpolation space — ``'oklch'`` (default), ``'oklab'``, or ``'rgb'``.
- Returns:
  - ``list[Color]`` — interpolated colors.

Color Mixing Utilities
----------------------

``mix_colors(color1, color2, alpha=0.5)``

- Parameters:
  - ``color1``: matplotlib-compatible color (name or RGB tuple).
  - ``color2``: second color to blend toward.
  - ``alpha``: weight for ``color1`` between 0 (all ``color2``) and 1 (all ``color1``).
- Returns:
  - blended RGB tuple.

``pseudo_alpha(color, alpha=1.0, background="white")``

- Parameters:
  - ``color``: foreground color to soften.
  - ``alpha``: perceived transparency level.
  - ``background``: color to mix toward when true transparency is unavailable (e.g., PDF export).
- Returns:
  - RGB tuple mixed against ``background``.

``classify_colormap(cmap)``

- Parameters:
  - ``cmap``: colormap instance or name.
- Returns: string label — one of ``"Categorical"``, ``"Sequential Single-Hue"``,
  ``"Sequential Multi-Hue"``, ``"Diverging"``, or ``"Cyclical"``.

Example
-------

.. code-block:: python

   import matplotlib.pyplot as plt
   import dartwork_mpl as dm

   # Named colors
   plt.plot(x, y, color="oc.blue5", label="Series A")
   lighter = dm.mix_colors("oc.blue5", "white", alpha=0.35)
   muted_line = dm.pseudo_alpha("oc.blue7", alpha=0.6)

   # Color class — perceptual manipulation
   color = dm.oklch(0.7, 0.15, 150)
   color.oklch.C *= 1.2                  # boost chroma
   print(color.to_hex())                 # '#...'

   # Interpolation
   palette = dm.cspace('#FF6B6B', '#4ECDC4', n=5, space='oklch')
   for i, c in enumerate(palette):
       ax.bar(i, 1, color=c.to_hex())

.. automodule:: dartwork_mpl.color
   :members:
   :undoc-members:
   :show-inheritance:

.. autofunction:: dartwork_mpl.mix_colors
.. autofunction:: dartwork_mpl.pseudo_alpha
.. autofunction:: dartwork_mpl.classify_colormap
