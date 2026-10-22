"""``save_formats`` parses each ``formats`` entry once into the output it plans.

Pins the path each entry produces, which spellings get the reproducible SVG
and PDF treatment, and that anything else is saved as a plain output.
"""

import pytest

from dartwork_mpl.io import (
    _parse_save_format,
    _PdfOutput,
    _PlainOutput,
    _SvgOutput,
)


@pytest.mark.parametrize(
    ("fmt", "expected"),
    [
        ("svg", _SvgOutput("out/c.svg", compressed=False)),
        (".svgz", _SvgOutput("out/c.svgz", compressed=True)),
        ("pdf", _PdfOutput("out/c.pdf")),
        ("png", _PlainOutput("out/c.png")),
        ("SVG", _PlainOutput("out/c.SVG")),
        ("PDF", _PlainOutput("out/c.PDF")),
        ("bogus", _PlainOutput("out/c.bogus")),
    ],
)
def test_format_entry_parses_to_its_output(fmt: str, expected: object) -> None:
    """Only exact lowercase svg/svgz/pdf are special; a leading dot is dropped."""
    assert _parse_save_format(fmt, "out/c") == expected
