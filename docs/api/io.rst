File I/O
========

Thin wrappers around ``matplotlib.Figure.savefig`` for common workflows:
export multiple formats in one call, or save-and-display SVGs sized for
notebooks/reports. Also includes prompt file utilities for managing
AI assistant guides bundled with the package.

Save & Display
--------------

``save_formats(fig, image_stem, formats=("png", "pdf"), bbox_inches=None, validate=True, **kwargs)``
   - Parameters:
     - ``fig``: figure to export.
     - ``image_stem``: path without extension; parent folders are created.
     - ``formats``: iterable of formats to write.
     - ``bbox_inches``: optional value forwarded to ``savefig``.
     - ``validate``: if ``True`` (default), runs ``validate_figure()`` before saving
       and prints ``[VISUAL]`` warnings to stdout.
     - ``**kwargs``: any extra arguments passed to ``savefig``.
   - Returns:
     - ``None`` after writing one file per requested format.

``save_and_show(fig, image_path=None, size=600, unit="pt", **kwargs)``
   - Parameters:
     - ``fig``: figure to save (closed after saving).
     - ``image_path``: destination path or ``None`` to use a temporary SVG.
     - ``size``: inline display width.
     - ``unit``: unit for ``size`` (defaults to points).
     - ``**kwargs``: forwarded to ``savefig``.
   - Returns:
     - ``None``; displays the SVG inline (Jupyter/HTML).

``show(image_path, size=600, unit="pt")``
   - Parameters:
     - ``image_path``: SVG file to display.
     - ``size``: display width.
     - ``unit``: unit for ``size``.
   - Returns:
     - ``None``; shows the scaled SVG inline.

Prompt Utilities
----------------

Bundled prompt guide files for AI coding assistants are stored in
``asset/prompt/*.md``.  These utilities let you list, read, and copy
them into your project.

``prompt_path(name)``
   - Parameters:
     - ``name``: prompt guide name (e.g. ``'layout-guide'``, ``'general-guide'``).
   - Returns:
     - ``pathlib.Path`` to the guide file.
   - Raises:
     - ``ValueError`` if the guide is not found.

``get_prompt(name)``
   - Parameters:
     - ``name``: prompt guide name.
   - Returns:
     - ``str`` — full content of the guide.

``list_prompts()``
   - Returns:
     - ``list[str]`` — available prompt guide names.

``copy_prompt(name, destination)``
   - Parameters:
     - ``name``: prompt guide name.
     - ``destination``: directory or file path; parent dirs are created.
   - Returns:
     - ``pathlib.Path`` — path to the copied file.

Example
-------

.. code-block:: python

   import dartwork_mpl as dm

   # Multi-format export with validation
   dm.save_formats(fig, "report/figures/example",
                   formats=("png", "svg", "pdf"), dpi=300)

   # Save and preview
   dm.save_and_show(fig, size=720)

   # Prompt guides
   available = dm.list_prompts()           # ['general-guide', 'layout-guide']
   content = dm.get_prompt('layout-guide')  # read content
   dm.copy_prompt('layout-guide', '.cursor/rules/')  # copy to IDE folder

.. autofunction:: dartwork_mpl.save_formats
.. autofunction:: dartwork_mpl.save_and_show
.. autofunction:: dartwork_mpl.show
.. autofunction:: dartwork_mpl.prompt_path
.. autofunction:: dartwork_mpl.get_prompt
.. autofunction:: dartwork_mpl.list_prompts
.. autofunction:: dartwork_mpl.copy_prompt
