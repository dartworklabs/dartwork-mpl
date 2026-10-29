"""Selected formats reject before render effects; missing selections still win.

Audit hooks live in disposable observer processes because Python cannot remove
them. Fixture creation and imports finish before observation starts; the real
renderer, process runner and publication adapter are never replaced.
"""

import json
import os
import random
import string
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from dartwork_mpl import prompt
from dartwork_mpl.mcp.templates import render

_INVALID_FORMATS = ("bogus", "", "PATH", " base64")
_TIERS = ("basic", "advanced", "fallback")
_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    "/x8AAwMCAO+aV1sAAAAASUVORK5CYII="
)


@pytest.fixture
def basic_only_assets(tmp_path):
    """Provide a genuine PNG template and an empty advanced lookup directory."""
    root = tmp_path / "assets"
    (root / "advanced").mkdir(parents=True)
    (root / "basic_only.py").write_text(
        "import base64\nfrom pathlib import Path\n"
        f"Path('out.png').write_bytes(base64.b64decode({_PNG!r}))\n",
        encoding="utf-8",
    )
    return root


def _invalid_reply(plot_type, return_format, tier):
    """Express the approved exact error envelope, with tier only for advanced."""
    expected = {
        "status": "render_error",
        "plot_type": plot_type,
        "png_base64": None,
        "png_path": None,
        "stderr": (
            f"return_format must be 'base64' or 'path'; got {return_format!r}"
        ),
    }
    if tier != "basic":
        expected["tier"] = "basic" if tier == "fallback" else "advanced"
    return expected


def _unknown_reply(root, tier):
    """Pin the old sorted availability diagnostics, including advanced none."""
    basic = sorted(p.stem for p in root.glob("*.py"))
    expected = {
        "status": "unknown_template",
        "plot_type": "missing_fixture",
        "png_base64": None,
        "png_path": None,
    }
    if tier == "basic":
        expected["stderr"] = (
            f"No template named 'missing_fixture'. Available: {basic}"
        )
    else:
        advanced = sorted(p.stem for p in (root / "advanced").glob("*.py"))
        expected.update(
            tier="none",
            stderr=(
                "No template named 'missing_fixture'. "
                f"Available basic: {basic}. Available advanced: {advanced}."
            ),
        )
    return expected


def _observations(tmp_path, root, tier, plot_type, formats):
    """Run isolated observers with an owned temp root and return their receipts."""
    temp_root = tmp_path / "watched-temp"
    temp_root.mkdir()
    request = {
        "root": str(root) if root else None,
        "temp_root": str(temp_root),
        "tier": tier,
        "plot_type": plot_type,
        "formats": list(formats),
    }
    process = subprocess.run(
        [sys.executable, __file__],
        input=json.dumps(request),
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "TMPDIR": str(temp_root)},
    )
    assert process.returncode == 0, process.stderr
    return json.loads(process.stdout)


def _assert_refusal(observation, expected):
    """Check the complete reply and both transient and retained creation effects."""
    reply = observation["reply"]
    assert reply == expected
    assert reply["png_base64"] is reply["png_path"] is None
    assert "fell_back" not in reply
    assert observation["creation_events"] == []
    assert observation["temp_tree_after"] == observation["temp_tree_before"]


@pytest.mark.parametrize("return_format", _INVALID_FORMATS)
@pytest.mark.parametrize("tier", _TIERS)
def test_selected_template_rejects_invalid_format_without_effects(
    tmp_path, basic_only_assets, tier, return_format
):
    """All selected tiers refuse exact invalid strings without render creation."""
    root = basic_only_assets if tier == "fallback" else None
    plot_type = "basic_only" if root else "bar"
    observations = _observations(
        tmp_path, root, tier, plot_type, [return_format]
    )
    _assert_refusal(
        observations[0], _invalid_reply(plot_type, return_format, tier)
    )


@pytest.mark.parametrize("tier", ["basic", "advanced"])
@pytest.mark.parametrize("scratch", [False, True])
def test_unknown_selection_precedes_invalid_format(
    tmp_path, basic_only_assets, tier, scratch
):
    """Unknown selections retain complete diagnostics on installed and owned roots."""
    root = basic_only_assets if scratch else None
    observations = _observations(
        tmp_path, root, tier, "missing_fixture", _INVALID_FORMATS
    )
    expected = _unknown_reply(root or prompt._TEMPLATE_DIR, tier)
    for observation in observations:
        _assert_refusal(observation, expected)


@pytest.mark.parametrize("tier", _TIERS)
def test_generated_invalid_formats_never_execute(
    tmp_path, basic_only_assets, tier
):
    """Seeded arbitrary invalid strings preserve exact replies and zero effects."""
    rng = random.Random(20261029)
    alphabet = string.ascii_letters + string.digits + " \t\n'\\\x00é"
    formats = ["base64\n", "path\x00", "Base64", "path "]
    formats += [
        "".join(rng.choices(alphabet, k=rng.randrange(1, 24))) for _ in range(8)
    ]
    assert not set(formats).intersection(("base64", "path"))
    # The same real basic-only asset supports basic and advanced fallback;
    # installed bar supplies the genuinely selected advanced tier.
    root = None if tier == "advanced" else basic_only_assets
    plot_type = "bar" if root is None else "basic_only"
    observations = _observations(tmp_path, root, tier, plot_type, formats)
    for return_format, observation in zip(formats, observations, strict=True):
        _assert_refusal(
            observation, _invalid_reply(plot_type, return_format, tier)
        )


def _observe(request):
    """Observe real direct calls with a removable process, not removable hooks."""
    temp_root = Path(request["temp_root"])
    tempfile.tempdir = str(temp_root)
    original_root = prompt._TEMPLATE_DIR
    if request["root"]:
        prompt._TEMPLATE_DIR = Path(request["root"])
    events = []
    watching = False

    def audit(event, args):
        """Retain creation attempts even when the created objects are removed."""
        if watching and event in (
            "subprocess.Popen",
            "tempfile.mkdtemp",
            "tempfile.mkstemp",
            "os.mkdir",
        ):
            events.append({"event": event, "args": [str(a) for a in args]})

    sys.addaudithook(audit)
    receipts = []
    callback = (
        render.render_basic
        if request["tier"] == "basic"
        else render.render_advanced
    )
    try:
        for return_format in request["formats"]:
            events.clear()
            before = sorted(str(p) for p in temp_root.rglob("*"))
            watching = True
            try:
                reply = callback(request["plot_type"], return_format, 30.0)
            finally:
                watching = False
            receipts.append(
                {
                    "reply": reply,
                    "creation_events": list(events),
                    "temp_tree_before": before,
                    "temp_tree_after": sorted(
                        str(p) for p in temp_root.rglob("*")
                    ),
                }
            )
    finally:
        prompt._TEMPLATE_DIR = original_root
    return receipts


if __name__ == "__main__":
    print(json.dumps(_observe(json.load(sys.stdin))))
