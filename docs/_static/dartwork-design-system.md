# dartwork-mpl docs — Design System (master SSOT)

> The single source of truth for **all** docs design elements — tokens,
> components, and the interaction language. Drives the 2026-06 consolidation
> overhaul. Companion: `dm-interactive-system.md` (interactive primitive
> deep-dive), `dm-interactive-styleguide.html` (living reference).

## Thesis

The docs have a clean Radix-based token foundation in `dartwork-design.css`,
undermined by three failures the overhaul resolves:

1. **Dark-scale leak** — only 4 of 12 teal steps were overridden in dark, so
   8 steps leaked light values (broke callouts, `::selection`, link
   underlines, chip borders). ✅ fixed (P1).
2. **Three competing accents** — canonical teal `#12a594`, legacy teal
   `#0d9488` (39 hardcoded fallbacks, 2 even cyan `#5eead4`), light-mode-only
   landing **purple** `#8b5cf6`. → collapse to one teal.
3. **Widget-level hardcoding** — ~20 hex grays, ad-hoc radii, untokenized
   shadows, bespoke `<style>` blocks (pickers, 3× copy-pasted compare
   toggles, `dynamic_ux.css`'s own `--dm-ux-accent #14b8a6`) bypass tokens.

> **Rule:** `dartwork-design.css` tokens are the SSOT; `dm-interactive.css`
> `--dm-i-*` primitives are the single component idiom. Everything folds onto
> them. No raw hex, no legacy accent, no per-widget dark color.

## Naming (decided 2026-06-12)

One brand abbreviation: **`dm`** (= dartwork-mpl, matching `import
dartwork_mpl as dm` and the `.dm-*` classes). Not `dw` (a second abbreviation
= confusion), not `rx` (leaks the upstream lib name).

- **Scale tokens** → `--dm-gray-*`, `--dm-accent-*`, `--dm-radius-*`,
  `--dm-space-*`, `--dm-fs/lh/ls-*`, `--dm-weight-*`, `--dm-shadow-*`
  (renamed from `--rx-*` — done, P3a).
- **Semantic tokens** → `--dm-text-*`, `--dm-bg-*`, `--dm-border-*`,
  `--dm-link*`, `--dm-i-*`. No collision (second segment differs).
- **Upstream, untouched** → `--sy-*` (Shibuya), `--pst-*` (PyData).
- The scale values are *sourced from Radix Colors*; the doc notes this once,
  the token names don't.

## Token SSOT

| Layer | Canonical | Notes |
|---|---|---|
| **Color** | one teal `--dm-accent-1..12` (+ `gray-1..12`, `gray-a1..a12`) | DELETE legacy `#0d9488`/`--accent-9` & purple `#8b5cf6`. Links=`accent-11`, primary/focus=`accent-9`, hover=`accent-10`, soft wash=`accent-3`, on-soft text=`accent-11` (AA). Amber admonition is the **one** allowed non-teal semantic → formalize `--dm-warning`/`--dm-warning-text` with dark override. |
| **Typography** | `--dm-fs-1..9` / `lh` / `ls` / `weight-light..bold` | add micro `--dm-fs-0` (13px), `--dm-fs-00` (11px) for TOC caption only; refuse the 0.78/0.72/0.62em scatter. Families: `--dm-f-sys`, `--dm-f-mono` ✅ defined (P2). h1/h2=semibold, h3/h4=medium (documented). |
| **Space** | `--dm-space-1..9` (4/8/12/16/24/32/40/48/64) | already clean. Replace remaining literal paddings. |
| **Radius** | `--dm-radius-1..6` + `full` (3/4/6/8/12/16/9999) | round orphans (5→radius-3, 10→radius-4/5, 20→radius-6, 2→radius-1, 50%→full). No half-steps. |
| **Shadow** | `--dm-shadow-1..4` (gray-alpha) | already defined. Remap literal `0 8px 28px …` families onto the ladder; DELETE purple-tinted shadows. |
| **Border** | `--dm-border-faint` / `--dm-border` / `--dm-border-strong` (+ `--dm-i-soft-border`=accent-7) | collapse warm `#ebe9e2`/`#e4e2dd`/`#d5d3cc` & cool `#e0e0e0` → the two-token system. |
| **Motion** | `--dm-i-transition` (when next touched) | out of scope now; add one timing token instead of per-widget literals. |

## Component SSOT

| Component | Canonical idiom |
|---|---|
| Cards | `--dm-border-faint` + `--dm-bg-panel` + `--dm-shadow-1` + `radius-4`; drop 16 bespoke `0 8px 28px` literals |
| Admonition | left teal stripe, title `accent-11`; warning = `--dm-warning` (the one non-teal) |
| Table | medium header, no fill, `--dm-border` bottom, hover `--dm-bg-hover` (already correct) |
| Code block / inline | **one** surface `--dm-i-code-surface` (gray-2 light / gray-3 dark). KILL navy `#0f172a` in dynamic_ux.css |
| Links | `--dm-link`/`-hover`, underline `accent-7` (now dark-correct after P1) |
| Sidebar / TOC | active `accent-3` bg + `accent-11` text; sizes → `fs-2`/`fs-0`/`fs-00` |
| Buttons | primary=`accent-9`+white+semibold, secondary=`accent-9` border+`accent-11`+medium → `.dm-cta--*` |
| **Interactive** | `dm-interactive.css` primitives: `.dm-seg` `.dm-tabs/.dm-tab` `.dm-chip` `.dm-swatch` `.dm-slider` `.dm-icon-btn` `.dm-code` `.dm-cta` `.dm-callout` — see `dm-interactive-system.md` |

## Redesign decisions (where variation was too chaotic)

| Element | Change | Why |
|---|---|---|
| Landing CTA + tagline | purple gradient → `.dm-cta` teal (or `accent-5→accent-11` gradient) | purple is light-mode-only (fails on dark), a 3rd accent |
| Legacy `--accent-9` `#0d9488` (+cyan `#5eead4`) | mass-replace → `var(--dm-accent-9)` | `#0d9488` is teal-**10** (off-by-one hue); `#5eead4` is Tailwind cyan |
| 3× compare/wipe toggles + `.dmc-tab`/`.dm-pc-tab` | → one `.dm-seg` + one `.dm-tabs` | triples maintenance; each ships own hardcoded color/size |
| `font-specimens.css` + `dynamic_ux.css` bespoke sheets | reskin over tokens; `--dm-ux-accent #14b8a6` → `accent-9`; navy code → `--dm-i-code-surface` | they define a 2nd parallel accent + hand-maintained dark that won't track tokens |
| Carded shadows + warm borders | one `--dm-shadow-1` + two-token border | per-widget literals have no dark variant |
| Letter-spacing magic numbers | bake into `--dm-ls` scale + one `--dm-text-tight` | 3 layered opaque adjustments are unauditable |

## Roadmap (phased, checkpoint each)

| Phase | Scope | Effort/Risk | Status |
|---|---|---|---|
| **P1** | complete dark accent scale (the leak bug) | S / Low | ✅ done |
| **P2** | define `--dm-f-mono`/`--dm-f-sys` | S / Low | ✅ done |
| **P3a** | rename `--rx-*`→`--dm-*` (one namespace) | S / Low | ✅ |
| **P3b** | kill legacy `--accent-9` + purple; migrate landing CTA/install picker → `.dm-cta`/`.dm-seg`/`.dm-code` | M / Med | ⬜ |
| **P4** | tokenize radii/shadows/borders/grays in custom.css | L / Med | ⬜ |
| **P5** | tokenize typography + collapse letter-spacing | L / Med | ⬜ |
| **P6** | refold bespoke widgets onto primitives (compare dedupe, pickers, dynamic_ux skin) | L / Med-High | ⬜ |

Verification each phase: build/serve + Playwright light **and** dark
screenshots Read; grep custom.css for residual hex/legacy → ~0.

## Files

| File | Role |
|---|---|
| `dartwork-design.css` | token SSOT (`:root` + `html.dark`) + Tier 1–6 overrides |
| `dm-interactive.css` | interactive primitive SSOT (`--dm-i-*`) |
| `dartwork-design-system.md` | **this — master SSOT + roadmap** |
| `dm-interactive-system.md` | interactive primitive deep-dive |
| `dm-interactive-styleguide.html` | living styleguide (links real CSS) |
| `install_picker_pocs.html` / `install_command_pocs.html` / `interactive_overhaul_pocs.html` | exploration galleries |
