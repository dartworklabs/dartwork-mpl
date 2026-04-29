"""Tests for dartwork_mpl.lint — anti-pattern detection engine."""

from __future__ import annotations

from dartwork_mpl.lint import Issue, Rule, lint, load_rules

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
