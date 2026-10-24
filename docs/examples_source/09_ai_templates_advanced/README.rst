Advanced AI Plot Templates (Tier 2)
====================================

Tier-2 templates extend each basic plot type with:

* **Believable synthetic data** (a story, not random noise)
* **Reference lines / event windows / threshold annotations**
* **Per-element value labels** (bars, points, segments)
* **Self-validation** via ``dm.validate_with_fixes`` +
  ``dm.check_figure_quality``

Like the basic tier, they size the canvas with ``dm.figsize_for(...)``
and draw no title, subtitle or source note: a caption or slide carries
those, and an agent adds one only when the user asks for it.

Use these as the gold standard when you want the AI-generated plot to
read like a finished report figure. See the basic gallery one level up
for the minimal "just get a chart out" version.
