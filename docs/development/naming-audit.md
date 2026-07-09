# Naming convention audit — `dm.__all__`

Audit of every name in the public `dm.__all__` surface (78 entries,
dartwork-mpl 0.5.1 + unreleased PR #329), looking for inconsistent
verb/noun patterns, prefix conventions, abbreviation collisions, and
sibling-naming mismatches. Output of issue
[#310 (C9 — naming convention audit)](https://github.com/dartworklabs/dartwork-mpl/issues/310).

The goal is not a rename storm — it's a written record of what we
have, what stays, what could improve, and what to watch for next time
a new public name is added.

## Method

Grouped every `dm.__all__` entry by its leading prefix. For each
group, asked:

1. Is the prefix carrying meaning (verb-action, accessor, factory)?
2. Are siblings consistent (e.g. `list_X` returns a list of `X`)?
3. Are there orphans (single-member prefixes that should re-home)?
4. Are there abbreviations / acronyms whose meaning isn't obvious?

## Prefix inventory

| Prefix | Count | Members | Verdict |
|---|---:|---|---|
| **`(noprefix)`** | 46 | `cm`, `inch`, `mm`, `pt`, `dpi`, `fs`, `fw`, `lw`, `col1`, `col2`, `figsize`, `length`, `Color`, `Length`, `Style`, `Config`, `config`, `color`, `cspace`, `hex`, `oklab`, `oklch`, `rgb`, `mix_colors`, `pseudo_alpha`, `make_palette`, `make_offset`, `classify_cmap`, `set_decimal`, `rotate_tick_labels`, `arrow_axis`, `label_axes`, `adopt_axis_label_font`, `simple_layout`, `tight_crop`, `figsize`, `find_template`, `lint_code`, `migrate_legacy_code`, `optimize_legend`, `suggest_chart_type`, `check_figure_quality`, `copy_prompt`, `load_style_dict`, `prompt_path`, `show`, `AGENT_DOCS` | **Keep** — primitives, factories, and verb-action helpers. Prefixing every primitive (`dm.unit_cm`, `dm.scale_fs`) would add noise without clarity |
| **`list_`** | 6 | `list_aspect_tokens`, `list_colors`, `list_icon_fonts`, `list_colors`, `list_prompts`, `list_styles` | **Keep** — consistent "return a list of *X*" convention; sibling-set complete |
| **`plot_`** | 4 | `render_cmap_catalog`, `render_color_catalog`, `plot_diverging_bar`, `plot_fonts` | **Watch** — mixed semantics. `plot_diverging_bar` is a *user* plot helper (creates a chart from data); the other three are *diagnostic* helpers (visualise package internals). Consider splitting at next major: `diagnose_*` for the diagnostic trio, `plot_*` for user-facing chart helpers (M3 #305 will add more `plot_*`) |
| **`format_axis_`** | 4 | `format_axis_billions`, `format_axis_currency`, `format_axis_millions`, `format_axis_si` | **Keep** — clear sibling set, parallel signatures, `axis` kwarg consistent across all four |
| **`validate_`** | 4 | `validate_data`, `validate_figure`, `validate_fixes` (module), `validate_with_fixes` | **Watch** — `validate_fixes` is a *module*; `validate_with_fixes` is a *function*. Importing both side-by-side is mildly confusing (`from dartwork_mpl import validate_fixes` vs `from dartwork_mpl import validate_with_fixes`). Already in place by the time it landed; would be a breaking rename today. Live with it; add a `# noqa` documentation note in the module docstring if surprises arise |
| **`get_`** | 3 | `get_agent_doc`, `get_bounding_box`, `get_prompt` | **Keep** — accessor convention; consistent |
| **`save_`** | 2 | `save_and_show`, `save_formats` | **Keep** — both write to disk; consistent |
| **`icon_`** | 2 | `icon_font`, `icon_font_path` | **Keep** — function/path pair, mirror of `style` / `style_path` |
| **`style*`** | 2 | `style` (singleton), `style_path` | **Keep** — singleton + path-resolver pair |
| **`show_`** | 1 | `show_colors` | **Orphan** — sibling-less. Either rename to `plot_palette` (matches `render_color_catalog` / `render_cmap_catalog`) or accept as a special case. Current name reads naturally; not worth a breaking rename |
| **`agent_`** | 1 | `agent_doc_path` | **Orphan but justified** — paired with `get_agent_doc`. Could be flattened to `agent_doc(...)` returning `(path, content)` tuple, but the split is fine as-is |

## Sibling-set completeness checks

A function that takes a kind/category should sit beside a `list_`
counterpart that enumerates the valid choices. Audit:

| Function | Takes a category | `list_*` counterpart exists | Status |
|---|---|---|---|
| `style.use(preset)` | yes | `list_styles()` | ✓ |
| `color(token)` | yes | `list_colors()` | ✓ |
| `make_palette(kind=...)` | yes | (no `list_palette_kinds()`) | **Gap** — only 3 enum values (`categorical`/`sequential`/`diverging`); arguably a `Literal` is enough |
| `icon_font(name)` | yes | `list_icon_fonts()` | ✓ |
| `get_prompt(name)` | yes | `list_prompts()` | ✓ |
| `find_template(name)` | yes | (no `list_templates()`) | **Gap** — 18 templates today; user-facing list would be useful. Track for M3 (#305) or a follow-up |
| `figsize(width, aspect)` | yes (aspect token) | `list_aspect_tokens()` | ✓ |

## Verb consistency for action helpers

Functions that *mutate* a figure / axes should use a verb. Audit:

| Function | Verb | Mutates | Verdict |
|---|---|---|---|
| `set_decimal` | "set" | yes (rcParam) | ✓ |
| `rotate_tick_labels` | "rotate" | yes (axes) | ✓ |
| `arrow_axis` | (noun) | yes (axes) | **Watch** — reads like an attribute. Compare with `dm.add_grid` (proposed in #302). If `add_grid` lands, consider renaming this to `add_arrow_axis` at the same time for sibling-set consistency. Defer the breaking rename until the M2 wave |
| `label_axes` | (noun-ish) | yes (axes) | ✓ — "label" reads as a verb (label-the-axes) |
| `adopt_axis_label_font` | "adopt" | yes (axes) | ✓ |
| `auto_layout` | (noun) | yes (figure) | **Already deprecated** — removed in 0.5.4 in favour of `simple_layout` |
| `simple_layout` | (noun) | yes (figure) | **Keep** — name describes the *output* (simple, content-aware), not the *action*; consistent with matplotlib's `tight_layout` / `constrained_layout` precedent |
| `tight_crop` | (noun) | yes (figure) | **Keep** — same convention as `simple_layout` / matplotlib |
| `optimize_legend` | "optimize" | yes (axes) | ✓ |
| `mix_colors` | "mix" | no (pure) | ✓ |

## Abbreviation collisions / readability

| Name | Concern | Verdict |
|---|---|---|
| `fs`, `fw`, `lw`, `dpi`, `pt`, `cm`, `mm`, `inch` | Two-letter abbreviations; rely on the user knowing matplotlib | **Keep** — these are *the* dartwork-mpl ergonomic primitives; lengthening to `font_size_step()` etc. would erase their main value (terseness when scattered through plotting code) |
| `cspace` | "color space" | **Keep** — well-known abbreviation in color-management contexts |
| `col1`, `col2` | "column 1, column 2" | **Watch** — could be confused with "color 1, color 2." Already documented as academic column widths; readers infer from context. Consider docstring beachhead `# academic column widths (1-col, 2-col)` in cross-references |
| `make_offset` | factory verb | ✓ |
| `pseudo_alpha` | special-case helper | **Keep** — name describes what it does (fake alpha by mixing against background) |
| `oklab`, `oklch`, `rgb`, `hex` | color-space constructors | **Keep** — lowercase short-form matches scientific convention |
| internal color Literal aliases | `Literal[...]` type aliases | **Internal** — generated in `_colors._typing` for signatures and parity checks, not exported at package root |

## Module-level vs package-level names

| Name | Lives at | Should live at | Action |
|---|---|---|---|
| `validate_fixes` | re-exported as a *module* in `dm.__all__` | module-only (`from dartwork_mpl.validate_fixes import ...`) | **Already documented**; the re-export is for completeness. Track for v0.6.0 |
| `AGENT_DOCS` | re-exported as `tuple` constant | constants module if we ever add one | **Keep** — single constant, no need for a `dm.constants` |

## Recommendations summary

| Action | Priority | Notes |
|---|---|---|
| **No renames in 0.x → 1.0 transition** | High | Every entry is reachable as-is. Naming choices that read awkwardly today have been there long enough that breaking them is a net loss |
| **Add `list_templates()` next time `find_template` changes** | Medium | Completes the `*` / `list_*` sibling set. Pair with #305 (M3) |
| **Splitting `plot_*` for diagnostic vs user** | Medium | If #305 (M3) ships 3+ user-facing `plot_*` helpers, the existing diagnostic `render_color_catalog` / `render_cmap_catalog` / `plot_fonts` start to look anomalous. Plan the split for next minor (0.6.0) |
| **Treat `arrow_axis` rename at H2 time** | Low | If `dm.add_grid` (issue #302) lands, evaluate `arrow_axis → add_arrow_axis` in the same wave for sibling-set consistency |
| **Docstring nudges for `cspace`, `col1`/`col2`, `Dartwork*` aliases** | Low | Pure documentation; can ship alongside the next docs PR |

## Re-running this audit

```bash
python -c "
import dartwork_mpl as dm
for name in sorted(dm.__all__):
    # Group by leading prefix
    prefix = name.split('_')[0] + '_' if '_' in name else '(noprefix)'
    print(f'{prefix:20s} {name}')
" | sort
```

Re-run before any release that adds 5+ new entries to `dm.__all__`.
Look for: new singletons of a prefix family, new orphan-prefix
members, new abbreviations that don't match an existing convention.
