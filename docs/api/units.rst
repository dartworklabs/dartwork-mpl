Units (``dm.Length`` / ``dm.cm`` / ``dm.inch`` / ``dm.mm`` / ``dm.pt``)
=======================================================================

Free-form width/aspect input helpers (0.4+).

The 0.4 figure-creation API takes a free-form ``width=`` value plus
a separate ``aspect=`` (height / width). This module is the parser
that turns user inputs — unit-suffixed strings or
:class:`~dartwork_mpl.units.Length` instances — into a single
inch-valued ``float`` that matplotlib's ``figsize`` argument
expects, and resolves named aspect tokens (``square`` /
``portrait`` / ``standard`` / ``golden`` / ``wide`` / ``cinema``)
into a height/width ratio.

Most callers never touch this module directly: they hand a string
or a helper call to :func:`dartwork_mpl.figsize`, and the parser
runs underneath. The names below are the underlying primitives in
case you need to share a length across several figures or convert
ad-hoc.

.. code-block:: python

   import dartwork_mpl as dm

   # Helper calls — return Length (Color-pattern wrapper)
   dm.cm(13)            # Length(13.0000cm)
   dm.inch(6.7)         # Length(6.7000in)
   dm.mm(170)           # Length(17.0000cm)
   dm.pt(24)            # Length(0.8467cm)

   # Multi-unit views as properties
   dm.cm(13).inch       # 5.118...
   dm.cm(13).pt         # 368.5...

   # parse_width accepts unit strings or Length instances
   from dartwork_mpl.units import parse_width, parse_aspect
   parse_width("13cm")     # 5.118...
   parse_width("6.7in")    # 6.7
   parse_width(dm.cm(13))  # 5.118... (Length pass-through)
   parse_aspect("standard")  # 0.75

   # dm.figsize's second argument is polymorphic — pick whichever
   # form reads naturally for the call site:
   dm.figsize("13cm", "wide")        # aspect token
   dm.figsize("13cm", 0.6)           # numeric ratio (height/width)
   dm.figsize("13cm", "8cm")         # unit-string height
   dm.figsize("13cm", dm.cm(8))      # Length height
   dm.figsize("13cm", "5in")         # mixed units (height in inches)

API
---

.. automodule:: dartwork_mpl.units
   :members:
   :undoc-members:
   :show-inheritance:
