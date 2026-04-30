# Layout Tool Usage Guide — Moved

> **DEPRECATED in 0.4.0 — content removed in 0.4.x.**
>
> The previous body covered `tight_layout`, `subplots_adjust`, and
> hand-tuned figure padding patterns. The 0.4 layout policy is much
> simpler: call `dm.auto_layout(fig)` after building the figure and
> let `dartwork-mpl` handle the rest.

## Where to look now

The 0.4 SSOT lives in this directory:

1. **[`00-index.md`](00-index.md)** — agent entry point. The "always-true
   facts" section already states the layout rule.
2. **[`01-policy.md`](01-policy.md)** — full layout policy
   (`auto_layout`, `simple_layout`, manual fallbacks).
3. **[`03-recipes.md`](03-recipes.md)** — copy-pasteable plot recipes
   that already include the right layout call.

Lint catalog: **[`02-anti-patterns.yaml`](02-anti-patterns.yaml)** —
`tight_layout` and friends are caught automatically.

## MCP equivalents

| Old URI                              | New URI                              |
| ------------------------------------ | ------------------------------------ |
| `dartwork-mpl://guide/layout-guide`  | `dartwork-mpl://guide/policy`        |

## Migration help

For 0.3 → 0.4 upgrades, see
**[`_legacy/migration-from-0.3.md`](_legacy/migration-from-0.3.md)**
or the rendered `docs/migration.md`. The migration guide is also
exposed via MCP as `dartwork-mpl://guide/migration`.

This stub will be removed in **0.5.0**.
