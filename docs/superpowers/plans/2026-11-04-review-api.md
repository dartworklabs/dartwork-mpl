# `dm.review`: one call for the review loop and edit diffs (masterplan stages 3–4)

Date: 2026-11-04. Scope: the agentic-workflow masterplan
(`docs/superpowers/specs/2026-10-22-agentic-workflow-masterplan.md`), stage 3
"검토 루프 (얇게 시작)" and stage 4 "`dm.review(..., baseline=...)`은 의도를
판단하지 않는다". The user asked on 2026-11-04 to finish the remaining core work,
so this note records the concrete shape instead of asking again.

## What it is

A thin wrapper over what already exists. It adds no check, no fix and no style:

```python
r = dm.review(fig, "output/figure-v1")          # saves PNG + PDF, reports
r2 = dm.review(fig2, "output/figure-v2", baseline="output/figure-v1",
               allow=["axes[0].ylabel.*"])        # neutral diff vs v1
```

1. `dm.save_formats(fig, stem, formats=formats, validate=False, **save_kwargs)`
   writes the files exactly as today (same bytes for the same figure).
2. `dm.validate_figure(fig, quiet=True)` runs every registered check on the
   figure as saved (`PRESET_OVERRIDE` included: this is the review report).
   The findings are kept as returned, in order, unfiltered.
3. A figure summary is read from the artists (below).
4. With `baseline=`, the summary is compared with the baseline's summary and
   the differences are listed. Nothing is judged: a difference is `allowed`
   only when its path matches an `allow=` pattern the caller gave.
5. `<stem>.review.json` is written next to the images, so a later process (the
   next revision script) can pass the stem or this path as `baseline=`.
6. Unless `quiet=True`, a short report is printed: files, findings grouped by
   check id with counts, completeness, and the changes. The grouping is only in
   the printout; `Review.findings` keeps every original finding.

Not done here: running scripts (a CLI waits for evidence from the evals),
automatic fixes, deciding whether a change was requested, new validation checks,
image comparison, anything in MCP (names, order, schemas, docstrings frozen).

## Signature

```python
def review(
    fig: Figure,
    stem: str | os.PathLike[str],
    *,
    baseline: Review | str | os.PathLike[str] | None = None,
    allow: Iterable[str] = (),
    formats: tuple[str, ...] = ("png", "pdf"),
    quiet: bool = False,
    **save_kwargs: Any,          # passed to save_formats (dpi=, bbox_inches=, ...)
) -> Review
```

- `stem` must not end in an image suffix (`.png`, `.pdf`, ...): a new API can
  refuse the ambiguity `save_formats` only warns about. `ValueError`.
- `baseline` as a path: `*.review.json` is read as is; anything else is a stem
  and `<stem>.review.json` is read. Missing file or other schema: `ValueError`.
- `allow` patterns: `*` matches any run of characters, everything else is
  literal (`axes[0]` is that Axes, `axes[*]` any).

## Return value: `Review` (frozen dataclass, `dartwork_mpl.figure_review`)

| field | type | meaning |
|---|---|---|
| `paths` | `dict[str, Path]` | format → written file, plus `"json"` |
| `findings` | `list[VisualWarning]` | `validate_figure` output, untouched |
| `complete` | `bool` | `False` when any `CHECK_FAILED` finding exists |
| `incomplete_checks` | `list[str]` | the check ids those findings name |
| `summary` | `dict` | JSON-ready figure summary (schema 1) |
| `changes` | `list[Change] \| None` | `None` without a baseline |

`Change(path, before, after, allowed)`; `before`/`after` are `None` for an
added/removed entry. Properties: `Review.warnings` (WARNING findings),
`Review.unexpected` (changes not allowed). `Review.to_dict()` is the JSON
document; `str(review)` is the printed report.

## Summary (schema 1)

Only what the masterplan names: titles, labels, series, ranges, legend and text
outside the canvas, per Axes in `fig.axes` order. Floats are rounded to six
significant digits so a re-render does not report noise.

```
figure: size_in, dpi, suptitle / supxlabel / supylabel {text,size,weight,color},
        texts, legends, subfigures[k] (the same fields, nested)
axes[i]: kind ("rectilinear", "polar", "3d", ...), position (fraction, 3 decimals)
  title.left|center|right {text,size,weight,color}
  xlabel / ylabel (/ zlabel on 3-D) {text,size,weight,color}
  xlim, ylim (zlim), xscale, yscale (zscale); xticks / yticks (zticks) {labels in view, size}
  series[j]: kind (line|bar|scatter|area|lines|image|patches|collection), label
             (a container's name for errorbar / hist parts), n, color, colors
             (digest when not uniform), line width / style / marker, scatter sizes,
             data (digest of shape, mask and exact values; 3-D from 3-D data)
  legends[k]: title, labels, ncols, inside   (every legend, add_artist ones too)
  texts: [{text,size,weight,color}]  (ax.texts: annotations, notes)
  insets[k]: the same fields for ax.inset_axes children
outside_canvas: [{where, text, beyond_px{left,bottom,right,top}}]
               (3-D tick labels are not measured: mplot3d keeps them at stale positions)
```

`data` is a digest, not the values: it says whether a series' values changed
without making the summary an eval snapshot API. Nothing in it is rounded
(re-rendering the same data gives the same bits); display fields (sizes,
limits) are rounded to six significant digits.

Diff paths flatten this tree: `axes[0].ylabel.text`, `axes[0].series[1].color`,
`axes[0].legends[0].labels`, `figure.size_in`. Lists of records compare by
index; lists of scalars compare as one value. `None` and empty lists are no
entry, so a first text or legend appears as its own fields only.

## Where it lives

- New slice `dartwork_mpl.figure_review` (`__init__.py` surface `review`,
  `Review`, `Change`; `_summary.py`, `_diff.py`; tests in its `tests/`). Not
  `dartwork_mpl.review`: a package of the same name as the `dm.review` function
  makes `import dartwork_mpl.review` ambiguous.
- `dm.review` exported from the root, listed in `EXPERIMENTAL` (shape may still
  change in a minor release, like `figsize_for`).
- Boundary checker: the slice and its two dependencies (`io` for
  `save_formats`, `validate` for `validate_figure`) with reasons.

## Docs and skill

- `docs/api/review.rst` (autodoc) in the API index; CHANGELOG `Added`;
  `docs/development/api-stability.md` experimental list.
- Skill: `references/review-loop.md` runs `dm.review` for v1 and
  `dm.review(..., baseline=...)` for revisions; `references/editing.md` uses the
  change list to show what an "only X" edit touched; `SKILL.md` review loop
  step names `dm.review` (120-line limit kept).

## Tests

- Same bytes: PNG pixels and PDF page from `review` equal `save_formats` output.
- Findings identical to `validate_figure(fig, quiet=True)`; a forced bbox error
  gives `complete=False` and the check id.
- Summary fields for line, bar, scatter, twin, polar, legend, outside text.
- Baseline: from a `Review`, a stem and a json path; label/colour/limit edits
  listed with paths; `allow` marks them; an unchanged re-render lists nothing.
- Stem with suffix and a missing baseline refuse; nothing is written then.
- Printout groups repeated findings; `quiet=True` prints nothing.
- Installed wheel: `dm.review` runs from a clean venv and the skill references
  shipped in the wheel name it.

## Coordination

`evals/agentic`, `release.yml`, the version and the diagnosis/endpoint docs belong
to the integration session (T3 ee7255af). The skill text change alters what the
next eval measures; it reports the head of this branch to that session before the
main eval runs.
