"""Each lint edge case, by name, on the source that needed it."""

from __future__ import annotations

from dartwork_mpl.edgecase import settle
from dartwork_mpl.guide import corpus, decide
from dartwork_mpl.guide.edges import EDGES
from dartwork_mpl.guide.model import Code, Known, LintFacts

KNOWN = Known(colors=frozenset({"red"}), colormaps=frozenset({"viridis"}))


def settled(source: str) -> tuple[list[str], tuple[str, ...]]:
    facts = LintFacts(Code.parse(source), KNOWN)
    result = settle(facts, decide.findings(facts, corpus.rules()), EDGES)
    return [f.rule_id for f in result.plan], result.fired


def test_quoted_text():
    source = '"""Never figsize=(w, h)."""\n# no plt.tight_layout() here\nx = "fig.savefig(p)"\n'
    assert settled(source) == ([], ("quoted-text",))


def test_quoted_text_keeps_code_on_the_same_line():
    assert settled("plt.tight_layout()  # tight_layout() is wrong")[0] == [
        "tight-layout"
    ]


def test_hand_merge_without_twin():
    two_panels = "a.legend(h1 + h2, l1 + l2)\n"
    assert settled(two_panels) == ([], ("hand-merge-without-twin",))
    twins = "b = a.twinx()\n" + two_panels
    assert settled(twins) == (["twin-legend-hand-merge"], ())


def test_colormap_registered_in_source():
    source = (
        'matplotlib.colormaps.register(cmap, name="mine")\n'
        'ax.imshow(z, cmap="mine")\nax.imshow(z, cmap="other")\n'
    )
    assert settled(source) == (
        ["invalid-colormap-name"],
        ("colormap-registered-in-source",),
    )
    dynamic = 'matplotlib.colormaps.register(cmap)\nax.imshow(z, cmap="x")\n'
    assert settled(dynamic) == ([], ("colormap-registered-in-source",))


def test_color_registered_in_source():
    source = (
        'get_named_colors_mapping()["brand"] = "#123456"\n'
        'ax.plot(x, color="brand")\nax.plot(x, color="nope")\n'
    )
    assert settled(source) == (
        ["invalid-color-name"],
        ("color-registered-in-source",),
    )
    dynamic = 'get_named_colors_mapping().update(m)\nax.plot(x, color="x")\n'
    assert settled(dynamic) == ([], ("color-registered-in-source",))


def test_global_random_seeded():
    draw = "y = np.random.normal(size=9)\n"
    assert settled(draw) == (["unseeded-global-random"], ())
    seeded = "np.random.seed(0)\n" + draw + "rng = np.random.default_rng()\n"
    assert settled(seeded) == (["unseeded-rng"], ("global-random-seeded",))
