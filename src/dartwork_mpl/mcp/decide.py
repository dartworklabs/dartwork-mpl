"""Pure MCP decisions: which references a query wants, which figure to save, how a run ended.

A search scores each entry by the query words it shares and keeps the best
few of each kind. The child saves the figure bound to ``figure_var``;
guessing pyplot's current figure instead is a named special case in
``edges.py``. A run that timed out is a timeout whatever it left behind; a
child that ended without a result crashed; otherwise its own result stands.
"""

from __future__ import annotations

from .model import (
    ChildRun,
    Crashed,
    Entries,
    Entry,
    FigureChoice,
    FigureFacts,
    Lint,
    Outcome,
    Pick,
    Query,
    TimedOut,
)


def rank(query: Query, entries: Entries) -> Entries:
    """The entries sharing a word with the query, best first, ``limit`` per kind."""
    scored = sorted(
        (
            (len(query.words & e.words), e)
            for e in entries
            if query.kind in {None, e.kind}
        ),
        key=lambda pair: (-pair[0], pair[1].id),
    )
    hits: list[Entry] = []
    for score, entry in scored:
        if score and sum(h.kind is entry.kind for h in hits) < query.limit:
            hits.append(entry)
    return tuple(hits)


def blocks(lint: Lint) -> bool:
    """Whether the lint stops the run: any critical finding does."""
    return any(f.severity == "critical" for f in lint)


def choose_figure(facts: FigureFacts) -> FigureChoice:
    """Save the figure the code bound to ``figure_var``, or none."""
    return FigureChoice(Pick.NAMED if facts.named else Pick.NONE)


def outcome(run: ChildRun) -> Outcome:
    """How the run ended, from the clock, the exit and the child's result."""
    if run.timed_out:
        return TimedOut(run.timeout)
    if run.result is None:
        return Crashed(run.returncode)
    return run.result
