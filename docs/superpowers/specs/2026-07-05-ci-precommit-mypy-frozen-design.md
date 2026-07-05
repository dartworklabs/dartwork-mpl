# CI Hygiene — stop the required pre-commit check flaking on the mypy hook (P2)

> Program umbrella #411, pillar EO2.

## Problem

`.pre-commit-config.yaml` runs mypy via a local hook: `entry: uv run mypy src/dartwork_mpl/`.
`uv run` (without `--frozen`) may **re-resolve and rewrite `uv.lock`** as a side effect. When it
does, pre-commit sees a tracked file change and reports **"files were modified by this hook" →
Failed** (stash-rollback), even though mypy itself printed "Success: no issues found". Because
`.github/workflows/pre-commit.yml` is a **required** status check (branch protection), this
spurious failure blocks merges — PRs #409 and #410 were admin-merged past exactly this flake,
and every worktree commit this program produces has to `SKIP=mypy`.

The intent of the local hook is correct — run mypy against the *project's uv-managed env* so it
sees the same matplotlib/numpy/fastmcp/fastapi/pydantic versions CI uses (an isolated
`mirrors-mypy` would silently diverge in strict mode). We keep that; we only stop the lock churn.

## Fix

1. **`.pre-commit-config.yaml`** — change the hook entry to `uv run --frozen mypy src/dartwork_mpl/`.
   `--frozen` installs deps into the venv from the *existing* lockfile but never updates
   `uv.lock`, so the hook can no longer modify a tracked file. mypy's type-check environment is
   unchanged (same locked deps), so results are identical to today. Update the comment to record
   why `--frozen` is load-bearing.
2. **`.github/workflows/pre-commit.yml`** — add a `uv sync --frozen --all-extras --dev` step after
   `setup-uv` and before `pre-commit/action`, so the hook's `uv run --frozen mypy` runs against a
   pre-populated env (fast, deterministic) and never needs to reach for the network mid-hook.

## Why this also unblocks the whole program

`pre-commit.yml` checks out the PR branch and uses *that branch's* config, so P2's own PR runs
with the fixed `--frozen` hook and passes. Once merged, every subsequent pillar PR's required
pre-commit check is healthy — no more admin-bypass, no more `SKIP=mypy`.

## Acceptance

- The mypy hook uses `--frozen`; the comment explains it.
- `pre-commit.yml` pre-syncs the env with `--frozen`.
- No other files touched. (Orchestrator confirms `uv run --frozen mypy src/dartwork_mpl/` is
  clean and leaves `uv.lock` unmodified.)

## Non-goals

- Not converting to `mirrors-mypy` (deliberately rejected — see the existing config comment).
- Not making the check non-required (governance; fixing the root cause is within our power).
