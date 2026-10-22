# #523 phase 0: natural-language agent eval and baseline harness

Status: the harness is implemented, smoke-tested, and calibrated against the
full baseline (`evals/agentic/calibration/2026-10-22-baseline-audit.md`). The
pilot and the A/B comparison have not been run; the orchestrator runs them.
Branch: `t3/p0-agent-eval-20261022`, rebased on `origin/main` `f8ec26e5`.
Details and commands: `evals/agentic/README.md`. The eval is the external
decider (CLAUDE.md rule 2). Aesthetics are not a gate.

## Design

- **Cases.**
  - 40 cases: 25 generate and 15 edit, in EN and KO, for paper, report,
    slides and vague purposes. Prompts are natural language only.
  - 10 are `held_out` and must not be used while tuning.
  - Edits declare `edit_scope: explicit|broad`, `target` patterns (what the
    request may touch) and optionally `max_new_texts`.
  - Cases may declare `auxiliary` kinds (`reference_lines`, `fit_lines`).
- **Trees.**
  - Records (`~/scratch/dartwork-mpl-evals/<run>`): an append-only manifest,
    then `run.json`, transcripts, artifacts and scores per unit.
  - Agent projects (`~/scratch/dartwork-mpl-evals-work/<token>`): only the
    case inputs, their own venv with the pinned wheel installed from a
    project-local copy, and for edits the rendered base.
  - Repo paths are stripped from the child `PATH`.
  - Contamination: a path named in any tool call or output that resolves
    into the repo, the records or another project fails the unit.
  - `--hide-grading` runs hosts in bwrap. It was checked with both hosts.
- **Hosts.**
  - Claude: project-only settings, no MCP, the user's CLAUDE.md excluded, no
    auto-memory, 7 tools including Skill and Read; `stream-json` output.
  - Codex: user config, rules, plugins, memories, apps and user skills off;
    `workspace-write`. Runs are not `--ephemeral`: code-mode `exec`,
    `view_image` and sub-agents appear only in rollouts. Sub-agents are found
    by `parent_thread_id`.
  - Budgets live in the manifest and are identical across arms:
    - Claude: 20 turns, $5 and 300 s;
    - Codex: 300 s and 1.5M tokens including sub-agents, monitored and
      killed on overrun.

    `termination` is recorded.
- **Scoring.**
  - Execution means the agent's own outputs: valid PNG and PDF, the PDF parsed
    and rendered by poppler with the PNG's aspect, written during the run, and
    not older than the final `plot.py`.
  - The re-run must be pixel-identical (measured same-env noise is 0).
  - Data contracts bind identity, including legend handles, plus coordinates,
    order, multiplicity and NaN masks, over visible artists only.
  - Every visible data artist must be explained by a contract, a declared
    auxiliary, or a derivation from the input (`derived.py`: references,
    repeats of claimed points, input columns, jitter, ECDF, statistics, fits,
    leaders). A display scale needs its unit visible.
  - Grouped and stacked bar layouts, cumulative stacks and distinct panels are
    contracts.
  - Distributions are estimator contracts recomputed from raw rows:
    histogram counts (bars or steps), ECDF, a Gaussian KDE with fitted
    bandwidth (2% of peak), box median and quartiles, violin KDE shape. An
    unrecognised form is *unchecked*, never a pass.
  - Explicit edits fail on any changed or added non-target property (series
    keyed by their data): ticks, texts, alpha, rotation, position, legend.
- **Inspection.** A successful image tool result counts only if it is
  timestamped after the last write to `plot.py`/outputs, at least 400 px, and
  equal to the final PNG by sha256 or after the host's measured resize (Claude
  LANCZOS, Codex BILINEAR) within 3/255 at every pixel.
- **Comparison.**
  - Rows are validated against the manifest; missing or duplicate units make
    the result incomplete unless `--missing-as-failure` is passed.
  - `improved` needs a difference ≥ 0.10 and a case-bootstrap CI lower bound > 0.
  - Unknown token usage blocks noninferiority.

## Metrics

| Metric | Definition |
|---|---|
| `execution_success` | The agent left valid PNG and PDF from the final source, during the run. |
| `task_success` | Execution, a pixel-identical re-run, every check `ok`, explicit preservation, and not contaminated. |
| `inspection_observed` | A post-final-write image view equal to the final PNG (see above). |
| turns / tokens / time / termination | Claude `num_turns`; Codex rollout tool calls + 1. Tokens include cache and sub-agents. |
| defects | Outside (<25% in), clipped (>1 pt), overlap (≥15%), legend over data, duplicate text, missing glyphs, meaningless decimals (integer labels printed as `200.0`). |

## Self-validation (no model calls)

- `score.py --selftest`: 40 references, 7 broken-figure controls and the
  fixture checksums all pass.
- `pytest evals/agentic/test_scorer.py evals/agentic/test_regressions.py`: 76
  pass (24 mutation tests, 52 regression controls). On 407bda8d's scorer, 45
  of the 52 fail, one per review probe or bug. The other 7 are companions that
  pass on both: a true KDE, a declared reference line, an only-target edit, a
  10-point gain, an executed reference, clean decimals, and scatter-for-line
  (already rejected before, for another reason).
- `pytest evals/agentic/test_calibration.py`: 24 controls from the real
  baseline (13 audited-correct units pass and fail on the pre-calibration
  scorer; the unexecuted edit and 6 fabricating mutations fail; 4 contamination).
- Default `pytest` collects none of `evals/`.

## Smoke and baseline results

Smoke `smoke-20261022-r2` (3 Claude + 1 Codex units): all executed, succeeded
and were inspected. Baseline `baseline-main-20261022` (80 units, no skill,
`--hide-grading`) was audited unit by unit; 25 of 26 failures were scorer false
failures, fixed by general rules and rescored without reruns:

| host | task success before → after | contaminated before → after |
|---|---|---|
| claude (`sonnet`, high) | 28/40 → 40/40 | 4 → 0 |
| codex (`gpt-6-astra`, medium) | 26/40 → 39/40 | 3 → 0 |

The one remaining failure is true: codex g23 never executed its last edit.

## Not done / limitations

- The pilot and the A/B comparison have not been run.
- The Codex global `AGENTS.md` is isolated only with `--codex-home`.
- Codex sub-agents are allowed (the default) and counted.
  `--codex-no-subagents` gives parity runs.
- `~/scratch` contains both trees; only `--hide-grading` hides the records
  from a determined agent. Without it, access is detected, not prevented.
- Uncovered forms are unchecked, never passed (e.g. boxes without readable
  edges). The baseline saturates near 100%, so the A/B needs harder cases or
  reps to separate arms.
