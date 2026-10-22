"""The token-file parser turns every damaged or incomplete file into a named refusal.

``semantic_tokens.json`` is the only source of the token roles (there is no
in-code fallback table), so these tests pin both directions: the shipped file
parses to the full table, and each kind of damage is reported as a value
naming the problem instead of being swallowed.
"""

import copy
import json
from pathlib import Path

import pytest

import dartwork_mpl as dm
from dartwork_mpl import tokens
from dartwork_mpl.tokens._table import (
    RcToken,
    TokenFileMalformed,
    TokenFileUnreadable,
    TokenTable,
    parse_tokens,
    read_tokens,
)

_SHIPPED = tokens._TOKEN_PATH
_RAW: dict[str, object] = json.loads(_SHIPPED.read_text(encoding="utf-8"))


def _malformed(raw: object) -> str:
    """Parse ``raw`` and return the refusal's detail; fail if it parsed."""
    result = parse_tokens(raw, Path("t.json"))
    assert isinstance(result, TokenFileMalformed), result
    return result.detail


def _edited(**sections: object) -> dict[str, object]:
    """Return a deep copy of the shipped JSON with ``sections`` replaced."""
    raw = copy.deepcopy(_RAW)
    raw.update(sections)
    return raw


def test_shipped_file_parses_to_the_complete_table() -> None:
    """The shipped file yields a table whose roles and values match the JSON."""
    table = read_tokens(_SHIPPED)

    assert isinstance(table, TokenTable)
    assert table.version == "2"
    assert table.type_scale["emphasis"] == RcToken("font.size", 1.5, 1.0)
    assert table.lw_ladder["hairline"] == RcToken("lines.linewidth", 0.0, 0.3)
    assert dict(table.scatter_size) == {
        "small": 16.0,
        "default": 30.0,
        "emphasis": 45.0,
    }
    assert list(table.spacing) == ["xs", "sm", "md", "lg", "xl"]


def test_missing_offset_and_multiplier_default_to_identity() -> None:
    """An entry with only ``rcparam`` resolves to the rcParam itself."""
    raw = _edited()
    raw["type_scale"]["body"] = {"rcparam": "font.size"}

    table = parse_tokens(raw, Path("t.json"))

    assert isinstance(table, TokenTable)
    assert table.type_scale["body"] == RcToken("font.size", 0.0, 1.0)


@pytest.mark.parametrize(
    ("raw", "fragment"),
    [
        ([], "<root>: expected an object"),
        (_edited(version=2), "version"),
        ({k: v for k, v in _RAW.items() if k != "spacing"}, "'spacing'"),
        (_edited(scatter_size={"small": 1, "default": 2}), "['emphasis']"),
        (_edited(spacing={**_RAW["spacing"], "xxl": 20}), "unexpected ['xxl']"),
        (
            _edited(scatter_size={"small": "big", "default": 2, "emphasis": 3}),
            "scatter_size.small",
        ),
        (_edited(lw_ladder="thin"), "lw_ladder: expected an object"),
    ],
    ids=[
        "root-not-object",
        "version-not-string",
        "section-missing",
        "role-missing",
        "role-unexpected",
        "size-not-number",
        "section-not-object",
    ],
)
def test_incomplete_or_mistyped_file_is_malformed(
    raw: object, fragment: str
) -> None:
    """Each structural defect is a ``TokenFileMalformed`` naming where it is."""
    assert fragment in _malformed(raw)


def test_unknown_rcparam_is_malformed() -> None:
    """A role pointing at an rcParam matplotlib lacks is rejected at parse time."""
    raw = _edited()
    raw["lw_ladder"]["trend"] = {"rcparam": "lines.widht"}

    assert "lw_ladder.trend.rcparam" in _malformed(raw)


def test_invalid_json_is_malformed(tmp_path: Path) -> None:
    """Undecodable JSON is a malformed file, not an exception."""
    path = tmp_path / "t.json"
    path.write_text("{not json", encoding="utf-8")

    result = read_tokens(path)

    assert isinstance(result, TokenFileMalformed)
    assert result.path == path
    assert "invalid JSON" in result.detail


def test_missing_file_is_unreadable(tmp_path: Path) -> None:
    """A file that is not there is ``TokenFileUnreadable`` carrying its path."""
    path = tmp_path / "absent.json"

    result = read_tokens(path)

    assert isinstance(result, TokenFileUnreadable)
    assert result.path == path


def test_table_rejects_a_missing_role() -> None:
    """A ``TokenTable`` lacking a role cannot be built."""
    shipped = read_tokens(_SHIPPED)
    assert isinstance(shipped, TokenTable)

    with pytest.raises(ValueError, match="missing \\['xl'\\]"):
        TokenTable(
            version="2",
            type_scale=shipped.type_scale,
            lw_ladder=shipped.lw_ladder,
            scatter_size=shipped.scatter_size,
            spacing={"xs": 1.0, "sm": 2.0, "md": 3.0, "lg": 4.0},
        )


def test_rc_token_rejects_an_unknown_rcparam() -> None:
    """An ``RcToken`` naming no rcParam cannot be built."""
    with pytest.raises(ValueError, match="unknown rcParam"):
        RcToken("not.a.param", 0.0, 1.0)


def test_accessor_reports_a_damaged_install(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With a refused file, accessors raise naming the file instead of inventing values."""
    monkeypatch.setattr(
        tokens, "_LOADED", TokenFileMalformed(Path("x.json"), "boom")
    )

    with pytest.raises(RuntimeError, match=r"x\.json is malformed \(boom\)"):
        dm.tokens.fs_body()
