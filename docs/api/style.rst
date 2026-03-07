Style Management
================

Helpers for discovering and applying the packaged matplotlib styles. The
``Style`` manager reads ``asset/mplstyle`` and preset combinations (scientific,
investment, presentation, and Korean variants) from ``presets.json``, resets
``rcParams``, and stacks multiple style files when needed.

Typical usage
-------------

.. code-block:: python

   import dartwork_mpl as dm

   # Apply a preset (recommended)
   dm.style.use("scientific")
   dm.style.use("presentation-kr")

   # Stack multiple styles for advanced customization
   dm.style.stack(["base", "font-scientific", "lang-kr"])

   # Inspect what a style will set
   available = dm.list_styles()
   style_dict = dm.load_style_dict("font-presentation")

API
---

.. automodule:: dartwork_mpl.style
   :members:
   :undoc-members:
   :show-inheritance:
