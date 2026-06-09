API Reference
=============

dartwork-mpl ships one import (``import dartwork_mpl as dm``) but several
small domains. Each page explains arguments in plain language plus defaults
that work in most cases.

Core
----

The essential modules you'll use in every project.

.. toctree::
   :maxdepth: 1
   :titlesonly:

   Style Management <style>
   Figure Creation <figure>
   Units (cm/inch/mm) <units>
   Layout Utilities <layout>
   Color Utilities <color>
   Formatting Utilities <formatting>
   Save & Export <io>
   Visual Validation <validate>
   Lint <lint>
   Configuration <config>

Extensions
----------

Additional tools for specialized use cases.

.. toctree::
   :maxdepth: 1
   :titlesonly:

   Font Utilities <font>
   Icon Font System <icon>
   Colormap Registry <cmap>
   Plot Templates <templates>
   Agent Helper Utilities <helpers>
   Interactive Viewer <ui>
   Asset Diagnostics (visualization) <visualization>
   Diagnostics (module) <diagnostics>
   Prompt Utilities <prompt>
   Figure Constants (deprecated) <constant>

Upgrading
---------

Already using a previous PyPI release? The
:doc:`Migration Guide </migration>` tracks every renamed / removed
name since v0.4.0 with a side-by-side ``Before → After`` table —
each entry's replacement is a one-line edit.
