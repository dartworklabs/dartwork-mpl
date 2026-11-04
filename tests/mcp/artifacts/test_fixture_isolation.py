"""Input fixtures stay trusted when the checkout itself cannot be admitted."""

import stat
from contextlib import contextmanager

from dartwork_mpl.mcp.artifacts.policy import ConfigurationError
from tests.mcp.artifacts import conftest
from tests.mcp.artifacts.test_input_access import access, policy


def test_owned_input_root_is_independent_of_group_writable_checkout(
    owned_input_root, monkeypatch
):
    """A shared checkout stays denied while an isolated fixture grants real access."""
    checkout = owned_input_root / "shared-checkout"
    checkout.mkdir(mode=0o775)
    checkout.chmod(0o775)
    fixture_file = checkout / "tests" / "mcp" / "artifacts" / "conftest.py"
    fixture_file.parent.mkdir(parents=True)
    fixture_file.touch()
    monkeypatch.setattr(conftest, "__file__", str(fixture_file))

    api = access()
    with contextmanager(conftest.owned_input_root.__wrapped__)() as isolated:
        assert not isolated.is_relative_to(checkout)
        assert stat.S_IMODE(isolated.stat().st_mode) == 0o700
        path, _, _, check = policy(isolated)
        grant = api.authorize_inputs(str(path), check)
        assert isinstance(grant, api.InputGrant), grant
        grant.close()
    assert not isolated.exists()

    path, _, _, check = policy(checkout)
    assert isinstance(
        api.authorize_inputs(str(path), check), ConfigurationError
    )
    assert stat.S_IMODE(checkout.stat().st_mode) == 0o775
