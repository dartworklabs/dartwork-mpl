Prompt Utilities
================

Bundled prompt guide files for AI coding assistants are stored in
``asset/prompt/*.md`` and ``asset/prompt/*.yaml``.  These utilities let you list, read, and copy
them into your project.  Use them together with the
:doc:`MCP Server </integrations/mcp_server>` for the richest AI
integration, or stand-alone for manual context injection.

Example
-------

.. code-block:: python

   import dartwork_mpl as dm

   # List available guides
   available = dm.list_prompts()
   # ['00-index', '01-policy', '02-anti-patterns', '03-recipes']

   # Read guide content
   content = dm.get_prompt("02-anti-patterns")

   # Copy to IDE folder
   dm.copy_prompt("01-policy", ".cursor/rules/")

   # Get the file path directly
   print(dm.prompt_path("00-index"))

API
---

.. autofunction:: dartwork_mpl.prompt_path
.. autofunction:: dartwork_mpl.get_prompt
.. autofunction:: dartwork_mpl.list_prompts
.. autofunction:: dartwork_mpl.copy_prompt
