# Orphan tick labels adopt axis-label font style

- **Date:** 2026-06-03
- **Status:** Approved (design)
- **Repo:** `dartwork-mpl`
- **Author:** agent + user (lesthesia)

> **Superseded default (2026-08-09):** The feature remains available, but
> `Config.adopt_orphan_tick_font` now defaults to `False`. This document
> preserves the original default-on design for historical context.

## Problem

When an axis carries tick labels but **no axis label**, the tick labels
become the most prominent textual descriptor of that axis. Under every
dartwork-mpl preset the tick labels are styled *lighter* than the axis
label (e.g. `report-kr`: tick weight `300` vs axis-label weight `400`;
`base`/`scientific`: tick size `7` vs axis-label size `7.5`). The result
is that a self-describing axis (e.g. month names on x with the metric in
the title) renders its descriptor in the *subordinate* tick style,
breaking the intended visual hierarchy.

## Goal

When — and only when — an axis has no axis label, its tick labels (and
its scientific offset text) should **adopt that axis's label font
style**. The x-axis and y-axis are judged **independently**: an axes
with a y-label but no x-label restyles only the x tick labels.

When an axis label *is* present, the tick labels are left untouched
(they keep their current/default style — "원래의 스타일").

## Non-goals

- Color is **not** copied (`axes.labelcolor` stays off-limits); tick
  colors set by the user are preserved.
- No change to `helpers/quality.py`'s "Missing x-axis label" warning
  (that is a semantic-completeness check, orthogonal to styling).
- No reversal of user-customized tick fonts when a label *is* present.

## Behavior specification

For each `Axes` in the figure, for each of its two axis directions
(x, y) **independently**:

1. Read the axis label's text via `ax.get_xlabel()` / `ax.get_ylabel()`.
2. **If the label text is non-empty** (after `.strip()`): do nothing to
   that axis's tick labels or offset text.
3. **If the label text is empty**: collect that axis's *visible,
   non-empty* tick labels plus its offset text (if visible & non-empty),
   and set each one's **fontsize, fontweight, fontfamily, fontstyle** to
   match the axis label Text object (`axis.label`).

### Style source

The font is read from the `axis.label` Text object, **not** from
rcParams. Verified empirically: an axis whose label text is `""` still
carries the rcParams-derived font (`axes.labelsize`/`axes.labelweight`/
`font.family`) on its label Text object. Reading from `axis.label`:

- respects any per-axis label-font customization the user made;
- is a **stable source we never mutate**, so repeated application is
  idempotent (no drift — we never read back our own modified tick font).

### Properties copied

`fontsize`, `fontweight`, `fontfamily`, `fontstyle`. Not color, not
stretch/variant.

## Timing (the hard part — verified)

Two facts were confirmed by experiment against the installed matplotlib:

1. **Persistence:** setting `set_fontsize`/`set_fontweight` on tick label
   Text objects survives a plain redraw, a locator regeneration
   (xlim change + figure resize), and the `savefig` draw. matplotlib
   copies the prototype tick's label properties to regenerated ticks via
   `_copy_tick_props`, so styling the existing ticks propagates to any
   ticks created later.
2. **Measurement coupling:** enlarging tick fonts grows their rendered
   extent, which feeds `simple_layout`'s margin computation. Therefore
   the adoption must happen **before** the extent is measured.

**Resolution:** inside `simple_layout`'s convergence loop, the core
adoption runs **immediately after each iteration's `fig.canvas.draw()`
and before extent measurement**. This guarantees (a) every margin
measurement reflects the styled tick size and (b) if a locator
regenerates ticks mid-loop, they are re-styled the next iteration.
After `set_*`, `Text.get_window_extent(renderer)` re-measures (stale
flag), so no extra `draw()` is needed before measuring.

## API

```python
# layout.py — private core. Assumes ticks already drawn; no draw() call.
def _adopt_axis_label_font_core(fig: Figure) -> None: ...

# layout.py — public standalone. Draws once, then applies.
def adopt_axis_label_font(fig: Figure) -> None: ...

# simple_layout gains a default-on toggle.
def simple_layout(fig, ..., adopt_orphan_tick_font: bool = True) -> None: ...
```

- Exported from `__init__.py`: `adopt_axis_label_font`.
- `simple_layout` calls `_adopt_axis_label_font_core(fig)` after each
  iteration's draw when `adopt_orphan_tick_font` is `True` (default).
- `dm.auto_layout` forwards to `simple_layout`, so it inherits the
  behavior automatically.
- Default-on ⇒ applies across the existing chart corpus (any script
  calling `simple_layout`/`auto_layout`). Disable per-call with
  `adopt_orphan_tick_font=False`, or drive manually with
  `dm.adopt_axis_label_font(fig)`.

## Edge cases

| Case | Handling |
|---|---|
| Unlabeled axis with no tick labels (`set_xticks([])`) | nothing to style → skip |
| Shared axes with hidden inner ticks | invisible/empty ticks skipped (same filter as existing layout code) |
| Axis label present + user-customized tick font | untouched (no clobber) |
| Re-entrancy: lay out unlabeled, then add label, lay out again | already-styled ticks remain styled (rare; normal flow sets labels first). Documented in docstring. |
| polar / 3D / non-standard axes | property access wrapped in try/except; failures skip that axis |
| offset text (`1e9`, `×10⁶`) on unlabeled axis | adopts axis-label font (treated like tick labels) |

## Testing (`tests/test_orphan_tick_font.py`, Agg backend)

- Unlabeled axis + ticks → tick font matches `axis.label` (size, weight, family, style).
- Labeled axis → tick font unchanged.
- x/y independence: y-label only ⇒ only x ticks adopt.
- Offset text adoption under `ScalarFormatter` `1e9`.
- Idempotency: two applications yield identical font.
- `adopt_orphan_tick_font=False` ⇒ no change.
- `scientific` preset (size 7→7.5 differs): after `simple_layout`, the
  bottom margin reflects the enlarged orphan x-tick extent.
- Standalone `adopt_axis_label_font(fig)` works after manual draw.

## Rollout

- `CHANGELOG.md` entry under a new section.
- Patch/minor version bump (`0.4.1` → `0.4.2`) decided in the plan.
