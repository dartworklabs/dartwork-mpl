# Explicit native data policy implementation

Goal: implement approved option A of [the specification](../specs/2026-11-04-explicit-data-policy-proposal.md).
Approval: user “진행해”, 2026-11-04; approved proposal digest recorded in the spec.
Base: `546c7418` (main fetched and fast-forwarded). Other sessions retain ownership
of visual/agent-workflow work; coordinate #501 scope through its issue and thread.

## 현재 권위와 상태

- role purpose/architecture; path `AGENTS.md`: native matplotlib, color/style and MCP freezes.
- role workflow; path `docs/development/structure-refactor/agent-followup-handoff.md`:
  original repairs shipped; this session's approval authorizes only option A.
- role native contract; path `src/dartwork_mpl/validate/_data.py`: legacy cleaner remains live.
- role verification; path `src/dartwork_mpl/validate/tests/test_data_ownership.py`:
  aliases, legacy calls, warning positions, storage and old dtype/shape outcomes.
- role MCP contract; paths `src/dartwork_mpl/mcp/plot_data/` and
  `tests/contracts/test_mcp_data_repair_contract.py`: separate shape/report semantics.

## 지켜야 할 현재 불변식

Omitted policy preserves behavior, positional parameters and tuple returns.
Inputs are never mutated; equal original lengths align, unequal lengths remain independent.
No MCP definitions, wire/report behavior, colors, fonts, styles or service choices change.
Only the approved keyword/signature and diagnostic-type additions change public API.

## 설계 이유와 제약

- role workflow / handoff and #501: explicit choices prevent silent loss; legacy compatibility costs a separate path.
- role verification / ownership tests: object and N-D behavior stays pinned on the old path.
- role purpose / AGENTS: executable evidence and bounded reviews; every design document stays <=200 lines.

## 충돌·미확인

No Handbook exists. Object/N-D/complex policies remain outside scope.
Wheel and MCP-native execution acceptance are not yet run.
Never read/search/hash/copy the prohibited 2026-10-20 design or copies.
No broad local docs tests, full docs scans, or test-id tools that copy prohibited files.
Existing remote CI remains unchanged; local verification uses inspected safe paths.

## Task 1 — native implementation and focused contracts

Files: `validate/_data.py`, `validate/__init__.py`, root `__init__.py`,
`validate/tests/test_data_policy.py`, existing `test_data_ownership.py`.
- [ ] Step 1: add observable policy examples and generated invariants; run before implementation.
  Expected: assertions exercising the new contract fail; preserve raw red evidence.
- [ ] Step 2: implement explicit policy parsing, masks, immutable diagnostics and safe text.
  Keep the legacy function body/caller warning stack intact after the opt-in branch.
- [ ] Step 3: update only the approved signature expectation; retain all other ownership assertions.
  Run focused policy/ownership/helpers tests, Ruff and mypy. Expected: pass, no weakened checks.
Commit point: native implementation plus behavioral regression tests after green.

## Task 2 — installed Python and MCP acceptance

Files: focused tests in `tests/contracts/test_data_policy_runtime.py`, reusable
synthetic probe in `tests/support/data_policy_probe.py` if useful.
- [ ] Step 1: build a wheel, install it non-editably outside the checkout, run finite,
  strict, preserve, clean and omitted-policy probes. Expected: installed path,
  tuple/data/diagnostic assertions and original inputs all correct.
- [ ] Step 2: exercise those calls through existing MCP render execution using a
  fixed sentinel after assertions; verify the actual envelope and untouched discovery.
  Use real in-process client and one bounded installed-server stdio path.
- [ ] Step 3: run existing MCP data-repair contracts and color freeze/boundary tests.
  Expected: no new protocol, no altered existing result and no digest regeneration.
Commit point: executable acceptance tests with real wheel/MCP evidence.

## Task 3 — consumer guidance, integration and review

Files: bundled skill reference routed to data usage, `CHANGELOG.md`, this plan.
- [ ] Step 1: document opt-in numeric scope, allow_nan conflict, diagnostics and
  unchanged default; retain MCP shape-vs-native distinction. Execute any new code examples.
- [ ] Step 2: inspect changed doc rendering before merge where visible output changes.
- [ ] Step 3: independent review against the approved contract and executable checks;
  fix bounded findings, then recheck only affected tests. Save evidence outside /tmp.
- [ ] Step 4: fetch main again, reconcile concurrent changes, run affected checks,
  create PR and require its latest checks. Merge per repository policy when green.
  Do not close all of #501: other dtype policies and task 8 decisions remain.
Commit point: guidance and verified completion record; PR links all work.
