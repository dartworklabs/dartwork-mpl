Lint (``dm.lint``)
==================

Static checker against the dartwork-mpl anti-pattern catalog (0.4+).

``dm.lint_code(source)`` checks a Python source string against the
anti-pattern catalog shipped at ``asset/prompt/02-anti-patterns.yaml``.
The MCP ``lint_dartwork_mpl_code`` tool uses the same engine, so
Python callers and AI assistants see the same violations.
No lint CLI is provided.

Quick start
-----------

.. code-block:: python

   import dartwork_mpl as dm
   from dartwork_mpl.lint import format_report

   source = """
   import matplotlib.pyplot as plt
   fig, ax = plt.subplots(figsize=(6.7, 4.0))
   plt.tight_layout()
   """

   issues = dm.lint_code(source)
   for issue in issues:
       print(issue.rule_id, issue.severity, issue.message)

   # Or render a human-readable report
   print(format_report(issues))

Each rule entry has an ``id``, ``severity``
(``critical`` / ``warning`` / ``info``), a short ``message``, an
optional ``why`` blurb, and a recommended ``fix_suggestion``. The
catalog lives in YAML so adding or tightening a rule is a single
file edit; the lint engine reloads it on call.

``load_rules(path)`` rejects unsupported severity, detector kind/check,
invalid regex patterns, and malformed containers or required fields with
contextual ``ValueError`` at load time. Previously some invalid catalogs
loaded successfully or raised incidental access errors. Empty mappings
and empty ``rules`` lists remain valid; filesystem and YAML syntax errors
retain their native exceptions.

Catalog highlights
------------------

- ``figsize-direct`` — raw ``figsize=(w, h)`` tuples are forbidden;
  use ``figsize=dm.figsize("<n>cm", "<aspect>")``.
- ``dm-subplots-removed`` — ``dm.subplots`` / ``dm.figure`` were
  removed; use ``plt.subplots(figsize=dm.figsize(...))``.
- ``raw-width-number`` — bare numbers passed to ``dm.figsize`` are
  rejected because they carry no unit.
- ``tight-layout`` — ``plt.tight_layout()`` is forbidden; use
  ``dm.simple_layout(fig)``.
- ``deprecated-width-token`` — deprecated 0.3 width tokens
  (``dm.SW`` / ``MW`` / ``TW`` / ``DW``).
- ``oversize-width`` — widths beyond 17 cm break most page layouts.
- ``fontsize-literal`` / ``linewidth-literal`` — pass numeric values
  via ``dm.fs(n)`` / ``dm.lw(n)`` so they track the active style.
- ``raw-hex-color`` — prefer named palette tokens (``oc.``, ``tw.``,
  ``dc.``, …) over inline hex.
- ``jet-cmap`` — flag rainbow colormaps that misrepresent ordinal
  data.

The full list (always authoritative) is at
``asset/prompt/02-anti-patterns.yaml`` in the source tree, or via
the MCP resource ``dartwork-mpl://guide/anti-patterns``.

API
---

.. automodule:: dartwork_mpl.lint
   :members:
   :undoc-members:
   :show-inheritance:
