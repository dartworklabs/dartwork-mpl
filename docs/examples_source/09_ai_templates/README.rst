AI Plot Templates
-----------------

Eighteen ready-to-use plot templates curated for AI coding assistants. Each
template is a small, self-contained script written with the 0.4
``width=...``/``aspect=...`` API and Open Color palette. They are bundled in
the wheel under ``dartwork_mpl/asset/prompt/05-templates/`` and exposed
through both the prompt utilities and the
:doc:`MCP server </integrations/mcp_server>`.

How to access these templates
=============================

.. code-block:: python

   import dartwork_mpl as dm

   # Read a template script as text
   bar_src = dm.get_prompt("05-templates/bar")

   # Or list everything available under prompts/
   print(dm.list_prompts())

Or via MCP from Claude / Cursor / Continue:

.. code-block:: text

   dartwork-mpl://templates/{plot_type}

where ``{plot_type}`` is one of ``bar``, ``bar_horizontal``,
``bar_grouped``, ``boxplot``, ``contour``, ``heatmap``, ``histogram``,
``line``, ``pie``, ``plot_3d``, ``polar``, ``scatter``, ``small_multiples``,
``stacked_bar``, ``tornado``, ``twin_axis``, ``violin``, or ``waterfall``.

The gallery entries below render each template so you can pick the right
shape at a glance, then copy the source from the page (or fetch it via
``dm.get_prompt``) into your project.
