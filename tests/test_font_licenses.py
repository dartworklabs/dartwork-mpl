"""Every bundled font family must ship its license text (G11).

Seven OFL families (Inter, Inter Display, the Noto Sans width families,
Noto Sans Math, Noto Sans CJK KR) were redistributed in the wheel with
no license text while the docs claimed all were bundled — an OFL §1
compliance gap. This test derives the expectation from the files on
disk: every font file's family prefix must map to an existing
``licenses/LICENSE-<X>.txt``.
"""

from __future__ import annotations

from pathlib import Path

_FONT_DIR = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "dartwork_mpl"
    / "asset"
    / "font"
)
_LICENSES = _FONT_DIR / "licenses"

# filename-prefix -> license file stem. A new family fails this test
# until its license text lands (or its prefix is mapped to an existing
# covering license, e.g. one OFL text per upstream project).
_PREFIX_TO_LICENSE: dict[str, str] = {
    "Roboto-": "LICENSE-Roboto",
    "RobotoMono-": "LICENSE-RobotoMono",
    "Inter-": "LICENSE-Inter",
    "InterDisplay-": "LICENSE-Inter",
    "NotoSans-": "LICENSE-NotoSans",
    "NotoSans_Condensed-": "LICENSE-NotoSans",
    "NotoSans_SemiCondensed-": "LICENSE-NotoSans",
    "NotoSansMath-": "LICENSE-NotoSans",
    "NotoSansCJK": "LICENSE-NotoSansCJK",
    "Paperlogy-": "LICENSE-Paperlogy",
    "Pretendard-": "LICENSE-Pretendard",
    "SourceSans3-": "LICENSE-SourceSans3",
    "SourceCodePro-": "LICENSE-SourceCodePro",
    "IBMPlexSans-": "LICENSE-IBMPlex",
    "IBMPlexMono-": "LICENSE-IBMPlex",
    "JetBrainsMono-": "LICENSE-JetBrainsMono",
}


def _font_files() -> list[Path]:
    return [
        p for p in _FONT_DIR.iterdir() if p.suffix.lower() in {".ttf", ".otf"}
    ]


def test_every_font_file_maps_to_a_license() -> None:
    unmapped = [
        f.name
        for f in _font_files()
        if not any(f.name.startswith(pre) for pre in _PREFIX_TO_LICENSE)
    ]
    assert not unmapped, (
        f"font files with no license mapping: {unmapped[:8]} — add the "
        f"family's LICENSE text under asset/font/licenses/ and map its "
        f"filename prefix in _PREFIX_TO_LICENSE"
    )


def test_every_mapped_license_file_exists() -> None:
    missing = {
        stem
        for stem in _PREFIX_TO_LICENSE.values()
        if not (_LICENSES / f"{stem}.txt").is_file()
    }
    assert not missing, f"license texts missing: {sorted(missing)}"


def test_no_orphan_license_files() -> None:
    on_disk = {p.stem for p in _LICENSES.glob("LICENSE-*.txt")}
    mapped = set(_PREFIX_TO_LICENSE.values())
    orphans = on_disk - mapped
    assert not orphans, (
        f"license files no font maps to: {sorted(orphans)} — stale after "
        f"a family removal?"
    )


def test_every_prefix_matches_some_file() -> None:
    """Reverse: a mapping entry whose prefix matches nothing is stale."""
    names = [f.name for f in _font_files()]
    stale = [
        pre
        for pre in _PREFIX_TO_LICENSE
        if not any(n.startswith(pre) for n in names)
    ]
    assert not stale, f"mapping prefixes matching no font file: {stale}"
