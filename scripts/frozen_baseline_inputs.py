"""Read a closed list of baseline files by exact path, and guard outputs.

Shared by the frozen v5 generators in this folder
(``freeze_color_v5_quality.py`` and ``freeze_color_v5_compatibility.py``).
Each generator names the exact baseline files its isolated probe needs; this
module reads only those, one tree entry and one blob at a time, from the
accepted commit. It never runs ``git archive``, lists a tree or expands a
directory. Each generator also names the working-tree files it reads or
pins; ``refuse_protected_output`` keeps an output from naming one of them.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path, PurePosixPath

PACKAGE_PREFIX = "src/dartwork_mpl/"
# Git is used only to resolve the commit and read single named objects.
GIT_COMMANDS = frozenset({"cat-file", "ls-tree", "rev-parse", "show"})
REGULAR_BLOB_MODES = frozenset({b"100644", b"100755"})

RunGit = Callable[..., bytes]


class BaselineRefusal(Exception):
    """An expected refusal of a generator input.

    A generator's ``main`` reports one of these as a one-line error and
    exits with status 2. Anything else -- a failed probe, a Git failure, a
    defect -- is not caught and keeps its traceback.
    """


class ProtectedOutputError(BaselineRefusal, ValueError):
    """``--output`` names a file the generator reads or pins, or an alias."""


class BaselineCommitError(BaselineRefusal, ValueError):
    """``--baseline-commit`` does not resolve to the accepted commit."""


class BaselineInputError(BaselineRefusal, RuntimeError):
    """A baseline input is unlisted, malformed, missing or off its pin."""


def run_git(command: str, *args: str, repo: Path) -> bytes:
    """Run one allowed Git read command in ``repo`` and return its output.

    Only commit resolution and single named-object reads are allowed; an
    archive or any other command is refused before Git runs. Pathspecs are
    literal, so a path argument never acts as a pattern.
    """
    if command not in GIT_COMMANDS:
        raise RuntimeError(f"git {command} is not an allowed baseline read")
    process = subprocess.run(
        ["git", "--literal-pathspecs", command, *args],
        cwd=repo,
        check=False,
        capture_output=True,
    )
    if process.returncode != 0:
        stderr = process.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git {command} {' '.join(args)} failed: {stderr}")
    return process.stdout


def resolve_baseline(
    revision: str, accepted: str, *, repo: Path, git: RunGit
) -> str:
    """Resolve ``revision`` and require it to be the ``accepted`` commit.

    An unresolvable revision (``git rev-parse`` fails) and a different
    commit both raise ``BaselineCommitError``.
    """
    try:
        output = git(
            "rev-parse", "--verify", f"{revision}^{{commit}}", repo=repo
        )
    except RuntimeError as error:
        raise BaselineCommitError(
            f"baseline commit {revision!r} does not resolve: {error}"
        ) from error
    resolved = output.decode("ascii").strip()
    if resolved != accepted:
        raise BaselineCommitError(
            f"baseline commit must resolve to {accepted}; got {resolved}"
        )
    return resolved


def check_input_path(path: str) -> None:
    """Refuse a listed path that is not one plain file path in the package."""
    parts = path.split("/")
    if (
        not path.startswith(PACKAGE_PREFIX)
        or any(character in path for character in "\\*?[]{}\0")
        or any(part in {"", ".", ".."} for part in parts)
        or PurePosixPath(path).as_posix() != path
    ):
        raise BaselineInputError(
            f"baseline input {path!r} is not a package file path"
        )


def read_baseline_input(
    commit: str, path: str, *, listed: frozenset[str], repo: Path, git: RunGit
) -> bytes:
    """Return one listed regular file of ``commit``, read by exact path.

    The path must be in ``listed`` and be a plain package path. Its tree entry
    must exist and be a regular blob: a symlink, a directory or a submodule at
    that path is refused, never followed or expanded. ``git`` runs the Git
    commands (``run_git`` or a generator's wrapper of it).
    """
    if path not in listed:
        raise BaselineInputError(f"baseline input {path!r} is not listed")
    check_input_path(path)
    output = git("ls-tree", "-z", "--full-tree", commit, "--", path, repo=repo)
    entries = [entry for entry in output.split(b"\0") if entry]
    if not entries:
        raise BaselineInputError(
            f"baseline input {path} is missing from {commit}"
        )
    if len(entries) != 1:
        raise BaselineInputError(
            f"baseline input {path} names more than one entry"
        )
    header, _, name = entries[0].partition(b"\t")
    mode, kind, object_id = header.split(b" ")
    if name.decode("utf-8") != path:
        raise BaselineInputError(
            f"baseline input {path} resolved to another entry"
        )
    if kind != b"blob" or mode not in REGULAR_BLOB_MODES:
        raise BaselineInputError(
            f"baseline input {path} is not a regular file "
            f"(mode {mode.decode('ascii')})"
        )
    return git("cat-file", "blob", object_id.decode("ascii"), repo=repo)


def extract_baseline_inputs(
    commit: str,
    destination: Path,
    *,
    inputs: Iterable[str],
    source_hashes: Mapping[str, str],
    repo: Path,
    git: RunGit,
) -> None:
    """Write exactly the listed baseline files below a fresh ``destination``.

    Files under ``source_hashes`` must keep their pinned raw SHA-256. Each
    file is created new (``O_EXCL``) inside directories this function makes,
    so nothing outside the list, and nothing outside ``destination``, is
    written.
    """
    listed = tuple(inputs)
    allowed = frozenset(listed)
    if len(allowed) != len(listed):
        raise BaselineInputError("baseline input list repeats a path")
    for path in listed:
        raw = read_baseline_input(
            commit, path, listed=allowed, repo=repo, git=git
        )
        pinned = source_hashes.get(path)
        if pinned is not None and hashlib.sha256(raw).hexdigest() != pinned:
            raise BaselineInputError(f"raw source hash mismatch for {path}")
        target = destination.joinpath(*path.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        flags = (
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        )
        with os.fdopen(os.open(target, flags, 0o644), "wb") as stream:
            stream.write(raw)


def refuse_protected_output(output: Path, protected: Iterable[Path]) -> Path:
    """Return ``output`` resolved, or refuse it if it names a protected file.

    ``output`` names a protected file when, made absolute with symlinks and
    ``..`` resolved, it is that file's path (relative, ``..`` and symlinked
    spellings all resolve to it, even before the file exists), or when it is
    the same existing file (device and inode, which also catches a hard
    link). The check covers the known inputs and their aliases at the moment
    it runs; it does not stop a parent path from being swapped concurrently
    after it. It guards these destinations only; it is not a general write
    policy.
    """
    resolved = output.resolve()
    try:
        status = output.stat()
    except FileNotFoundError:
        identity = None
    else:
        identity = (status.st_dev, status.st_ino)
    for path in protected:
        same_file = False
        if identity is not None:
            try:
                other = path.stat()
            except FileNotFoundError:
                pass
            else:
                same_file = (other.st_dev, other.st_ino) == identity
        if resolved == path.resolve() or same_file:
            raise ProtectedOutputError(
                f"--output {output} names a protected generator input: {path}"
            )
    return resolved
