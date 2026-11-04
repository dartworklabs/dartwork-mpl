"""Round 1 audit script for dartwork-mpl public API.

Outputs a markdown table with the auto-extractable columns:
``name``, ``module``, ``loc``, ``repo_callsites``.

Manual columns (``mpl_canonical_1to1``, ``inline_difficulty``,
``classification``, ``notes``, ``status``) are filled in
``docs/development/api_audit.md`` after running this.

Usage::

    python scripts/api_audit.py > /tmp/audit_raw.md

.. caution::
    ``repo_callsites`` is approximate. Searches ``.py`` and ``.md`` only
    and counts whole-word matches without context. Common names (e.g.
    ``figure``, ``hex``) include matches against unrelated identifiers —
    matplotlib's ``plt.figure``, hex codes in prose. Treat counts as
    upper bounds when classifying.

See ``docs/superpowers/specs/2026-05-05-prune-low-value-utils-design.md``
for column definitions.
"""

from __future__ import annotations

import ast
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "dartwork_mpl"

# Out of scope per spec §7.
EXCLUDED_PARTS = {"_helpers.py", "cli.py", "mcp", "ui", "asset", "asset_viz"}
SEARCH_DIRS = ["docs", "tests", "examples"]


def iter_python_files(root: pathlib.Path):
    """Yield ``.py`` files under ``root`` in sorted order.

    Skips ``__pycache__`` and any path with a part in ``EXCLUDED_PARTS``
    (MCP, UI, assets, the CLI and private helpers).
    """
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in rel.parts):
            continue
        yield path


def extract_public_defs(path: pathlib.Path):
    """Yield the module-level functions and classes in ``path`` without a leading underscore.

    Nested definitions are not visited. Raises ``SyntaxError`` if the file does
    not parse.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            if node.name.startswith("_"):
                continue
            yield node


def function_loc(node: ast.AST) -> int:
    """Return the body line span of a function, excluding its docstring.

    Classes and empty bodies count as 0. Blank and comment lines inside the
    span are counted.
    """
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return 0
    body = node.body
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    if not body:
        return 0
    start = body[0].lineno
    end = body[-1].end_lineno or body[-1].lineno
    return end - start + 1


def grep_callsites(name: str, cwd: pathlib.Path) -> int:
    """Count whole-word matches of ``name`` in docs, tests and examples via ``rg``.

    Searches ``.py`` and ``.md`` files, excluding the audit's own output page.
    Returns -1 when ``rg`` fails; raises ``FileNotFoundError`` if ``rg`` is not
    installed.
    """
    cmd = [
        "rg",
        "-c",
        "--type",
        "py",
        "--type",
        "md",
        "--glob",
        "!docs/development/api_audit.md",
        "--",
        rf"\b{name}\b",
        *SEARCH_DIRS,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if result.returncode not in (0, 1):
        return -1
    total = 0
    for line in result.stdout.splitlines():
        try:
            total += int(line.rsplit(":", 1)[1])
        except (ValueError, IndexError):  # noqa: PERF203
            continue
    return total


def main() -> int:
    """Print a markdown table of every public definition with its size and call sites.

    Runs one ``rg`` per definition, so it is slow; always returns 0.
    """
    rows = []
    for path in iter_python_files(SRC):
        rel = path.relative_to(ROOT)
        module = ".".join(rel.with_suffix("").parts).replace("src.", "")
        for node in extract_public_defs(path):
            kind = "class" if isinstance(node, ast.ClassDef) else "func"
            loc = function_loc(node)
            callsites = grep_callsites(node.name, ROOT)
            rows.append((module, node.name, kind, loc, callsites))

    rows.sort()
    print("| name | module | kind | loc | repo_callsites |")
    print("|---|---|---|---|---|")
    for module, name, kind, loc, callsites in rows:
        print(f"| `{name}` | `{module}` | {kind} | {loc} | {callsites} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
