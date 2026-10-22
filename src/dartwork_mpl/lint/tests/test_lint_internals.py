"""Internal lint representations: the detector union and named refusals.

These pin the private variants the engine narrows on, so a refactor that
reintroduces a bare ``None`` or a string kind shows up as a failing case.
"""

from __future__ import annotations

import pytest

from dartwork_mpl.lint import Rule, lint, load_rules
from dartwork_mpl.lint.catalog import (
    _AstNameDetector,
    _detector_fields,
    _parse_detector,
    _parse_severity,
    _RegexDetector,
    _rule_detector,
    _SubstringDetector,
    _UnsupportedDetector,
)
from dartwork_mpl.lint.fix import (
    EditedSourceRejected,
    EditsOverlap,
    InsideEdit,
    _apply_edits,
    _Edit,
    _original_offset,
)
from dartwork_mpl.lint.syntax import SourceRejected, _parse_source, _Syntax


class TestDetectorUnion:
    """YAML detectors parse once; public Rule strings round-trip through it."""

    @pytest.mark.parametrize(
        ("raw", "detector"),
        [
            ({"pattern": "a+"}, _RegexDetector("a+")),
            ({"kind": "regex", "pattern": "b"}, _RegexDetector("b")),
            ({"kind": "substring", "literal": "x"}, _SubstringDetector("x")),
            (
                {"kind": "ast", "check": "colormap-name"},
                _AstNameDetector("colormap-name"),
            ),
            (
                {"kind": "ast", "check": "color-name"},
                _AstNameDetector("color-name"),
            ),
        ],
    )
    def test_parse_and_round_trip(self, raw, detector) -> None:
        """Each supported mapping parses to its variant and back to Rule strings."""
        parsed = _parse_detector(raw, "rule 'p' (entry 0)")
        assert parsed == detector
        kind, value = _detector_fields(parsed)
        rule = Rule("p", "info", kind, value, "m")
        assert _rule_detector(rule) == detector

    @pytest.mark.parametrize(
        "raw",
        [
            {"pattern": "("},
            {"kind": "substring"},
            {"kind": "ast", "check": "unknown"},
            {"kind": "other"},
            [],
        ],
    )
    def test_unsupported_mapping_is_rejected(self, raw) -> None:
        """No detector variant can be built from an unsupported mapping."""
        with pytest.raises(ValueError, match="rule 'p'"):
            _parse_detector(raw, "rule 'p' (entry 0)")

    @pytest.mark.parametrize(
        ("kind", "value"), [("custom", "x"), ("ast", "unknown")]
    )
    def test_hand_built_unknown_detector_matches_nothing(
        self, kind, value
    ) -> None:
        """A hand-built Rule outside the union is named and scans as empty."""
        rule = Rule("p", "info", kind, value, "m")
        assert _rule_detector(rule) == _UnsupportedDetector(kind, value)
        assert lint("plt.plot(color='nope')\n", rules=[rule]) == []

    def test_bundled_rules_all_parse_to_the_union(self) -> None:
        """Every bundled rule's public strings read back as a supported variant."""
        for rule in load_rules():
            assert not isinstance(_rule_detector(rule), _UnsupportedDetector)

    def test_severity_parse(self) -> None:
        """Only the three catalog severities parse."""
        assert _parse_severity("info", "rule 'p'") == "info"
        with pytest.raises(ValueError, match="severity"):
            _parse_severity("INFO", "rule 'p'")


class TestNamedRefusals:
    """Parsing and editing refusals are values, not ``None``."""

    @pytest.mark.parametrize("code", ["def (:\n", "x = 1 $ 2\n", "x = '\n"])
    def test_malformed_source_is_rejected(self, code) -> None:
        """Malformed source yields SourceRejected with a diagnostic cause."""
        rejected = _parse_source(code)
        assert isinstance(rejected, SourceRejected)
        assert rejected.cause

    def test_valid_source_parses(self) -> None:
        """Valid source yields the syntax value."""
        assert isinstance(_parse_source("x = 1\n"), _Syntax)

    def test_overlapping_edits_are_refused(self) -> None:
        """Two edits over the same characters return EditsOverlap naming both."""
        first, second = _Edit(0, 3, "a"), _Edit(2, 4, "b")
        assert _apply_edits("x = 1\n", [second, first]) == EditsOverlap(
            first, second
        )

    def test_unparseable_result_is_refused(self) -> None:
        """An edit that breaks the syntax returns EditedSourceRejected."""
        refused = _apply_edits("x = 1\n", [_Edit(0, 1, "def")])
        assert isinstance(refused, EditedSourceRejected)
        assert isinstance(refused.rejection, SourceRejected)

    def test_clean_edits_apply(self) -> None:
        """Nonoverlapping edits that keep the syntax return the new source."""
        assert _apply_edits("x = 1\n", [_Edit(4, 5, "2")]) == "x = 2\n"

    def test_offset_inside_inserted_text(self) -> None:
        """A result offset inside an edit's text has no original position."""
        edits = [_Edit(2, 2, "abc")]
        assert _original_offset(3, edits) == InsideEdit()
        assert _original_offset(1, edits) == 1
        assert _original_offset(6, edits) == 3


class TestBuiltinDetectorTable:
    """Every bundled rule has exactly one way to be detected."""

    def test_table_and_text_only_rules_cover_the_catalog(self) -> None:
        """Table ids and text-only ids partition the bundled catalog ids."""
        from dartwork_mpl.lint.detect import (
            _BUILTIN_DETECTORS,
            _TEXT_ONLY_RULES,
        )

        catalog = {rule.id for rule in load_rules()}
        table = set(_BUILTIN_DETECTORS)
        assert not table & _TEXT_ONLY_RULES
        assert table | _TEXT_ONLY_RULES == catalog

    def test_text_only_rules_are_raw_text_detectors(self) -> None:
        """A text-only rule must carry a catalog detector that scans raw text."""
        from dartwork_mpl.lint.detect import _TEXT_ONLY_RULES

        for rule in load_rules():
            if rule.id in _TEXT_ONLY_RULES:
                assert isinstance(
                    _rule_detector(rule), (_RegexDetector, _SubstringDetector)
                )

    def test_literal_name_rules_use_their_ast_check(self) -> None:
        """AST-detector rules in the table are the literal-name rules."""
        from dartwork_mpl.lint.detect import _BUILTIN_DETECTORS, _literal_names

        for rule in load_rules():
            is_ast = isinstance(_rule_detector(rule), _AstNameDetector)
            uses_names = _BUILTIN_DETECTORS.get(rule.id) is _literal_names
            assert is_ast == uses_names, rule.id
