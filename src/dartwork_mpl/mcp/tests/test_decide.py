"""The pure MCP decisions and the edge cases, called directly."""

from __future__ import annotations

import pytest

from dartwork_mpl.edgecase import settle
from dartwork_mpl.mcp import decide
from dartwork_mpl.mcp.edges import EDGES
from dartwork_mpl.mcp.model import (
    MAX_SOURCE_BYTES,
    Canvas,
    ChildRun,
    Crashed,
    Entry,
    FigureFacts,
    Kind,
    LintFinding,
    NoFigure,
    Pick,
    Query,
    Raised,
    Rendered,
    RenderRequest,
    TimedOut,
    words,
)


def entry(kind: Kind, id: str, text: str) -> Entry:
    return Entry(kind, id, text, words(text))


ENTRIES = (
    entry(Kind.PRESET, "presentation", "talk slides deck"),
    entry(Kind.PRESET, "report", "report document"),
    entry(Kind.COLOR, "dc.teal", "teal sequential colour"),
    entry(Kind.RULE, "figsize-direct", "raw figsize tuple slides"),
)


def test_rank_keeps_sharing_entries_best_first_and_narrows_by_kind() -> None:
    hits = decide.rank(Query.parse("slides talk"), ENTRIES)
    assert [h.id for h in hits] == ["presentation", "figsize-direct"]
    narrowed = decide.rank(Query.parse("slides", "rules"), ENTRIES)
    assert [h.id for h in narrowed] == ["figsize-direct"]


def test_rank_caps_each_kind_at_the_limit() -> None:
    many = tuple(entry(Kind.COLOR, f"dc.c{i}", "blue") for i in range(9))
    hits = decide.rank(Query(words("blue"), None, limit=3), many)
    assert len(hits) == 3


@pytest.mark.parametrize(
    ("severity", "blocks"),
    [("critical", True), ("warning", False), ("info", False)],
)
def test_only_a_critical_finding_blocks_the_run(severity, blocks) -> None:
    finding = LintFinding("x", severity, 1, "m", None)
    assert decide.blocks((finding,)) is blocks
    assert decide.blocks(()) is False


RENDERED = Rendered(Canvas(3.5, 2.6), ())


@pytest.mark.parametrize(
    ("run", "expected"),
    [
        (ChildRun(20, False, 0, RENDERED), RENDERED),
        (ChildRun(20, True, -9, RENDERED), TimedOut(20)),
        (ChildRun(20, False, -24, None), Crashed(-24)),
        (ChildRun(20, False, 0, NoFigure("fig")), NoFigure("fig")),
    ],
)
def test_outcome_timeout_first_then_missing_result_then_the_childs(
    run, expected
) -> None:
    assert decide.outcome(run) == expected


def test_the_named_figure_is_saved_and_nothing_is_guessed() -> None:
    assert decide.choose_figure(FigureFacts(True, 3)).pick is Pick.NAMED
    assert decide.choose_figure(FigureFacts(False, 0)).pick is Pick.NONE


@pytest.mark.parametrize(
    ("open_", "fired", "note"),
    [
        (1, ("figure-var-unbound",), "current figure"),
        (3, ("several-figures-unbound",), "the last of 3 open"),
        (0, (), None),
    ],
)
def test_an_unbound_figure_var_falls_back_to_the_current_figure(
    open_, fired, note
) -> None:
    facts = FigureFacts(False, open_)
    settled = settle(facts, decide.choose_figure(facts), EDGES)
    assert settled.fired == fired
    assert (settled.plan.note is None) is (note is None)
    if note:
        assert settled.plan.pick is Pick.CURRENT
        assert note in str(settled.plan.note)


@pytest.mark.parametrize(
    "args",
    [
        {"code": b"x"},
        {"code": "x" * (MAX_SOURCE_BYTES + 1)},
        {"code": "", "figure_var": "fig.ax"},
        {"code": "", "timeout": 0},
        {"code": "", "timeout": 121},
        {"code": "", "timeout": True},
        {"code": "", "timeout": float("nan")},
        {"code": "", "out_dir": ""},
        {"code": "", "inputs": "data.csv"},
    ],
)
def test_a_bad_render_argument_is_refused_before_anything_runs(args) -> None:
    with pytest.raises(ValueError):
        RenderRequest.parse(**args)


def test_queries_and_kinds_parse_or_refuse() -> None:
    assert Kind.parse("Templates") is Kind.TEMPLATE
    with pytest.raises(ValueError, match="kind must be one of"):
        Kind.parse("font")
    with pytest.raises(ValueError):
        Query.parse("  ")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (None, None),
        ("{not json", None),
        ('{"status": "weird"}', None),
        ('{"status": "raised", "error": "Boom"}', Raised("Boom")),
        ('{"status": "no_figure", "figure_var": "f"}', NoFigure("f")),
    ],
)
def test_a_missing_or_malformed_child_result_reads_as_none(
    text, expected
) -> None:
    assert ChildRun.parse_result(text) == expected
