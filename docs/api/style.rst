Style Management
================

Helpers for discovering and applying the packaged matplotlib styles. The
``Style`` manager reads ``asset/mplstyle`` and preset combinations (scientific,
investment, presentation, and Korean variants) from ``presets.json``, resets
``rcParams``, and stacks multiple style files when needed. Use the helpers below
to apply a preset, stack multiple styles, or inspect what a preset changes
before you commit it to a figure.

``Style.use(preset_name)``
Applies a preset key from ``presets.json`` (e.g., ``"scientific"``,
``"investment"``, ``"presentation"``, ``"scientific-kr"``). This is the
recommended way to apply styles.

- Parameters:
  - ``preset_name``: string looked up in the presets mapping.
- Returns:
  - ``None``.

``Style.stack(style_names)``
Stack multiple style files in order. Use this for advanced customization.

- Parameters:
  - ``style_names``: list/tuple of style stems; later styles override earlier ones.
- Returns:
  - ``None``.

``list_styles()``
Lists every ``*.mplstyle`` file bundled with the package.

- Parameters:
  - none.
- Returns:
  - ``list[str]`` sorted by filename.

``load_style_dict(name)``
Reads a single style file into a ``dict`` so you can inspect or tweak rcParams
programmatically.

- Parameters:
  - ``name``: style stem.
- Returns:
  - ``dict`` mapping rcParam keys to values.

``style_path(name)``
Returns the ``pathlib.Path`` to a style file.

- Parameters:
  - ``name``: style stem (e.g. ``"base"``).
- Returns:
  - ``pathlib.Path`` to the ``.mplstyle`` file.
- Raises:
  - ``ValueError`` if the style is not found.

Typical usage

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

.. automodule:: dartwork_mpl.style
   :members:
   :undoc-members:
   :show-inheritance:
