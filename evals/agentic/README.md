# Agentic eval (#523 phase 0)

Natural-language plotting requests run headless in Claude Code and Codex
against an installed dartwork-mpl wheel, scored by deterministic checks. This
is the project's external decider (CLAUDE.md rule 2). It is outside the
package, not collected by the default `pytest` run, and not part of CI. Run it
by hand.

## Files

| Path | Role |
|---|---|
| `cases/*.yaml` | 40 cases: 25 `generate` and 15 `edit`. Each has `id`, `kind`, `lang`, `purpose`, `held_out`, `prompt`, `data` and `oracle`. Edit cases add `base`, `edit_scope` and `target`. |
| `fixtures/data/*.csv` | Frozen inputs, pinned by `SHA256SUMS`. `make_fixtures.py` records how they were made. |
| `fixtures/base/` | The starting `plot.py` for each edit case. |
| `fixtures/reference/` | One correct solution per case. Only `--selftest` uses them. |
| `fixtures/controls/` | Deliberately broken figures. Each one must trip its detector. |
| `run.py` | Creates the projects and runs the hosts. |
| `probe.py` | Re-runs `plot.py` and snapshots the figure. |
| `oracle.py` | Data contracts and request checks. |
| `metrics.py` | Layout defects and edit preservation. |
| `score.py` | Scores a run, or runs the selftest. |
| `summary.py` | Writes `summary.md`. |
| `compare.py` | Paired A/B statistics. |
| `sheet.py` | Contact sheets. |
| `test_scorer.py` | Mutation controls. |

## What the agent sees

Each run unit is `ROOT/<run-id>/<host>/<case>/<arm>-r<k>/`. Only `project/` is
the agent's working directory. It holds:

- the case's CSVs in `data/`;
- `.venv`, with the evaluated wheel and pandas;
- for edit cases, the base `plot.py` and its rendered `out/`;
- a git repo, used to diff the agent's changes.

Cases, oracles, references and scorer code stay in this repository. The prompt
suffix (`common.SUFFIX`) states the library, the interpreter and the output
paths. It never describes a workflow: no review step, no API hints. Prompts
never name a skill.

Host isolation:

- **Claude Code** runs with:
  - `--setting-sources project`, so user settings, plugins and hooks are not loaded;
  - `--strict-mcp-config`, so no MCP servers are loaded;
  - `claudeMdExcludes` on `~/.claude/**`, so the user's CLAUDE.md is not loaded;
  - auto-memory disabled;
  - tools limited to `Bash, Read, Write, Edit, Glob, Grep, Skill`.

  Built-in skills (including `/dataviz`) stay on, as they would be for any user.
- **Codex** runs with:
  - `--ignore-user-config` and `--ignore-rules`;
  - plugins, memories and apps disabled;
  - every user-level skill disabled through `skills.config`;
  - the `workspace-write` sandbox, which also blocks network access.

  Two limitations apply:
  - **Global instructions leak.** `$CODEX_HOME/AGENTS.md` cannot be excluded
    without moving the login. Its hash is recorded in `run.json`. To remove the
    leak, pass `--codex-home DIR` with a separately logged-in home.
  - **Sessions are kept.** Codex runs are not `--ephemeral`. Only the session
    rollout records code-mode `exec` calls, `view_image` and sub-agents, so it
    is needed as evidence. The rollout is copied into the run unit, and the
    session also stays in that Codex home's history.
  - **Sub-agents.** Codex's default `multi_agent` stays on. Sub-agent rollouts
    are found through `parent_thread_id` and copied as `rollout-sub*.jsonl`.
    Their tool calls and tokens are added to the unit, and their image views
    count as inspection. Claude has no agent-spawning tool here; for parity
    runs, pass `--codex-no-subagents`.

Every host call uses the user's subscription login. The child environment is an
allowlist, so no `ANTHROPIC_API_KEY` reaches it. Defaults are 20 turns, 300 s
and $5 list-cost per unit. Models are pinned and recorded: Claude `sonnet` with
`high` effort, and Codex `gpt-6-astra` with `medium` effort.

## Commands

Use `uv run python evals/agentic/...` from the repo root.

```sh
# 1. Harness self-checks. No model calls.
uv run python evals/agentic/score.py --selftest      # 40 references, 6 controls, fixture checksums
uv run pytest evals/agentic/test_scorer.py -q         # scorer mutation controls

# 2. Smoke run (3 Claude units + 1 Codex unit), then score and draw sheets.
uv run python evals/agentic/run.py --run-id smoke-20261022 --host claude \
    --case g01-line-gdp --case g14-korean-combo --case e01-label-step-en --jobs 3
uv run python evals/agentic/run.py --run-id smoke-20261022 --host codex --case g01-line-gdp
uv run python evals/agentic/score.py ~/scratch/dartwork-mpl-evals/smoke-20261022
uv run python evals/agentic/sheet.py ~/scratch/dartwork-mpl-evals/smoke-20261022

# 3. Full baseline: 40 cases x 2 hosts on one pinned wheel.
uv build --wheel --out-dir ~/scratch/dartwork-mpl-evals/wheels/main-$(git rev-parse --short HEAD)
uv run python evals/agentic/run.py --run-id baseline-$(date +%Y%m%d) --jobs 4 \
    --wheel ~/scratch/dartwork-mpl-evals/wheels/main-$(git rev-parse --short HEAD)/dartwork_mpl-*.whl
uv run python evals/agentic/score.py ~/scratch/dartwork-mpl-evals/baseline-$(date +%Y%m%d)
uv run python evals/agentic/sheet.py ~/scratch/dartwork-mpl-evals/baseline-$(date +%Y%m%d)

# 4. Skill A/B. Same wheel; both arms in one run; random paired order; repetitions.
uv run python evals/agentic/run.py --run-id skill-ab-$(date +%Y%m%d) --jobs 4 --reps 2 \
    --wheel PATH/TO/SAME.whl --ab-skill PATH/TO/skills/dartwork-mpl
uv run python evals/agentic/score.py ~/scratch/dartwork-mpl-evals/skill-ab-$(date +%Y%m%d)
uv run python evals/agentic/compare.py ~/scratch/dartwork-mpl-evals/skill-ab-$(date +%Y%m%d)
# Or compare two separate runs (warns if the wheels differ):
uv run python evals/agentic/compare.py --a RUN_A --b RUN_B
```

`--with-skill DIR` runs only the skill arm. `--seed` fixes the shuffled unit
order. Re-invoking `run.py` with an existing `--run-id` adds units to that run
and reuses its wheel. Keep `--jobs` at 7 or below.

## Held-out cases

10 cases carry `held_out: true`:

- `g03`, `g07`, `g11`, `g15`, `g20`, `g24`;
- `e04`, `e08`, `e10`, `e14`.

They cover both kinds, both languages and every purpose. Do not read, run or
inspect them while tuning a skill, docs or prompts. Report them separately; the
comparison tables split `all` from `held_out`.

## Metrics (per run unit)

- **execution_success.** The agent's own run left a valid `out/figure.png` and
  `out/figure.pdf`, written during the run, plus a `plot.py`. The original
  artifacts are copied to `artifacts/` the moment the host exits, so scoring
  never depends on a re-run.
- **rerun_ok / rerun_matches.** `plot.py` is re-run in a fresh process, in the
  case's own venv, through `probe.py`. The re-run must save both files again.
  Its PNG must also reproduce the original (same pixel size; mean absolute
  difference ≤ 0.01).
- **task_success.** All of the following hold:
  - execution_success;
  - a reproducing re-run;
  - every oracle check;
  - for explicit edits, preservation.
- **inspection_observed.** A host tool event delivered the final PNG's pixels to
  the model. The evidence is Claude's `Read` tool result, or Codex's
  `view_image` output in its rollout. The viewed image is matched to the final
  PNG by sha256, or by pixels after resizing. A text self-report does not count.
  The value is `null` when the event log is missing.
- **Turns, tokens, time.**
  - Claude turns come from `num_turns`. Codex turns are the rollout tool calls, sub-agents included, + 1.
  - Tokens include cache read and write. The raw usage JSON is kept in `run.json`.
  - Token counts mean different things on the two hosts. Compare within a host only.
- **Defects.** These are computed from matplotlib geometry, independent of
  `dm.validate_figure`, whose findings are only recorded as advisory input.
  - `text_outside`: less than 25% of a drawn text is inside the canvas. This
    covers `_left_title`, `_right_title` and suptitles.
  - `text_clipped`: a drawn text extends more than 1 pt past an edge.
  - `text_overlap`: the number of texts whose rotated boxes overlap another
    text by at least 15% of the smaller box.
  - `legend_covers_data`: a legend frame covers line samples, markers, bars or
    filled areas.
  - `duplicate_text`: the same non-numeric string appears twice in one axes, or
    a figure-level text repeats an axes text.
  - `missing_glyphs`: matplotlib reported a glyph missing from the font, for
    example Hangul tofu.
- **Oracle `values` contracts.** These bind identity, order, multiplicity and NaN masks:
  - `series`: name → (x, y). Data and NaN gaps must match exactly. The name may
    come from a label, a panel title or ylabel, or an end label.
  - `bars`: category → value. The category is the tick at the bar; the series
    is the container label.
  - `points`: the multiset of (x, y) for each named group.
  - `fits`: the slope of each group's fit line.
  - `dist`: per-bin counts recomputed from raw rows, group medians, violin
    extremes, or a KDE that integrates to 1.
  - `matrix`: tick-labelled cells.
  - `stack`: per-layer thickness.
  - `errorbars`.
  - `span`.
- **Oracle `spec` checks.** These cover the request: size, aspect, preset,
  scale, twin axes, panel ratio, grid, shared limits, legend placement, sorting,
  highlight, end labels, label font-size delta, and "no more defects than the
  base".
- **Preservation (edit cases).** This diffs a property snapshot:
  - figure size;
  - axes positions (tolerance 0.03 figure fraction), scales and limits;
  - spines;
  - size, weight and colour of the text in each role;
  - line colour, width, style and marker, and the data digest including the NaN mask;
  - bar and scatter colours and data;
  - legend location, texts and size.

  For `edit_scope: explicit`, every property outside `target` must be
  unchanged. For `broad`, only the data contracts are hard checks; the diff is
  reported.
- **Comparison (`compare.py`).** Per host:
  - per case, average over repetitions;
  - the B-A difference in success, with a case-level bootstrap 95% CI that
    resamples cases, not repetitions;
  - the B/A token ratio, with a 10% noninferiority margin.

  The verdict is improved, inconclusive or worse.

Aesthetic preference is not a gate. Look at `sheet-<host>-<arm>.png`; edit
cases show the before and after figures side by side.
