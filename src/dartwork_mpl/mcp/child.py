"""The process ``render`` starts: limit itself, run the code once, save and check one figure.

Run as ``python -m dartwork_mpl.mcp.child <job.json>`` by :mod:`.render`,
never by hand. The job names the source, the bundle directory and the
result path. The child applies its resource limits first (and records which
ones took in ``limits.json`` beside the result), forces Agg, executes the
source as ``__main__``, picks the figure (``decide.choose_figure`` and the
named ``EDGES``), writes ``figure.png`` and ``figure.pdf`` with
``dm.save_formats`` and runs the figure checker through :func:`check_figure`.
Everything it learns goes to ``result.json``; stdout and stderr are the
code's own.
"""

from __future__ import annotations

import json
import math
import sys
import traceback
from pathlib import Path
from typing import TYPE_CHECKING

from ..edgecase import settle
from . import decide
from .edges import EDGES
from .model import MAX_ADDRESS_SPACE, MAX_FILE_BYTES, FigureFacts, Pick

if TYPE_CHECKING:
    from matplotlib.figure import Figure


def check_figure(fig: Figure) -> list[dict[str, str]]:
    """What ``dm.check`` finds in the figure, as the report's plain rows."""
    from ..check import check

    return [
        {
            "id": f.rule,
            "severity": f.severity.value,
            "message": f.message,
            "fix": f.fix,
        }
        for f in check(fig)
    ]


def limit(timeout: float) -> dict[str, int | None]:
    """Cap CPU seconds, address space and file size; ``None`` where the OS refused."""
    try:
        import resource
    except ImportError:  # Windows: no rlimits
        return dict.fromkeys(("cpu_seconds", "address_space", "file_bytes"))
    wanted = {
        "cpu_seconds": (resource.RLIMIT_CPU, math.ceil(timeout) + 1),
        "address_space": (resource.RLIMIT_AS, MAX_ADDRESS_SPACE),
        "file_bytes": (resource.RLIMIT_FSIZE, MAX_FILE_BYTES),
    }
    applied: dict[str, int | None] = {}
    for key, (which, value) in wanted.items():
        try:
            resource.setrlimit(which, (value, value))
            applied[key] = value
        except (ValueError, OSError):  # macOS refuses RLIMIT_AS
            applied[key] = None
    return applied


def run(source: Path, out_dir: Path, figure_var: str) -> dict[str, object]:
    """Execute the source once and save its figure; the result as JSON data."""
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure

    from ..save import save_formats

    namespace: dict[str, object] = {
        "__name__": "__main__",
        "__file__": str(source),
    }
    try:
        code = compile(source.read_text(encoding="utf-8"), "source.py", "exec")
        try:
            exec(code, namespace)
        except SystemExit as stop:
            if stop.code not in (None, 0):
                raise
        facts = FigureFacts(
            named=isinstance(namespace.get(figure_var), Figure),
            open=len(plt.get_fignums()),
        )
        choice = settle(facts, decide.choose_figure(facts), EDGES).plan
        if choice.pick is Pick.NONE:
            return {"status": "no_figure", "figure_var": figure_var}
        fig = namespace[figure_var] if choice.pick is Pick.NAMED else plt.gcf()
        assert isinstance(fig, Figure)
        save_formats(fig, out_dir / "figure", formats=("png", "pdf"))
    except BaseException as exc:  # noqa: BLE001 - any end of caller code is reported
        tail = exc.__traceback__.tb_next if exc.__traceback__ else None
        error = "".join(traceback.format_exception(type(exc), exc, tail))
        return {"status": "raised", "error": error}
    notes = [] if choice.note is None else [choice.note]
    try:
        findings = check_figure(fig)
    except Exception as exc:  # noqa: BLE001 - the image stands without its check
        findings = []
        notes.append(f"the figure check failed: {type(exc).__name__}: {exc}")
    width, height = fig.get_size_inches()
    return {
        "status": "rendered",
        "canvas": {"width_in": float(width), "height_in": float(height)},
        "findings": findings,
        "notes": notes,
    }


def main(job_path: str) -> None:
    """Read the job, limit this process, run, write the result."""
    job = json.loads(Path(job_path).read_text(encoding="utf-8"))
    result = Path(job["result"])
    limits = limit(float(job["timeout"]))
    result.with_name("limits.json").write_text(json.dumps(limits))
    outcome = run(Path(job["source"]), Path(job["out_dir"]), job["figure_var"])
    result.write_text(json.dumps(outcome), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
