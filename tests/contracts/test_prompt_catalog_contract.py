"""Cross-slice catalog selection, diagnostics and live-read contracts."""

import random
from pathlib import Path

import pytest
import yaml

from dartwork_mpl import prompt
from dartwork_mpl.lint import load_rules
from dartwork_mpl.mcp.guides.corpus import anti_pattern_catalog


@pytest.mark.parametrize(
    "case", ["shipped", "missing", "yaml", "both", "md", "broken"]
)
def test_catalog_consumer_selection_and_errors(case, tmp_path, monkeypatch):
    """Native MD preference must not redirect exact-YAML lint/MCP reads."""
    shipped = prompt.prompt_path("02-anti-patterns")
    if case == "shipped":
        expected = shipped.read_text(encoding="utf-8")
        assert prompt.get_prompt("02-anti-patterns") == expected
        assert anti_pattern_catalog() == expected
        assert load_rules() == load_rules(shipped)
        return
    corpus = tmp_path / "corpus"
    monkeypatch.setattr(prompt, "_PROMPT_DIR", corpus)
    catalog = corpus / "02-anti-patterns.yaml"
    if case != "missing":
        corpus.mkdir()
    if case in ("yaml", "both", "broken"):
        catalog.write_text(
            "rules: [\n" if case == "broken" else "rules: []\n",
            encoding="utf-8",
        )
    if case in ("both", "md"):
        (corpus / "02-anti-patterns.md").write_text(
            "# probe\n", encoding="utf-8"
        )
    if case == "missing":
        with pytest.raises(ValueError) as exc:
            prompt.get_prompt("02-anti-patterns")
        assert str(exc.value) == "Prompt guide not found: 02-anti-patterns."
    else:
        assert prompt.get_prompt("02-anti-patterns") == (
            "# probe\n"
            if case in ("both", "md")
            else catalog.read_text(encoding="utf-8")
        )
    if case in ("missing", "md"):
        with pytest.raises(FileNotFoundError) as expected_error:
            catalog.open("r", encoding="utf-8")
        for read in (anti_pattern_catalog, load_rules):
            with pytest.raises(FileNotFoundError) as actual:
                read()
            assert (
                actual.value.errno,
                actual.value.filename,
                str(actual.value),
            ) == (
                expected_error.value.errno,
                expected_error.value.filename,
                str(expected_error.value),
            )
    else:
        assert anti_pattern_catalog() == catalog.read_text(encoding="utf-8")
        if case == "broken":
            assert_parser_error(catalog, None)
        else:
            assert load_rules() == []


def assert_parser_error(catalog, override):
    """PyYAML must receive the real stream, preserving source marks verbatim."""
    with catalog.open("r", encoding="utf-8") as stream:
        with pytest.raises(yaml.parser.ParserError) as expected:
            yaml.safe_load(stream)
    with pytest.raises(yaml.parser.ParserError) as actual:
        load_rules(override)
    assert str(actual.value) == str(expected.value)
    assert actual.value.problem == expected.value.problem
    assert actual.value.context == expected.value.context
    for name in ("problem_mark", "context_mark"):
        a, e = getattr(actual.value, name), getattr(expected.value, name)
        assert (a.name, a.line, a.column, a.index) == (
            e.name,
            e.line,
            e.column,
            e.index,
        )


def test_catalog_override_and_error_context(tmp_path, monkeypatch):
    """Explicit paths bypass a broken bundle and keep their own diagnostics."""
    corpus = tmp_path / "corpus"
    monkeypatch.setattr(prompt, "_PROMPT_DIR", corpus)
    monkeypatch.chdir(tmp_path)
    override = Path("custom.rules")
    rule = "rules:\n- id: probe\n  severity: warning\n  detector: {kind: substring, literal: x}\n  message: first\n"
    override.write_text(rule, encoding="utf-8")
    previous = load_rules(override)
    assert [(r.id, r.message) for r in previous] == [("probe", "first")]
    corpus.mkdir()
    (corpus / "02-anti-patterns.md").write_text("# probe\n", encoding="utf-8")
    bundled = corpus / "02-anti-patterns.yaml"
    bundled.write_text("rules: [\n", encoding="utf-8")
    override.write_text(rule.replace("first", "second"), encoding="utf-8")
    assert load_rules(override)[0].message == "second"
    assert previous[0].message == "first"
    for text, suffix in [
        ("[]", "must be a mapping"),
        ("rules: {}", "rules must be a list"),
    ]:
        for path, arg in [(bundled, None), (override, override)]:
            path.write_text(text, encoding="utf-8")
            with pytest.raises(ValueError) as exc:
                load_rules(arg)
            assert str(exc.value) == f"Catalog {path} {suffix}"
    override.write_text("rules: [\n", encoding="utf-8")
    assert_parser_error(override, override)
    override.write_bytes(b"\xff")
    with pytest.raises(UnicodeDecodeError):
        load_rules(override)
    override.unlink()
    with pytest.raises(FileNotFoundError) as expected:
        override.open("r", encoding="utf-8")
    with pytest.raises(FileNotFoundError) as actual:
        load_rules(override)
    assert (actual.value.errno, actual.value.filename, str(actual.value)) == (
        expected.value.errno,
        expected.value.filename,
        str(expected.value),
    )


def test_catalog_text_decoding_and_reread(tmp_path, monkeypatch):
    """Seeded Unicode/newline changes are decoded afresh by all consumers."""
    monkeypatch.setattr(prompt, "_PROMPT_DIR", tmp_path)
    catalog = tmp_path / "02-anti-patterns.yaml"
    rng = random.Random(20261029)
    for index in range(20):
        comment = "".join(rng.choice("abc한글éΩ🙂") for _ in range(12))
        newline = rng.choice(["\n", "\r\n", "\r"])
        raw = f"# {index} {comment}{newline}rules: []{newline}".encode()
        catalog.write_bytes(raw)
        expected = raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
        assert prompt.get_prompt("02-anti-patterns") == expected
        assert anti_pattern_catalog() == expected
        assert load_rules() == []
    catalog.write_bytes(b"\xff")
    for read in (
        lambda: prompt.get_prompt("02-anti-patterns"),
        anti_pattern_catalog,
        load_rules,
    ):
        with pytest.raises(UnicodeDecodeError):
            read()
