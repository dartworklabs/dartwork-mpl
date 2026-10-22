# Bundled templates

The package ships 18 chart types, each as a `basic` and an `advanced`
runnable script: bar, bar_grouped, bar_horizontal, boxplot, contour,
heatmap, histogram, line, pie, plot_3d, polar, scatter, small_multiples,
stacked_bar, tornado, twin_axis, violin, waterfall. `basic` is the minimal
pattern; `advanced` adds annotation and narrative touches. They are
starting points; any matplotlib chart type is fine without one.

```python
from importlib.resources import files
import dartwork_mpl as dm

match = dm.find_template("grouped bar comparison", top_k=1, tier="all")[0]
print(match["template_id"], match["tier"], match["data_shape"])

folder = files("dartwork_mpl").joinpath("asset", "prompt", "05-templates")
if match["tier"] == "advanced":
    folder = folder.joinpath("advanced")
source = folder.joinpath(f"{match['template_id']}.py").read_text(encoding="utf-8")
print(source)                    # read and adapt; reading does not run it
```

- `match["source_path"]` is the repository gallery path, not an installed
  file; read the source through `importlib.resources` as above.
- `dm.suggest_chart_type("categorical", "continuous", 8, 3)` returns a chart
  name for a data description (`"grouped_bar"` here).

When adapting a template:

1. Replace every synthetic array, label and hard-coded summary with the
   user's data. Never keep invented numbers or annotations.
2. Keep the user's preset and size; the template's preset and
   `dm.figsize` are defaults.
3. Change the output stem in its `dm.save_formats` call, then run the
   review loop (`references/review-loop.md`). Advanced templates draw long
   titles and annotations: check them in the PNG.
