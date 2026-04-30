# dartwork-mpl Library Usage Guide — Moved

> **DEPRECATED in 0.4.0 — content removed in 0.4.x.**
>
> The previous body documented the 0.3 width-aliases (`SW`, `MW`, `TW`,
> `DW`, `FS_*`) and the `cm2in`-based figsize idiom. Both are removed
> in 0.4 and reading them would actively mislead an agent.

## Where to look now

The 0.4 SSOT lives in this directory. Start at:

1. **[`00-index.md`](00-index.md)** — agent entry point + decision tree.
2. **[`01-policy.md`](01-policy.md)** — full policy (width, aspect,
   layout, color, font, save).
3. **[`03-recipes.md`](03-recipes.md)** — intent → function-call cookbook.

Lint catalog: **[`02-anti-patterns.yaml`](02-anti-patterns.yaml)**.
Plot templates: **[`05-templates/`](05-templates/)**.

## MCP equivalents

| Old URI                              | New URI                              |
| ------------------------------------ | ------------------------------------ |
| `dartwork-mpl://guide/general-guide` | `dartwork-mpl://guide/agent-entry`   |

## Migration help

For 0.3 → 0.4 upgrades, see
**[`_legacy/migration-from-0.3.md`](_legacy/migration-from-0.3.md)**
or the rendered `docs/migration.md`. The migration guide is also
exposed via MCP as `dartwork-mpl://guide/migration`.

This stub will be removed in **0.5.0**.
