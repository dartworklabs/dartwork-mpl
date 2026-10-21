"""Only typed safe relative output names become save targets."""

from __future__ import annotations

import pytest

from dartwork_mpl.ui.saving import SaveInputFailure as InputFailure
from dartwork_mpl.ui.saving import parse_output


class TestOutputLanguage:
    """Only typed safe relative output paths reach the confined filesystem owner."""

    @pytest.mark.parametrize("name", ["figure.png", "sub/figure.png"])
    def test_safe_relative_name_allowed(self, name: str) -> None:
        """Relative files and safe subdirectories retain their accepted spelling."""
        result = parse_output(name)
        assert not isinstance(result, InputFailure)
        assert result.filename == name

    @pytest.mark.parametrize("name", ["../../etc/passwd", "/etc/passwd", "   "])
    def test_unsafe_name_rejected(self, name: str) -> None:
        """Absolute, parent traversal and blank names never become output capabilities."""
        assert isinstance(parse_output(name), InputFailure)
