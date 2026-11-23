"""Pure: which script the recorded Bash calls last ran, from where, with what arguments.

Agents run their plot script in many shapes: ``python plot.py``, ``cd X &&
uv run --with pandas python plot.py $P/data.csv 2>&1 | tail``, a heredoc
written first in the same call. This reads the command strings the way the
shell would for that much: statements, ``cd``, ``VAR=value``, ``$VAR`` and
``~``. What it cannot resolve keeps its ``$`` so the caller can tell.
"""

from __future__ import annotations

import posixpath
import re
import shlex
from collections.abc import Mapping
from dataclasses import dataclass, replace

HEREDOC = re.compile(r"(<<-?\s*(['\"]?)(\w+)\2[^\n]*)\n.*?\n\s*\3\b", re.S)
COMMENT = re.compile(r"^\s*#.*$", re.M)
REDIRECT = re.compile(r"\d*>&\d+|\d*(?:>>?|<)&?\s*[^\s;&|()]+")
ASSIGN = re.compile(r"^([A-Za-z_]\w*)=(.*)$", re.S)
VAR = re.compile(r"\$(?:\{(\w+)\}|(\w+))")
PYTHON = re.compile(r"python[\d.]*$")
SEPARATORS = frozenset(";&|()")
PREFIXES = frozenset({"time", "env", "command", "exec", "nohup"})
# ``uv run`` options that take a value as the next word.
UV_VALUE = frozenset({"--with", "-w", "--python", "-p", "--project"})
UV_VALUE |= {"--directory", "--with-requirements", "--extra", "--group"}


@dataclass(frozen=True)
class Run:
    """One ``python script.py args`` the agent ran: absolute script, args, cwd.

    ``env`` holds the assignments written in front of it (``MPLBACKEND=Agg
    python plot.py``), ``packages`` what ``uv run --with`` added.
    """

    script: str
    args: tuple[str, ...]
    cwd: str
    env: tuple[tuple[str, str], ...] = ()
    packages: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        """False when the script path still holds a shell variable."""
        return "$" not in self.script


def statements(command: str) -> list[list[str]]:
    """The command's simple statements as words, heredoc bodies and redirections gone."""
    text = HEREDOC.sub(r"\1", command).replace("\\\n", " ")
    text = REDIRECT.sub(" ", COMMENT.sub("", text)).replace("\n", " ; ")
    lexer = shlex.shlex(text, posix=True, punctuation_chars=";&|()")
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        words = list(lexer)
    except ValueError:  # unbalanced quotes: not a command we can read
        return []
    found: list[list[str]] = [[]]
    for word in words:
        if set(word) <= SEPARATORS:
            found.append([])
        else:
            found[-1].append(word)
    return [s for s in found if s]


def expand(word: str, variables: Mapping[str, str]) -> str:
    """``~`` and the known ``$VAR``; an unknown variable stays as written."""
    home = variables.get("HOME")
    if home and (word == "~" or word.startswith("~/")):
        word = home + word[1:]
    return VAR.sub(lambda m: variables.get(m[1] or m[2], m[0]), word)


def script_call(words: list[str]) -> Run | None:
    """The run, with the script as written, if the statement runs a ``.py`` file."""
    env: list[tuple[str, str]] = []
    packages: list[str] = []
    while words and (ASSIGN.match(words[0]) or words[0] in PREFIXES):
        if found := ASSIGN.match(words[0]):
            env.append((found[1], found[2]))
        words = words[1:]
    through_uv = words[:2] == ["uv", "run"]
    if through_uv:
        words = words[2:]
        while words and words[0].startswith("-"):
            if words[0] in ("--with", "-w"):
                packages += words[1:2]
            words = words[2:] if words[0] in UV_VALUE else words[1:]
    if words and PYTHON.fullmatch(posixpath.basename(words[0])):
        words = words[1:]
        while words and re.fullmatch(r"-[A-Zabd-ln-z]+", words[0]):
            words = words[2:] if words[0] in ("-W", "-X") else words[1:]
    elif not through_uv:
        return None
    if words and words[0].endswith(".py"):
        return Run(words[0], tuple(words[1:]), "", tuple(env), tuple(packages))
    return None


def inside(path: str, folder: str) -> bool:
    """Whether ``path`` is ``folder`` or under it (macOS ``/private`` prefix aside)."""
    path, folder = (
        path.removeprefix("/private"),
        folder.removeprefix("/private"),
    )
    return path == folder or path.startswith(folder.rstrip("/") + "/")


def runs(
    commands: list[str], project: str, variables: Mapping[str, str]
) -> list[Run]:
    """Every script run, in order. Each call starts in the project or where the last ended inside it."""
    found: list[Run] = []
    cwd = project
    for command in commands:
        known = dict(variables)
        previous = cwd
        for words in statements(command):
            known["PWD"] = cwd
            words = [expand(w, known) for w in words]
            if all(ASSIGN.match(w) for w in words):
                for word in words:
                    name, value = word.split("=", 1)
                    if "$" not in value:
                        known[name] = value
            elif words[0] == "cd":
                target = words[1] if len(words) > 1 else known.get("HOME", cwd)
                target = previous if target == "-" else target
                previous, cwd = (
                    cwd,
                    posixpath.normpath(posixpath.join(cwd, target)),
                )
            elif call := script_call(words):
                script = call.script
                if "$" not in script:
                    script = posixpath.normpath(posixpath.join(cwd, script))
                found.append(replace(call, script=script, cwd=cwd))
        if not inside(cwd, project):  # Claude Code resets the shell there
            cwd = project
    return found
