"""Separate raw corpus metadata from confined, tier-specific file selection."""

import random
import string

import pytest

from dartwork_mpl import prompt


@pytest.fixture
def template_root(tmp_path, monkeypatch):
    """Real files and symlinks distinguish names/existence from read authority."""
    root = tmp_path / "templates"
    (root / "advanced").mkdir(parents=True)
    (tmp_path / "outside.py").write_text("OUTSIDE_SENTINEL\n")
    (root / "basic_only.py").write_text("# basic\n")
    (root / "advanced/advanced_only.py").write_text("# advanced\n")
    for tier in (root, root / "advanced"):
        (tier / "inside.py").write_text("# inside\n")
        (tier / "MiXeD.py").write_text("# mixed\n")
        (tier / "directory.py").mkdir()
        (tier / "nested").mkdir()
        (tier / "nested/inside.py").write_text("# nested\n")
        (tier / "alias.py").symlink_to(tier / "inside.py")
        (tier / "escape.py").symlink_to(tmp_path / "outside.py")
        (tier / "broken.py").symlink_to("missing.py")
        (tier / "loop.py").symlink_to("loop.py")
        (tier / "invalid_utf8.py").write_bytes(b"\xff")
    # Missing declarations must fail in test bodies, not fixture/collection setup.
    monkeypatch.setattr(prompt, "_TEMPLATE_DIR", root, raising=False)
    return root


def test_template_assets_declared_surface():
    """Only prompt declares the three corpus operations for other slices."""
    for name in (
        "resolve_template_path",
        "list_template_names",
        "template_exists",
    ):
        assert name in prompt.__all__
        assert callable(getattr(prompt, name))


@pytest.mark.parametrize("advanced", [False, True])
def test_template_assets_metadata_keeps_raw_filesystem_semantics(
    template_root, advanced
):
    """Sorted glob names include nonfiles; exists preserves spelling and joins."""
    root = template_root / "advanced" if advanced else template_root
    names = prompt.list_template_names(advanced=advanced)
    assert names == sorted(p.stem for p in root.glob("*.py"))
    assert {"directory", "escape", "broken", "loop", "MiXeD"} <= set(names)
    assert prompt.template_exists("directory", advanced=advanced) is True
    for stem in (
        "MiXeD",
        "mixed",
        "INSIDE",
        "../outside",
        "../../outside",
        "broken",
    ):
        assert (
            prompt.template_exists(stem, advanced=advanced)
            == (root / f"{stem}.py").exists()
        )


@pytest.mark.parametrize("advanced", [False, True])
def test_template_assets_confines_resolved_regular_files(
    template_root, advanced
):
    """Case-insensitive valid IDs select regular files only within their tier."""
    root = template_root / "advanced" if advanced else template_root
    assert (
        prompt.resolve_template_path("INSIDE", advanced=advanced)
        == (root / "inside.py").resolve()
    )
    assert (
        prompt.resolve_template_path("alias", advanced=advanced)
        == (root / "inside.py").resolve()
    )
    for stem in ("escape", "directory", "broken", "loop", "missing"):
        assert prompt.resolve_template_path(stem, advanced=advanced) is None
    expected = (root / "mixed.py").resolve()
    assert prompt.resolve_template_path("MiXeD", advanced=advanced) == (
        expected if expected.is_file() else None
    )
    assert prompt.resolve_template_path("basic_only", advanced=True) is None
    assert prompt.resolve_template_path("advanced_only") is None


@pytest.mark.parametrize(
    "stem",
    [
        "../outside",
        "/outside",
        "%2e%2e%2foutside",
        "%252e%252e%252foutside",
        "..\\outside",
        "nested/inside",
        "inside.py",
        "inside.dot",
        "inside\n",
        "\x00",
        "",
    ],
)
@pytest.mark.parametrize("advanced", [False, True])
def test_template_assets_invalid_ids_deny(template_root, stem, advanced):
    """A complete bare-ID grammar rejects paths, encodings and terminators."""
    assert prompt.resolve_template_path(stem, advanced=advanced) is None


def test_template_assets_generated_resolution_property(template_root):
    """Every generated successful selection is resolved, regular and confined."""
    seed = 20261018
    rng = random.Random(seed)
    alphabet = string.ascii_letters + string.digits + "_-/\\%.\x00\n"
    candidates = [
        "inside",
        "INSIDE",
        "alias",
        "escape",
        "directory",
        "loop",
        "broken",
        "MiXeD",
        "basic_only",
        "advanced_only",
    ]
    candidates += [
        "".join(rng.choices(alphabet, k=rng.randrange(0, 50)))
        for _ in range(300)
    ]
    for advanced in (False, True):
        root = template_root / "advanced" if advanced else template_root
        for stem in candidates:
            path = prompt.resolve_template_path(stem, advanced=advanced)
            if path is not None:
                context = f"seed={seed} id={stem!r} advanced={advanced}"
                assert path == path.resolve(), context
                assert path.is_file(), context
                assert path.is_relative_to(root.resolve()), context


def test_template_assets_selection_does_not_read_or_cache(template_root):
    """Selection returns a Path; decoding and later deletion retain native errors."""
    path = prompt.resolve_template_path("invalid_utf8")
    assert path == (template_root / "invalid_utf8.py").resolve()
    with pytest.raises(UnicodeDecodeError):
        path.read_text(encoding="utf-8")
    path.write_text("# replaced\n", encoding="utf-8")
    assert (
        prompt.resolve_template_path("invalid_utf8").read_text(encoding="utf-8")
        == "# replaced\n"
    )
    path.unlink()
    with pytest.raises(FileNotFoundError):
        path.read_text(encoding="utf-8")
