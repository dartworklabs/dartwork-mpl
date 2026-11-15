"""The lint rules and the search ranking, decided from text alone."""

from __future__ import annotations

import pytest

from dartwork_mpl.guide import corpus, decide
from dartwork_mpl.guide.model import (
    Code,
    ColorName,
    Known,
    LintFacts,
    Literal,
    Rules,
)
from dartwork_mpl.guide.reference import Query, Reference, ref_id

KNOWN = Known(
    colors=frozenset({"red", "dc.blue6", "tab:blue"}),
    colormaps=frozenset({"viridis", "viridis_r", "dc.blue", "jet"}),
)


def rule_ids(source: str) -> list[str]:
    facts = LintFacts(Code.parse(source), KNOWN)
    return [f.rule_id for f in decide.findings(facts, corpus.rules())]


# One line per kept rule: a source that breaks it and only it.
BROKEN = [
    ('ax.imshow(z, cmap="virdis")', "invalid-colormap-name"),
    ('ax.plot(x, color="dc.blu6")', "invalid-color-name"),
    ("fig, ax = plt.subplots(figsize=(4, 3))", "figsize-direct"),
    ("plt.subplots(figsize=dm.figsize(13))", "raw-width-number"),
    ("fig.tight_layout()", "tight-layout"),
    ("plt.subplots(dpi=200)", "dpi-arg"),
    ('plt.style.use("ggplot")', "plt-style-use"),
    ('fig.savefig("a.png")', "savefig-direct"),
    ('ax.set_title("t", fontsize=12)', "fontsize-literal"),
    ("ax.plot(x, linewidth=2)", "linewidth-literal"),
    ('ax.imshow(z, cmap="jet")', "jet-cmap"),
    ('plt.subplots(figsize=dm.figsize("20cm"))', "oversize-width"),
    ('ax.plot(x, color="#235fa4")', "raw-hex-color"),
    ("plt.show()", "plt-show-only"),
    ("ax.legend(h1 + h2, l1 + l2)", "twin-legend-hand-merge"),
]


@pytest.mark.parametrize(("source", "rule"), BROKEN)
def test_each_rule_finds_its_pattern(source, rule):
    assert rule_ids(source) == [rule]


def test_every_catalog_rule_has_a_case():
    assert {r.id for r in corpus.rules().items} == {rule for _, rule in BROKEN}


@pytest.mark.parametrize(
    "source",
    [
        'fig, ax = plt.subplots(figsize=dm.figsize("13cm", "wide"))',
        "ax.plot(x, linewidth=0.3, lw=0)",  # hairline and no border
        'ax.plot(x, color="C0", mec="0.5", mfc="none", fc="#abcd")',
        'ax.imshow(z, cmap="viridis_r")',
        "ax.set_title('t', fontsize=dm.fs(1))",
        'dm.label_bars(ax, color="series")',  # a dm helper's own word
    ],
)
def test_the_preset_way_is_clean(source):
    assert rule_ids(source) == []


def test_a_finding_names_its_line_and_literal():
    facts = LintFacts(Code.parse('import x\nax.plot(color="nope")\n'), KNOWN)
    (found,) = decide.findings(facts, corpus.rules())
    assert (found.line, found.name) == (2, "nope")
    assert str(found).startswith("[critical] invalid-color-name (line 2)")


def test_unparsable_source_still_gets_the_pattern_rules():
    assert rule_ids("def broken(:\n    plt.tight_layout()") == ["tight-layout"]


@pytest.mark.parametrize(
    ("value", "ok"),
    [("red", True), ("RED", True), ("tab:blue", True), ("#fff", True),
     ("#ffffff80", True), ("C12", True), ("0.75", True), ("none", True),
     ("#ggg", False), ("1.5", False), ("dc.blue66", False)],
)  # fmt: skip
def test_is_color(value, ok):
    assert decide.is_color(Literal(ColorName(), value, 0), KNOWN) is ok


def test_oversized_source_is_refused():
    with pytest.raises(ValueError, match="at most"):
        Code.parse("x = 1\n" * 100_000)


def test_a_malformed_catalog_is_refused():
    with pytest.raises(ValueError, match="pattern or a check"):
        Rules.parse("rules:\n  - {id: a, severity: info, message: m}\n")


def _template(id: str, tags: str) -> Reference:
    text = f'"""{id}."""\n# ai-template-meta-start\n# tags: {tags}\n# ai-template-meta-end\n'
    return Reference.template(id, text)


def test_rank_scores_shared_words_and_puts_templates_first():
    refs = (
        Reference.guide("guide/colors", "# Colours\n\nBars and lines.\n"),
        _template("template/bar", "bar, comparison"),
        _template("template/line", "line, trend"),
    )
    hits = decide.rank(Query.parse("compare bars"), refs)
    assert [r.id for r in hits] == ["template/bar", "guide/colors"]
    assert decide.rank(Query.parse("nothing shared"), refs) == ()
    assert len(decide.rank(Query.parse("bars", limit=1), refs)) == 1


@pytest.mark.parametrize(
    "text", ["../etc/passwd", "guide/../x", "template/Bar", "templates/bar", 3]
)
def test_a_reference_id_never_names_a_path(text):
    with pytest.raises(ValueError):
        ref_id(text)
