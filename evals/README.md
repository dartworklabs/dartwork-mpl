# Agent evals

The repository's one criterion: a user turns on the skill, says "draw this",
and a beautiful chart comes out. This folder measures it by
putting a real agent (`claude -p`) in exactly that situation.

```bash
uv run python -m evals run                       # every case, arms bare,skill
uv run python -m evals run --cases grouped_bar --arms skill --model claude-sonnet-5-5 --jobs 3
uv run python -m evals report evals/runs/<stamp> # rebuild index.html + summary.json
uv run python -m evals rejudge evals/runs/<stamp> # judge recorded runs again, no claude call
```

Everything a run writes goes to `evals/runs/<stamp>/` (git-ignored): per case
and arm the transcript (`stream.jsonl`), the final `figure.png`, `source.py`,
the agent's project files and `result.json`;
`summary.json` and the contact sheet `index.html` at the top. Open
`index.html`: beauty is decided by looking at it.

## Arms

| arm | skill | built-in tools |
|---|---|---|
| `skill` | yes | Bash, Read, Write, Edit, Skill |
| `bare` | no | Bash, Read, Write, Edit (control: plain matplotlib) |

## Isolation

Each run gets a fresh temp project (the case's data files, plus the skill
installed by `python -m dartwork_mpl.guide install`, which links
`.claude/skills/dartwork-mpl`), an empty `CLAUDE_CONFIG_DIR`, a scrubbed
environment, `--setting-sources project`, `--strict-mcp-config`,
`CLAUDE_CODE_DISABLE_BUNDLED_SKILLS=1`, the two remaining built-in skills set
to `off` and the built-in plugins disabled. The run's init event must list
exactly the arm's tools and our skill (or none), and no MCP servers or
plugins; anything else makes the run `INVALID`.

`--bare` is not used: it removes the Skill tool, so the model never sees a
project skill (only a user typing `/dartwork-mpl` reaches it), which is not
the user's situation. `--bare` also accepts only `ANTHROPIC_API_KEY` or an
`apiKeyHelper`. Auth: `ANTHROPIC_API_KEY` if set, else (macOS) an
`apiKeyHelper` that reads the logged-in Claude Code OAuth token from the
keychain at call time; the token is never written to disk.

Agents run with `--permission-mode bypassPermissions`: their code runs as you.

## Verdicts (mechanical, they only filter)

- `OK`: a figure exists, re-running the final source draws it, `dm.check`
  has no WARNING (and no rule NOT RUN), lint has no critical finding (not
  applied to `bare`, which is not expected to follow dartwork-mpl), and every
  fact in the case's `[expect]` holds (panels, marks, texts, legend).
- `DEFECT`: a figure exists, but one of the above fails; the reasons are listed.
- `NO_FIGURE`: the agent left no image.
- `INVALID`: isolation broken, `claude` failed or timed out, or the harness crashed.
- `NOTRUN`: the run did not execute. Never counted as passed.

## Cases

One TOML file per case in `cases/`: `prompt`, `[files]` (tiny inline data)
and `[expect]`. Add a case by adding a file.

## Cost

A run costs about $0.03 (Sonnet 5.5: 33 runs at `--jobs 3` took about 3
minutes and reported $1.08 on 2026-11-15); it spends real Claude usage (the
summary prints the cost the stream reports). Run single cases while
iterating, and `rejudge` after changing the judge instead of re-running.

`evals/tests/` (pure parts, no `claude`) run with the default `uv run pytest`.
`evals/` is ruff-checked but not in basedpyright's strict paths (like tests).
