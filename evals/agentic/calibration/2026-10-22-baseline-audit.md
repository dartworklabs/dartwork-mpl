# Baseline audit — `baseline-main-20261022`

Run: 40 cases × 2 hosts (Claude `sonnet`, Codex default), no skill, `--hide-grading`,
one pinned wheel from `main`. Records live under the eval records root
(`baseline-main-20261022/` there). Per unit: the figure is
`<host>/<case>/noskill-r1/artifacts/figure.png` and the source is the `plot.py` of the
project named in that unit's `run.json`. Sources of the units used as controls are copied
verbatim into `../fixtures/calibration/`.

Method: every unit the pre-calibration scorer failed (26 of 80) was judged from its figure
and its `plot.py`, then classed as a **true failure** (the agent's output is wrong) or a
**scorer false failure** (the output is correct and the scorer rule was wrong).

## Counts

| host | failing (pre-calibration) | true failures | scorer false failures |
|---|---|---|---|
| claude | 12 | 0 | 12 |
| codex | 14 | 1 | 13 |

## Units

`old failure` is what the pre-calibration scorer reported. `fixed by` names the rule
change (section below) that reclassified a false failure.

| host | case | old failure | verdict | reason | fixed by |
|---|---|---|---|---|---|
| claude | e05-highlight-korea-en | preservation | false | Korea highlighted, others grey; legend replaced by one end label per country; series props were keyed by label | d |
| claude | e07-end-labels-en | preservation | false | Lines labelled at their ends, legend removed, data and styles unchanged; label-keyed props | d |
| claude | e08-end-labels-ko | preservation | false | Same as e07 (Korean labels) | d |
| claude | g04-scatter-fit-plants | contamination | false | Correct scatter and fits; `../` only inside its own `.venv` | a |
| claude | g06-hist-response | dist unchecked; 2 lines unexplained | false | Step/stepfilled histograms of all rows, ECDFs, median lines, p95 markers | step hist, ECDF, c |
| claude | g07-box-exam | 4 scatters unexplained | false | Violin + box; dots are every real score, jittered sideways | c |
| claude | g08-stacked-area-energy | contamination | false | Correct stacked areas; `ls ../` saw only the sandboxed work root | a |
| claude | g09-small-multiples-ko | panels not named; context lines unexplained | false | Left titles name each city; grey lines are the other cities' real series | b, c |
| claude | g10-dashboard-kpi | users not found; lines unexplained | false | Users plotted in thousands, "(thousands)" in the panel title | e |
| claude | g11-dual-axis-ko | contamination | false | Correct dual axis; `../` inside its own `.venv` | a |
| claude | g20-slides-renewables | 1 line unexplained | false | Line plus first/last highlight markers (copies of real points) | c |
| claude | g21-size-17x9 | contamination | false | Correct 17 × 9 cm stacked bars; `../../../bin/python` from inside `.venv` | a |
| codex | e04-legend-outside | contamination | false | Legend outside; `find .. -name AGENTS.md` returned only its own project | a |
| codex | e07-end-labels-en | preservation | false | Same as claude e07 | d |
| codex | e09-look-better-en | 2 scatters unexplained | false | Cleaner two-panel chart; end dots repeat real last points | c |
| codex | g04-scatter-fit-plants | points, fits not named; scatters unexplained | false | Legend built from proxy `Line2D` handles (colour + marker + line) | proxy legends |
| codex | g06-hist-response | dist failed; ECDF lines, p95 dots unexplained | false | `stairs` fractions, labelled ECDFs, p95 dots at the true percentiles | step hist, ECDF, c |
| codex | g07-box-exam | 4 scatters unexplained | false | Box + jittered real scores | c |
| codex | g10-dashboard-kpi | panels not named; end lines unexplained | false | Each card named by its top in-axes text; dots on real last points | b, c |
| codex | g13-uneven-panels | contamination | false | Correct uneven panels; `find ..` saw only its own project | a |
| codex | g17-paper-two-panel | panel-label regex | false | Titles "(a) Annual GDP growth" / "(b) Average, 2012–2023"; regex wanted a bare "a" | panel_labels |
| codex | g18-report-traffic | panels not named; markers unexplained | false | Panels named by in-axes texts; signup gap kept; end dots | b, c |
| codex | g19-slides-share-ko | Others bar not found | false | "Others" shown as 기타 on a Korean slide | case alias |
| codex | g20-slides-renewables | contamination; 1 scatter unexplained | false | Correct line; `find ..` own project; end dot repeats the last point | a, c |
| codex | g23-vague-en | execution (figure older than plot.py) | **true** | The last `plot.py` edit (20 s after the last save) was never executed; the saved figure is from an earlier version | — |
| codex | g24-vague-ko | 4 lines unexplained | false | Leader lines from each series end to its label | c |

## Rule changes (general, not per case)

- **a. Contamination** (`run.py`). Every path a tool call or its output names is resolved
  (absolute, `~`, or `..` relative to the project; symlinks followed). Contamination is a
  resolved path inside a grading root: a repo checkout, the records tree, or another
  project. The bare `../` substring rule and the name fragments (`evals/agentic`,
  `manifest.json`, ...) are gone. `score.py` recomputes contamination from the stored
  transcripts, so a rescore applies the rule; the run-time value stays as
  `contamination_at_run`.
- **b. Naming** (`views.panel_names`). A panel names a series by its centre/left/right
  title or y label (titles via the public `ax.get_title(loc)`), else by a text inside the
  panel, else (single data panel) by the suptitle or a figure text — regardless of how many
  context lines the panel holds. Only texts naming exactly one series count; the top-most
  wins. End labels must be texts of the same panel (another panel's title is not one).
- **c. Derived artists** (`derived.py`). An unclaimed artist is explained when its data
  follows from the input: constant reference line; repeat of claimed points; contiguous
  run of an input column; jittered observations of one distribution group; ECDF;
  points at a group's mean/median/min/max/linear quantile; least-squares fit; ≤ 4-vertex
  leader from a claimed point to a text. Contracts claim their artists even when they fail.
- **d. Edit touch sets** (cases + `metrics.preservation`). Series properties are keyed by
  their data digest, not their label. Each explicit edit's `target` lists what the request
  legitimately touches; `max_new_texts` caps added texts. Highlight (e05) may restyle all
  series and replace the legend with one label per series; end labels (e07, e08) may
  remove the legend and the series labels.
- **e. Display scale** (`oracle.c_series`, `c_bars`). One factor per artist (×1e-3,
  ×1e-6, ×100, ...) is accepted only when a visible text of its panel states the unit.
- Also: step histograms (`stairs`, `hist` step types) and ECDFs as distribution forms;
  proxy legend handles name the same-coloured artists of their axes; `panel_labels` check
  replaces g17's regex; g19 accepts 기타 for Others.

## Rescore (same records, no reruns)

| host | task success before | after | contaminated before | after |
|---|---|---|---|---|
| claude | 28/40 | 40/40 | 4 | 0 |
| codex | 26/40 | 39/40 | 3 | 0 |

No unit went from pass to fail. Remaining failure: codex g23 (true, unexecuted edit).

## Controls added

`../test_calibration.py` (24 tests). 13 real units above must pass (each fails on the
pre-calibration scorer); codex g23 must fail on its recorded timeline; six mutations of real
sources must fail (context lines shifted, unit text removed, leader moved off the data,
p95 marker moved, jitter values shifted, an extra text in an end-label edit); the real
`../` tool calls are clean, while climbing into another project, the records or the repo
is contamination.
