"""Regression tests for the docs API asset generators.

Guards the long-standing ``viz_example`` docs-build failure (#235):
``_save_viz_example`` passed ``dm.cm(15)`` / ``dm.cm(10)`` (``Length``
objects, not float subclasses since 0.4.x) straight to
``fig.set_size_inches``. matplotlib built an object-dtype size array and
raised ``ufunc 'isfinite' not supported``, so the asset was never written
and the ``-W`` docs build aborted on the missing figure. The fix passes
``dm.figsize(...)`` inch floats instead.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_api_generate_assets():
    path = _REPO_ROOT / "docs" / "api" / "generate_assets.py"
    spec = importlib.util.spec_from_file_location(
        "docs_api_generate_assets", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_viz_example_renders_without_placeholder(tmp_path) -> None:
    mod = _load_api_generate_assets()
    images_dir = mod._prepare_images_dir(tmp_path)
    out = mod._save_viz_example(images_dir)

    assert out.exists()
    content = out.read_text(encoding="utf-8")
    # The placeholder fallback writes "<label> unavailable"; a real
    # plot_colors swatch SVG is large. Before the dm.figsize fix the
    # generator raised and (now) would fall back to the placeholder.
    assert "unavailable" not in content
    assert len(content) > 5000


def test_set_size_inches_accepts_figsize_floats() -> None:
    """The root cause: dm.figsize returns plain floats; dm.cm a Length.

    Passing the Length to set_size_inches is what tripped numpy's
    isfinite on an object array.
    """
    import dartwork_mpl as dm

    w, h = dm.figsize("15cm", "10cm")
    assert isinstance(w, float) and isinstance(h, float)
