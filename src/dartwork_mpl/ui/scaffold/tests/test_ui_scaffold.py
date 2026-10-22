"""Tests for ui/scaffold project scaffolding."""

from __future__ import annotations

from pathlib import Path

from dartwork_mpl.ui.scaffold import (
    EXAMPLES,
    TargetNotEmpty,
    UnknownExample,
    scaffold,
)


class TestScaffold:
    """Tests for scaffold() project generator."""

    def test_simple_creates_files(self, tmp_path: Path) -> None:
        """Simple example creates app.py, README.md, .gitignore."""
        dest = tmp_path / "my_project"
        scaffold(str(dest), example="simple")

        assert (dest / "app.py").exists()
        assert (dest / "README.md").exists()
        assert (dest / ".gitignore").exists()

    def test_app_py_has_content(self, tmp_path: Path) -> None:
        """Generated app.py is non-empty."""
        dest = tmp_path / "my_project"
        scaffold(str(dest), example="simple")

        content = (dest / "app.py").read_text()
        assert len(content) > 100

    def test_non_empty_dir_aborts(self, tmp_path: Path) -> None:
        """A non-empty directory is refused as a value and left unchanged."""
        dest = tmp_path / "existing"
        dest.mkdir()
        (dest / "dummy.txt").write_text("x")

        result = scaffold(str(dest))

        assert result == TargetNotEmpty(dest=dest.resolve())
        assert sorted(p.name for p in dest.iterdir()) == ["dummy.txt"]

    def test_unknown_example_is_refused_before_any_write(
        self, tmp_path: Path
    ) -> None:
        """An example without a bundled template is refused; no directory appears."""
        dest = tmp_path / "proj"

        result = scaffold(str(dest), example="complex")

        assert result == UnknownExample(example="complex", available=EXAMPLES)
        assert not dest.exists()

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Nested target directories are created automatically."""
        dest = tmp_path / "a" / "b" / "project"
        scaffold(str(dest))

        assert dest.exists()
        assert (dest / "app.py").exists()
