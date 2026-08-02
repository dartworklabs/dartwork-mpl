# Color rationale accuracy design

Date: 2026-07-21
Status: approved for implementation
Scope: public color-system rationale, directly duplicated claims, generated
theory-figure labels, and documentation contract tests

## 1. Problem

The current Design rationale has the right central architecture—OKLab/OKLCH
construction, a separately named relative-Y compatibility target, and
downstream CIELAB/CVD diagnostics—but it overstates several scientific claims
and describes some capabilities and release gates that the shipped system does
not have.

The document currently mixes four kinds of statement:

1. colorimetric facts;
2. project-specific compatibility contracts;
3. design and art-direction choices; and
4. measurements of the current catalog.

When those categories are presented with the same certainty, a descriptive fit
can look like psychophysical evidence, a house style can look like a law of
vision, and a regression diagnostic can look like an accessibility
certification.

## 2. Decision

Adopt an evidence-tier rewrite. Keep the existing beginner-first structure and
all valid technical detail, while making every consequential claim identifiable
as one of the following:

- **Design choice** — what dartwork-mpl intentionally optimizes.
- **Implementation** — what the current compiler or API actually does.
- **Evidence** — a reproducible measurement of the shipped catalog.
- **Limits** — the conditions under which the statement should not be
  generalized.

The A2–A8 sections remain recognizable, but they are called design rules rather
than laws of color vision. They need not use four literal subheadings when a
short paragraph communicates the same distinction clearly.

## 3. Scientific language contract

### 3.1 Construction and distance

- Describe OKLab as a perceptually oriented working space, not a perfectly
  uniform or universal appearance model.
- Describe OKLCH as the cylindrical representation of the same coordinates.
- State that dartwork-mpl reports `DeltaEOK x 100`, equal to 100 times raw
  Euclidean Oklab distance. Scaling changes displayed units, not rankings,
  arc-length placement, or coefficients of variation.
- Scope DeltaEOK equalization to the path kinds that actually use it.

### 3.2 Relative Y and WCAG

- Replace “physical light output” with “modeled relative CIE Y calculated from
  nominal D65 sRGB,” or the shorter “modeled relative Y” after first use.
- State that this value is not a measurement of a particular display.
- Explain that catalog `relative_y` and WCAG relative luminance are closely
  related decoded-sRGB Y-like calculations with separately pinned coefficient
  conventions and different software contracts.
- Reserve WCAG claims for a specified foreground/background pair. Passing a
  contrast threshold does not certify general readability or accessibility.

### 3.3 CIEDE2000 and CVD

- Replace “accessibility oracle” and unqualified “correctly passes/fails” with
  “model-specific collision diagnostic” or “regression diagnostic.”
- State that the 10/8 floors were historical Octave search criteria, not CIE,
  WCAG, or universal categorical requirements.
- State that current release validation protects each asset's frozen
  non-regression baseline.
- Document the relevant pipeline: nominal sRGB decoding, named full-severity
  simulation, gamut clamp/re-encoding, catalog quantization convention, CIELAB
  conversion, and CIEDE2000 comparison.
- Keep the limitation that simulations do not represent every observer.

### 3.4 Gamut mapping

- Describe the shipped policy as constant-OKLCH-L, constant-h chroma reduction
  by boundary bisection for in-range lightness.
- Do not call it CSS Local-MINDE or globally optimal appearance mapping.
- Acknowledge black/white limits, near-neutral hue, numeric tolerance, and final
  quantization.

## 4. Claim corrections

### 4.1 Recipe bookkeeping

Remove the headline claim that ramps and continuous maps compile from “107
input numbers.” The palette authoring bookkeeping may still be explained as 76
free family fields, 24 Fourier coefficients, and seven named constants, but it
must disclose that the ten-value gray profile counts as one named constant.
Under the same exclusions this corresponds to 116 scalar numeric leaves, not
107. The migration-only tone derivation grid remains outside both counts.

Existing shipped family rows store all eight operational values. The four
Fourier-derived fields are an extension mechanism and an authoring prior, not
values recomputed for every existing family at runtime. Continuous maps also
have topology-specific recipe data outside this palette bookkeeping.

### 4.2 Chroma fit and shape

- Compute the displayed R-squared value from the same 19 points and curve shown
  in the figure; do not hard-code the inherited 15-family value.
- Describe the result as an in-sample descriptive fit to the authored catalog,
  not independent evidence of an sRGB boundary or predictive validity.
- Say that families share a functional form and exponents while `C_max`, `t_p`,
  `c_0`, and `c_end` vary.

### 4.3 Step placement

- Describe the one shipped spacing policy: DeltaEOK arc-length equalization.
- Remove claims that `ease`, `exp`, `log`, or a public warp option exist.
- Alternative endpoint-emphasizing policies may be mentioned only as possible
  future designs requiring an explicit API and compatibility contract.

### 4.4 Release validation

- Describe actual metric-specific non-regression gates from Validation.
- Keep WCAG outside the color-authority compile-gate table.
- Separate historical Octave adoption thresholds from current per-asset
  release baselines.

### 4.5 Colormap topology

- Single-hue sequential maps default to light-low/dark-high.
- Multi-hue sequential maps default to dark-low/light-high.
- Diverging maps have two poles around a light center and no single monotonic
  low-to-high brightness direction.
- Cyclic maps have no low/high direction. Their generating path closes, while
  the stored endpoint-exclusive LUT leaves first and last entries one ordinary
  wrap step apart.
- Qualitative maps are unordered.
- `_r` is a continuous-map registration. Qualitative reversal uses the
  discrete API's `reverse=True` option.

### 4.6 Range and hue vocabulary

- Say that colormap output ranges are independent of palette family floors but
  are class- or scene-specific, not globally shared.
- State that different maps are not cross-panel comparable merely because they
  have broad ranges; shared normalization and preferably the same map are still
  required.
- Scope the nineteen `h_0` anchors to named palette identity and multi-hue scene
  waypoints. Document topology-specific hue sources for diverging and cyclic
  maps.

### 4.7 Bounded design claims

- Present hue-specific dark endpoints and warm-hue drift as this catalog's art
  direction, not universal hue identity thresholds or laws of perception.
- State that no shipped yellow token reaches 4.5:1 on white, while darker
  olive-yellow colors can; the limitation belongs to the selected ramp.
- Explain Turbo's non-monotonic lightness as a task-dependent trade-off that
  can create ambiguity or emphasize variation, not as proof that all visible
  detail is invented.
- Scope typography reproducibility to bundled glyph coverage and a pinned
  rendering environment.

## 5. Files in scope

Primary:

- `docs/color_system/design-rationale.md`
- `docs/color_system/generate_theory_figures.py`
- regenerated affected theory SVGs
- documentation tests that pin claims, generated labels, and numeric values

Direct consistency fixes are allowed in:

- `docs/color_system/colormaps.md`
- `docs/color_system/palettes.md`
- `docs/color_system/validation.md`

Those adjacent pages change only when they repeat a corrected claim. This is
not a general rewrite of the public color documentation.

## 6. Non-goals and invariants

- Do not change generated palette hex values or any 256-stop LUT.
- Do not change runtime color APIs, registration names, or public counts.
- Do not implement a spacing-warp API as part of a documentation correction.
- Do not replace the relative-Y compatibility contract with direct OKLCH L.
- Do not remove CIELAB, CIEDE2000, or CVD diagnostics.
- Do not rewrite superseded historical specifications as if they were current
  API documentation.
- Preserve valid formulas, catalog facts, model names, protocol details,
  figures, and compatibility rationale. False or misleading claims are not
  protected by the earlier content-preservation invariant.
- Keep public documentation in English and readable without prior color-theory
  study.

## 7. Verification design

### Mechanical checks

- R-squared is independently recomputed from the displayed 19-family protocol
  and compared with the prose and generated figure label at three decimal
  places.
- Recipe-count tests distinguish bookkeeping slots from scalar leaves.
- Documentation tests reject the removed warp capability and universal WCAG,
  CVD, range, hue-vocabulary, reversal, and direction claims.
- Existing catalog-count, float-claim, generated-asset, discrete-form, and
  topology tests remain green.

### Rendered-document checks

- Regenerate affected theory SVGs from the live package.
- Build Sphinx with warnings as errors.
- Inspect the rendered Design rationale for readable callouts, equations,
  tables, figure labels, and cross-links.

### Adversarial review

Run three independent reviews after implementation:

1. a color-science review for standards scope and causal overclaiming;
2. a visualization-design review for defensible design rationale and map
   semantics; and
3. an implementation-contract review against the compiler, gates, and tests.

## 8. Acceptance criteria

The work is complete when:

1. a reader can distinguish colorimetric fact, project contract, design intent,
   and catalog measurement;
2. no public claim advertises a capability, gate, range, direction, or reversal
   contract absent from the implementation;
3. modeled relative Y, WCAG contrast, DeltaEOK scaling, and CVD/CIEDE2000 scope
   are described in scientifically bounded language;
4. R-squared and other quoted measurements are derived from documented current
   protocols rather than stale literals;
5. the central compatibility decision remains clear: direct OKLCH L is valid
   for a new incompatible system, while the shipped catalog retains relative-Y
   targets to preserve accepted output; and
6. runtime generated colors and public API surfaces are unchanged.

## 9. Primary references

- Oklab construction and intended viewing assumptions: Björn Ottosson,
  “A perceptual color space for image processing.”
- Oklab/OkLCh distance scaling and constant-lightness, constant-hue chroma
  reduction: W3C CSS Color Module Level 4.
- Relative luminance and pairwise contrast: W3C WCAG 2.2.
- CIEDE2000 scope and reference conditions: CIE 142 and the Sharma–Wu–Dalal
  implementation notes.
- CVD simulations: Machado, Oliveira, and Fernandes (2009) for protan/deutan;
  Brettel, Viénot, and Mollon (1997) for tritan.
