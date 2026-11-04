# #523 phase 0: natural-language agent eval and baseline harness

Status: implemented, smoke-tested, calibrated on the full baseline
(`evals/agentic/calibration/`); A/B endpoints pre-registered below before any
skill-arm run; pilot done. Details: `evals/agentic/README.md`. The eval is
the external decider (CLAUDE.md rule 2); aesthetics are not a gate.

## Design

- **Cases.** 40 natural-language cases: 25 generate and 15 edit, in EN and
  KO, for paper, report, slides and vague purposes; 10 are `held_out`. Edits
  declare `edit_scope`, `target` (what the request may touch) and optionally
  `max_new_texts`; cases may declare `auxiliary` kinds.
- **Trees.** Records (`~/scratch/dartwork-mpl-evals/<run>`) and agent
  projects (`~/scratch/dartwork-mpl-evals-work/<token>`: inputs, own venv with
  the pinned wheel, the rendered base for edits).
- **Contamination fails closed.** `--hide-grading` (bwrap tmpfs over the repo,
  records, work root and HOME transcript stores; Codex gets a per-unit
  sessions dir) is the enforcement; skill runs require it and any unsandboxed
  unit blocks every verdict. Text evidence (`contamination.py`: paths, globs,
  `cd`/`workdir`, grading names; HOME transcript and Codex sqlite stores
  count) is OR-ed run time + rescore, never cleared; it gates unsandboxed
  units, and under the sandbox only what the sandbox neutralised is advisory.
- **Hosts.** Claude (project settings only, no MCP/CLAUDE.md/memory) and
  Codex (user config, rules, plugins, memories, user skills off); identical
  budgets per arm (Claude 20 turns, $5, 300 s; Codex 300 s, 1.5M tokens).
  Skill arm: `--ab-skill-install` runs `python -m dartwork_mpl.skills install`.
- **Scoring.** Execution: valid PNG and PDF from the final source, written
  during the run. Re-run pixel-identical (same-env noise 0). Data contracts
  bind identity, coordinates, order, multiplicity and NaN masks over visible
  artists; every other visible artist must be derivable from the input
  (`derived.py`). Distributions are recomputed estimators (histogram bars or
  steps, ECDF, KDE, box, violin); unrecognised forms are unchecked. Explicit
  edits fail on any non-target change (series keyed by their data).
- **Inspection.** An image view after the last write, at least 400 px, equal
  to the final PNG by sha256 or after the host's measured resize.
- **Source conformance.** `dm.lint_code` of the final `plot.py` by a fresh
  per-session interpreter built from the sha-verified wheel (0700, read-only
  bwrap), and preset overrides counted from its AST (`conformance.py`).

## Threat model (stopping rule for review rounds)

Agents are non-adversarial coding assistants; the risks are accidental access
to grading data and broken environments, not gaming. The sandbox enforces;
text detection is a fail-closed backstop; every score-affecting computation
runs in harness-owned environments. Findings that need a deliberately
adversarial agent are recorded as known limits (README), not fixed in this
phase. Per CLAUDE.md rule 2, the mechanical controls are the decider.

## Pre-registered skill A/B endpoints (2026-10-22, before any skill-arm run)

Task success saturates on the baseline (79/80), so it is a guardrail, not the
endpoint. `compare.py` holds the same text (`PREREGISTERED`, checked by
`test_endpoints.py`) and is the default `compare.py` output.

```text
Skill A/B (noskill vs skill, same wheel, --hide-grading, per host).
Primary 1 - inspection_observed: share of units whose agent viewed the final PNG
  after its last write (baseline noskill: claude 30/40, codex 31/40).
Primary 2 - API conformance: share of units whose final executed plot.py has zero
  dm.lint_code findings of severity critical or warning (raw figsize, tight_layout,
  plt.style.use, direct savefig, dpi argument, literal sizes/widths, oversize
  width, ...), linted with the wheel under test; info findings (e.g. a hex colour
  literal) are reported, not counted.
  Each primary: case-level bootstrap 95% CI of skill - noskill; improved needs a
  difference >= 0.10 and CI lower bound > 0; worse needs CI upper bound < 0.
Guardrails: task_success noninferior (CI lower bound of skill - noskill > -0.05);
  tokens noninferior (CI upper bound of skill/noskill total ratio <= 1.10).
Decision per host: the skill helps when at least one primary is improved, no
  primary is worse and both guardrails hold.
Secondary (descriptive, no verdict): visual defects per unit (incl.
  meaningless_decimals), unrequested preset overrides per unit (rcParams, fonts,
  figure/axes facecolor, style sheets; AST count), tokens, turns, wall time.
Contaminated units count as failures; any unsandboxed unit blocks every verdict.
```

## Self-validation (no model calls)

- `score.py --selftest` (40 references, 7 controls); `test_scorer.py` (24),
  `test_regressions.py` (52 review probes), `test_calibration.py` (24 from
  the real baseline; the 13 audited-correct units fail the old scorer).
- `test_contamination.py` (52): tokenizer, each backstop, OR-never-clear,
  sandbox coverage, exact own-rollout exemption; `test_endpoints.py` (24):
  lint/override counts, patched venv or planted env cannot clean the lint.
- Default `pytest` collects none of `evals/`.

## Baseline `baseline-main-20261022` (80 units, no skill, sandboxed)

25 of 26 failures were scorer false failures (audit), rescored without
reruns; codex g23 never executed its last edit. Lint findings: claude 13,
codex 27 (literal sizes/widths, oversize width); overrides mostly facecolor;
advisory text flags: 7 old `../` hits, 2 Claude `cd`s into its bundled skills.

| host | task success | inspected | lint clean | overrides/unit | text flags (advisory) |
|---|---|---|---|---|---|
| claude (`sonnet`, high) | 40/40 | 30/40 | 29/40 | 0.12 (2 units) | 6 |
| codex (`gpt-6-astra`, medium) | 39/40 | 31/40 | 24/40 | 0.65 (13 units) | 3 |

## Pilot `pilot-skill-20261022` (16 units, one p1 wheel `22f1a059`, sandboxed)

4 cases (e01, e15, g02, g09) x 2 hosts x 2 arms; every skill unit discovered
and invoked the installed skill; all 16 succeeded; no contamination flags.
n = 4 cases per host, so every primary is `inconclusive` (by design).

| host | inspected no -> skill | lint clean | task | tokens/unit | wall/unit |
|---|---|---|---|---|---|
| claude | 3/4 -> 4/4 | 2/4 -> 4/4 | 4/4 -> 4/4 | 157k -> 98k | 31 s -> 23 s |
| codex | 3/4 -> 2/4 | 3/4 -> 4/4 | 4/4 -> 4/4 | 720k -> 353k | 145 s -> 71 s |

## Not done / limitations

- The full A/B (40 x 2 hosts x 2 arms x 2 reps = 320 units) has not run;
  estimate ~120M tokens (Claude ~33M, about $24 at list price; Codex ~90M),
  about 2.5 h at `--jobs 4` including project setup.
- The Codex global `AGENTS.md` is isolated only with `--codex-home`; Codex
  sub-agents are allowed and counted (`--codex-no-subagents` for parity).
- Name markers can fire on package text that mentions them, and they gate
  even under the sandbox (fail closed).
- Lint counts depend on the wheel's linter: compare arms on one wheel only.
