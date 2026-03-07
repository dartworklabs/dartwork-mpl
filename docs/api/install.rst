LLM Integration
===============

Utilities for installing dartwork-mpl usage guides into IDE integration
folders, enabling AI coding assistants to automatically access library
documentation.

``install_llm_txt(project_dir=None)``
   - Parameters:
     - ``project_dir``: project directory; ``None`` uses ``cwd()``.
   - Side effects:
     - Creates ``.claude/commands/dartwork-mpl-usage.md``
     - Creates ``.cursor/dartwork-mpl-usage.md``
   - Returns: ``None`` (prints confirmation).

``uninstall_llm_txt(project_dir=None)``
   - Parameters:
     - ``project_dir``: project directory; ``None`` uses ``cwd()``.
   - Side effects:
     - Removes the files created by ``install_llm_txt``.
   - Returns: ``None``.

Example
-------

.. code-block:: python

   import dartwork_mpl as dm

   # Install usage guides for AI assistants
   dm.install_llm_txt()
   # ✅ dartwork-mpl usage guide installed successfully!
   # 📁 Claude Code: .claude/commands/dartwork-mpl-usage.md
   # 📁 Cursor IDE: .cursor/dartwork-mpl-usage.md

   # Remove when no longer needed
   dm.uninstall_llm_txt()

.. automodule:: dartwork_mpl.install
   :members:
   :undoc-members:
   :show-inheritance:
