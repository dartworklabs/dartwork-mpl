# dartwork-mpl Agent Coding Rules — Moved

> **DEPRECATED in 0.4.0 — content removed in 0.4.x.**
>
> The previous body of this file was retained from the 0.3 series and
> documented patterns that conflict with the 0.4 width / aspect API
> (e.g. `figsize=`, `cm2in`, `SW/MW/TW/DW`). Reading it would actively
> mislead an agent.

## Where to look now

The 0.4 SSOT is split across **three** files in this same directory.
Read them in order:

1. **[`00-index.md`](00-index.md)** — agent entry point + always-true
   facts + the standard agent loop.
2. **[`01-policy.md`](01-policy.md)** — full policy: width, aspect,
   layout, color, font, save.
3. **[`03-recipes.md`](03-recipes.md)** — intent → function-call cookbook.

The machine-readable lint catalog lives at
**[`02-anti-patterns.yaml`](02-anti-patterns.yaml)**, and the curated
plot templates are under **[`05-templates/`](05-templates/)**.

## MCP equivalents

| Old URI                              | New URI                              |
| ------------------------------------ | ------------------------------------ |
| `dartwork-mpl://guide/coding-rules`  | `dartwork-mpl://guide/agent-entry`   |
| `dartwork-mpl://guide/general-guide` | `dartwork-mpl://guide/agent-entry`   |
| `dartwork-mpl://guide/layout-guide`  | `dartwork-mpl://guide/policy`        |

## Migration help

If you're upgrading code from 0.3 to 0.4, see
**[`_legacy/migration-from-0.3.md`](_legacy/migration-from-0.3.md)** or
the rendered docs at `docs/migration.md`. The migration guide is also
exposed via MCP as `dartwork-mpl://guide/migration`.

This stub will be removed in **0.5.0** along with the matching MCP
URIs. Update any pinned references now.
