---
orphan: true
---

# Recapturing the legacy MCP wire

`tests/mcp/data_repair/fixtures/legacy_calls.json` pins what the
pre-`report` `validate_plot_data` tool answered through a real FastMCP
`Client`, one entry per FastMCP version
(`tests/contracts/test_mcp_data_repair_contract.py` picks the entry by
`fastmcp.__version__` and fails collection for a version without one). The
files that produce an entry live in `tests/mcp/data_repair/capture/`.

| File | Role | sha256 (first 8) |
| --- | --- | --- |
| `capture_legacy_runtime.py` | runs the 62 recorded requests against the pinned tool | `36793779` |
| `legacy-tools.py` | historical `mcp/tools.py` of baseline `226cddc5`, verbatim | `897292d9` |
| `legacy-assets.py` | the `_assets` module it imports, verbatim | `216f0e5e` |

## The hashes are the rule

Each entry records `tools_sha256`, `capture_provenance.legacy_assets_sha256`,
`requests_sha256` and `capture_script_sha256`.
`tests/contracts/test_mcp_data_repair_capture.py` checks every record against
the file in the repository, so the script is **byte-identical** to the one that
produced the 2.14.7, 3.4.10 and 3.4.11 entries. That is why the script is
excluded from Ruff in `pyproject.toml` and why none of the three files may be
edited or reformatted: a changed byte makes the recorded hash point at nothing.
If the script must change, recapture the entries that cite it, or retire the
old hash in the same commit and say why.

The 2.13.3 and 3.4.2 entries predate the provenance record (they name the tool
source only). Their script is not in the repository.

The first script (sha256 `9720960720e6…`, used for the 2.14.7 and 3.4.10
entries before pydantic 2.14) is this file with four edits reversed: the
repository path was hard-coded to a worktree and the results were written next
to the script instead of to the two arguments, the artifact store was kept next
to the results instead of a temporary directory, the comparison JSON was written
instead of dropped, and the last line asserted
`comparison['calls'] and comparison['discovery']`. Reversing those four hunks
gives the first script byte for byte (checked when this page was written).

## Why the closing assert is not restored

It compared the new capture with the 3.4.2 entry. Any pydantic minor newer than
3.4.2's 2.13 changes the error-URL text (`errors.pydantic.dev/2.13/` to
`/2.14/`), so `calls` is false on every legitimate capture today and the assert
would only fail. The script now prints that comparison and exits 0; **its exit
code is not an acceptance check.** The checks that can fail are:

- `test_entry_answers_like_the_reference_capture` compares `calls` and
  `discovery` with 3.4.2 after reading the URL minor as one text.
- The contract test compares the production server with the new entry.

## Recapture a runtime

An entry is valid for one pydantic minor (the URL), so a pydantic minor bump
recaptures every entry; a FastMCP patch release adds one. Use Python 3.12, as
CI does, and write the output outside the repository.

```bash
# The locked runtime:
uv run python tests/mcp/data_repair/capture/capture_legacy_runtime.py . /abs/out/capture.json

# Any other FastMCP, in a private environment (`uv pip install` rewrites its target):
export UV_PYTHON=3.12 UV_PROJECT_ENVIRONMENT=$HOME/.cache/wire-venv VIRTUAL_ENV=$HOME/.cache/wire-venv
uv sync --frozen --all-extras --dev
uv pip uninstall fastmcp fastmcp-slim
uv pip install '.[mcp,notebook,ui]' 'fastmcp==X.Y.Z'
uv run --no-sync python tests/mcp/data_repair/capture/capture_legacy_runtime.py . /abs/out/capture.json

# Put it in the fixture under its own version; `--indent 2` keeps every other byte.
F=tests/mcp/data_repair/fixtures/legacy_calls.json
jq --indent 2 --slurpfile c /abs/out/capture.json '.runtimes[$c[0].fastmcp] = $c[0]' $F > /abs/out/fixture.json
cp /abs/out/fixture.json $F
```

Then run, under that same runtime, `tests/contracts/test_mcp_data_repair_contract.py`
and `tests/contracts/test_mcp_data_repair_capture.py`, and read `git diff`: only
the new or replaced entry may change. A capture takes about three seconds; the
install is the slow part. The lock needs an entry; each `test-mcp-artifacts`
cell needs one too and runs this contract (see `ci-execution.md`).
