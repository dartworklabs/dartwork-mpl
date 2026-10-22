# Agent entry: installable skill and guidance diet (#523 phase 1)

Branch `t3/p1-agent-skill-20261022`, based on `main` `3acf03db`. Decision
context: the agentic-workflow masterplan (PR #524), phase 1. No pull request
is opened by this work.

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
   stem, opening the PNG, `CHECK_FAILED` = incomplete validation. Catalogs
   (all aspect tokens, pixels, palettes) live in references.
2. **`/dataviz` guidance, no precedence claim.** Hosts do not rank skills;
   the text says how to use both when both are active (chart choice there,
   construction here: preset, static output, physical size).
3. **Installer, additions only.** `python -m dartwork_mpl.skills install
   [--claude] [--codex] [--dest DIR] [--copy] [--force]`, `... path`, and
   `skill_version()`. Symlinks by default (library-skills convention).
   Copies record SHA-256 per file; an edited copy, foreign content or an
   unreadable marker is refused without `--force`. Every replacement is
   staged next to its destination first and swapped by rename, restoring the
   old install if the swap fails. A `.claude/skills -> .agents/skills` link
   (skm) is installed once. The CLI prints the source path and version and
   says links follow the Python environment.
4. **Consumer entry.** `dm.get_agent_doc("AGENTS")` / `("CLAUDE")` keep their
   signature and frozen asset paths (`asset/agent/AGENTS.md`, `CLAUDE.md`,
   ADR 0005) with the same 53-line consumer entry pointing to the skill.
   Repo-root `AGENTS.md` / `CLAUDE.md` stay mirrored contributor docs.
5. **`dm.figsize` tolerance.** `"W:H"` strings in `figsize`, `figsize_grid`,
   `parse_aspect`; `px` input explains DPI. Old inputs return old values.
6. **MCP prompt text** loses "0.4". Names, order, docstrings, arguments and
   the discovery snapshot are unchanged; no expectation was regenerated.
7. **Not touched:** styles, presets, fonts, colours, MCP tools, `prompt.py`,
   `__init__.py`, `layout.py`, `validate/_checks/`, `evals/agentic/`.

## Measurements (chars / 4 ≈ tokens)

| Surface | Lines | Chars | ≈ tokens |
|---|---|---|---|
| `SKILL.md` | 117 | 5,937 | 1,484 |
| consumer entry | 53 | 2,301 | 575 |
| SKILL.md + entry | 170 | 8,238 | 2,060 |
| six references (on demand) | 455 | 18,314 | 4,578 |
| old documented path | 1,537 | 74,504 | 18,626 |

## Verification

- `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`
  (118 files), `scripts/check_boundaries.py`: pass.
- Full suite, CI commands, at `a8e8e5d8` in a clone whose directories are
  not group-writable (the MCP input fixtures require that; this worktree's
  parents are 0775): Python 3.12 with coverage 6,998 passed, 0 failed,
  coverage 92.04 % (gate 80 %), `check_integration_junit.py` "OK: 42
  required modules"; Python 3.10 6,996 passed, 2 skipped, 0 failed. The run
  before that caught finance vocabulary in the Korean reference
  (`test_domain_neutrality`), fixed in `a8e8e5d8`.
- `sphinx-build -W` (full gallery): build succeeded, 0 warnings,
  `llms-full.txt` untouched. `llms-full.txt` was regenerated only through
  `docs/_ext/build_hooks.generate_llms_full_txt(write=True)`.
- `uv build --wheel`: skill (`__init__`, `__main__`, `SKILL.md`, six
  references), `asset/agent/{AGENTS,CLAUDE}.md` (consumer entry) and
  `llms*.txt` ship; no `tests/`. `tests/architecture/test_packaging.py`
  checks this.
- `tests/test_shipped_colors_hash.py` passes; no digest was regenerated.
- Trial merge of the #525–#528 stack (`refactor/core-d`) into this branch:
  no conflicts; the `units.py` edit followed the rename to
  `units/__init__.py`; boundaries, skill, figsize, packaging and parity
  tests pass on the merged tree (306 tests).
- Real path, wheel in an empty project: install linked both targets, rerun
  `unchanged`; `--copy` replaced the link; an edited copy was refused and
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
`tests/test_figsize_ratio_strings.py`, `tests/test_agent_docs_runtime.py`
(corpus lists, panel-label recipe, MCP prompt version, AI hub claims,
mirrors, frozen asset paths), `tests/architecture/test_packaging.py`.

## Open issues and follow-ups

- Phase 1's pass condition (skill beats no-skill on the phase 0 set) needs
  the `evals/agentic/` baseline; the smoke runs are not that evidence.
- Overlap with #525–#528: `scripts/check_boundaries.py` (one `SLICES` line,
  all four PRs), `tests/test_deprecation_registry_parity.py` (#528, other
  hunk), `src/dartwork_mpl/units.py` (#526 renames it). All merge cleanly.
- `references/editing.md` shows `set_title(..., loc="left")`; phase 2 fixes
  layout and checks that ignore left titles today.
- This repository's `.agents/skills` is managed by skm; the skill is not
  linked into it.
- `make_palette` returns `oc.*` names while docs recommend `dc.*`; the skill
  does not route to it.
