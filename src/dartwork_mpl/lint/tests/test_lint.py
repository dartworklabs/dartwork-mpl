"""Tests for dartwork_mpl.lint — anti-pattern detection engine."""

from __future__ import annotations

import ast
import io
import random
import tokenize

import pytest
import yaml

from dartwork_mpl.lint import (
    Issue,
    Rule,
    apply_lint_fixes,
    format_report,
    lint,
    load_rules,
    migrate_legacy_code,
)

GOOD_CODE = """
import matplotlib.pyplot as plt
import dartwork_mpl as dm

fig, ax = plt.subplots(figsize=dm.figsize("13cm", "wide"))
ax.bar(["A", "B"], [1, 2], color="dc.blue6")
dm.simple_layout(fig)
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
    """The bundled anti-pattern rule catalog loads and contains the expected rule ids."""

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
    """Detection of core anti-patterns and the line and message reported per issue."""

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
    """Linting with a caller-supplied rule subset applies only those rules."""

    def test_custom_rules_subset(self):
        all_rules = load_rules()
        subset = [r for r in all_rules if r.id == "figsize-direct"]
        issues = lint(BAD_TIGHT_LAYOUT, rules=subset)
        # No figsize-direct in BAD_TIGHT_LAYOUT, so subset finds nothing.
        assert all(i.rule_id == "figsize-direct" for i in issues)
        # And tight-layout is filtered out.
        assert not any(i.rule_id == "tight-layout" for i in issues)


class TestIssue:
    """Lint issues are immutable values."""

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
        code = 'plt.subplots(figsize=dm.figsize("20cm"))\n'
        ids = {i.rule_id for i in lint(code)}
        assert "oversize-width" in ids

    def test_oversize_width_skips_within_limit(self):
        code = 'plt.subplots(figsize=dm.figsize("17cm"))\n'
        ids = {i.rule_id for i in lint(code)}
        assert "oversize-width" not in ids

    def test_oversize_width_fractional_above_17(self):
        """17.x fractional widths above 17.0 are also flagged."""
        for w in ("17.5cm", "17.1cm", "17.99cm"):
            code = f'plt.subplots(figsize=dm.figsize("{w}"))\n'
            ids = {i.rule_id for i in lint(code)}
            assert "oversize-width" in ids, f"{w} should fire oversize-width"

    def test_oversize_width_skips_17_0(self):
        """Exactly 17 cm (= col2 max) is allowed."""
        for w in ("17.0cm", "17cm"):
            code = f'plt.subplots(figsize=dm.figsize("{w}"))\n'
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
            'plt.subplots(figsize=dm.figsize("9cm"), dpi=300)\n',
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


class TestMultirowSubplotsNoGridspecKw:
    """Coverage for the info-level subplot-overlap prevention rule."""

    def test_fires_on_default_hspace(self):
        code = 'fig, axs = plt.subplots(2, 1, figsize=dm.figsize("9cm", 1.2))\n'
        ids = {i.rule_id for i in lint(code)}
        assert "multirow-subplots-no-gridspec-kw" in ids

    def test_fires_on_2x2(self):
        code = "fig, axs = plt.subplots(2, 2, figsize=dm.figsize('16cm'))\n"
        ids = {i.rule_id for i in lint(code)}
        assert "multirow-subplots-no-gridspec-kw" in ids

    def test_skipped_when_gridspec_kw_present(self):
        code = (
            "fig, axs = plt.subplots(2, 1, figsize=dm.figsize('9cm'), "
            'gridspec_kw={"hspace": 0.55})\n'
        )
        ids = {i.rule_id for i in lint(code)}
        assert "multirow-subplots-no-gridspec-kw" not in ids

    def test_skipped_when_sharex(self):
        # sharex=True hides the upper xtick + xlabel, eliminating the
        # collision risk with the lower title.
        code = "fig, axs = plt.subplots(2, 1, sharex=True)\n"
        ids = {i.rule_id for i in lint(code)}
        assert "multirow-subplots-no-gridspec-kw" not in ids

    def test_skipped_when_single_row(self):
        code = "fig, axs = plt.subplots(1, 3, figsize=dm.figsize('17cm'))\n"
        ids = {i.rule_id for i in lint(code)}
        assert "multirow-subplots-no-gridspec-kw" not in ids

    def test_fires_on_line_wrapped_call(self):
        # The opening `plt.subplots(` and the nrows arg sit on separate
        # lines — the old single-line `^...$` detector missed this.
        code = (
            "fig, axs = plt.subplots(\n"
            '    2, 1, figsize=dm.figsize("9cm", 1.2)\n'
            ")\n"
        )
        ids = {i.rule_id for i in lint(code)}
        assert "multirow-subplots-no-gridspec-kw" in ids

    def test_skipped_when_gridspec_kw_on_later_line(self):
        # gridspec_kw lives on a continuation line of a wrapped call; the
        # bounded look-ahead must still find it and suppress the hint.
        code = (
            "fig, axs = plt.subplots(\n"
            "    2, 1,\n"
            '    gridspec_kw={"hspace": 0.55},\n'
            ")\n"
        )
        ids = {i.rule_id for i in lint(code)}
        assert "multirow-subplots-no-gridspec-kw" not in ids


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
        # The bundled fix_suggestion for figsize-direct points to
        # ``figsize=dm.figsize(...)``.
        assert "dm.figsize" in report

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


class TestAutoFixTableContract:
    """``_AUTO_FIX_TABLE`` must stay aligned with the SSOT catalog.

    Each rewrite is labelled with a rule_id; ``apply_lint_fixes`` keys
    its applied/unfixed diff on it. A label with no matching SSOT rule
    is silently dead code (the diff can never attribute to it).
    """

    def test_auto_fix_rule_ids_exist_in_ssot(self) -> None:
        from dartwork_mpl.lint.fix import _AUTO_FIX_TABLE

        ssot_ids = {r.id for r in load_rules()}
        table_ids = set(_AUTO_FIX_TABLE)
        orphans = table_ids - ssot_ids
        assert not orphans, (
            f"_AUTO_FIX_TABLE references rule_ids absent from the "
            f"anti-pattern SSOT: {orphans}"
        )

    def test_cm2in_is_not_auto_substituted(self) -> None:
        # ``dm.cm2in`` (inches) must NOT be rewritten to ``dm.cm`` (a
        # Length) — the two are not interchangeable. The legacy form is
        # left untouched for ``migrate_legacy_code`` to handle in context.
        from dartwork_mpl.lint import apply_lint_fixes

        fixed, _applied, _unfixed = apply_lint_fixes("x = dm.cm2in(13)\n")
        assert "dm.cm2in(13)" in fixed


class TestLiteralColorNames:
    """Static literal checks follow live registries without executing source."""

    def test_invalid_literal_colormap_is_reported(self):
        """A fabricated dc map is rejected at its literal source position."""
        code = '\nax.imshow(data, cmap="dc.coolwarm")'
        issues = [i for i in lint(code) if i.rule_id == "invalid-colormap-name"]
        assert len(issues) == 1
        assert issues[0].severity == "critical"
        assert issues[0].line == 2
        assert issues[0].column == code.index('"dc.coolwarm"')
        assert "matplotlib.colormaps" in issues[0].fix_suggestion

    def test_invalid_literal_color_is_reported(self):
        """Unknown named colors in plotting kwargs are actionable errors."""
        issues = lint('ax.plot(x, y, color="dc.not_a_color")')
        assert any(i.rule_id == "invalid-color-name" for i in issues)

    def test_valid_names_follow_live_registries(self):
        """A deterministic registry sample and scalar color forms stay valid."""
        import random

        import matplotlib
        from matplotlib.colors import get_named_colors_mapping

        randomizer = random.Random(489)
        maps = randomizer.sample(sorted(matplotlib.colormaps), 12)
        colors = randomizer.sample(sorted(get_named_colors_mapping()), 12)
        colors += ["C0", "C12", "#123456", "0.5", "none"]
        for name in maps:
            issues = lint(f"ax.imshow(data, cmap={name!r})")
            assert not any(
                i.rule_id == "invalid-colormap-name" for i in issues
            ), name
        for name in colors:
            issues = lint(f"ax.plot(x, y, color={name!r})")
            assert not any(i.rule_id == "invalid-color-name" for i in issues), (
                name
            )

    def test_custom_runtime_registrations_are_live(self):
        """Registry changes after earlier lint calls are accepted immediately."""
        import matplotlib
        from matplotlib.colors import ListedColormap, get_named_colors_mapping

        map_name = "_dartwork_lint_test_map_489"
        color_name = "_dartwork_lint_test_color_489"
        code = (
            f"ax.imshow(data, cmap={map_name!r})\n"
            f"ax.plot(x, y, color={color_name!r})"
        )
        assert {i.rule_id for i in lint(code)} >= {
            "invalid-colormap-name",
            "invalid-color-name",
        }
        mapping = get_named_colors_mapping()
        matplotlib.colormaps.register(
            ListedColormap(["black", "white"], name=map_name)
        )
        mapping[color_name] = "#123456"
        try:
            assert not any(i.rule_id.startswith("invalid-") for i in lint(code))
        finally:
            matplotlib.colormaps.unregister(map_name)
            del mapping[color_name]
        assert {i.rule_id for i in lint(code)} >= {
            "invalid-colormap-name",
            "invalid-color-name",
        }

    def test_inline_registration_and_sentinels_are_not_rejected(self):
        """Explicit registrations and context-specific color sentinels are legal."""
        snippets = [
            'import matplotlib as m\nm.colormaps.register(cmap, name="custom")\n'
            'ax.imshow(data, cmap="custom")',
            "from matplotlib import colormaps as maps\nmaps.register(custom_map)\n"
            'ax.imshow(data, cmap="custom")',
            "import matplotlib.colors as mc\n"
            'mc.get_named_colors_mapping()["custom"] = "red"\n'
            'ax.plot(x, y, color="custom")',
            "from matplotlib.colors import get_named_colors_mapping as mapping\n"
            'mapping()["custom"] = "red"\nax.plot(x, y, color="custom")',
            'ax.scatter(x, y, edgecolor="face")',
            'ax.scatter(x, y, edgecolor="FACE")',
            'ax.plot(x, y, markerfacecolor="auto", markeredgecolor="auto")',
            'ax.plot(x, y, markerfacecolor="AUTO", markeredgecolor="AUTO")',
        ]
        for code in snippets:
            assert not any(
                i.rule_id.startswith("invalid-") for i in lint(code)
            ), code
        assert any(
            i.rule_id == "invalid-color-name"
            for i in lint('ax.plot(x, y, color="auto")')
        )

    def test_pyplot_aliases_and_get_cmap_are_checked(self):
        """Recognized pyplot calls share checks and preserve separate literals."""
        code = (
            "import matplotlib.pyplot as p\n"
            'p.get_cmap("dc.coolwarm"); p.imshow(data, cmap="dc.coolwarm")\n'
            "from matplotlib import pyplot as chart\n"
            'chart.plot(x, y, color="dc.not_a_color")'
        )
        issues = [i for i in lint(code) if i.rule_id.startswith("invalid-")]
        assert [i.rule_id for i in issues] == [
            "invalid-colormap-name",
            "invalid-colormap-name",
            "invalid-color-name",
        ]
        assert len({i.column for i in issues}) == 3

    def test_static_scope_never_executes_source(self, tmp_path):
        """Imports, dynamic values, unrelated calls, comments and strings are inert."""
        marker = tmp_path / "executed"
        code = (
            "import nonexistent_untrusted_module\n"
            f'open({str(marker)!r}, "w").write("executed")\n'
            '# ax.imshow(data, cmap="dc.coolwarm")\n'
            "example = 'ax.plot(x, y, color=\"dc.not_a_color\")'\n"
            "ax.imshow(data, cmap=choose_map())\n"
            'ax.plot(x, y, color=f"dc.{name}")\n'
            'other.imshow(data, cmap="dc.coolwarm")'
        )
        assert not any(i.rule_id.startswith("invalid-") for i in lint(code))
        assert not marker.exists()

    def test_generated_malformed_source_is_left_unchecked(self):
        """Incomplete fragments never execute or crash the AST name detectors."""
        import random
        import string

        randomizer = random.Random(489)
        for _ in range(30):
            fragment = "".join(randomizer.choices(string.ascii_letters, k=20))
            issues = lint(f'ax.imshow({fragment}, cmap="dc.coolwarm"')
            assert not any(i.rule_id.startswith("invalid-") for i in issues)

    def test_unicode_location_matches_existing_character_offsets(self):
        """Non-ASCII text before a literal cannot shift the reported location."""
        code = 'ax.plot("한글", y, color="dc.not_a_color")'
        issue = next(i for i in lint(code) if i.rule_id == "invalid-color-name")
        assert issue.column == code.index('"dc.not_a_color"')

    def test_inline_mapping_updates_and_dynamic_keys_defer_only_color_checks(
        self,
    ):
        """Direct mapping mutations defer color checks without running registration."""
        from matplotlib.colors import get_named_colors_mapping

        name = "custom_review489"
        registrations = [
            f'mc.get_named_colors_mapping().update({name}="#ff0000")',
            f'mc.get_named_colors_mapping().update({{{name!r}: "red"}})',
            'mc.get_named_colors_mapping()[dynamic_key] = "red"',
        ]
        assert name not in get_named_colors_mapping()
        for registration in registrations:
            code = (
                f"import matplotlib.colors as mc\n{registration}\n"
                f"ax.plot([1, 2], color={name!r})\n"
                'ax.imshow(data, cmap="dc.coolwarm")'
            )
            ids = {issue.rule_id for issue in lint(code)}
            assert "invalid-color-name" not in ids
            assert "invalid-colormap-name" in ids
        assert name not in get_named_colors_mapping()


class TestExecutableDetectionBoundary:
    """Built-in executable rules need syntax and an applicable receiver."""

    @pytest.mark.parametrize(
        "code",
        [
            '# plt.tight_layout()\ntext = "plt.tight_layout()"\n',
            "def tight_layout():\n    return 'local'\ntight_layout()\n",
            "import matplotlib.pyplot as plt\n"
            "class Local:\n"
            "    def tight_layout(self):\n        return 'local'\n"
            "plt = Local()\nresult = plt.tight_layout()\n",
            "class Local:\n"
            "    def draw(self):\n        self.fig.tight_layout()\n",
            "ax.figure.tight_layout()\n",
        ],
        ids=[
            "mentions",
            "local-definition",
            "rebound-plt",
            "self",
            "ax-figure",
        ],
    )
    def test_no_false_critical_for_mentions_or_unproven_methods(self, code):
        """C1 mentions and local/attribute methods are not matplotlib calls."""
        assert not [
            issue for issue in lint(code) if issue.severity == "critical"
        ]

    def test_aliases_keep_style_and_scalar_axes_advisories(self):
        """C1 pyplot/dm aliases and a direct single Axes retain useful findings."""
        code = (
            "import matplotlib.pyplot as p\nimport dartwork_mpl as d\n"
            'p.style.use("ggplot")\n'
            'fig, ax2 = p.subplots(figsize=d.figsize("20cm", "standard"))\n'
            'ax2.plot([0, 1], [0, 1], color="#ff0000", '
            "fontsize=12, linewidth=2)\n"
        )
        issues = {issue.rule_id: issue for issue in lint(code)}
        assert issues.keys() >= {
            "plt-style-use",
            "fontsize-literal",
            "linewidth-literal",
            "raw-hex-color",
            "oversize-width",
        }
        assert issues["plt-style-use"].severity == "warning"
        assert issues["fontsize-literal"].severity == "warning"

    @pytest.mark.parametrize(
        "binding", ["ax = other\n", "del ax\n", "ax, unused = other\n"]
    )
    def test_explicit_conflicts_suppress_canonical_axes_convention(
        self, binding
    ):
        """An omitted import is conventional; an explicit conflicting binding is not."""
        code = binding + 'ax.plot(x, y, color="dc.not_a_color", fontsize=12)\n'
        assert not {issue.rule_id for issue in lint(code)} & {
            "invalid-color-name",
            "fontsize-literal",
        }

    def test_parameters_shadow_all_canonical_receiver_conventions(self):
        """Parameters denote caller objects rather than implicit plotting bindings."""
        code = (
            "def draw(plt, ax, fig, dm):\n"
            "    plt.tight_layout()\n"
            '    ax.plot(x, y, color="dc.not_a_color", fontsize=12)\n'
            '    fig.savefig("out.png")\n'
            "    dm.subplots()\n"
        )
        assert lint(code) == []

    @pytest.mark.parametrize(
        "arguments", ["2, 1", "nrows=count", "1, 1, squeeze=False"]
    )
    def test_array_or_unknown_axes_do_not_gain_scalar_axes_rules(
        self, arguments
    ):
        """A direct subplots tuple alone cannot prove its second target is scalar."""
        code = (
            "import matplotlib.pyplot as p\n"
            f"f, ax2 = p.subplots({arguments})\n"
            'ax2.plot(x, y, color="dc.not_a_color", fontsize=12)\n'
        )
        assert not {issue.rule_id for issue in lint(code)} & {
            "invalid-color-name",
            "fontsize-literal",
        }

    def test_text_only_and_custom_detectors_keep_their_contract(self):
        """Syntax-aware built-ins do not suppress deliberate caller text searches."""
        code = '# Zero-Resize plt.tight_layout()\ntext = "plt.tight_layout()"\n'
        assert any(
            issue.rule_id == "zero-resize-mention" for issue in lint(code)
        )
        rules = [
            Rule("custom-regex", "warning", "regex", r"tight_layout", "seen"),
            Rule("custom-text", "info", "substring", "plt.", "seen"),
        ]
        issues = lint(code, rules=rules)
        assert [issue.rule_id for issue in issues].count("custom-regex") == 2
        assert [issue.rule_id for issue in issues].count("custom-text") == 2


class TestRelativeImports:
    """Local modules named matplotlib never prove native plotting receivers."""

    @pytest.mark.parametrize("level", [".", ".."])
    @pytest.mark.parametrize("receiver", ["p", "plt", "pyplot"])
    @pytest.mark.parametrize("operation", ["lint", "fix", "migrate"])
    def test_relative_pyplot_import_preserves_unrelated_methods(
        self, level, receiver, operation
    ):
        """Relative pyplot names neither justify diagnostics nor source edits."""
        alias = "" if receiver == "pyplot" else f" as {receiver}"
        code = (
            "import dartwork_mpl as dm\n"
            f"from {level}matplotlib import pyplot{alias}\n"
            f'{receiver}.style.use("scientific")\n'
            f"fig = {receiver}.figure()\nfig.tight_layout()\n"
        )
        if operation == "lint":
            assert lint(code) == []
        elif operation == "fix":
            assert apply_lint_fixes(code) == (code, [], [])
        else:
            assert migrate_legacy_code(code) == code

    @pytest.mark.parametrize("level", [".", ".."])
    @pytest.mark.parametrize("constructor", ["F", "Figure"])
    @pytest.mark.parametrize("operation", ["lint", "fix", "migrate"])
    def test_relative_figure_import_preserves_unrelated_methods(
        self, level, constructor, operation
    ):
        """A relative Figure constructor grants no native type or layout hint."""
        alias = "" if constructor == "Figure" else f" as {constructor}"
        code = (
            "import dartwork_mpl as dm\n"
            f"from {level}matplotlib.figure import Figure{alias}\n"
            f"fig = {constructor}()\nfig.tight_layout()\n"
        )
        if operation == "lint":
            assert lint(code) == []
        elif operation == "fix":
            assert apply_lint_fixes(code) == (code, [], [])
        else:
            assert migrate_legacy_code(code) == code

    @pytest.mark.parametrize("level", [".", ".."])
    def test_relative_import_shadows_existing_canonical_pyplot_proof(
        self, level
    ):
        """An explicit local import invalidates prior and conventional plt facts."""
        code = (
            "import matplotlib.pyplot as plt\nimport dartwork_mpl as dm\n"
            f"from {level}matplotlib import pyplot as plt\n"
            'plt.style.use("scientific")\nplt.tight_layout()\n'
        )
        assert lint(code) == []
        assert apply_lint_fixes(code) == (code, [], [])
        assert migrate_legacy_code(code) == code


class TestProvenAutoFix:
    """A fix requires local binding proof and preserves every refused source byte."""

    @pytest.mark.parametrize(
        ("imports", "construction", "owner"),
        [
            ("import matplotlib.pyplot as p", "f = p.figure()", "d"),
            ("from matplotlib import pyplot as p", "f, ax = p.subplots()", "d"),
            ("import matplotlib.pyplot", "f = matplotlib.pyplot.figure()", "d"),
        ],
    )
    def test_complete_proven_figure_call_is_fixed(
        self, imports, construction, owner
    ):
        """Proven pyplot Figure constructors preserve the actual receiver."""
        code = f"{imports}\nimport dartwork_mpl as {owner}\n{construction}\nf.tight_layout()\n"
        fixed, applied, unfixed = apply_lint_fixes(code)
        assert fixed == code.replace(
            "f.tight_layout()", f"{owner}.simple_layout(f)"
        )
        assert [(issue.rule_id, issue.column) for issue in applied] == [
            ("tight-layout", code.index("tight_layout"))
        ]
        assert unfixed == []
        assert apply_lint_fixes(fixed) == (fixed, [], [])

    @pytest.mark.parametrize(
        ("imports", "constructor"),
        [
            ("from matplotlib.figure import Figure as F", "F"),
            ("from matplotlib.figure import Figure", "Figure"),
        ],
    )
    def test_bare_figure_constructor_is_detected_but_exactly_unfixed(
        self, imports, constructor
    ):
        """A working native bare Figure cannot be rewritten to a renderer failure."""
        # These two constructors formerly shared the safe-fix expectation above.
        # Native tight_layout supplies a renderer; dm.simple_layout requires one.
        code = (
            f"{imports}\nimport dartwork_mpl as d\n"
            f'f = {constructor}(figsize=d.figsize("13cm", "standard"))\n'
            "f.add_subplot().plot([0, 1], [0, 1])\n"
            "f.tight_layout()\nresult = len(f.axes)\n"
        )
        fixed, applied, unfixed = apply_lint_fixes(code)
        assert fixed == code
        assert applied == []
        assert [(issue.rule_id, issue.severity) for issue in unfixed] == [
            ("tight-layout", "critical")
        ]
        for source in (code, fixed):
            namespace = {}
            exec(compile(source, "trusted-bare-figure.py", "exec"), namespace)
            assert namespace["result"] == 1

    def test_nonaliased_dm_import_uses_its_real_bound_name(self):
        """A nonaliased package import establishes dartwork_mpl, never an invented dm."""
        code = (
            "import matplotlib.pyplot as p\nimport dartwork_mpl\n"
            'p.style.use("scientific")\nf = p.figure()\nf.tight_layout()\n'
        )
        fixed, applied, unfixed = apply_lint_fixes(code)
        assert fixed == code.replace(
            "p.style.use", "dartwork_mpl.style.use"
        ).replace("f.tight_layout()", "dartwork_mpl.simple_layout(f)")
        assert len(applied) == 2
        assert unfixed == []

    @pytest.mark.parametrize(
        "statement",
        [
            "self.fig.tight_layout()",
            "ax.figure.tight_layout()",
            "plt.tight_layout()",
            "unknown.tight_layout()",
            "fig.tight_layout(pad=1)",
            "fig.tight_layout(*args)",
        ],
    )
    def test_unsafe_layout_calls_are_exactly_refused(self, statement):
        """C2 refuses attribute suffix edits, implicit figures, and nonempty calls."""
        code = (
            "import matplotlib.pyplot as plt\nimport dartwork_mpl as dm\n"
            "fig, ax = plt.subplots()\n" + statement + "\n"
        )
        fixed, applied, unfixed = apply_lint_fixes(code)
        assert fixed == code
        assert applied == []
        tight = [issue for issue in unfixed if issue.rule_id == "tight-layout"]
        if statement.startswith(("fig.", "plt.")):
            assert len(tight) == 1 and tight[0].severity == "critical"
        else:
            assert tight == []

    @pytest.mark.parametrize(
        "code",
        [
            "import matplotlib.pyplot as plt\nplt.tight_layout()\n",
            "import matplotlib.pyplot as plt\nfig = plt.figure()\nfig.tight_layout()\n",
            "import dartwork_mpl as dm\nfig.tight_layout()\n",
            'import matplotlib.pyplot as plt\nplt.style.use("scientific")\n',
        ],
    )
    def test_missing_names_do_not_gain_invented_bindings(self, code):
        """Canonical snippet diagnostics do not authorize an autofix binding."""
        fixed, applied, unfixed = apply_lint_fixes(code)
        assert fixed == code
        assert applied == []
        assert unfixed

    @pytest.mark.parametrize(
        "argument", ['"ggplot"', '"not-a-preset"', '["scientific"]', "name"]
    )
    def test_unsupported_or_dynamic_style_is_unfixed(self, argument):
        """C2 ggplot and nonliteral or list requests cannot become dm presets."""
        code = (
            "import matplotlib.pyplot as p\nimport dartwork_mpl as d\n"
            f"p.style.use({argument})\n"
        )
        fixed, applied, unfixed = apply_lint_fixes(code)
        assert fixed == code
        assert applied == []
        assert [(issue.rule_id, issue.severity) for issue in unfixed] == [
            ("plt-style-use", "warning")
        ]

    @pytest.mark.parametrize(
        "preset", ["scientific", "presentation-kr", "report"]
    )
    def test_supported_single_literal_style_uses_proven_alias(self, preset):
        """Supported preset families keep literal spelling and receiver aliases."""
        code = (
            "from matplotlib import pyplot as chart\n"
            "import dartwork_mpl as drawing\n"
            f"chart.style.use({preset!r})\n"
        )
        fixed, applied, unfixed = apply_lint_fixes(code)
        assert fixed == code.replace("chart.style.use", "drawing.style.use")
        assert len(applied) == 1
        assert applied[0].column == code.index("chart.style.use")
        assert unfixed == []

    @pytest.mark.parametrize(
        "interruption",
        [
            "p = other\n",
            "d = other\n",
            "del p\n",
            "del d\n",
            "p.style = other\n",
            "p.style.use = replacement\n",
            "d.style.use = replacement\n",
        ],
    )
    def test_rebound_or_overwritten_style_owners_do_not_authorize_fix(
        self, interruption
    ):
        """Relevant owner and attribute writes prevent safe-looking style edits."""
        code = (
            "import matplotlib.pyplot as p\nimport dartwork_mpl as d\n"
            + interruption
            + 'p.style.use("scientific")\n'
        )
        assert apply_lint_fixes(code)[0:2] == (code, [])

    @pytest.mark.parametrize(
        "interruption",
        [
            "fig = other\n",
            "del fig\n",
            "dm = other\n",
            "fig.tight_layout = replacement\n",
            "dm.simple_layout = replacement\n",
            "if condition:\n    fig = other\n",
            "for fig in others:\n    pass\n",
            "try:\n    fig = other\nexcept Exception:\n    pass\n",
        ],
    )
    def test_invalidated_bindings_never_authorize_layout_edits(
        self, interruption
    ):
        """Assignments, deletes, relevant writes and ambiguous flow remove proof."""
        code = (
            "import matplotlib.pyplot as plt\nimport dartwork_mpl as dm\n"
            "fig = plt.figure()\n" + interruption + "fig.tight_layout()\n"
        )
        fixed, applied, _unfixed = apply_lint_fixes(code)
        assert fixed == code
        assert applied == []

    @pytest.mark.parametrize(
        "code",
        [
            "import matplotlib.pyplot as p\nimport dartwork_mpl as d\n"
            "f = p.figure()\ndef draw():\n    f.tight_layout()\n",
            "def draw(f, d):\n    f.tight_layout()\n",
            "import matplotlib.pyplot as p\nimport dartwork_mpl as d\n"
            "f = p.figure()\ng = f\ng.tight_layout()\n",
            "import matplotlib.pyplot as p\nimport dartwork_mpl as d\n"
            "f = p.figure()\ndef draw():\n    global f, d\n    f.tight_layout()\n",
            "def outer():\n    import matplotlib.pyplot as p\n"
            "    import dartwork_mpl as d\n    f = p.figure()\n"
            "    def inner():\n        nonlocal f\n        f.tight_layout()\n",
        ],
    )
    def test_outer_scope_and_arbitrary_aliases_supply_no_fix_proof(self, code):
        """The initial proof envelope has neither inherited nor inferred aliases."""
        assert apply_lint_fixes(code)[0:2] == (code, [])

    def test_later_unconditional_import_and_constructor_restore_proof(self):
        """A new explicit binding after conflicting flow permits a later local fix."""
        code = (
            "import matplotlib.pyplot as p\nimport dartwork_mpl as d\n"
            "f = p.figure()\nif condition:\n    f = other\n"
            "import matplotlib.pyplot as p\nimport dartwork_mpl as d\n"
            "f = p.figure()\nf.tight_layout()\n"
        )
        fixed, applied, unfixed = apply_lint_fixes(code)
        assert fixed == code.replace("f.tight_layout()", "d.simple_layout(f)")
        assert len(applied) == 1
        assert unfixed == []

    def test_local_imports_in_complete_function_scope_authorize_fix(self):
        """Local direct imports dominate a call without relying on outer facts."""
        code = (
            "def draw():\n    import matplotlib.pyplot as p\n"
            "    import dartwork_mpl as d\n    f = p.figure()\n"
            "    f.tight_layout()\n"
        )
        fixed, applied, unfixed = apply_lint_fixes(code)
        assert fixed == code.replace("f.tight_layout()", "d.simple_layout(f)")
        assert len(applied) == 1
        assert unfixed == []

    def test_fixed_trusted_fixture_runs_actual_style_and_layout(self):
        """Only this owned fixture executes; accepted fixes reach real dm paths."""
        code = (
            "import matplotlib.pyplot as p\nimport dartwork_mpl as d\n"
            'p.style.use("scientific")\n'
            'f, ax2 = p.subplots(figsize=d.figsize("13cm", "standard"))\n'
            "ax2.plot([0, 1], [0, 1])\nf.tight_layout()\n"
            "result = len(f.axes)\n"
        )
        fixed, applied, unfixed = apply_lint_fixes(code)
        assert len(applied) == 2 and unfixed == []
        namespace = {}
        exec(compile(fixed, "trusted-fixed-fixture.py", "exec"), namespace)
        assert namespace["result"] == 1


class TestAutoFixOccurrenceIdentity:
    """Applied locations refer to the original and survivors to the returned source."""

    def test_mixed_same_line_unicode_crlf_occurrences_do_not_overlap(self):
        """A moved unfixable occurrence cannot be reported as applied as well."""
        code = (
            "import matplotlib.pyplot as p\r\nimport dartwork_mpl as d\r\n"
            "label = '한글 🧭'\r\nf = p.figure()\r\n"
            "f.tight_layout(); f.tight_layout(pad=1); f.tight_layout(); "
            'p.style.use("scientific"); p.style.use("ggplot")\r\n'
        )
        first = code.index("tight_layout")
        survivor = code.index("tight_layout", first + 1)
        third = code.index("tight_layout", survivor + 1)
        style = code.index('p.style.use("scientific")')
        fixed, applied, unfixed = apply_lint_fixes(code)
        applied_keys = {(issue.rule_id, issue.column) for issue in applied}
        assert applied_keys == {
            ("tight-layout", first),
            ("tight-layout", third),
            ("plt-style-use", style),
        }
        assert len(applied) == 3
        original_survivors = {
            ("tight-layout", survivor),
            ("plt-style-use", code.index('p.style.use("ggplot")')),
        }
        assert applied_keys.isdisjoint(original_survivors)
        assert {(issue.rule_id, issue.column) for issue in unfixed} == {
            ("tight-layout", fixed.index("tight_layout")),
            ("plt-style-use", fixed.index('p.style.use("ggplot")')),
        }
        assert unfixed == lint(fixed)
        assert fixed.count("\r\n") == code.count("\r\n")
        assert apply_lint_fixes(fixed) == (fixed, [], unfixed)

    def test_canonical_c2_comment_is_neither_applied_nor_unfixed(self):
        """C2 fixes one real call while retaining the inert later comment exactly."""
        code = (
            "import matplotlib.pyplot as plt\nimport dartwork_mpl as dm\n"
            'dm.style.use("scientific")\n'
            'fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))\n'
            "fig.tight_layout()\n# plt.tight_layout()\nresult = len(fig.axes)\n"
        )
        fixed, applied, unfixed = apply_lint_fixes(code)
        assert fixed == code.replace(
            "fig.tight_layout()", "dm.simple_layout(fig)"
        )
        assert len(applied) == 1
        assert applied[0].column == code.index("tight_layout")
        assert unfixed == []


def _literal_values(source):
    """Read original literal values as an independent preservation oracle."""
    return [
        node.value
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant)
    ]


def _comments(source):
    """Read comment tokens without executing the submitted Python source."""
    return [
        token.string
        for token in tokenize.generate_tokens(io.StringIO(source).readline)
        if token.type == tokenize.COMMENT
    ]


def _seeded_static_fixtures():
    """Build exactly 48 bounded valid fixtures using the accepted seed 314159."""
    rng = random.Random(314159)
    fixtures = []
    for index in range(48):
        pyplot = rng.choice(["plt", "p", "chart"])
        package = rng.choice(["dm", "d", "drawing"])
        figure = rng.choice(["fig", "f", "canvas"])
        newline = rng.choice(["\n", "\r\n"])
        prefix = (
            f"import matplotlib.pyplot as {pyplot}\n"
            f"import dartwork_mpl as {package}\n"
            "label = '한글 🧭'\n"
            'note = """literal\nplt.tight_layout()\ndm.SW\n'
            'plt.style.use("scientific")\n"""\n'
            "# plt.tight_layout(); dm.SW; color='#ff0000'\n"
        )
        style = (
            f'{pyplot}.style.use(\n    "scientific"\n)'
            if index % 2
            else f'{pyplot}.style.use("scientific")'
        )
        creation = rng.choice(
            [
                f"{figure} = {pyplot}.figure()",
                f"{figure}, axis = {pyplot}.subplots()",
            ]
        )
        call = (
            f"{figure}.tight_layout(\n)"
            if index % 4 == 0
            else f"{figure}.tight_layout()"
        )
        count = 2 if index % 3 == 0 else 1
        body = f"{style}\n{creation}\n" + "; ".join([call] * count) + "\n"
        fixed_body = body.replace(
            f"{pyplot}.style.use", f"{package}.style.use"
        ).replace(call, f"{package}.simple_layout({figure})")
        suffix = (
            f'{figure}.tight_layout(pad=0.2); {pyplot}.style.use("ggplot")\n'
            "width = \\\n    dm.SW\n"
        )
        source = (prefix + body + suffix).replace("\n", newline)
        expected = (prefix + fixed_body + suffix).replace("\n", newline)
        fixtures.append((source, expected, count + 1, newline))
    return fixtures


class TestSeededSourcePreservation:
    """Bounded generated sources pin byte, literal, identity and refusal invariants."""

    def test_48_valid_sources_preserve_literals_bytes_and_idempotence(self):
        """Seed 314159 covers aliases, repeats, Unicode, CRLF and continuations."""
        fixtures = _seeded_static_fixtures()
        assert len(fixtures) == 48
        for index, (source, expected, expected_count, newline) in enumerate(
            fixtures
        ):
            evidence = f"seed=314159 case={index} source={source!r}"
            before = lint(source)
            fixed, applied, unfixed = apply_lint_fixes(source)
            assert fixed == expected, evidence
            assert len(applied) == expected_count, evidence
            assert {(i.rule_id, i.column) for i in applied} <= {
                (i.rule_id, i.column) for i in before
            }, evidence
            assert unfixed == lint(fixed), evidence
            assert (
                len([i for i in unfixed if i.rule_id == "tight-layout"]) == 1
            ), evidence
            assert (
                len([i for i in unfixed if i.rule_id == "plt-style-use"]) == 1
            ), evidence
            assert _literal_values(fixed) == _literal_values(source), evidence
            assert _comments(fixed) == _comments(source), evidence
            assert apply_lint_fixes(fixed) == (fixed, [], unfixed), evidence
            migrated = migrate_legacy_code(source)
            try:
                ast.parse(migrated)
            except (SyntaxError, ValueError) as error:
                pytest.fail(f"{evidence} migration became invalid: {error}")
            assert _literal_values(migrated) == _literal_values(source), (
                evidence
            )
            assert all(
                comment in _comments(migrated) for comment in _comments(source)
            ), evidence
            assert migrate_legacy_code(migrated) == migrated, evidence
            if newline == "\r\n":
                assert "\n" not in migrated.replace("\r\n", ""), evidence

    def test_24_malformed_sources_are_exactly_refused(self):
        """AST and tokenization failures preserve every original character."""
        mutations = [
            "\n(\n",
            '\ntext = """unterminated\n',
            "\nif :\n    pass\n",
            "\n    unexpected_indent = 1\n",
            "\ntext = 'unterminated\n",
            "\x00",
        ]
        for index, (source, _expected, _count, _newline) in enumerate(
            _seeded_static_fixtures()[:24]
        ):
            malformed = source + mutations[index % len(mutations)]
            evidence = f"seed=314159 malformed={index} source={malformed!r}"
            with pytest.raises((SyntaxError, ValueError)):
                ast.parse(malformed)
            fixed, applied, unfixed = apply_lint_fixes(malformed)
            assert fixed == malformed, evidence
            assert applied == [], evidence
            assert not [
                issue for issue in unfixed if issue.severity == "critical"
            ], evidence
            assert migrate_legacy_code(malformed) == malformed, evidence

    def test_all_static_functions_leave_untrusted_source_inert(self, tmp_path):
        """Scanning/fixing/migrating may parse a source string but never execute it."""
        marker = tmp_path / "must-not-execute"
        source = (
            "import nonexistent_untrusted_module\n"
            f'open({str(marker)!r}, "w").write("executed")\n'
            "import matplotlib.pyplot as p\nimport dartwork_mpl as d\n"
            'p.style.use("scientific")\nf = p.figure()\nf.tight_layout()\n'
        )
        lint(source)
        apply_lint_fixes(source)
        migrate_legacy_code(source)
        assert not marker.exists()


class TestCatalogBoundary:
    """Catalog loads reject malformed rules before any source scan can occur."""

    @staticmethod
    def write_catalog(tmp_path, document):
        """Write actual YAML so tests observe the public file-loading boundary."""
        path = tmp_path / "rules.yaml"
        path.write_text(
            yaml.safe_dump(document, sort_keys=False), encoding="utf-8"
        )
        return path

    @staticmethod
    def entry(**changes):
        """Provide one valid rule whose selected field a case can replace."""
        return {
            "id": "probe",
            "severity": "warning",
            "message": "seen\n",
            "detector": {"pattern": "needle"},
            **changes,
        }

    @pytest.mark.parametrize("severity", ["critcal", 7, None, [], {}, True])
    def test_invalid_severity_rejected_at_load(self, tmp_path, severity):
        """Invalid severity values never escape as successfully loaded Rules."""
        path = self.write_catalog(
            tmp_path, {"rules": [self.entry(severity=severity)]}
        )
        with pytest.raises(ValueError, match="severity.*probe"):
            load_rules(path)

    @pytest.mark.parametrize("rule_id", ["probe", "tight-layout"])
    @pytest.mark.parametrize("pattern", ["(", "[", 7, None, [], {}])
    def test_invalid_regex_rejected_at_load(self, tmp_path, rule_id, pattern):
        """Regex type and grammar are checked even for builtin detector IDs."""
        path = self.write_catalog(
            tmp_path,
            {"rules": [self.entry(id=rule_id, detector={"pattern": pattern})]},
        )
        with pytest.raises(ValueError, match=f"regex.*{rule_id}"):
            load_rules(path)

    @pytest.mark.parametrize(
        "document",
        [
            None,
            [],
            "rules",
            {"rules": None},
            {"rules": {}},
            {"rules": "bad"},
            {"rules": [7]},
            {"rules": [{"detector": []}]},
        ],
    )
    def test_invalid_catalog_structure_has_context(self, tmp_path, document):
        """Malformed containers reject with a catalog or rule context."""
        path = self.write_catalog(tmp_path, document)
        with pytest.raises(ValueError, match="[Cc]atalog|[Rr]ule"):
            load_rules(path)

    @pytest.mark.parametrize("field", ["id", "severity", "message", "detector"])
    def test_missing_required_fields_have_context(self, tmp_path, field):
        """Missing construction fields reject consistently at catalog load."""
        entry = self.entry()
        del entry[field]
        path = self.write_catalog(tmp_path, {"rules": [entry]})
        with pytest.raises(ValueError, match="[Rr]ule"):
            load_rules(path)

    def test_seeded_malformed_fields_and_shapes_reject(self, tmp_path):
        """Finite seed-500 malformed inputs reject without leaking access errors."""
        rng = random.Random(500)
        mutations = (
            [{"severity": "bad-" + str(rng.randrange(10000))} for _ in range(8)]
            + [{"id": value} for value in [None, 3, [], {}]]
            + [{"message": value} for value in [None, 3, [], {}]]
            + [
                {"detector": {"kind": value}}
                for value in [None, 3, [], {}, "unknown"]
            ]
            + [
                {"detector": {"kind": "ast", "check": value}}
                for value in [None, 3, [], {}, "unknown"]
            ]
            + [
                {"detector": {"pattern": "(" * rng.randrange(1, 8)}}
                for _ in range(8)
            ]
            + [
                {"detector": {"kind": "substring", "literal": value}}
                for value in [None, 3, [], {}]
            ]
            + [{"detector": value} for value in [None, 3, "bad", []]]
            + [
                {"detector": {"kind": "substring"}},
                {"detector": {"kind": "ast"}},
            ]
        )
        rng.shuffle(mutations)
        for index, mutation in enumerate(mutations):
            path = self.write_catalog(
                tmp_path, {"rules": [self.entry(**mutation)]}
            )
            with pytest.raises(ValueError, match="rule") as caught:
                load_rules(path)
            assert str(caught.value), (500, index, mutation)

    @pytest.mark.parametrize("document", [{}, {"rules": []}])
    def test_empty_catalogs_remain_valid(self, tmp_path, document):
        """An absent rules key and explicit empty list still load as no rules."""
        assert load_rules(self.write_catalog(tmp_path, document)) == []

    def test_supported_detectors_defaults_and_open_metadata(self, tmp_path):
        """Valid kinds retain strings, defaults, optional metadata, and order."""
        entries = [
            self.entry(
                id="implicit",
                detector={"pattern": "^needle$"},
                why={"open": True},
                extra="ignored",
            ),
            self.entry(
                id="explicit",
                severity="critical",
                detector={"kind": "regex", "pattern": "needle"},
            ),
            self.entry(
                id="text",
                severity="info",
                detector={"kind": "substring", "literal": ""},
                fix_suggestion=7,
            ),
            self.entry(
                id="map", detector={"kind": "ast", "check": "colormap-name"}
            ),
            self.entry(
                id="color", detector={"kind": "ast", "check": "color-name"}
            ),
        ]
        rules = load_rules(
            self.write_catalog(
                tmp_path, {"version": "ignored", "rules": entries}
            )
        )
        assert [
            (r.id, r.severity, r.detector_kind, r.detector_value) for r in rules
        ] == [
            ("implicit", "warning", "regex", "^needle$"),
            ("explicit", "critical", "regex", "needle"),
            ("text", "info", "substring", ""),
            ("map", "warning", "ast", "colormap-name"),
            ("color", "warning", "ast", "color-name"),
        ]
        assert rules[0].message == "seen"
        assert rules[0].why == {"open": True}
        assert rules[2].fix_suggestion == 7
        assert [
            issue.line for issue in lint("other\nneedle\n", rules=rules[:1])
        ] == [2]
        assert lint("plt.tight_layout()", rules=[]) == []
        assert (
            Rule("direct", "custom", "custom", "value", "message").severity
            == "custom"
        )

    def test_path_reread_preserves_old_snapshot_and_custom_override(
        self, tmp_path
    ):
        """Same-path reloads observe edits while previous rule lists remain values."""
        path = self.write_catalog(
            tmp_path,
            {
                "rules": [
                    self.entry(
                        id="tight-layout",
                        detector={"kind": "substring", "literal": "needle"},
                    ),
                    self.entry(
                        id="second",
                        severity="info",
                        detector={"pattern": "other"},
                    ),
                ]
            },
        )
        first = load_rules(path)
        self.write_catalog(
            tmp_path,
            {
                "rules": [
                    self.entry(
                        severity="critical", detector={"pattern": "changed"}
                    )
                ]
            },
        )
        second = load_rules(path)
        issues = lint("other needle", rules=first)
        assert [
            (issue.rule_id, issue.severity, issue.snippet) for issue in issues
        ] == [
            ("tight-layout", "warning", "other needle"),
            ("second", "info", "other needle"),
        ]
        assert [issue.rule_id for issue in lint("changed", rules=second)] == [
            "probe"
        ]
        assert lint("changed", rules=first) == []

    def test_filesystem_and_yaml_syntax_errors_remain_native(self, tmp_path):
        """Catalog validation does not conceal file access or YAML parse failures."""
        with pytest.raises(FileNotFoundError):
            load_rules(tmp_path / "missing.yaml")
        path = tmp_path / "broken.yaml"
        path.write_text("rules: [", encoding="utf-8")
        with pytest.raises(yaml.YAMLError):
            load_rules(path)
