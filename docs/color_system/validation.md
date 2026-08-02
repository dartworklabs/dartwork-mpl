---
orphan: true
---

# Validating the color system

Modeled relative CIE Y (`relative_y`) is calculated from nominal D65 sRGB; it
is not a measurement of a particular display, perceived brightness, or OKLab
`L`.

:::{tip}
This page is for release maintainers. Ordinary users should start with
[Colors](colors.md) or [Colormaps](colormaps.md).

A successful validation result—the green release result—requires the live
compiler to reproduce the published names, orders, colors, and discrete
selections; `passed` is `true`; the exact mismatch count is zero; and the
quality-violation list is empty.
:::

Every shipping workflow runs the following dedicated color-authority and
generated-doc checks before deployment or publication. Run them from the
repository checkout:

```bash
uv run python scripts/build_color_v6_ssot.py \
  --baseline-commit 12d16bac22dee790bd0696ca92a814a797dc728b \
  --output /tmp/dartwork-color-v6-ssot.json
cmp /tmp/dartwork-color-v6-ssot.json \
  src/dartwork_mpl/asset/color/color_v6_ssot.json
uv run python -m dartwork_mpl._colors._build --check
uv run python scripts/compare_color_systems.py \
  --output build/color-system-comparison --check
uv run python docs/_static/scripts/build_categorical_explorer.py --check
uv run python docs/_static/scripts/build_colormap_explorer.py --check
uv run python docs/color_system/generate_theory_figures.py --check
```

:::{note}
Read the block as one ordered maintainer workflow:

1. Rebuild the color authority into a temporary file, leaving the packaged
   authority untouched.
2. Byte-compare that temporary rebuild with the packaged authority.
3. Check that the generated Python catalog is current.
4. Compare the frozen output with a fresh result from the live compiler.
5. Verify the categorical explorer, colormap explorer, and theory figures.
:::

Generated typing parity is covered by the full test suite; Sphinx separately
checks the template index and `llms-full.txt` without rewriting either tracked
authority.

The v6 rebuild goes to a temporary file and `cmp` verifies byte parity without
rewriting the packaged authority. The compiler and docs-generator checks are
also non-writing. The comparator is the deliberate exception: `--check` still
writes ignored local diagnostics to `build/color-system-comparison/` so a
failed comparison can be inspected. Use `--output PATH` to choose another
directory.

- `report.json` is the machine-readable gate record. It is strict, sorted JSON
  and keeps `passed`, provenance, violations, and raw, unrounded decision
  values from a completed report-generation run. CI, docs-deploy, and release
  jobs use the comparator process exit code to decide whether the step passed;
  they upload `report.json` as inspectable evidence rather than parsing it to
  control the current step.
- `index.html` is a deterministic, standalone human review surface. It uses
  inline CSS and SVG and has no network or runtime-registry dependency.
  Open `index.html` for human review.

Every CI, docs-deploy, and release run uploads that directory as CI artifact
`color-system-comparison`, with `always()` semantics so diagnostics survive a
passing or failing comparator. The directory remains intentionally ignored;
the HTML is a local/CI inspection surface, not a repository-hosted page.

`report.json` is written last, after `index.html`, as the last-write completion
marker for successful report generation. The marker means that report
generation completed successfully; it does not mean that all gates passed.
Both exit codes `0` and `1` write `report.json`.

Its presence does not by itself prove that an arbitrary current invocation
completed. Argument parsing happens before the selected output path is
available and therefore before an older `report.json` can be removed. An
invalid-argument invocation exits `2` and can leave a previous report in that
directory untouched. A green validation result requires `passed` to be `true`
and the process exit code to be `0`; an exit-`1` report records `passed` as
`false` and remains available for diagnosis.

After argument parsing succeeds, the comparator removes the preceding marker
from the selected output directory before it creates that directory or loads,
compiles, compares, serializes, or renders anything. Writing JSON last then
prevents an ordinary failure later in that invocation from pairing new HTML
with an older gate record. Use the current process exit code—not file presence
alone—to determine the result of the current invocation.

## Exit codes

| Code | Meaning |
|---:|---|
| `0` | A trustworthy report was written and all exact and quality gates passed. |
| `1` | A trustworthy report was written, but the candidate has an exact mismatch or quality regression. |
| `2` | The current invocation produced no trustworthy new report because a reference, oracle, schema, serialization, rendering, argument, or I/O check failed. |

A representable invalid hex leaf already present in a constructed candidate
snapshot belongs to exit `1`: the report can represent and explain it. A source
parse or schema failure—including a malformed bundled vendor asset—belongs to
exit `2`, because no trustworthy candidate snapshot exists to compare. A
changed or unreadable frozen fixture, failed pinned reference case, baseline
recomputation drift, or output failure also belongs to exit `2`.

## Exact compatibility scope

In the compatibility list, a surface is one public group being compared. Exact
does not mean visually close: it means identical names, order, hex values,
registrations, and frozen indices. A 256-stop lookup table is the ordered list
of 256 colors behind a continuous map.

All 18 frozen public surfaces are compared recursively, with sorted escaped
JSON Pointer paths for missing, extra, shortened, and changed leaves:

1. palette rows;
2. cycle rows;
3. all 43 full 256-stop colormap LUTs;
4. curated/manual rows;
5. diverging canonicals;
6. semantic coordinates;
7. resolved semantic colors;
8. dark-cycle coordinates;
9. resolved dark-cycle colors;
10. family taxonomy;
11. forward and reverse registration names;
12. typing literals;
13. MCP discovery identities;
14. public inventory;
15. forward discrete hex forms;
16. reverse discrete hex forms;
17. frozen multi-hue discrete indices; and
18. all 892 vendor token name → hex values.

The isolation exists so the candidate cannot grade itself by importing the
stored expected answer. The audit therefore constructs the candidate from its
sources before comparing it with the frozen result.

The CLI loads the `_colors/` construction and comparison sources under the
private `_dartwork_mpl_color_audit` package alias. It does not initialize the
canonical `dartwork_mpl` package or load `_generated`, `_loader`, `_register`,
`_semantic`, `_families`, `_discrete`, or `_typing`. Every file-backed module
in that alias closure must resolve beneath this checkout's `_colors/`
directory. The construction path currently uses matplotlib's color-math
library, but the isolated audit neither reads nor changes matplotlib's named
color or colormap registries. This audit-only boundary does not alter the
public package's existing eager-registration behavior.

The live candidate snapshot therefore compiles recipe sources directly. It
does not read the committed generated catalog or runtime registries, so a
stale generated file cannot make the comparison pass circularly.

## Independent quality oracle

An oracle is an independent reference implementation checked against published
examples.

The separately pinned standard-library oracle is verified with published
Sharma et al. CIEDE2000 reference pairs, source-pinned Machado (2009)
matrices, project-adapted Brettel–Viénot–Mollon (1997) matrices, and
project-derived CVD regression cases. At comparison entry, it recomputes all
v5 metrics from immutable literals and requires canonical semantic equality
with the frozen quality fixture before evaluating the live candidate. Baseline
fixture, oracle-source, reference-case, and recomputation drift therefore stop
the run with exit `2`.

:::{note}
**Reading the metric names**

- **direct-32** is a 32-color preview compiled directly at that size, not
  downsampled from the 256-color table.
- **full-256** is the complete 256-stop lookup table for a continuous map.
- **Modeled relative Y** is the nominal output coordinate defined above;
  later references use this shorter name.
- **step CV** is the coefficient of variation—the relative spread—of
  neighboring OKLab color-distance steps;
  lower step CV means more even neighboring steps.
- **span** is the largest modeled-relative-Y value minus the smallest in an
  ordered row.
- A **monotonic floor** is the minimum allowed signed neighbor change in the
  intended direction.
- **Quantization** turns calculated colors into the finite 8-bit hex stops that
  are shipped.
- A **regression** means that the candidate makes a guarded metric worse than
  its frozen v5 baseline permits.
:::

Quality decisions use raw doubles. Every one of the 43 direct-32 previews and
43 full-256 LUTs is checked for count, degenerate neighboring steps, and step
CV; a full-LUT topology result cannot substitute for those direct-preview
gates. Ordered palettes and ordered sequential/multi-hue direct-32 and
full-256 rows must also keep their v5 direction, monotonic
modeled-relative-Y/OKLab-L floors, and Y span. The direct-32 rule is
`step_cv <= min(v5, 0.08)`. Nonordered diverging/cyclic direct-32 rows and all
quantized full-256 rows use `step_cv <= v5`, because some frozen values
intrinsically exceed `0.08`.

Ordered full-256 rows have an additional absolute check. For each adjacent
pair, the oracle expands both stored colors to their local half-step 8-bit
sRGB quantization cells, using round-to-nearest/ties-to-even, and computes the
most favorable modeled-relative-Y ordering still represented by those cells.
The smallest `oriented_delta_y + local_tolerance` margin must be non-negative.
This distinguishes a small reversal explainable by the two quantization cells
from an ordering inversion that those cells cannot represent. It applies only
to the normal nominal-sRGB row—not to CVD simulations, whose per-asset
regression floors remain separate. Categorical CIEDE2000 floors and full-LUT
diverging/cyclic topology metrics likewise may not regress from each asset's
own v5 value.

CIEDE2000 and the named CVD simulations are model-specific
collision/regression diagnostics. Their per-asset baselines guard the shipped
catalog against regression under those named models; they are not observer
guarantees or palette certification.

The HTML uses the archived literal v5 32-stop previews—not a downsample of the
256 LUT—and the candidate's direct 32-stop compiler output. It shows both
versions' palette chips, grayscale/CVD strips and OKLab-L, modeled-relative-Y, and
neighbor-distance profiles, plus real diverging mirror-Y and cyclic seam
diagnostics. It also generates the direct-OKLCH unlocked diagnostic for all 43
continuous-map rows. That panel is explanatory, non-normative, and never a
gate input.
