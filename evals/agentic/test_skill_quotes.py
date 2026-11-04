"""skill_quotes finds eval cases quoted in a skill, and only those."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import skill_quotes  # noqa: E402


def _skill(tmp_path: Path, text: str) -> Path:
    d = tmp_path / "skill"
    (d / "references").mkdir(parents=True)
    (d / "SKILL.md").write_text("# skill\n", encoding="utf-8")
    (d / "references" / "x.md").write_text(text, encoding="utf-8")
    return d


def test_the_2026_11_04_quotes_are_found(tmp_path: Path) -> None:
    """The examples that taught g19 / g20 / c06 their answers."""
    d = _skill(
        tmp_path,
        "Labels: `share_pct` -> `Share (%)`, `week_start` -> `Week start`;"
        ' "the share of renewables" -> `Share of renewables`.',
    )
    quotes = {(h["kind"], h["quote"]) for h in skill_quotes.find(d)}
    assert ("column", "share_pct") in quotes
    assert ("column", "week_start") in quotes
    assert ("prompt g20-slides-renewables", "the share of renewables") in quotes


def test_examples_no_case_uses_and_request_kinds_pass(tmp_path: Path) -> None:
    """Neutral examples, generic words and the named request kinds are fine."""
    d = _skill(
        tmp_path,
        "Labels: `order_date` -> `Order date`, `margin_pct` -> `Margin (%)`;"
        " a date, the year, 월; make it look better; the legend above the plot.",
    )
    assert skill_quotes.find(d) == []


def test_an_installed_skill_is_read_from_the_wheel(tmp_path: Path) -> None:
    # --ab-skill-install arms have no skill folder; the quote check must read
    # the skill the wheel installs (local codex review, 2026-11-04).
    import zipfile

    import run as runner

    column = sorted(
        skill_quotes._columns(skill_quotes.HERE / "fixtures" / "data")
    )[0]
    wheel = tmp_path / "dartwork_mpl-0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as zf:
        zf.writestr(skill_quotes.WHEEL_SKILL + "SKILL.md", f"Use `{column}`.\n")
        zf.writestr(skill_quotes.WHEEL_SKILL + "references/x.md", "nothing\n")
    a = argparse.Namespace(skill_dir=None, skill_install=True)
    hits = runner.skill_quote_hits(a, wheel)
    assert {"kind": "column", "quote": column, "file": "SKILL.md"} in hits
    assert (
        runner.skill_quote_hits(
            argparse.Namespace(skill_dir=None, skill_install=False), wheel
        )
        is None
    )
