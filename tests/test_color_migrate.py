"""Tests for the v4 → v5 color-token migration codemod."""

from __future__ import annotations

import matplotlib
import matplotlib.colors as mcolors

matplotlib.use("Agg")


def test_rewrites_removed_palette_tokens() -> None:
    import dartwork_mpl  # noqa: F401 — register the palette
    from dartwork_mpl.colors._migrate import migrate_text

    src = (
        'ax.plot(x, y, color="dc.spectrum3")\n'
        'ax.plot(x, z, color="dc.coolwarm2")\n'
        'dm.set_cycle("dc.warm_cool")\n'
    )
    new, changes = migrate_text(src)
    assert 'color="dc.vivid3"' in new
    assert 'color="dc.cool_warm2"' in new
    assert '"dc.blue_orange"' in new
    assert {c.old for c in changes} == {"spectrum", "coolwarm", "warm_cool"}


def test_rename_vs_merge_kind() -> None:
    from dartwork_mpl.colors._migrate import migrate_text

    _, changes = migrate_text("dc.spectrum1 dc.bold2 dc.corporate3")
    by_old = {c.old: c.kind for c in changes}
    assert by_old == {
        "spectrum": "rename",
        "bold": "merge",
        "corporate": "merge",
    }


def test_rewritten_tokens_resolve() -> None:
    """The migrated names must be real, resolvable colors (the whole point)."""
    import dartwork_mpl  # noqa: F401
    from dartwork_mpl.colors._migrate import migrate_text

    src = "dc.spectrum0 dc.coolwarm1 dc.bold2 dc.corporate3 dc.warm_cool4"
    new, _ = migrate_text(src)
    mapping = mcolors.get_named_colors_mapping()
    for tok in new.split():
        assert tok in mapping, f"{tok} does not resolve"


def test_idempotent_and_leaves_valid_tokens() -> None:
    from dartwork_mpl.colors._migrate import migrate_text

    src = 'color="dc.vivid3"\ncmap="dc.aurora"\ncolor="dc.trustworthy0"\n'
    once, changes = migrate_text(src)
    assert changes == []
    assert once == src  # nothing removed here — untouched
    twice, _ = migrate_text(migrate_text("dc.spectrum3")[0])
    assert twice == "dc.vivid3"


def test_migrate_regex_edges() -> None:
    """T3 — prefix preservation, base rewrites, and negative-match guards."""
    from dartwork_mpl.colors._migrate import migrate_text

    # dm.* mirror prefix is preserved through the rewrite.
    assert migrate_text("dm.coolwarm4")[0] == "dm.cool_warm4"
    # v0.5.4 base-name alias rewrite.
    assert migrate_text("dc.ocean2")[0] == "dc.teal2"
    # Negatives — must NOT be rewritten. group 3 requires a shade digit OR a
    # trailing string quote, so ordinary attribute/method access is excluded:
    #   xdc.spectrum3   → no word boundary before "dc"
    #   dc.bold_r       → "_" is a word char, so no boundary after "bold"
    #   dc.spectrum3x   → trailing word char, so (\d+)\b never matches
    #   dc.pop(0) / dm.pop(key) / dm.focus()  → method call (base + "(")
    #   dm.muted / x = dm.pop  → bare attribute (no digit, no quote)
    for src in (
        "xdc.spectrum3",
        "dc.bold_r",
        "dc.spectrum3x",
        "dc.pop(0)",
        "dm.pop(key)",
        "dm.focus()",
        "dm.muted",
        "x = dm.pop",
    ):
        assert migrate_text(src)[0] == src, src
    # A bare removed name inside a string IS rewritten (set_cycle name arg).
    assert migrate_text('set_cycle("dc.pop")')[0] == 'set_cycle("dc.vivid")'
    # A token inside an f-string still rewrites (plain text substitution).
    new, changes = migrate_text('label = f"series {dc.nordic1}"')
    assert new == 'label = f"series {dc.teal_indigo1}"'
    assert changes and changes[0].prefix == "dc"


def test_bare_name_reported_with_suggestion() -> None:
    """A bare (unprefixed) removed name in a palette-API call is reported
    with its current suggested name — but NOT rewritten."""
    from dartwork_mpl.colors._migrate import find_bare_names, migrate_text

    src = 'dm.set_cycle("spectrum")\n'
    hits = find_bare_names(src)
    assert len(hits) == 1
    hit = hits[0]
    assert hit.name == "spectrum"
    assert hit.suggestion == "vivid"
    assert hit.lineno == 1
    # Report-only: migrate_text must not touch a bare name.
    new, changes = migrate_text(src)
    assert new == src
    assert changes == []


def test_bare_name_contexts() -> None:
    """set_cycle( / get_palette( calls and cycle= / palette= kwargs are the
    recognised contexts; the suggestion comes from PALETTE_RENAMES."""
    from dartwork_mpl.colors._migrate import find_bare_names

    cases = {
        'set_cycle("spectrum")': ("spectrum", "vivid"),
        "get_palette('ocean')": ("ocean", "teal"),
        'cycle="pop"': ("pop", "vivid"),
        "palette='corporate'": ("corporate", "trustworthy"),
    }
    for src, (name, suggestion) in cases.items():
        hits = find_bare_names(src)
        assert len(hits) == 1, src
        assert (hits[0].name, hits[0].suggestion) == (name, suggestion), src


def test_bare_name_longest_match_wins() -> None:
    """focus_warm must not be reported as bare 'focus'."""
    from dartwork_mpl.colors._migrate import find_bare_names

    hits = find_bare_names('set_cycle("focus_warm")')
    assert [h.name for h in hits] == ["focus_warm"]
    assert hits[0].suggestion == "coral_accent"


def test_bare_name_negatives_no_false_positive() -> None:
    """Bare removed words outside a palette-API context are NOT flagged, and
    a bare name that is still a live v5 target (vivid) is never flagged."""
    from dartwork_mpl.colors._migrate import find_bare_names

    for src in (
        "# keep the focus on the data, not the chrome\n",  # prose comment
        'title = "ocean depth study"',  # arbitrary string
        'd.pop("focus")',  # unrelated method call
        'set_cycle("vivid")',  # vivid still resolves in v5 → no migration
        'get_palette("teal")',  # teal is a current family, not removed
    ):
        assert find_bare_names(src) == [], src


def test_bare_name_not_double_reported_with_prefixed_rewrite() -> None:
    """A prefixed token is rewritten by migrate_text and must NOT also show
    up as a bare-name hit (no double report of the same site)."""
    from dartwork_mpl.colors._migrate import find_bare_names, migrate_text

    src = 'set_cycle("dc.spectrum")'
    new, changes = migrate_text(src)
    assert new == 'set_cycle("dc.vivid")'  # rewritten as before
    assert {c.old for c in changes} == {"spectrum"}
    assert find_bare_names(src) == []  # not reported as bare


def test_cli_bare_only_suppresses_all_clear(tmp_path, capsys) -> None:
    """A file with only bare-name hits must be reported (with the advisory
    label) and must NOT print the 'No removed … tokens found.' all-clear."""
    from dartwork_mpl.colors._migrate import main

    f = tmp_path / "uses_bare.py"
    f.write_text('dm.set_cycle("spectrum")\n', encoding="utf-8")
    rc = main([str(f), "--no-advisory"])
    out = capsys.readouterr().out
    assert "No removed v0.5.5 palette tokens found." not in out
    assert "bare 'spectrum'" in out
    assert "not auto-rewritten (bare name — verify context)" in out
    assert "→ 'vivid'" in out
    # Nothing was rewritten, so the file is untouched.
    assert f.read_text(encoding="utf-8") == 'dm.set_cycle("spectrum")\n'
    # Report-only bare hits don't force a nonzero (rewrite-pending) exit.
    assert rc == 0


def test_collision_shift_table() -> None:
    from dartwork_mpl.colors._migrate import collision_shift_table

    rows = collision_shift_table()
    assert len(rows) == 24  # teal/indigo/gray steps 0-7
    for token, old_hex, new_hex, de in rows:
        assert token.startswith(("dc.teal", "dc.indigo", "dc.gray"))
        assert old_hex.startswith("#") and new_hex.startswith("#")
        assert de >= 0.0
