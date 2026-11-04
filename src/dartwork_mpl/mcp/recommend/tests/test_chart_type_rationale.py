"""The recommendation describes what the templates draw now (#561)."""

from dartwork_mpl.mcp.recommend.chart_type import suggest


def test_rationale_promises_no_title_or_source_note() -> None:
    # #561 removed every template's title, subtitle and source footnote; the
    # rationale an agent reads when it picks a template must not offer them.
    rationale = suggest("temporal", "continuous", 19, 1)["rationale"]
    assert "narrative title" not in rationale
    assert "source footnote" not in rationale
    assert "only when the user asks" in rationale
