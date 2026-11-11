"""Agent guidance names only what the runtime has (#677).

Agents in other projects read three shipped surfaces, then call the library:

* the skill (``skills/dartwork-mpl/SKILL.md`` and ``references/*.md``),
* the consumer entry (``dm.get_agent_doc("AGENTS")``),
* the prompt corpus (``dm.get_prompt(...)`` and the bundled templates).

A function, keyword or value that the guidance names and the runtime lacks
fails an agent on first use. Every oracle here is read from the runtime
(``getattr``, ``inspect.signature``, ``Literal`` annotations, the check and
lint registries, ``dm.__version__``), never from a second hand-written list.
Mentions are read from prose and inline code as well as fenced blocks.
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import re
import tomllib
import typing
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from types import UnionType
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
import pytest
from matplotlib.artist import ArtistInspector
from matplotlib.backend_bases import FigureCanvasBase
from matplotlib.legend import Legend
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.text import Text

import dartwork_mpl as dm
from dartwork_mpl.figure_review import Review
from dartwork_mpl.lint import load_rules
from dartwork_mpl.skills import skill_path
from dartwork_mpl.validate._checks import registered_checks
from dartwork_mpl.validate._orchestrator import CheckFailed, _outcome_warnings


@dataclass(frozen=True)
class Doc:
    """One guidance file: the surface it belongs to, its name and its text."""

    surface: str
    name: str
    text: str


def _documents() -> list[Doc]:
    """Every file of the three surfaces, read from the installed package."""
    skill = skill_path()
    docs = [
        Doc("skill", p.name, p.read_text(encoding="utf-8"))
        for p in [
            skill / "SKILL.md",
            *sorted((skill / "references").glob("*.md")),
        ]
    ]
    for name in ("AGENTS", "CLAUDE"):
        text = Path(dm.agent_doc_path(name)).read_text(encoding="utf-8")
        docs.append(Doc("agent", f"{name}.md", text))
    docs += [
        Doc("prompt", f"{name}", dm.get_prompt(name))
        for name in dm.list_prompts()
    ]
    templates = Path(dm.prompt_path("00-index")).parent / "05-templates"
    docs += [
        Doc("prompt", p.relative_to(templates).as_posix(), p.read_text("utf-8"))
        for p in sorted(templates.rglob("*.py"))
    ]
    return docs


DOCS = _documents()
PROMPT_DOCS = [d for d in DOCS if d.surface == "prompt"]
_REJECTED = re.compile(r"\b(?:rejects?|rejected|raises?)\b", re.I)
_PLACEHOLDER = re.compile(r"\.\.\.|…|<[a-z_]+>")


@dataclass(frozen=True)
class Call:
    """A ``dm.<dotted>(...)`` mention: the positional arguments' source (or
    ``None`` where not a plain literal) and the keywords' source text."""

    doc: Doc
    dotted: str
    positional: tuple[str, ...]
    keywords: tuple[tuple[str, str], ...]
    context: str = ""

    @property
    def where(self) -> str:
        """``surface/file: dm.name(...)`` for failure messages."""
        return f"{self.doc.surface}/{self.doc.name}: dm.{self.dotted}(...)"


def _call_text(text: str, start: int) -> str | None:
    """The text between the parenthesis opening at ``start - 1`` and its match,
    or ``None`` when the mention is not closed (a prose fragment)."""
    depth, quote, i = 1, None, start
    while i < len(text) and depth:
        char = text[i]
        if quote:
            quote = None if char == quote else quote
        elif char in "\"'":
            quote = char
        elif char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        i += 1
    return text[start : i - 1] if depth == 0 else None


def _calls(docs: list[Doc]) -> Iterator[Call]:
    """Every closed ``dm.<dotted>(...)`` mention, with its arguments where they
    parse as Python and its bare ``keyword=`` names where they do not."""
    for doc in docs:
        for match in re.finditer(r"\bdm\.([A-Za-z_][\w.]*)\(", doc.text):
            inner = _call_text(doc.text, match.end())
            if inner is None:
                continue
            line = doc.text.count("\n", 0, match.start())
            context = "\n".join(doc.text.splitlines()[line : line + 2])
            try:
                node = ast.parse(f"f({inner})", mode="eval").body
            except SyntaxError:
                # Shorthand such as ``dm.figsize_for(nrows=, ncols=)``: no
                # positional or value information, but the keywords count.
                bare = re.sub(r"\"[^\"]*\"|'[^']*'", "", inner)
                names = re.findall(r"(?<![=!<>\w])(\w+)\s*=(?!=)", bare)
                keywords = tuple((name, "") for name in names)
                yield Call(doc, match.group(1), (), keywords, context)
                continue
            assert isinstance(node, ast.Call)
            positional: list[str] = []
            for arg in node.args:
                if isinstance(arg, ast.Starred):
                    break
                positional.append(
                    ast.get_source_segment(f"f({inner})", arg) or ""
                )
            keywords = tuple(
                (kw.arg, ast.get_source_segment(f"f({inner})", kw.value) or "")
                for kw in node.keywords
                if kw.arg is not None
            )
            yield Call(
                doc, match.group(1), tuple(positional), keywords, context
            )


def _resolve(dotted: str) -> Any:
    """``dm.<dotted>`` as the package defines it (``AttributeError`` if not)."""
    target: Any = dm
    for part in dotted.split("."):
        target = getattr(target, part)
    return target


def _literal(source: str) -> tuple[bool, Any]:
    """Whether ``source`` is a plain literal (no placeholder), and its value."""
    if _PLACEHOLDER.search(source):
        return False, None
    try:
        return True, ast.literal_eval(source)
    except (ValueError, SyntaxError):
        return False, None


# ---------------------------------------------------------------- (a) names


def _removal_message(name: str) -> str | None:
    """The runtime's own ``removed in`` message for a retired top-level name."""
    try:
        getattr(dm, name)
    except AttributeError as error:
        return str(error) if "was removed in" in str(error) else None
    return None


@pytest.mark.parametrize("doc", PROMPT_DOCS, ids=lambda d: d.name)
def test_prompt_corpus_dm_names_exist_or_are_announced_removals(
    doc: Doc,
) -> None:
    """Every ``dm.<name>`` the prompt corpus mentions (prose, inline code,
    fences, lint messages) resolves, or is a name the package itself reports
    as removed, so a retired helper is only ever named as retired."""
    names = {
        n.rstrip(".") for n in re.findall(r"\bdm\.[A-Za-z_][\w.]*", doc.text)
    }
    broken: list[str] = []
    for dotted in sorted(names):
        parts = dotted.split(".")[1:]
        try:
            _resolve(".".join(parts))
        except AttributeError:
            if not _removal_message(parts[0]):
                broken.append(dotted)
    assert not broken, f"{doc.name} names missing dm attributes: {broken}"


# ------------------------------------------------------------- (b) keywords


def _artist_property_names() -> set[str]:
    """Property names matplotlib accepts as artist or savefig keywords."""
    names: set[str] = set()
    for cls in (Text, Legend, Line2D, Patch):
        inspector = ArtistInspector(cls)
        names |= {s.removeprefix("set_") for s in inspector.get_setters()}
        names |= {
            a for aliases in inspector.get_aliases().values() for a in aliases
        }
    names |= set(inspect.signature(FigureCanvasBase.print_figure).parameters)
    for cls in (Text, Legend):  # constructor keywords such as ``frameon=``
        names |= set(inspect.signature(cls.__init__).parameters)
    return names - {"self", "args", "kwargs"}


def _forwarded_keyword_ok(dotted: str, keyword: str) -> bool:
    """Whether ``keyword`` is accepted by what ``dm.<dotted>``'s ``**kwargs``
    forwards to: the config fields, the rcParams, or matplotlib's properties."""
    if dotted == "config.override":
        return keyword in {f.name for f in dataclasses.fields(dm.config)}
    if dotted in ("style.use", "style.context"):
        rc = mpl.rcParams
        return (
            keyword in rc
            or keyword.replace("_", ".") in rc
            or any(k.replace(".", "_") == keyword for k in rc)
        )
    return keyword in _artist_property_names()


def _parameter_names(signature: inspect.Signature) -> list[str]:
    """Positional-capable parameter names in call order."""
    return [
        p.name
        for p in signature.parameters.values()
        if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
    ]


def test_keywords_in_dm_calls_exist_in_the_real_signature() -> None:
    """Every ``dm.<name>(...)`` call the three surfaces show, in prose, inline
    code or fences, binds to the real signature: no unknown keyword, no extra
    positional argument; a keyword only ``**kwargs`` could take must be a
    property of what it forwards to (config field, rcParam, matplotlib)."""
    problems: list[str] = []
    checked = 0
    for call in _calls(DOCS):
        try:
            target = _resolve(call.dotted)
            signature = inspect.signature(target)
        except (AttributeError, TypeError, ValueError):
            continue  # a removed or non-callable name: the names tests own it
        checked += 1
        accepts_any = any(
            p.kind is p.VAR_KEYWORD for p in signature.parameters.values()
        )
        try:
            signature.bind_partial(
                *[None] * len(call.positional),
                **{
                    k: None
                    for k, _ in call.keywords
                    if k in signature.parameters
                },
            )
        except TypeError as error:
            problems.append(f"{call.where}: {error}")
        for keyword, _ in call.keywords:
            if keyword in signature.parameters:
                continue
            if not accepts_any or not _forwarded_keyword_ok(
                call.dotted, keyword
            ):
                problems.append(f"{call.where}: unknown keyword {keyword}=")
    assert checked > 150, "call extraction found too few calls; format changed?"
    assert not problems, "\n".join(sorted(set(problems)))


def _callable_parameters(member: Any) -> set[str]:
    """Parameter names of ``member``, or none when it has no signature."""
    try:
        return set(inspect.signature(member).parameters)
    except (TypeError, ValueError):
        return set()


def _public_keyword_names() -> set[str]:
    """Every name a prose ``keyword=`` can honestly refer to: parameters of the
    public ``dm`` callables, of ``dm.style`` and ``dm.config``, and of
    ``matplotlib.pyplot``; config and review-report fields; rcParam leaf names
    (``scale_dashes``); matplotlib's artist and savefig properties."""
    names = _artist_property_names()
    names |= {f.name for f in dataclasses.fields(dm.config)}
    names |= {f.name for f in dataclasses.fields(Review)}
    names |= {rc.rsplit(".", 1)[-1] for rc in mpl.rcParams}
    for owner in (dm, dm.style, dm.config, plt):
        for member_name in dir(owner):
            if not member_name.startswith("_"):
                names |= _callable_parameters(getattr(owner, member_name))
    return names


@pytest.mark.parametrize(
    "doc",
    [d for d in DOCS if not d.name.endswith(".py")],
    ids=lambda d: f"{d.surface}:{d.name}",
)
def test_bare_keywords_in_inline_code_are_real_parameters(doc: Doc) -> None:
    """A keyword written alone in inline code (``where=``, ``fit_labels=False``,
    ``tick_years=4``), outside any ``dm.name(...)`` call, is a parameter of
    some public ``dm`` callable, a config field, or a matplotlib property, so
    a renamed or invented keyword cannot linger in prose."""
    known = _public_keyword_names()
    seen = {
        m.group(1) for m in re.finditer(r"`([a-z][a-z_0-9]*)=[^`]*`", doc.text)
    }
    assert not seen - known, (
        f"{doc.name}: unknown keywords {sorted(seen - known)}"
    )


# ---------------------------------------------------------------- (c) values


def _literal_choices(annotation: Any) -> set[tuple[type, Any]] | None:
    """The closed set of values an annotation allows, or ``None`` when it is
    open (anything but ``Literal`` members and ``None``)."""
    members = (
        typing.get_args(annotation)
        if typing.get_origin(annotation) in (typing.Union, UnionType)
        else (annotation,)
    )
    choices: set[tuple[type, Any]] = set()
    for member in members:
        if member is type(None):
            choices.add((type(None), None))
        elif typing.get_origin(member) is typing.Literal:
            choices |= {(type(v), v) for v in typing.get_args(member)}
        else:
            return None
    return choices


def _annotation(target: Any, parameter: str) -> Any:
    """``parameter``'s annotation evaluated in the function's module, or
    ``inspect.Parameter.empty`` when it cannot be evaluated here."""
    signature = inspect.signature(target)
    annotation = signature.parameters[parameter].annotation
    if isinstance(annotation, str):
        namespace = dict(vars(typing)) | dict(
            getattr(inspect.unwrap(target), "__globals__", {})
        )
        try:
            return eval(annotation, namespace)
        except Exception:
            return inspect.Parameter.empty
    return annotation


def _allowed_values(call: Call, parameter: str) -> set[tuple[type, Any]] | None:
    """Closed value set for ``parameter`` of the called function, if any."""
    if call.dotted == "config.override":
        hints = typing.get_type_hints(type(dm.config))
        return (
            _literal_choices(hints[parameter]) if parameter in hints else None
        )
    target = _resolve(call.dotted)
    if parameter not in inspect.signature(target).parameters:
        return None
    annotation = _annotation(target, parameter)
    if annotation is inspect.Parameter.empty:
        return None
    return _literal_choices(annotation)


def _literal_arguments(call: Call) -> Iterator[tuple[str, Any]]:
    """``(parameter, value)`` for each literal argument of ``call``."""
    try:
        names = _parameter_names(inspect.signature(_resolve(call.dotted)))
    except (AttributeError, TypeError, ValueError):
        names = []
    for index, source in enumerate(call.positional):
        ok, value = _literal(source)
        if ok and index < len(names):
            yield names[index], value
    for keyword, source in call.keywords:
        ok, value = _literal(source)
        if ok:
            yield keyword, value


def test_literal_values_in_dm_calls_are_in_the_declared_choices() -> None:
    """A string, bool or number the guidance passes to a parameter annotated
    with ``Literal[...]`` (``where=``, ``sign=``, ``config.override`` fields,
    ``axis=``) is one of that annotation's values."""
    problems: list[str] = []
    seen = 0
    for call in _calls(DOCS):
        try:
            _resolve(call.dotted)
        except AttributeError:
            continue
        for parameter, value in _literal_arguments(call):
            allowed = _allowed_values(call, parameter)
            if allowed is None:
                continue
            seen += 1
            if (type(value), value) not in allowed:
                shown = sorted(repr(v) for _, v in allowed)
                problems.append(
                    f"{call.where}: {parameter}={value!r} not in {shown}"
                )
    assert seen > 10, "no Literal-typed arguments found; format changed?"
    assert not problems, "\n".join(sorted(set(problems)))


def test_preset_names_passed_to_the_style_api_exist() -> None:
    """``dm.style.use("x")`` / ``dm.style.context("x")`` in any surface names a
    preset in ``dm.style.presets`` (the registry the call itself consults)."""
    problems: list[str] = []
    seen = 0
    for call in _calls(DOCS):
        if (
            call.dotted not in ("style.use", "style.context")
            or not call.positional
        ):
            continue
        ok, value = _literal(call.positional[0])
        if not ok or value == "preset":  # "preset" is a placeholder word
            continue
        seen += 1
        for name in [value] if isinstance(value, str) else list(value):
            if name not in dm.style.presets:
                problems.append(f"{call.where}: preset {name!r}")
    assert seen > 5
    assert not problems, "\n".join(sorted(set(problems)))


def test_literal_arguments_of_pure_dm_helpers_evaluate() -> None:
    """The size and lookup helpers are pure: a literal call the guidance shows
    (``dm.figsize("13cm", "wide")``, ``dm.figsize_for("full_slide")``,
    ``dm.get_agent_doc("AGENTS")``, ``dm.find_template(..., tier="all")``)
    runs without raising, so a retired token or kind cannot be taught. A call
    shown next to "rejected" / "raises" must raise."""
    pure = {
        "figsize",
        "figsize_for",
        "figsize_grid",
        "grid_shape",
        "get_agent_doc",
        "get_prompt",
        "find_template",
    }
    problems: list[str] = []
    executed = 0
    for call in _calls(DOCS):
        if call.dotted not in pure:
            continue
        values = [_literal(s) for s in call.positional]
        values += [_literal(s) for _, s in call.keywords]
        if not all(ok for ok, _ in values):
            continue
        args = [v for _, v in values[: len(call.positional)]]
        kwargs = {
            k: v
            for (k, _), (_, v) in zip(
                call.keywords, values[len(call.positional) :], strict=True
            )
        }
        rejected = bool(_REJECTED.search(call.context))
        try:
            _resolve(call.dotted)(*args, **kwargs)
        except Exception as error:
            if not rejected:
                problems.append(f"{call.where}{args}{kwargs}: {error!r}")
        else:
            if rejected:
                problems.append(
                    f"{call.where}{args}{kwargs}: shown as rejected but runs"
                )
        executed += 1
    assert executed > 15, "too few literal helper calls; format changed?"
    assert not problems, "\n".join(sorted(set(problems)))


def test_legend_sides_passed_to_the_legend_helpers_are_accepted() -> None:
    """``loc=`` literals the guidance gives ``dm.place_legend`` and
    ``dm.figure_legend`` (``"above"``, ``"below"``, ``"right"`` ...) are
    accepted by the real helper on a labelled line."""
    problems: list[str] = []
    seen = 0
    for call in _calls(DOCS):
        if call.dotted not in ("place_legend", "figure_legend"):
            continue
        for keyword, source in call.keywords:
            ok, value = _literal(source)
            if keyword != "loc" or not ok:
                continue
            seen += 1
            fig, ax = plt.subplots()
            ax.plot([0, 1], [0, 1], label="a")
            try:
                if call.dotted == "place_legend":
                    dm.place_legend(ax, loc=value)
                else:
                    dm.figure_legend(fig, loc=value)
            except Exception as error:
                problems.append(f"{call.where}: loc={value!r}: {error!r}")
            finally:
                plt.close(fig)
    assert seen > 3
    assert not problems, "\n".join(sorted(set(problems)))


def _check_ids() -> set[str]:
    """Every id ``validate_figure`` can report: the registry's, plus the one
    it reports itself when a check cannot run."""
    emitted = _outcome_warnings(CheckFailed("probe"))
    return {c.check_id for c in registered_checks()} | {
        w.check_id for w in emitted
    }


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: f"{d.surface}:{d.name}")
def test_validate_check_ids_in_guidance_are_reported_by_the_runtime(
    doc: Doc,
) -> None:
    """An ALL_CAPS finding id the guidance names (``LEGEND_OVERLAP``,
    ``CHECK_FAILED`` ...) is one ``dm.validate_figure`` reports, unless it is
    written as an attribute (``dm.INSTALL_TARGETS``, a removed name)."""
    ids = _check_ids()
    named = set(
        re.findall(
            r"(?<!dm\.)\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b(?!\*)", doc.text
        )
    )
    named -= {n for n in named if _removal_message(n)}  # INSTALL_TARGETS
    named -= {n for n in named if re.search(rf"dm\.{n}\b", doc.text)}
    assert not named - ids, f"{doc.name}: {sorted(named - ids)}"


def _known_kebab_words() -> set[str]:
    """Hyphenated words that are not lint rules: presets, prompt ids, the
    console scripts ``pyproject.toml`` declares."""
    # pyproject.toml, not installed metadata: the test bootstrap installs a
    # metadata stub without entry points (tests/architecture/test_test_bootstrap).
    pyproject = tomllib.loads(
        (Path(__file__).resolve().parents[2] / "pyproject.toml").read_text(
            "utf-8"
        )
    )
    scripts = set(pyproject["project"]["scripts"])
    return set(dm.style.presets) | set(dm.list_prompts()) | scripts


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: f"{d.surface}:{d.name}")
def test_lint_rule_ids_in_guidance_are_in_the_catalog(doc: Doc) -> None:
    """A backticked hyphenated id the guidance names (``oversize-width``,
    ``jet-cmap`` ...) is a rule in the bundled anti-pattern catalog, unless it
    is a preset, a prompt id, an installed command or an output stem
    (``figure-v2``)."""
    rules = {r.id for r in load_rules()}
    words = set(re.findall(r"`([a-z][a-z0-9]*(?:-[a-z0-9]+)+)`", doc.text))
    words = {w for w in words if not re.search(r"-v\d+$", w)}
    unknown = words - rules - _known_kebab_words()
    assert not unknown, f"{doc.name}: not lint rules: {sorted(unknown)}"


# --------------------------------------------------------------- (d) version

_CLAIM = re.compile(
    r"(?i:removed|retired|renamed|deprecated|since|version|introduced)"
    r"[^.\n]{0,30}?\bv?(\d+\.\d+(?:\.\d+)?)\b"
)


def _release(version: str) -> tuple[int, ...]:
    """``"0.5.4"`` as ``(0, 5, 4)``."""
    return tuple(int(part) for part in version.split("."))


def _refines(claimed: str, recorded: str) -> bool:
    """Whether ``claimed`` ("0.4.0") is ``recorded`` ("0.4") or an extension."""
    return _release(claimed)[: len(_release(recorded))] == _release(recorded)


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: f"{d.surface}:{d.name}")
def test_version_claims_in_guidance_match_the_runtime(doc: Doc) -> None:
    """A release the guidance cites (``removed in 0.5.4``) is not newer than
    ``dm.__version__``; where the same paragraph names a removed ``dm.<name>``
    the package reports, the cited release is the one it reports; and the
    package is never pinned to another version (``dartwork-mpl 0.4``)."""
    current = _release(dm.__version__)
    problems: list[str] = []
    for paragraph in re.split(r"\n\s*\n", doc.text):
        reported = {
            name: re.search(r"removed in (\d+(?:\.\d+)*)", message).group(1)  # type: ignore[union-attr]
            for name in re.findall(r"\bdm\.([A-Za-z_]\w*)", paragraph)
            if (message := _removal_message(name))
        }
        for claim in _CLAIM.finditer(paragraph):
            version = claim.group(1)
            if _release(version) > current:
                problems.append(f"{version} is newer than {dm.__version__}")
            for name, recorded in reported.items():
                if not _refines(version, recorded):
                    problems.append(
                        f"{version} cited for dm.{name}; runtime says {recorded}"
                    )
    for pin in re.findall(
        r"dartwork[-_]mpl[ =>~]+v?(\d+\.\d+(?:\.\d+)?)", doc.text
    ):
        if not _refines(dm.__version__, pin):
            problems.append(
                f"pins dartwork-mpl {pin}; runtime is {dm.__version__}"
            )
    assert not problems, f"{doc.name}: {problems}"
