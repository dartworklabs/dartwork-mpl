"""The legacy wire goldens name the files that produced them, and those exist.

``legacy_calls.json`` is evidence only if a reader can rerun the capture. Each
entry records the sha256 of the pinned historical tool source, its assets, the
request list and the capture script; this module checks those records against
the files in ``tests/mcp/data_repair/capture/`` (see
``docs/development/mcp-wire-recapture.md``). It needs no FastMCP.
"""

import hashlib
import json
import re
from pathlib import Path

import pytest

_DATA = Path(__file__).resolve().parents[1] / "mcp" / "data_repair"
_CAPTURE = _DATA / "capture"
_FIXTURE = json.loads((_DATA / "fixtures" / "legacy_calls.json").read_text())
_RUNTIMES = _FIXTURE["runtimes"]
_SCRIPT = _CAPTURE / "capture_legacy_runtime.py"

# Captured before the provenance record existed: they name the pinned tool
# source but not the script that ran, which is not in the repository.
_BEFORE_PROVENANCE = {"2.13.3", "3.4.2"}
# The first capture. Every later one is checked against it, once the pydantic
# error-URL minor (``errors.pydantic.dev/2.14/``) is read as the same text.
_REFERENCE = "3.4.2"
_URL_MINOR = re.compile(r"errors\.pydantic\.dev/2\.\d+/")


def _sha(path: Path) -> str:
    """Return the sha256 of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _requests_sha() -> str:
    """Hash the request list exactly as the capture script does."""
    blob = json.dumps(_FIXTURE["requests"], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def _normalised(value: object) -> str:
    """Serialise a golden part with the pydantic error-URL minor blanked."""
    return _URL_MINOR.sub("errors.pydantic.dev/X/", json.dumps(value))


def test_capture_script_pins_the_tool_source_it_ships_with() -> None:
    """The script refuses any other tool source than the file beside it."""
    pinned = re.search(r"SOURCE_SHA = '([0-9a-f]{64})'", _SCRIPT.read_text())
    assert pinned is not None
    assert pinned.group(1) == _sha(_CAPTURE / "legacy-tools.py")


@pytest.mark.parametrize("version", sorted(_RUNTIMES))
def test_entry_names_the_pinned_tool_source(version: str) -> None:
    """Every entry was captured from the one pinned historical tool source."""
    assert _RUNTIMES[version]["tools_sha256"] == _sha(
        _CAPTURE / "legacy-tools.py"
    )


@pytest.mark.parametrize("version", sorted(set(_RUNTIMES) - _BEFORE_PROVENANCE))
def test_entry_provenance_matches_the_files_in_the_repository(
    version: str,
) -> None:
    """A recorded hash that matches no file here would be unfalsifiable.

    Editing ``capture_legacy_runtime.py`` changes its hash, so entries that
    cite the old bytes stop matching: recapture them, or say in the same
    commit why the old hash is retired. Do not edit the script casually.
    """
    provenance = _RUNTIMES[version]["capture_provenance"]
    assert provenance["capture_script_sha256"] == _sha(_SCRIPT)
    assert provenance["legacy_assets_sha256"] == _sha(
        _CAPTURE / "legacy-assets.py"
    )
    assert provenance["requests_sha256"] == _requests_sha()


@pytest.mark.parametrize("version", sorted(set(_RUNTIMES) - {_REFERENCE}))
def test_entry_answers_like_the_reference_capture(version: str) -> None:
    """Calls and discovery agree with the first capture across runtimes.

    The capture script's own comparison with the reference is only printed,
    because it differs by the pydantic URL minor on any newer pydantic. This
    keeps the check where it can fail: a runtime whose answers differ in
    anything but that URL needs an audit, not just a new entry.
    """
    entry, reference = _RUNTIMES[version], _RUNTIMES[_REFERENCE]
    for part in ("calls", "discovery"):
        assert _normalised(entry[part]) == _normalised(reference[part]), (
            f"FastMCP {version} {part} differs from {_REFERENCE} beyond the "
            "pydantic error-URL minor; audit it before keeping the entry"
        )
