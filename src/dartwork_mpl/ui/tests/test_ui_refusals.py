"""The refusal edge: each named refusal answers its frozen status, code and body."""

import json

import pytest

from dartwork_mpl.ui._refusals import RestartFailed, refusal_response
from dartwork_mpl.ui.params import InvalidRequest
from dartwork_mpl.ui.platform.access import AccessDenied
from dartwork_mpl.ui.platform.fs import (
    FileIOFailure,
    PartialSave,
    RootConflict,
    TargetConflict,
    UnsafeTarget,
    UnsupportedFilesystem,
)
from dartwork_mpl.ui.platform.http import CallbackFailed, UnsupportedMediaType
from dartwork_mpl.ui.platform.json_bounds import LimitExceeded, MalformedInput
from dartwork_mpl.ui.render import UnsupportedFormat
from dartwork_mpl.ui.saving import InvalidOutput
from dartwork_mpl.ui.state import InvalidStoredState, PresetNotFound


@pytest.mark.parametrize(
    "failure, status, code",
    [
        (MalformedInput(), 400, "invalid_json"),
        (UnsupportedMediaType(), 415, "unsupported_media_type"),
        (LimitExceeded(), 413, "input_too_large"),
        (InvalidRequest(), 422, "invalid_request"),
        (UnsupportedFormat("bad format"), 400, "invalid_request"),
        (InvalidOutput(), 400, "invalid_output_path"),
        (UnsafeTarget(), 400, "unsafe_output_target"),
        (TargetConflict(), 409, "output_conflict"),
        (RootConflict(), 409, "root_changed"),
        (UnsupportedFilesystem(), 501, "unsupported_filesystem_capability"),
        (FileIOFailure(), 503, "filesystem_unavailable"),
        (InvalidStoredState(), 409, "invalid_stored_state"),
        (PresetNotFound(3), 404, "preset_not_found"),
        (CallbackFailed("The figure callback failed."), 500, "callback_failed"),
        (AccessDenied(), 403, "local_access_denied"),
        (RestartFailed(), 500, "restart_failed"),
    ],
)
def test_each_refusal_answers_its_status_and_detail_code_body(
    failure, status, code
):
    """The edge, not the refusal, decides status and code; the body is detail + code."""
    response = refusal_response(failure)
    assert response.status_code == status
    assert json.loads(response.body) == {"detail": failure.detail, "code": code}


def test_partial_save_lists_its_relative_paths():
    """Only a partial save adds ``paths``, as given (root-qualified, relative)."""
    response = refusal_response(PartialSave(("primary/a.tmp", "copy-1/b")))
    assert response.status_code == 503
    assert json.loads(response.body) == {
        "detail": PartialSave(()).detail,
        "code": "partial_save",
        "paths": ["primary/a.tmp", "copy-1/b"],
    }
