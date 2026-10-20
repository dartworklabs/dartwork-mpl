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

## Repeat retained evaluations without model calls

The retained phase-0 evidence is at
`~/scratch/dartwork-mpl-agent-loop-eval-2026-10-20`. These commands only read saved
members, replay observations and review sidecars; they do not execute source or
invoke a model. Keep the evidence tree intact, including `runtime/` and the frozen
baseline record.

```sh
export UV_PYTHON=3.12
export AGENT_EVAL_ROOT="$HOME/scratch/dartwork-mpl-agent-loop-eval-2026-10-20"
uv run --no-sync python scripts/evaluate_agent_plot.py evaluate --run "$AGENT_EVAL_ROOT/candidate/line"
uv run --no-sync python scripts/evaluate_agent_plot.py compare --baseline "$AGENT_EVAL_ROOT/baseline" --candidate "$AGENT_EVAL_ROOT/candidate"
```

`evaluate --run DIR` prints one episode's JSON and exits 0 only when all six
independent dimensions pass: `delivery`, `declared_validation`, `model_review`,
`semantic_replay`, `visual_review`, and `human_code_edits`. Failure or unchecked
returns 1. The same command works for each of the four case directories.
`compare` prints both labels and `candidate_gate`; its overall exit also requires
the baseline to pass. This frozen comparison intentionally exits 1 while
`candidate_gate` is true. An incomplete baseline must remain visible.

## Authorized phase-0 live procedure (historical)

Live capture is manual opt-in in one representative Python 3.12 environment,
with a separately approved corpus, model selection, admission and spending cap.
It is outside pytest and PR jobs. The current corpus is consumed and immutable;
the following records what was executed, rather than a fresh-run bootstrap.
Do not rerun these commands against it or reset its ledger.

Before those calls, the operator inspected the installed host's help/version and
live model catalog, saving `runtime/selection.json` with `model`, `effort`,
`provider`, `checked_at`, and `catalog_model`. There is no alias or fallback.
Authentication used the host's normal existing mechanism; no credential files or
secret environment values were copied. The commands were the runner's `smoke`,
then authorized `smoke-repair`, then `run --label baseline --cases all` and
`run --label candidate --cases all`, each with `--output-root "$AGENT_EVAL_ROOT"`.
Each scored label/case ran once. A new evaluation requires its own bounded
execution/admission decision; the present runner does not offer generic successful
smoke admission or a corpus retry procedure.

The first smoke received an actual image/full report but failed because the host
advertised built-in agents/plugins in restricted mode. An exact built-in metadata
allowlist repaired that capture rejection. Unknown/custom context stays rejected.
The specifically authorized repair used three USD 0.2 stage caps from the
original uninvoked allocation. It failed the model workflow: the final revised
artifact's full report was not read. Both records remain FAILED under `smoke/line`
and `smoke-repair/line`; no further preflight occurred.

Both the CLI and exported `run_episode` require
`runtime/admission-decision.json` before context collection or host work. Its
`phase0-observed-infrastructure-2026-10-20` policy binds those two unchanged
failed smoke hashes and independent code-review approval to observed model,
image/full-report receipt, resume, scope, cleanup and real stdio tests.
`fresh_agent_recovery` remains `unverified` in that historical admission; the
scored episodes subsequently measured actual new-agent recovery. This was an
explicit infrastructure admission, never a passing model-workflow result.

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
Remaining corpus/episode time bounds host stages, collectors and replay. Replay
counts shared episode evidence plus files in the owned cwd during execution.
Its pipes retain only the remaining capacity; controlled observation/PNG/result
writes check capacity before persistence, reserving metadata space. A replay
byte/time/cleanup failure stops before any next host stage or budget reservation.
Source-created files are observed at poll boundaries, rather than controlled by
an OS filesystem quota. The external watchdog retains partial streams and terminates observed owned
descendants, including separate process groups. No hard token/turn cap is
claimed. Call limits are observed in the stream, rather than an MCP proxy that
authorizes each request before it reaches the server.

Replay keeps the original owned workspace until it finishes, so source using
an absolute CSV path needs no rewrite. A fresh Python process executes the exact
stored bytes with the recorded `figure_var`, checks the CSV digest before/after,
and reads native artists for `assess`. Replay uses the production export call,
`dm.save_formats(..., formats=("png", "pdf"), validate=False,
adopt_orphan_tick_font=False)`, staging both formats in the monitored owned cwd
and retaining PNG through the byte guard. This happens before cwd cleanup;
later comparison consumes the recorded replay. Unsupported external IO, network, time or
unfixed random inputs are marked unchecked. This process replay is separate
evidence; it cannot establish original execution internals, arbitrary Python
isolation or complete reproducibility. Private workspaces/stores are removed in
finally; retained evidence belongs in the research checkout or scratch, never
`datasets`.

## Results and limits of this comparison

All four candidate `evaluate` calls exit 0. Their selected original/revision
bundles pass the independent data/row/mask/group/panel oracle, strict saved replay
pixels, both retrieval paths, review receipts, cleanup and explicit zero human
plotting-code edits. Four frozen baseline run hashes still match.

| Case | Preserved baseline result | Candidate result |
| --- | --- | --- |
| line | Final revision full-report receipt missing; other dimensions pass | Six dimensions pass |
| groupedbar | Final report receipt missing; native NumPy scalar JSON serialization broke both saved replays, leaving semantics/pixels unchecked | Six dimensions pass |
| scatter | No artifact: a production-valid 60-second request hit an undisclosed evaluator-only 20-second cap | Six dimensions pass, including the final sentinel row |
| custom2panel | Six dimensions pass; global chart-hint warning retained | Six dimensions pass; same warning retained |

The evaluator's four-field numeric normalization was fixed after the baseline
(`e71e0b46`) and before candidate capture (`810b4541`). Baseline grouped-bar
replays were never reconstructed or rerendered after cleanup. The scatter cap
was absent from model input and within the production API's allowed timeout;
its failure is not a demonstrated model/user-contract violation. These confounds
and four single episodes do not establish general model performance or prompt
causality. Baseline collection completion and candidate quality are separate.

Both custom2panel full reports expose `line_no_lines` for the scatter panel
because one global line hint covers both axes. Their complete status and empty
`failed_checks` do not erase this warning or prove data accuracy. Host previews
can resize larger images; actual decoded, artifact-correlated image receipt is
recorded separately from independent evaluator visual review. Five-member
recovery remains byte-exact, and replay versus stored PNG compares decoded
pixels strictly. The evaluator independently read all 14 retained original/
revision PNGs; baseline scatter has explicit missing tiles. No human wrote or
repaired the model's plotting Python.

Two failed smokes plus eight scored attempts invoked USD 37.8 of the USD 41
stage-cap budget, within the original 7,500-second corpus clock. Known reported
costs sum to USD 3.1587164; this is not the billing total because baseline scatter
cost is unknown. Configured effort is recorded; effective effort remains null.

Execution receipts, frozen hashes, independent visual/zero-edit attestations,
and the actual equal-scale image PoC are retained in
`~/scratch/dartwork-mpl-agent-loop-execution-2026-10-20/task-4-evidence/`
(`comparison.json`, `command-receipts.json`, `evaluator-versions.json`,
`independent-visual-and-human-review.json`, `visual-review.html`). The PoC was
previewed at desktop/mobile widths before any merge or deployment. Source and
member evidence survives owned cwd/store cleanup; replaying source that needs a
removed absolute CSV path is not supported by this read-only comparison.

## Cheap CI and follow-up scope

The existing `tests/` collection runs the oracle and real stdio capture tests.
The Python 3.12 coverage job's existing
`scripts/check_integration_junit.py REPORT.xml` requires a passing executed case
from each protected module, including `tests.mcp.agent_loop.test_oracle` and
`tests.mcp.agent_loop.test_capture`. Missing or only skipped/failed/error cases
fail that guard; pytest itself still rejects any failed case. No model job,
additional matrix, dependency or repeated suite is added.

This guide connects #483's agent loop. Updating #482's roadmap criteria remains
a proposal; #499 viewer repair and #470 measured CI are independent tracks.
Other P0 work stays on the backlog. Immutable run/revision and retained-input
permission/lifetime/deletion, wire/discovery changes, hosted execution, website/
login/community and separate docs require their own approved scope. Phase 0
keeps native Figure/Axes, the five-member v1 bundle's seven-day retention,
18/10/9/2 discovery and trusted local execution contracts.
