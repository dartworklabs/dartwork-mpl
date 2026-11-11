"""Metric and alpha-policy contracts for ``GRAYSCALE_SAFETY``."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

import dartwork_mpl as dm
from dartwork_mpl.validate import Severity, VisualWarning, validate_figure


def _warning_for_lines(
    colors_and_alphas: tuple[tuple[str, float | None], ...],
    *,
    background: str = "#ffffff",
) -> VisualWarning | None:
    """Return the grayscale warning for source colors on one background."""
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    fig.patch.set_facecolor(background)
    ax.set_facecolor(background)
    for index, (color, alpha) in enumerate(colors_and_alphas):
        ax.plot(
            [0, 1], [float(index), float(1 - index)], color=color, alpha=alpha
        )

    warnings = validate_figure(fig, checks=("GRAYSCALE_SAFETY",), quiet=True)
    warning = next(
        (item for item in warnings if item.check_id == "GRAYSCALE_SAFETY"), None
    )
    plt.close(fig)
    return warning


def test_grayscale_warning_is_an_explicit_precompositing_heuristic() -> None:
    """Keep the INFO diagnostic bounded while preserving legacy fields."""
    warning = _warning_for_lines((("#000048", None), ("#0000ff", None)))

    assert warning is not None
    assert warning.severity is Severity.INFO
    detail = warning.detail
    pair = detail["pairs"][0]

    assert {
        "delta_y_threshold",
        "delta_l_threshold",
        "pairs",
        "count",
        "omitted",
    } <= detail.keys()
    assert {
        "colors",
        "relative_y",
        "delta_y",
        "delta_e_ok",
        "delta_l",
    } <= pair.keys()
    assert detail["delta_y_threshold"] == 0.10
    assert detail["delta_l_threshold"] == 0.10
    assert detail["count"] == 1
    assert detail["omitted"] == 0
    assert detail["metric_model"] == "project_modeled_relative_y_srgb_d65"
    assert detail["alpha_policy"] == (
        "ignore_zero_alpha_compare_positive_alpha_source_rgb_before_compositing"
    )
    assert pair["colors"] == ("#000048", "#0000ff")
    assert pair["relative_y"] == (0.005, 0.072)
    assert pair["delta_y"] == 0.067
    assert pair["delta_e_ok"] == 32.904
    # Compatibility alias: WCAG coefficients give 0.068, while the project's
    # modeled-relative-Y kernel gives 0.067. Keep the old key's old meaning.
    assert pair["delta_l"] == 0.068
    assert (
        "project modeled-relative-Y proximity heuristic before compositing"
        in warning.message
    )
    assert "ΔEOK" in warning.message

    lowered = warning.message.casefold()
    for unbounded_term in (
        "near-identical",
        "collapse",
        "indistinguishable",
        "safe",
        "guarantee",
    ):
        assert unbounded_term not in lowered


def test_grayscale_warning_ignores_line_artist_with_zero_alpha() -> None:
    """A fully transparent line must not create a diagnostic pair."""
    warning = _warning_for_lines((("#000048", None), ("#0000ff", 0.0)))

    assert warning is None


def test_positive_alpha_uses_source_rgb_before_background_compositing() -> None:
    """Background changes must not alter the documented source-RGB metric."""
    colors_and_alphas = (("#000048", 0.25), ("#0000ff", 0.75))

    white_warning = _warning_for_lines(colors_and_alphas, background="#ffffff")
    black_warning = _warning_for_lines(colors_and_alphas, background="#000000")

    assert white_warning is not None
    assert black_warning is not None
    assert white_warning.detail["pairs"] == black_warning.detail["pairs"]
    assert white_warning.detail["pairs"][0]["relative_y"] == (0.005, 0.072)
    assert white_warning.detail["pairs"][0]["delta_y"] == 0.067


def _warnings_for_scatter(
    colors: tuple[str, ...], alpha: object
) -> list[VisualWarning]:
    """Validate one scatter collection and return every finding."""
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    ax.scatter(
        range(len(colors)), range(len(colors)), c=list(colors), alpha=alpha
    )
    warnings = validate_figure(fig, checks=("GRAYSCALE_SAFETY",), quiet=True)
    plt.close(fig)
    return warnings


def test_grayscale_check_runs_on_collection_with_per_point_alpha() -> None:
    """A collection with an alpha array must be checked, not CHECK_FAILED.

    ``Collection.get_alpha()`` returns an ndarray for per-point alpha; the
    check once tested it in a scalar ``or`` and the orchestrator reported the
    resulting ValueError as ``CHECK_FAILED``.
    """
    warnings = _warnings_for_scatter(
        ("#000048", "#0000ff", "#00ff00"), alpha=[1.0, 0.5, 1.0]
    )

    assert [item.check_id for item in warnings] == ["GRAYSCALE_SAFETY"]
    assert warnings[0].detail["pairs"][0]["colors"] == ("#000048", "#0000ff")


def test_grayscale_check_skips_only_zero_alpha_rows_of_a_collection() -> None:
    """Rows with alpha 0 are ignored; the other rows of the collection count.

    The pair stays reported when the invisible row is a third colour, and is
    not reported when the invisible row is one of the two close colours, so
    partially visible collections are neither dropped whole nor kept whole.
    """
    visible_pair = _warnings_for_scatter(
        ("#000048", "#0000ff", "#00ff00"), alpha=[1.0, 1.0, 0.0]
    )
    hidden_member = _warnings_for_scatter(
        ("#000048", "#0000ff", "#00ff00"), alpha=[0.0, 1.0, 1.0]
    )

    assert [item.check_id for item in visible_pair] == ["GRAYSCALE_SAFETY"]
    assert visible_pair[0].detail["count"] == 1
    assert hidden_member == []
