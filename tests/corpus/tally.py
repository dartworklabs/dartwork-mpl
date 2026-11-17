"""Gather evidence from the corpus: what dm.check finds and what gets called.

    uv run python tests/corpus/tally.py                # this checkout
    uv run python tests/corpus/tally.py --render DIR   # also one PNG per figure

To judge an old commit, check it out into a temporary worktree and put its
package first on the path; the corpus is still read from this checkout:

    git worktree add /tmp/old <commit>
    PYTHONPATH=/tmp/old/src uv run python tests/corpus/tally.py --render /tmp/r

Only ``import dartwork_mpl as dm`` is used from the package, and every
attribute is looked up defensively, so a function an old commit lacks (or a
newer one removed) shows up as an error for that script, not a crash.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import io
import os
import runpy
import sys
import tempfile
import traceback
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

import dartwork_mpl as dm

HERE = Path(__file__).resolve().parent
FOLDERS = ("charts", "rough")


def scripts() -> list[Path]:
    """Every corpus script, charts first."""
    return [
        p for folder in FOLDERS for p in sorted((HERE / folder).glob("*.py"))
    ]


def run(script: Path, render: Path | None) -> tuple[list[tuple[str, str]], str]:
    """Run one script in an empty directory; what dm.check finds on each of
    its figures (suffix, rules) and any error.

    The figures are checked and rendered while the script's rcParams still
    hold: matplotlib picks tick locations again on every draw, from the
    rcParams of that moment, so a figure drawn after they are restored gets
    other ticks than the ones its layout was fitted to.
    """
    saved: list[object] = []
    original = getattr(dm, "save_formats", None)

    def capture(fig: object, *args: object, **kwargs: object) -> object:
        saved.append(fig)
        if original is None:
            return None
        return original(fig, *args, **kwargs)

    before = set(plt.get_fignums())
    error = ""
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        dm.save_formats = capture
        try:
            # rc_context: one script's rcParams never leak into the next.
            with plt.rc_context():
                try:
                    with contextlib.redirect_stdout(io.StringIO()):
                        runpy.run_path(str(script), run_name="__main__")
                except Exception as exc:  # an old commit may lack a call
                    last = traceback.extract_tb(exc.__traceback__)[-1]
                    error = f"{type(exc).__name__}: {exc} (line {last.lineno})"
                figures = list(saved)
                for num in sorted(set(plt.get_fignums()) - before):
                    fig = plt.figure(num)
                    if fig not in figures:
                        figures.append(fig)
                found: list[tuple[str, str]] = []
                for i, fig in enumerate(figures):
                    suffix = "" if len(figures) == 1 else f"_{i}"
                    found.append((suffix, rules_of(fig)))
                    if render is not None:
                        stem = script.parent.name + "_" + script.stem
                        fig.savefig(render / f"{stem}{suffix}.png", dpi=150)
        finally:
            if original is not None:
                dm.save_formats = original
            os.chdir(cwd)
    return found, error


def rules_of(fig: object) -> str:
    """The rules dm.check fired on one figure, however this commit says it."""
    check = getattr(dm, "check", None)
    if check is None:
        return "NOTRUN (no dm.check)"
    try:
        found = check(fig)
    except Exception as exc:
        return f"NOTRUN ({type(exc).__name__}: {exc})"
    rules = getattr(found, "rules", None)
    if rules is None:
        rules = [getattr(f, "rule", str(f)) for f in found]
    names = sorted({str(getattr(r, "value", r)) for r in rules})
    text = ", ".join(names) if names else "-"
    if "NOT RUN" in str(found):
        text += "  (some rules NOT RUN)"
    return text


def calls(paths: list[Path]) -> tuple[Counter[str], Counter[str]]:
    """How often each dm.* function and each of its keywords is called."""
    functions: Counter[str] = Counter()
    keywords: Counter[str] = Counter()
    for path in paths:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call):
                continue
            parts: list[str] = []
            target = node.func
            while isinstance(target, ast.Attribute):
                parts.append(target.attr)
                target = target.value
            if not (isinstance(target, ast.Name) and target.id == "dm"):
                continue
            name = "dm." + ".".join(reversed(parts))
            functions[name] += 1
            for keyword in node.keywords:
                if keyword.arg is not None:
                    keywords[f"{name}({keyword.arg}=)"] += 1
    return functions, keywords


def main() -> None:
    """Run the corpus, print the findings per script and the call counts."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--render", type=Path, help="write one PNG per figure")
    args = parser.parse_args()
    if args.render:
        args.render.mkdir(parents=True, exist_ok=True)

    print(f"dartwork_mpl from {Path(dm.__file__).parent}")
    paths = scripts()
    fired: Counter[str] = Counter()
    for path in paths:
        name = f"{path.parent.name}/{path.stem}"
        figures, error = run(path, args.render)
        if error:
            print(f"{name:42} ERROR {error}")
        for suffix, found in figures:
            fired.update(r for r in found.split(", ") if r.isupper())
            label = f"{name}[{suffix[1:]}]" if suffix else name
            print(f"{label:42} {found}")
        plt.close("all")

    print("\nrules fired, scripts:")
    for rule, count in fired.most_common():
        print(f"  {count:3}  {rule}")
    functions, keywords = calls(paths)
    print("\ndm.* calls over the corpus:")
    for function, count in functions.most_common():
        print(f"  {count:3}  {function}")
    print("\nkeywords:")
    for keyword, count in keywords.most_common():
        print(f"  {count:3}  {keyword}")


if __name__ == "__main__":
    sys.exit(main())
