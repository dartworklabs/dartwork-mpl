# #523 phase 0: natural-language agent eval and baseline harness

Status: the harness is implemented and smoke-tested. The full baseline, the
pilot and the A/B comparison have not been run; the orchestrator runs them
after review. Branch: `t3/p0-agent-eval-20261022`, from `origin/main` `c332c7ab`.
Details and commands: `evals/agentic/README.md`. The eval is the external
decider (CLAUDE.md rule 2) for later phases. Aesthetics are not a gate.

## Design choices

- **Cases.** 40 cases: 25 generate and 15 edit, in EN and KO, for paper,
  report, slides and vague purposes. Prompts are natural language only.
  - 10 are `held_out` (6 generate, 4 edit; 6 KO, 4 EN) and must not be used
    while tuning.
  - Edits declare `edit_scope: explicit|broad` and `target` patterns.
- **One fresh project per unit** (`<run>/<host>/<case>/<arm>-r<k>/project`):
  a `uv venv` with one pinned wheel plus pandas, and git.
  - Only the case's CSVs, and for edits the base `plot.py`, are agent-visible.
  - `--wheel` pins the bytes. `--ab-skill` runs both arms on that wheel, in
    seeded random order, with `--reps`.
- **Isolation.**
  - Claude: project-only settings, no MCP, the user's CLAUDE.md excluded, no
    auto-memory, and 7 tools including Skill and Read. Built-in skills,
    including `/dataviz`, stay on.
  - Codex: user config, rules, plugins, memories, apps and user skills off, in
    the `workspace-write` sandbox. Its global `AGENTS.md` still leaks: it is
    hashed into `run.json`, and `--codex-home` removes it.
  - Caps: 20 turns, 300 s and $5 per unit, on the subscription login with an
    allowlisted environment.
- **Evidence.**
  - Claude runs with `stream-json`, whose `result` event equals `json` output.
  - Codex runs are not `--ephemeral`, because code-mode `exec`, `view_image`
    and sub-agents appear only in rollouts. Sub-agents are found by
    `parent_thread_id`.
- **Original artifacts first.** Outputs are copied when the host exits. A
  fresh re-run through `probe.py` must then reproduce the PNG (mean absolute
  difference ≤ 0.01) before any check counts.
- **Data contracts, not value pools.** Expected values come from the frozen
  CSVs, pinned by `SHA256SUMS`. Contracts bind identity (label, panel title or
  ylabel, or end label), paired coordinates, order, multiplicity and NaN masks.
  Distributions accept any of:
  - per-bin counts recomputed from raw rows;
  - labelled medians;
  - violin extremes;
  - a unit-area KDE.
- **Defects** are computed from drawn-text geometry, including `_left_title`
  and `_right_title`. `dm.validate_figure` is advisory only.
- **Preservation.** Explicit edits must leave every non-target property
  unchanged: data and NaN mask, scales, limits, spines, per-role text style,
  line style, positions, legend, figure size. Broad edits are judged on data
  contracts only.

## Metrics

| Metric | Definition |
|---|---|
| `execution_success` | The agent's run left a valid PNG and PDF, written during the run, plus `plot.py`. |
| `task_success` | Execution success, a reproducing re-run, all oracle checks, and preservation for explicit edits. Defects are reported, not gated. |
| `inspection_observed` | A tool event delivered the final PNG's pixels to the model (sha256 or resized-pixel match). A text claim never counts. |
| turns / tokens / time | Claude `num_turns`; Codex rollout tool calls + 1. Tokens include cache and sub-agents. Compare within a host. |
| defects | Text outside the canvas (<25% inside), clipped (>1 pt), overlapping (≥15%), legend over data, duplicated text, missing glyphs. |
| A/B (`compare.py`) | Per host. Success difference with a case-level bootstrap 95% CI; tokens with a 10% noninferiority margin. Verdict: improved, inconclusive or worse, for all cases and for held-out cases. |

## Self-validation (no model calls)

- `score.py --selftest` passes all 40 references (base re-runs included), all 6
  broken-figure controls and the fixture checksums.
- `pytest evals/agentic/test_scorer.py`: 24 pass. Correct figures are accepted;
  18 mutations are rejected:
  - swapped labels, categories, groups or layers;
  - reordered or swapped coordinates;
  - removed rows or observations;
  - a dropped NaN gap;
  - duplicates.

  Explicit preservation flags a one-property change.
- Default `pytest` collects 6914 tests, none from `evals/`; the eval is not in CI.
- True positives in dm found during validation:
  - `loc="left"` panel titles are lost above the canvas (references g17, g18;
    marked `known-defect`).
  - A narrowed panel's legend covers data (e03).

## Smoke results (`smoke-20261022`, main wheel, no skill)

Claude is `sonnet` (resolved to `claude-sonnet-5-5`) with high effort. Codex is
`gpt-6-astra` with medium effort.

| Case | Host | Exec | Task | Inspected | Turns | Tokens | Time (s) | Defects |
|---|---|---|---|---|---|---|---|---|
| g01-line-gdp | claude | yes | yes | yes | 22 | 476,736 | 75 | 5 duplicate_text (legend and end labels) |
| g14-korean-combo | claude | yes | yes | yes | 15 | 219,068 | 42 | 0 |
| e01-label-step-en | claude | yes | yes; 58/58 props kept | no | 7 | 120,675 | 18 | 0 |
| g01-line-gdp | codex | yes | yes | yes | 18 | 427,453 (sub-agent: 203,165) | 76 | 0 |

The scores match the contact sheets.

Observations:

- Claude called the built-in `/dataviz` first in both generate cases.
- On e01 Claude used `dm.fs(1)` and did not view the result.
- Codex delegated the plot to a `gpt-6.1-sol` sub-agent.

Harness bugs fixed during bring-up: hist labels on the first patch, Hangul
alias matching, Codex activity missing from `--json` (the smoke unit was
re-derived from its rollouts), appending to a run, and sheet size.

## Not done / limitations

- The full 40×2 baseline, the pilot and the A/B comparison have not been run.
- Codex sub-agents are allowed (the default) and counted. Claude has no spawn
  tool here; `--codex-no-subagents` gives parity runs.
- Contract coverage gaps:
  - `histtype="step"` histograms are not covered;
  - box plots are checked by medians only;
  - categorical line x values are checked for order only.
