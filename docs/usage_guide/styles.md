# Styles and Presets

dartwork-mpl ships with curated style presets that configure palette, fonts,
line weights, and spine visibility in one call.

## Using presets

```python
import dartwork_mpl as dm

dm.style.use("scientific")              # papers/technical (recommended)
dm.style.use("presentation")            # slides/reports
dm.style.use("investment")              # finance decks (spines hidden)
dm.style.use("scientific-kr")           # includes Korean fonts
```

Each preset is a named combination of style layers.
The `-kr` variants add Korean font support on top of the equivalent English preset.

## Preset comparison

Toggle between presets below to see how font sizes and spines change on the
same chart:

```{raw} html
:file: images/preset_compare.html
```

All three English presets share the same `base` layer (thin lines, no grid,
lightweight Roboto font family). They differ only in **font scale** and
**spine visibility**:

| rcParam             | `scientific` | `investment` | `presentation` |
| ------------------- | ------------ | ------------ | -------------- |
| `font.size`         | 7.5 pt       | 8.0 pt       | 8.5 pt         |
| `axes.titlesize`    | 8.5 pt       | 9.0 pt       | 9.5 pt         |
| `axes.labelsize`    | 7.5 pt       | 8.0 pt       | 8.5 pt         |
| `xtick.labelsize`   | 7.0 pt       | 7.0 pt       | 8.0 pt         |
| `legend.fontsize`   | 5.5 pt       | 6.0 pt       | 6.5 pt         |
| `axes.spines.top`   | True (base)  | **False**    | True (base)    |
| `axes.spines.right` | True (base)  | **False**    | True (base)    |

**When to use which:**

- **`scientific`** — Compact sizing for journal figures at 3.5″ column width.
  All four spines are visible.
- **`investment`** — Slightly larger fonts for equity research reports and
  financial dashboards. Top/right spines are hidden for a cleaner look.
- **`presentation`** — Largest font scale for slides and web. Text stays
  readable when projected or viewed on a monitor.

## Korean variants (`-kr`)

Appending `-kr` swaps the primary font family to Korean-capable fonts:

| Layer       | Primary font fallback chain                           |
| ----------- | ----------------------------------------------------- |
| **English** | Roboto → Lato → Inter → Open Sans → Arial             |
| **Korean**  | Noto Sans CJK KR → Paperlogy → Pretendard → Gothic A1 |

```python
dm.style.use("investment-kr")  # investment sizing + Korean fonts
```

## How presets work

Presets are built by **stacking** style layers in order — each layer overrides
the previous. For example, `scientific` applies the `base` layer first (shared
defaults), then `font-scientific` on top (which sets the compact font sizes).

The `-kr` variants simply add a `lang-kr` layer that overrides the font family
with Korean-capable fonts. You don't need to manage layers manually — just call
`dm.style.use()` with a preset name.

## Advanced: stacking and inspection

For advanced use cases, you can compose custom styles or inspect what a preset
changes:

```python
# List all available style files
available = dm.list_styles()
# → ['base', 'font-investment', 'font-presentation', 'font-scientific', ...]

# Inspect what a specific style layer changes
style_dict = dm.load_style_dict("font-presentation")
# → {'font.size': 8.5, 'axes.titlesize': 9.5, ...}

# Stack multiple styles manually
dm.style.stack(["base", "font-scientific", "lang-kr"])
```

## Standalone styles

These standalone styles can be combined with `style.stack`:

| Style        | Purpose                                                           |
| ------------ | ----------------------------------------------------------------- |
| `dmpl`       | Original dartwork-mpl defaults (pre-preset system; rarely needed) |
| `dmpl_light` | Lighter variant of `dmpl` (pre-preset system; rarely needed)      |
| `spine-no`   | Hides top + right spines                                          |
| `spine-yes`  | Shows all four spines                                             |
| `lang-kr`    | Korean font family override                                       |

> **Note:** `dmpl` and `dmpl_light` predate the current preset system and are
> retained for backwards compatibility. For new projects, use `scientific`,
> `investment`, or `presentation` instead.

## See also

- [API › Style Management](../api/style) for all helper functions and arguments
- [Fonts](../fonts/index) for the complete list of bundled typefaces
