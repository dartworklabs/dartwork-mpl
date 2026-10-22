"""The legacy preset-file helpers in ui/_config.py (outside the viewer's HTTP routes)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from dartwork_mpl.ui._config import (
    PRESET_FILENAME,
    _atomic_write_text,
    load_presets,
    save_preset,
)


class TestConfigPersistence:
    """Test save/load of the legacy preset file helpers."""

    def test_save_and_load_preset_json(self, tmp_path: Path) -> None:
        """Presets are saved to and loaded from JSON."""
        preset_file = tmp_path / PRESET_FILENAME
        with patch(
            "dartwork_mpl.ui._config._preset_path", return_value=preset_file
        ):
            save_preset("test_a", {"n": 1})
            save_preset("test_b", {"n": 2})
            presets = load_presets()

        assert len(presets) == 2
        assert presets[0]["label"] == "test_a"
        assert presets[0]["params"]["n"] == 1
        assert presets[1]["label"] == "test_b"

    def test_load_presets_corrupt_json(self, tmp_path: Path) -> None:
        """Corrupt preset file returns empty list."""
        preset_file = tmp_path / PRESET_FILENAME
        preset_file.write_text("not valid json", encoding="utf-8")
        with patch(
            "dartwork_mpl.ui._config._preset_path", return_value=preset_file
        ):
            assert load_presets() == []

    def test_load_presets_non_list_json(self, tmp_path: Path) -> None:
        """Preset file with a non-list JSON returns empty list."""
        preset_file = tmp_path / PRESET_FILENAME
        preset_file.write_text('{"not": "a list"}', encoding="utf-8")
        with patch(
            "dartwork_mpl.ui._config._preset_path", return_value=preset_file
        ):
            assert load_presets() == []


class TestConfigInternals:
    """Tests for internal config helpers."""

    def test_set_and_get_base_dir(self, tmp_path: Path) -> None:
        """set_base_dir sets the directory used by path helpers."""
        from dartwork_mpl.ui._config import _get_base_dir, set_base_dir

        try:
            set_base_dir(tmp_path)
            assert _get_base_dir() == tmp_path
        finally:
            # Restore
            import dartwork_mpl.ui._config as cfg

            cfg._base_dir = None

    def test_serializable_scalar_types(self) -> None:
        """Scalar types pass through unchanged."""
        from dartwork_mpl.ui._config import _serializable

        result = _serializable(
            {"i": 42, "f": 3.14, "s": "hello", "b": True, "n": None}
        )
        assert result == {
            "i": 42,
            "f": 3.14,
            "s": "hello",
            "b": True,
            "n": None,
        }

    def test_serializable_list_and_tuple(self) -> None:
        """Lists pass through, tuples are converted to lists."""
        from dartwork_mpl.ui._config import _serializable

        result = _serializable({"lst": [1, 2], "tup": (3, 4)})
        assert result["lst"] == [1, 2]
        assert result["tup"] == [3, 4]

    def test_serializable_unknown_type(self) -> None:
        """Unknown types are str()-ified."""
        from dartwork_mpl.ui._config import _serializable

        result = _serializable({"obj": {"nested": True}})
        assert isinstance(result["obj"], str)


class TestAtomicWriteText:
    """Atomic text writes create parents, replace content and leave no temp files."""

    def test_writes_content(self, tmp_path: Path) -> None:
        target = tmp_path / "presets.json"
        _atomic_write_text(target, '[{"a": 1}]\n')
        assert target.read_text(encoding="utf-8") == '[{"a": 1}]\n'

    def test_overwrite_leaves_no_temp_files(self, tmp_path: Path) -> None:
        target = tmp_path / "presets.json"
        _atomic_write_text(target, "first")
        _atomic_write_text(target, "second")
        assert target.read_text(encoding="utf-8") == "second"
        # The temp file is renamed into place, never left behind.
        assert list(tmp_path.iterdir()) == [target]

    def test_creates_parent_dir(self, tmp_path: Path) -> None:
        target = tmp_path / "nested" / "dir" / "presets.json"
        _atomic_write_text(target, "ok")
        assert target.read_text(encoding="utf-8") == "ok"
