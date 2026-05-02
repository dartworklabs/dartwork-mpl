"""Shared fixtures and matplotlib hygiene for the robustness suite."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pytest

# Force the headless backend so the suite is safe under CI / SSH.
matplotlib.use("Agg")


@pytest.fixture(autouse=True)
def _close_all_figures_after_each_scenario() -> Iterator[None]:
    """Robustness scenarios deliberately stress matplotlib's state. We
    therefore close *every* open figure after each test (the parent
    conftest already resets rcParams)."""
    yield
    plt.close("all")


@pytest.fixture
def tmp_image_dir(tmp_path: Path) -> Path:
    """Per-test directory for saved PNG artefacts."""
    out = tmp_path / "robust_out"
    out.mkdir(parents=True, exist_ok=True)
    return out
