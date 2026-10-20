"""Real operator-owned fixtures pin startup authorization and confined opens."""

import hashlib
import importlib
import importlib.util
import json
import os
import random
import subprocess
import sys
from pathlib import Path

import pytest

from dartwork_mpl.mcp.artifacts import (
    ConfigurationError,
    CopyInput,
    InvalidRequest,
    configure_store,
)


def access():
    """Require the implementation surface with an assertion-visible RED."""
    name = "dartwork_mpl.mcp.artifacts.input_access"
    assert importlib.util.find_spec(name) is not None, (
        "input authority is missing"
    )
    return importlib.import_module(name)


def policy(root: Path):
    """Create only a private disposable fixture policy with preexisting roots."""
    storage, source = root / "storage", root / "source"
    storage.mkdir(mode=0o700)
    source.mkdir(mode=0o700)
    path = root / "policy.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "storage_dir": str(storage),
                "copy_roots": {"data": str(source)},
            }
        )
    )
    path.chmod(0o600)
    store = configure_store(str(root / "artifacts"))
    assert not isinstance(store, ConfigurationError)
    return path, storage, source, store.check_input_roots


def selection(path="sample.csv", digest=None):
    """Choose a logical root without encoding any filesystem authority."""
    return CopyInput(
        "sample",
        "data",
        path,
        digest or hashlib.sha256(b"exact\x00bytes\n").hexdigest(),
    )


def test_grant_matrix_and_descriptor_confinement(owned_input_root):
    """Only startup policy admits exact bytes; opened source survives rename."""
    api = access()
    path, storage, source, check = policy(owned_input_root)
    assert isinstance(api.authorize_inputs(None, check), api.InputsDisabled)
    grant = api.authorize_inputs(str(path), check)
    assert isinstance(grant, api.InputGrant), grant
    try:
        original = source / "sample.csv"
        original.write_bytes(b"exact\x00bytes\n")
        opened = grant.open_copy(selection())
        assert isinstance(opened, api.OwnedInputFD)
        with opened:
            original.rename(source / "renamed.csv")
            sentinel = owned_input_root / "outside-sentinel"
            sentinel.write_bytes(b"must not read outside")
            original.symlink_to(sentinel)
            assert os.read(opened.fd, 1024) == b"exact\x00bytes\n"
            assert isinstance(grant.open_copy(selection()), InvalidRequest)
        with pytest.raises(OSError):
            os.fstat(opened.fd)
        assert grant.storage_path == storage
        duplicate = grant.duplicate_storage()
        assert isinstance(duplicate, api.OwnedInputFD)
        with duplicate:
            assert os.fstat(duplicate.fd).st_ino == storage.stat().st_ino
        assert isinstance(
            grant.open_copy(CopyInput("x", "unknown", "x", "a" * 64)),
            InvalidRequest,
        )
    finally:
        grant.close()
        grant.close()
    assert isinstance(grant.open_copy(selection()), ConfigurationError)
    assert isinstance(grant.duplicate_storage(), ConfigurationError)


@pytest.mark.parametrize(
    "case",
    [
        "malformed",
        "duplicate",
        "oversized",
        "unknown",
        "version",
        "foreign_writable",
        "policy_link",
        "ancestor_link",
        "alias",
        "overlap",
        "missing_storage",
        "missing_source",
        "storage_mode",
        "root_mode",
    ],
)
def test_invalid_policy_never_mints_grant(owned_input_root, case):
    """Closed policy, private ancestry, existing roots and separation are required."""
    api = access()
    path, storage, source, check = policy(owned_input_root)
    payload = json.loads(path.read_text())
    if case == "malformed":
        path.write_bytes(b"{")
    elif case == "duplicate":
        path.write_text('{"schema_version":1,"schema_version":1}')
    elif case == "oversized":
        path.write_bytes(b" " * (16 * 1024 + 1))
    elif case == "unknown":
        payload["other"] = True
    elif case == "version":
        payload["schema_version"] = True
    elif case == "foreign_writable":
        path.chmod(0o622)
    elif case == "policy_link":
        other = path.with_name("real.json")
        path.rename(other)
        path.symlink_to(other)
    elif case == "ancestor_link":
        link = owned_input_root / "link"
        link.symlink_to(source, target_is_directory=True)
        payload["copy_roots"]["data"] = str(link)
    elif case == "alias":
        payload["storage_dir"] = str(storage.parent) + "/./storage"
    elif case == "overlap":
        payload["storage_dir"] = str(source)
    elif case == "missing_storage":
        storage.rmdir()
    elif case == "missing_source":
        source.rmdir()
    elif case == "storage_mode":
        storage.chmod(0o750)
    elif case == "root_mode":
        source.chmod(0o722)
    if case in {"unknown", "version", "ancestor_link", "alias", "overlap"}:
        path.write_text(json.dumps(payload))
    result = api.authorize_inputs(str(path), check)
    assert isinstance(result, ConfigurationError), (case, result)
    assert str(owned_input_root) not in repr(result)


@pytest.mark.parametrize("target", ["source", "storage"])
def test_replacement_during_callback_or_later_is_denied(
    owned_input_root, target
):
    """Pinning brackets the overlap callback and every subsequent grant use."""
    api = access()
    path, storage, source, check = policy(owned_input_root)
    root = source if target == "source" else storage

    def replace_root(storage_dir, roots):
        """Exchange a validated root while the owned callback is in progress."""
        result = check(storage_dir, roots)
        root.rename(root.with_name(root.name + "-old"))
        root.mkdir(mode=0o700)
        return result

    assert isinstance(
        api.authorize_inputs(str(path), replace_root), ConfigurationError
    )
    grant = api.authorize_inputs(str(path), check)
    assert isinstance(grant, api.InputGrant)
    try:
        root.rename(root.with_name(root.name + "-second"))
        root.mkdir(mode=0o700)
        assert isinstance(grant.open_copy(selection()), ConfigurationError)
        if target == "storage":
            assert isinstance(grant.duplicate_storage(), ConfigurationError)
        else:
            opened = grant.duplicate_storage()
            assert isinstance(opened, api.OwnedInputFD)
            opened.close()
    finally:
        grant.close()


@pytest.mark.parametrize(
    "kind", ["symlink", "fifo", "directory", "intermediate_link"]
)
def test_outside_sentinel_is_never_opened(owned_input_root, kind):
    """No-follow walks and nonblocking regular checks avoid escapes and FIFOs."""
    api = access()
    path, storage, source, check = policy(owned_input_root)
    sentinel = owned_input_root / "outside"
    sentinel.write_bytes(b"must never be read")
    requested = source / "sample.csv"
    relative = "sample.csv"
    if kind == "symlink":
        requested.symlink_to(sentinel)
    elif kind == "fifo":
        os.mkfifo(requested)
    elif kind == "directory":
        requested.mkdir()
    else:
        requested.symlink_to(owned_input_root, target_is_directory=True)
        relative = "sample.csv/outside"
    grant = api.authorize_inputs(str(path), check)
    assert isinstance(grant, api.InputGrant)
    try:
        assert isinstance(grant.open_copy(selection(relative)), InvalidRequest)
        assert sentinel.read_bytes() == b"must never be read"
    finally:
        grant.close()


def test_original_hardlinks_are_not_origin_uniqueness_claims(owned_input_root):
    """An ordinary already-open regular source may have other hardlink names."""
    api = access()
    path, storage, source, check = policy(owned_input_root)
    (source / "sample.csv").write_bytes(b"exact\x00bytes\n")
    os.link(source / "sample.csv", source / "second")
    grant = api.authorize_inputs(str(path), check)
    assert isinstance(grant, api.InputGrant)
    try:
        opened = grant.open_copy(selection())
        assert isinstance(opened, api.OwnedInputFD)
        with opened:
            assert os.read(opened.fd, 100) == b"exact\x00bytes\n"
    finally:
        grant.close()


def test_unsupported_capability_and_constructor_are_closed(
    owned_input_root, monkeypatch
):
    """Missing owned OS mechanisms refuse retention and constructors are sealed."""
    api = access()
    path, storage, source, check = policy(owned_input_root)
    with pytest.raises((ValueError, TypeError)):
        api.InputGrant(object(), storage, {})
    monkeypatch.setattr(api, "_check_capabilities", lambda fd: False)
    assert isinstance(
        api.authorize_inputs(str(path), check), ConfigurationError
    )


def test_seeded_policy_bytes_always_refuse_safely(owned_input_root):
    """Bounded random byte policies yield named failures without leaking paths."""
    api = access()
    path, storage, source, check = policy(owned_input_root)
    rng = random.Random(20261021)
    for _ in range(40):
        path.write_bytes(rng.randbytes(rng.randrange(0, 512)))
        assert isinstance(
            api.authorize_inputs(str(path), check), ConfigurationError
        )


@pytest.mark.parametrize(
    "failure", ["callback", "callback_io", "first_probe", "second_probe"]
)
def test_partial_startup_failure_closes_all_pins(
    owned_input_root, monkeypatch, failure
):
    """Failure after pinning never retains root/process descriptors."""
    api = access()
    path, storage, source, check = policy(owned_input_root)
    before = len(os.listdir("/dev/fd"))
    real_probe = api._check_capabilities
    probes = 0

    def probe(fd):
        """Fail either side of the callback at the owned capability seam."""
        nonlocal probes
        probes += 1
        if (failure == "first_probe" and probes == 1) or (
            failure == "second_probe" and probes == 2
        ):
            return False
        return real_probe(fd)

    def callback(storage_dir, roots):
        """Return a safe refusal or fail an owned root observation."""
        if failure == "callback":
            return ConfigurationError()
        if failure == "callback_io":
            raise OSError("private policy path must not escape")
        return check(storage_dir, roots)

    monkeypatch.setattr(api, "_check_capabilities", probe)
    result = api.authorize_inputs(str(path), callback)
    assert isinstance(result, ConfigurationError)
    assert len(os.listdir("/dev/fd")) == before
    assert str(owned_input_root) not in repr(result)


@pytest.mark.parametrize("change", ["removed", "replaced"])
def test_storage_authority_is_independent_of_original_copy_root(
    owned_input_root, change
):
    """Retained/delete/maintenance storage survives loss of an original root."""
    api = access()
    path, storage, source, check = policy(owned_input_root)
    grant = api.authorize_inputs(str(path), check)
    assert isinstance(grant, api.InputGrant)
    try:
        if change == "removed":
            source.rmdir()
        else:
            source.rename(source.with_name("old-source"))
            source.mkdir(mode=0o700)
        assert isinstance(grant.open_copy(selection()), ConfigurationError)
        opened = grant.duplicate_storage()
        assert isinstance(opened, api.OwnedInputFD), opened
        with opened:
            assert os.fstat(opened.fd).st_ino == storage.stat().st_ino
        storage.rename(storage.with_name("old-storage"))
        storage.mkdir(mode=0o700)
        assert isinstance(grant.duplicate_storage(), ConfigurationError)
    finally:
        grant.close()


@pytest.mark.parametrize("missing", ["lock", "descriptor", "process"])
def test_unsupported_host_keeps_import_and_legacy_parser(
    owned_input_root, missing
):
    """An actual fresh interpreter imports legacy with retention mechanisms absent."""
    access()
    path, storage, source, check = policy(owned_input_root)
    script = """
import builtins, os, sys
real_import = builtins.__import__
def unsupported_import(name, *args, **kwargs):
    'Deny only the missing host mechanism before importing product modules.'
    if name == 'fcntl' and sys.argv[2] == 'lock':
        raise ImportError('unsupported lock mechanism')
    return real_import(name, *args, **kwargs)
builtins.__import__ = unsupported_import
if sys.argv[2] == 'descriptor':
    del os.O_NOFOLLOW
from dartwork_mpl.mcp.artifacts import parse_render_request, ConfigurationError
from dartwork_mpl.mcp.artifacts import input_access as access
from dartwork_mpl.mcp.artifacts import input_io as io
if sys.argv[2] == 'process':
    def unsupported_probe(fd):
        'Refuse exec support at the owned startup probe seam.'
        return False
    io.probe_worker = unsupported_probe
assert not isinstance(parse_render_request('fig = None'), ConfigurationError)
assert isinstance(access.authorize_inputs(sys.argv[1], lambda storage, roots: None), ConfigurationError)
print('legacy import/parse available; retention configuration_error')
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(path), missing],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert "retention configuration_error" in result.stdout
