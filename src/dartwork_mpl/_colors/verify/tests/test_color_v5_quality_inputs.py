"""The quality generator reads only its listed inputs and never writes over one.

``scripts/freeze_color_v5_quality.py`` compiles the archived direct previews
from a closed list of baseline files (``BASELINE_PREVIEW_INPUTS``). Every
extraction check runs on a synthetic Git repository under ``tmp_path`` that
holds a listed regular file, an unlisted decoy, a documentation decoy, a
symlink, a symlinked directory and a plain directory. None reads the real
accepted commit, and none produces an archive: a check that must refuse
before Git runs replaces ``subprocess.run`` with a stand-in that fails if it
is called.

The output checks require ``--output`` and refuse a protected destination
and its aliases. They point the generator only at a synthetic protected
sentinel under ``tmp_path`` (``_protected_inputs`` is replaced), never at a
real accepted file, and stand-ins stop Git, compute and writes.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
GENERATOR_PATH = REPO_ROOT / "scripts/freeze_color_v5_quality.py"
LISTED = "src/dartwork_mpl/listed.py"
INNER = "src/dartwork_mpl/pkg/inner.py"
UNLISTED = "src/dartwork_mpl/unlisted.py"
DOCS_DECOY = "docs/decoy.md"
ALIAS = "src/dartwork_mpl/alias.py"
ALIASED_DIRECTORY = "src/dartwork_mpl/linked"
DIRECTORY = "src/dartwork_mpl/pkg"


@pytest.fixture(scope="module")
def generator() -> ModuleType:
    """Load the generator module without running its entry point."""
    specification = importlib.util.spec_from_file_location(
        "quality_generator_inputs_test", GENERATOR_PATH
    )
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def _git(repo: Path, *args: str) -> str:
    """Run Git in the synthetic repository with no user or system config."""
    environment = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "synthetic",
        "GIT_AUTHOR_EMAIL": "synthetic@example.invalid",
        "GIT_COMMITTER_NAME": "synthetic",
        "GIT_COMMITTER_EMAIL": "synthetic@example.invalid",
    }
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def synthetic_commit(tmp_path: Path) -> tuple[Path, str]:
    """Commit synthetic files, decoys, symlinks and a directory."""
    repo = tmp_path / "repo"
    files = {
        LISTED: "VALUE = 'listed'\n",
        INNER: "VALUE = 'inner'\n",
        UNLISTED: "VALUE = 'unlisted decoy'\n",
        DOCS_DECOY: "documentation decoy\n",
    }
    for relative, text in files.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (repo / ALIAS).symlink_to("../../docs/decoy.md")
    (repo / ALIASED_DIRECTORY).symlink_to(
        "../../docs", target_is_directory=True
    )
    _git(repo, "init", "-q")
    _git(repo, "add", "--", *files, ALIAS, ALIASED_DIRECTORY)
    _git(repo, "commit", "-q", "--no-gpg-sign", "-m", "synthetic")
    return repo, _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def no_git(
    generator: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    """Fail the test if the generator starts any process."""

    def refuse(*args: object, **kwargs: object) -> object:
        raise AssertionError(f"git was started: {args!r}")

    monkeypatch.setattr(generator.subprocess, "run", refuse)
    yield


def _files_below(root: Path) -> list[str]:
    """List the files this test's own destination holds."""
    if not root.exists():
        return []
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() or path.is_symlink()
    )


def test_listed_files_are_written_byte_for_byte_and_nothing_else(
    generator: ModuleType, synthetic_commit: tuple[Path, str], tmp_path: Path
) -> None:
    """Extract exactly the listed regular files, with their committed bytes."""
    repo, commit = synthetic_commit
    destination = tmp_path / "destination"

    generator._extract_baseline_inputs(
        commit, destination, inputs=(LISTED, INNER), repo=repo
    )

    assert _files_below(destination) == sorted((LISTED, INNER))
    for relative in (LISTED, INNER):
        assert (destination / relative).read_bytes() == (
            repo / relative
        ).read_bytes()


def test_extraction_reads_named_objects_and_never_an_archive(
    generator: ModuleType,
    synthetic_commit: tuple[Path, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each listed file costs one exact tree lookup and one blob read."""
    repo, commit = synthetic_commit
    commands: list[tuple[str, ...]] = []
    original = generator._run_git

    def record(command: str, *args: str, repo: Path) -> bytes:
        commands.append((command, *args))
        return original(command, *args, repo=repo)

    monkeypatch.setattr(generator, "_run_git", record)
    generator._extract_baseline_inputs(
        commit, tmp_path / "destination", inputs=(LISTED,), repo=repo
    )

    assert [command[0] for command in commands] == ["ls-tree", "cat-file"]
    assert commands[0][-2:] == ("--", LISTED)


@pytest.mark.parametrize(
    "command", ["archive", "ls-files", "checkout", "worktree", "clone"]
)
def test_archive_and_other_git_commands_are_refused_before_git_runs(
    generator: ModuleType, no_git: None, command: str, tmp_path: Path
) -> None:
    """The old whole-tree ``git archive`` request is refused, not run."""
    with pytest.raises(RuntimeError, match="not an allowed baseline read"):
        generator._run_git(command, "--format=tar", "HEAD", repo=tmp_path)


@pytest.mark.parametrize("path", [UNLISTED, DOCS_DECOY, INNER])
def test_unlisted_path_is_refused_before_git_runs(
    generator: ModuleType, no_git: None, path: str
) -> None:
    """A path outside the list is refused before any Git object is read."""
    with pytest.raises(RuntimeError, match="is not listed"):
        generator._read_baseline_input(
            "HEAD", path, listed=frozenset({LISTED}), repo=REPO_ROOT
        )


@pytest.mark.parametrize(
    "path",
    [
        "src/dartwork_mpl/../../docs/decoy.md",
        "/src/dartwork_mpl/listed.py",
        "src/dartwork_mpl//listed.py",
        "src/dartwork_mpl/./listed.py",
        "src/dartwork_mpl/pkg/",
        "src/dartwork_mpl\\listed.py",
        "src/dartwork_mpl/*.py",
        "src/dartwork_mpl/[l]isted.py",
        DOCS_DECOY,
        "src/other_package/listed.py",
    ],
)
def test_escaping_or_pattern_path_is_refused_even_when_listed(
    generator: ModuleType, no_git: None, path: str
) -> None:
    """A listed entry must still be one plain file path in the package."""
    with pytest.raises(RuntimeError, match="not a package file path"):
        generator._read_baseline_input(
            "HEAD", path, listed=frozenset({path}), repo=REPO_ROOT
        )


@pytest.mark.parametrize(
    ("path", "message"),
    [
        (ALIAS, r"not a regular file \(mode 120000\)"),
        (DIRECTORY, r"not a regular file \(mode 040000\)"),
        (f"{ALIASED_DIRECTORY}/decoy.md", "is missing from"),
        ("src/dartwork_mpl/absent.py", "is missing from"),
    ],
    ids=["symlink", "directory", "below-symlinked-directory", "missing"],
)
def test_alias_directory_and_missing_inputs_are_refused(
    generator: ModuleType,
    synthetic_commit: tuple[Path, str],
    tmp_path: Path,
    path: str,
    message: str,
) -> None:
    """Refuse instead of following an alias or expanding a directory."""
    repo, commit = synthetic_commit
    destination = tmp_path / "destination"

    with pytest.raises(RuntimeError, match=message):
        generator._extract_baseline_inputs(
            commit, destination, inputs=(path,), repo=repo
        )

    assert _files_below(destination) == []


def test_pinned_source_drift_is_refused_before_writing(
    generator: ModuleType,
    synthetic_commit: tuple[Path, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A listed file under ``SOURCE_HASHES`` must keep its pinned bytes."""
    repo, commit = synthetic_commit
    destination = tmp_path / "destination"
    monkeypatch.setattr(generator, "SOURCE_HASHES", {LISTED: "0" * 64})

    with pytest.raises(RuntimeError, match="raw source hash mismatch"):
        generator._extract_baseline_inputs(
            commit, destination, inputs=(LISTED,), repo=repo
        )

    assert _files_below(destination) == []


def test_repeated_list_entry_is_refused(
    generator: ModuleType, no_git: None, tmp_path: Path
) -> None:
    """The input list names each file once."""
    with pytest.raises(RuntimeError, match="repeats a path"):
        generator._extract_baseline_inputs(
            "HEAD", tmp_path / "destination", inputs=(LISTED, LISTED)
        )


def test_baseline_input_list_is_a_closed_list_of_package_files(
    generator: ModuleType, no_git: None
) -> None:
    """The real list: plain package files, no docs, every pinned source."""
    inputs = generator.BASELINE_PREVIEW_INPUTS
    package_sources = {
        path
        for path in generator.SOURCE_HASHES
        if path.startswith(generator.BASELINE_INPUT_PREFIX)
    }

    assert len(set(inputs)) == len(inputs)
    for path in inputs:
        generator._check_input_path(path)
    assert package_sources <= set(inputs)
    assert not [path for path in inputs if "superpowers" in path]


SENTINEL_BYTES = b"SYNTHETIC PROTECTED SENTINEL\n"


@pytest.fixture
def no_side_effects(
    generator: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    """Fail the test if ``main`` reaches Git, extraction, compute or a write."""

    def refuse(step: str) -> Callable[..., object]:
        def stand_in(*args: object, **kwargs: object) -> object:
            raise AssertionError(f"{step} was reached: {args!r}")

        return stand_in

    monkeypatch.setattr(generator.subprocess, "run", refuse("git"))
    for name, step in (
        ("_extract_baseline_inputs", "extraction"),
        ("_build_payload", "compute"),
        ("_atomic_write_text", "write"),
    ):
        monkeypatch.setattr(generator, name, refuse(step))
    yield


@pytest.fixture
def sentinel(
    generator: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Make a synthetic file the only protected generator input."""
    path = tmp_path / "protected" / "sentinel.json"
    path.parent.mkdir()
    path.write_bytes(SENTINEL_BYTES)
    monkeypatch.setattr(
        generator, "_protected_inputs", lambda: (path,), raising=False
    )
    return path


def _run_main(
    generator: ModuleType, monkeypatch: pytest.MonkeyPatch, *args: str
) -> int:
    """Run the generator's ``main`` in-process with ``args``."""
    monkeypatch.setattr(sys, "argv", [str(GENERATOR_PATH), *args])
    return int(generator.main())


def test_missing_output_fails_before_git_extraction_or_writes(
    generator: ModuleType,
    no_side_effects: None,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """There is no default destination: ``--output`` is required."""
    with pytest.raises(SystemExit) as stopped:
        _run_main(generator, monkeypatch, "--baseline-commit", "HEAD")

    assert stopped.value.code == 2
    error = capsys.readouterr().err
    assert "--output" in error and "required" in error


def _alias(kind: str, sentinel: Path, tmp_path: Path) -> str:
    """Return one spelling or alias of ``sentinel`` as an ``--output``."""
    if kind == "exact":
        return str(sentinel)
    if kind == "dot-dot":
        return str(tmp_path / "protected" / ".." / "protected" / sentinel.name)
    if kind == "relative":
        return os.path.relpath(sentinel)
    if kind == "symlink":
        link = tmp_path / "link.json"
        link.symlink_to(sentinel)
        return str(link)
    if kind == "symlinked-parent":
        linked = tmp_path / "linked"
        linked.symlink_to(sentinel.parent, target_is_directory=True)
        return str(linked / sentinel.name)
    if kind == "hard-link":
        hard = tmp_path / "hard.json"
        os.link(sentinel, hard)
        return str(hard)
    raise AssertionError(kind)


ALIASES = (
    "exact",
    "dot-dot",
    "relative",
    "symlink",
    "symlinked-parent",
    "hard-link",
)


@pytest.mark.parametrize("kind", ALIASES)
def test_protected_destination_is_refused_before_git_and_left_unchanged(
    generator: ModuleType,
    no_side_effects: None,
    sentinel: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
) -> None:
    """An explicit ``--output`` may not name a protected input or an alias."""
    monkeypatch.chdir(tmp_path)
    destination = _alias(kind, sentinel, tmp_path)

    status = _run_main(
        generator,
        monkeypatch,
        "--baseline-commit",
        "HEAD",
        "--output",
        destination,
    )

    assert status == 2
    assert "names a protected generator input" in capsys.readouterr().err
    assert sentinel.read_bytes() == SENTINEL_BYTES


@pytest.mark.parametrize("kind", ALIASES)
def test_writer_refuses_a_protected_alias_at_write_time(
    generator: ModuleType,
    sentinel: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """The final write checks again, so a later alias is refused too."""
    monkeypatch.chdir(tmp_path)
    destination = Path(_alias(kind, sentinel, tmp_path))

    with pytest.raises(ValueError, match="protected generator input"):
        generator._write_output(destination, "{}\n")

    assert sentinel.read_bytes() == SENTINEL_BYTES


@pytest.mark.parametrize(
    "kind", ["exact", "dot-dot", "relative", "symlink", "symlinked-parent"]
)
def test_protected_destination_is_refused_before_it_exists(
    generator: ModuleType,
    sentinel: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """Path spellings are refused even when no file identity can be compared.

    The sentinel is removed first, so only path resolution can match; a
    dangling symlink and a symlinked parent still lead to it.
    """
    monkeypatch.chdir(tmp_path)
    sentinel.unlink()
    destination = Path(_alias(kind, sentinel, tmp_path))

    with pytest.raises(ValueError, match="protected generator input"):
        generator._refuse_protected_output(destination)

    assert not sentinel.exists()


def test_owned_destinations_are_accepted_and_written(
    generator: ModuleType, sentinel: Path, tmp_path: Path
) -> None:
    """A new file, or an unrelated existing one, is an allowed output."""
    fresh = tmp_path / "owned" / "quality.json"
    existing = tmp_path / "existing.json"
    existing.write_bytes(b"old\n")

    for destination in (fresh, existing):
        generator._write_output(destination, "{}\n")
        assert destination.read_text(encoding="utf-8") == "{}\n"
    assert sentinel.read_bytes() == SENTINEL_BYTES


def test_protected_inputs_name_every_file_the_generator_reads_or_pins(
    generator: ModuleType,
) -> None:
    """Compare paths only; no file is opened or written."""
    expected = {
        generator.QUALITY_PATH,
        generator.COMPATIBILITY_PATH,
        generator.ORACLE_PATH,
        *(generator.REPO_ROOT / path for path in generator.SOURCE_HASHES),
    }

    assert set(generator._protected_inputs()) == expected
    assert generator.QUALITY_PATH.relative_to(generator.REPO_ROOT) == Path(
        "docs/superpowers/specs/assets/2026-07-14-oklab-centered-color-system"
        "/color_v5_quality.json"
    )
