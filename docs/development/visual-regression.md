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
