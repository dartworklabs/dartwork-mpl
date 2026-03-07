Prompt Utilities
================

Bundled prompt guide files for AI coding assistants are stored in
``asset/prompt/*.md``.  These utilities let you list, read, and copy
them into your project.  Use them together with the
:doc:`MCP Server </integrations/mcp_server>` for the richest AI
integration, or stand-alone for manual context injection.

Example
-------

.. code-block:: python

   import dartwork_mpl as dm

   # List available guides
   available = dm.list_prompts()           # ['general-guide', 'layout-guide']

   # Read guide content
   content = dm.get_prompt('layout-guide')

   # Copy to IDE folder
   dm.copy_prompt('layout-guide', '.cursor/rules/')

   # Get the file path directly
   print(dm.prompt_path('general-guide'))

API
---

.. autofunction:: dartwork_mpl.prompt_path
.. autofunction:: dartwork_mpl.get_prompt
.. autofunction:: dartwork_mpl.list_prompts
.. autofunction:: dartwork_mpl.copy_prompt

LLM Integration
---------------

Install or remove static guide files for IDE-based AI assistants that
do not support MCP.

.. autofunction:: dartwork_mpl.install_llm_txt
.. autofunction:: dartwork_mpl.uninstall_llm_txt
