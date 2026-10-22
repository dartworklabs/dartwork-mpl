"""Real-file contracts for confined viewer outputs and fixed-name state."""

import hashlib
import io
import os
import random
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from dartwork_mpl.ui import saving
from dartwork_mpl.ui.platform import fs
from dartwork_mpl.ui.saving import RelativeOutput, _plan, parse_output
from dartwork_mpl.ui.state import StateFile
from dartwork_mpl.ui.state import _store as state


def snapshot(root: Path) -> dict[str, str]:
    """Hash the complete tree without following links, including empty folders."""
    result = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            result[relative] = "link:" + os.readlink(path)
        elif path.is_dir():
            result[relative] = "directory"
        else:
            result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def opened(root: Path, copies: fs.CopyTo = None) -> fs.RootScope:
    """Open real capabilities and fail usefully if this host cannot provide them."""
    result = fs.open_roots(root, copies, cwd=root.parent)
    assert isinstance(result, fs.RootScope), result
    return result


def output(name: str) -> RelativeOutput:
    """Create a valid path using the policy owner instead of a raw handle."""
    result = parse_output(name)
    assert isinstance(result, RelativeOutput), result
    return result


def save(roots: fs.RootScope, name: str) -> saving.SaveReceipt | fs.FsFailure:
    """Drive preparation and streaming together against the real filesystem."""
    plan = saving.prepare_save(roots, output(name), include_copies=True)
    if not isinstance(plan, saving.PreparedSave):
        return plan
    with plan:
        return saving.commit_save(plan, io.BytesIO(b"new figure bytes"))


@pytest.mark.parametrize("destination", ["primary", "copy"])
def test_existing_primary_or_copy_is_unchanged(
    tmp_path: Path, destination: str
) -> None:
    """A collision at either destination preserves every existing byte and tree."""
    primary, copy = tmp_path / "primary", tmp_path / "copy"
    primary.mkdir()
    copy.mkdir()
    (primary if destination == "primary" else copy).joinpath(
        "figure.png"
    ).write_bytes(b"old")
    before = snapshot(tmp_path)
    with opened(primary, copy) as roots:
        result = save(roots, "figure.png")
    assert isinstance(result, fs.TargetConflict)
    assert snapshot(tmp_path) == before


def test_all_targets_validate_before_missing_directories_are_created(
    tmp_path: Path,
) -> None:
    """A bad later copy cannot leave new parents in an earlier target."""
    primary, copy = tmp_path / "primary", tmp_path / "copy"
    primary.mkdir()
    (copy / "new").mkdir(parents=True)
    (copy / "new" / "figure.png").write_bytes(b"old")
    before = snapshot(tmp_path)
    with opened(primary, copy) as roots:
        result = save(roots, "new/figure.png")
    assert isinstance(result, fs.TargetConflict)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("link_parent", [False, True])
def test_symlink_or_parent_swap_cannot_redirect_save(
    tmp_path: Path, link_parent: bool
) -> None:
    """No-follow traversal refuses symlink leaves and parents without touching outside."""
    primary, outside = tmp_path / "primary", tmp_path / "outside"
    primary.mkdir()
    outside.mkdir()
    (outside / "sentinel").write_bytes(b"outside old")
    target = "link/figure.png" if link_parent else "figure.png"
    (primary / ("link" if link_parent else "figure.png")).symlink_to(
        outside if link_parent else outside / "sentinel"
    )
    before = snapshot(tmp_path)
    with opened(primary) as roots:
        result = save(roots, target)
    assert isinstance(result, fs.UnsafeTarget)
    assert snapshot(tmp_path) == before


def test_pinned_parent_replacement_is_detected(tmp_path: Path) -> None:
    """A prepared parent swap rejects writes to both old and replacement trees."""
    primary = tmp_path / "primary"
    (primary / "sub").mkdir(parents=True)
    with opened(primary) as roots:
        plan = saving.prepare_save(
            roots, output("sub/a.png"), include_copies=True
        )
        assert isinstance(plan, saving.PreparedSave)
        (primary / "sub").rename(primary / "moved")
        (primary / "sub").mkdir()
        before = snapshot(tmp_path)
        with plan:
            result = saving.commit_save(plan, io.BytesIO(b"new"))
    assert isinstance(result, fs.RootConflict)
    assert snapshot(tmp_path) == before


def test_root_replacement_is_detected(tmp_path: Path) -> None:
    """The configured root's name cannot redirect a pinned authority."""
    primary = tmp_path / "primary"
    with opened(primary) as roots:
        primary.rename(tmp_path / "old")
        primary.mkdir()
        before = snapshot(tmp_path)
        result = save(roots, "a.png")
    assert isinstance(result, fs.RootConflict)
    assert snapshot(tmp_path) == before


def test_root_swapped_during_reservation_never_writes_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A swap inside exclusive reservation is detected and cleans the pinned old file."""
    primary, copy = tmp_path / "primary", tmp_path / "copy"
    reserve = fs.reserve_file
    with opened(primary, copy) as roots:

        def reserve_then_swap(parent_fd: int, name: str, **options: int) -> int:
            """Move the primary after a real reservation and supply a sentinel tree."""
            fd = reserve(parent_fd, name, **options)
            if not (tmp_path / "old").exists():
                primary.rename(tmp_path / "old")
                primary.mkdir()
                (primary / "sentinel").write_bytes(b"replacement preserved")
            return fd

        monkeypatch.setattr(fs, "reserve_file", reserve_then_swap)
        result = save(roots, "a.png")
    assert isinstance(result, fs.RootConflict)
    assert snapshot(tmp_path) == {
        "copy": "directory",
        "old": "directory",
        "primary": "directory",
        "primary/sentinel": hashlib.sha256(
            b"replacement preserved"
        ).hexdigest(),
    }


def test_late_create_conflicts_without_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exclusive reservation preserves a late writer's bytes and rolls back ours."""
    primary, copy = tmp_path / "primary", tmp_path / "copy"
    reserve = fs.reserve_file
    calls = 0

    def late_create(parent_fd: int, name: str, **options: int) -> int:
        """Introduce a real competing leaf immediately before its reservation."""
        nonlocal calls
        calls += 1
        if calls == 2:
            (copy / "a.png").write_bytes(b"late writer")
        return reserve(parent_fd, name, **options)

    with opened(primary, copy) as roots:
        monkeypatch.setattr(fs, "reserve_file", late_create)
        result = save(roots, "a.png")
    assert isinstance(result, fs.TargetConflict)
    assert not (primary / "a.png").exists()
    assert (copy / "a.png").read_bytes() == b"late writer"


def test_failed_second_write_rolls_back_owned_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A later sink failure removes only new files and their empty parents."""
    primary, copy = tmp_path / "primary", tmp_path / "copy"
    with opened(primary, copy) as roots:
        (copy / "old").write_bytes(b"keep")
        before = snapshot(tmp_path)
        write = fs.write_file
        calls = 0

        def fail_second(fd: int, data: bytes) -> None:
            """Allow one real write, then fail the next destination deterministically."""
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("controlled sink failure")
            write(fd, data)

        monkeypatch.setattr(fs, "write_file", fail_second)
        result = save(roots, "new/sub/a.png")
    assert isinstance(result, fs.FileIOFailure)
    assert snapshot(tmp_path) == before


def test_failed_cleanup_reports_relative_partial_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cleanup failure reports exactly the remaining file without absolute paths."""
    primary, copy = tmp_path / "primary", tmp_path / "copy"
    with opened(primary, copy) as roots:
        write, remove = fs.write_file, fs.remove_file
        calls = 0

        def fail_second(fd: int, data: bytes) -> None:
            """Write the primary and refuse the copy."""
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("controlled write failure")
            write(fd, data)

        def leave_primary(
            parent_fd: int, name: str, identity: tuple[int, int]
        ) -> bool:
            """Leave the first reserved file while using normal cleanup elsewhere."""
            if os.fstat(parent_fd).st_ino == primary.stat().st_ino:
                raise OSError("controlled cleanup failure")
            return remove(parent_fd, name, identity)

        monkeypatch.setattr(fs, "write_file", fail_second)
        monkeypatch.setattr(fs, "remove_file", leave_primary)
        result = save(roots, "a.png")
    assert isinstance(result, fs.PartialSave)
    assert result.paths == ("primary/a.png",)
    assert snapshot(tmp_path) == {
        "copy": "directory",
        "primary": "directory",
        "primary/a.png": hashlib.sha256(b"new figure bytes").hexdigest(),
    }


def test_normalized_roots_aliases_and_streaming(tmp_path: Path) -> None:
    """One/list PathLike roots normalize from CWD and deduplicate inode aliases."""
    primary, copy = tmp_path / "primary", tmp_path / "copy"
    with opened(primary, [primary, "copy", copy]) as roots:
        result = save(roots, "safe/sub/a.svg")
        assert isinstance(result, saving.SaveReceipt)
        assert result.primary == "safe/sub/a.svg"
        assert result.copies == ("safe/sub/a.svg",)
        assert (primary / result.primary).read_bytes() == b"new figure bytes"
        assert (copy / result.copies[0]).read_bytes() == b"new figure bytes"


def test_single_string_and_home_expansion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A configured string is one path, and tilde expansion precedes root opening."""
    monkeypatch.setenv("HOME", str(tmp_path))
    with opened(tmp_path / "primary", "~/paper") as roots:
        assert isinstance(save(roots, "a.pdf"), saving.SaveReceipt)
    assert (tmp_path / "paper" / "a.pdf").is_file()


def test_close_is_idempotent_and_abandoned_plan_cleans_parents(
    tmp_path: Path,
) -> None:
    """Explicit close releases descriptors and removes an unused plan's new folders."""
    roots = opened(tmp_path / "primary")
    before = snapshot(tmp_path)
    plan = saving.prepare_save(
        roots, output("unused/sub/a.png"), include_copies=False
    )
    assert isinstance(plan, saving.PreparedSave)
    plan.close()
    plan.close()
    assert snapshot(tmp_path) == before
    roots.close()
    roots.close()
    assert isinstance(save(roots, "a.png"), fs.RootConflict)


@pytest.mark.parametrize(
    "failure", ["existing-stat", "created-open", "created-stat"]
)
def test_directory_acquisition_failure_closes_fds_and_reports_unknown_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    """Unpinned new directories remain honestly reported; acquired descriptors close."""
    primary = tmp_path / "primary"
    part = "existing" if failure == "existing-stat" else "new"
    observed: list[int] = []
    fail_fds: set[int] = set()
    open_directory, stat_handle = fs.open_directory, fs.stat_handle
    with opened(primary) as roots:
        (primary / "sentinel").write_bytes(b"keep")
        if failure == "existing-stat":
            (primary / part).mkdir()
        before = snapshot(tmp_path)

        def acquire(parent_fd: int, name: str) -> int:
            """Fail only the directory opened after its actual creation or inspection."""
            if failure == "created-open" and (primary / part).exists():
                raise OSError("controlled open failure after mkdir")
            fd = open_directory(parent_fd, name)
            observed.append(fd)
            fail_fds.add(fd)
            return fd

        def stat_acquired(fd: int) -> os.stat_result:
            """Refuse metadata for just the observed acquired directory descriptors."""
            if fd in fail_fds:
                raise OSError("controlled acquired-directory metadata failure")
            return stat_handle(fd)

        monkeypatch.setattr(fs, "open_directory", acquire)
        monkeypatch.setattr(fs, "stat_handle", stat_acquired)
        result = saving.prepare_save(
            roots, output(f"{part}/a.png"), include_copies=False
        )
        if failure == "existing-stat":
            assert isinstance(result, fs.FileIOFailure)
            assert snapshot(tmp_path) == before
        else:
            assert isinstance(result, fs.PartialSave)
            assert result.paths == ("primary/new",)
            assert snapshot(tmp_path) == {**before, "primary/new": "directory"}
        for fd in observed:
            with pytest.raises(OSError):
                os.fstat(fd)
        assert _plan._SAVE_LOCK.acquire(blocking=False)
        _plan._SAVE_LOCK.release()


@pytest.mark.parametrize("sink", ["output", "state"])
def test_reserved_file_metadata_failure_closes_and_reports_unverified_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sink: str
) -> None:
    """An acquired file without verified identity is closed and never blindly unlinked."""
    primary = tmp_path / "primary"
    reserve, stat_handle = fs.reserve_file, fs.stat_handle
    observed: dict[str, int] = {}
    with opened(primary) as roots:
        (primary / "sentinel").write_bytes(b"keep")
        store = state.FixedStateStore(roots)
        if sink == "state":
            assert isinstance(
                store.update(
                    StateFile.CONFIG,
                    max_bytes=100,
                    edit=lambda old: b"old bytes",
                ),
                state.StateWritten,
            )
        before = snapshot(tmp_path)

        def acquire(parent_fd: int, name: str, **options: int) -> int:
            """Remember each exclusively created file before its metadata can fail."""
            fd = reserve(parent_fd, name, **options)
            observed[name] = fd
            return fd

        def stat_acquired(fd: int) -> os.stat_result:
            """Refuse only metadata for the newly reserved file descriptor."""
            if fd in observed.values():
                raise OSError("controlled acquired-file metadata failure")
            return stat_handle(fd)

        monkeypatch.setattr(fs, "reserve_file", acquire)
        monkeypatch.setattr(fs, "stat_handle", stat_acquired)
        if sink == "output":
            result = save(roots, "a.png")
        else:
            result = store.update(
                StateFile.CONFIG, max_bytes=100, edit=lambda old: b"next bytes"
            )
        assert isinstance(result, fs.PartialSave)
        ((name, fd),) = observed.items()
        assert result.paths == (f"primary/{name}",)
        assert snapshot(tmp_path) == {
            **before,
            f"primary/{name}": hashlib.sha256(b"").hexdigest(),
        }
        with pytest.raises(OSError):
            os.fstat(fd)
        assert _plan._SAVE_LOCK.acquire(blocking=False)
        _plan._SAVE_LOCK.release()


def test_unexpected_source_error_rolls_back_and_releases_plan(
    tmp_path: Path,
) -> None:
    """A non-OS stream failure cannot strand reserved files or the process save lock."""

    class BrokenSource(io.BytesIO):
        """Represent a local staging stream whose Python-level read fails."""

        def read(self, size: int = -1) -> bytes:
            """Fail after reservations without depending on a filesystem error type."""
            raise ValueError("controlled source failure")

    with opened(tmp_path / "primary", tmp_path / "copy") as roots:
        before = snapshot(tmp_path)
        plan = saving.prepare_save(
            roots, output("new/a.png"), include_copies=True
        )
        assert isinstance(plan, saving.PreparedSave)
        try:
            result = saving.commit_save(plan, BrokenSource())
            assert isinstance(result, fs.FileIOFailure)
            assert snapshot(tmp_path) == before
            assert _plan._SAVE_LOCK.acquire(blocking=False)
            _plan._SAVE_LOCK.release()
        finally:
            plan.close()


def test_source_cancellation_cleans_reservations_before_propagating(
    tmp_path: Path,
) -> None:
    """A cancellation still releases pinned parents, files and the save lock."""

    class InterruptedSource(io.BytesIO):
        """Raise a BaseException outside the ordinary controlled-error contract."""

        def read(self, size: int = -1) -> bytes:
            """Interrupt streaming only after the real target reservations exist."""
            raise KeyboardInterrupt

    with opened(tmp_path / "primary") as roots:
        before = snapshot(tmp_path)
        plan = saving.prepare_save(
            roots, output("new/a.png"), include_copies=False
        )
        assert isinstance(plan, saving.PreparedSave)
        try:
            with pytest.raises(KeyboardInterrupt):
                saving.commit_save(plan, InterruptedSource())
            assert snapshot(tmp_path) == before
            assert _plan._SAVE_LOCK.acquire(blocking=False)
            _plan._SAVE_LOCK.release()
        finally:
            plan.close()


_UMASK_CHILD = r"""
import io, os, sys
from pathlib import Path
os.umask(0o022)
from dartwork_mpl.ui import saving
from dartwork_mpl.ui.platform import fs
from dartwork_mpl.ui.saving import _plan, parse_output
from dartwork_mpl.ui.state import StateFile
from dartwork_mpl.ui.state import _store as state
root, origin = Path(sys.argv[1]), Path(sys.argv[2])
assert Path(_plan.__file__).resolve() == origin.resolve()
roots = fs.open_roots(root / "primary", [root / "copy"], cwd=root)
assert isinstance(roots, fs.RootScope), roots
with roots:
    plan = saving.prepare_save(roots, parse_output("new/sub/fig.png"), include_copies=True)
    assert isinstance(plan, saving.PreparedSave), plan
    with plan:
        receipt = saving.commit_save(plan, io.BytesIO(b"figure"))
    assert isinstance(receipt, saving.SaveReceipt), receipt
    store = state.FixedStateStore(roots)
    for kind in (StateFile.CONFIG, StateFile.PRESETS):
        written = store.update(kind, max_bytes=64, edit=lambda old: b"{}")
        assert isinstance(written, state.StateWritten), written
"""


def test_outputs_follow_umask_while_state_stays_private(tmp_path: Path) -> None:
    """With umask 022 in an isolated child, outputs are 0644, new parents 0755, state 0600."""
    subprocess.run(
        [sys.executable, "-c", _UMASK_CHILD, str(tmp_path), _plan.__file__],
        check=True,
        timeout=60,
    )
    expected = {
        "copy": 0o755,
        "copy/new": 0o755,
        "copy/new/sub": 0o755,
        "copy/new/sub/fig.png": 0o644,
        "primary": 0o755,
        "primary/.dartwork_ui_config.json": 0o600,
        "primary/.dartwork_ui_presets.json": 0o600,
        "primary/new": 0o755,
        "primary/new/sub": 0o755,
        "primary/new/sub/fig.png": 0o644,
    }
    observed = {
        path.relative_to(tmp_path).as_posix(): oct(
            stat.S_IMODE(path.lstat().st_mode)
        )
        for path in sorted(tmp_path.rglob("*"))
    }
    assert observed == {name: oct(mode) for name, mode in expected.items()}


def test_seeded_paths_keep_outside_sentinel(tmp_path: Path) -> None:
    """Generated safe/refused path sequences preserve an independent outside oracle."""
    rng = random.Random(499)
    sentinel = tmp_path / "outside"
    sentinel.write_bytes(b"unchanged")
    expected = hashlib.sha256(sentinel.read_bytes()).hexdigest()
    with opened(tmp_path / "primary") as roots:
        for index in range(80):
            name = rng.choice(
                [
                    f"safe/{index}.png",
                    f"../outside{index}",
                    f"/outside{index}",
                    "link/a.png",
                ]
            )
            parsed = parse_output(name)
            if isinstance(parsed, RelativeOutput):
                plan = saving.prepare_save(roots, parsed, include_copies=False)
                if isinstance(plan, saving.PreparedSave):
                    with plan:
                        assert isinstance(
                            saving.commit_save(plan, io.BytesIO(b"value")),
                            (saving.SaveReceipt, fs.TargetConflict),
                        )
            assert hashlib.sha256(sentinel.read_bytes()).hexdigest() == expected
