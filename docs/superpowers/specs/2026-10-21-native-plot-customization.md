# Native plot customization guidance

Status: bounded correction directed by the user's explicit 2026-10-21 contract.
Base: PR512 `639f73ddfbe0b75ae3e032ee2a12f0545639f853` (main `13932f54`).
This records the requested agent behavior and a bounded source investigation;
it introduces no runtime architecture or additional approval decision.

## User requirements

- Users describe plots/edits in ordinary language; they need not write plotting code.
- Native matplotlib properties remain accessible: line width/color/custom dash
  and dot spacing, spines, ticks, tick labels, axis labels, grids, chart types
  and layout ratios. The 18 bundled templates are starters, not a finite API.
- Presets provide defaults. Explicit scoped overrides, including absolute
  point sizes/widths and hex/native colors, take priority.
- Example: report style with only axis labels one step larger preserves
  tick labels, legend, title, colors, data and canvas.
- Distinguish preset-relative offsets from current-relative deltas and exact
  absolute values. Repeated “one more” increments the retained current value.
- Resolve the intended panel/series/artist; ask one short question only when
  target ambiguity materially affects the result. Change only requested properties.
- Apply the preset before retained overrides and local artist changes. Preserve
  unrelated styling, selected preset, data and its transformation policy.
- Choose unspecified defaults from data, purpose, panel density and categorical
  text; reuse the recommender/templates without universal-ratio or palette mandates.

## Source evidence and exploratory limits

The completed source audit found the existing runtime already accepts native
Python/Figure customization. At the base commit:

- `src/dartwork_mpl/mcp/execution.py:138-161` gates only critical lint;
  `:181-210` executes Python and extracts a native Figure.
- `src/dartwork_mpl/asset/prompt/00-index.md:58-67`, `01-policy.md:161-190`
  and `mcp/prompts.py:142` nevertheless prohibit literal sizes/widths.
- `02-anti-patterns.yaml:334-359` warns on literal sizes/widths;
  `src/dartwork_mpl/lint.py:843-915` does not auto-rewrite those values.
- `src/dartwork_mpl/scale.py:31-88`: fs/lw use global rcParams bases, not
  current artists or role-specific defaults; fs +1 is +1 pt and fw +1 is +100.
- `src/dartwork_mpl/style.py:349-372,443-448` resets preset values before
  keyword overrides, so retained intent must be reapplied in order.

This repair changes guidance and advisory text only. It does not claim every
native property, backend, chart type or language-model response was tested.
Dash lengths normally scale with linewidth; exact physical lengths require
local `lines.scale_dashes=False` before line creation and rescaling setters. Representative rendered
PoCs are reviewed separately before product integration; no merge/deploy occurs here.

## Scope and non-goals

Update mirrored agent entry points, bundled policy/index/recipes, quickstart,
MCP prompt/info human-readable strings and generated llms-full authority.
Keep literal-size/width warning IDs, severity, detectors and fixer semantics;
explain advisories without hiding warnings or erasing explicit values.
Use native getters, properties(), help or official installed-version docs for
property discovery. No NLP parser, finite property schema, matplotlib wrapper,
new MCP tool/signature, dependency, test, CI gate, palette or preset changes.
No ADR lock or shipped-color digest is changed.

## Three bounded tasks and verification

- [x] Task 1: Correct precedence, targeting, preservation, units and warning
  wording across entry points and prompt surfaces; add a few native recipes.
  Verify the diff stays within the listed files and Python AST changes are strings only.
- [x] Task 2: Regenerate llms-full with existing composition logic. Run existing
  focused prompt/lint/drift/MCP checks and Ruff; do not add tests or run the full suite.
- [x] Task 3: Build a wheel without installation; verify changed bundled-member
  bytes, mirrored entry points, unchanged detector/fixer metadata and all-base
  tracked-file hashes. Preserve the patch/SHA manifest and review rendered PoCs
  separately. Record results and limitations without claiming universal model compliance.

Local completion: the three tasks passed the recorded focused checks and wheel
byte verification; representative PoCs were reviewed separately by the parent.
Hosted CI remains pending. These results do not establish universal property,
backend or language-model compliance.
