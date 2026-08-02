| ID | source | preserved content | destination | status |
|---|---|---|---|---|
| U01 | usage_guide/colors.md | seven library prefixes and `dc.*` recommendation | usage_guide/colors.md#named-colors | preserved |
| U02 | usage_guide/colors.md | `color=` versus `cmap=` distinction | usage_guide/colors.md#named-colors | preserved |
| U03 | usage_guide/colors.md | named-color, mixing, pseudo-alpha, manual cycler, discovery, interpolation, and colormap examples | usage_guide/colors.md (Named colors through Colormaps) | preserved |
| U04 | usage_guide/colors.md | interpolation and colormap widgets | usage_guide/colors.md#color-interpolation | preserved |
| C01 | color_system/colors.md | 20 families: 19 chromatic ramps plus gray, ten steps, naming grammar | color_system/colors.md (How to read the labels; Palette sheets › dartwork Color — families) | preserved |
| C02 | color_system/colors.md | semantic aliases and locale behavior | color_system/colors.md (Semantic aliases) | preserved |
| C03 | color_system/colors.md | six third-party token sheets and rendering guidance | color_system/colors.md (Semantic aliases — OpenColor through Primer sheets; Rendering guidance) | preserved |
| P01 | color_system/palettes.md | explorer, 13 rail choices, apply examples, chooser table | color_system/palettes.md (Pick a palette; Apply it; Which palette for which data?) | preserved |
| P02 | color_system/palettes.md | four discrete forms, counts, API grammar, curated membership | color_system/palettes.md (How the system is organized; Reference › Curated sets; Reference › `colors` and `set_colors` options) | preserved |
| P03 | color_system/palettes.md | Octave/Okabe-Ito/CVD scores, CVD model attribution, the historical `Octave Print` L* diagnostic, its explicit no-printing-guarantee caveat, and style expansion | color_system/palettes.md (Reference › Octave — the default cycle) | preserved |
| M01 | color_system/colormaps.md | 43 continuous, 13 qualitative, 56 records, 99 registrations | color_system/colormaps.md (The catalog — group table and Technical detail) | preserved |
| M02 | color_system/colormaps.md | explorer and complete four-group name table | color_system/colormaps.md (The catalog — explorer and four-group table) | preserved |
| M03 | color_system/colormaps.md | direction grammar, dark-center and isoluminant notes, chooser | color_system/colormaps.md (Choosing a map; The catalog; Naming grammar) | preserved |
| M04 | color_system/colormaps.md | aurora/viridis CV values and interpretation | color_system/colormaps.md (Choosing a map; Why not just use viridis?) | preserved |
| M05 | color_system/colormaps.md | CVD models, modeled relative CIE Y guidance and its non-measurement limit, custom-map caveats, rendering tips | color_system/colormaps.md (Why not just use viridis?; Color-blind safety; Creating custom colormaps; Rendering tips) | preserved |
| O01 | color_system/color-class.md | constructors, conversions, mutable views, copy behavior, interpolation | color_system/color-class.md (Creating Color objects through Color interpolation with cspace) | preserved |
| O02 | color_system/color-class.md | all interactive widgets, figures, examples, custom-map construction and registration | color_system/color-class.md (Creating Color objects, Color space conversion, Color interpolation with cspace, Creating custom colormaps) | preserved |
| R01 | color_system/design-rationale.md | 107-input construction statement and MCP count distinction | color_system/design-rationale.md (Design rationale; Anatomy of a family) | preserved |
| R02 | color_system/design-rationale.md | four principles, A1, direct-OKLCH alternative, modeled relative CIE Y compatibility rationale and measurement limits, gamut policy | color_system/design-rationale.md (Four principles; The construction foundation (axiom A1)) | preserved |
| R03 | color_system/design-rationale.md | A2-A8 formulas, figures, fit values, gate table, and interpretations | color_system/design-rationale.md (The generation axioms (A2–A8)) | preserved |
| R04 | color_system/design-rationale.md | family anatomy, parameter table, metric layers, CVD critique and scores | color_system/design-rationale.md (Anatomy of a family; The metric system — what the ruler is) | preserved |
| R05 | color_system/design-rationale.md | colormap grammar, scene table, cyclic behavior, limitations, reproducibility, typography rationale | color_system/design-rationale.md (Colormaps, derived from the palette through Typography rationale) | preserved |
| V01 | color_system/validation.md | complete executable command block and non-writing behavior | color_system/validation.md (Validating the color system — maintainer workflow and non-writing behavior) | preserved |
| V02 | color_system/validation.md | report/HTML roles, atomic marker behavior, exit codes | color_system/validation.md (Validating the color system — report artifacts and marker behavior; Exit codes) | preserved |
| V03 | color_system/validation.md | all 18 exact surfaces, including all 892 vendor token name → hex values, and isolated candidate-loading rationale | color_system/validation.md (Exact compatibility scope) | preserved |
| V04 | color_system/validation.md | independent oracle and every direct-32/full-256 quality rule | color_system/validation.md (Independent quality oracle) | preserved |
| D01 | design_system/index.md | task table, catalog cards, counts, page navigation | design_system/index.md (Overview — task table, catalog cards, counts, and navigation) | preserved |

## Final preservation summary

All 27 inventoried claim groups are preserved at the descriptive destinations
above. No unique claim was removed: the final pages retain the original
numbers, formulas, caveats, protocol names, examples, figures, and API
guidance. The rewrite consolidated only duplicate introductory wording: the
repeated token/palette/colormap task choice now has one beginner reading path,
and repeated definitions of OKLab/OKLCH, ΔEOK, modeled relative CIE Y
calculated from nominal D65 sRGB, CIELAB/ΔE00, CVD, and WCAG now point readers
from compact local explanations to the Design rationale and Validation
evidence pages. Those consolidations changed placement and phrasing, not
technical meaning.
