"""Pure judging: read a transcript, prove isolation, decide a run's verdict.

Nothing here runs ``claude`` or matplotlib. Inputs are the stream-json lines
of one run and the facts the probe measured; outputs are plain data.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from .shelltrace import inside

SKILL = "dartwork-mpl"
SCRIPT_TOOLS = ("Bash", "Read", "Write", "Edit")
ARMS = ("bare", "skill")
VERDICTS = ("OK", "DEFECT", "NO_FIGURE", "INVALID", "NOTRUN")
# A re-render equals the agent's figure up to this RMS (0..255), as in tests/visual.
SAME_PICTURE_RMS = 0.5
SHARED_TEMP = re.compile(r"(?<![\w.$-])(?:/private)?/(?:var/)?tmp/[\w.+-]+")


@dataclass(frozen=True)
class Arm:
    """What one arm loads: built-in tools and the skill."""

    name: str
    tools: tuple[str, ...]
    skill: bool


ARM_SPECS = {
    "bare": Arm("bare", SCRIPT_TOOLS, skill=False),
    "skill": Arm("skill", (*SCRIPT_TOOLS, "Skill"), skill=True),
}


@dataclass
class Trace:
    """What one ``claude -p`` stream says happened."""

    init: dict[str, Any] | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)
    results: dict[str, dict[str, Any]] = field(default_factory=dict)
    result: dict[str, Any] | None = None

    @property
    def tool_names(self) -> list[str]:
        """Tool names in call order."""
        return [str(c.get("name")) for c in self.calls]


def parse_stream(lines: list[str]) -> Trace:
    """Collect the init event, tool calls, tool results and the result event."""
    trace = Trace()
    for line in lines:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        ev: dict[str, Any] = event
        kind = ev.get("type")
        if kind == "system" and ev.get("subtype") == "init":
            trace.init = ev
        elif kind in ("assistant", "user"):
            content = (ev.get("message") or {}).get("content") or []
            for block in content if isinstance(content, list) else []:
                if not isinstance(block, dict):
                    continue
                b: dict[str, Any] = block
                if b.get("type") == "tool_use":
                    trace.calls.append(b)
                elif b.get("type") == "tool_result":
                    trace.results[str(b.get("tool_use_id"))] = b
        elif kind == "result":
            trace.result = ev
    return trace


def isolation_problems(init: dict[str, Any] | None, arm: Arm) -> list[str]:
    """Why the session was not exactly our skill and the arm's tools (empty: isolated)."""
    if init is None:
        return ["no init event in the stream"]
    problems: list[str] = []
    servers = [
        (s.get("name"), s.get("status")) for s in init.get("mcp_servers") or []
    ]
    if servers:
        problems.append(f"mcp_servers {servers}, expected none")
    skills = list(init.get("skills") or [])
    want_skills = [SKILL] if arm.skill else []
    if skills != want_skills:
        problems.append(f"skills {skills}, expected {want_skills}")
    plugins = [p.get("name") for p in init.get("plugins") or []]
    if plugins:
        problems.append(f"plugins loaded: {plugins}")
    tools, want = set(init.get("tools") or []), set(arm.tools)
    if tools != want:
        extra = sorted(tools - want)
        missing = sorted(want - tools)
        problems.append(f"tools differ: extra {extra}, missing {missing}")
    return problems


def missing_facts(expect: dict[str, Any], figure: dict[str, Any]) -> list[str]:
    """Each required fact the measured figure lacks."""
    missing: list[str] = []
    panels = expect.get("panels")
    if panels is not None and figure.get("panels") != panels:
        missing.append(f"panels: {figure.get('panels')}, expected {panels}")
    marks = set(figure.get("marks") or [])
    missing.extend(
        f"no {m} marks" for m in expect.get("marks") or [] if m not in marks
    )
    # Wrapped labels ("Samsung\nInternet") still name the category.
    texts = " | ".join(
        " ".join(str(t).split()) for t in figure.get("texts") or []
    ).casefold()
    missing.extend(
        f"text {t!r} not on the figure"
        for t in expect.get("texts") or []
        if str(t).casefold() not in texts
    )
    any_text = [str(t) for t in expect.get("any_text") or []]
    if any_text and not any(t.casefold() in texts for t in any_text):
        missing.append(f"none of {any_text} on the figure")
    if expect.get("legend") and not figure.get("legend"):
        missing.append("no legend")
    return missing


def strays(paths: list[str], commands: list[str], root: str) -> list[str]:
    """Places outside the run's root that the session worked in.

    ``paths`` are the files it wrote or ran by absolute path; ``commands``
    are searched for the shared temp folders (``/tmp/s``), where concurrent
    runs overwrite each other.
    """
    found = {p for p in paths if p.startswith("/") and not inside(p, root)}
    for command in commands:
        found |= {
            m for m in SHARED_TEMP.findall(command) if not inside(m, root)
        }
    return sorted(found)


def reproduction(
    size: tuple[int, int],
    renders: list[dict[str, Any]],
    rerun_rms: float | None = None,
) -> str | None:
    """Why no re-rendered image is the agent's figure (``None``: one is).

    ``renders`` are the images the re-run wrote: ``size`` in pixels and
    ``rms`` against the figure where the sizes agree. ``rerun_rms`` is how
    far a second re-run landed from the first, measured when neither is
    the figure: apart, the script itself draws differently each time.
    """
    if not renders:
        return "re-running it wrote no image to compare with figure.png"
    close = [r["rms"] for r in renders if r.get("rms") is not None]
    if not close:
        drawn = ", ".join(
            sorted({"x".join(map(str, r["size"])) for r in renders})
        )
        return (
            f"it does not reproduce figure.png: it draws {drawn} px, "
            f"the figure is {size[0]}x{size[1]} px"
        )
    if min(close) <= SAME_PICTURE_RMS:
        return None
    if rerun_rms is not None and rerun_rms > SAME_PICTURE_RMS:
        return (
            "the script does not draw the same figure twice (two re-runs "
            f"differ by RMS {rerun_rms:.2f}), so figure.png cannot be "
            "reproduced: its randomness is not seeded"
        )
    return (
        "it does not reproduce figure.png: the closest re-render "
        f"differs by RMS {min(close):.2f} (same picture: {SAME_PICTURE_RMS})"
    )


@dataclass
class Evidence:
    """Everything the verdict reads about one run."""

    isolation: list[str] = field(default_factory=list)
    harness_error: str | None = None
    strays: list[str] = field(default_factory=list)
    has_image: bool = False
    source_problem: str | None = None
    figure: dict[str, Any] | None = None
    lint_critical: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


def verdict(ev: Evidence) -> tuple[str, list[str]]:
    """``OK``, ``DEFECT``, ``NO_FIGURE`` or ``INVALID``, with the reasons.

    A run is ``INVALID`` when the harness cannot vouch for it: the session
    was not isolated or failed, it worked outside its root, or the source
    that drew the figure cannot be established. Only then do the checks on
    the re-rendered figure say anything about the agent's figure.
    """
    if ev.isolation:
        return "INVALID", [f"isolation: {p}" for p in ev.isolation]
    if ev.harness_error:
        return "INVALID", [ev.harness_error]
    if ev.strays:
        return "INVALID", [
            f"worked outside its sandbox: {p}" for p in ev.strays
        ]
    if not ev.has_image:
        return "NO_FIGURE", ["the agent left no figure image"]
    if ev.source_problem or ev.figure is None:
        return "INVALID", [
            f"source: {ev.source_problem or 'no figure measured'}"
        ]
    reasons = [
        f"check {f['severity']} {f['rule']}: {f['message']}"
        for f in ev.figure.get("check") or []
        if f.get("severity") == "WARNING"
    ]
    reasons.extend(
        f"check NOT RUN: {s}" for s in ev.figure.get("check_skipped") or []
    )
    reasons.extend(f"lint critical {r}" for r in ev.lint_critical)
    reasons.extend(ev.missing)
    return ("DEFECT" if reasons else "OK"), reasons
