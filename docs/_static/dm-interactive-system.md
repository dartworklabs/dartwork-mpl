# dartwork-mpl docs — Interactive Design System (SSOT)

> Single source of truth for every **interactive** control in the docs.
> Foundation for the 2026-06 consistency overhaul. Pairs with
> `dm-interactive.css` (implementation), `dm-interactive-styleguide.html`
> (living reference), and `_overhaul_review.html` (visual checkpoint).

## Why this exists

The docs grew three competing visual languages for interactive UI:

| Language | Where | Problem |
|---|---|---|
| Radix teal `#12a594` (`--dm-accent-9`) | dartwork-design.css Tier 1–6 (modern overlay) | the intended system |
| Legacy teal `#0d9488` / `--accent-9` | older custom.css widgets, pickers | competes, off-hue |
| Landing **purple** `#8b5cf6` | landing CTA buttons (light mode only) | a third accent |

…and most widgets (palette/fonts/colormap pickers, compare/wipe toggles)
ship their own hardcoded-hex `<style>` blocks instead of inheriting tokens.
The install picker was caught half-migrated: `.dm-ip-tab { background:
transparent !important }` shipped without the matching active fill, so the
selected Tool/OS button rendered **transparent + white text = invisible**.

The overhaul collapses everything to **one token system + one primitive per
interaction pattern**.

Legacy literals in this document are diagnostic examples only. In the current
shipping docs surface, component CSS and generated widget HTML must use
`--dm-*` / `--dm-i-*` tokens plus `is-active` and ARIA state. Hardcoded legacy
accent values are confined to historical notes and explicit comparison POCs.

## Token SSOT

Raw scale lives in `dartwork-design.css :root` (`--dm-*` Radix Slate + Teal,
`--dm-radius-*`, `--dm-space-*`, `--dm-weight-*`) with dark-mode counterparts
under `html.dark`. **Do not introduce new hex.** Interactive components never
reference the raw scale directly — they go through the *semantic interaction
tokens* defined at the top of `dm-interactive.css`:

| Semantic token | Aliases | Use |
|---|---|---|
| `--dm-i-track` | `--dm-gray-a3` | segmented / slider track |
| `--dm-i-thumb` | `--dm-bg-panel` | segmented active surface |
| `--dm-i-active-soft` | `--dm-accent-3` | soft active wash (chips, icon-hover) |
| `--dm-i-active-text` | `--dm-accent-11` | **text on any active/soft fill (AA both themes)** |
| `--dm-i-active-line` | `--dm-accent-9` | underline / handle / ring / primary fill |
| `--dm-i-code-surface` | `--dm-gray-2` light / `--dm-gray-3` dark | command surface |
| `--dm-i-border` | `--dm-border-faint` | hairline |
| `--dm-i-focus` | `--dm-accent-9` | `:focus-visible` ring |

Retuning the interaction look = edit these aliases in one place.

## Typography roles

`dartwork-design.css` also defines semantic type aliases for docs scaffolds and
interactive surfaces:

| Role | Tokens | Use |
|---|---|---|
| Display | `--dm-type-display-*` | page/styleguide hero titles and specimen hero samples |
| Heading | `--dm-type-heading-*` | panel titles, specimen card headings |
| Body | `--dm-type-body-*` | readable descriptions and sample body text |
| Label | `--dm-type-label-*` | control labels, row labels, compact buttons |
| Caption | `--dm-type-caption-*` | metadata, badges, uppercase section labels |
| Mono | `--dm-type-mono-*` | token names, weights, file names, numeric tags |

Component CSS should depend on these roles, not raw `--dm-fs-*` values, unless
the page is deliberately demonstrating a size scale.

## Hard rules (a11y + cascade)

1. **Active ≠ background-only.** The active cue lives on a *separate surface*
   (segmented thumb), a *different property* (underline `border-bottom`), or a
   *soft wash with its own text token* — never a bare `background` that has to
   out-fight a `transparent !important` base. (This is exactly what broke the
   install picker.)
2. **Never white-on-accent-9.** `#fff` on `--dm-accent-9` ≈ 2.5:1 → fails AA.
   Active text on soft/teal is always `--dm-i-active-text` (`--dm-accent-11`).
   Solid teal fill is reserved for *large UI* (the primary CTA), where ~3:1 is
   acceptable for UI text.
3. **`:focus-visible` is a distinct ring** (`outline: 2px var(--dm-i-focus);
   offset 2px`) so "focused" and "selected" never collapse into one cue.
4. **Real controls.** Every primitive wraps a `<button>` / `<a>` / `<input>`
   with the right ARIA state (`aria-pressed`, `aria-selected`, `aria-label`).
5. **Theme-adaptive only.** No hardcoded navy/slate/hex in component rules.
6. **Motion via `transform`** + honor `prefers-reduced-motion`.

## Primitives

| Primitive | Class | Active cue | Maps from |
|---|---|---|---|
| Segmented control | `.dm-seg` / `.dm-seg__thumb` / `.dm-opt` | sliding panel thumb, or `.no-thumb` static fill for tiny groups | install picker Tool/OS, CVD toggle, example view toggle, colormap type toggle, interpolation comparison toggle, tone toggles |
| Underline tab | `.dm-tabs` / `.dm-tab` | 2px `accent-9` underline | doc tab-sets (`.sd-tab-set`), generated palette explorer tabs, palette picker namespaces, font picker families, before/after compare widgets |
| Soft chip | `.dm-chip` (+`.dm-chip__x`) | `accent-3` wash + `accent-11` text | gallery/FAQ filter pills, palette choices, evolution milestones, favorites tray |
| Field/input | `.dm-field` / `.dm-input` | neutral input surface + teal focus ring | gallery search, color search, FAQ search |
| Swatch tile | `.dm-swatch` | teal double-ring | palette / colormap / color picker |
| Range slider | `.dm-slider` | teal handle + filled track | evolution / interactive sliders |
| Ghost icon button | `.dm-icon-btn` | faint → `accent-3` hover | copy buttons, toggles |
| Light code surface | `.dm-code` / `.dm-code__prompt` | n/a (theme-adaptive slab) | install command, inline commands |
| CTA button | `.dm-cta--primary/secondary/ghost` | solid/outline/ghost teal | landing CTA (replaces purple) |
| Callout stripe | `.dm-callout` | left teal stripe | evolution description, notes |

## shadcn/Base UI component grammar

Use shadcn as a naming and composition reference, not as a React runtime inside
Sphinx. The docs already have a static Shibuya shell and page TOC, so the safe
borrowed surface is CSS class grammar:

| shadcn pattern | Docs primitive | Notes |
|---|---|---|
| Button variants/sizes/icons | `.dm-cta`, `.dm-icon-btn`, `.dm-chip`; future `.dm-button` only after repeated generic actions | Gallery pills intentionally behave like chips, not rectangular buttons. |
| Card header/content/footer | gallery card anatomy now follows tokenized card rules; promote `.dm-card*` only when hand-authored repeated cards need it | Generated Sphinx-gallery classes remain the stable hook. |
| Tabs list/trigger/content | `.dm-tabs` / `.dm-tab` | Already implemented and should absorb navigation-like tab sets; compact mutually exclusive controls use `.dm-seg`. |
| Input + Field description/error | `.dm-field` / `.dm-input` | Gallery and color search now share one static field primitive; keep focus ring and disabled/error states aligned with interaction tokens. |
| Command menu | gallery search/filter layout grammar only | No global command palette until there is a real keyboard/action model. |
| Sheet/Dialog side panel | not adopted | Shibuya owns offcanvas sidebars and the right TOC; duplicating sheet behavior risks overlap and focus conflicts. |

## shadcn adoption matrix for the docs

| Decision | shadcn/Base UI idea | Where it lands in this docs codebase | Reason |
|---|---|---|---|
| **Adopt now** | Field + Input | `.dm-field` / `.dm-input` for Examples Gallery search, Color search, and FAQ search | Static Sphinx pages need consistent focus, disabled, empty, and warning states without React form runtime. |
| **Adopt now** | Badge / Chip | `.dm-chip` for gallery category pills, FAQ section pills, palette choices, evolution milestones, and small filter affordances | Filter chips are repeated, stateful, and compact; the shadcn chip grammar fits better than rectangular buttons. |
| **Adopt now** | Segmented Control / Toggle Group | `.dm-seg` / `.dm-opt` for CVD mode selection, example Code/Output view controls, colormap type, and OKLCH/RGB comparison modes | Mutually exclusive toolbar options should share ARIA pressed state and active surface semantics instead of local `.active` button skins. |
| **Adopt now** | Tabs | `.dm-tabs` / `.dm-tab` for generated palette explorer tabs, palette picker namespaces, font picker families, before/after compare widgets, tab-like pickers, and future doc tab sets | This is already a stable primitive and avoids every widget inventing its own active underline. |
| **Adopt now** | Icon button | `.dm-icon-btn` for copy/toggle/icon-only actions | Small utility actions should use a quiet ghost button with a focus ring, not local filled-button skins. |
| **Adopt as anatomy, not class yet** | Card | Sphinx Gallery cards, categorical explorer panels, and repeated future content blocks use tokenized card anatomy | Generated Sphinx classes are the stable hook today; add `.dm-card*` only when hand-authored repeated cards need it. |
| **Adopt later only if repeated** | Generic Button | Reserve `.dm-button` for future repeated generic commands; today use `.dm-cta`, `.dm-chip`, or `.dm-icon-btn` | Prevents adding an abstraction before there is a real repeated generic button surface. |
| **Defer / spike** | Command menu | Search/filter density only; no global command palette | A real command palette needs keyboard scope, action registry, and focus management. |
| **Do not adopt in this PR** | Sheet / Dialog / Popover runtime | Keep Shibuya sidebars, offcanvas, and right TOC as the only page-level rails | Extra overlay primitives would compete with Sphinx navigation and can collide with the page TOC. |

Gallery filter categories use `.dm-chip` as a **mobile chip rail** on narrow
content canvases up to 1100px: the rail stays one row tall and scrolls
horizontally instead of wrapping into a tall toolbar. This preserves
first-screen access to the first gallery section and cards while keeping the
same chip semantics on desktop and mobile.

For tab-like widgets, `.dm-tab[aria-selected="true"]` and `.dm-tab.is-active`
are the supported active hooks. Old aliases such as bespoke `*-active` classes
or `.active` selectors are not part of the shipping grammar; they remain only
inside comparison POCs where the point is to show a historical alternative.

## Decided directions (2026-06-12, after 4-lens critique)

- **Install picker selector → segmented control (`.dm-seg`).** Chosen for the
  "dynamic" feel; active is a solid surface so it can *never* re-break to
  invisible. Underline (`.dm-tab`) stays canonical for everything that must
  match the Quick Install tab-set.
- **Install command → light code surface (`.dm-code`)**, ghost-icon copy.
  No forced dark slab.
- Copy affordance → **ghost icon** (`.dm-icon-btn`), not a dark filled button.

## Rollout (tiers)

| Phase | Scope | Effort |
|---|---|---|
| **P1** | Token SSOT + kill the bug class: decouple active from background; delete legacy `#0d9488` / purple `#8b5cf6` / legacy `--accent-9` (delete, not override). | M |
| **P2** | Install picker → `.dm-seg` + `.dm-code` + ghost copy (this doc's reference implementation). | M |
| **P3** | Fold FAQ filter, palette/fonts/colormap pickers, compare/wipe toggles, evolution slider onto the shared primitives (one component, provably). | L |
| **P4** | Landing CTA purple → `.dm-cta` teal; final sweep so no raw hex / legacy var can win anywhere. | S |
| **P5** | Promote typography roles into `dartwork-design.css`; migrate font specimens and review harnesses off private type/palette rules. | S |
| **P6** | Rebase Dynamic UX CSS/SVG generation on `--dm-*` tokens; remove the last Shibuya-token and hardcoded validation skin reads. | M |

## Files

| File | Role |
|---|---|
| `dartwork-design.css` | raw token scale + Tier 1–6 legacy overrides |
| `dm-interactive.css` | **interactive primitive SSOT** (this system) |
| `dm-interactive-system.md` | this doc — the human SSOT |
| `dm-interactive-styleguide.html` | living styleguide linked to real CSS, included in layout audits |
| `_overhaul_review.html` | visual checkpoint linked to real CSS/JS, included in layout audits |
| `interactive_overhaul_pocs.html` | comparison gallery for historical alternatives |
| `install_picker_pocs.html`, `install_command_pocs.html` | exploration galleries (the directions that were compared) |
