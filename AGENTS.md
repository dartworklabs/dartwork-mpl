# dartwork-mpl — contributor entry point

You are working **on** dartwork-mpl, a publication-quality matplotlib
design system. This file is for AI coding assistants changing this
repository. For human contributors, see [`README.md`](README.md).

The same content is mirrored in [`AGENTS.md`](AGENTS.md) so non-Claude
clients (Codex, Aider, Continue, etc.) can pick it up.
A machine-readable index is in [`llms.txt`](llms.txt) and a single-file
concatenated dump in [`llms-full.txt`](llms-full.txt).

## What is dartwork-mpl

A thin utility layer on top of matplotlib that gives you a free-form
physical-width API, ten aspect tokens, curated style presets, an
OKLCH-aware color system, content-aware layout, validation, and an
MCP server for AI agent integration. It does **not** wrap matplotlib
with a new API — `Figure` / `Axes` stay native.

## Plotting rules live in the bundled skill

Before writing or reviewing any plotting code here (docs examples,
templates, tests), read
[`src/dartwork_mpl/skills/dartwork-mpl/SKILL.md`](src/dartwork_mpl/skills/dartwork-mpl/SKILL.md)
and the `references/` file it routes to. It is the single source of the
consumer rules: preset by purpose, `dm.figsize`, `dm.simple_layout` (never
`plt.tight_layout()`), `dm.save_formats`, colour names, `dm.fs` / `dm.lw` /
`dm.fw`, editing only the requested target, and the render → inspect →
revise loop.

What ships to agents in other projects:

| Surface | Source | Limit (tested) |
|---|---|---|
| Skill, installed by `python -m dartwork_mpl.skills install` | `src/dartwork_mpl/skills/dartwork-mpl/` | `SKILL.md` ≤ 120 lines; every Python block runs and lints |
| Consumer entry, `dm.get_agent_doc("AGENTS")` | `src/dartwork_mpl/asset/agent/AGENTS.md` | ≤ 60 lines |
| Prompt corpus, `dm.get_prompt(...)` / MCP resources | `src/dartwork_mpl/asset/prompt/` | lists match runtime |

Change a consumer rule in the skill first, then keep the corpus and docs in
step. The full anti-pattern SSOT is
[`src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml`](src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml);
`dm.lint_code(code)` or the MCP tool `lint_dartwork_mpl_code` runs it.

## MCP server

For Claude Code / Cursor / any MCP client, see the step-by-step setup
in [`docs/integrations/mcp_server.md`](docs/integrations/mcp_server.md).
The server exposes 19 tools (lint + auto-fix + figure validation + render + color lookup + info
+ chart-type recommender + layered-plot composer + advanced-tier render + durable artifact delivery + retained-input deletion), 10 resources +
9 resource templates (the prompt corpus + 18 basic + 18 tier-2 advanced plot templates + five artifact members), and 2 prompts.
New MCP features are frozen (#523); bug and security fixes continue, and
tool names, order, schemas and docstrings do not change.

Inputs are kept in the operator-selected private `storage_dir` on the server
host. Unset policy denies Copy/Retained/delete. Historical report receipts do
not prove current availability or upstream freshness; actual Retained admission
checks reuse. Clients handle per-input display and ambiguous data choices. See
the MCP guide for hashes, seven-day child copies and deletion limits.

## Design documents and agent work

These four rules exist because a colour-system refactor stalled for weeks
behind a 13,868-line design document whose completion criteria could not be
met on any developer machine. The full post-mortem is
[ADR 0002](docs/adr/0002-separate-shipped-color-compatibility-from-oklab-authoring.md).

1. **A design document does not exceed 200 lines.** If it wants to be longer,
   the work needs splitting, not a longer document. A design nobody can read
   is not a design.
2. **Adversarial review requires an external decider.** "Reviewer A and B both
   passed" is not a stopping condition on its own — reviewers reading the same
   document can always find one more gap, so the loop diverges. Land a
   mechanical check first (a pinned digest, a golden file, a measured
   threshold), then review against it.
3. **An ADR may not release a preceding ADR's lock.** If an accepted decision
   froze something, superseding it is a separate decision that needs its own
   approval — not a clause inside the document that wants the freedom.
4. **Completion criteria must be executable in this repository's development
   environment.** A criterion that requires hardware, an OS or a tool nobody
   has is not a high standard; it is an unreachable one.

The colour freeze specifically: `tests/test_shipped_colors_hash.py` pins every
shipped colour value. Never regenerate its digests to make a failing test pass
— a failure means a shipped colour moved, which is a decision for a human, not
a test fix.

The visual style is also held: fonts, weights, spines, grids, preset looks
and colour values do not change outside a bug fix whose before/after the
user has seen.

## Where to read more

| If you want… | Open |
|---|---|
| 5-minute hands-on tour | [`docs/usage_guide/quickstart.md`](docs/usage_guide/quickstart.md) |
| Width / aspect / layout deep dive | [`docs/usage_guide/layout.md`](docs/usage_guide/layout.md) |
| Color system & palettes | [`docs/color_system/colors.md`](docs/color_system/colors.md) (or the [design rationale](docs/color_system/design-rationale.md)) |
| Fonts, math & symbols | [`docs/fonts/index.md`](docs/fonts/index.md) (or the [math/symbol guide](docs/fonts/math_and_symbols.md)) |
| Saving, validation & reproducible output | [`docs/usage_guide/save_export.md`](docs/usage_guide/save_export.md) |
| 18 ready-to-use plot templates | [`docs/examples_gallery/09_ai_templates/`](docs/examples_gallery/09_ai_templates/) (rendered) or [`src/dartwork_mpl/asset/prompt/05-templates/`](src/dartwork_mpl/asset/prompt/05-templates/) (source) |
| Upgrading from v4 | [`docs/migration.md`](docs/migration.md) |
| Why this design exists | [`docs/philosophy/ai_native.md`](docs/philosophy/ai_native.md) |
| AI integration overview | [`docs/ai/index.md`](docs/ai/index.md) |
| Agent-workflow plan and its phases | [#523](https://github.com/dartworklabs/dartwork-mpl/issues/523) |
