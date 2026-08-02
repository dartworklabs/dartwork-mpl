# Beginner-friendly color documentation design

Date: 2026-07-17  
Status: approved for implementation  
Scope: current public Sphinx documentation for the dartwork-mpl color system

## 1. Problem

The color documentation is technically accurate, but it often introduces the
implementation vocabulary before it tells readers what practical question is
being answered. A reader can meet OKLab, OKLCH, DeltaEOK, `relative_y`,
CIELAB, DeltaE00, CVD, and WCAG in one paragraph without knowing what any of
those terms helps them decide.

The documentation should remain rigorous while becoming readable by someone
who has never studied color theory. The reader should first understand the
plain-language conclusion, then choose whether to read the measurement or
implementation detail.

## 2. Goals

1. Make every public color page useful without prior color-theory knowledge.
2. Lead with the reader's task and the practical conclusion rather than the
   internal model or validation protocol.
3. Define every specialist term or acronym at first meaningful use.
4. Explain construction, modeled output ordering, model-specific validation,
   and pairwise text contrast as four different jobs.
5. Preserve all current technical claims, exact catalog facts, code examples,
   interactive explorers, and compatibility contracts.
6. Keep advanced evidence available without forcing every reader through it.

### Content-preservation invariant

This is a readability refactor, not a content reduction. Every unique factual
claim in the current public color documentation must remain available after
the rewrite.

Allowed changes are limited to:

- reordering a conclusion before its evidence;
- splitting a dense sentence or paragraph;
- adding a plain-language paraphrase, definition, example, or callout;
- placing implementation detail in an adjacent technical-detail dropdown;
- consolidating genuinely duplicate wording; and
- moving maintainer-only detail to Design rationale or Validation when the
  original page retains a direct, descriptive link to it.

The rewrite must not discard or weaken formulas, measured values, thresholds,
catalog counts, protocol/model names, citations, provenance, compatibility
caveats, code examples, interactive widgets, figures, or API behavior. If a
sentence is simplified, its technical qualifiers must remain in the same
paragraph, an adjacent callout, or the directly linked evidence section.

## 3. Non-goals

- Do not change color generation, validation, APIs, catalog contents, or
  rendered color output.
- Do not create a second standalone glossary or color-primer page.
- Do not remove formulas, thresholds, provenance, or maintainer procedures
  that are needed to reproduce or audit the system.
- Do not rewrite historical v5 specifications beyond their existing
  superseded-model banners.
- Do not translate the English documentation into Korean or make it bilingual.

## 4. Information architecture

The existing pages keep their URLs but receive clearer roles.

| Page | Reader question | Role |
|---|---|---|
| Usage Guide: Colors and Colormaps | “What should I use?” | Beginner learning path and compact vocabulary |
| Colors | “How do I color one thing?” | Named token and family reference |
| Palettes | “How do I color several separate series or categories?” | Finite color-list chooser and reference |
| Colormaps | “How do I map numeric values to color?” | Continuous-map chooser and reference |
| Color class | “How do I create or adjust a color myself?” | Optional advanced/custom workflow |
| Design rationale | “Why was the system designed this way?” | Plain-language decisions followed by technical evidence |
| Validation | “How does a maintainer prove it still works?” | Release protocol, metrics, and exact compatibility evidence |

`docs/usage_guide/colors.md` becomes the primer instead of adding another page.
The Design System overview links readers to the appropriate task before it
uses catalog or measurement vocabulary. Root navigation remains unchanged.

## 5. Vocabulary contract

The following nouns have one stable meaning across the pages.

- **token:** one named color string used with `color=`.
- **swatch** or **step:** one color within a family or palette.
- **family:** a related source of colors that may provide several forms.
- **ramp:** an ordered light-to-dark or low-to-high series of related colors.
- **palette:** a finite list used for separate categories or plotted series.
- **colormap:** a rule that converts numeric values into colors.
- **sequential:** one ordered path from low to high.
- **diverging:** two ordered arms meeting at a meaningful center.
- **cyclic:** a path whose last color joins its first, such as angle or phase.
- **qualitative/categorical:** separate colors for labels with no numeric order.

Color-science terms receive a direct interpretation, not only an expanded
name:

- **OKLab/OKLCH:** two views of the same perceptual color model. OKLab is
  convenient for color math; OKLCH exposes lightness `L`, colorfulness `C`,
  and hue angle `h` for authoring.
- **DeltaEOK:** OKLab color distance; a larger number means the colors are more
  different under that ruler.
- **modeled `relative_y`:** relative CIE Y calculated from nominal D65 sRGB,
  with nominal black at 0 and nominal reference white at 1 under the pinned
  software convention. It is not a display measurement, perceived brightness,
  or OKLab `L`.
- **CIELAB/DeltaE00:** a standardized color model and difference formula,
  retained here as a model-specific regression check rather than a
  construction input.
- **CVD:** color-vision deficiency. Simulations estimate how distinctions may
  change for common red-green or rarer blue-yellow deficiency classes.
- **WCAG contrast:** a pairwise contrast ratio for a specified foreground and
  background; it is not the same calculation as the catalog's modeled-output
  contract and does not by itself establish legibility.
- **gamut mapping:** adapting a requested color that the target sRGB gamut
  cannot represent. For in-range OKLCH lightness and non-negligible chroma,
  the pre-quantization search reduces chroma while holding `L` and `h`; near
  neutral, out-of-range achromatic inputs, final clamping, and 8-bit
  serialization have explicitly documented limits.

## 6. Writing rules

1. Put the conclusion before its metric or formula.
2. Prefer concrete verbs and examples: “larger means more different,” “lower
   means more even,” and “the last color joins the first.”
3. Expand an acronym on first use and explain why the reader should care.
4. Keep one conceptual job per paragraph. Do not introduce construction,
   output compatibility, validation, and text contrast in one dense sentence.
5. Replace internal vocabulary such as “Model B,” “canonical,” “frozen
   replay,” “LUT,” and “topology gate” in beginner-facing prose. Keep it only
   where the implementation or release process requires it, with a definition.
6. Do not call OKLab or any palette perfectly perceptually uniform.
7. Describe modeled relative Y as a nominal-sRGB calculation, not perceived
   brightness, OKLab `L`, or a measurement of a particular device.
8. Keep numerical claims paired with an interpretation of whether higher or
   lower is desirable and what the comparison does—and does not—prove.
9. Use links to evidence instead of repeating detailed protocols in catalog
   pages.
10. Keep code examples focused on the current page's task.

## 7. Explanation-box pattern

Use existing MyST directives; no new CSS or JavaScript is required.

- `:::{tip}` titled or opened as **In plain English** for the practical
  conclusion a beginner should remember.
- `:::{note}` titled or opened as **What this term means** when a local
  definition prevents ambiguity.
- `:::{admonition} Technical detail` with `:class: dropdown` for formulas,
  protocol names, historical scores, or implementation mechanics that should
  remain available but need not interrupt the first reading.
- `:::{important}` only for choices that can make a chart misleading, such as
  using a categorical palette for ordered values or relying on hue alone.

Callouts supplement the prose; they must not become the only place where a
page states its main conclusion.

## 8. Page-level changes

### Usage Guide

Start with a four-way chooser: one mark -> token, separate series -> palette,
numeric field -> colormap, custom manipulation -> `Color`. Add a compact
definition list for hue, lightness, chroma, contrast, and the map types. Keep
one beginner accessibility checklist. Move catalog internals and detailed
validation language behind links to the reference/evidence pages.

### Colors, Palettes, and Colormaps

Start each page with “Use this when,” a minimal example, and a chooser before
catalog arithmetic or construction vocabulary. Define `color=` versus `cmap=`
prominently. Replace dense metric paragraphs with a plain quality summary and
links to Design rationale or Validation. Retain exact counts and names where
they serve the catalog.

### Color class

Label this as optional for most plots. Keep the first path simple:
construct -> adjust -> export. Explain OKLab and OKLCH before showing their
coordinate details. Put storage internals and validation exclusions later or
in technical notes.

### Design rationale

Add an early “decision in plain language” box that answers the central
question: a new incompatible system could use direct OKLCH `L`; the shipped
catalog keeps a modeled-relative-Y lock only to preserve its exact output and
nominal topology contracts. Explain the four different rulers before using
them.

Add local boxes for brightness-like coordinates, gamut mapping, the A2-A8
reading guide, map vocabulary, DeltaE metrics, and CVD classes. Rewrite dense
sentences throughout, but retain the formulas, figures, measured values, and
reproducibility evidence.

### Validation

State immediately that this is maintainer documentation and send ordinary
users to the chooser pages. Explain the success criteria, what each command
checks, which artifact humans should open, what “exact” means, why candidate
loading is isolated, and how to read direct-32/full-256/CV/span terminology.
Use “successful-run marker” instead of the ambiguous “generation commit
marker.”

### Design System overview

Rewrite card summaries in task language and add a compact “new to color?”
route to the Usage Guide. Do not change the root toctree or add another
sidebar entry.

## 9. Accessibility guidance

The beginner checklist must state:

1. Do not rely on hue alone for critical distinctions.
2. For ordered values, choose a map that still changes from light to dark.
3. For critical grayscale or print output, add labels, contours, markers,
   hatching, or line styles.
4. WCAG contrast applies to text against a known background; it does not
   certify an entire palette.
5. CVD simulation is a useful model-based check, not a guarantee for every
   individual observer.

## 10. Verification

- Add documentation tests that require the beginner definitions and preserve
  the construction/output/validation/WCAG separation.
- Inventory existing unique claims before editing and reconcile them after the
  rewrite. Record any relocation so reviewers can find the new destination
  without comparing every sentence manually.
- Keep all existing exact count, float-claim, asset, explorer, and drift tests
  green.
- Run Ruff on any changed Python tests.
- Build Sphinx with warnings as errors. A fast `PLOT_GALLERY=0` build is enough
  for prose and cross-reference verification; the existing full visual build
  remains the reference for generated figures.
- Review the rendered Usage Guide, Colors, Palettes, Colormaps, Color class,
  Design rationale, and Validation pages at desktop and narrow widths.
- Run an independent content-preservation review that looks specifically for
  dropped numbers, formulas, caveats, protocol names, examples, figures, or
  API guidance rather than only reviewing tone and layout.

## 11. Acceptance criteria

The work is complete when:

1. A reader can choose between a token, palette, colormap, and custom `Color`
   before learning any color-science metric.
2. OKLab, OKLCH, DeltaEOK, `relative_y`, CIELAB, DeltaE00, CVD, WCAG,
   gamut, sequential, diverging, cyclic, and qualitative are explained in
   plain English at first meaningful use or through an immediately adjacent
   link/callout.
3. The direct-OKLCH-versus-Y-lock decision is visible near the top of Design
   rationale and clearly identified as compatibility rather than color-theory
   necessity.
4. Beginner-facing pages no longer front-load internal compiler or validation
   vocabulary.
5. Advanced readers can still find every formula, threshold, exact catalog
   count, historical metric, and release command.
6. A before/after claim inventory has no unexplained missing unique claim;
   duplicate wording may be consolidated only when its meaning remains at an
   obvious destination.
7. Existing documentation contracts and Sphinx warnings-as-errors build pass.
