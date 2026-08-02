"""Atomic publication contracts for color-authority writers."""

import importlib
import importlib.util
import json
import os
import stat
import tempfile
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATHS = {
    "build_color_v6_ssot": REPO_ROOT / "scripts/build_color_v6_ssot.py",
    "freeze_color_v5_compatibility": (
        REPO_ROOT / "scripts/freeze_color_v5_compatibility.py"
    ),
    "freeze_color_v5_quality": (
        REPO_ROOT / "scripts/freeze_color_v5_quality.py"
    ),
}
SCRIPT_NAMES = tuple(SCRIPT_PATHS)
WRITER_NAMES = (*SCRIPT_NAMES, "runtime_color_build")
TEXT_PAYLOAD = '{"label":"원자적 쓰기"}\n'


def _load_writer(writer_name: str) -> ModuleType:
    """Load one writer without invoking its command-line entry point."""
    if writer_name == "runtime_color_build":
        return importlib.import_module("dartwork_mpl._colors._build")
    path = SCRIPT_PATHS[writer_name]
    specification = importlib.util.spec_from_file_location(
        f"atomic_test_{writer_name}", path
    )
    if specification is None or specification.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def _publish(script_name: str, target: Path) -> str:
    """Invoke one writer and return its expected UTF-8 text."""
    module = _load_writer(script_name)
    if script_name == "runtime_color_build":
        target.parent.mkdir(parents=True, exist_ok=True)
        module._atomic_write_text(target, TEXT_PAYLOAD)
        return TEXT_PAYLOAD
    if script_name == "build_color_v6_ssot":
        payload = {"label": "원자적 쓰기"}
        module._write_payload(payload, target)
        return (
            json.dumps(
                payload,
                ensure_ascii=False,
                allow_nan=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
    module._write_output(target, TEXT_PAYLOAD)
    return TEXT_PAYLOAD


@pytest.mark.parametrize("script_name", WRITER_NAMES)
def test_writer_fsyncs_unique_sibling_before_atomic_replace(
    script_name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Flush one unique sibling before atomically publishing exact text."""
    target = tmp_path / "nested" / "authority.json"
    expected = (
        json.dumps(
            {"label": "원자적 쓰기"},
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
        if script_name == "build_color_v6_ssot"
        else TEXT_PAYLOAD
    )
    real_mkstemp = tempfile.mkstemp
    real_fsync = os.fsync
    real_replace = os.replace
    temporary_paths: list[Path] = []
    events: list[str] = []

    def record_mkstemp(
        *, prefix: str, suffix: str, dir: str | os.PathLike[str]
    ) -> tuple[int, str]:
        """Allocate a real temporary while recording its location."""
        descriptor, name = real_mkstemp(prefix=prefix, suffix=suffix, dir=dir)
        events.append("mkstemp")
        temporary_paths.append(Path(name))
        return descriptor, name

    def record_fsync(descriptor: int) -> None:
        """Require complete encoded bytes before the durability barrier."""
        assert os.fstat(descriptor).st_size == len(expected.encode("utf-8"))
        events.append("fsync")
        real_fsync(descriptor)

    def record_replace(
        source: str | os.PathLike[str], destination: str | os.PathLike[str]
    ) -> None:
        """Require a durable sibling before performing the real replace."""
        source_path = Path(source)
        assert source_path.is_file()
        events.append("replace")
        real_replace(source, destination)

    monkeypatch.setattr(tempfile, "mkstemp", record_mkstemp)
    monkeypatch.setattr(os, "fsync", record_fsync)
    monkeypatch.setattr(os, "replace", record_replace)

    actual = _publish(script_name, target)

    assert actual == expected
    assert target.read_text(encoding="utf-8") == expected
    assert events == ["mkstemp", "fsync", "replace"]
    assert len(temporary_paths) == 1
    temporary = temporary_paths[0]
    assert temporary.parent == target.parent
    assert temporary.name.startswith(f".{target.name}.")
    assert temporary.name.endswith(".tmp")
    assert temporary not in {
        target.with_suffix(target.suffix + ".tmp"),
        target.with_name(f".{target.name}.tmp"),
    }
    assert not temporary.exists()


@pytest.mark.parametrize("script_name", WRITER_NAMES)
def test_writer_cleans_sibling_after_replace_failure(
    script_name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Preserve the old target and remove the sibling after interruption."""
    target = tmp_path / "authority.json"
    target.write_text("old\n", encoding="utf-8")

    class PublicationInterrupted(BaseException):
        """Represent a process-control interruption during publication."""

    def reject_replace(
        source: str | os.PathLike[str], destination: str | os.PathLike[str]
    ) -> None:
        """Interrupt publication after writing the sibling."""
        raise PublicationInterrupted(
            f"cannot replace {source} -> {destination}"
        )

    monkeypatch.setattr(os, "replace", reject_replace)

    with pytest.raises(PublicationInterrupted, match="cannot replace"):
        _publish(script_name, target)

    assert target.read_text(encoding="utf-8") == "old\n"
    assert tuple(tmp_path.iterdir()) == (target,)


@pytest.mark.parametrize("script_name", WRITER_NAMES)
def test_writer_closes_descriptor_and_cleans_sibling_if_fdopen_fails(
    script_name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Release the raw descriptor when stream construction is interrupted."""
    target = tmp_path / "authority.json"
    real_mkstemp = tempfile.mkstemp
    descriptors: list[int] = []

    def record_mkstemp(
        *, prefix: str, suffix: str, dir: str | os.PathLike[str]
    ) -> tuple[int, str]:
        """Allocate a real descriptor so its eventual closure is observable."""
        descriptor, name = real_mkstemp(prefix=prefix, suffix=suffix, dir=dir)
        descriptors.append(descriptor)
        return descriptor, name

    def reject_fdopen(
        descriptor: int, mode: str, *, encoding: str, newline: str
    ) -> None:
        """Fail after allocation but before ownership reaches a text stream."""
        del descriptor, mode, encoding, newline
        raise OSError("stream construction interrupted")

    monkeypatch.setattr(tempfile, "mkstemp", record_mkstemp)
    monkeypatch.setattr(os, "fdopen", reject_fdopen)

    with pytest.raises(OSError, match="stream construction interrupted"):
        _publish(script_name, target)

    assert len(descriptors) == 1
    with pytest.raises(OSError):
        os.fstat(descriptors[0])
    assert not target.exists()
    assert tuple(tmp_path.iterdir()) == ()


@pytest.mark.parametrize("script_name", WRITER_NAMES)
def test_writer_preserves_existing_target_permissions(
    script_name: str, tmp_path: Path
) -> None:
    """Retain the destination mode when a source-controlled file is replaced."""
    target = tmp_path / "authority.json"
    target.write_text("old\n", encoding="utf-8")
    target.chmod(0o640)
    expected_mode = stat.S_IMODE(target.stat().st_mode)

    _publish(script_name, target)

    assert stat.S_IMODE(target.stat().st_mode) == expected_mode


@pytest.mark.parametrize("script_name", WRITER_NAMES)
def test_writer_uses_path_chmod_before_fdopen_when_fchmod_is_unavailable(
    script_name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Preserve mode through the portable path fallback before writing."""
    target = tmp_path / "authority.json"
    target.write_text("old\n", encoding="utf-8")
    target.chmod(0o640)
    expected_mode = stat.S_IMODE(target.stat().st_mode)
    real_chmod = os.chmod
    real_fdopen = os.fdopen
    events: list[str] = []

    def record_chmod(path: str | os.PathLike[str], mode: int) -> None:
        """Apply the real path operation while recording fallback order."""
        events.append("chmod")
        real_chmod(path, mode)

    def record_fdopen(
        descriptor: int, mode: str, *, encoding: str, newline: str
    ) -> object:
        """Record stream construction after the fallback permission change."""
        events.append("fdopen")
        return real_fdopen(descriptor, mode, encoding=encoding, newline=newline)

    monkeypatch.delattr(os, "fchmod", raising=False)
    monkeypatch.setattr(os, "chmod", record_chmod)
    monkeypatch.setattr(os, "fdopen", record_fdopen)

    _publish(script_name, target)

    assert events[:2] == ["chmod", "fdopen"]
    assert stat.S_IMODE(target.stat().st_mode) == expected_mode
