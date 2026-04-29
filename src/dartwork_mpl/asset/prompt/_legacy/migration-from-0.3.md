# Migrating dartwork-mpl 0.3 → 0.4

## Width tokens

| 0.3 | 0.4 replacement |
|---|---|
| `dm.SW` | `width="9cm"` or `dm.col1` |
| `dm.MW` | `width="12cm"` |
| `dm.TW` | `width="14.5cm"` (or round to `"15cm"`) |
| `dm.DW` | `width="17cm"` or `dm.col2` |
| `dm.WIDTHS` | iterate explicit widths instead |
| `dm.FS_*` tuples | replace with `dm.subplots(width=..., aspect=...)` |

The 0.3 names still resolve at runtime (with a `DeprecationWarning`)
through 0.4.x and are removed in 0.5.0.

## subplots

```python
# 0.3
fig, ax = plt.subplots(figsize=(dm.cm2in(9), dm.cm2in(7)), dpi=200)

# 0.4
fig, ax = dm.subplots(width="9cm", aspect=7/9)
```

## Layout

| 0.3 | 0.4 |
|---|---|
| `plt.tight_layout()` | `dm.auto_layout(fig)` |
| `dm.simple_layout(fig)` (most cases) | `dm.auto_layout(fig)` (recommended); `dm.simple_layout` reserved for advanced GridSpec |

## Style application

| 0.3 | 0.4 |
|---|---|
| `plt.style.use("scientific")` | `dm.style.use("scientific")` |

## What was removed

- The phrase "Zero-Resize Policy" — replaced by free width input plus
  the lint consistency guard described in `01-policy.md`.
- `asset/USAGE_GUIDE.md` (PR 2 deletion) — split into
  `00-index.md` / `01-policy.md` / `03-recipes.md`.
