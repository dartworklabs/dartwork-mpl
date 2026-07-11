"""Reachability checks for raw-included documentation assets."""

from __future__ import annotations

import re
import subprocess
from collections import defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DOCS = _ROOT / "docs"
_RAW_FILE_RE = re.compile(
    r"^```\{raw\} html\s*$\n^:file:\s*(\S+)\s*$", re.MULTILINE
)
_SRC_RE = re.compile(r"""\bsrc=["']([^"']+)["']""")


def _raw_includes() -> list[tuple[Path, Path]]:
    includes = []
    for source in sorted(_DOCS.rglob("*.md")):
        text = source.read_text(encoding="utf-8")
        for target in _RAW_FILE_RE.findall(text):
            includes.append((source, (source.parent / target).resolve()))
    return includes


def _tracked_docs_html() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--", "docs/**/*.html"],
        cwd=_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [_ROOT / path for path in result.stdout.splitlines()]


def _source_asset(include: Path, src: str) -> Path:
    static_match = re.fullmatch(r"(?:\.\./)?_static/(.+)", src)
    if static_match:
        return _DOCS / "_static" / static_match.group(1)

    images_match = re.fullmatch(r"(?:\.\./)?_images/(.+)", src)
    if images_match:
        return include.parent / "images" / images_match.group(1)

    return include.parent / src


def test_raw_html_file_targets_exist() -> None:
    missing = [
        f"{source.relative_to(_ROOT)} -> {target.relative_to(_ROOT)}"
        for source, target in _raw_includes()
        if not target.is_file()
    ]
    assert not missing, "missing raw HTML targets:\n" + "\n".join(missing)


def test_committed_html_relative_sources_exist() -> None:
    include_sources: dict[Path, list[Path]] = defaultdict(list)
    for source, target in _raw_includes():
        include_sources[target].append(source)

    missing = []
    for html in _tracked_docs_html():
        text = html.read_text(encoding="utf-8")
        relative_srcs = [
            src
            for src in _SRC_RE.findall(text)
            if not re.match(r"(?:[a-z]+:|//|/|#)", src)
        ]
        for src in relative_srcs:
            owners = include_sources.get(html.resolve(), [])
            if not owners:
                missing.append(
                    f"{html.relative_to(_ROOT)}: no including document"
                )
                continue
            for owner in owners:
                asset = _source_asset(owner, src)
                if not asset.is_file():
                    missing.append(
                        f"{html.relative_to(_ROOT)}: {src} -> "
                        f"{asset.relative_to(_ROOT)}"
                    )

    assert not missing, "missing relative HTML assets:\n" + "\n".join(missing)
