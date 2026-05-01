"""Tests for dartwork_mpl.lint — anti-pattern detection engine."""

from __future__ import annotations

from dartwork_mpl.lint import Issue, Rule, format_report, lint, load_rules

GOOD_CODE = """
import matplotlib.pyplot as plt
import dartwork_mpl as dm

fig, ax = dm.subplots(width="13cm", aspect="wide")
ax.bar(["A", "B"], [1, 2], color="dc.blue500")
dm.auto_layout(fig)
dm.save_and_show(fig, "out")
"""

BAD_FIGSIZE = """
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(5, 3))
"""

BAD_TIGHT_LAYOUT = """
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
plt.tight_layout()
"""

BAD_ZERO_RESIZE_MENTION = """
# Zero-Resize Policy is great
import dartwork_mpl as dm
"""


class TestLoadRules:
    def test_returns_nonempty_rule_list(self):
        rules = load_rules()
        assert isinstance(rules, list)
        assert len(rules) >= 5
        for r in rules:
            assert isinstance(r, Rule)
            assert r.id
            assert r.severity in {"critical", "warning", "info"}
            assert r.message

    def test_includes_core_rule_ids(self):
        ids = {r.id for r in load_rules()}
        for required in {
            "figsize-direct",
            "tight-layout",
            "zero-resize-mention",
            "plt-style-use",
            "plt-show-only",
        }:
            assert required in ids

    def test_includes_extended_rule_ids(self):
        ids = {r.id for r in load_rules()}
        for required in {
            "raw-hex-color",
            "fontsize-literal",
            "linewidth-literal",
            "savefig-direct",
            "jet-cmap",
            "oversize-width",
        }:
            assert required in ids


class TestLint:
    def test_good_code_has_no_critical_issues(self):
        issues = lint(GOOD_CODE)
        criticals = [i for i in issues if i.severity == "critical"]
        assert criticals == []

    def test_detects_figsize_direct(self):
        issues = lint(BAD_FIGSIZE)
        ids = {i.rule_id for i in issues}
        assert "figsize-direct" in ids
        figsize_issue = next(i for i in issues if i.rule_id == "figsize-direct")
        assert figsize_issue.severity == "critical"

    def test_detects_tight_layout(self):
        issues = lint(BAD_TIGHT_LAYOUT)
        assert any(i.rule_id == "tight-layout" for i in issues)

    def test_detects_zero_resize_mention(self):
        issues = lint(BAD_ZERO_RESIZE_MENTION)
        assert any(i.rule_id == "zero-resize-mention" for i in issues)

    def test_issue_has_message_and_line(self):
        issues = lint(BAD_FIGSIZE)
        first = next(i for i in issues if i.rule_id == "figsize-direct")
        assert first.message
        assert first.line is None or first.line >= 1


class TestRuleApplication:
    def test_custom_rules_subset(self):
        all_rules = load_rules()
        subset = [r for r in all_rules if r.id == "figsize-direct"]
        issues = lint(BAD_TIGHT_LAYOUT, rules=subset)
        # No figsize-direct in BAD_TIGHT_LAYOUT, so subset finds nothing.
        assert all(i.rule_id == "figsize-direct" for i in issues)
        # And tight-layout is filtered out.
        assert not any(i.rule_id == "tight-layout" for i in issues)


class TestIssue:
    def test_issue_is_frozen_dataclass(self):
        issue = Issue(
            rule_id="figsize-direct", severity="critical", message="msg", line=5
        )
        # frozen=True → setting attribute raises FrozenInstanceError
        import dataclasses

        try:
            issue.line = 6  # type: ignore[misc]
        except dataclasses.FrozenInstanceError:
            pass
        else:
            raise AssertionError("Issue should be frozen")


class TestExtendedRules:
    """Coverage for the 0.4 lint expansion (raw-hex, fontsize, linewidth, savefig, jet-cmap, oversize-width)."""

    def test_raw_hex_color_fires(self):
        code = 'ax.bar(x, y, color="#ff0000")\n'
        ids = {i.rule_id for i in lint(code)}
        assert "raw-hex-color" in ids

    def test_raw_hex_color_skips_named_token(self):
        code = "ax.bar(x, y, color=dm.oc.red6)\n"
        ids = {i.rule_id for i in lint(code)}
        assert "raw-hex-color" not in ids

    def test_fontsize_literal_fires(self):
        code = 'ax.text(0, 0, "hi", fontsize=12)\n'
        ids = {i.rule_id for i in lint(code)}
        assert "fontsize-literal" in ids

    def test_fontsize_literal_skips_helper(self):
        code = 'ax.text(0, 0, "hi", fontsize=dm.fs(0))\n'
        ids = {i.rule_id for i in lint(code)}
        assert "fontsize-literal" not in ids

    def test_linewidth_literal_fires(self):
        code = "ax.plot(x, y, linewidth=2)\n"
        ids = {i.rule_id for i in lint(code)}
        assert "linewidth-literal" in ids

    def test_linewidth_literal_fires_on_decimal_ge_one(self):
        # 1.5 still bypasses the style → warn.
        code = "ax.plot(x, y, linewidth=2.5)\n"
        ids = {i.rule_id for i in lint(code)}
        assert "linewidth-literal" in ids

    def test_linewidth_literal_allows_zero(self):
        # linewidth=0 is the canonical no-border idiom; must not fire.
        code = "ax.bar(x, y, linewidth=0)\n"
        ids = {i.rule_id for i in lint(code)}
        assert "linewidth-literal" not in ids

    def test_linewidth_literal_allows_sub_one_hairline(self):
        # Sub-1 hairline widths (e.g. 0.3, 0.5, 0.8) are common,
        # intentional decoration in bundled templates and don't
        # conflict with the active style. Must not fire.
        for code in (
            "ax.bar(x, y, edgecolor='white', linewidth=0.3)\n",
            "ax.axvline(0, color='black', linewidth=0.5)\n",
            "ax.plot(x, y, linewidth=0.8)\n",
        ):
            ids = {i.rule_id for i in lint(code)}
            assert "linewidth-literal" not in ids, (
                f"sub-1 linewidth should not fire: {code!r}"
            )

    def test_savefig_direct_fires(self):
        code = 'fig.savefig("out.png")\n'
        ids = {i.rule_id for i in lint(code)}
        assert "savefig-direct" in ids

    def test_savefig_direct_skips_dm_helper(self):
        code = 'dm.save_formats(fig, "out")\n'
        ids = {i.rule_id for i in lint(code)}
        assert "savefig-direct" not in ids

    def test_jet_cmap_fires(self):
        code = 'plt.imshow(z, cmap="jet")\n'
        ids = {i.rule_id for i in lint(code)}
        assert "jet-cmap" in ids

    def test_jet_cmap_skips_perceptual(self):
        code = 'plt.imshow(z, cmap="viridis")\n'
        ids = {i.rule_id for i in lint(code)}
        assert "jet-cmap" not in ids

    def test_oversize_width_fires(self):
        code = 'dm.subplots(width="20cm")\n'
        ids = {i.rule_id for i in lint(code)}
        assert "oversize-width" in ids

    def test_oversize_width_skips_within_limit(self):
        code = 'dm.subplots(width="17cm")\n'
        ids = {i.rule_id for i in lint(code)}
        assert "oversize-width" not in ids

    def test_oversize_width_fractional_above_17(self):
        """17.x fractional widths above 17.0 are also flagged."""
        for w in ("17.5cm", "17.1cm", "17.99cm"):
            code = f'dm.subplots(width="{w}")\n'
            ids = {i.rule_id for i in lint(code)}
            assert "oversize-width" in ids, f"{w} should fire oversize-width"

    def test_oversize_width_skips_17_0(self):
        """Exactly 17 cm (= col2 max) is allowed."""
        for w in ("17.0cm", "17cm"):
            code = f'dm.subplots(width="{w}")\n'
            ids = {i.rule_id for i in lint(code)}
            assert "oversize-width" not in ids, f"{w} should not fire"

    def test_dpi_arg_fires_simple(self):
        code = "plt.figure(dpi=200)\n"
        ids = {i.rule_id for i in lint(code)}
        assert "dpi-arg" in ids

    def test_dpi_arg_is_critical(self):
        """Severity was raised from ``warning`` to ``critical`` in
        0.4.x to align with ``00-index.md`` and ``figsize-direct``."""
        code = "plt.figure(dpi=200)\n"
        issues = [i for i in lint(code) if i.rule_id == "dpi-arg"]
        assert issues, "dpi-arg rule did not fire"
        assert issues[0].severity == "critical"

    def test_dpi_arg_fires_with_inner_parens(self):
        # Regression: the prior ``[^)]*`` regex stopped at the first
        # ``)``, missing this common spelling.
        for code in (
            "plt.figure(figsize=(8, 6), dpi=200)\n",
            'dm.subplots(width="9cm", figsize=(7, 4), dpi=300)\n',
            "plt.subplots(nrows=2, ncols=3, figsize=(8, 4), dpi=150)\n",
        ):
            ids = {i.rule_id for i in lint(code)}
            assert "dpi-arg" in ids, (
                f"dpi= inside subplots/figure with inner parens "
                f"should still fire: {code!r}"
            )

    def test_dpi_arg_skips_savefig(self):
        # ``savefig(dpi=...)`` is owned by the ``savefig-direct`` rule,
        # not ``dpi-arg``.
        code = 'fig.savefig("out.png", dpi=300)\n'
        ids = {i.rule_id for i in lint(code)}
        assert "dpi-arg" not in ids


class TestDedupeKey:
    """Issues on the same line at different columns must NOT collapse.

    Regression for the prior ``(rule_id, line)`` dedupe key, which hid
    the second violation from auto-fixers.
    """

    def test_two_figsize_calls_same_line(self) -> None:
        # Two ``plt.subplots(figsize=...)`` invocations chained on a
        # single line. Both should be reported.
        code = (
            "fig1, ax1 = plt.subplots(figsize=(5,3)); "
            "fig2, ax2 = plt.subplots(figsize=(7,4))\n"
        )
        issues = [i for i in lint(code) if i.rule_id == "figsize-direct"]
        assert len(issues) == 2, (
            f"expected 2 figsize-direct issues on the same line, "
            f"got {len(issues)}: {issues}"
        )
        # Distinct columns, both populated.
        cols = {i.column for i in issues}
        assert None not in cols
        assert len(cols) == 2

    def test_two_figsize_calls_different_lines(self) -> None:
        # Sanity: cross-line dedup still doesn't collapse legitimate
        # separate occurrences.
        code = (
            "fig1, ax1 = plt.subplots(figsize=(5,3))\n"
            "fig2, ax2 = plt.subplots(figsize=(7,4))\n"
        )
        issues = [i for i in lint(code) if i.rule_id == "figsize-direct"]
        assert len(issues) == 2

    def test_issue_carries_column(self) -> None:
        code = "plt.subplots(figsize=(5,3))\n"
        issues = [i for i in lint(code) if i.rule_id == "figsize-direct"]
        assert issues
        assert issues[0].column is not None and issues[0].column >= 0


class TestFormatReportFixSuggestion:
    """``format_report`` must emit ``→ fix:`` lines for rules whose
    YAML entry includes a ``fix_suggestion``."""

    def test_fix_suggestion_emitted(self) -> None:
        code = "plt.subplots(figsize=(5, 3))\n"
        report = format_report(lint(code))
        assert "→ fix:" in report, (
            f"format_report should include a fix line; got:\n{report}"
        )
        # The bundled fix_suggestion for figsize-direct uses ``dm.subplots``.
        assert "dm.subplots" in report

    def test_no_fix_line_when_clean(self) -> None:
        report = format_report([])
        assert "→ fix:" not in report

    def test_issue_default_fix_suggestion_none(self) -> None:
        # Hand-built Issue without fix_suggestion still renders without
        # the ``→ fix:`` line.
        issues = [
            Issue(
                rule_id="figsize-direct",
                severity="critical",
                message="msg",
                line=5,
            )
        ]
        report = format_report(issues)
        assert "→ fix:" not in report


class TestBundledTemplatesLintClean:
    """The 18 prompt-asset templates ship as the canonical examples
    agents copy from. They must lint clean against the very rules
    they teach — otherwise the linter contradicts the templates.
    """

    def test_all_prompt_templates_lint_clean(self) -> None:
        from pathlib import Path

        from dartwork_mpl.lint import lint

        templates_dir = (
            Path(__file__).resolve().parent.parent
            / "src"
            / "dartwork_mpl"
            / "asset"
            / "prompt"
            / "05-templates"
        )
        assert templates_dir.is_dir(), (
            f"templates directory missing: {templates_dir}"
        )
        violations: dict[str, list[str]] = {}
        for tpl in sorted(templates_dir.glob("*.py")):
            issues = lint(tpl.read_text(encoding="utf-8"))
            if issues:
                violations[tpl.name] = [
                    f"[{i.severity}] {i.rule_id} (line {i.line}): "
                    f"{i.message.strip().splitlines()[0]}"
                    for i in issues
                ]
        assert not violations, (
            f"Bundled prompt templates have lint violations: {violations}"
        )
