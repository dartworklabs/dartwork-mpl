#!/usr/bin/env python3
"""Fetch the bundled sans-serif (+ mono) font corpus from canonical
OFL / Apache-2.0 upstreams into ``src/dartwork_mpl/asset/font``.

Reproducible, idempotent font sourcing. Each family is pinned to its
upstream repo/release; the script resolves download URLs via ``gh api``
(so it is not brittle to a repo's default-branch name), verifies every
downloaded file opens as a real font, normalizes italic filenames, and
writes each upstream's license into ``asset/font/licenses/``.

Run:  python docs/fonts/fetch_fonts.py            # add missing / refresh all
      python docs/fonts/fetch_fonts.py --verify   # just report what's on disk

Weight depth follows the "full weights + italics, where the upstream
publishes static instances" decision:
  · Roboto        9 uprights + 9 italics   (100-900, instanced from the
                                            google/fonts variable font —
                                            GF static zips clamp Thin/
                                            ExtraLight usWeightClass to 250)
  · Paperlogy     9 uprights               (no italics upstream — Korean)
  · Pretendard    9 uprights               (no italics upstream — Korean)
  · IBM Plex Sans 7 uprights + 7 italics   (Text weight skipped)
  · IBM Plex Mono 7 uprights + 7 italics   (Text weight skipped)
  · Source Sans 3 7 uprights + 7 italics   (no Thin upstream)
  · JetBrains Mono 8 uprights + 8 italics  (no Black upstream)
  · Source Code Pro 7 uprights + 7 italics (no Thin upstream)
  · Roboto Mono    7 uprights + 7 italics  (100-700, instanced from the
                                            google/fonts variable font)
  · Noto Sans Symbols   1 upright (Regular) — plain-text symbol fallback
  · Noto Sans Symbols 2 1 upright (Regular) — dingbat / warning / star fallback
"""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
FONT_DIR = ROOT / "src" / "dartwork_mpl" / "asset" / "font"
LICENSE_DIR = FONT_DIR / "licenses"

STD = [
    "Thin",
    "ExtraLight",
    "Light",
    "Regular",
    "Medium",
    "SemiBold",
    "Bold",
    "ExtraBold",
    "Black",
]


def gh_json(endpoint: str) -> Any:
    """Return parsed JSON from ``gh api <endpoint>``."""
    out = subprocess.run(
        ["gh", "api", endpoint], capture_output=True, text=True, check=True
    ).stdout
    return json.loads(out)


def dir_urls(repo: str, path: str) -> dict[str, str]:
    """Map {filename: raw download_url} for a repo directory."""
    data = gh_json(f"repos/{repo}/contents/{path}")
    return {e["name"]: e["download_url"] for e in data if e.get("download_url")}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "dm-fetch"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def norm_italic(name: str) -> str:
    """Normalize an upstream italic token to ``…Italic`` / ``-Italic``."""
    stem = name.rsplit(".", 1)[0]
    ext = name.rsplit(".", 1)[1]
    # Adobe uses the ``It`` abbreviation (…-It, …-BoldIt).
    if stem.endswith("It") and not stem.endswith("Italic"):
        stem = stem[:-2] + "Italic"
    stem = stem.replace("-Italic", "-Italic")  # no-op, keeps -Italic form
    return f"{stem}.{ext}"


def want_std_faces(
    stem: str, weights: list[str], italics: bool, ext: str
) -> list[str]:
    """Build the target filenames for a standard-labeled family."""
    out = []
    for w in weights:
        out.append(f"{stem}-{w}.{ext}")
        if italics:
            it = "Italic" if w == "Regular" else f"{w}Italic"
            out.append(f"{stem}-{it}.{ext}")
    return out


# ── per-family source manifest ──────────────────────────────────────
def plan() -> list[dict]:
    return [
        {
            # The current Google Fonts Roboto family is a wdth,wght variable
            # font. Its packaged static instances clamp Thin/ExtraLight
            # usWeightClass to 250, so we instance the variable font directly
            # (pinning wdth=100 = normal width) to get honest 100-900
            # usWeightClass values. Family name records stay "Roboto".
            "family": "Roboto",
            "kind": "gf-variable-instance",
            "repo": "google/fonts",
            "vf_path": "ofl/roboto/Roboto[wdth,wght].ttf",
            "vf_italic_path": "ofl/roboto/Roboto-Italic[wdth,wght].ttf",
            "pin": {"wdth": 100},
            "ext": "ttf",
            "wght": {
                "Thin": 100,
                "ExtraLight": 200,
                "Light": 300,
                "Regular": 400,
                "Medium": 500,
                "SemiBold": 600,
                "Bold": 700,
                "ExtraBold": 800,
                "Black": 900,
            },
            "italics": True,
            "stem": "Roboto",
            "license": (
                "google/fonts",
                "ofl/roboto/OFL.txt",
                "LICENSE-Roboto.txt",
            ),
        },
        {
            "family": "Pretendard",
            "kind": "gh-dir",
            "repo": "orioncactus/pretendard",
            "path": "packages/pretendard/dist/public/static",
            "ext": "otf",
            "weights": STD,  # all 9
            "italics": False,
            "stem": "Pretendard",
            "license": (
                "orioncactus/pretendard",
                "LICENSE",
                "LICENSE-Pretendard.txt",
            ),
        },
        {
            "family": "IBM Plex Sans",
            "kind": "gh-dir",
            "repo": "IBM/plex",
            "path": "packages/plex-sans/fonts/complete/ttf",
            "ext": "ttf",
            "weights": [
                "Thin",
                "ExtraLight",
                "Light",
                "Regular",
                "Medium",
                "SemiBold",
                "Bold",
            ],
            "italics": True,
            "stem": "IBMPlexSans",
            "license": (
                "IBM/plex",
                "packages/plex-sans/fonts/complete/ttf/license.txt",
                "LICENSE-IBMPlex.txt",
            ),
        },
        {
            "family": "IBM Plex Mono",
            "kind": "gh-dir",
            "repo": "IBM/plex",
            "path": "packages/plex-mono/fonts/complete/ttf",
            "ext": "ttf",
            "weights": [
                "Thin",
                "ExtraLight",
                "Light",
                "Regular",
                "Medium",
                "SemiBold",
                "Bold",
            ],
            "italics": True,
            "stem": "IBMPlexMono",
            "license": None,  # same OFL as IBM Plex Sans
        },
        {
            "family": "Source Sans 3",
            "kind": "release-zip",
            "repo": "adobe-fonts/source-sans",
            "asset_contains": "TTF-",
            "ext": "ttf",
            "weights": [
                "ExtraLight",
                "Light",
                "Regular",
                "Medium",
                "SemiBold",
                "Bold",
                "Black",
            ],
            "italics": True,
            "stem": "SourceSans3",
            "license": (
                "adobe-fonts/source-sans",
                "LICENSE.md",
                "LICENSE-SourceSans3.txt",
            ),
        },
        {
            "family": "Paperlogy",
            "kind": "repo-zip",
            "repo": "Freesentation/paperlogy",
            "zip_name": "Paperlogy-1.001.zip",
            "ext": "ttf",
            # numeric-prefixed weights matching the existing bundle
            "numeric": {
                "1Thin": 1,
                "2ExtraLight": 2,
                "3Light": 3,
                "4Regular": 4,
                "5Medium": 5,
                "6SemiBold": 6,
                "7Bold": 7,
                "8ExtraBold": 8,
                "9Black": 9,
            },
            "stem": "Paperlogy",
            "license": (
                "Freesentation/paperlogy",
                "OFL license.txt",
                "LICENSE-Paperlogy.txt",
            ),
        },
        {
            "family": "JetBrains Mono",
            "kind": "gh-dir",
            "repo": "JetBrains/JetBrainsMono",
            "path": "fonts/ttf",
            "ext": "ttf",
            "weights": [
                "Thin",
                "ExtraLight",
                "Light",
                "Regular",
                "Medium",
                "SemiBold",
                "Bold",
                "ExtraBold",
            ],
            "italics": True,
            "stem": "JetBrainsMono",
            "license": (
                "JetBrains/JetBrainsMono",
                "OFL.txt",
                "LICENSE-JetBrainsMono.txt",
            ),
        },
        {
            "family": "Source Code Pro",
            "kind": "release-zip",
            "repo": "adobe-fonts/source-code-pro",
            "asset_contains": "TTF-",
            "ext": "ttf",
            "weights": [
                "ExtraLight",
                "Light",
                "Regular",
                "Medium",
                "SemiBold",
                "Bold",
                "Black",
            ],
            "italics": True,
            "stem": "SourceCodePro",
            "license": (
                "adobe-fonts/source-code-pro",
                "LICENSE.md",
                "LICENSE-SourceCodePro.txt",
            ),
        },
        {
            # Roboto Mono is a wght-only variable font upstream; instance the
            # 7 named weights (100-700) + italics for the full mono ladder.
            "family": "Roboto Mono",
            "kind": "gf-variable-instance",
            "repo": "google/fonts",
            "vf_path": "ofl/robotomono/RobotoMono[wght].ttf",
            "vf_italic_path": "ofl/robotomono/RobotoMono-Italic[wght].ttf",
            "pin": {},
            "ext": "ttf",
            "wght": {
                "Thin": 100,
                "ExtraLight": 200,
                "Light": 300,
                "Regular": 400,
                "Medium": 500,
                "SemiBold": 600,
                "Bold": 700,
            },
            "italics": True,
            "stem": "RobotoMono",
            "license": (
                "google/fonts",
                "ofl/robotomono/OFL.txt",
                "LICENSE-RobotoMono.txt",
            ),
        },
        # ── Families added 2026-07 for full re-sourcing coverage ──
        # These were bundled by hand before; the entries below let
        # fetch_fonts reproduce them from the same OFL/Apache upstreams.
        # Licenses are already bundled (LICENSE-Inter / -NotoSans /
        # -NotoSansCJK) and G11-mapped, so no `license` key is needed.
        # The Noto Sans Symbols / Symbols 2 families (added 2026-07 for
        # scientific/report special-character coverage) come from the same
        # notofonts upstream and are covered by LICENSE-NotoSans (one OFL
        # text per upstream project — see tests/test_font_licenses.py).
        {
            "family": "Inter",
            "kind": "release-zip",
            "repo": "rsms/inter",
            # Inter-<ver>.zip; static instances live in extras/ttf/.
            "asset_contains": "Inter-",
            "ext": "ttf",
            "weights": STD,
            "italics": True,
            "stem": "Inter",
        },
        {
            "family": "Inter Display",
            "kind": "release-zip",
            "repo": "rsms/inter",
            "asset_contains": "Inter-",  # same zip, InterDisplay-* statics
            "ext": "ttf",
            "weights": STD,
            "italics": True,
            "stem": "InterDisplay",
        },
        {
            "family": "Noto Sans",
            "kind": "gh-dir",
            "repo": "notofonts/notofonts.github.io",
            "path": "fonts/NotoSans/full/ttf",
            "ext": "ttf",
            "weights": STD,
            "italics": True,
            "stem": "NotoSans",
        },
        {
            "family": "Noto Sans Condensed",
            "kind": "gh-dir-width",
            "repo": "notofonts/notofonts.github.io",
            "path": "fonts/NotoSans/full/ttf",
            "ext": "ttf",
            "weights": STD,
            "italics": True,
            "src_stem": "NotoSans",
            "width": "Condensed",
            "stem": "NotoSans_Condensed",
        },
        {
            "family": "Noto Sans SemiCondensed",
            "kind": "gh-dir-width",
            "repo": "notofonts/notofonts.github.io",
            "path": "fonts/NotoSans/full/ttf",
            "ext": "ttf",
            "weights": STD,
            "italics": True,
            "src_stem": "NotoSans",
            "width": "SemiCondensed",
            "stem": "NotoSans_SemiCondensed",
        },
        {
            "family": "Noto Sans Math",
            "kind": "gh-dir",
            "repo": "notofonts/notofonts.github.io",
            "path": "fonts/NotoSansMath/full/ttf",
            "ext": "ttf",
            "weights": ["Regular"],
            "italics": False,
            "stem": "NotoSansMath",
        },
        {
            "family": "Noto Sans Symbols",
            "kind": "gh-dir",
            "repo": "notofonts/notofonts.github.io",
            "path": "fonts/NotoSansSymbols/full/ttf",
            "ext": "ttf",
            # Regular only: the plain-text fallback chain needs a single
            # weight for symbol coverage (arrows, geometric shapes, misc
            # technical). Upstream ships 9 weights; we bundle just Regular.
            "weights": ["Regular"],
            "italics": False,
            "stem": "NotoSansSymbols",
        },
        {
            "family": "Noto Sans Symbols 2",
            "kind": "gh-dir",
            "repo": "notofonts/notofonts.github.io",
            "path": "fonts/NotoSansSymbols2/full/ttf",
            "ext": "ttf",
            # Regular is the only weight upstream publishes. Covers the
            # dingbat / warning / star / check ranges (⚠ ✓ ★) the sans and
            # math faces lack.
            "weights": ["Regular"],
            "italics": False,
            "stem": "NotoSansSymbols2",
        },
        {
            "family": "Noto Sans CJK KR",
            "kind": "gh-file-subset",
            "repo": "notofonts/noto-cjk",
            "src_path": "Sans/OTF/Korean/NotoSansCJKkr-Regular.otf",
            "ext": "otf",
            "weight": "Regular",
            "stem": "NotoSansCJK",
            # Korean (Hangul syllables + jamo) + Latin + CJK punctuation.
            "unicodes": [
                (0x0020, 0x007E),  # Basic Latin
                (0x00A0, 0x00FF),  # Latin-1 Supplement
                (0x2000, 0x206F),  # General Punctuation
                (0x3000, 0x303F),  # CJK Symbols and Punctuation
                (0x3130, 0x318F),  # Hangul Compatibility Jamo
                (0x1100, 0x11FF),  # Hangul Jamo
                (0xA960, 0xA97F),  # Hangul Jamo Extended-A
                (0xAC00, 0xD7A3),  # Hangul Syllables
                (0xD7B0, 0xD7FF),  # Hangul Jamo Extended-B
                (0xFF00, 0xFFEF),  # Halfwidth and Fullwidth Forms
            ],
        },
    ]


def write_license(spec: dict) -> None:
    if not spec.get("license"):
        return
    repo, path, out = spec["license"]
    try:
        meta = gh_json(f"repos/{repo}/contents/{path.replace(' ', '%20')}")
        url = meta["download_url"]
        LICENSE_DIR.mkdir(parents=True, exist_ok=True)
        (LICENSE_DIR / out).write_bytes(fetch(url))
        print(f"    license -> licenses/{out}")
    except Exception as e:  # noqa: BLE001
        print(f"    !! license fetch failed for {spec['family']}: {e}")


def do_gh_dir(spec: dict, added: list[str]) -> None:
    urls = dir_urls(spec["repo"], spec["path"])
    targets = want_std_faces(
        spec["stem"], spec["weights"], spec["italics"], spec["ext"]
    )
    for tgt in targets:
        # source filename == target filename for these upstreams
        if tgt not in urls:
            print(f"    ?? upstream missing {tgt}")
            continue
        (FONT_DIR / tgt).write_bytes(fetch(urls[tgt]))
        added.append(tgt)
    write_license(spec)


def do_release_zip(spec: dict, added: list[str]) -> None:
    rel = gh_json(f"repos/{spec['repo']}/releases/latest")
    asset = next(
        a for a in rel["assets"] if spec["asset_contains"] in a["name"]
    )
    blob = fetch(asset["browser_download_url"])
    zf = zipfile.ZipFile(io.BytesIO(blob))
    # Case-insensitive map so upstream spellings (Adobe's "Semibold",
    # "…It") resolve to our canonical target names ("SemiBold", "…Italic").
    wanted = {
        w.lower(): w
        for w in want_std_faces(
            spec["stem"], spec["weights"], spec["italics"], spec["ext"]
        )
    }
    for member in zf.namelist():
        base = Path(member).name
        if not base.lower().endswith("." + spec["ext"]):
            continue
        canon = wanted.get(norm_italic(base).lower())
        if canon:
            (FONT_DIR / canon).write_bytes(zf.read(member))
            added.append(canon)
    write_license(spec)


def do_repo_zip(spec: dict, added: list[str]) -> None:
    meta = gh_json(
        f"repos/{spec['repo']}/contents/{spec['zip_name'].replace(' ', '%20')}"
    )
    blob = fetch(meta["download_url"])
    zf = zipfile.ZipFile(io.BytesIO(blob))
    for member in zf.namelist():
        base = Path(member).name
        if not base.lower().endswith("." + spec["ext"]):
            continue
        # match e.g. Paperlogy-9Black.ttf
        for label in spec["numeric"]:
            if base == f"{spec['stem']}-{label}.{spec['ext']}":
                (FONT_DIR / base).write_bytes(zf.read(member))
                added.append(base)
                break
    write_license(spec)


def do_gf_variable_instance(spec: dict, added: list[str]) -> None:
    """Instance named weights from a Google Fonts variable font.

    The modern Google Fonts Roboto / Roboto Mono families ship as variable
    fonts; their packaged static instances clamp the lightest weights'
    ``usWeightClass`` (Thin/ExtraLight both report 250). Pinning the weight
    axis with ``fontTools.varLib.instancer`` instead yields honest 100-900
    ``usWeightClass`` values, and ``updateFontNames`` keeps the typographic
    family name record intact (``Roboto`` / ``Roboto Mono``) while labelling
    each instance's subfamily.
    """
    from io import BytesIO

    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer

    ext = spec["ext"]
    pin = spec.get("pin", {})
    italics = spec.get("italics", False)

    up_dir, up_name = spec["vf_path"].rsplit("/", 1)
    up_urls = dir_urls(spec["repo"], up_dir)
    up_vf = fetch(up_urls[up_name])
    it_vf = None
    if italics:
        it_dir, it_name = spec["vf_italic_path"].rsplit("/", 1)
        it_urls = (
            up_urls if it_dir == up_dir else dir_urls(spec["repo"], it_dir)
        )
        it_vf = fetch(it_urls[it_name])

    def _instance(vf_bytes: bytes, wval: int, tgt: str) -> None:
        # recalcTimestamp=False keeps the upstream ``head.modified`` date so
        # re-runs are byte-identical (the default would stamp "now").
        font = TTFont(BytesIO(vf_bytes), recalcTimestamp=False)
        instancer.instantiateVariableFont(
            font, {**pin, "wght": wval}, updateFontNames=True, inplace=True
        )
        font.save(str(FONT_DIR / tgt))
        added.append(tgt)

    for name, wval in spec["wght"].items():
        _instance(up_vf, wval, f"{spec['stem']}-{name}.{ext}")
        if italics and it_vf is not None:
            it = "Italic" if name == "Regular" else f"{name}Italic"
            _instance(it_vf, wval, f"{spec['stem']}-{it}.{ext}")
    write_license(spec)


def _grab(urls: dict[str, str], src: str, tgt: str, added: list[str]) -> None:
    """Download ``urls[src]`` and write it under the target filename ``tgt``."""
    if src not in urls:
        print(f"    ?? upstream missing {src}")
        return
    (FONT_DIR / tgt).write_bytes(fetch(urls[src]))
    added.append(tgt)


def do_gh_dir_width(spec: dict, added: list[str]) -> None:
    """Fetch a Noto width sub-family, renaming to dartwork's stem convention.

    Upstream encodes the width as a name prefix on the weight
    (``NotoSans-CondensedBold.ttf``); dartwork bundles it under a
    stem-separated name (``NotoSans_Condensed-Bold.ttf``). This maps each
    upstream face to that canonical target.
    """
    urls = dir_urls(spec["repo"], spec["path"])
    src_stem = spec["src_stem"]  # e.g. "NotoSans"
    width = spec["width"]  # e.g. "Condensed"
    ext = spec["ext"]
    for w in spec["weights"]:
        # upright: Regular has no weight token upstream (NotoSans-Condensed)
        src_up = (
            f"{src_stem}-{width}.{ext}"
            if w == "Regular"
            else f"{src_stem}-{width}{w}.{ext}"
        )
        _grab(urls, src_up, f"{spec['stem']}-{w}.{ext}", added)
        if spec.get("italics"):
            it = "Italic" if w == "Regular" else f"{w}Italic"
            _grab(
                urls,
                f"{src_stem}-{width}{it}.{ext}",
                f"{spec['stem']}-{it}.{ext}",
                added,
            )
    write_license(spec)


def do_gh_file_subset(spec: dict, added: list[str]) -> None:
    """Download one large OTF and write a language-subset copy.

    The bundled ``NotoSansCJK-Regular.otf`` is a Korean+Latin subset of
    the full 16 MB ``NotoSansCJKkr-Regular.otf`` — shipping the whole CJK
    face would balloon the wheel. Subsets via ``fontTools`` (already a
    matplotlib dependency) to the configured unicode ranges.
    """
    from fontTools import subset as _subset
    from fontTools.ttLib import TTFont as _TTFont

    meta = gh_json(
        f"repos/{spec['repo']}/contents/{spec['src_path'].replace(' ', '%20')}"
    )
    blob = fetch(meta["download_url"])
    src_tmp = FONT_DIR / f".{spec['stem']}-src.tmp"
    src_tmp.write_bytes(blob)
    try:
        options = _subset.Options()
        # Keep OpenType layout + hinting so Korean renders identically to
        # the full face; only glyph coverage is reduced.
        options.name_IDs = ["*"]
        options.recalc_bounds = True
        font = _TTFont(str(src_tmp))
        subsetter = _subset.Subsetter(options=options)
        subsetter.populate(unicodes=_expand_unicode_ranges(spec["unicodes"]))
        subsetter.subset(font)
        tgt = f"{spec['stem']}-{spec['weight']}.{spec['ext']}"
        font.save(str(FONT_DIR / tgt))
        font.close()
        added.append(tgt)
    finally:
        src_tmp.unlink(missing_ok=True)
    write_license(spec)


def _expand_unicode_ranges(ranges: list[tuple[int, int]]) -> list[int]:
    out: list[int] = []
    for lo, hi in ranges:
        out.extend(range(lo, hi + 1))
    return out


def verify() -> None:
    from matplotlib import ft2font

    bad = []
    files = sorted(
        p for p in FONT_DIR.iterdir() if p.suffix.lower() in (".ttf", ".otf")
    )
    fams: dict[str, int] = {}
    for p in files:
        try:
            f = ft2font.FT2Font(str(p))
            fams[f.family_name] = fams.get(f.family_name, 0) + 1
        except Exception as e:  # noqa: BLE001, PERF203
            bad.append((p.name, str(e)))
    print(f"\nOn disk: {len(files)} font files, {len(fams)} families")
    for fam, n in sorted(fams.items()):
        print(f"  {fam:26s} {n}")
    print("Corrupt:", bad or "NONE")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    ap.add_argument(
        "--only",
        default="",
        help="comma-separated family names to fetch (default: all)",
    )
    args = ap.parse_args()
    if args.verify:
        verify()
        return

    specs = plan()
    if args.only:
        names = {s.strip() for s in args.only.split(",")}
        specs = [s for s in specs if s["family"] in names]

    FONT_DIR.mkdir(parents=True, exist_ok=True)
    added: list[str] = []
    for spec in specs:
        print(f"== {spec['family']} ({spec['kind']}) ==")
        try:
            if spec["kind"] == "gh-dir":
                do_gh_dir(spec, added)
            elif spec["kind"] == "release-zip":
                do_release_zip(spec, added)
            elif spec["kind"] == "repo-zip":
                do_repo_zip(spec, added)
            elif spec["kind"] == "gh-dir-width":
                do_gh_dir_width(spec, added)
            elif spec["kind"] == "gf-variable-instance":
                do_gf_variable_instance(spec, added)
            elif spec["kind"] == "gh-file-subset":
                do_gh_file_subset(spec, added)
        except Exception as e:  # noqa: BLE001
            print(f"    !! {spec['family']} failed: {e}", file=sys.stderr)
    print(f"\nAdded/refreshed {len(added)} files.")
    verify()


if __name__ == "__main__":
    main()
