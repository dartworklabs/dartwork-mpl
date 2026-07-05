"""Tests for the decorator-based validate check registry.

Replaces the orchestrator's hand-maintained ``all_checks`` dict with a
``@register_check`` self-registration model (mirroring
``validate_fixes.register_fix`` and ``lint``'s ``Rule`` registry). These
tests pin the contract that made the dict risky: the registry must expose
the expected checks in a deterministic order, with unique ids, and
``validate_figure`` must run precisely that set.
"""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
import pytest

from dartwork_mpl.validate import validate_figure
from dartwork_mpl.validate._checks import register_check, registered_checks

matplotlib.use("Agg")  # Non-interactive backend for testing.

# The historical run/report order the orchestrator's dict encoded, now
# expressed as ``order=`` values on each check. Kept here as an explicit
# guard so a re-ordering is a conscious, reviewed change.
_EXPECTED_ORDER = [
    "OVERFLOW",
    "OVERLAP",
    "CROSS_AXES_OVERLAP",
    "LEGEND_OVERFLOW",
    "TICK_CROWD",
    "EMPTY_AXES",
    "MARGIN_ASYMMETRY",
    "PIE_LABEL_OFFSET",
    "TEXT_CONTRAST",
    "MIN_FONT_SIZE",
    "GRAYSCALE_SAFETY",
    "CLIPPED_TEXT",
]


class TestRegistryContents:
    def test_all_expected_checks_registered_in_order(self) -> None:
        ids = [c.check_id for c in registered_checks()]
        assert ids == _EXPECTED_ORDER

    def test_order_is_deterministic_across_calls(self) -> None:
        first = [c.check_id for c in registered_checks()]
        second = [c.check_id for c in registered_checks()]
        assert first == second

    def test_orders_are_sorted_and_ids_are_unique(self) -> None:
        orders = [c.order for c in registered_checks()]
        ids = [c.check_id for c in registered_checks()]
        assert orders == sorted(orders)
        assert len(set(ids)) == len(ids)

    def test_every_check_is_callable(self) -> None:
        for c in registered_checks():
            assert callable(c.fn)


class TestRegistryGuards:
    def test_duplicate_registration_raises(self) -> None:
        """Re-registering an existing id must raise without polluting
        the registry (the dispatch table stays unambiguous)."""
        before = [c.check_id for c in registered_checks()]
        with pytest.raises(RuntimeError, match="Duplicate check registered"):

            @register_check("OVERFLOW", order=999)
            def _dup(fig, _renderer=None):  # pragma: no cover - never runs
                return []

        after = [c.check_id for c in registered_checks()]
        assert after == before


class TestOrchestratorParity:
    def test_valid_ids_match_registry(self) -> None:
        """``validate_figure``'s accepted ids are exactly the registry's."""
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.plot([1, 2, 3], [1, 2, 3])
        registered = {c.check_id for c in registered_checks()}
        # Passing the full set must not raise (all recognized) ...
        validate_figure(fig, checks=tuple(registered), quiet=True)
        # ... and an id outside the registry must raise.
        with pytest.raises(ValueError, match="Unknown check IDs"):
            validate_figure(fig, checks=("NOT_A_CHECK",), quiet=True)
        plt.close(fig)

    def test_empty_axes_invoked_with_renderer(self) -> None:
        """EMPTY_AXES now takes an (unused) renderer for uniform dispatch;
        selecting only it must still run and flag a blank axes."""
        fig, ax = plt.subplots(figsize=(4, 3))  # nothing plotted
        warnings = validate_figure(fig, checks=("EMPTY_AXES",), quiet=True)
        assert [w for w in warnings if w.check_id == "EMPTY_AXES"]
        plt.close(fig)
