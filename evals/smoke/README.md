# Agent plotting smoke

This is a small failure-harvesting exercise: twenty-seven realistic requests, one
attempt per selected host. Inspect the PNGs and transcripts and file defects. Execution
success only means the host exited successfully, produced PNG/PDF, and its final
script could be re-run and validated. It says nothing about visual correctness.

There are no oracles, reference solutions, grading, verdicts, statistical claims,
repetitions, or pooling with `evals/agentic`. Those frozen evaluation files are
neither imported nor changed. Review these cases before running a full round.

## Run

On macOS, with `uv`, logged-in Codex and subscription-authenticated Claude Code:

```sh
uv run python evals/smoke/run_smoke.py
uv run python evals/smoke/run_smoke.py --cases g01-single-column --hosts claude codex --jobs 2 --timeout 600 --run-id my-check
```

`--cases` and `--hosts` accept space-separated or comma-separated names.
Defaults: all twenty-seven cases, both hosts, two parallel units, 600 seconds per host.
An existing run id is refused. No API keys are passed to either host. Models
use the host defaults (Codex's configured model selection is retained).

The wheel is built once from the current checkout. Each unit gets a fresh venv,
the wheel, pandas, the wheel's installed skill, and only its own CSV/base script.
The raw user request and appended project logistics are recorded separately.
Edit originals and rendered bases are kept. No host sees the runner or results.

Three kinds of case: `generate` (a new figure from a CSV), `edit` (one asked
change to a clean `plot.py`) and `repair` (a `plot.py` that runs but carries a
defect the validator reports; the request only says to validate and fix it).
For `edit` and `repair` the base is also validated before the host starts
(`base-validator.json`, `base_warnings` in `run.json`); that replay is removed
before the host runs, so the host has to find the defect itself. Read a repair
as base WARNING ids → final WARNING ids, then count in the transcript how many
render-and-validate passes it took and whether the fix is the one the finding
asked for.

macOS Seatbelt blocks reads of all worktrees of this repo, the result root,
other temporary units, and global instructions/skills/session histories.
Writes are confined to the temporary project. A read-denial probe runs before
every model call. Other operating systems fail closed, without model calls.
The host retains access to OS resources, its CLI and subscription credentials;
this is not a general-purpose security sandbox for adversarial workloads.
Codex uses a fresh private auth home and ignores global settings and rules.
Claude uses project settings only, excludes global instructions and disables MCP.

## Results and review

Results: `~/scratch/dartwork-mpl-smoke/<run-id>/<case>/<host>/`.
Temporary projects: `~/scratch/dartwork-mpl-smoke-work/`, removed after each unit.
No model artifacts are written to the repository or `/tmp`.

Start at `SUMMARY.md`. Each unit has the request, prompt, raw JSONL and stderr,
scripts, PNG/PDF artifacts, usage, turns, elapsed host wall time and validator
findings in `run.json`/`validator.json`. A replay runs in a separate directory;
its captured save-time figures are validated without overwriting the originals.
Re-rendered outputs are kept separately in `replay-artifacts/`.
Failure to capture a figure is recorded as "could not re-run", not a clean check.
Tokens keep the host's native schema (including cache fields); missing usage is
`null`. Image-tool evidence is conservative: absent timestamps mean unknown,
never proof of visual inspection. Read the rollout/transcript to resolve it.

To file a defect, inspect the final PNG at intended physical size, compare the
request and (for edits) original script/image, then read the transcript. Include
the case id, host/version, wheel digest/commit from `manifest.json`, offending
script, PNG, validator ids and a short reproduction. Redact private transcript
content before attaching it. Separate runner failures from library/skill defects.
Do not interpret counts across hosts or rounds as a performance estimate.

Inputs are synthetic and deterministic. `make_cases.py` regenerates the committed
CSV, metadata, five runnable edit bases and four defective repair bases; it
contains no reference solutions and no repaired versions.

Model-free checks: `uv run pytest evals/smoke/test_smoke.py` (explicit opt-in).
Default pytest testpaths remain `tests` and `src/dartwork_mpl`; they exclude evals.
