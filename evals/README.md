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
and arm the transcript (`stream.jsonl`), the final `figure.png`, the
`source.py` that drew it, the agent's files (`project/`, `tmp/` for what
it put in its temp dir, `root/` for what it wrote beside the project, such
as `../scripts/plot.py`) and `result.json`; `run.json`, `summary.json` and the
contact sheet `index.html` at the top. Open `index.html`: beauty is decided
by looking at it.

`run.json`, `summary.json` and every `result.json` carry `provenance`: the
library version, git commit and whether the tree was dirty, the sha256 of
the wheel the agents had installed, the skill's version and sha256, the
Claude Code, Python and drawing-library versions, and whether the runs were
confined. Together with the prompt, the data, `source.py` and the model
that is what a one-shot result needs to be handed to the hub
([hub-contract.md](../docs/hub-contract.md)).

A run directory can be copied, archived or moved to another machine and
judged again there (`rejudge`) with the same result. Which image was the
agent's last and which scripts it wrote last are read from the file times
once, when the run ends, and kept in `result.json` (`figure_file`,
`source_file`, `scripts`) with the case's `[expect]`; `rejudge` reads them
there, not from the file times, which a plain `cp -R` resets. A run recorded
before that is read by content (its `figure.png`, and the script equal to
its `source.py`). What `rejudge` cannot carry across is the library: the
re-render draws with this checkout, so a figure drawn by another commit
does not reproduce, and the reason then names both commits. Check out the
recorded commit to judge such a run again.

## Arms

| arm | skill | built-in tools |
|---|---|---|
| `skill` | yes | Bash, Read, Write, Edit, Skill |
| `bare` | no | Bash, Read, Write, Edit (control: plain matplotlib) |

## Isolation

Each run gets a root of its own with four places in it:

- `project/`, the working directory: a uv project (`pyproject.toml`,
  `uv.lock`, `.venv`) with this checkout's wheel installed and synced, the
  case's data files, and the skill put in by `dartwork-mpl install` from
  that `.venv`. `uv run python plot.py`, `python plot.py` and
  `uv run dartwork-mpl path` work in place, against the installed copy, as
  for a user after `uv add dartwork-mpl`. matplotlib, numpy, pandas and
  pillow are pinned to this checkout's versions, because the re-render
  below runs here.
- `home/` as `HOME`: empty, so `~` shows nothing of yours.
- `tmp/` as `TMPDIR` and Claude Code's temp dir.
- `cfg/` as `CLAUDE_CONFIG_DIR`: no user settings, plugins, skills, hooks,
  memory or CLAUDE.md.

The session runs with a scrubbed environment, `--setting-sources project`,
`--strict-mcp-config`, `CLAUDE_CODE_DISABLE_BUNDLED_SKILLS=1`, the two
remaining built-in skills set to `off` and the built-in plugins disabled.
The run's init event must list exactly the arm's tools and our skill (or
none), and no MCP servers or plugins; anything else makes the run `INVALID`.

**Confinement.** Agents treat the plot script as scratch and write it to
`/tmp/s/plot.py` whatever `TMPDIR` says; concurrent runs then overwrite each
other (#822). On macOS the session therefore runs under `sandbox-exec`: it
can write only under its root (and uv's cache) and cannot read the shared
`/tmp`, so `mkdir /tmp/s` fails in front of the agent and it carries on in a
place of its own. The prompt is not touched. On other systems nothing
enforces this (`provenance.confinement` is `none`): the transcript is
checked instead, and a run that worked outside its root is `INVALID`. Reads
elsewhere are not blocked: an agent that names your real home by its
absolute path can read it.

`--bare` is not used: it removes the Skill tool, so the model never sees a
project skill (only a user typing `/dartwork-mpl` reaches it), which is not
the user's situation. `--bare` also accepts only `ANTHROPIC_API_KEY` or an
`apiKeyHelper`. Auth: `ANTHROPIC_API_KEY` if set, else (macOS) an
`apiKeyHelper` that reads the logged-in Claude Code OAuth token from the
keychain at call time; the token is never written to disk.

Agents run with `--permission-mode bypassPermissions`: their code runs as
you, on macOS inside the write rule above.

## Verdicts (mechanical, they only filter)

The judged source is the script the agent last ran (`python plot.py`,
`cd X && uv run python plot.py $P/data.csv`, traced from the recorded Bash
calls), read from the run's own files. It is re-run in a copy of those files
with the same arguments, working directory, backend and added packages
(`uv run --with scipy`, `uv add`), and the image it
writes must equal the agent's `figure.png` (same pixel size, RMS at most
0.5 of 255). Only then do `dm.check`, lint and `[expect]` on the re-render
say anything about the figure.

- `OK`: a figure exists, its source reproduces it, `dm.check` has no
  WARNING (and no rule NOT RUN), lint has no critical finding (not applied
  to `bare`, which is not expected to follow dartwork-mpl), and every fact
  in the case's `[expect]` holds (panels, marks, texts, legend).
- `DEFECT`: a figure exists and its source reproduces it, but one of the
  above fails; the reasons are listed.
- `NO_FIGURE`: the agent left no image.
- `INVALID`: the harness cannot vouch for the run, with the reason:
  isolation broken, `claude` failed or timed out, the harness crashed, the
  run worked outside its root, or the source cannot be established (no
  script found, the script is not among the run's files, re-running it
  failed, or it does not reproduce `figure.png`). The figure is still on
  the contact sheet. When the re-render is not the figure, the script is
  run once more: if the two re-runs differ from each other, the reason says
  the script does not draw the same figure twice (its randomness is not
  seeded), which is the script's defect, not a tracing failure. Nothing is
  seeded or retried for the agent.
- `NOTRUN`: the run did not execute. Never counted as passed.

## Cases

One TOML file per case in `cases/`: `prompt`, `[files]` (tiny inline data)
and `[expect]`. Add a case by adding a file.

## Cost

A run costs about $0.03 to $0.08 (Sonnet 5.5: 33 runs at `--jobs 3` took
about 3 minutes and reported $1.08 on 2026-11-15; 26 runs at `--jobs 4`
reported $2.18 on 2026-11-22); it spends real Claude usage (the
summary prints the cost the stream reports). Run single cases while
iterating, and `rejudge` after changing the judge instead of re-running.

A sweep needs `uv` (it builds the wheel and syncs each project) and `claude`.

`evals/tests/` (pure parts, no `claude`) run with the default `uv run pytest`.
`evals/` is ruff-checked but not in basedpyright's strict paths (like tests).
