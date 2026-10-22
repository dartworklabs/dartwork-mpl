"""Agent-facing lists match the runtime they describe.

The prompt corpus once listed six of the ten aspect tokens (``slide`` 16:9
was missing) and four of the seven presets, and a panel-label recipe drew
every label twice. Agents copy these lists verbatim, so each is read back
from the text and compared with the live registry.
"""

from __future__ import annotations

import re
from fractions import Fraction
from pathlib import Path

import matplotlib.pyplot as plt
import pytest
from matplotlib.text import Text

import dartwork_mpl as dm

ROOT = Path(__file__).resolve().parents[1]
BASE_PRESETS = {n for n in dm.style.presets if not n.endswith("-kr")}


def _section(text: str, heading: str) -> str:
    """The body under ``heading`` up to the next heading of any level."""
    body = text.split(heading, 1)[1]
    return re.split(r"\n#+ ", body, maxsplit=1)[0]


def _ratio(expr: str) -> float:
    """Evaluate the corpus's ``"5 / 4"`` / ``"1.0"`` ratio notation."""
    if "/" in expr:
        num, den = (float(part) for part in expr.split("/"))
        return num / den
    return float(Fraction(expr))


def test_policy_aspect_tokens_match_runtime() -> None:
    section = _section(dm.get_prompt("01-policy"), "### Aspect tokens")
    rows = dict(re.findall(r'- `"(\w+)"` — ([\d. /]+)', section))
    runtime = dm.list_aspect_tokens()
    assert set(rows) == set(runtime)
    for token, expr in rows.items():
        assert _ratio(expr) == pytest.approx(runtime[token], rel=1e-4), token


def test_index_aspect_tokens_match_runtime() -> None:
    text = dm.get_prompt("00-index")
    clause = text.split("an aspect token (", 1)[1].split(")", 1)[0]
    assert set(re.findall(r'`"(\w+)"`', clause)) == set(dm.list_aspect_tokens())


def test_policy_presets_match_runtime() -> None:
    text = dm.get_prompt("01-policy")
    line = text.split("- Available presets:", 1)[1].split("\n- ", 1)[0]
    listed = set(re.findall(r"`([a-z]+)`", line))
    assert listed == BASE_PRESETS
    kr = {n for n in dm.style.presets if n.endswith("-kr")}
    assert kr == {f"{name}-kr" for name in BASE_PRESETS}


def test_mcp_prompt_text_pins_no_package_version() -> None:
    """The prompts said "dartwork-mpl 0.4" long after 0.5 shipped."""
    source = "\n".join(
        (ROOT / "src/dartwork_mpl/mcp" / rel).read_text("utf-8")
        for rel in ("prompts.py", "guides/prompts.py")
    )
    assert not re.search(r"dartwork-mpl \d+\.\d", source)
    assert not re.search(r"\b\d+\.\d+ (?:policy|invocations|SSOT)\b", source)


def test_ai_hub_size_claims_track_the_files() -> None:
    """docs/ai/index.md called llms-full.txt "≈ 45 KB" when it was 76 KB."""
    claims = [
        (line, float(size))
        for line in (ROOT / "docs/ai/index.md").read_text("utf-8").splitlines()
        for size in re.findall(r"≈ (\d+(?:\.\d+)?) KB", line)
    ]
    assert claims
    for line, size in claims:
        name = "llms-full.txt" if "llms-full.txt" in line else "llms.txt"
        assert name in line, line
        actual_kb = (ROOT / name).stat().st_size / 1000
        assert abs(size - actual_kb) <= 0.3 * actual_kb, (line, actual_kb)


def test_ai_hub_names_only_files_that_exist() -> None:
    text = (ROOT / "docs/ai/index.md").read_text("utf-8")
    assert "repo-root `GEMINI.md`" not in text
    codex = next(ln for ln in text.splitlines() if "**OpenAI Codex CLI**" in ln)
    assert "❌" not in codex, "Codex supports MCP (codex mcp add)"


def test_contributor_entry_files_stay_mirrored() -> None:
    assert (ROOT / "CLAUDE.md").read_bytes() == (
        ROOT / "AGENTS.md"
    ).read_bytes()


def test_panel_label_recipe_draws_each_label_once() -> None:
    recipes = dm.get_prompt("03-recipes")
    section = _section(recipes, '## "Multi-panel grid (a/b/c labels)"')
    (block,) = re.findall(r"```python\n(.*?)```", section, re.S)
    namespace = {"plt": plt, "dm": dm}
    exec(compile(block, "03-recipes:panel-labels", "exec"), namespace)
    fig = namespace["fig"]
    texts = [t.get_text() for t in fig.findobj(Text)]
    for label in "abcd":
        assert texts.count(label) == 1, (label, texts)
