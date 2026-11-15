"""The ordinary save plan and its named edge cases, called directly."""

from __future__ import annotations

import pytest

from dartwork_mpl.edgecase import settle
from dartwork_mpl.save import decide
from dartwork_mpl.save.edges import EDGES
from dartwork_mpl.save.model import (
    Metadata,
    PdfWriter,
    PlainWriter,
    SaveRequest,
    SvgWriter,
    SvgzWriter,
)


def _plan(stem="out/chart", formats=("png", "pdf"), metadata=None, salt=False):
    request = SaveRequest.parse(stem, formats, metadata, ambient_salt=salt)
    return settle(request, decide.plan(request), EDGES)


@pytest.mark.parametrize(
    ("stem", "path", "cut"),
    [
        ("out/chart", "out/chart", None),
        ("out/chart.png", "out/chart", ".png"),
        ("out/chart.PDF", "out/chart", ".pdf"),
        ("out/v1.2", "out/v1.2", None),
        ("out/.png", "out/.png", None),
    ],
)
def test_a_trailing_image_suffix_is_cut(stem, path, cut):
    parsed = SaveRequest.parse(stem, ()).stem
    assert (parsed.path, parsed.cut) == (path, cut)


def test_each_format_gets_its_writer_and_path():
    writes = _plan(formats=("png", ".pdf", "svg", "svgz", "eps")).plan.writes
    assert [(w.path, w.writer) for w in writes] == [
        ("out/chart.png", PlainWriter()),
        ("out/chart.pdf", PdfWriter()),
        ("out/chart.svg", SvgWriter()),
        ("out/chart.svgz", SvgzWriter()),
        ("out/chart.eps", PlainWriter()),
    ]


def test_pdf_and_svg_drop_the_timestamp_and_svg_is_salted_by_name():
    png, pdf, svg = _plan(formats=("png", "pdf", "svg")).plan.writes
    assert png.metadata is None and png.salt is None
    assert pdf.metadata == Metadata((("CreationDate", None),))
    assert pdf.salt == "chart"  # unused by the PDF writer
    assert svg.metadata == Metadata((("Date", None),))


def test_other_caller_metadata_is_kept_in_order():
    (pdf,) = _plan(formats=("pdf",), metadata={"Title": "t"}).plan.writes
    assert pdf.metadata == Metadata((("Title", "t"), ("CreationDate", None)))


def test_caller_timestamp_wins_only_where_it_applies():
    settled = _plan(formats=("pdf", "svg"), metadata={"CreationDate": "d"})
    assert settled.fired == ("caller-timestamp",)
    pdf, svg = settled.plan.writes
    assert pdf.metadata == Metadata((("CreationDate", "d"),))
    assert svg.metadata == Metadata((("CreationDate", "d"), ("Date", None)))


def test_ambient_svg_salt_is_left_in_force():
    settled = _plan(formats=("svg",), salt=True)
    assert settled.fired == ("ambient-svg-salt",)
    assert settled.plan.writes[0].salt is None


@pytest.mark.parametrize(
    ("formats", "error"),
    [((3,), TypeError), (("",), ValueError), ((".",), ValueError)],
)
def test_bad_format_entries_are_rejected(formats, error):
    with pytest.raises(error):
        SaveRequest.parse("out", formats)


def test_metadata_must_be_a_mapping():
    with pytest.raises(TypeError, match="metadata must be a dict"):
        SaveRequest.parse("out", ("pdf",), [("Title", "t")])
