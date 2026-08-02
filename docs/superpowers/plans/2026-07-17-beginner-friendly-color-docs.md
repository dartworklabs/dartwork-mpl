# Beginner-Friendly Color Documentation Implementation Plan

> **Status: historical record — do not execute.**
> The REQUIRED SUB-SKILL directive, unchecked checkboxes, commands,
> `/private/tmp` paths, and 17-surface, physical-Y, and print wording below
> describe the 2026-07-17 implementation session only. They are preserved for
> provenance; current source, approved specifications, tests, and the active
> goal govern current work.
>
> **Everything below—including the “For agentic workers” directive, all
> checkboxes, commands, `/private/tmp` paths, and 17-surface, physical-Y, and
> print wording—is historical quotation only; do not follow or execute it.**

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the current public color documentation so a reader with no color-theory background can choose and understand the system without losing any existing technical fact, example, figure, metric, or compatibility caveat.

**Architecture:** Keep the existing URLs and interactive assets. Turn `docs/usage_guide/colors.md` into the beginner path, make the catalog pages task-first references, and layer Design rationale and Validation as plain-language conclusions followed by optional technical detail. A tracked claim inventory plus semantic documentation tests protects against content loss.

**Tech Stack:** MyST Markdown, Sphinx, sphinx-design admonitions, pytest, Ruff, existing generated HTML/SVG explorers.

## Global Constraints

- This is a readability refactor only: do not change Python behavior, color output, APIs, catalog membership, generated authorities, CSS, or JavaScript.
- Preserve every unique formula, measured value, threshold, count, protocol/model name, citation, provenance statement, compatibility caveat, code example, widget, figure, and API instruction.
- Duplicate wording may be consolidated only when the same meaning remains at an obvious destination.
- Keep construction as OKLab `L` / OKLCH `C` and `h` / DeltaEOK; keep physical `relative_y` as the optional shipped-output compatibility contract; keep CIELAB/DeltaE00/CVD validation-only; keep WCAG contrast separate.
- Never call OKLab, OKLCH, or the catalog perfectly perceptually uniform.
- Never describe physical Y as perceived brightness or as OKLab `L`.
- Expand acronyms at first meaningful use and state how to interpret the number or model.
- Reuse existing MyST `tip`, `note`, `important`, and dropdown-admonition patterns; add no new presentation dependency.
- Keep all current URLs and root/sidebar topology; do not add a standalone primer or glossary page.
- Continue in `/private/tmp/dartwork-mpl-oklab`; do not edit the user's main worktree.
- Do not stage or commit until the user explicitly approves the complete color-system branch.

---

### Task 1: Freeze the Content-Preservation and Beginner-Language Contracts

**Files:**
- Create: `docs/superpowers/specs/assets/2026-07-17-beginner-friendly-color-docs/claim-inventory.md`
- Create: `tests/test_docs_beginner_color_language.py`
- Reference: `docs/superpowers/specs/2026-07-17-beginner-friendly-color-docs-design.md`

**Interfaces:**
- Consumes: the unedited public pages and the approved vocabulary contract in the design spec.
- Produces: a human-readable map from each existing claim group to its final destination, plus executable requirements for the beginner-facing copy.

- [ ] **Step 1: Record the pre-edit claim inventory**

Create the inventory with one row for every item below. Use columns `ID`,
`source`, `preserved content`, `destination`, and `status`. Begin with
`destination` equal to the current source and `status` equal to `pending`.

```markdown
| ID | source | preserved content | destination | status |
|---|---|---|---|---|
| U01 | usage_guide/colors.md | seven library prefixes and `dc.*` recommendation | usage_guide/colors.md | pending |
| U02 | usage_guide/colors.md | `color=` versus `cmap=` distinction | usage_guide/colors.md | pending |
| U03 | usage_guide/colors.md | named-color, mixing, pseudo-alpha, manual cycler, discovery, interpolation, and colormap examples | usage_guide/colors.md | pending |
| U04 | usage_guide/colors.md | interpolation and colormap widgets | usage_guide/colors.md | pending |
| C01 | color_system/colors.md | 20 families: 19 chromatic ramps plus gray, ten steps, naming grammar | color_system/colors.md | pending |
| C02 | color_system/colors.md | semantic aliases and locale behavior | color_system/colors.md | pending |
| C03 | color_system/colors.md | six third-party token sheets and rendering guidance | color_system/colors.md | pending |
| P01 | color_system/palettes.md | explorer, 13 rail choices, apply examples, chooser table | color_system/palettes.md | pending |
| P02 | color_system/palettes.md | four discrete forms, counts, API grammar, curated membership | color_system/palettes.md | pending |
| P03 | color_system/palettes.md | Octave/Okabe-Ito/CVD scores, CVD model attribution, L* print diagnostics, style expansion | color_system/palettes.md | pending |
| M01 | color_system/colormaps.md | 43 continuous, 13 qualitative, 56 records, 99 registrations | color_system/colormaps.md | pending |
| M02 | color_system/colormaps.md | explorer and complete four-group name table | color_system/colormaps.md | pending |
| M03 | color_system/colormaps.md | direction grammar, dark-center and isoluminant notes, chooser | color_system/colormaps.md | pending |
| M04 | color_system/colormaps.md | aurora/viridis CV values and interpretation | color_system/colormaps.md | pending |
| M05 | color_system/colormaps.md | CVD models, physical-Y guidance, custom-map caveats, rendering tips | color_system/colormaps.md | pending |
| O01 | color_system/color-class.md | constructors, conversions, mutable views, copy behavior, interpolation | color_system/color-class.md | pending |
| O02 | color_system/color-class.md | all interactive widgets, figures, examples, custom-map construction and registration | color_system/color-class.md | pending |
| R01 | color_system/design-rationale.md | 107-input construction statement and MCP count distinction | color_system/design-rationale.md | pending |
| R02 | color_system/design-rationale.md | four principles, A1, direct-OKLCH alternative, physical-Y compatibility rationale, gamut policy | color_system/design-rationale.md | pending |
| R03 | color_system/design-rationale.md | A2-A8 formulas, figures, fit values, gate table, and interpretations | color_system/design-rationale.md | pending |
| R04 | color_system/design-rationale.md | family anatomy, parameter table, metric layers, CVD critique and scores | color_system/design-rationale.md | pending |
| R05 | color_system/design-rationale.md | colormap grammar, scene table, cyclic behavior, limitations, reproducibility, typography rationale | color_system/design-rationale.md | pending |
| V01 | color_system/validation.md | complete executable command block and non-writing behavior | color_system/validation.md | pending |
| V02 | color_system/validation.md | report/HTML roles, atomic marker behavior, exit codes | color_system/validation.md | pending |
| V03 | color_system/validation.md | all 17 exact surfaces and isolated candidate-loading rationale | color_system/validation.md | pending |
| V04 | color_system/validation.md | independent oracle and every direct-32/full-256 quality rule | color_system/validation.md | pending |
| D01 | design_system/index.md | task table, catalog cards, counts, page navigation | design_system/index.md | pending |
```

- [ ] **Step 2: Add failing beginner-language tests**

Create `tests/test_docs_beginner_color_language.py` with this structure. The
exact phrases form the stable plain-language contract; normalize whitespace so
line wrapping does not matter.

```python
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _page(relpath: str) -> str:
    text = (ROOT / relpath).read_text(encoding="utf-8")
    return re.sub(r"\s+", " ", text)


def test_usage_guide_starts_with_a_task_chooser() -> None:
    text = _page("docs/usage_guide/colors.md")
    for phrase in (
        "one mark",
        "separate series or categories",
        "numeric values",
        "create or adjust a color",
    ):
        assert phrase in text
    assert text.index("What should I use?") < text.index("OKLab")


def test_usage_guide_defines_beginner_color_vocabulary() -> None:
    text = _page("docs/usage_guide/colors.md")
    for phrase in (
        "Hue is the color family",
        "Lightness describes the light-to-dark direction",
        "Chroma describes how colorful or muted a color is",
        "A palette is a finite list of colors",
        "A colormap turns numeric values into colors",
        "Sequential",
        "Diverging",
        "Cyclic",
        "Qualitative",
    ):
        assert phrase in text


def test_rationale_explains_the_decision_before_the_metrics() -> None:
    text = _page("docs/color_system/design-rationale.md")
    decision = text.index("The decision in plain language")
    metrics = text.index("The construction foundation")
    assert decision < metrics
    assert "A new, intentionally incompatible color system could use direct OKLCH" in text
    assert "compatibility promise, not a law of color theory" in text


def test_rationale_defines_the_four_rulers_in_plain_language() -> None:
    text = _page("docs/color_system/design-rationale.md")
    for phrase in (
        "larger ΔEOK means two colors are farther apart",
        "physical light output",
        "independent validation check",
        "text against a known background",
    ):
        assert phrase in text


def test_catalog_pages_lead_with_user_tasks() -> None:
    expected = {
        "docs/color_system/colors.md": "Use this page when you want to color one mark",
        "docs/color_system/palettes.md": "Use this page when separate series or categories need distinct colors",
        "docs/color_system/colormaps.md": "Use this page when numeric values should become colors",
        "docs/color_system/color-class.md": "Most plots do not need the Color class",
    }
    for relpath, phrase in expected.items():
        assert phrase in _page(relpath)


def test_validation_explains_maintainer_terms() -> None:
    text = _page("docs/color_system/validation.md")
    for phrase in (
        "This page is for release maintainers",
        "Open `index.html` for human review",
        "Automation reads `report.json`",
        "A 256-stop lookup table",
        "lower step CV means more even neighboring steps",
        "successful-run marker",
    ):
        assert phrase in text
    assert "generation commit marker" not in text


def test_accessibility_terms_include_meaning_not_only_acronyms() -> None:
    combined = " ".join(
        _page(path)
        for path in (
            "docs/usage_guide/colors.md",
            "docs/color_system/colormaps.md",
            "docs/color_system/design-rationale.md",
        )
    )
    for phrase in (
        "color-vision deficiency (CVD)",
        "Web Content Accessibility Guidelines (WCAG)",
        "ΔEOK is a color-distance ruler: larger means more different",
        "not a guarantee for every individual observer",
    ):
        assert phrase in combined
```

- [ ] **Step 3: Run the new tests and confirm the expected red state**

Run:

```bash
uv run pytest tests/test_docs_beginner_color_language.py -q --no-cov
```

Expected: the new tests fail because the current pages front-load jargon and
do not contain the approved task-first copy.

- [ ] **Step 4: Confirm the preservation baseline is green**

Run:

```bash
uv run pytest \
  tests/test_docs_count_claims.py \
  tests/test_docs_float_claims.py \
  tests/test_docs_asset_inventory.py \
  tests/test_docs_snippets.py \
  tests/test_docs_color_tokens.py -q --no-cov
```

Expected: PASS before prose edits. Save the pass counts in the task report.

- [ ] **Step 5: Review checkpoint**

Verify the inventory covers every current section and that the new tests fail
for missing beginner explanations rather than import or fixture errors. Do not
stage or commit.

---

### Task 2: Turn the Usage Guide into the Beginner Path

**Files:**
- Modify: `docs/usage_guide/colors.md:1-247`
- Modify: `docs/design_system/index.md:1-75`
- Modify: `docs/superpowers/specs/assets/2026-07-17-beginner-friendly-color-docs/claim-inventory.md`
- Test: `tests/test_docs_beginner_color_language.py`

**Interfaces:**
- Consumes: Task 1's stable vocabulary and inventory IDs U01-U04/D01.
- Produces: the task chooser and compact conceptual vocabulary linked by every catalog page.

- [ ] **Step 1: Add the beginner chooser before catalog vocabulary**

Keep the existing URL and title, then add this structure before the current
prefix inventory:

```markdown
## What should I use?

| If you need to... | Use... | Matplotlib surface |
|---|---|---|
| color one mark, line, or area | a named color token | `color="dc.blue6"` |
| color separate series or categories | a palette | `dm.set_colors(...)` |
| turn numeric values into colors | a colormap | `cmap="dc.aurora"` |
| create or adjust a color yourself | the `Color` class | `dm.oklch(...)` |
```

Follow it with a `tip` stating that most readers only need the first three
rows and can ignore the color-space math.

- [ ] **Step 2: Add a compact “Four ideas” definition list**

Use MyST's enabled definition-list syntax. Include the exact tested opening
sentences for Hue, Lightness, and Chroma, then define contrast, palette,
colormap, sequential, diverging, cyclic, and qualitative. Each definition must
include a chart example rather than only a formal definition.

- [ ] **Step 3: Reorder the existing usage content without deleting it**

Use this order:

1. chooser and definitions;
2. named colors and seven prefixes;
3. palette selection and the current manual-cycle example;
4. `Color` and interpolation, including both existing widgets;
5. discovery utilities;
6. colormaps;
7. accessibility checklist;
8. See also.

Retain every current Python fence, raw HTML widget, prefix row, rough `oc.*`
mapping, and API link. Replace the dense “10 DeltaEOK-equalized steps” passage
with a short quality summary and a descriptive link to Design rationale.

- [ ] **Step 4: Add the beginner accessibility checklist**

Add an `important` box containing all five rules from spec section 9. Expand
CVD as “color-vision deficiency (CVD)” and WCAG as “Web Content Accessibility
Guidelines (WCAG)” before using either acronym.

- [ ] **Step 5: Simplify the Design System overview route**

Add a `tip` above the task table that points new readers to
`../usage_guide/colors.md`. Rewrite the four color-card summaries in task
language while retaining the exact count phrases pinned by
`test_docs_count_claims.py`, including `43 perceptually-designed colormaps`.
Do not alter the hidden toctree.

- [ ] **Step 6: Mark inventory rows U01-U04 and D01 preserved**

Update their destination cells if content moved within the page and set status
to `preserved`. Do not mark a row preserved until every listed example/widget
is still present.

- [ ] **Step 7: Run the task tests**

Run:

```bash
uv run pytest \
  tests/test_docs_beginner_color_language.py \
  tests/test_docs_snippets.py \
  tests/test_docs_color_tokens.py \
  tests/test_docs_count_claims.py -q --no-cov
```

Expected: usage/overview beginner tests pass; rationale/catalog/validation
tests may still fail because later tasks own them. All pre-existing tests pass.

- [ ] **Step 8: Review checkpoint**

Compare U01-U04/D01 against the edited pages and confirm no code fence, widget,
prefix, option, or link disappeared. Do not stage or commit.

---

### Task 3: Make Colors, Palettes, and Colormaps Task-First

**Files:**
- Modify: `docs/color_system/colors.md:1-113`
- Modify: `docs/color_system/palettes.md:1-158`
- Modify: `docs/color_system/colormaps.md:1-219`
- Modify: `docs/superpowers/specs/assets/2026-07-17-beginner-friendly-color-docs/claim-inventory.md`
- Test: `tests/test_docs_beginner_color_language.py`

**Interfaces:**
- Consumes: the chooser and stable definitions from Task 2.
- Produces: task-first token, palette, and colormap reference pages with all catalog evidence preserved.

- [ ] **Step 1: Rewrite the Colors opening**

Begin with the exact sentence `Use this page when you want to color one mark,
line, area, label, or other plot element.` Define a token as one named color
string and a family step as one swatch in a related ramp. Move “How to read the
labels” immediately after a minimal `color="dc.blue6"` example. Keep the 20/19
family count phrases required by count tests.

Replace the current construction-heavy family paragraph with an **In plain
English** tip: adjacent numbers are designed to progress more consistently,
and ordered ramps also keep a stable light-to-dark output order. Link the exact
metrics to Design rationale and Validation.

- [ ] **Step 2: Rewrite the Palettes opening and chooser**

Begin with the exact sentence `Use this page when separate series or categories
need distinct colors.` Define palette, qualitative, sequential, and diverging
before the explorer. Keep the explorer, all apply examples, chooser rows,
family list, curated membership table, API option table, and migration note.

Move the Octave metric paragraph into a `Technical detail` dropdown without
changing its pinned values or model attribution. Precede it with a plain rule:
Octave is the default for unrelated series; Octave Print trades one chromatic
slot for dark gray so grayscale output separates more reliably.

- [ ] **Step 3: Rewrite the Colormaps opening and chooser**

Begin with the exact sentence `Use this page when numeric values should become
colors.` Define a colormap and distinguish `color=` from `cmap=` before the
inventory arithmetic. Move Quick start and Choosing a map ahead of the deep
catalog mechanics while preserving all headings/anchors needed by links.

Define map types in plain English:

```markdown
- **Sequential:** low to high along one ordered path.
- **Diverging:** two sides meet at a meaningful center such as zero.
- **Cyclic:** the end joins the beginning, as with 0° and 360°.
- **Qualitative:** separate colors for labels that have no numeric order.
```

Keep the complete 43-map table and the exact phrases required by inventory and
count tests: 43 continuous, 13 qualitative, 56 Model B family records, 99
registrations, and “Explore the 43-map continuous v5 catalog.” The internal
labels may live in a `Technical detail` dropdown, but cannot disappear.

- [ ] **Step 4: Explain quality and accessibility in ordinary language**

Before the aurora/viridis values, state that `ΔEOK is a color-distance ruler:
larger means more different`, and that lower CV means more even neighboring
steps. Keep `0.063` and `0.086` with
the same protocol caveat. Expand color-vision deficiency (CVD) and describe
protan/deutan as common red-green classes and tritan as the rarer blue-yellow
class. Preserve Machado/BVM attribution and the warning that simulations are
not guarantees for individuals.

- [ ] **Step 5: Preserve custom-map and rendering caveats**

Keep both custom-colormap cards and code fences. Rewrite “not automatically
gated” as a practical warning: a smooth-looking gradient has not automatically
passed the shipped catalog's ordering, step-evenness, or accessibility checks.
Retain all `vmin`, `vmax`, `_r`, outline, and symmetric-limit tips.

- [ ] **Step 6: Reconcile inventory rows C01-C03, P01-P03, and M01-M05**

Set each row to `preserved` only after checking the source facts against their
new location. Record cross-page destinations only for genuinely maintainer-only
details, and leave a descriptive link at the original page.

- [ ] **Step 7: Run catalog regression tests**

Run:

```bash
uv run pytest \
  tests/test_docs_beginner_color_language.py \
  tests/test_docs_count_claims.py \
  tests/test_docs_float_claims.py \
  tests/test_docs_asset_inventory.py \
  tests/test_docs_snippets.py \
  tests/test_docs_color_tokens.py \
  tests/test_colormap_explorer_taxonomy.py \
  tests/test_palette_family_taxonomy.py -q --no-cov
```

Expected: catalog and usage beginner tests pass; rationale/validation tests may
remain red. Every existing inventory, numeric claim, snippet, and explorer test
passes.

- [ ] **Step 8: Review checkpoint**

Review the explorer/table/widget boundaries in source and rendered Markdown.
Confirm no name, table row, raw HTML include, example, or numeric qualifier was
dropped. Do not stage or commit.

---

### Task 4: Give the Color Class an Optional Beginner Entry Point

**Files:**
- Modify: `docs/color_system/color-class.md:1-456`
- Modify: `docs/superpowers/specs/assets/2026-07-17-beginner-friendly-color-docs/claim-inventory.md`
- Test: `tests/test_docs_beginner_color_language.py`

**Interfaces:**
- Consumes: Task 2's hue/lightness/chroma vocabulary.
- Produces: a simple construct-adjust-export path followed by the complete advanced API reference.

- [ ] **Step 1: Rewrite the opening without changing API content**

Begin with `Most plots do not need the Color class: a named token, palette, or
colormap is usually enough.` Then show one short existing-API path:

```python
color = dm.oklch(0.7, 0.15, 150)
color.oklch.C *= 1.2
hex_value = color.to_hex()
```

Explain that `L` is the model's lightness coordinate, `C` controls colorful
versus muted, and `h` chooses the hue angle. Preserve the current warning that
these spaces improve color math but do not guarantee equal perception.

- [ ] **Step 2: Clarify OKLab versus OKLCH before internals**

Add a note saying they are two coordinate views of the same underlying model,
not two competing construction rules. Use a map analogy: OKLab's `a`/`b` are
rectangular axes; OKLCH converts those axes into distance-from-center `C` and
angle `h`. Keep the existing color-space table and all constructor/conversion
examples.

- [ ] **Step 3: Preserve every advanced surface**

Keep the universal constructor widget, view-object operations, mutation/copy
semantics, interpolation figure and widget, custom colormap builder, sequential
and diverging examples, registration instructions, quick reference, and See
also links. Put the statement about ungated custom endpoints in a Technical
detail dropdown and link to Validation.

- [ ] **Step 4: Reconcile inventory rows O01-O02**

Verify every heading and embedded raw HTML block still exists. Mark both rows
`preserved` with their final section destinations.

- [ ] **Step 5: Run the Color-class documentation tests**

Run:

```bash
uv run pytest \
  tests/test_docs_beginner_color_language.py \
  tests/test_docs_snippets.py \
  tests/test_docs_color_tokens.py \
  tests/test_docs_design_ssot.py -q --no-cov
```

Expected: the Color-class beginner test and all existing widgets/snippets pass;
only later rationale/validation beginner tests may remain red.

- [ ] **Step 6: Review checkpoint**

Compare O01-O02 against the edited page and confirm the new entry point did not
replace any constructor, conversion, mutation, interpolation, or registration
instruction. Do not stage or commit.

---

### Task 5: Layer the Design Rationale from Decision to Evidence

**Files:**
- Modify: `docs/color_system/design-rationale.md:1-535`
- Modify: `docs/superpowers/specs/assets/2026-07-17-beginner-friendly-color-docs/claim-inventory.md`
- Test: `tests/test_docs_beginner_color_language.py`
- Test: `tests/test_docs_float_claims.py`

**Interfaces:**
- Consumes: the approved four-layer metric model and claim inventory R01-R05.
- Produces: the same evidence page with an understandable first reading and optional detail layers.

- [ ] **Step 1: Add the plain-language decision before A1**

After the page introduction and before “Four principles,” add:

```markdown
:::{tip}
**The decision in plain language**

dartwork-mpl builds color paths in OKLab/OKLCH. Under this ruler, larger ΔEOK
means two colors are farther apart, so the compiler can place adjacent steps
more evenly.

The shipped catalog also keeps a normalized physical light output fixed where
its compatibility contract requires it. A new, intentionally incompatible
color system could use direct OKLCH `L` and choose different output rules. The
extra Y lock is a compatibility promise, not a law of color theory.

CIELAB and color-vision simulations do not construct the colors; they check the
finished result. WCAG contrast answers a separate question: whether text is
readable against a known background.
:::
```

Keep the exact direct-OKLCH unlocked-diagnostic caveat later in A1.

- [ ] **Step 2: Explain the four rulers before formulas**

Add a note that distinguishes actual OKLab `L`, `neutral_tone`, physical
`relative_y`, and WCAG contrast luminance. State black/reference-white bounds
for `relative_y`, and state that neither Y nor OKLab `L` is a universal model
of perceived brightness. Define DeltaEOK and DeltaE00 as construction and
independent-validation distance rulers respectively.

- [ ] **Step 3: Add local reading aids without deleting evidence**

Add these callouts at first meaningful use:

- gamut mapping without jargon: sRGB cannot display every OKLCH request, so
  reduce `C` while retaining requested `L` and `h`; bisection repeatedly halves
  the search range;
- A2-A8 reading guide: seven practical questions matching floors, chroma,
  drift, step placement, gray, release gates, and heatmap ranges;
- map vocabulary: sequential, diverging, cyclic, categorical, seam,
  isoluminant;
- statistics: CV lower means more even, R-squared 1 means perfect model fit,
  and wRMSE is weighted fit error;
- CVD: protan/deutan red-green classes, tritan blue-yellow class, and the
  model-not-guarantee caveat;
- LUT: lookup table, the ordered 256 colors shipped behind a continuous map.

- [ ] **Step 4: Rewrite dense prose paragraph by paragraph**

Split paragraphs that currently introduce more than one metric layer. Keep all
axiom statements, formulas, values, figures, alt text, tables, family names,
provenance, citations, colormap scenes, cyclic notes, limitations, reproduction
commands, and typography rationale. Correct only readability issues such as:

- “Colors are not stored” -> “Colors are not authored as hand-picked tables;
  they are computed and stored as generated outputs.”
- “generation inputs/oracles/topology” -> explain the practical effect before
  retaining the maintainer term.
- every numerical comparison -> add whether higher/lower is better and the
  limit of the inference.

Do not move or reformat the pinned numeric phrases unless the corresponding
regex tests are deliberately updated to continue checking the same claim.

- [ ] **Step 5: Reconcile inventory rows R01-R05**

Perform a heading-by-heading comparison with the original claim list. Mark
each row `preserved`; if text moved into a dropdown, record its heading in the
destination cell.

- [ ] **Step 6: Run rationale-specific tests**

Run:

```bash
uv run pytest \
  tests/test_docs_beginner_color_language.py \
  tests/test_docs_count_claims.py \
  tests/test_docs_float_claims.py \
  tests/test_docs_theory_figures.py \
  tests/test_drift.py -q --no-cov
```

Expected: rationale beginner tests and all pinned fact/figure/drift tests pass;
only Validation beginner requirements may remain red.

- [ ] **Step 7: Review checkpoint**

Review R01-R05 against the full diff. Search for every formula, figure
directive, table heading, quoted metric, named model, and compatibility caveat
from the original. Do not stage or commit.

---

### Task 6: Explain Validation as a Maintainer Workflow

**Files:**
- Modify: `docs/color_system/validation.md:1-129`
- Modify: `docs/superpowers/specs/assets/2026-07-17-beginner-friendly-color-docs/claim-inventory.md`
- Test: `tests/test_docs_beginner_color_language.py`
- Test: `tests/test_docs_asset_inventory.py`

**Interfaces:**
- Consumes: the unchanged build/comparison commands and inventory V01-V04.
- Produces: a maintainer page whose artifacts, isolation, exactness, and quality metrics are understandable without prior release-system knowledge.

- [ ] **Step 1: Identify the audience and success condition**

Immediately after the title add a tip beginning `This page is for release
maintainers.` Say that ordinary users should start with Colors or Colormaps.
Define a successful run as the live compiler reproducing published names,
orders, colors, and discrete selections; `passed` true; zero exact mismatches;
and an empty quality-violation list.

- [ ] **Step 2: Explain the command block and artifacts**

Keep the complete shell block byte-for-byte in meaning and order. Follow it
with a numbered note explaining: rebuild authority to a temporary file,
byte-compare it, check generated Python, compare frozen output to the live
compiler, then verify explorers/theory figures.

Add the exact sentences `Open \`index.html\` for human review.` and
`Automation reads \`report.json\`.` Explain “machine authority” in ordinary
language while retaining the exact phrase required by
`test_docs_asset_inventory.py`: `` `report.json` is the machine authority ``.

- [ ] **Step 3: Explain atomic completion and exit codes**

Replace every “generation commit marker” occurrence with “successful-run
marker.” Explain that writing JSON last prevents an interrupted run from
leaving an old green result next to new partial output. Keep all three exit
codes and their distinctions unchanged.

- [ ] **Step 4: Explain exact comparison and isolation**

Before the 17-item list, define a surface as one public group being compared
and state that exact means identical names, order, hex values, registrations,
and frozen indices—not visually close. Define `A 256-stop lookup table` as the
ordered list behind a continuous map.

Before private-alias mechanics, explain the purpose: the candidate must not
grade itself by importing the stored expected answer. Keep every module and
registry detail after that explanation.

- [ ] **Step 5: Explain the quality oracle and metrics**

Define oracle as an independent reference implementation checked against
published examples. Add a note defining direct-32, full-256, step CV, span,
monotonic floor, quantization, and regression. Include the exact phrase `lower
step CV means more even neighboring steps`. Keep every threshold and baseline
rule unchanged.

- [ ] **Step 6: Reconcile inventory rows V01-V04**

Confirm all commands, artifact semantics, exit cases, 17 surfaces, isolation
details, oracle pins, and quality rules remain. Mark all rows `preserved`.

- [ ] **Step 7: Run Validation and full beginner-contract tests**

Run:

```bash
uv run pytest \
  tests/test_docs_beginner_color_language.py \
  tests/test_docs_asset_inventory.py \
  tests/test_docs_design_ssot.py \
  tests/test_docs_count_claims.py \
  tests/test_docs_float_claims.py -q --no-cov
```

Expected: all beginner-language and existing validation/fact tests pass.

- [ ] **Step 8: Review checkpoint**

Compare V01-V04 to the edited page, including exact command strings and every
exit-code condition. Do not stage or commit.

---

### Task 7: Complete the Preservation, Sphinx, and Rendered-Page Audit

**Files:**
- Modify: `docs/superpowers/specs/assets/2026-07-17-beginner-friendly-color-docs/claim-inventory.md`
- Review: all files changed by Tasks 1-6
- Produce locally: `docs/_build/html/`

**Interfaces:**
- Consumes: every page and inventory row from Tasks 1-6.
- Produces: a fully reconciled no-loss audit, green documentation suite, and rendered pages ready for user inspection.

- [ ] **Step 1: Close the claim inventory**

Require every row to have a descriptive destination and status `preserved`.
Add a final summary stating that no unique claim was removed and listing any
duplicate wording that was consolidated. Search for unfinished states:

```bash
rg -n "\| pending \|" \
  docs/superpowers/specs/assets/2026-07-17-beginner-friendly-color-docs/claim-inventory.md
```

Expected: no output.

- [ ] **Step 2: Run the complete focused documentation suite**

Run:

```bash
uv run pytest \
  tests/test_docs_beginner_color_language.py \
  tests/test_docs_count_claims.py \
  tests/test_docs_float_claims.py \
  tests/test_docs_asset_inventory.py \
  tests/test_docs_design_ssot.py \
  tests/test_docs_snippets.py \
  tests/test_docs_color_tokens.py \
  tests/test_docs_theory_figures.py \
  tests/test_colormap_explorer_taxonomy.py \
  tests/test_palette_family_taxonomy.py \
  tests/test_drift.py -q --no-cov
```

Expected: all selected tests pass.

- [ ] **Step 3: Run static checks**

Run:

```bash
uv run ruff check tests/test_docs_beginner_color_language.py
uv run ruff format --check tests/test_docs_beginner_color_language.py
git diff --check
uv lock --check
```

Expected: all commands exit 0 and no diff-check output appears.

- [ ] **Step 4: Build Sphinx with warnings as errors**

Use the fast prose build while retaining the existing generated figures:

```bash
PLOT_GALLERY=0 uv run sphinx-build \
  -b html -W --keep-going \
  docs docs/_build/html \
  -w docs/build.log
```

Expected: `build succeeded`, with no missing reference, malformed directive,
or toctree warning. If the build refreshes unrelated tracked example outputs,
revert only those known build products and preserve every intended docs edit.

- [ ] **Step 5: Review the rendered reading path**

Serve the built tree and inspect these exact pages at desktop and narrow
widths:

```bash
uv run python -m http.server 8461 --directory docs/_build/html
```

- `/usage_guide/colors.html`
- `/design_system/index.html`
- `/color_system/colors.html`
- `/color_system/palettes.html`
- `/color_system/colormaps.html`
- `/color_system/color-class.html`
- `/color_system/design-rationale.html`
- `/color_system/validation.html`

Confirm the task chooser appears before jargon, admonitions render with titles
and dropdown behavior, tables/widgets are not clipped, and technical evidence
is still reachable without broken anchors.

- [ ] **Step 6: Request an independent content-preservation review**

Give the reviewer the original diff base, the claim inventory, and the final
pages. Ask specifically for dropped numbers, formulas, caveats, protocol names,
examples, figures, API guidance, or changed technical meaning—not only style.
Resolve every finding and rerun the focused tests.

- [ ] **Step 7: Final worktree checkpoint**

Confirm the feature worktree contains only intended color-system and
beginner-doc changes, the user's main worktree still contains all pre-existing
SVG/HTML/PNG/PDF edits, and neither worktree is staged or committed. Present
the claim inventory, rendered URLs, test results, and any remaining risk to the
user for approval.
