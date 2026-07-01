"""Golden tests for ``dartwork_mpl.lint.migrate_legacy_code`` (T4)."""

from __future__ import annotations

import dartwork_mpl as dm
from dartwork_mpl.lint import migrate_legacy_code


class TestSafeSubstitutions:
    """Pass 1 — patterns whose 0.4 replacement is unambiguous."""

    def test_cm2in_becomes_cm(self) -> None:
        out = migrate_legacy_code("x = dm.cm2in(9)")
        assert "dm.cm(9)" in out
        assert "dm.cm2in" not in out

    def test_plt_style_use_becomes_dm_style_use(self) -> None:
        out = migrate_legacy_code('plt.style.use("scientific")')
        assert 'dm.style.use("scientific")' in out
        assert "plt.style.use" not in out

    def test_plt_subplots_unchanged(self) -> None:
        # ``plt.subplots`` is the new canonical entry point — no rewrite.
        out = migrate_legacy_code("fig, ax = plt.subplots()")
        assert out == "fig, ax = plt.subplots()"

    def test_safe_pass_does_not_add_hint_comments(self) -> None:
        out = migrate_legacy_code("x = dm.cm2in(9)\n")
        assert "TODO(dm-migrate)" not in out


class TestHintComments:
    """Pass 2 — context-dependent patterns get TODO hints above."""

    def test_dm_sw_gets_hint(self) -> None:
        out = migrate_legacy_code("w = dm.SW")
        assert "# TODO(dm-migrate):" in out
        assert "dm.SW" in out  # original line preserved
        assert "dm.col1" in out  # hint mentions replacement

    def test_dm_fs_single_gets_hint(self) -> None:
        out = migrate_legacy_code("size = dm.FS_SINGLE")
        assert "TODO(dm-migrate)" in out
        assert "dm.FS_*" in out
        assert "dm.figsize" in out

    def test_widths_dict_gets_hint(self) -> None:
        out = migrate_legacy_code('w = dm.WIDTHS["SW"]')
        assert "TODO(dm-migrate)" in out
        assert "dm.WIDTHS" in out

    def test_figsize_literal_gets_hint(self) -> None:
        out = migrate_legacy_code("fig, ax = plt.subplots(figsize=(8, 6))")
        # ``plt.subplots`` itself is fine — it's the raw ``figsize=(w,h)``
        # tuple that needs a hint pointing at ``dm.figsize(...)``.
        assert "dm.figsize" in out
        assert "TODO(dm-migrate)" in out
        assert "figsize=(8, 6)" in out  # original kept

    def test_tight_layout_gets_hint(self) -> None:
        out = migrate_legacy_code("plt.tight_layout()")
        assert "TODO(dm-migrate)" in out
        assert "tight_layout()" in out
        assert "simple_layout" in out  # hint mentions replacement

    def test_agent_utils_gets_hint(self) -> None:
        out = migrate_legacy_code("from dm.agent_utils import lint_code")
        assert "TODO(dm-migrate)" in out
        assert "agent_utils" in out

    def test_xplot_gets_hint(self) -> None:
        out = migrate_legacy_code("dm.xplot.bar(ax, x, y)")
        assert "TODO(dm-migrate)" in out
        assert "dm.xplot" in out

    def test_dm_subplots_gets_hint(self) -> None:
        # ``dm.subplots`` and ``dm.figure`` were removed; the migrator
        # leaves the call in place but flags it for the agent to rewrite
        # to ``plt.subplots(figsize=dm.figsize(...))``.
        out = migrate_legacy_code('fig, ax = dm.subplots(width="13cm")')
        assert "TODO(dm-migrate)" in out
        assert "plt.subplots(figsize=dm.figsize" in out
        assert 'dm.subplots(width="13cm")' in out  # original kept

    def test_indent_is_preserved_in_hint(self) -> None:
        out = migrate_legacy_code("    w = dm.SW\n")
        # The TODO comment should sit at the same indent as the
        # offending line so the result remains syntactically valid.
        assert "    # TODO(dm-migrate):" in out

    def test_multiple_patterns_one_line_get_multiple_hints(self) -> None:
        out = migrate_legacy_code("dm.SW; dm.WIDTHS['MW']")
        # Two patterns on the same line → two hint comments.
        hint_count = out.count("TODO(dm-migrate)")
        assert hint_count == 2


class TestPassThrough:
    """Inputs without legacy patterns are returned unchanged."""

    def test_modern_code_is_unchanged(self) -> None:
        modern = (
            "import dartwork_mpl as dm\n"
            'dm.style.use("scientific")\n'
            'fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))\n'
            "dm.simple_layout(fig)\n"
        )
        assert migrate_legacy_code(modern) == modern

    def test_empty_input(self) -> None:
        assert migrate_legacy_code("") == ""


class TestNativeApiSurface:
    """T4 contract: lint + migrate are reachable from the package top
    level so offline workflows don't need MCP."""

    def test_lint_code_alias_is_callable(self) -> None:
        # ``dm.lint`` is the module; ``dm.lint_code`` is the function.
        assert callable(dm.lint_code)
        assert dm.lint_code is dm.lint.lint  # same callable

    def test_migrate_alias_is_callable(self) -> None:
        assert callable(dm.migrate_legacy_code)
        assert dm.migrate_legacy_code is dm.lint.migrate_legacy_code

    def test_lint_code_round_trip_on_safe_pass(self) -> None:
        """After the safe substitutions, the resulting source should
        carry no critical issues from the same patterns."""
        legacy = 'import matplotlib.pyplot as plt\nplt.style.use("x")\n'
        rewritten = migrate_legacy_code(legacy)
        issues = dm.lint_code(rewritten)
        # The ``plt.style.use`` rule should no longer fire; any
        # remaining issues must come from rules we didn't touch.
        assert not any(i.rule_id == "plt-style-use" for i in issues)
