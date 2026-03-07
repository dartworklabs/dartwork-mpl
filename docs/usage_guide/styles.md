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

Each preset is a named combination of style layers defined in `presets.json`.
The `-kr` variants add Korean font support on top of the equivalent English preset.

## Preset comparison

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

## How presets stack

Presets are defined in `presets.json` as ordered lists of style layers:

```json
{
  "scientific": ["base", "font-scientific"],
  "investment": ["base", "font-investment"],
  "presentation": ["base", "font-presentation"],
  "scientific-kr": ["base", "font-scientific", "lang-kr"],
  "investment-kr": ["base", "font-investment", "lang-kr"],
  "presentation-kr": ["base", "font-presentation", "lang-kr"]
}
```

Later layers override earlier ones, so `font-investment` overrides the font
sizes set in `base`, and `lang-kr` overrides the font family.

## Advanced: stacking and inspection

```python
# Stack multiple styles manually (advanced)
dm.style.stack(["base", "font-modern"])

# List all available style files
available = dm.list_styles()
# → ['base', 'dmpl', 'dmpl_light', 'font-investment', ...]

# Inspect what a style changes
style_dict = dm.load_style_dict("font-presentation")
```

## Standalone styles

Beyond the preset system, these standalone styles are available for
`style.stack`:

| Style        | Purpose                                 |
| ------------ | --------------------------------------- |
| `dmpl`       | Original dartwork-mpl defaults (legacy) |
| `dmpl_light` | Lighter variant of `dmpl`               |
| `spine-no`   | Hides top + right spines                |
| `spine-yes`  | Shows all four spines                   |
| `lang-kr`    | Korean font family override             |

## See also

- [API › Style Management](../api/style) for all helper functions and arguments
- [Fonts](../fonts/index) for the complete list of bundled typefaces
