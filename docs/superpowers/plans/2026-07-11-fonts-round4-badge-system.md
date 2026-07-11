# Fonts browser — round-4: badge system, type scale, title-row lock (advisory)

> Branch: `feat/fonts-browser-ux-2026-07-10`. Single offline worker (codex).
> Generator contract unchanged (`--check` green + idempotent after changes).
> Applies to BOTH fragments: `docs/_static/fonts_browser.frag.html`
> (root `dm-fontfacets`) and `docs/_static/pocs/fonts_ux_b.frag.html`
> (root `dm-fbuxb`) — keep them in sync (B = core + preview-input + pin/tray).

User picked layout **C** and flagged: title-vs-bottom badge roles unclear;
badge colors arbitrary (role=accent, script=info-blue, Mono=warning-yellow);
"Mono" appears up to 4×/card (group header + role + script suffix + flag);
sample text/size rules inconsistent; title-row actions must never wrap.

## The system (implement exactly)

### S1 — "One fact, once" two-tier card
- **Title row** (`.card-top`): font name + `Default` chip (roboto only) +
  spacer + actions right-aligned: `Copy chain` (+ pin ★ in the B fragment).
  `flex-wrap: nowrap`; name gets `min-width:0; white-space:nowrap;
  overflow:hidden; text-overflow:ellipsis`; actions `flex-shrink:0`.
  NEVER two lines. **The role badge is REMOVED from the title row** (the
  group subheaders already carry category; role was redundant).
- **Meta row** (bottom): fixed order — coverage · `N weights` · `Italics`
  (only when italic) · `Aligned digits` (only when true, tooltip kept).
  **The `Mono` flag badge is DELETED** (group header + coverage suffice).
- Description stays full-width between title and sample.

### S2 — coverage vocabulary (replaces the 7 ad-hoc script strings)
Generator emits a normalized `coverage` value (keep `script` for search/back-
compat if simpler, but the BADGE renders `coverage`):
| old script value | coverage |
| --- | --- |
| `Latin` | `Latin` |
| `Latin (monospace)` | `Latin` |
| `Latin + pan-script` | `Multiscript` |
| `한글 + Latin` | `한글+Latin` |
| `한글 + Latin (mono)` | `한글+Latin` |
| `CJK (한·중·일)` (Noto Sans CJK KR — verify actual string) | `CJK` |
| `Math symbols` | `Math` |
| `Symbols` | `Symbols` |
Rail Script facet uses the SAME coverage vocabulary (counts recomputed);
the mono-ness never appears in coverage (group + description carry it).
`Multiscript` gets `title="Broad multi-script coverage in one family"`.

### S3 — badge color = semantic ladder (3 steps, no more)
- `Default` chip: solid accent (`--dm-accent-9` bg, white text).
- Coverage badge: accent tint (`--dm-accent-3` bg, `--dm-accent-11` text).
- Fact badges (weights / Italics / Aligned digits): neutral —
  transparent bg, `--dm-border` 1px, `--dm-text-muted` text.
Delete the `--dm-info-3` and `--dm-warning-3` badge styles entirely.
Add a one-line comment above the badge CSS documenting the ladder.

### S4 — type scale + sample-text standard (document in a CSS-var block)
At the top of each fragment's `<style>`, define scoped vars + comment:
```
/* Type scale: card sample 22 / drawer specimen 26 / ladder 19 / tray 24.
   Sample text: card+specimen+tray use the family `sample` sentence;
   ladder+width-variants use the short `ladder_sample`. Nothing else. */
--fbx-fs-sample: 22px; --fbx-fs-specimen: 26px; --fbx-fs-ladder: 19px;
--fbx-fs-tray: 24px;
```
Re-point `.sample-line`, drawer specimen, `.ladder-sample`, width-variant
rows, and the tray sentence to these vars; line-height 1.4 on all of them
(descender-safe). Remove any other hardcoded sample font sizes.

### S5 — interface polish
- Whole card (`article.card`) opens the drawer on click (inner buttons
  `stopPropagation`); keep the `.card-open` button as the keyboard/a11y path
  (visible focus ring), cursor:pointer on the card.
- Group subheaders show the visible count: e.g. `Monospace · 5` (count of
  currently visible cards in that group; updates with filters/search).
- Card hover: border-color accent-6 + shadow-1 only — zero layout shift.
- POC page: **remove the A/B/C badge-layout switcher** (C is decided);
  the refined C IS the layout in both fragments now. Update
  `docs/pocs_fonts_ux.md` banner copy accordingly (트레이 비교가 남은 delta).

### S6 — sync + verification
- Regenerate data if the generator changed (coverage field): `--check` exit 0,
  twice byte-identical.
- Update `tests/test_fonts_browser_consistency.py`: coverage non-empty for
  all 20 + coverage vocabulary ⊆ {Latin, 한글+Latin, CJK, Multiscript, Math,
  Symbols}; drop any test asserting the removed Mono badge / role badge.
- `uv run pytest tests/test_fonts_browser_consistency.py tests/test_font_invariants.py tests/test_font_licenses.py -q`
  → only the 2 pre-existing environmental mathtext failures.
- Clean rebuild (module form) succeeds; hygiene greps 0 on both fragments.
- Spot: a JetBrains Mono card shows exactly: title `JetBrains Mono` (+actions)
  / meta `Latin · 8 weights · Italics` (+Aligned digits if true) — the word
  "Mono" appears ONLY in the name and the `Monospace · N` subheader.

## Commits (atomic)
1. `feat(docs): normalize coverage vocabulary in fonts browser data`
2. `feat(docs): two-tier badge system + semantic color ladder + type scale`
3. `feat(docs): title-row action lock + whole-card open + group counts`
4. `chore(docs): retire badge-layout switcher (C adopted) + tests sync`
