"""The parsed semantic-token table and the parser of its shipped JSON file.

``semantic_tokens.json`` is the single source of the semantic token roles.
:func:`read_tokens` reads it once and returns either a :class:`TokenTable`
holding every role the accessors in :mod:`dartwork_mpl.tokens` need, or a
named refusal saying why the file cannot be used. Nothing here reads
``rcParams`` at resolution time; the accessors do that.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias, TypeVar, get_args

import matplotlib as mpl

TypeRole = Literal["annotation", "tick", "body", "label", "title", "emphasis"]
WeightRole = Literal["hairline", "reference", "trend", "emphasis"]
ScatterLevel = Literal["small", "default", "emphasis"]
SpacingLevel = Literal["xs", "sm", "md", "lg", "xl"]

_Key = TypeVar("_Key", bound=str)


@dataclass(frozen=True)
class RcToken:
    """A size resolved at call time as ``(rcParams[rcparam] + offset) * multiplier``.

    ``rcparam`` must name a matplotlib rcParam; construction rejects any other
    name with ``ValueError``.
    """

    rcparam: str
    offset: float
    multiplier: float

    def __post_init__(self) -> None:
        """Reject an ``rcparam`` matplotlib does not know."""
        if self.rcparam not in mpl.rcParams:
            raise ValueError(f"unknown rcParam {self.rcparam!r}")


@dataclass(frozen=True)
class TokenTable:
    """Every semantic token role, keyed by its role name.

    Each mapping holds exactly the names of its ``Literal`` key type, so an
    accessor's lookup of a known role cannot miss; construction rejects a
    missing or extra name with ``ValueError``.
    """

    version: str
    type_scale: Mapping[TypeRole, RcToken]
    lw_ladder: Mapping[WeightRole, RcToken]
    scatter_size: Mapping[ScatterLevel, float]
    spacing: Mapping[SpacingLevel, float]

    def __post_init__(self) -> None:
        """Reject a section whose names differ from its role set."""
        for section, keys, roles in (
            ("type_scale", self.type_scale, TypeRole),
            ("lw_ladder", self.lw_ladder, WeightRole),
            ("scatter_size", self.scatter_size, ScatterLevel),
            ("spacing", self.spacing, SpacingLevel),
        ):
            _require_exact_names(section, set(keys), get_args(roles))


@dataclass(frozen=True)
class TokenFileUnreadable:
    """The token file could not be read (missing, unreadable); ``detail`` says how."""

    path: Path
    detail: str


@dataclass(frozen=True)
class TokenFileMalformed:
    """The token file was read but is not a complete, valid token table; ``detail`` says where."""

    path: Path
    detail: str


TokenLoad: TypeAlias = TokenTable | TokenFileUnreadable | TokenFileMalformed


class _Reject(Exception):
    """Raised inside the parser only; :func:`parse_tokens` turns it into a refusal."""


def _require_exact_names(
    section: str, names: set[str], roles: tuple[str, ...]
) -> None:
    """Raise ``ValueError`` naming the missing and unexpected entries of ``section``."""
    missing = sorted(set(roles) - names)
    extra = sorted(names - set(roles))
    if missing or extra:
        raise ValueError(f"{section}: missing {missing}, unexpected {extra}")


def _number(value: object, where: str) -> float:
    """Return ``value`` as a float, accepting numbers and numeric strings.

    Raises ``_Reject`` for anything else.
    """
    if isinstance(value, (int, float, str)):
        try:
            return float(value)
        except ValueError:
            pass
    raise _Reject(f"{where}: expected a number, got {value!r}")


def _mapping(value: object, where: str) -> Mapping[str, object]:
    """Return ``value`` if it is a JSON object (string keys); raise ``_Reject`` otherwise."""
    if isinstance(value, dict) and all(isinstance(k, str) for k in value):
        return value
    raise _Reject(f"{where}: expected an object")


def _section(
    raw: Mapping[str, object], section: str, roles: tuple[_Key, ...]
) -> dict[_Key, object]:
    """Return ``raw[section]`` keyed by exactly ``roles``; raise ``_Reject`` otherwise."""
    if section not in raw:
        raise _Reject(f"missing section {section!r}")
    entries = _mapping(raw[section], section)
    try:
        _require_exact_names(section, set(entries), roles)
    except ValueError as exc:
        raise _Reject(str(exc)) from None
    return {role: entries[role] for role in roles}


def _rc_token(value: object, where: str) -> RcToken:
    """Parse one ``{"rcparam", "offset"?, "multiplier"?}`` entry; raise ``_Reject`` if invalid.

    A missing ``offset`` means ``0.0`` and a missing ``multiplier`` ``1.0``.
    """
    entry = _mapping(value, where)
    rcparam = entry.get("rcparam")
    if not isinstance(rcparam, str):
        raise _Reject(f"{where}.rcparam: expected a string")
    offset = _number(entry.get("offset", 0.0), f"{where}.offset")
    multiplier = _number(entry.get("multiplier", 1.0), f"{where}.multiplier")
    try:
        return RcToken(rcparam, offset, multiplier)
    except ValueError as exc:
        raise _Reject(f"{where}.rcparam: {exc}") from None


def parse_tokens(raw: object, path: Path) -> TokenTable | TokenFileMalformed:
    """Parse decoded token JSON into a :class:`TokenTable`, without I/O.

    Every section must hold exactly its role names; ``path`` only labels the
    refusal. Returns :class:`TokenFileMalformed` naming the first problem found.
    """
    try:
        top = _mapping(raw, "<root>")
        version = top.get("version")
        if not isinstance(version, str):
            raise _Reject("version: expected a string")
        type_scale = _section(top, "type_scale", get_args(TypeRole))
        lw_ladder = _section(top, "lw_ladder", get_args(WeightRole))
        scatter = _section(top, "scatter_size", get_args(ScatterLevel))
        spacing = _section(top, "spacing", get_args(SpacingLevel))
        return TokenTable(
            version=version,
            type_scale={
                role: _rc_token(entry, f"type_scale.{role}")
                for role, entry in type_scale.items()
            },
            lw_ladder={
                role: _rc_token(entry, f"lw_ladder.{role}")
                for role, entry in lw_ladder.items()
            },
            scatter_size={
                level: _number(size, f"scatter_size.{level}")
                for level, size in scatter.items()
            },
            spacing={
                level: _number(size, f"spacing.{level}")
                for level, size in spacing.items()
            },
        )
    except _Reject as exc:
        return TokenFileMalformed(path, str(exc))


def read_tokens(path: Path) -> TokenLoad:
    """Read and parse the token file at ``path`` (UTF-8 JSON).

    Returns the table, :class:`TokenFileUnreadable` when the file cannot be
    read, or :class:`TokenFileMalformed` when it is not valid JSON or not a
    complete table. Never raises for the file's state.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return TokenFileUnreadable(path, f"{type(exc).__name__}: {exc}")
    except UnicodeDecodeError as exc:
        return TokenFileMalformed(path, f"not UTF-8: {exc}")
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        return TokenFileMalformed(path, f"invalid JSON: {exc}")
    return parse_tokens(raw, path)
