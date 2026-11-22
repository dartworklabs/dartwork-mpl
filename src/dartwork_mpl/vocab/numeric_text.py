"""Numeric runs and decimal boundaries in one line of display text."""

from __future__ import annotations

import re
from dataclasses import dataclass

_NUMBER = re.compile(
    r"[+\u2212-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)"
)
_CLOSING = re.compile(r"[^\s\[({]*")
_MATH_DELIMITER = re.compile(r"(?<!\\)\$")


def has_math(text: str) -> bool:
    """Whether Matplotlib will see paired mathtext delimiters."""
    count = len(_MATH_DELIMITER.findall(text))
    return count > 0 and count % 2 == 0


@dataclass(frozen=True)
class NumberRun:
    """The space before a number and what sits on each side of its mark."""

    space: str
    prefix: str
    dot: str
    before: str
    after: str


@dataclass(frozen=True)
class NumericText:
    """A whole cell and the runs it can use for decimal alignment."""

    text: str
    numbers: tuple[NumberRun, ...]
    tail: str

    @classmethod
    def parse(cls, text: str) -> NumericText:
        """Keep mathtext intact and give numeric minus signs their glyph."""
        matches = () if has_math(text) else tuple(_NUMBER.finditer(text))
        at = 0
        runs: list[NumberRun] = []
        whole: list[str] = []
        for i, match in enumerate(matches):
            prefix = text[at : match.start()]
            limit = (
                matches[i + 1].start() if i + 1 < len(matches) else len(text)
            )
            closing = _CLOSING.match(text, match.end(), limit)
            at = closing.end() if closing else match.end()
            suffix = text[match.end() : at]
            token = match.group()
            if token.startswith("-"):
                token = "\u2212" + token[1:]
            whole.extend((prefix, token, suffix))
            before, dot, fraction = token.partition(".")
            lead = prefix.lstrip()
            raw_before = match.group().partition(".")[0]
            runs.append(
                NumberRun(
                    prefix[: len(prefix) - len(lead)],
                    text[: match.start()] + raw_before,
                    dot,
                    lead + before,
                    dot + fraction + suffix,
                )
            )
        tail = text[at:]
        return cls("".join((*whole, tail)), tuple(runs), tail)
