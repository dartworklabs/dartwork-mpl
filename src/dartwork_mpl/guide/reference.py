"""The guide's reading side: a :class:`Reference` (a guide page or a
template) with the words a :class:`Query` is ranked against."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class Guide:
    """A guide page (prose). ``tie``: its order on an equal score."""

    word: ClassVar[str] = "guide"
    tie: ClassVar[int] = 1

    def __str__(self) -> str:
        """The word an id starts with."""
        return self.word


@dataclass(frozen=True)
class Template:
    """A plot template (a runnable script); ranked first on an equal score."""

    word: ClassVar[str] = "template"
    tie: ClassVar[int] = 0

    def __str__(self) -> str:
        """The word an id starts with."""
        return self.word


#: A guide page or a plot template.
Kind = Guide | Template


_REF_ID = re.compile(r"guide/[a-z0-9-]+|template/(?:advanced/)?[a-z0-9_]+")
_WORD = re.compile(r"[a-z0-9]+")


def ref_id(text: object) -> str:
    """``text`` as a reference id; anything else raises ``ValueError``.

    An id (``guide/layout``, ``template/bar``, ``template/advanced/bar``)
    never names a path.
    """
    if not isinstance(text, str) or not _REF_ID.fullmatch(text):
        raise ValueError(
            f"{text!r} is not a reference id like 'guide/layout', 'template/bar'"
            " or 'template/advanced/bar'; dm.guide.references() lists them"
        )
    return text


def words(text: str) -> frozenset[str]:
    """The lower-case words of ``text``, a plural ``s`` dropped (bars → bar)."""
    return frozenset(
        w[:-1] if len(w) > 3 and w.endswith("s") else w
        for w in _WORD.findall(text.lower())
    )


@dataclass(frozen=True)
class Reference:
    """A guide page or template: its id, a title and summary, and its words."""

    id: str
    kind: Kind
    title: str
    summary: str
    tags: frozenset[str]
    words: frozenset[str]

    @classmethod
    def guide(cls, id: str, text: str) -> Reference:
        """A Markdown page: its first heading, first paragraph and every heading."""
        headings = [
            ln.lstrip("#").strip()
            for ln in text.splitlines()
            if ln.startswith("#")
        ]
        title = headings[0] if headings else id
        prose = [
            " ".join(p.split())
            for p in text.split("\n\n")
            if p.strip()
            and not p.lstrip().startswith(("#", "```", "|", "---", "-"))
        ]
        summary = prose[0] if prose else title
        tags = words(id.removeprefix("guide/"))
        return cls(
            id,
            Guide(),
            title,
            summary,
            tags,
            words(" ".join([*headings, summary])),
        )

    @classmethod
    def template(cls, id: str, text: str) -> Reference:
        """A template script: its docstring's first line and its meta block."""
        meta = template_meta(text)
        docstring = text.lstrip().removeprefix('"""').split('"""', 1)[0].strip()
        title = docstring.splitlines()[0] if docstring else id
        summary = meta.get("use_case", title)
        if (shape := meta.get("data_shape")) is not None:
            summary += f". Data: {shape}"
        tags = words(meta.get("tags", ""))
        return cls(
            id,
            Template(),
            title,
            summary,
            tags,
            words(" ".join([title, *meta.values()])),
        )


def template_meta(text: str) -> dict[str, str]:
    """The ``key: value`` lines between ``# ai-template-meta-start`` and ``-end``."""
    block = text.partition("# ai-template-meta-start")[2]
    block = block.partition("# ai-template-meta-end")[0]
    pairs = (
        line.removeprefix("#").partition(":") for line in block.splitlines()
    )
    return {k.strip(): v.strip() for k, sep, v in pairs if sep and k.strip()}


@dataclass(frozen=True)
class Query:
    """What a search asks for, and how many references to return."""

    words: frozenset[str]
    limit: int

    @classmethod
    def parse(cls, text: object, limit: object = 5) -> Query:
        """A free-text query and a positive ``limit``."""
        if not isinstance(text, str):
            raise TypeError(f"query must be a str (got {type(text).__name__})")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError(f"limit must be a positive int (got {limit!r})")
        return cls(words(text), limit)
