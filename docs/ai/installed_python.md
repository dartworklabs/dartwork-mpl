# Installed Python agent workflow

This route needs the core `dartwork-mpl` installation and Python file/image
access, without MCP, a repository checkout or a lint CLI. Use existing APIs;
matplotlib Figure/Axes and artist setters stay native. A human can request a
plot or revision in ordinary language; the agent performs this loop.

Agents that read project skill folders can load the same guidance as a
skill: run `python -m dartwork_mpl.skills install` once in the project.

## Read the installed guidance and template source

```python
from importlib.resources import files
from pathlib import Path
import dartwork_mpl as dm

print(dm.get_agent_doc("AGENTS"))
print(dm.get_prompt("01-policy"))
print(dm.get_prompt("03-recipes"))
print(dm.get_prompt("02-anti-patterns"))

# Ranking metadata is available without MCP; source_path is repo-relative.
root = files("dartwork_mpl").joinpath("asset", "prompt", "05-templates")
Path("output").mkdir(exist_ok=True)
for tier in ("basic", "advanced"):
    match = dm.find_template("line time series", top_k=1, tier=tier)[0]
    folder = root if tier == "basic" else root.joinpath("advanced")
    source = folder.joinpath(f"{match['template_id']}.py").read_text(encoding="utf-8")
    print(tier, match["template_id"], match["source_path"])
    Path(f"output/template-{tier}.py").write_text(source, encoding="utf-8")
    print(source)  # inspect/adapt; retrieving a template does not execute it
```

`find_template(...)[0]["source_path"]` identifies the repository gallery source;
it is not an installed filesystem path. `importlib.resources` above reads the
bundled executable basic/advanced source. Keep the selected preset and existing
scoped overrides when adapting it. Templates are starting points, not chart or
property limits. For equal, ratio, spanning, nested and whole-canvas container
layouts, read `dm.get_prompt("03-recipes")` or [Layout](../usage_guide/layout.md#native-multi-panel-layouts).

`figsize_grid` estimates whole-figure size from nominal panel/gap inputs;
it does not enforce exact Axes dimensions or cm gaps. The layout recipes
also distinguish MCP's template/checklist-only `compose_layered_plot` from
`simple_layout`'s bounded root-margin correction (#209). Neither supplies a
nested spacing solver or proof that content fits; render, measure and review.

## Interpreting optional source auto-fixes

Import `ast` and parse the complete source string with `ast.parse(code)`
before lint/fix. This nonexecuting preflight can detect malformed Python;
repair syntax errors in the source first. Some lint checks skip malformed
source, so empty findings or MCP's “No issues found” do not prove valid
syntax. Parsing and linting do not prove that code can compile, execute or
render correctly, and do not authorize executing arbitrary source.

For a source string named `code`, import `apply_lint_fixes` from
`dartwork_mpl.lint`, then call
`fixed_code, applied, unfixed = apply_lint_fixes(code)`. The MCP tool of the
same name returns a dict with those three keys. Neither route executes the
submitted source. Inspect the diff and every remaining finding: `applied`
locations refer to the original source, `unfixed` to the returned source.

The fixer needs an existing dartwork import binding and locally proven
calls. It can redirect pyplot's `style.use` with one supported literal
preset to that binding, or replace a no-argument `fig.tight_layout()` on a
proven pyplot-created Figure with `simple_layout(fig)`. Not all aliases or
constructors are recognized. It does not invent imports, infer the current
Figure for `plt.tight_layout()`, transfer layout kwargs, or rewrite
unsupported/dynamic styles, bare native Figure layout calls or arbitrary
artist properties. A suggestion alone does not establish an applicable fix.

Unchanged bytes with empty `applied` mean no correction was applied;
nonempty `unfixed` still needs attention, while empty `unfixed` means no
reported findings, not that all checks ran. Changed source can also retain
`unfixed` findings. Preserve the user's style, colors, legend and layout
intent, including intentional overrides. Stop retrying identical source.
Resolve bindings, arguments and intended behavior before making a scoped
source edit, then parse/lint again. For trusted code you choose to execute,
retain the normal runtime validation and actual image-review steps below.

## Choose the input version before a revision

For each logical input, keep its name, chosen version, SHA-256, source and
snapshot location visible beside the revision. Explicit requests settle the
choice; do not ask again when the requested version is clear.

| Request | Input choice |
| --- | --- |
| “Keep the previous data; change only the markers/style.” | Verify and reuse the retained bytes used by the previous figure, even if the upstream file changed. |
| “Use the current file.” | Read the authorized current bytes and pin them in a new revision; retain earlier snapshots and prior requested style edits. |
| Data version is materially ambiguous or prior evidence is unknown | Ask one relevant question before choosing; keep the original artifacts. |

Read only user/operator-authorized inputs. For native Python, save copies in
an authorized, user-owned project output area outside `datasets`. MCP instead
uses its operator-authorized private `storage_dir` and existing admission rules.
Never write upstream or collect unrelated files. Consume the pinned bytes/path,
rather than reopening
a mutable upstream path after hashing it. For style-only work, verify every
required input against its previous receipt. A missing/changed snapshot or
unknown input evidence needs clarification, never a silent current-file fallback.
Hashes establish byte identity, not freshness, permission or complete
reproducibility. An old snapshot is not evidence of the latest upstream data.
MCP uses its existing explicit Copy/Retained admission and receipts; native local
copies have no automatic MCP seven-day expiry or deletion guarantee.

## File-only scripts: select the backend before creating figures

For standalone PNG/PDF export, start the process with `MPLBACKEND=Agg`, before
importing pyplot or creating figures: `MPLBACKEND=Agg python plot.py` (likewise
`plot-v2.py` and `pin-input.py`). This is scoped to file-only scripts; keep
interactive/notebook backend choices. `dm.figsize` returns the requested inch
tuple, but a GUI backend can quantize a Figure's size at creation. A local
macOS backend observation is not a universal limitation of `dm.figsize`.

Check `fig.get_size_inches()` after creation and after export against the
requested physical canvas. Keep `bbox_inches=None`, then inspect the saved
PDF page width/height (72 points per inch), not only the PNG pixel dimensions.
Report any mismatch and the backend actually used; do not silently resize the
canvas, change layout or blame the unit conversion. Agg avoids the observed
GUI quantization in these file-export examples; still check the actual PDF.

## Native file input: pin the bytes actually consumed

This standalone example expects an authorized UTF-8 `measurements.csv` with
`x,y` columns (blank `y` means a missing reading). Save it as `pin-input.py`
and run `MPLBACKEND=Agg python pin-input.py` for file-only export.
Choose the input and a **new** revision directory in the configuration below.
The small JSON receipt is a local example, not a public schema/API. Treat its
paths as trusted, user-owned project paths, not untrusted service requests.
Keep the receipt, snapshot, exact source, PNG/PDF and full validation findings.

<!-- pinned-input-example -->
```python
import csv
import hashlib
import io
import json
from dataclasses import asdict
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

# User-authorized paths; output must be outside datasets. Never reuse a directory.
choice = "current"  # initial/current-file request; use "previous" for old data
upstream = Path("measurements.csv")
previous_receipt = Path("output/figure-v1/input.json")
revision = Path("output/figure-v1")
logical_name = "measurements"

if choice == "current":
    raw = upstream.read_bytes()  # read upstream once; copy AND parse these bytes
    source = str(upstream.resolve())
    selected_from = None
elif choice == "previous":
    old = json.loads(previous_receipt.read_text(encoding="utf-8"))
    if old["logical_name"] != logical_name:
        raise ValueError("Unknown prior input: clarify the intended version")
    raw = Path(old["snapshot"]).read_bytes()  # missing: stop, do not read upstream
    if hashlib.sha256(raw).hexdigest() != old["sha256"]:
        raise ValueError("Prior snapshot changed: clarify the intended version")
    source = old["source"]
    selected_from = str(previous_receipt.resolve())
else:
    raise ValueError("Choose current or previous explicitly")

rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"), newline="")))
x = np.array([float(row["x"]) for row in rows])
y = np.array([float(row["y"]) if row["y"] else np.nan for row in rows])
if not np.isfinite(x).all() or np.isinf(y).any() or np.isfinite(y).sum() < 2:
    raise ValueError("Expected finite x and at least two finite y observations")
x, y = dm.validate_data(x, y, allow_nan=True)

revision.mkdir(parents=True, exist_ok=False)  # refuse overwrite, even on rerun
snapshot = revision / "input.csv"
with snapshot.open("xb") as stream:
    stream.write(raw)
receipt = dict(logical_name=logical_name, choice=choice, source=source,
               sha256=hashlib.sha256(raw).hexdigest(),
               snapshot=str(snapshot.resolve()), selected_from=selected_from)
with (revision / "input.json").open("x", encoding="utf-8") as stream:
    json.dump(receipt, stream, indent=2)
print(json.dumps(receipt, indent=2))  # show the selected version, not only a filename

# Keep the existing construction/overrides when adapting this to a revision.
dm.style.use("report")
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
ax.plot(x, y, color="oc.blue9", label="Observed")
ax.set(xlabel="Time (s)", ylabel="Response")
ax.legend(loc="upper left")
dm.simple_layout(fig, margin="2mm")
code = Path(__file__).read_text(encoding="utf-8")
with (revision / "plot.py").open("x", encoding="utf-8") as stream:
    stream.write(code)
report = {"lint": [asdict(item) for item in dm.lint_code(code)],
          "visual": [asdict(item) for item in dm.validate_figure(fig)]}
with (revision / "report.json").open("x", encoding="utf-8") as stream:
    json.dump(report, stream, indent=2)
dm.save_formats(fig, str(revision / "figure"), formats=("png", "pdf"),
                bbox_inches=None)
```

For the next style-only revision, retain the construction and all earlier edits,
set `choice = "previous"`, point `previous_receipt` at the previous revision's
`input.json`, and choose a new directory such as `output/figure-v2`. An explicit
current-file request instead sets `choice = "current"` with the authorized
upstream path and another new directory. Never relabel the old receipt as current.
Missing/unreadable receipts, absent snapshots, mismatched hashes or unknown
required inputs stop this example; disclose the problem and ask which available
version to use. Do not repair evidence or silently substitute another file.
Then follow the full report and actual PNG/PDF review steps below. These local
copies persist until the user manages them; they do not inherit MCP expiry.

## Check data without silently closing gaps

`dm.validate_data(x, y)` returns cleaned NumPy arrays, not a report or boolean.
Its default `allow_nan=False` removes NaN/Inf observations and aligned rows,
which can connect a line across a missing observation. Decide the blank/missing
policy first. Preserve meaningful gaps with `allow_nan=True` and separate shape,
alignment, infinity and finite-observation checks as below. That option also
allows infinities; it is not a complete shape/domain validator. Do not coerce
arbitrary categorical blanks to zero or drop rows without the user's intent.
The MCP `validate_plot_data(plot_type, data_json, ...)` is a distinct tool with
chart-specific input checks; it is not `dm.validate_data` or a Python alias.

## Native Figure → full report → files → actual image review

Save the following as `plot.py` and run `MPLBACKEND=Agg python plot.py` for
file-only export. In a notebook, replace
`Path(__file__)` with the path where you saved the exact executed source.

```python
from dataclasses import asdict
from pathlib import Path
import json
import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

# Blank observations represent missing readings, so retain a visible line gap.
x_input = [0, 1, 2, 3, 4, 5]
y_input = [1.0, 1.8, None, 2.1, 1.7, 2.5]
x = np.asarray(x_input, dtype=float)
y = np.asarray([np.nan if v is None else v for v in y_input], dtype=float)
if x.ndim != 1 or y.ndim != 1 or x.shape != y.shape:
    raise ValueError("Expected aligned one-dimensional x/y observations")
if not np.isfinite(x).all() or np.isinf(y).any() or np.isfinite(y).sum() < 2:
    raise ValueError("Expected finite x and at least two finite y observations")
x, y = dm.validate_data(x, y, allow_nan=True)

dm.style.use("report")
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
line, = ax.plot(x, y, color="oc.blue9", label="Observed")
ax.set(xlabel="Time (s)", ylabel="Response", title="Missing reading retained")
ax.legend(loc="upper left")
dm.simple_layout(fig, margin="2mm")

# Save this complete script as plot.py before running it.
source_path = Path(__file__)
code = source_path.read_text(encoding="utf-8")
report = {"lint": [asdict(item) for item in dm.lint_code(code)],
          "visual": [asdict(item) for item in dm.validate_figure(fig)]}
Path("output").mkdir(exist_ok=True)
Path("output/figure-v1.py").write_text(code, encoding="utf-8")
Path("output/figure-v1-report.json").write_text(json.dumps(report, indent=2))
dm.save_formats(fig, "output/figure-v1", formats=("png", "pdf"),
                bbox_inches=None)
```

Read every lint and visual finding, including its severity, message and detail.
`CHECK_FAILED` means validation is incomplete. An empty heuristic warning list
cannot prove visual or scientific correctness. `save_formats` returns `None`;
its return value is not clean-validation evidence. It saves despite warnings.
Preserve advisory findings and explain intentional choices rather than hiding
warnings or changing requested colors, dimensions or local overrides.

**Open and inspect the actual `output/figure-v1.png` with the agent's image
viewer**, then review the PDF at its target physical size (or rasterize the PDF
and inspect that page). Check the gap, labels, fonts, legend, clipping and data.
Reading filenames, file sizes or the JSON report is not image review. If the
agent has no image reader, disclose that missing step; do not claim completion.

## Revise to a separate stem and hand off

After reviewing v1, copy `plot.py` to `plot-v2.py`. In the copy, replace all
`figure-v1` output stems with `figure-v2` and insert this requested label-only
revision immediately before `source_path = Path(__file__)`. Run
`MPLBACKEND=Agg python plot-v2.py`, then inspect v2 PNG/PDF and its full report. This retains
v1 source/files and saves the exact revised script under the new stem.
Repeated “one more step” acts on retained current label values, not the preset
base; retain previous local edits when preparing another revision.
The insertion point is after the original `dm.simple_layout(fig, margin="2mm")`,
before report/export. Follow the local-revision recipes in
`dm.get_prompt("03-recipes")`: keep already-fitting geometry. Ordinary label
enlargement permits necessary fitting through the existing method/settings,
starting from the original kwargs and adjusting only needed margins/spacing.
Preserve the physical canvas, panel/container allocations and explicit ratios,
data, colors, other typography and legend's intended location. Keep any active
native layout engine configuration; do not reset defaults or switch engines.
An explicit Axes-position lock overrides fitting: retain it and disclose any
clipping/conflict. Ask one relevant question only if protected constraints must
change or the safe existing fit is unclear; retain the original. Explicit user
instructions take precedence. Inspect actual PNG/PDF and bounds after draw and
export, and report necessary Axes movement without claiming position invariance.
Fit depends on the content and constraints, not a universal pixel/mm tolerance.
The same recipes cover a selected plain `Line2D` dash edit and its known
existing legend sample; update both in place without rebuilding the legend.

```python
# Insert before the source/report/export block in plot-v2.py.
for label in (ax.xaxis.label, ax.yaxis.label):
    label.set_fontsize(label.get_fontsize() + 1)
# Draw and inspect changed labels before deciding whether a refit is needed.
fig.canvas.draw()
# Compare actual axes/legend bounds after draw/export; inspect for clipping.
# If needed and not geometry-locked, fit through the existing method/settings.
```

Hand off the exact source, PNG, PDF and full report for each revision, the
chosen preset and physical canvas, data/gap policy, requested changes, retained
warnings and what images were actually reviewed. Preserve original artifacts;
use another stem for the next revision. These deterministic examples demonstrate
the APIs, not evidence that an autonomous agent successfully followed the loop.
