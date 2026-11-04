"""``axes_titles`` reads the side titles and agrees with ``ax.get_title`` (#523).

``ax.set_title(..., loc="left")`` stores its Text in a private attribute;
``axes_titles`` is the one reader of those attributes and keeps a title only
while its text equals the public ``ax.get_title(loc=...)``.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from dartwork_mpl._figure_geometry import axes_text_artists, axes_titles


def test_titles_match_the_public_get_title() -> None:
    fig, ax = plt.subplots()
    for loc in ("center", "left", "right"):
        ax.set_title(f"{loc} headline", loc=loc)
    titles = axes_titles(ax)
    assert set(titles) == {"center", "left", "right"}
    for loc, text in titles.items():
        assert text.get_text() == ax.get_title(loc=loc)
    plt.close(fig)


def test_a_title_the_public_api_disowns_is_dropped(monkeypatch) -> None:
    fig, ax = plt.subplots()
    ax.set_title("Left headline", loc="left")
    monkeypatch.setattr(ax, "get_title", lambda loc="center": "")
    assert "left" not in axes_titles(ax)
    plt.close(fig)


def test_text_artists_cover_texts_titles_and_axis_labels() -> None:
    fig, ax = plt.subplots()
    note = ax.text(0.5, 0.5, "note")
    ax.set_title("Left headline", loc="left")
    artists = axes_text_artists(ax)
    assert note in artists
    assert ax.xaxis.label in artists and ax.yaxis.label in artists
    assert any(t.get_text() == "Left headline" for t in artists)
    plt.close(fig)
