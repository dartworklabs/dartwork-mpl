"""Read unambiguous numeric runs without changing the source text."""

from __future__ import annotations

import re
from dataclasses import dataclass

_NUMBER = re.compile(
    r"(?P<mantissa>[+\u2212-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)"
    r"(?:\.\d+)?|\.\d+))(?P<exponent>[eE][+\u2212-]?\d+)?"
)
_OPEN = re.compile(r"\s*[\[({$€£¥]*")
_ATTACHED = re.compile(r"[^\s\[({$€£¥]*")
_UNIT = re.compile(
    r"[\s,\])}%°‰†*]*(?:[^\W\d_]+(?:[/· ][^\W\d_]+)*[\s,\])}%°‰†*]*)?"
)
_CALENDAR = re.compile(r"\s*\d{2,4}년\s*\d{1,2}월(?:\s*\d{1,2}일)?\s*")
_MATH_DELIMITER = re.compile(r"(?<!\\)\$")


def has_math(text: str) -> bool:
    """Whether Matplotlib will see paired mathtext delimiters."""
    count = len(_MATH_DELIMITER.findall(text))
    return count > 0 and count % 2 == 0


@dataclass(frozen=True)
class NumberRun:
    """The authored space and text runs on either side of one decimal stop."""

    space: str
    prefix: str
    dot: str
    before: str
    after: str


@dataclass(frozen=True)
class NumericText:
    """A line of numbers, or an intact label with no unambiguous stops."""

    text: str
    numbers: tuple[NumberRun, ...]

    @classmethod
    def parse(cls, text: str) -> NumericText:
        """Keep dates, ranges, ratios, identifiers and math intact."""
        if has_math(text) or _CALENDAR.fullmatch(text):
            return cls(text, ())
        matches = tuple(_NUMBER.finditer(text))
        at = 0
        runs: list[NumberRun] = []
        for i, match in enumerate(matches):
            prefix = text[at : match.start()]
            if not _OPEN.fullmatch(prefix) or (
                i
                and not prefix
                and text[at - 1 : at] not in {",", ")", "]", "}"}
            ):
                return cls(text, ())
            if i + 1 == len(matches):
                at = len(text)
            else:
                between = _ATTACHED.match(
                    text, match.end(), matches[i + 1].start()
                )
                assert between is not None
                at = between.end()
            suffix = text[match.end() : at]
            if not _UNIT.fullmatch(suffix):
                return cls(text, ())
            whole, dot, fraction = match.group("mantissa").partition(".")
            lead = prefix.lstrip()
            runs.append(
                NumberRun(
                    prefix[: len(prefix) - len(lead)],
                    text[: match.start()] + whole,
                    dot,
                    lead + whole,
                    dot + fraction + (match.group("exponent") or "") + suffix,
                )
            )
        return cls(text, tuple(runs))
