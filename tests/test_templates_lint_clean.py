"""The bundled prompt templates lint clean against the catalog they teach.

A contract between the lint engine and the prompt-template corpus, so it
stays in the cross-cutting ``tests/`` tree.
"""

from __future__ import annotations

from pathlib import Path

from dartwork_mpl.lint import lint


class TestBundledTemplatesLintClean:
    """The 18 prompt-asset templates ship as the canonical examples
    agents copy from. They must lint clean against the very rules
    they teach — otherwise the linter contradicts the templates.
    """

    def test_all_prompt_templates_lint_clean(self) -> None:
        templates_dir = (
            Path(__file__).resolve().parents[1]
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
