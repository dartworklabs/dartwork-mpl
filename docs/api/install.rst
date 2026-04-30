Install (``dm.install_llm_txt``)
================================

LLM/agent integration installer.

``dartwork_mpl.install`` writes the canonical 0.4 usage bundle —
composed at install-time from the SSOT prompt directory under
``asset/prompt/`` — into the location an IDE or AI coding assistant
expects (e.g. Cursor's project rules, Claude Code's project memory).

The bundle is rebuilt from
``asset/prompt/00-index.md`` + ``01-policy.md`` + ``03-recipes.md``
each time, so it always tracks the canonical guidance and never
drifts from the lint catalog at ``02-anti-patterns.yaml``.

Quick start
-----------

.. code-block:: python

   import dartwork_mpl as dm

   # Install the bundle for the active project
   dm.install_llm_txt()

   # Remove it later
   dm.uninstall_llm_txt()

API
---

.. automodule:: dartwork_mpl.install
   :members:
   :undoc-members:
   :show-inheritance:
