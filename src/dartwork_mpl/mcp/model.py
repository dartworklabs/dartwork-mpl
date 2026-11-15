"""The MCP slice's types, and the one place tool arguments and child output become them.

Searching: a :class:`Query` over :class:`Entry` items of one :class:`Kind`.
Rendering: a :class:`RenderRequest` (the parsed ``render`` arguments), the
:class:`FigureFacts` a child sees after the code ran, the :class:`ChildRun`
the parent sees afterwards, and the :data:`Outcome` variant that run ended
in. The bundle on disk is described by :class:`Report` and
:class:`Manifest` (schema ``dartwork-mpl.bundle``, version
:data:`BUNDLE_VERSION`); both serialise with ``to_json``.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

# -- limits -------------------------------------------------------------------

MAX_SOURCE_BYTES = 256 * 1024  # a plotting script is a few hundred lines
MAX_TIMEOUT = 120.0
DEFAULT_TIMEOUT = 20.0
MAX_LOG_BYTES = 64 * 1024  # stdout and stderr each, as quoted in the report
MAX_FILE_BYTES = 64 * 1024 * 1024  # any file the child writes (RLIMIT_FSIZE)
MAX_ADDRESS_SPACE = 4 * 1024**3  # RLIMIT_AS where the platform enforces it
MAX_INPUTS = 32

BUNDLE_SCHEMA = "dartwork-mpl.bundle"
BUNDLE_VERSION = 1
FIGURE_FILES = ("figure.png", "figure.pdf")
BUNDLE_FILES = (*FIGURE_FILES, "source.py", "report.json", "manifest.json")

_IDENTIFIER = re.compile(r"[A-Za-z_]\w*")
_WORD = re.compile(r"[a-z0-9]+")


def words(text: str) -> frozenset[str]:
    """The lower-case words of ``text``, a plural ``s`` dropped (bars → bar)."""
    return frozenset(
        w[:-1] if len(w) > 3 and w.endswith("s") else w
        for w in _WORD.findall(text.lower())
    )


# -- references -----------------------------------------------------------------


class Kind(StrEnum):
    """What a reference is: a template script, a style preset, a colour, a lint rule."""

    TEMPLATE = "template"
    PRESET = "preset"
    COLOR = "color"
    RULE = "rule"

    @classmethod
    def parse(cls, text: object) -> Kind:
        """One kind name; anything else raises ``ValueError`` listing them."""
        try:
            return cls(str(text).strip().lower().removesuffix("s"))
        except ValueError:
            raise ValueError(
                f"kind must be one of {[k.value for k in cls]} (got {text!r})"
            ) from None


@dataclass(frozen=True)
class Entry:
    """One reference a search can return: its id, one line about it, its words."""

    kind: Kind
    id: str
    summary: str
    words: frozenset[str]

    def to_json(self) -> dict[str, str]:
        """``{"kind", "id", "summary"}``."""
        return {"kind": self.kind.value, "id": self.id, "summary": self.summary}


Entries = tuple[Entry, ...]

# The purposes the skill's preset table names, so "slides" finds a preset.
PRESET_PURPOSES = {
    "scientific": "paper journal thesis publication",
    "report": "report document dashboard",
    "presentation": "talk slides deck",
    "poster": "poster large",
    "web": "web page screen",
    "dark": "dark background screen",
    "minimal": "minimal sparse",
}


@dataclass(frozen=True)
class Query:
    """A search: its words, the kind it is narrowed to, how many hits per kind."""

    words: frozenset[str]
    kind: Kind | None
    limit: int = 5

    @classmethod
    def parse(cls, text: object, kind: object = None) -> Query:
        """A non-empty free-text query and an optional kind."""
        if not isinstance(text, str) or not words(text):
            raise ValueError(f"query must name what you need (got {text!r})")
        return cls(words(text), None if kind is None else Kind.parse(kind))


# -- render request --------------------------------------------------------------


@dataclass(frozen=True)
class RenderRequest:
    """The parsed ``render`` arguments; paths stay strings until the shell."""

    code: str
    figure_var: str = "fig"
    timeout: float = DEFAULT_TIMEOUT
    out_dir: str | None = None
    inputs: tuple[str, ...] = ()

    @classmethod
    def parse(
        cls,
        code: object,
        figure_var: object = "fig",
        timeout: object = DEFAULT_TIMEOUT,
        out_dir: object = None,
        inputs: object = None,
    ) -> RenderRequest:
        """Check every argument before anything runs; a bad one raises ``ValueError``."""
        if not isinstance(code, str):
            raise ValueError(f"code must be a str (got {type(code).__name__})")
        if len(code.encode("utf-8", "surrogatepass")) > MAX_SOURCE_BYTES:
            raise ValueError(f"code is over {MAX_SOURCE_BYTES // 1024} KiB")
        if not isinstance(figure_var, str) or not _IDENTIFIER.fullmatch(
            figure_var
        ):
            raise ValueError(f"figure_var must be a name (got {figure_var!r})")
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, int | float)
            or not math.isfinite(timeout)
            or not 0 < timeout <= MAX_TIMEOUT
        ):
            raise ValueError(f"timeout must be in (0, {MAX_TIMEOUT:g}] seconds")
        if out_dir is not None and (
            not isinstance(out_dir, str) or not out_dir
        ):
            raise ValueError("out_dir must be a directory path")
        if inputs is not None and not isinstance(inputs, list | tuple):
            raise ValueError("inputs must be a list of file paths")
        paths = [] if inputs is None else list(cast("list[object]", inputs))
        if not all(isinstance(p, str) and p for p in paths):
            raise ValueError("inputs must be a list of file paths")
        if len(paths) > MAX_INPUTS:
            raise ValueError(f"at most {MAX_INPUTS} inputs")
        return cls(
            code, figure_var, float(timeout), out_dir, tuple(map(str, paths))
        )


# -- inside the child: which figure to save ---------------------------------------


class Pick(StrEnum):
    """Which figure the child saves."""

    NAMED = "named"  # the object bound to figure_var
    CURRENT = "current"  # pyplot's current figure (plt.gcf())
    NONE = "none"


@dataclass(frozen=True)
class FigureFacts:
    """After the code ran: is ``figure_var`` a Figure, how many pyplot figures are open."""

    named: bool
    open: int


@dataclass(frozen=True)
class FigureChoice:
    """The figure to save, and a note for the report when it was a guess."""

    pick: Pick
    note: str | None = None


# -- after the child: how the run ended --------------------------------------------


@dataclass(frozen=True)
class CheckFinding:
    """One figure-checker finding, as the report quotes it."""

    id: str
    severity: str
    message: str


@dataclass(frozen=True)
class Canvas:
    """The saved figure's size in inches and the PNG's pixels."""

    width_in: float
    height_in: float
    width_px: int = 0
    height_px: int = 0


@dataclass(frozen=True)
class Rendered:
    """The figure was saved and checked."""

    canvas: Canvas
    findings: tuple[CheckFinding, ...]
    notes: tuple[str, ...] = ()
    status: str = "rendered"


@dataclass(frozen=True)
class LintBlocked:
    """A critical lint finding stopped the run before any code executed."""

    status: str = "lint_blocked"


@dataclass(frozen=True)
class NoFigure:
    """The code ran but left no figure to save."""

    figure_var: str
    status: str = "no_figure"


@dataclass(frozen=True)
class Raised:
    """The code raised; ``error`` is the traceback's tail."""

    error: str
    status: str = "raised"


@dataclass(frozen=True)
class TimedOut:
    """The run passed its timeout and its process group was killed."""

    timeout: float
    status: str = "timed_out"


@dataclass(frozen=True)
class Crashed:
    """The child ended without a result: a resource limit or a hard exit."""

    returncode: int
    status: str = "crashed"


Outcome = Rendered | LintBlocked | NoFigure | Raised | TimedOut | Crashed


@dataclass(frozen=True)
class ChildRun:
    """What the parent knows after the child ended: the clock, the exit, the result."""

    timeout: float
    timed_out: bool
    returncode: int
    result: Rendered | NoFigure | Raised | None

    @staticmethod
    def parse_result(text: str | None) -> Rendered | NoFigure | Raised | None:
        """The child's ``result.json``; missing or malformed reads as no result."""
        try:
            data = cast("dict[str, Any]", json.loads(text or "null"))
            status = data["status"]
            if status == "no_figure":
                return NoFigure(str(data["figure_var"]))
            if status == "raised":
                return Raised(str(data["error"])[-MAX_LOG_BYTES:])
            if status != "rendered":
                return None
            canvas = cast("dict[str, float]", data["canvas"])
            found = cast("list[dict[str, str]]", data["findings"])
            return Rendered(
                canvas=Canvas(
                    float(canvas["width_in"]), float(canvas["height_in"])
                ),
                findings=tuple(
                    CheckFinding(f["id"], f["severity"], f["message"])
                    for f in found
                ),
                notes=tuple(str(n) for n in cast("list[str]", data["notes"])),
            )
        except (ValueError, KeyError, TypeError):
            return None


# -- the bundle ------------------------------------------------------------------


@dataclass(frozen=True)
class Log:
    """The head of one output stream, and whether it was cut."""

    text: str = ""
    truncated: bool = False


@dataclass(frozen=True)
class LintFinding:
    """One lint finding, as the report quotes it."""

    rule_id: str
    severity: str
    line: int
    message: str
    fix: str | None


Lint = tuple[LintFinding, ...]


@dataclass(frozen=True)
class Report:
    """``report.json``: how the run ended, the lint, the check, the logs."""

    outcome: Outcome
    lint: Lint
    stdout: Log = Log()
    stderr: Log = Log()
    limits: dict[str, int | None] = field(default_factory=dict)

    def to_json(self) -> dict[str, object]:
        """The report as JSON-ready data; ``status`` names the outcome."""
        details = {
            k: v
            for k, v in _plain(self.outcome).items()
            if k not in {"status", "canvas"}
        }
        return {
            "status": self.outcome.status,
            **details,
            "lint": [_plain(f) for f in self.lint],
            "stdout": _plain(self.stdout),
            "stderr": _plain(self.stderr),
            "limits": self.limits,
        }


@dataclass(frozen=True)
class FileDigest:
    """One file of the bundle (or an input): its path, SHA-256 and size."""

    path: str
    sha256: str
    bytes: int


@dataclass(frozen=True)
class Manifest:
    """``manifest.json``, the contract a hub ingests a bundle by.

    ``files`` lists every bundle file but the manifest itself, by name
    relative to the bundle; ``inputs`` the data files the caller declared, by
    the path given (hashed, never copied). ``canvas`` is ``None`` unless the
    run rendered. Fields are only added under a new :data:`BUNDLE_VERSION`.
    """

    status: str
    created: str
    seconds: float
    versions: dict[str, str]
    files: tuple[FileDigest, ...]
    inputs: tuple[FileDigest, ...] = ()
    canvas: Canvas | None = None
    schema: str = BUNDLE_SCHEMA
    version: int = BUNDLE_VERSION

    def to_json(self) -> dict[str, object]:
        """The manifest as JSON-ready data."""
        return _plain(self)


def _plain(value: DataclassInstance) -> dict[str, object]:
    """A frozen dataclass as a dict, nested ones and tuples included."""
    return asdict(value)
