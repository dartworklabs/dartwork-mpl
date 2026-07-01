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
  · Roboto        6 uprights + 6 italics   (Thin Light Reg Med Bold Black)
  · Paperlogy     9 uprights               (no italics upstream — Korean)
  · Pretendard    9 uprights               (no italics upstream — Korean)
  · IBM Plex Sans 7 uprights + 7 italics   (Text weight skipped)
  · IBM Plex Mono 7 uprights + 7 italics   (Text weight skipped)
  · Source Sans 3 7 uprights + 7 italics   (no Thin upstream)
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
            "family": "Roboto",
            "kind": "gh-dir",
            "repo": "googlefonts/roboto-2",
            "path": "src/hinted",
            "ext": "ttf",
            "weights": ["Thin", "Light", "Regular", "Medium", "Bold", "Black"],
            "italics": True,
            "stem": "Roboto",
            "license": (
                "googlefonts/roboto-2",
                "LICENSE",
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
    args = ap.parse_args()
    if args.verify:
        verify()
        return

    FONT_DIR.mkdir(parents=True, exist_ok=True)
    added: list[str] = []
    for spec in plan():
        print(f"== {spec['family']} ({spec['kind']}) ==")
        try:
            if spec["kind"] == "gh-dir":
                do_gh_dir(spec, added)
            elif spec["kind"] == "release-zip":
                do_release_zip(spec, added)
            elif spec["kind"] == "repo-zip":
                do_repo_zip(spec, added)
        except Exception as e:  # noqa: BLE001
            print(f"    !! {spec['family']} failed: {e}", file=sys.stderr)
    print(f"\nAdded/refreshed {len(added)} files.")
    verify()


if __name__ == "__main__":
    main()
