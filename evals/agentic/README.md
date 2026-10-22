# Agentic eval (#523 phase 0)

Natural-language plotting requests run headless in Claude Code and Codex
against an installed dartwork-mpl wheel, scored by deterministic checks. This
is the project's external decider (CLAUDE.md rule 2). It is outside the
package, not collected by the default `pytest` run, and not part of CI. Run it
by hand.

## Files

| Path | Role |
|---|---|
| `cases/*.yaml` | 40 cases: 25 `generate` and 15 `edit`. Each has `id`, `kind`, `lang`, `purpose`, `held_out`, `prompt`, `data`, `oracle` and an optional `auxiliary`. Edit cases add `base`, `edit_scope` and `target`. |
| `fixtures/data/*.csv` | Frozen inputs, pinned by `SHA256SUMS`. `make_fixtures.py` records how they were made. |
| `fixtures/base/` | The starting `plot.py` for each edit case. |
| `fixtures/reference/` | One correct solution per case. Only `--selftest` uses them. |
| `fixtures/controls/` | 7 deliberately broken figures. Each one must trip its detector. |
| `run.py` | Creates the projects, runs the hosts and gathers evidence. |
| `probe.py` | Re-runs `plot.py` and snapshots the figure. |
| `views.py` | Fixture access and snapshot views. |
| `oracle.py` | Data contracts and the runner. |
| `estimators.py` | Histogram, KDE and box contracts. |
| `spec_checks.py` | Request checks. |
| `metrics.py` | Layout defects and edit preservation. |
| `score.py` | Scores a run, or runs the selftest. |
| `summary.py` | Writes `summary.md`. |
| `compare.py` | Paired A/B statistics. |
| `sheet.py` | Contact sheets. |
| `test_scorer.py` | Mutation controls. |
| `test_regressions.py` | Round-2 review probes, pinned as regression controls. |

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

**Contamination.** After each run, every tool call and tool output (from the
Claude transcript, or the Codex stream and rollouts) is scanned for:

- the repo or records paths;
- `evals/agentic`, `fixtures/reference`, `manifest.json`, `run_meta.json`,
  `score.json`;
- another project under the work root;
- a `../` escape in a command.

A hit sets `contaminated=true`. A contaminated unit is never a task success, and
it counts as a failure in comparisons.

Plain filesystem access cannot hide `~/scratch` itself, which contains both
trees. Pass `--hide-grading` to run each host inside `bwrap`. It mounts empty
`tmpfs` over the repo, the records root and the work root, then re-binds only
the unit's project. This was checked with both hosts, including Codex's own
sandbox nested inside. It is off by default.

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
uv run pytest evals/agentic/test_scorer.py evals/agentic/test_regressions.py -q

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

# 4. Skill A/B. Same wheel; both arms in one run; seeded random order; repetitions.
uv run python evals/agentic/run.py --run-id skill-ab-$(date +%Y%m%d) --jobs 4 --reps 2 \
    --wheel PATH/TO/SAME.whl --ab-skill PATH/TO/skills/dartwork-mpl
uv run python evals/agentic/score.py ~/scratch/dartwork-mpl-evals/skill-ab-$(date +%Y%m%d)
uv run python evals/agentic/compare.py ~/scratch/dartwork-mpl-evals/skill-ab-$(date +%Y%m%d)
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
  invisible. Identity comes from a label, a legend handle (`label=` is not
  required), a panel title or ylabel, or an end label.
  - `series`: one-to-one; an extra artist labelled as a series fails;
    `panels: distinct` puts each series in its own axes.
  - `bars`: category → value, plus `layout: grouped` (side by side from 0) or
    `layout: stacked` (cumulative from 0).
  - `points`.
  - `fits`.
  - `dist`: per-group estimator contracts recomputed from the raw rows:
    - histogram counts in the drawn bins;
    - a Gaussian KDE, up to one scale factor, for a fitted bandwidth, within
      2% of the peak;
    - box median and Q1/Q3 at the labelled tick;
    - a violin body with the KDE shape and the data range.

    A form no contract recognises is *unchecked* (`ok: null`), never a pass.
  - `matrix`.
  - `stack`: per-layer thickness, with layers tiling [0, total] at every x.
  - `errorbars`.
  - `span`.

  Finally, every visible data artist must be claimed by a contract or match a
  declared `auxiliary` kind (`reference_lines`, `fit_lines`). Errorbar caps
  are always auxiliary.
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
  - line colour, width, style, marker, alpha, visibility and data digest
    (including the NaN mask);
  - bar and scatter colours, alpha and data;
  - legend location, texts, size and bbox.

  Placements (`.position`, `.pos`, `.bbox`) are compared with a 0.03 figure
  fraction tolerance. For `explicit` edits, a missing base snapshot, any
  changed non-target property, or any **added** non-target property fails. For
  `broad` edits, only the data contracts are hard checks.
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

Aesthetic preference is not a gate. Look at `sheet-<host>-<arm>.png`; edit
cases show the before and after figures side by side.
