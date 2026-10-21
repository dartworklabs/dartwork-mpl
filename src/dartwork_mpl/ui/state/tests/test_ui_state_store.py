"""Real-file contracts for the two fixed-name viewer state files."""

import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from dartwork_mpl.ui.platform import fs
from dartwork_mpl.ui.platform.json_bounds import LimitExceeded
from dartwork_mpl.ui.state import _store as state
from dartwork_mpl.ui.state._language import InvalidStoredState


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


def test_state_replace_preserves_corrupt_bytes_when_edit_refuses(
    tmp_path: Path,
) -> None:
    """State edits may refuse corrupt bytes without creating a staging file."""
    with opened(tmp_path / "primary") as roots:
        path = tmp_path / "primary" / ".dartwork_ui_config.json"
        path.write_bytes(b"broken\xff")
        before = snapshot(tmp_path)
        store = state.FixedStateStore(roots)
        result = store.update(
            "config", max_bytes=1024, edit=lambda _old: InvalidStoredState()
        )
        assert isinstance(result, InvalidStoredState)
        assert snapshot(tmp_path) == before


def test_state_unchanged_never_creates_or_replaces_bytes(
    tmp_path: Path,
) -> None:
    """A locked no-write decision preserves both missing and existing fixed state."""
    with opened(tmp_path / "primary") as roots:
        store = state.FixedStateStore(roots)
        for initial in (None, b"original state"):
            if initial is not None:
                assert isinstance(
                    store.update(
                        "presets",
                        max_bytes=100,
                        edit=lambda old, value=initial: value,
                    ),
                    state.StateWritten,
                )
            before = snapshot(tmp_path)
            assert isinstance(
                store.update(
                    "presets",
                    max_bytes=100,
                    edit=lambda old: state.StateUnchanged(),
                ),
                state.StateUnchanged,
            )
            assert snapshot(tmp_path) == before


def test_state_missing_replace_bounds_and_fixed_names(tmp_path: Path) -> None:
    """Only fixed names are updated, and both old and next bytes are bounded."""
    with opened(tmp_path / "primary") as roots:
        store = state.FixedStateStore(roots)
        assert isinstance(store.read("config", max_bytes=8), state.MissingState)
        assert isinstance(
            store.update("config", max_bytes=8, edit=lambda old: b"12345678"),
            state.StateWritten,
        )
        assert store.read("config", max_bytes=8) == b"12345678"
        before = snapshot(tmp_path)
        assert isinstance(
            store.update("config", max_bytes=8, edit=lambda old: b"123456789"),
            LimitExceeded,
        )
        assert isinstance(store.read("config", max_bytes=7), InvalidStoredState)
        assert snapshot(tmp_path) == before
        assert set(before) == {"primary", "primary/.dartwork_ui_config.json"}


@pytest.mark.parametrize("nonregular", ["symlink", "directory", "fifo"])
def test_state_nonregular_refused_without_external_changes(
    tmp_path: Path, nonregular: str
) -> None:
    """State reads and edits never follow links or block on special files."""
    primary = tmp_path / "primary"
    primary.mkdir()
    outside = tmp_path / "sentinel"
    outside.write_bytes(b"keep")
    path = primary / ".dartwork_ui_presets.json"
    if nonregular == "symlink":
        path.symlink_to(outside)
    elif nonregular == "directory":
        path.mkdir()
    else:
        os.mkfifo(path)
    with opened(primary) as roots:
        store = state.FixedStateStore(roots)
        assert isinstance(
            store.read("presets", max_bytes=100), InvalidStoredState
        )
        assert isinstance(
            store.update("presets", max_bytes=100, edit=lambda old: b"[]"),
            InvalidStoredState,
        )
    assert outside.read_bytes() == b"keep"
    assert path.is_symlink() if nonregular == "symlink" else path.exists()


def test_state_replacement_failure_preserves_old_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Atomic replace failure leaves the original state and no sibling staging files."""
    with opened(tmp_path / "primary") as roots:
        store = state.FixedStateStore(roots)
        assert isinstance(
            store.update("config", max_bytes=100, edit=lambda old: b"old"),
            state.StateWritten,
        )
        before = snapshot(tmp_path)

        def refuse_replace(
            parent_fd: int, staging: str, destination: str
        ) -> None:
            """Fail only the owned state replacement operation."""
            raise OSError("controlled replacement failure")

        monkeypatch.setattr(state, "_replace_state", refuse_replace)
        assert isinstance(
            store.update("config", max_bytes=100, edit=lambda old: b"next"),
            fs.FileIOFailure,
        )
        assert snapshot(tmp_path) == before


def test_state_updates_are_serialized_across_stores(tmp_path: Path) -> None:
    """Every read/edit/write is one process transaction even across separate scopes."""
    primary = tmp_path / "primary"
    with opened(primary) as first, opened(primary) as second:
        stores = [state.FixedStateStore(first), state.FixedStateStore(second)]

        def increment(index: int) -> None:
            """Increment persisted state through independently constructed stores."""
            result = stores[index % 2].update(
                "config",
                max_bytes=100,
                edit=lambda old: str(
                    (0 if isinstance(old, state.MissingState) else int(old)) + 1
                ).encode(),
            )
            assert isinstance(result, state.StateWritten), result

        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(increment, range(40)))
        assert stores[0].read("config", max_bytes=100) == b"40"
