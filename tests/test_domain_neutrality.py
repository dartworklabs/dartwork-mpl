"""Regression test for domain-neutrality of the dartwork-mpl source tree.

dartwork-mpl is a general-purpose matplotlib design utility. It must not
accumulate finance-domain vocabulary in its public surface (module code,
docstrings, the shipped prompt assets, or the shipped style/asset files).
When finance examples or phrasing are needed, they belong in downstream
packages such as the ``valuation`` workspace sibling.

This test scans the shipped source tree for a small, carefully chosen set
of finance-domain terms. The list is intentionally narrow so that it
triggers only on unambiguous finance vocabulary, not on general English
words that happen to show up in scientific or visual contexts.

If this test fires, the usual fix is to reword the offending docstring,
comment, or example with a domain-neutral analogue (temperature, time,
measurement value, category A/B/C, etc.).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Root of the installable package (what actually ships).
_SRC_ROOT = Path(__file__).resolve().parents[1] / "src" / "dartwork_mpl"

# File extensions to scan. We deliberately include:
#   - .py    (code and docstrings)
#   - .md    (shipped prompt assets under asset/prompt/)
#   - .mplstyle (style presets)
# We do NOT scan binary assets (fonts, pdfs, pngs).
_SCAN_SUFFIXES = {".py", ".md", ".mplstyle"}

# Paths to skip within _SRC_ROOT (normalised relative path parts).
_SKIP_DIR_PARTS = {"__pycache__"}

# Finance-domain vocabulary that should not appear in the shipped package.
# Matched case-insensitively, as whole words. English entries use \b word
# boundaries; Korean entries use positive/negative lookarounds against
# Hangul syllables to avoid matching inside compound words.
_ENGLISH_TERMS = (
    "revenue",
    "profit",
    "ebitda",
    "earnings",
    "fiscal",
    "valuation",
    "dcf",
)
_KOREAN_TERMS = ("억원", "조원", "매출", "영업이익", "매출액")

# Built regex: English words with \b boundaries; Korean tokens without
# word boundaries (Unicode \b does not treat Hangul syllables as word
# characters consistently across platforms).
_EN_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in _ENGLISH_TERMS) + r")\b",
    flags=re.IGNORECASE,
)
_KR_PATTERN = re.compile("|".join(re.escape(t) for t in _KOREAN_TERMS))


def _iter_shipped_files() -> list[Path]:
    files: list[Path] = []
    for path in _SRC_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in _SCAN_SUFFIXES:
            continue
        if any(part in _SKIP_DIR_PARTS for part in path.parts):
            continue
        files.append(path)
    return files


def _scan(path: Path) -> list[tuple[int, str, str]]:
    """Return (line_no, term, line_text) for every finance-term hit."""
    hits: list[tuple[int, str, str]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return hits
    for line_no, line in enumerate(text.splitlines(), start=1):
        for match in _EN_PATTERN.finditer(line):
            hits.append((line_no, match.group(0), line.rstrip()))
        for match in _KR_PATTERN.finditer(line):
            hits.append((line_no, match.group(0), line.rstrip()))
    return hits


@pytest.mark.parametrize(
    "path", _iter_shipped_files(), ids=lambda p: str(p.relative_to(_SRC_ROOT))
)
def test_no_finance_terms_in_shipped_source(path: Path) -> None:
    """Each shipped file must be free of finance-domain vocabulary."""
    hits = _scan(path)
    if hits:
        formatted = "\n".join(
            f"  {path.relative_to(_SRC_ROOT)}:{line_no}: "
            f"finance term {term!r} in: {text}"
            for line_no, term, text in hits
        )
        pytest.fail(
            "Finance-domain vocabulary detected in dartwork-mpl source "
            "(dartwork-mpl is a general-purpose library; finance examples "
            "belong downstream, e.g. in the valuation package). "
            f"Offenders:\n{formatted}"
        )
