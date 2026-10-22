# Agentic eval (#523 phase 0)

Natural-language plotting requests run headless in Claude Code and Codex
against an installed dartwork-mpl wheel, scored by deterministic checks. This
is the project's external decider (CLAUDE.md rule 2). It is outside the
package, not collected by the default `pytest` run, and not part of CI. Run it
by hand.

## Threat model (the stopping rule for review rounds)

- The agents under test are non-adversarial coding assistants. The risks are
  accidental access to grading data (cases, references, scores, other units'
  work or transcripts) and broken environments, not deliberate gaming.
- The sandbox (`--hide-grading`) is the enforcement. Text detection
  (`contamination.py`) is a fail-closed backstop. Every score-affecting
  computation (oracle re-run and probe, lint, AST counts) runs in
  harness-owned environments: the probe re-runs a copy, the lint uses an
  interpreter built per scoring session from the sha-verified wheel, the
  AST counts parse in the harness.
- Review findings that need a deliberately adversarial agent are recorded as
  known limits (below), not fixed in this phase. Known limits: an agent could
  tamper with its own venv so its *re-run* (not the lint) behaves differently
  from its PNG; it could read Codex's sqlite stores (visible, but gating
  text evidence); it could hide an access from the transcript (e.g. inside a
  script it writes and runs), which only the sandbox stops.
- This follows rule 2 of the repo's CLAUDE.md: the mechanical controls
  (`test_*.py`, `--selftest`) are the decider, not further review rounds.

## Files

| Path | Role |
|---|---|
| `cases/*.yaml` | 40 cases: 25 `generate` and 15 `edit`. Each has `id`, `kind`, `lang`, `purpose`, `held_out`, `prompt`, `data`, `oracle` and an optional `auxiliary`. Edit cases add `base`, `edit_scope`, `target` (the properties the requested change may touch) and optionally `max_new_texts`. |
| `fixtures/data/*.csv` | Frozen inputs, pinned by `SHA256SUMS`. `make_fixtures.py` records how they were made. |
| `fixtures/base/` | The starting `plot.py` for each edit case. |
| `fixtures/reference/` | One correct solution per case. Only `--selftest` uses them. |
| `fixtures/controls/` | 7 deliberately broken figures. Each one must trip its detector. |
| `fixtures/calibration/` | Agents' final `plot.py` from the real baseline, verbatim (`*.plot.txt`), with provenance in `index.json`. |
| `calibration/` | Audits of real runs: every failing unit, judged from its figure and source. |
| `run.py` | Creates the projects, runs the hosts and gathers evidence. |
| `probe.py` | Re-runs `plot.py` and snapshots the figure. |
| `views.py` | Fixture access and snapshot views. |
| `oracle.py` | Data contracts and the runner. |
| `estimators.py` | Histogram (bars and steps), KDE, ECDF and box contracts. |
| `derived.py` | Rules that explain unclaimed artists derived from the input. |
| `spec_checks.py` | Request checks. |
| `metrics.py` | Layout defects and edit preservation. |
| `score.py` | Scores a run, or runs the selftest. |
| `summary.py` | Writes `summary.md`. |
| `compare.py` | Paired A/B statistics and the pre-registered endpoints (`PREREGISTERED`). |
| `contamination.py` | Text evidence of grading-file access (fail-closed backstop to the sandbox). |
| `conformance.py` | Unrequested preset overrides in the final source (AST). |
| `lint_source.py` | `dm.lint_code` of the final source, run by a trusted interpreter in a read-only bwrap. |
| `sheet.py` | Contact sheets. |
| `ab_sheet.py` | A/B sheet: per host and case, noskill and skill figures at one scale with their scores. |
| `test_scorer.py` | Mutation controls. |
| `test_regressions.py` | Round-2 review probes, pinned as regression controls. |
| `test_calibration.py` | Real-baseline controls: audited-correct units pass, true failures and fabricated mutations fail. |
| `test_contamination.py` | Fail-closed contamination: tokenizer, each backstop, OR-never-clear, sandbox gating. |
| `test_endpoints.py` | Lint and override metrics; the plan doc and `compare.py` state the same endpoints. |

## Trees, and what the agent sees

A run has two trees.

- **Records:** `ROOT/<run-id>/`, by default `~/scratch/dartwork-mpl-evals/`. It holds:
  - `manifest.json`: wheel sha, config, budgets, and every planned unit. Plans
    are append-only; extending a run with another wheel or config is refused;
  - `run_meta.json`;
  - one directory per unit, `<host>/<case>/<arm>-r<k>/`, with `run.json`,
    transcripts or rollouts, `artifacts/`, `base_out/` and `score.json`.

  Completed units are immutable, and new repetitions get new ids.
- **Work:** `WORK_ROOT/<opaque-token>/`, by default
  `~/scratch/dartwork-mpl-evals-work/`. This is the agent's project and its
  working directory. It holds:
  - the case's CSVs in `data/`;
  - its own `.venv`, holding the wheel and pandas. The wheel is installed from
    a project-local copy, which is then deleted;
  - for edit cases, the base `plot.py` and its rendered `out/`;
  - a git repo.

  No ancestor of a project holds a manifest, run metadata or a pointer to the
  repo. Repo paths are also stripped from the child `PATH`.

Cases, oracles, references and scorer code stay in this repository. The prompt
suffix (`common.SUFFIX`) states only the library, the interpreter and the output
paths. Prompts never name a skill.

**Contamination fails closed.** The enforcement is the sandbox:
`--hide-grading` runs each host inside `bwrap`, mounting empty `tmpfs` over the
repo, the records root and the work root and re-binding only the unit's
project (checked with both hosts, including Codex's own sandbox nested
inside). It also hides other sessions' transcripts and histories under HOME
(`~/.claude/projects`, `file-history`, `sessions`, `history.jsonl`;
`~/.codex/archived_sessions`, `history.jsonl`, `session_index.jsonl`, `log`):
directories get an empty tmpfs, files an empty per-unit copy, and a Codex
unit gets a fresh per-unit `~/.codex/sessions` (the harness reads its own
rollouts there). Codex's sqlite stores stay visible because Codex needs them. Plain filesystem access cannot hide `~/scratch`, which contains both
trees, so skill (decision) runs refuse to start without it, the manifest
records it, and `compare.py`/`summary.py` block every verdict when any unit
ran without it (`sandboxed` per unit: bwrap with the records, the work root
and this repo hidden).

Text evidence (`contamination.py`) reads the decoded transcript objects (the
Claude transcript; the Codex stream and rollouts) as raw strings, so `\n`,
`\t` and `\"` separate words. A hit is:

- a path that resolves into a grading root: a repo checkout, the records tree
  or another project (absolute anywhere in a word, `~`/`$HOME`, or relative to
  the current directory, which `cd`/`pushd`/`workdir` move; `//` collapses
  except after a URL scheme);
- in a command, a glob or expansion (`*?[$`{`) whose literal prefix is a
  string prefix of a grading root or another project, or whose pattern reaches
  one component by component;
- `cd`/`pushd` or a tool `workdir` outside the project;
- a grading file name: `evals/agentic`, `fixtures/reference`, `score.json`,
  `manifest.json`, `run_meta.json` (package text that mentions them can trip
  this; it fails closed).

Those HOME transcript stores (and the Codex sqlite stores) are grading roots
for the text evidence too; the only exemptions are this unit's own rollout
files, recorded in `run.json` (`own_rollouts`, with the thread or session id)
while the harness owns them and compared for exact path equality. `score.py` ORs the run-time result with a recheck
of the stored transcript under the current rule; a recheck never clears a
flag. The result is kept as `contamination_text`. Without the sandbox every
finding sets `contaminated` (never a success, a failure in comparisons).
Under the sandbox, findings it neutralised (a path inside a root it hid or
replaced) are advisory and reported (`text flags` in the summary), while
grading names and paths it did not hide (e.g. another session's transcript,
a Codex sqlite store) still set `contaminated` (`contamination_text.gating`).

## Host isolation and budgets

- **Claude Code** runs with:
  - `--setting-sources project`, so user settings, plugins and hooks are not loaded;
  - `--strict-mcp-config`, so no MCP servers are loaded;
  - `claudeMdExcludes` on `~/.claude/**`, so the user's CLAUDE.md is not loaded;
  - auto-memory disabled;
  - tools limited to `Bash, Read, Write, Edit, Glob, Grep, Skill`.

  Built-in skills (including `/dataviz`) stay on. There is no agent-spawning tool.
- **Codex** runs with:
  - `--ignore-user-config` and `--ignore-rules`;
  - plugins, memories and apps disabled;
  - every user-level skill disabled through `skills.config`;
  - the `workspace-write` sandbox, which also blocks network access.

  Limitations:
  - **Global instructions leak.** `$CODEX_HOME/AGENTS.md` still loads unless
    you pass `--codex-home`. Its hash is recorded.
  - **Sessions are kept.** Runs are not `--ephemeral`. Code-mode `exec`,
    `view_image` and sub-agents appear only in rollouts, so the rollouts are
    needed as evidence.
  - **Sub-agents.** They stay on (Codex's default). They are found through
    `parent_thread_id` and counted in turns, tokens and inspection.
    `--codex-no-subagents` gives parity runs.
- **Budgets.** The manifest records them, and they are identical across arms
  and invocations:
  - Claude: `--max-turns 20`, `--max-budget-usd 5` and a 300 s wall clock.
  - Codex: a 300 s wall clock, and 1,500,000 tokens (input + output, sub-agents
    included). The token budget is enforced by polling the rollouts every 2 s
    and killing the process group on overrun.

  `run.json` records `termination` as one of: `completed`, `turn_limit`,
  `budget_usd`, `timeout`, `token_budget`, `error`. Every host call uses the
  subscription login, and no `ANTHROPIC_API_KEY` reaches the child. Models are
  pinned and recorded: Claude `sonnet` with `high` effort, and Codex
  `gpt-6-astra` with `medium` effort.

## Commands

Use `uv run python evals/agentic/...` from the repo root.

```sh
# 1. Harness self-checks. No model calls.
uv run python evals/agentic/score.py --selftest   # 40 references, 7 controls, fixture checksums
uv run pytest evals/agentic/test_scorer.py evals/agentic/test_regressions.py \
    evals/agentic/test_calibration.py evals/agentic/test_contamination.py evals/agentic/test_endpoints.py -q

# 2. Smoke run (3 Claude units + 1 Codex unit in one run id), then score and draw sheets.
R=smoke-$(date +%Y%m%d-%H%M)
uv run python evals/agentic/run.py --run-id $R --host claude \
    --case g01-line-gdp --case g14-korean-combo --case e01-label-step-en --jobs 3
uv run python evals/agentic/run.py --run-id $R --host codex --case g01-line-gdp
uv run python evals/agentic/score.py ~/scratch/dartwork-mpl-evals/$R
uv run python evals/agentic/sheet.py ~/scratch/dartwork-mpl-evals/$R

# 3. Full baseline: 40 cases x 2 hosts on one pinned wheel.
uv build --wheel --out-dir ~/scratch/dartwork-mpl-evals/wheels/main-$(git rev-parse --short HEAD)
uv run python evals/agentic/run.py --run-id baseline-$(date +%Y%m%d) --jobs 4 \
    --wheel ~/scratch/dartwork-mpl-evals/wheels/main-$(git rev-parse --short HEAD)/dartwork_mpl-*.whl
uv run python evals/agentic/score.py ~/scratch/dartwork-mpl-evals/baseline-$(date +%Y%m%d)
uv run python evals/agentic/sheet.py ~/scratch/dartwork-mpl-evals/baseline-$(date +%Y%m%d)

# 4. Skill A/B. Same wheel; both arms in one run; seeded random order; repetitions;
#    sandbox required. --ab-skill-install runs the wheel's own installer in the
#    project (python -m dartwork_mpl.skills install); --ab-skill DIR copies a folder.
cc-swap job --prefer quota -- uv run python evals/agentic/run.py --run-id skill-ab-$(date +%Y%m%d) \
    --jobs 4 --reps 2 --hide-grading --claude-model sonnet \
    --wheel PATH/TO/SAME.whl --ab-skill-install
uv run python evals/agentic/score.py ~/scratch/dartwork-mpl-evals/skill-ab-$(date +%Y%m%d)
uv run python evals/agentic/compare.py ~/scratch/dartwork-mpl-evals/skill-ab-$(date +%Y%m%d)   # pre-registered endpoints
uv run python evals/agentic/compare.py RUN --metric task_success                             # one metric
uv run python evals/agentic/ab_sheet.py ~/scratch/dartwork-mpl-evals/skill-ab-$(date +%Y%m%d)    # writes ab-sheet.png
uv run python evals/agentic/compare.py --a RUN_A --b RUN_B   # two runs; manifests validated
```

`--with-skill DIR` runs only the skill arm. Re-invoking `run.py` with an
existing `--run-id` adds units. It needs the same wheel and config, and new
repetitions get the next rep numbers. Keep `--jobs` at 7 or below.

## Held-out cases

10 cases carry `held_out: true`:

- `g03`, `g07`, `g11`, `g15`, `g20`, `g24`;
- `e04`, `e08`, `e10`, `e14`.

Do not read, run or inspect them while tuning a skill, docs or prompts. The
comparison tables report them separately.

## Metrics (per run unit)

- **execution_success.** The agent's own run left `out/figure.png` and
  `out/figure.pdf` (copied to `artifacts/` the moment the host exits). Both must:
  - be valid: the PNG decodes; `pdfinfo` parses the PDF; `pdftoppm` renders
    page 1, and its aspect is within 2% of the PNG's;
  - have been written during the run;
  - be no older than the final `plot.py`, so an edit that was never executed
    fails.
- **rerun_ok / rerun_matches.** `plot.py` is re-run in a fresh process, in the
  unit's venv, through `probe.py`. It must save both files, and the re-run PDF
  must be valid. The re-run PNG must be **pixel-identical** to the original:
  the measured same-environment noise is 0.
- **task_success.** All of the following hold:
  - execution;
  - a matching re-run;
  - every check `ok` (an *unchecked* result is not a pass);
  - preservation for explicit edits;
  - not contaminated.
- **inspection_observed.** A successful image tool result, timestamped after the
  last write to `plot.py` or the outputs, shows the final PNG.
  - Evidence: the Claude `Read` result, or Codex `view_image` in the parent or
    a sub-agent rollout, merged by time.
  - The match is by sha256. Otherwise the final PNG is resized with the hosts'
    measured filters (Claude LANCZOS, Codex BILINEAR) and must match within
    3/255 at every pixel.
  - Views under 400 px on the long side, and views without a timestamp, do not
    count. A text self-report never counts.
- **Turns, tokens, time.**
  - Claude turns come from `num_turns`. Codex turns are the rollout tool calls,
    sub-agents included, + 1.
  - Tokens include cache and sub-agents. The raw usage is kept.
  - Compare within a host only.
- **Defects.** These are computed from drawn-text and artist geometry,
  independent of `dm.validate_figure`, whose findings are advisory input only.
  - `text_outside`: less than 25% of a drawn text is inside the canvas. This
    includes `_left_title`, `_right_title` and suptitles.
  - `text_clipped`: a drawn text extends more than 1 pt past an edge.
  - `text_overlap`: texts whose rotated boxes overlap another text by at least
    15% of the smaller box.
  - `legend_covers_data`.
  - `duplicate_text`: the same non-numeric string twice in one scope.
  - `missing_glyphs`.
  - `meaningless_decimals`: a tick set, or an axes' value labels, where every
    number is integer-valued but some are printed with trailing zeros (`200.0`,
    `1.0k`). Fractional steps such as `17.5 / 20.0 / 22.5` are fine.
- **Oracle `values` contracts.** These bind identity, coordinates, order,
  multiplicity and NaN masks, and claim the artists they explain. Only
  *visible* artists count: hidden, alpha 0, or no stroke and no marker is
  invisible. Identity comes from:
  - a label, or a legend handle (`label=` is not required; a proxy handle
    names the same-coloured artists of its axes when no other entry shares
    the colour);
  - the panel's name: its centre, left or right title or y label; else a text
    inside the panel; else, with one data panel, the suptitle or a figure
    text. Only texts naming exactly one series count, and the top-most wins,
    so "Sessions and signups" names nothing and a unit subtitle does not
    override the title;
  - an end label: a text or annotation of the same panel next to the line end.

  A display scale (thousands, millions, percent, ...) is accepted only as one
  factor for the whole artist and only when a visible text of its panel
  states the unit (`Active users (thousands)`, `12k`, `%`).
  - `series`: one-to-one; an extra artist labelled as a series fails;
    `panels: distinct` puts each series in its own axes.
  - `bars`: category → value, plus `layout: grouped` (side by side from 0) or
    `layout: stacked` (cumulative from 0).
  - `points`.
  - `fits`.
  - `dist`: per-group estimator contracts recomputed from the raw rows:
    - histogram counts in the drawn bins (bars, `stairs`, `step`/`stepfilled`);
    - an ECDF: every observation a vertex, each height within its jump;
    - a Gaussian KDE, up to one scale factor, for a fitted bandwidth, within
      2% of the peak;
    - box median and Q1/Q3 at the labelled tick;
    - a violin body with the KDE shape and the data range.

    A form no contract recognises is *unchecked* (`ok: null`), never a pass.
  - `matrix`.
  - `stack`: per-layer thickness, with layers tiling [0, total] at every x.
  - `errorbars`.
  - `span`.

  Finally, every visible data artist must be claimed by a contract (failing
  contracts claim too), match a declared `auxiliary` kind (`reference_lines`,
  `fit_lines`), or be derivable from the input (`derived.py`): a constant
  reference line; a repeat of claimed points (context copies, endpoint
  markers); a contiguous run of an input column; jittered observations of a
  distribution group; an ECDF; points at a group's mean, median, min, max or
  quantile; a least-squares fit; a short leader line from a claimed point to a
  text. Made-up values match none of these. Errorbar caps are always
  auxiliary.
- **Oracle `spec` checks.** These cover the request: size, aspect, preset,
  scale, twin axes, panel ratio, grid, shared limits, legend placement, sorting,
  highlight, end labels, label font-size delta, and "no more defects than the
  base".
- **Preservation (edit cases).** This diffs a property snapshot:
  - figure size;
  - axes positions, scales, limits, tick locations and texts, and tick style;
  - spines;
  - text, size, weight, colour, alpha, rotation and position for each role and
    each annotation;
  - line label, colour, width, style, marker, alpha and visibility, keyed by
    the line's data digest (including the NaN mask), so relabelling or
    re-ordering is not a change of every property and changed data is;
  - bar and scatter labels, colours and alpha, keyed the same way;
  - legend location, texts, size and bbox.

  Placements (`.position`, `.pos`, `.bbox`) are compared with a 0.03 figure
  fraction tolerance. For `explicit` edits, a missing base snapshot, any
  changed non-target property, any **added** non-target property, or more new
  texts than `max_new_texts` fails. `target` declares what the requested
  change legitimately touches: a highlight may restyle every series and
  replace the legend with one direct label per series; end labels may remove
  the legend and the series labels. For `broad` edits, only the data
  contracts are hard checks.
- **Comparison (`compare.py`).**
  - Rows are validated against the manifest's planned units. A missing or
    duplicate unit makes the result **incomplete**, unless you pass
    `--missing-as-failure`.
  - Without a manifest, the arms must at least mirror each other.
  - Per host, a case-level bootstrap 95% CI gives the success difference.
    `improved` needs a difference ≥ 0.10 **and** a CI lower bound > 0.
    `worse` needs a CI upper bound < 0.
  - Tokens use a 10% noninferiority margin. Any unknown usage blocks the token
    verdict.
  - Any unsandboxed unit, or a manifest without `hide_grading`, blocks every
    verdict.
  - **Pre-registered skill A/B** (`compare.PREREGISTERED`, also in the plan
    doc; the default output): primaries `inspection_observed` and API
    conformance (`lint_clean`: zero `dm.lint_code` findings of severity
    critical or warning in the final source, with the wheel under test), each
    `improved` at ≥ 0.10 with a CI lower bound > 0; guardrails task success
    (noninferior at 5 points) and tokens (10%); secondaries descriptive:
    defects, meaningless decimals, preset overrides, lint findings, tokens,
    turns, time.
- **Source conformance (per unit).** `lint_findings` (critical + warning),
  `lint_findings_all` and per-rule counts from `dm.lint_code`, run with a
  trusted interpreter, never the agent-writable project venv: the run's wheel
  (checked against the manifest sha256) installed into a fresh mode-0700
  directory per scoring session (`~/.cache/dartwork-mpl-evals/lint-envs/
  session-*`, removed at exit; no env is ever looked up by path), run inside
  a read-only bwrap with the repo, records and work trees hidden, the source
  on stdin (`lint.interpreter`, `lint.wheel_sha256` are recorded);
  `preset_overrides` (`conformance.py`: rcParams writes, font changes,
  figure/axes facecolor, non-dartwork style sheets; distinct source lines;
  parsed in the harness, nothing from the project executed).

Aesthetic preference is not a gate. Look at `sheet-<host>-<arm>.png`; edit
cases show the before and after figures side by side.
