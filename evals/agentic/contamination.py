"""Text evidence that an agent reached grading files (fail-closed backstop).

Enforcement is the sandbox: ``run.py --hide-grading`` mounts empty tmpfs over
the repo, the records tree and the work root and re-binds only the unit's
project, and A/B (decision) runs require it. This module reads the decoded
transcript objects and reports any sign that grading files were reached:

* **paths**: every path named in a tool call or its output is resolved
  (absolute anywhere in a word, ``~``/``$HOME``, or relative to the current
  directory, which ``cd``/``pushd`` and ``workdir`` move). A resolved path
  inside a grading root (a repo checkout, the records tree, another project
  under the work root) is a hit. ``//`` is skipped only after a URL scheme;
  elsewhere extra leading slashes collapse;
* **globs and expansions** (commands only; an output cannot expand): a word
  whose literal prefix (before ``*?[$`{``, with a named component) is a
  string prefix of a grading root or of another project, or whose pattern
  reaches a grading root component by component, is a hit;
* **leaving the project**: ``cd``/``pushd`` (or a tool ``workdir``) outside
  the project is a hit;
* **names**: ``evals/agentic``, ``fixtures/reference``, ``score.json``,
  ``manifest.json``, ``run_meta.json`` anywhere is a hit (package text that
  mentions them can trip this; it fails closed);
* **transcript stores**: other sessions' transcripts and histories under
  HOME (``~/.claude/projects``, ``~/.codex/sessions``, Codex sqlite stores,
  ...; ``transcript_stores``) count as grading roots.

Under the sandbox, ``gating`` keeps the findings it did not neutralise
(names, and roots not hidden by a tmpfs or a per-unit bind) gating.

Strings are scanned raw (JSON is decoded first), so ``\\n``, ``\\t`` and
``\\"`` separate words.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
from pathlib import Path

RULE = "resolved-path-v4"
NAME_MARKERS = (
    "evals/agentic",
    "fixtures/reference",
    "score.json",
    "manifest.json",
    "run_meta.json",
)
OUTPUT_KEYS = {
    "aggregated_output",
    "output",
    "formatted_output",
    "stdout",
    "stderr",
    "result",
}
WORKDIR_KEYS = {"workdir", "cwd", "working_directory"}
EXPANSION = "*?[$`{"
URL = re.compile(r"[a-z][a-z0-9+.-]*://\S*", re.IGNORECASE)
WORD = re.compile(r"""[^\s'"();|&<>=,]+""")
ABSOLUTE = re.compile(r"(?<![\w.-])/+[^:*?\[$`{]*")
SEGMENT = re.compile(r"&&|\|\||[;\n|]")
WRAPPER = re.compile(r"^(?:\S*/)?(?:ba|z|da|k)?sh$|^env$|^-\w+$|^\w+=\S*$")
HOME = str(Path.home())


# ------------------------------------------------------------ transcript strings
def _walk(obj, role: str, out: list) -> None:
    if isinstance(obj, str):
        s = obj.strip()
        if s[:1] in "{[":
            try:
                _walk(json.loads(s), role, out)
                return
            except ValueError:
                pass
        out.append((role, obj))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k in WORKDIR_KEYS and isinstance(v, str):
                out.append(("workdir", v))
            else:
                _walk(v, "output" if k in OUTPUT_KEYS else role, out)
    elif isinstance(obj, list):
        for v in obj:
            _walk(v, role, out)


def tool_strings(
    host: str, lines: list[dict], rollouts: list[list[dict]]
) -> list[tuple[str, str]]:
    """(role, raw string) of every tool call (``input``) and tool output (``output``)."""
    out: list = []
    if host == "claude":
        for e in lines:
            for item in (e.get("message") or {}).get("content") or []:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "tool_use":
                    _walk(item.get("input"), "input", out)
                elif item.get("type") == "tool_result":
                    _walk(item.get("content"), "output", out)
        return out
    for e in lines:
        if e.get("type", "").startswith("item."):
            _walk(e.get("item"), "input", out)
    for r in rollouts:
        for e in r:
            p = e.get("payload") or {}
            kind = p.get("type")
            if kind in ("function_call", "custom_tool_call"):
                _walk(p, "input", out)
            elif kind in ("function_call_output", "custom_tool_call_output"):
                _walk(p, "output", out)
    return out


def _normalise(texts: list) -> list[tuple[str, str]]:
    """Accept raw strings, JSON strings (decoded) or (role, string) pairs."""
    out: list = []
    for t in texts:
        if isinstance(t, tuple):
            out.append(t)
        else:
            _walk(t, "input", out)
    return out


# ------------------------------------------------------------ resolution
def _inside(path: str, root: str) -> bool:
    return path == root or path.startswith(root.rstrip("/") + "/")


def _expand(word: str) -> str:
    word = re.sub(r"\$\{HOME\}|\$HOME(?![\w])", HOME, word)
    if word == "~" or word.startswith("~/"):
        word = HOME + word[1:]
    return word


def _reaches(pattern: list[str], root: list[str]) -> bool:
    """Glob components (``**`` = any depth) select ``root`` or something below it."""

    def match(i: int, j: int) -> bool:
        if j == len(root):
            return True
        if i == len(pattern):
            return False
        if pattern[i] == "**":
            return match(i + 1, j) or match(i, j + 1)
        return fnmatch.fnmatchcase(root[j], pattern[i]) and match(i + 1, j + 1)

    return match(0, 0)


def _resolve(path: str, cwd: str) -> str:
    path = re.sub(r"^/+", "/", path)  # //x and ///x are /x
    if not path.startswith("/"):
        path = os.path.join(cwd, path)
    return os.path.realpath(os.path.normpath(path))


def transcript_stores(home: str = HOME) -> list[str]:
    """Other sessions' transcripts and histories under HOME (Claude Code, Codex).

    Not grading files, but they hold other units' work and the operator's
    sessions, so reaching them is contamination too. ``run.py`` hides or
    replaces them inside the sandbox (``home_store_mounts``).
    """
    claude, codex = Path(home) / ".claude", Path(home) / ".codex"
    paths = [
        claude / "projects",
        claude / "file-history",
        claude / "sessions",
        claude / "todos",
        claude / "plans",
        claude / "history.jsonl",
        codex / "sessions",
        codex / "archived_sessions",
        codex / "history.jsonl",
        codex / "session_index.jsonl",
        codex / "log",
        *sorted(codex.glob("*.sqlite*")),
        *sorted(codex.glob("accounts/*/sessions")),
    ]
    return [str(p) for p in paths]


class _Scan:
    def __init__(
        self,
        roots: list,
        work_root: Path,
        project: Path,
        stores: list | None = None,
        exempt: list | None = None,
    ):
        self.grading = sorted(
            {os.path.realpath(str(r)) for r in roots if os.path.isabs(str(r))}
        )
        self.stores = sorted(
            {
                os.path.realpath(str(r))
                for r in (transcript_stores() if stores is None else stores)
            }
        )
        # absolute entries exempt a subtree, relative ones a file-name suffix
        self.exempt = [
            os.path.realpath(e) if os.path.isabs(e) else e
            for e in map(str, exempt or [])
        ]
        self.work = os.path.realpath(str(work_root))
        self.own = os.path.realpath(str(project))
        self.found: dict[str, dict] = {}

    def add(self, label: str, kind: str, root: str | None = None) -> None:
        self.found.setdefault(label, {"kind": kind, "root": root})

    def root_of(self, path: str) -> str | None:
        """The grading root (repo, records, another project, a store) ``path`` is in."""
        if _inside(path, self.own) or any(
            _inside(path, e) if e.startswith("/") else path.endswith(e)
            for e in self.exempt
        ):
            return None
        for r in [*self.grading, *self.stores]:
            if _inside(path, r):
                return r
        if path != self.work and _inside(path, self.work):
            rel = path[len(self.work) + 1 :]
            return os.path.join(self.work, rel.split("/")[0])
        return None

    def _sibling(self, comps: list[str]) -> bool:
        """Pattern components can select a project other than this one."""
        work = [c for c in self.work.split("/") if c]
        if len(comps) <= len(work) or not _reaches(comps[: len(work)], work):
            return False
        nxt = comps[len(work)]
        return nxt != os.path.basename(self.own)

    def expands_into_grading(self, word: str, cwd: str) -> str | None:
        """The grading root a glob/expansion in a command could reach, else None.

        Either its literal prefix (before ``*?[$`{``, with at least one named
        component) is a string prefix of a grading root, a store or another
        project, or the pattern, component by component (unknown expansions
        as ``*``, ``**`` as any depth), reaches one.
        """
        cut = min((word.index(c) for c in EXPANSION if c in word), default=None)
        if cut is None:
            return None
        targets = [*self.grading, *self.stores]
        literal = word[:cut]
        if literal.strip("/"):
            lit = _resolve(literal, cwd) + (
                "/" if literal.endswith("/") else ""
            )
            if not _inside(lit.rstrip("/"), self.own):
                hit = next((r for r in targets if r.startswith(lit)), None)
                if hit:
                    return hit
                if (self.work + "/").startswith(lit) or lit.startswith(
                    self.work + "/"
                ):
                    return self.work
        pattern = re.sub(
            r"\$\{[^}]*\}?|\$\(?\w*\)?|`[^`]*`?|\{[^}]*\}?", "*", word
        )
        pattern = re.sub(r"^/+", "/", pattern)
        if not pattern.startswith("/"):
            pattern = os.path.join(cwd, pattern)
        comps = [c for c in os.path.normpath(pattern).split("/") if c]
        hit = next(
            (
                r
                for r in targets
                if _reaches(comps, [c for c in r.split("/") if c])
            ),
            None,
        )
        return hit or (self.work if self._sibling(comps) else None)

    def word(self, raw: str, cwd: str) -> None:
        w = _expand(raw)
        cut = min((w.index(c) for c in EXPANSION if c in w), default=None)
        literal = w if cut is None else w[:cut]
        paths = [_resolve(m.group(0), cwd) for m in ABSOLUTE.finditer(literal)]
        if (not literal.startswith("/") and "/" in literal) or literal == "..":
            paths.append(_resolve(literal, cwd))
        for path in paths:
            root = self.root_of(path)
            if root:
                self.add(path, "path", root)

    def text(self, s: str, cwd: str, globs: bool = False) -> None:
        s = URL.sub(" ", s)
        for m in WORD.finditer(s):
            self.word(m.group(0), cwd)
        if not globs:  # an output cannot expand a glob; only commands can
            return
        for tok in re.split(r"[\s'\"();|&<>]+", s):
            for piece in re.split(r"[=:]", tok):
                root = piece and self.expands_into_grading(_expand(piece), cwd)
                if root:
                    self.add(f"glob into grading root: {piece}", "glob", root)

    def command(self, s: str) -> None:
        """Scan a tool-call string segment by segment, following cd/pushd."""
        cwd = self.own
        for seg in SEGMENT.split(s):
            words = [w for w in re.split(r"[\s'\"]+", seg) if w]
            while words and WRAPPER.match(words[0]):  # bash -lc 'cd ..'
                words = words[1:]
            self.text(seg, cwd, globs=True)
            if words and words[0] in ("cd", "pushd"):
                args = [w for w in words[1:] if not w.startswith("-")]
                dest = (
                    _resolve(_expand(args[0]), cwd)
                    if args and args[0] != "-"
                    else HOME  # bare cd goes home; cd - is unknown
                )
                if not _inside(dest, self.own):
                    self.add(f"left the project: {seg.strip()[:80]}", "cd")
                cwd = dest


def contamination(
    texts: list,
    roots: list,
    work_root: Path,
    project: Path,
    stores: list | None = None,
    exempt: list | None = None,
) -> dict:
    """Findings of every rule above over tool calls and outputs; ``contaminated`` if any.

    ``findings`` maps each hit to its ``kind`` (``path``, ``glob``, ``cd``,
    ``workdir``, ``name``) and, for paths and globs, the grading ``root``
    reached; ``score.py`` uses the root to decide whether the sandbox hid it.
    ``stores`` defaults to ``transcript_stores()``; ``exempt`` paths (this
    unit's own rollouts) are never hits.
    """
    scan = _Scan(roots, work_root, project, stores, exempt)
    for role, s in _normalise(texts):
        if not isinstance(s, str):
            continue
        for m in NAME_MARKERS:
            if m in s:
                scan.add(f"name: {m}", "name")
        if role == "workdir":
            dest = _resolve(_expand(s), scan.own)
            if not _inside(dest, scan.own):
                scan.add(f"left the project: workdir {s[:80]}", "workdir")
        elif role == "input":
            scan.command(s)
        else:
            scan.text(s, scan.own)
    hits = sorted(scan.found)
    return {
        "contaminated": bool(hits),
        "hits": hits[:20],
        "findings": [{"hit": h, **scan.found[h]} for h in hits[:200]],
        "rule": RULE,
    }


def gating(result: dict | None, covered) -> list[dict]:
    """Findings the sandbox did not neutralise: grading names, and paths or
    globs whose root ``covered(root)`` says was not hidden in the sandbox."""
    return [
        f
        for f in (result or {}).get("findings") or []
        if f["kind"] == "name"
        or (
            f["kind"] in ("path", "glob")
            and f.get("root")
            and not covered(f["root"])
        )
    ]
