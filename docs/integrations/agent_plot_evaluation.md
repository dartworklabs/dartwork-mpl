# Live agent plot evaluation

`scripts/run_agent_plot_eval.py` captures an opt-in, trusted local agent journey:
CSV request → durable rendered plot → style revision in the same session →
retrieval of both artifacts in a fresh session. It does not generate a plotting
solution for the agent. It changes no production MCP contracts or global host
settings. Fixed cases are `line`, `groupedbar`, `scatter`, and `custom2panel`.

Use the locked development environment with Python 3.12 and the optional MCP
extra already installed. No live host runs during pytest.

```sh
export UV_PYTHON=3.12
uv run --no-sync pytest tests/mcp/agent_loop/test_capture.py tests/mcp/agent_loop/test_oracle.py -q
```

Before spending any live budget, inspect the installed host's help/version and
select the current middle tier and supported effort from its live catalog. Save
`runtime/selection.json` beneath the evidence root, with `model`, `effort`,
`provider`, `checked_at`, and the selected `catalog_model` record. The runner has
no model alias or fallback. Authentication uses the host's existing normal
mechanism; the runner copies no credential files or secret environment values.

```sh
export AGENT_EVAL_ROOT="$HOME/scratch/dartwork-mpl-agent-loop-eval-2026-10-20"
uv run --no-sync python scripts/run_agent_plot_eval.py smoke --output-root "$AGENT_EVAL_ROOT"
uv run --no-sync python scripts/run_agent_plot_eval.py run --label baseline --cases all --output-root "$AGENT_EVAL_ROOT"
```

The scored command requires the explicit phase-0 admission record described
below. Each case/label runs once, and existing evidence is never overwritten. The approved comparison has
four baseline and four candidate cases. Candidate runs use `--label candidate`.
Do not run either corpus without its spending authorization.

The first actual smoke revealed that the host advertises built-in agents/plugins
even in restricted mode. The initial incomplete failure remains under
`smoke/line`. A specifically authorized harness repair uses `smoke-repair`, with
three USD 0.2 caps; it is not a general retry option. Together with the first
invoked USD 0.4 cap, smoke invocation caps would total USD 1.0 if all stages ran. Both actual smoke
records remain FAILED: the repaired revision omitted its final report review.
Only USD 0.8 of smoke stage caps was invoked; no further preflight is permitted.
Unknown agents/plugins, custom plugin paths
or sources, skills, additional directories, unexpected tools and other MCP
servers still fail capture.

The parent approved a narrow sequencing adjustment after this workflow failure.
`runtime/admission-decision.json` binds both unchanged FAILED smoke hashes to the
observed image/full-report receipt, actual resume, model/scope/cleanup and real
stdio recovery tests. Its policy is `phase0-observed-infrastructure-2026-10-20`;
its `fresh_agent_recovery` must explicitly remain `unverified`. Baseline execution
is pending independent code review. The first scored episode measures live fresh
recovery; a reconstructed store or deterministic collector cannot prove it.

Each episode records `infrastructure_status`, `workflow_status` and
`agent_recovery_status`. Capture/config/model/fixture/oracle/tool/bounds/cleanup
failures stop the episode. A missing image or final report review remains a
scored workflow failure, while intact selected artifacts and matching render
arguments allow the already scheduled revision/recovery to continue. Any
workflow failure keeps final `status: failed`, even when fresh recovery succeeds.
No report-receipt requirement is weakened and no stage is silently retried.

Every stage passes inspected host flags as argv: restricted mode, empty setting
sources, strict per-run MCP configuration, only Read/resource readers and the
dartwork-mpl tools, and noninteractive permission denial. The MCP server is the
current venv's absolute executable. It inherits the episode cwd and an explicit,
private artifact store. The model's initial cwd contains the original CSV plus
the actual returned `create_plot` prompt and agent entry. The sample is only a
preview; the complete CSV path is also provided. Evaluator expectations, their
paths and the evaluator implementation are excluded from model inputs.

Evidence lives at `<root>/<label>/<case>/`:

- `input.csv`, `context.json`, `events.jsonl`, `stderr.txt`, `run.json`.
- `original/` and `revision/`: request, argv, raw stream, exact PNG/PDF/source/
  report/manifest, render arguments, and independent collection evidence.
- `recovery/`: the genuinely fresh agent transcript and a separate SDK collector
  reading all five members for both IDs through a new stdio server.
- `replay/`: bounded process replay observations, PNG, source/CSV/output digests
  and the independent data-space oracle result.

The fresh recovery agent receives both IDs and the retrieval request only. It
starts with a new UUID and empty cwd, using the same store. Rendering during
recovery fails admission. The deterministic collector's byte equality proves
stored member recovery; agent image/report receipt is assessed separately from
actual correlated tool results. A template image or failed report read cannot
serve as evidence that the generated artifact was reviewed.

Configured model/effort, actual returned model, sessions, reported usage/cost,
host/server/package/font provenance, fixture/output hashes, process durations and
stop reasons are preserved. Missing effective effort or usage/cost stays null.
Dollar flags and reported costs do not establish account-wide enforcement.

The configured bounds are USD 2/2/1 for scored stages, USD 41 across invoked
stage caps, 125 minutes for the complete corpus, 15 minutes per scored episode,
5 minutes per host process, 24 observed MCP/resource calls per episode, 512 KiB
source, 32 MiB per bundle, 128 MiB evidence and 20 seconds for render/replay.
Remaining corpus/episode time bounds host stages, collectors and replay. The
external watchdog retains partial streams and terminates observed owned
descendants, including separate process groups. No hard token/turn cap is
claimed. Call limits are observed in the stream, rather than an MCP proxy that
authorizes each request before it reaches the server.

Replay keeps the original owned workspace until it finishes, so source using
an absolute CSV path needs no rewrite. A fresh Python process executes the exact
stored bytes with the recorded `figure_var`, checks the CSV digest before/after,
and reads native artists for `assess`. Unsupported external IO, network, time or
unfixed random inputs are marked unchecked. This process replay is separate
evidence; it cannot establish original execution internals, arbitrary Python
isolation or complete reproducibility. Private workspaces/stores are removed in
finally; retained evidence belongs in the research checkout or scratch, never
`datasets`.

Replay can also be invoked explicitly for an available original CSV/workspace:

```sh
uv run --no-sync python scripts/evaluate_agent_plot.py replay /absolute/source.py /absolute/replay-output fig --csv /absolute/input.csv --case line
```
