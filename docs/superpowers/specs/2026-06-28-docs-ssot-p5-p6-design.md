# Docs Design SSOT P5/P6 Design

## Goal

Finish the docs design-system follow-up by making typography and remaining
bespoke widgets read from the same dartwork docs SSOT. The result should feel
like the current docs, only calmer and more internally consistent: same type
roles, same token names, same interaction primitives, and no stray teal/gray
skins living outside the system.

## Current State

The parent plan listed two carry-over defects that are already resolved on
current `main`:

- `dartwork-design.css` now contains a complete dark teal accent ramp for
  `--dm-accent-1` through `--dm-accent-12`.
- The token namespace is already unified on `--dm-*`; no `--rx-*` tokens remain
  in the reviewed design-system files.

The remaining P5/P6 work is concentrated in:

- `docs/_static/font-specimens.css`, which still owns a separate beige/gray
  palette, dark-mode palette, and independent type sizing.
- `docs/_static/dynamic_ux.css`, which still defines `--dm-ux-*` through
  Shibuya `--sy-*` fallbacks and raw hex colors.
- `docs/_static/dynamic_ux.js`, whose validation simulator SVG mock uses
  hardcoded teal/gray/white palette values instead of CSS variables.
- `docs/_static/dm-interactive-styleguide.html` and
  `docs/_static/_overhaul_review.html`, whose scaffold styles should display
  the same type roles and primitive usage they are meant to review.
- `docs/_static/dartwork-design.css` / `docs/_static/dm-interactive.css`,
  which already contain raw size scales but need semantic role aliases that
  downstream widgets can consume.

## Design Direction

Use a conservative SSOT consolidation. Do not redesign the site or introduce a
new visual language. Preserve the Radix/Inter/Shibuya-based feel already on
`main`; move the remaining bespoke CSS and JS onto semantic tokens and shared
primitives.

## P5 Typography

Add semantic type role tokens on top of the existing raw Radix scale:

- `--dm-type-display-size`, `--dm-type-display-line`,
  `--dm-type-display-weight`, `--dm-type-display-spacing`
- `--dm-type-heading-size`, `--dm-type-heading-line`,
  `--dm-type-heading-weight`, `--dm-type-heading-spacing`
- `--dm-type-body-size`, `--dm-type-body-line`, `--dm-type-body-weight`,
  `--dm-type-body-spacing`
- `--dm-type-label-size`, `--dm-type-label-line`, `--dm-type-label-weight`,
  `--dm-type-label-spacing`
- `--dm-type-caption-size`, `--dm-type-caption-line`,
  `--dm-type-caption-weight`, `--dm-type-caption-spacing`
- `--dm-type-mono-size`, `--dm-type-mono-line`, `--dm-type-mono-weight`,
  `--dm-type-mono-spacing`

These aliases should live in `dartwork-design.css` because they are global
semantic roles, not only interactive-control roles. Components may still use
raw `--dm-fs-*` when a one-off optical fit is intentional, but repeated widget
roles must use semantic type roles.

Migrate `font-specimens.css` to these roles and to the existing color/surface
tokens:

- Card-like specimen containers use `--dm-bg-panel`,
  `--dm-border-faint`, `--dm-radius-4`, and existing spacing tokens.
- Headings, descriptions, labels, samples, and metadata use the semantic type
  roles above.
- Controls use the shared `.dm-chip`, `.dm-slider`, `.dm-code`, and form-token
  styling where possible, without changing the generated docs markup more than
  necessary.
- Dark-mode overrides should mostly disappear because the same tokens already
  adapt under `html.dark` and `body[data-theme="dark"]`.

## P6 Bespoke Widgets

Repoint the dynamic UX layer to the same token system:

- In `dynamic_ux.css`, define `--dm-ux-*` aliases from `--dm-*` tokens, not
  `--sy-*` fallbacks or raw hex values.
- Replace hardcoded accent/error/background colors with `--dm-accent-*`,
  `--dm-warning-*`, `--dm-info-*`, `--dm-success-*`, `--dm-gray-*`,
  `--dm-bg-*`, `--dm-border-*`, and `--dm-text-*`.
- Replace repeated control styling with primitive-equivalent rules:
  `.dm-chip` for pills and filters, `.dm-slider` for range controls,
  `.dm-icon-btn` for copy/toggle affordances, `.dm-code` for code-like output,
  and `.dm-tabs` / `.dm-tab` or their existing compatibility selectors for tab
  strips.
- In `dynamic_ux.js`, make the validation simulator SVG read CSS variables
  at runtime. SVG attributes must receive resolved color strings, but those
  strings should come from computed CSS custom properties on the widget/root.
- Keep the install picker behavior and DOM shape already established by P3; do
  not rework it except where type/color tokens are needed.

## Review Harnesses

The review harnesses should demonstrate the actual SSOT:

- `dm-interactive-styleguide.html` keeps linking the shipping CSS files and
  should add a compact typography role section.
- `_overhaul_review.html` keeps serving the landing hero, live install picker,
  and link to the styleguide; its scaffold styles should use the same type
  roles rather than literal font sizes and weights.
- Any swatches in the styleguide should use token-backed gradients or CSS
  variables instead of raw inspection-only hex, except where the content is
  explicitly demonstrating a color value.

## Non-Goals

- Do not change the docs navigation, content hierarchy, or Shibuya theme.
- Do not remove existing shipped widgets.
- Do not introduce a new dependency.
- Do not rename `--dm-*` tokens or revive any `--rx-*` / `--dw-*` migration.
- Do not commit generated `docs/_build/**` output.
- Do not commit color reference SVGs outside `docs/examples_gallery/**` or
  `docs/examples_source/**`.

## Verification

Implementation is complete only when all of the following are true:

- Source scans show no `--rx-*`, `#14b8a6`, `#0d9488`, or `#8b5cf6` in the
  active design-system files.
- `font-specimens.css` no longer uses its own raw beige/gray/dark palettes for
  normal surfaces and text.
- `dynamic_ux.css` and the validation SVG code in `dynamic_ux.js` use `--dm-*`
  tokens or computed token values for their skin.
- The review harnesses render in light and dark mode with no obvious text
  clipping, invisible active state, or collapsed controls.
- `dm-interactive.css` still loads last in `docs/conf.py`.
- `python -m sphinx -b html -q docs docs/_build/html` exits cleanly after
  filtering only the known `tight_layout` comparison warning.
- A visual check is captured for both light and dark themes on
  `_overhaul_review.html` and `dm-interactive-styleguide.html`.
