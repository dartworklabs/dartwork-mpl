Units (``dm.cm`` / ``dm.inch`` / ``dm.mm``)
===========================================

Free-form width/aspect input helpers (0.4+).

The 0.4 figure-creation API takes a free-form ``width=`` value plus
a separate ``aspect=`` (height / width). This module is the parser
that turns user inputs — unit-suffixed strings, helper calls, raw
numbers — into a single inch-valued ``float`` that matplotlib's
``figsize`` argument expects, and resolves named aspect tokens
(``square`` / ``portrait`` / ``standard`` / ``golden`` / ``wide`` /
``cinema``) into a height/width ratio.

Most callers never touch this module directly: they hand a string
or a helper call to :func:`dartwork_mpl.subplots`, and the parser
runs underneath. The names below are the underlying primitives in
case you need to share a width across several figures or convert
ad-hoc.

.. code-block:: python

   import dartwork_mpl as dm

   # Helper calls — return Inches (a float subclass)
   dm.cm(13)            # Inches(5.118...)
   dm.inch(6.7)         # Inches(6.7)
   dm.mm(170)           # Inches(6.692...)

   # parse_width accepts strings, Inches, or raw numbers (cm)
   from dartwork_mpl.units import parse_width, parse_aspect
   parse_width("13cm")     # 5.118...
   parse_width("6.7in")    # 6.7
   parse_width(13)         # 5.118... (bare number → cm)
   parse_aspect("standard")  # 0.75

API
---

.. automodule:: dartwork_mpl.units
   :members:
   :undoc-members:
   :show-inheritance:
