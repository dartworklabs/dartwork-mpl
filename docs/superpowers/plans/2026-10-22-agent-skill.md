# Agent entry: installable skill and guidance diet (#523 phase 1)

Branch `t3/p1-agent-skill-20261022`, ported onto the refactored `main`
`f8ec26e5` (ADR 0005 stack #525–#536). Decision context: the agentic-workflow
masterplan (PR #524), phase 1. No pull request is opened by this work.

## Problem (measured on `c332c7ab`)

An agent in another project that follows the documented path reads
`AGENTS.md` + `00-index` + `01-policy` + `03-recipes` + `02-anti-patterns.yaml`:
74,504 chars ≈ 18.6K tokens. No skill is auto-loaded. The docs disagreed
with the runtime (6 of 10 aspect tokens, 4 of 7 presets, "dartwork-mpl 0.4",
Codex "no MCP", a nonexistent `GEMINI.md`, `llms-full.txt` "≈ 45 KB"), a
recipe drew panel labels twice, `.cursor/rules` taught removed APIs, and
`"1920px"` was answered with "Did you mean 'pt'".

## Decisions

1. **Skill SSOT in the package.** `src/dartwork_mpl/skills/dartwork-mpl/`
   holds `SKILL.md` (router, ≤ 120 lines) and six one-level references
   (sizing-and-layout, editing, colors, korean, review-loop, templates).
   The description leads with trigger words. The router carries what agents
   get wrong: data and NaN gaps kept, one-target edits with a new script and
   stem, opening the PNG, `CHECK_FAILED` = incomplete validation; per the
   user (2026-10-22) no meaningless decimals and value labels at
   `dm.fw(1)`. Generic examples omit `color=`.
   Catalogs (all aspect tokens, pixels, palettes) live in references.
2. **`/dataviz` guidance, no precedence claim.** Hosts do not rank skills;
   the text says how to use both when both are active (chart choice there,
   construction here: preset, static output, physical size).
3. **Installer, additions only.** `python -m dartwork_mpl.skills install
   [--claude] [--codex] [--dest DIR] [--copy] [--force]`, `... path`, and
   `skill_version()`. Symlinks by default (library-skills convention).
   Copies record an lstat inventory (types, file SHA-256, link targets); an
   edited or restructured copy, foreign content or an unreadable marker is
   refused without `--force`. Targets resolving outside `--dest` through a
   linked parent are refused. The destination is re-checked just before the
   swap (refused if changed, `--force` included). A link replaces a link in
   one rename; a copy swap restores at once on any exception, and after a
   hard stop the next `install` or `path` puts the old copy back. A
   `.claude/skills -> .agents/skills` link (skm) is installed once.
4. **Consumer entry.** `dm.get_agent_doc("AGENTS")` / `("CLAUDE")` keep their
   signature and frozen asset paths (`asset/agent/AGENTS.md`, `CLAUDE.md`,
   ADR 0005) with the same 54-line consumer entry pointing to the skill.
   Repo-root `AGENTS.md` / `CLAUDE.md` stay mirrored contributor docs.
5. **`dm.figsize` tolerance** (`units/__init__.py`). `"W:H"` strings in
   `figsize`, `figsize_grid`, `parse_aspect` (quotient must be positive and
   finite); `px` input explains DPI. Old inputs return old values.
6. **MCP prompt text** (`mcp/guides/prompts.py` after the refactor) loses
   "0.4". Names, order, docstrings, arguments and the discovery snapshot are
   unchanged; no expectation was regenerated.
7. **Slice.** `dartwork_mpl.skills` is a slice in `scripts/check_boundaries.py`
   (stdlib only; its `__main__` imports only its own package).
8. **Not touched:** styles, presets, fonts, colours, MCP tools, the package
   root, `layout`, `validate`, `evals/agentic/`.

## Measurements (chars / 4 ≈ tokens)

| Surface | Lines | Chars | ≈ tokens |
|---|---|---|---|
| `SKILL.md` | 120 | 6,340 | 1,585 |
| consumer entry | 54 | 2,363 | 591 |
| SKILL.md + entry | 174 | 8,703 | 2,176 |
| six references (on demand) | 481 | 19,418 | 4,854 |
| old documented path | 1,537 | 74,504 | 18,626 |

## Verification

- After the port: `uv run ruff check .`, `ruff format --check .`,
  `uv run mypy` (191 files), `scripts/check_boundaries.py` pass;
  `scripts/test_id_map.py --ref origin/main`: 7,114 → 7,209, the 95 new ids
  are this branch's tests, 0 lost, 0 duplicated.
- Full suite, CI commands, in a clone whose directories are not
  group-writable (MCP input fixtures require it; this worktree's parents
  are 0775), with per-run `TMPDIR`, at `5a14357a`: Python 3.12 with coverage
  7,210 passed, 0 failed, coverage 92.32 %, `check_integration_junit.py`
  "OK: 45 required modules"; Python 3.10 7,208 passed, 2 skipped, 0 failed.
- Pixel baselines (`tests/visual`, `--mpl`): 14 passed. Colour hash passes;
  no digest was regenerated.
- Rendering on `f8ec26e5` vs this branch, decoded RGBA: 18 basic and five
  advanced templates (line, bar_grouped, waterfall, twin_axis, contour),
  0 differing pixels in all 23.
- `sphinx-build -W` (full gallery): 0 warnings, `llms-full.txt` untouched; it
  was regenerated only via `generate_llms_full_txt(write=True)`.
- `uv build --wheel` contents are checked by `tests/architecture/test_packaging.py`.
- Real path: `install` into scratch projects linked both targets (rerun
  `unchanged`); `--copy` copied both, rerun `unchanged`, copy identical to
  the source apart from its marker. Earlier: an edited copy was refused and
  `--force` replaced it; no staging folders left. Headless smoke runs (one
  each, not an evaluation): Claude Code listed the skill and, asked in
  Korean for a report line chart, invoked it, used `report` + `dm.figsize`,
  saved v1, read the PNG and saved v2 (9 turns, 29 s); Codex listed it.
- Docs PoC: before (live site) / after (local build) screenshots of the AI
  hub setup tabs (desktop, mobile), the compatibility table and the
  "ask in your own words" table were handed to the coordinator.

## Tests added

`src/dartwork_mpl/skills/tests/test_skills.py` (format limits, routing,
router rules, `/dataviz` text, every Python block run and linted, colour
names, lists vs runtime, installer safety on real directories, CLI),
`src/dartwork_mpl/units/tests/test_figsize_ratio_strings.py`,
`tests/test_agent_docs_runtime.py` (corpus lists, panel-label recipe, MCP
prompt version, AI hub claims, mirrors, frozen asset paths),
`tests/architecture/test_packaging.py`. The skill test also resolves every
`dm.*` name and prompt guide the skill mentions.

## Open issues and follow-ups

- Phase 1's pass condition (skill beats no-skill on the phase 0 set) needs
  the `evals/agentic/` baseline; the smoke runs are not that evidence.
- `references/editing.md` shows `set_title(..., loc="left")`; phase 2 fixes
  layout and checks that ignore left titles today.
- This repository's `.agents/skills` is managed by skm; the skill is not
  linked into it.
- The skill says `dm.format_axis_si/_myriad/_millions/_billions` choose
  decimals by default; that holds once the parallel formatter branch lands
  (today their default is `decimals=1`).
- `dm.validate_data(..., allow_nan=True)` keeps Inf as well as NaN; the
  skill does not repeat the 03-recipes note on checking finiteness.
