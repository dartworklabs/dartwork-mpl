# Final agentic A/B implementation and execution plan

> **For agentic workers:** Use `superpowers:executing-plans` to implement these tasks inline. The user authorized implementation and completion; no additional approval gate is introduced here. The root session owns review, integration and live execution.

**Goal:** Freeze a reproducible final-wheel comparison without pooling the supplemental cases or relabeling previously observed cases as independent holdouts.

**Architecture:** A standalone stdlib helper reads case filenames, explicit runtime configuration and the existing preregistered endpoint text. It creates an immutable prelaunch record and emits existing-runner argv only after rechecking frozen inputs. It never launches hosts, changes old records or reads case YAML/reference solutions.

**Tech stack:** Python >=3.10, pytest, existing `run.py` and `compare.py`.

**Spec and approval:** The user's 2026-11-04 instruction to finish all remaining work and the root's scoped delegation in this session. The user reconciled completion to the existing preregistration on 2026-11-04; current rules are in `../specs/2026-10-22-agentic-workflow-masterplan.md:81-89,182-189`. Endpoint text remains in `2026-10-22-agent-eval.md:50-74` and `compare.PREREGISTERED`.

## Global constraints

- Native Figure/Axes, visual style, shipped colours and MCP contracts stay unchanged.
- Do not open held-out YAML, reference solutions, the forbidden 2026-10-20 contract-repairs spec or its copies.
- Do not change `run.py`, `compare.py` or existing reports in this helper task.
- No model calls, payment/API fallback, commit or push by this worker.
- Models/efforts, host versions, final wheel/path/SHA, trusted harness commit, authenticated Codex home and budgets must be explicit configuration inputs; never invent missing values.
- Hosts use verified subscriptions, grading isolation, valid disabled GitHub MCP and Codex subagents off. Start at jobs=2; supported ceiling=7.
- Two fresh repetitions per host/arm; seeded order; no retries, replacements or optional stopping. Never dry-run an official run ID.
- Keep the prelaunch record under the sandbox-hidden records root, outside both official run-ID directories; verification and command emission enforce the same location.

## Current authority and status

- **Current authority:** Existing `run.py` CLI, `compare.PREREGISTERED`, user-authorized primary/supplemental split and exposure declaration below.
- **Current invariants:** Same final wheel and runtime/budgets for both arms; existing endpoint thresholds unchanged; missing units/usage block a decision.
- **Design reason:** Earlier tuning/pilots do not prove final-main acceptance; 50 default cases would silently expand the original 40-case primary experiment.
- **Unresolved:** Peer session owns `dm.review`/baseline API integration. Root pins the final API wheel and trusted harness after that work. Existing default “held_out” report labels need a provenance-aware integration after the current fix PR lands.

## Population and provenance

- **Primary:** original g01–g25 and e01–e15; 40 ×2 hosts ×2 arms ×2 reps =320 units.
- **Supplemental:** c01–c07 and e16–e18; 10 ×2×2×2 =80 units, descriptive only. Never pool into the primary decision.
- YAML's historical held-out declaration: g03/g07/g11/g15/g20/g24 and e04/e08/e10/e14.
- Tuning-exposed among those: e04/e08/e10/e14/g20.
- g03/g07/g11/g15/g24 were not used in v13–v24 tuning, but their original baseline was observed. Their five-case subset is descriptive, not a new primary endpoint or an independent holdout estimate.
- Freeze declaration and exposure in separate per-case fields; leave YAML and historical scores untouched. Other tuning exposure is not asserted by this helper.

## Review focus

1. Renamed, missing, duplicate-prefix or added case files must fail before output; filenames only are needed.
2. Missing/changed wheel, configuration, endpoint text, harness or runtime evidence must prevent command emission.
3. A reused official ID or overwritten freeze record must fail; primary completion must not prevent emitting the fresh supplemental command.
4. Missing configuration or disabled isolation/subscription controls must fail closed; no implicit model/budget/auth defaults.
5. Seeded unit order must match `run.py`'s case/host/arm/rep loop; supplemental and provenance labels must not change primary membership.

## Task 1 — helper and mechanical controls

**Files:** Create `evals/agentic/preregister.py` and `evals/agentic/test_preregister.py`; this plan is the only documentation file in scope.

**Interfaces:**

- `inventory(cases_dir)` inventories validated exact IDs from filenames only.
- `freeze(config_path, output_path, repo)` exclusively writes a checksummed prelaunch record; existing output or official run directories are refused.
- `verify(record_path, repo)` rechecks exact config bytes, wheel SHA, clean trusted harness, runtime evidence/versions, roster, endpoint text and provenance without executing hosts.
- `command(record_path, cohort, repo)` verifies inputs and requires the selected run ID to be unused before returning argv. The CLI prints JSON argv or shell-quoted argv with `</dev/null`; it does not launch.

- [x] Step 1: Write tests pinning 320/80 units, exact roster/exposure labels, seeded order and missing/duplicate IDs. Run them and observe failure before implementing the helper.
- [x] Step 2: Implement filename-only inventory, fixed cohort/provenance rules and strict explicit-config parsing. Do not import grading modules or load cases.
- [x] Step 3: Write freeze/verify tests for normal config, missing input, wheel/config/endpoint/provenance mutation, dirty/moved harness, unsafe controls, reused official IDs and immutable output. Observe failures before the corresponding implementation.
- [x] Step 4: Implement exclusive immutable freeze, byte hashes, trusted-commit/clean-tree checks, runtime-version checks and verified command emission.
- [x] Step 5: Run `.venv/bin/python -m pytest evals/agentic/test_preregister.py -q`, Ruff format/check, targeted mypy and `git diff --check`. Use real temporary files and tiny git fixtures; no models. Record red/green evidence under the session's persistent scratch.
- [ ] Step 6: Root reviews and integrates this logical unit after the current fix PR. Worker creates no commit/PR.

**Expected:** Normal explicit configuration yields disjoint primary320/supplemental80 planned units and two exact runner commands. Every changed/missing frozen input blocks command output. No case YAML/reference content is read.

## Task 2 — root-owned final run and reporting

- [ ] Step 1: Integrate peer-owned review/baseline API and pin the final wheel SHA and trusted clean harness head; preserve a receipt for current model catalog, host versions and subscription auth without credentials.
- [ ] Step 2: Write explicit configuration with wheel `{path,sha256}`, harness commit, runner/project Python, model/effort/host-version per host, Codex home, runtime evidence `{path,sha256}`, budgets, records/work roots, two distinct run IDs, two seeds and jobs=2. Freeze once under the hidden records root, outside the repository and both official run directories.
- [ ] Step 3: Review the frozen argv, all400 unit IDs, endpoint text, cohort membership and provenance. Hash/retain the prelaunch record. Do not allocate dry units under either official ID.
- [ ] Step 4: Reverify and emit the primary command immediately before execution; pass stdin=DEVNULL. Run the complete primary320 once. Retain failed/missing units; no substitutions.
- [ ] Step 5: Reverify and emit the fresh supplemental command; run its80 units under the same frozen wheel/runtime. Do not extend the primary run.
- [ ] Step 6: Score both runs with the frozen harness. Apply the current user-reconciled masterplan/PREREGISTERED primary decision. Historical task-success improvement is descriptive only; raw value/explicit-edit preservation failures remain failed task_success with their evidence. Failed/inconclusive results stay failed/inconclusive.
- [ ] Step 7: Report the supplemental80 and five not-used-in-v13–v24 cases descriptively, with baseline observation/exposure visible. Propose/implement the smallest provenance-aware summary integration after the fix PR; do not silently trust historical booleans.
- [ ] Step 8: Verify source→frozen manifest→all400 actual unit records→scores→rendered report. Root owns review, merge and final publication/delivery if authorized.

**Budget:** Initial final-main pilot measured1.87M tokens/16 units: rough37.4M for320 or46.8M for400 before new API/model effects. The existing cost-projection file is evidence, not a spending authorization. Recheck subscription quota and capacity; existing host ceilings remain explicit in config. At jobs2, estimate elapsed time from measured host distributions, not the old October2.5h estimate.

**Completion boundary:** Helper tests prove preregistration mechanics only. The final A/B and current user-reconciled masterplan acceptance remain incomplete until the final API wheel has run and the actual results satisfy PREREGISTERED without reinterpreting failures. Historical task-success +10pp is not an additional gate.
