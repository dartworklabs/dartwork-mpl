Lint (``dm.lint``)
==================

Static checker against the dartwork-mpl anti-pattern catalog (0.4+).

``dm.lint`` runs a Python source string through the 15-rule
anti-pattern catalog shipped at
``asset/prompt/02-anti-patterns.yaml``. It is the same engine
behind the MCP ``lint_dartwork_mpl_code`` tool and the
``dartwork-mpl lint`` CLI, so editor integrations, CI, and AI
assistants all see the same violations.

Quick start
-----------

.. code-block:: python

   import dartwork_mpl as dm

   source = """
   import matplotlib.pyplot as plt
   fig, ax = plt.subplots(figsize=(6.7, 4.0))
   plt.tight_layout()
   """

   issues = dm.lint.lint(source)
   for issue in issues:
       print(issue.rule_id, issue.severity, issue.message)

   # Or render a human-readable report
   print(dm.lint.format_report(issues))

Each rule entry has an ``id``, ``severity``
(``critical`` / ``warning`` / ``info``), a short ``message``, an
optional ``why`` blurb, and a recommended ``fix_suggestion``. The
catalog lives in YAML so adding or tightening a rule is a single
file edit; the lint engine reloads it on call.

Catalog highlights
------------------

- ``figsize-direct`` — raw ``figsize=(w, h)`` tuples are forbidden;
  use ``figsize=dm.figsize("<n>cm", "<aspect>")``.
- ``dm-subplots-removed`` — ``dm.subplots`` / ``dm.figure`` were
  removed; use ``plt.subplots(figsize=dm.figsize(...))``.
- ``raw-width-number`` — bare numbers passed to ``dm.figsize`` are
  rejected because they carry no unit.
- ``tight-layout`` — ``plt.tight_layout()`` is forbidden; use
  ``dm.auto_layout(fig)``.
- ``width-token`` — deprecated 0.3 width tokens
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
