---
orphan: true
---

# Visual Regression Testing

dartwork-mpl uses two visual regression layers because rendered
matplotlib output is environment-sensitive.

## Layer 1: Property Tests

`tests/visual/test_visual_properties.py` builds every scenario and checks
semantic figure properties instead of pixels:

- expected axes, lines, patches, images, and collections are present
- declared palette tokens resolve to colors used by artists
- required Korean, math, and special-character text appears in Text artists
- at least one y-axis label is present when the scenario requires it
- the active font resolves to the bundled dartwork font directory

This layer is robust across Python, matplotlib, and freetype differences,
so it runs as part of the normal test matrix.

Run it locally:

```bash
pytest tests/visual/test_visual_properties.py
```

## Layer 2: Pixel Baselines

`tests/visual/test_visual_pixels.py` uses pytest-mpl. Without `--mpl`,
the builders still execute as smoke coverage. With `--mpl`, pytest-mpl
compares rendered PNGs against committed baselines.

Run the smoke path:

```bash
pytest tests/visual/test_visual_pixels.py
```

Run the pixel comparison when baselines are present:

```bash
pytest tests/visual/test_visual_pixels.py --mpl
```

## Tolerance

Every scenario uses one tolerance, `PIXEL_TOLERANCE = 0.5` (RMS on the
0–255 scale) in `tests/visual/test_visual_pixels.py`. It is set where the
renders are deterministic, so a visible change fails however small.
Measured on 2026-11-06 against the committed baselines:

| Render | RMS |
|---|---|
| lock environment (Python 3.11, Matplotlib 3.11.2, NumPy 2.4); Matplotlib 3.11.0 and 3.11.1; NumPy without its AVX-512 or AVX2 kernels | 0 (byte-identical) |
| NumPy 2.5.4, as the `visual` job (Python 3.12) and `test-matplotlib (latest-deps)` resolve it | 0.007 (`scatter_fit` only, 95 pixels) |
| one character of one tick label changed | 1.65 – 22 |
| `dual_axis_timeseries` with `tick_years=4` (every x tick relabelled) | 11.2 |

0.5 sits 70 times above the NumPy 2.5 noise and 3 times below the smallest
change measured. `test_pixel_tolerance_catches_a_tick_text_change` keeps it
there: it fails if the tolerance would let the `tick_years=4` relabel pass.
A pixel test that fails after a dependency update means the render really
changed: look at the diff images, and regenerate the baselines on purpose.

Where the pixel tests run in CI:

- `visual` (the lock) and `test-matplotlib (minimum)` (Matplotlib 3.11.2, NumPy 1.26.0)
  run them on pinned versions. A failure there is a defect in the PR.
- `test-matplotlib (latest-deps)` resolves the newest releases that
  pyproject allows. It is not a required check: branch protection requires
  pre-commit, lint, test (3.11–3.13), test-no-extras and docs. A pixel
  failure there that main shares signals an upstream rendering change, not
  a PR defect. Look at its diff images, and rebaseline deliberately in its
  own PR when the new rendering is accepted.

## Updating Baselines

Baselines are Ubuntu-native. Do not regenerate them on macOS.

For an intentional design change:

1. Run the `visual-baselines` workflow with `workflow_dispatch`.
2. Download the `visual-baselines` artifact.
3. Review the generated PNGs through the
   [serve-visual review step](#reviewing-baselines-with-serve-visual).
4. Commit the reviewed images under `tests/visual/baseline/`.

## Reviewing Baselines With serve-visual

Use the repository or orchestrator `serve-visual` review step to inspect
the downloaded artifact before committing it. The review should compare
the new PNGs against the intentional design change, not against local
macOS output.
