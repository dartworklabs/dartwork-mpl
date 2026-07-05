# Semantic design-token layer (`dm.tokens`) — Design (P3)

> Program umbrella #411, pillar EO3. Advisory/design by orchestrator; implementation by codex.

## Problem

The v5 **color** system has a versioned JSON SSOT + registered accessors. The rest of the design
system does not: type sizes and line widths live as raw rcParams spread across the mplstyle
fragments, and the only accessors are the imperative offset helpers `dm.fs(n)` / `dm.lw(n)`. The
**semantic** layer — named roles like *body / title / tick* text and *reference / trend / emphasis*
line weights — exists only in the **valuation** repo (`valuation.visualization.theme`:
`fs_annotation/fs_tick/fs_body/fs_emphasis/fs_title`, `lw_reference/lw_trend/lw_emphasis`), coupled
to dartwork-mpl via an editable install. Bespoke chart scripts must import that external clone to
name a token. dartwork-mpl should own its own semantic token layer.

## Design (additive, render-neutral, versioned, exportable)

A new `dm.tokens` module exposing **preset-tracking** semantic accessors, defined by a versioned
JSON SSOT (mirroring the color-v5 SSOT pattern). Nothing about existing rendering changes — these
are new *read* accessors over the active preset's rcParams plus a few literal sizes. This is a
utilities layer (named token roles), not a plotting wrapper — consistent with "utilities not
wrappers".

### SSOT `src/dartwork_mpl/asset/tokens/semantic_tokens.json`
```json
{
  "version": "1",
  "type_scale": {
    "annotation": {"rcparam": "legend.fontsize"},
    "tick":       {"rcparam": "xtick.labelsize"},
    "body":       {"rcparam": "font.size"},
    "label":      {"rcparam": "axes.labelsize"},
    "title":      {"rcparam": "axes.titlesize"},
    "emphasis":   {"rcparam": "font.size", "offset": 1.5}
  },
  "lw_ladder": {
    "hairline":  {"rcparam": "axes.linewidth"},
    "reference": {"rcparam": "grid.linewidth"},
    "trend":     {"rcparam": "lines.linewidth"},
    "emphasis":  {"rcparam": "lines.linewidth", "multiplier": 1.6}
  },
  "scatter_size": {"small": 16, "default": 30, "emphasis": 45}
}
```
Resolution: `value = rcParams[rcparam] (+ offset) (* multiplier)`, read at call time so it tracks
the active preset (exactly how `dm.fs`/`dm.lw` behave). `scatter_size` are literals (matplotlib
`s=` point² areas).

### Module `src/dartwork_mpl/tokens.py`
Callable accessors returning `float` (mirroring `valuation.theme`'s names for drop-in migration):
- Type scale: `fs_annotation()`, `fs_tick()`, `fs_body()`, `fs_label()`, `fs_title()`, `fs_emphasis()`.
- Line-width ladder: `lw_hairline()`, `lw_reference()`, `lw_trend()`, `lw_emphasis()`.
- Scatter: `scatter_size(level: Literal["small","default","emphasis"] = "default") -> float`.
- Introspection: `version() -> str` (the SSOT version) and `as_dict() -> dict[str, float]` returning
  every currently-resolved token value (for export to Typst/web — the "exportable SSOT" payload).

Load the SSOT once at import (module-level, like the color loader). Each accessor reads
`matplotlib.pyplot.rcParams` live. Unknown `scatter_size` level → `ValueError` with the valid set.

### Wiring (`__init__.py`)
`from . import tokens` and add `"tokens"` to `__all__`, so the layer is reachable as `dm.tokens`
(namespace — avoids adding ~15 flat names to the top level). Confirm `tokens` isn't already taken.

## Rationale notes
- Values mirror `valuation.theme` for parity so bespoke scripts can migrate off the external clone.
  (The workspace chart rule `chart-layout-aesthetics` already anticipates these exact scatter tokens
  16/30/45 and flags `lw_emphasis=1.6` for a future review; we keep 1.6 for valuation parity and
  note the open question rather than changing behavior here.)
- These COMPLEMENT `dm.fs(n)`/`dm.lw(n)` (imperative offsets) — they don't replace them; they name
  the common roles declaratively.

## Scope (P3 PR)
- `src/dartwork_mpl/tokens.py` (new), `src/dartwork_mpl/asset/tokens/semantic_tokens.json` (new).
- `src/dartwork_mpl/__init__.py`: `from . import tokens` + `"tokens"` in `__all__`.
- `tests/test_tokens.py`: base values under `scientific` (fs_body 7.5, fs_tick 7, fs_title 8.5,
  fs_annotation 6.5, fs_emphasis 9.0, lw_hairline 0.3, lw_reference 0.3, lw_trend 1.0, lw_emphasis
  1.6, scatter default 30 / small 16 / emphasis 45); preset-tracking (a preset whose `font.size`
  differs — e.g. `presentation` — yields a different `fs_body()`); `as_dict()` has all keys;
  `version()=="1"`; unknown scatter level raises.
- `docs/development/design-tokens.md` (orphan — use MyST frontmatter `---\norphan: true\n---`,
  NOT rST `:orphan:`).

## Acceptance
- `dm.tokens.*` accessors resolve + track the preset; SSOT JSON loaded; new tests green; ruff +
  mypy clean; **existing rendering unchanged** (no mplstyle edits → visual/determinism suites
  unaffected); full suite green. Docs build (`-W`) clean.

## Non-goals
- No regeneration of mplstyle base values from the SSOT (that would change rendered output and risks
  colliding with the concurrent design-SSOT work — deliberately out of scope; this layer *reads*,
  it doesn't *drive* the presets yet).
- No spacing/elevation tokens in this PR (type + line-width + scatter cover the valuation.theme
  parity surface; spacing can follow).
