"""Tests for _helpers module."""

from __future__ import annotations

from pathlib import Path

from dartwork_mpl._helpers import create_parent_path


class TestCreateParentPath:
    """Tests for create_parent_path()."""

    def test_creates_nested_parent(self, tmp_path: Path) -> None:
        """Deep nested parent directories are created."""
        target = tmp_path / "a" / "b" / "c" / "file.txt"
        create_parent_path(target)
        assert target.parent.exists()

    def test_existing_parent_no_error(self, tmp_path: Path) -> None:
        """No error when parent directory already exists."""
        target = tmp_path / "file.txt"
        create_parent_path(target)
        # Call again — should not raise
        create_parent_path(target)
        assert target.parent.exists()

    def test_accepts_str(self, tmp_path: Path) -> None:
        """Accepts a plain string path."""
        target = str(tmp_path / "sub" / "file.txt")
        create_parent_path(target)
        assert Path(target).parent.exists()

    def test_accepts_path(self, tmp_path: Path) -> None:
        """Accepts a pathlib.Path object."""
        target = tmp_path / "sub" / "file.txt"
        create_parent_path(target)
        assert target.parent.exists()
