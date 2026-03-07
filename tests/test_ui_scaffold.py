"""Tests for ui/_scaffold.py project scaffolding."""

from __future__ import annotations

from pathlib import Path

from dartwork_mpl.ui._scaffold import scaffold


class TestScaffold:
    """Tests for scaffold() project generator."""

    def test_simple_creates_files(self, tmp_path: Path) -> None:
        """Simple example creates app.py, README.md, .gitignore."""
        dest = tmp_path / "my_project"
        scaffold(str(dest), example="simple")

        assert (dest / "app.py").exists()
        assert (dest / "README.md").exists()
        assert (dest / ".gitignore").exists()

    def test_complex_creates_files(self, tmp_path: Path) -> None:
        """Complex example also creates all expected files."""
        dest = tmp_path / "my_project"
        scaffold(str(dest), example="complex")

        assert (dest / "app.py").exists()
        assert (dest / "README.md").exists()
        assert (dest / ".gitignore").exists()

    def test_app_py_has_content(self, tmp_path: Path) -> None:
        """Generated app.py is non-empty."""
        dest = tmp_path / "my_project"
        scaffold(str(dest), example="simple")

        content = (dest / "app.py").read_text()
        assert len(content) > 100

    def test_non_empty_dir_aborts(
        self, tmp_path: Path, capsys: object
    ) -> None:
        """Scaffold refuses to overwrite a non-empty directory."""
        dest = tmp_path / "existing"
        dest.mkdir()
        (dest / "dummy.txt").write_text("x")

        scaffold(str(dest))

        # app.py should NOT be created
        assert not (dest / "app.py").exists()

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Nested target directories are created automatically."""
        dest = tmp_path / "a" / "b" / "project"
        scaffold(str(dest))

        assert dest.exists()
        assert (dest / "app.py").exists()
