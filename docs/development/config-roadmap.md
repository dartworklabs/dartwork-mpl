# `dm.config` expansion roadmap

Audit of every `dm.__all__` function for **bool / Literal kwargs whose
default the user might reasonably want to flip project-wide**. Output
of issue [#311 (B19 — config audit)](https://github.com/dartworklabs/dartwork-mpl/issues/311);
input to issue [#304 (M1 — `dm.config` expansion)](https://github.com/dartworklabs/dartwork-mpl/issues/304).

The full SSOT for the singleton lives in
[`src/dartwork_mpl/config.py`](https://github.com/dartworklabs/dartwork-mpl/blob/main/src/dartwork_mpl/config.py).
The user-facing cookbook lives in
[`docs/usage_guide/config.md`](../usage_guide/config.md).

## Method

Walked every entry in `dm.__all__` (78 names, dartwork-mpl 0.5.1 +
unreleased PR #329). For each callable, enumerated `bool` defaults and
`Literal[...]` enum defaults. Classified each into one of four
buckets:

| Class | Action |
|---|---|
| **Add to config now** | Strong global default, no preset conflict, clear use case |
| **Add to config later** | Niche; wait until 2+ users report wanting it |
| **Keep per-call only** | Truly call-site decision (file paths, individual diagnostic toggles) |
| **Should be a preset attribute** | Belongs in `style.use(...)`, not `dm.config` |

## Summary

- 20 functions surfaced bool / Literal kwargs (out of 70 callables in
  `dm.__all__`)
- **6** kwargs qualify for **"Add to config now"** — pass to issue #304 (M1)
- **5** qualify for **"Add to config later"** — track but don't ship
- **15** stay **per-call only** — diagnostic flags, position selectors, etc.
- **0** should move to preset — none of the candidates are style-shaped

## "Add to config now" — feeds issue #304 (M1)

Highest priority. Each of these is a project-wide default a typical
user might want to flip once and forget.

| Field | Current default | Source kwarg(s) | Rationale |
|---|---|---|---|
| `validate_default` | `True` | `save_formats(..., validate=...)` | Validation is loud-by-default — some users prefer opt-in. Currently the only escape is `validate=False` on every save call. Per-project toggle is the obvious fix |
| `validate_quiet` | `False` | `save_formats(..., validate_quiet=...)` | Same call site; same project-wide rationale. CI runs typically want quiet, interactive runs want verbose |
| `auto_apply_fixes` | `False` | `validate_with_fixes(..., auto_apply=...)` | Some teams want every save to auto-fix detected layout issues; today they thread the kwarg through every call site |
| `verbose_layout` | `False` (auto_layout) / `False` (simple_layout) / `False` (tight_crop) | three layout funcs | Three call sites converge on the same "tell me what layout did" toggle — unify under a single config field |
| `legend_outside_default` | `False` | `optimize_legend(..., outside=...)` | Plot-heavy reports often want every legend outside; flipping once is cleaner than threading the kwarg |
| `allow_nan` | `False` | `validate_data(..., allow_nan=...)` | Some data pipelines treat NaN as semantic ("missing data") and want validators to accept it. M4 (#306) `nan_strategy` partially overlaps — coordinate so we don't ship two knobs for the same intent |

## "Add to config later" — defer unless requested

Conceptually valid but unlikely to need the global default until we
see real demand.

| Field | Current default | Rationale to defer |
|---|---|---|
| `use_all_axes` (simple_layout) | `True` | Niche; the alternative is "GridSpec edges only," which advanced users already know to set per call |
| `validate_quiet_default` for `validate_figure(quiet=...)` | `False` | `validate_figure` is rarely called directly — the SaveFlow's `validate_quiet` covers it |
| `include_reversed` (list_colormaps) | `False` | A docs / introspection helper; once-off use, per-call decision is fine |
| `add_total` (plot_diverging_bar) | `True` | Plot-specific; per-call decision feels right |
| `validate_with_fixes(verbose=...)` | `True` | Default is already correct for both audiences (interactive + CI). Toggle would be cosmetic |

## "Keep per-call only" — stays as a kwarg, no config field

Either truly call-site (position/axis selectors) or already covered
by another singleton (style preset).

| Function | Kwarg | Why per-call |
|---|---|---|
| `format_axis_millions`, `..._billions`, `..._currency`, `..._si` | `axis: 'x' \| 'y' \| 'both'` | Axis selection is a per-figure decision; a project-wide default would be misleading |
| `format_axis_currency` | `position: 'prefix' \| 'suffix'` | Currency convention is regional; if anything belongs in a *style preset*, not config |
| `rotate_tick_labels` | `axis`, `ha` | Same — per-figure layout decision |
| `make_palette` | `kind: 'categorical' \| 'sequential' \| 'diverging'` | Choice is *intent-driven* per call (visualising categories vs. magnitudes vs. polarity). Wrong shape for a global default |
| `plot_colors` | `sort_colors`, `show_hex` | Diagnostic display options for a one-shot palette dump |
| `plot_colormaps` | `group_by_type` | Same as above — diagnostic display option |
| `save_and_show` | `close_figure` | Already in `dm.config` via the orphan-tick chain; the kwarg is the per-call escape hatch |
| `Config` | `adopt_orphan_tick_font`, `warn_on_orphan_tick_adoption` | Already shipped (this is the singleton itself) |

## "Should be a preset attribute" — none today

No candidate kwarg surfaced that genuinely belongs in `style.use(...)`
rather than `dm.config`. The two singletons stay cleanly separated:
preset = *style*, config = *behaviour*.

## Recommended top-priority bundle for M1 (#304)

If issue #304 ships exactly one batch, the minimum-viable expansion is:

```python
@dataclass
class Config:
    # ... existing fields ...
    validate_default: bool = True
    validate_quiet: bool = False
    auto_apply_fixes: bool = False
    verbose_layout: bool = False
    legend_outside_default: bool = False
    allow_nan: bool = False
```

Six new fields. Each unblocks a documented call-site pain point.
Each follows the same resolution chain already proven by
`adopt_orphan_tick_font`: per-call kwarg (`None`) → `dm.config` →
hard-coded default.

Implementation cost is ~1 PR per field (or one bundle PR with six
small surface changes). Test cost is light — the kwarg → config
fallback is a single pattern, already tested for the two existing
fields.

## Out-of-scope kwargs already known to be on the radar

These appear in other audit issues; not re-evaluated here.

- `grid_style` — issue [#302 (H2 — `dm.add_grid` reintroduction)](https://github.com/dartworklabs/dartwork-mpl/issues/302)
- `respect_constrained_layout` — issue [#303 (H3 — `constrained_layout` compat)](https://github.com/dartworklabs/dartwork-mpl/issues/303)
- `nan_strategy` — issue [#306 (M4 — `validate_data(nan_strategy=...)`)](https://github.com/dartworklabs/dartwork-mpl/issues/306) (coordinate with `allow_nan` above)
- `legend_location` — covered by `legend_outside_default` above
- `margin_default` — preset territory, not config; preset attribute already exposes this

## Re-running this audit

```bash
python -c "
import dartwork_mpl as dm
import inspect
for name in sorted(dm.__all__):
    obj = getattr(dm, name)
    if not callable(obj):
        continue
    try:
        sig = inspect.signature(obj)
    except (ValueError, TypeError):
        continue
    for p in sig.parameters.values():
        d, a = p.default, str(p.annotation)
        if isinstance(d, bool) or 'Literal' in a:
            print(f'{name:30s} {p.name:30s} = {d!r}  :: {a}')
"
```

Re-run after every PR that adds a new public `dm.__all__` entry. If a
new bool / Literal kwarg lands, it should appear in one of the four
buckets above before the next minor release.
