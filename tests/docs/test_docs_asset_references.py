"""Targets must exist as committed files, or be gitignored build outputs produced by the docs build."""

from __future__ import annotations

import random
import re
import subprocess
import sys
import textwrap
from collections import defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_DOCS = _ROOT / "docs"
_RAW_FILE_RE = re.compile(
    r"^```\{raw\} html\s*$\n^:file:\s*(\S+)\s*$", re.MULTILINE
)
_SRC_RE = re.compile(r"""\bsrc=["']([^"']+)["']""")


def _raw_includes() -> list[tuple[Path, Path]]:
    """Read raw HTML includes from the public Markdown source surface."""
    includes = []
    for source in sorted(_DOCS.rglob("*.md")):
        # Sphinx excludes these internal notes via ``superpowers/**``.
        if source.relative_to(_DOCS).parts[0] == "superpowers":
            continue
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


def _gitignored_paths(paths: list[Path]) -> set[Path]:
    if not paths:
        return set()

    relative_paths = [path.relative_to(_ROOT) for path in paths]
    result = subprocess.run(
        ["git", "check-ignore", "--stdin"],
        cwd=_ROOT,
        input="".join(f"{path.as_posix()}\n" for path in relative_paths),
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 1):
        raise subprocess.CalledProcessError(
            result.returncode,
            result.args,
            output=result.stdout,
            stderr=result.stderr,
        )
    return {Path(path) for path in result.stdout.splitlines()}


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
        (target, f"{source.relative_to(_ROOT)} -> {target.relative_to(_ROOT)}")
        for source, target in _raw_includes()
        if not target.is_file()
    ]
    ignored = _gitignored_paths([target for target, _ in missing])
    broken = [
        message
        for target, message in missing
        if target.relative_to(_ROOT) not in ignored
    ]
    assert not broken, "missing raw HTML targets:\n" + "\n".join(broken)


def test_committed_html_relative_sources_exist() -> None:
    include_sources: dict[Path, list[Path]] = defaultdict(list)
    for source, target in _raw_includes():
        include_sources[target].append(source)

    missing: list[tuple[Path, str]] = []
    structural_errors = []
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
                structural_errors.append(
                    f"{html.relative_to(_ROOT)}: no including document"
                )
                continue
            for owner in owners:
                asset = _source_asset(owner, src)
                if not asset.is_file():
                    missing.append(
                        (
                            asset,
                            f"{html.relative_to(_ROOT)}: {src} -> "
                            f"{asset.relative_to(_ROOT)}",
                        )
                    )

    ignored = _gitignored_paths([asset for asset, _ in missing])
    broken = structural_errors + [
        message
        for asset, message in missing
        if asset.relative_to(_ROOT) not in ignored
    ]
    assert not broken, "missing relative HTML assets:\n" + "\n".join(broken)


def test_raw_includes_never_opens_excluded_design_sources(
    tmp_path: Path,
) -> None:
    """Read public includes while an audit trap denies every internal design."""
    docs = tmp_path / "docs"
    internal = docs / "superpowers"
    internal.mkdir(parents=True)
    generator = random.Random(0)
    internal_paths = ["design.md", "specs/one.md", "plans/deep/two.md"]
    for index in range(12):
        parents = [f"part{generator.randrange(10)}" for _ in range(index % 5)]
        internal_paths.append("/".join([*parents, f"note{index}.md"]))
    for relative in internal_paths:
        source = internal / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("```{raw} html\n:file: hidden.html\n```\n")
    public = docs / "public.md"
    public.write_text("```{raw} html\n:file: visible.html\n```\n")
    nested = docs / "reference" / "superpowers" / "public.md"
    nested.parent.mkdir(parents=True)
    nested.write_text("```{raw} html\n:file: ../../visible.html\n```\n")
    (docs / "visible.html").write_text("<p>Public asset</p>\n")
    code = textwrap.dedent(
        """
        import os
        from pathlib import Path
        import runpy
        import sys

        namespace = runpy.run_path(sys.argv[1])
        docs = Path(sys.argv[2])
        excluded = {path.resolve() for path in (docs / "superpowers").rglob("*.md")}

        def deny_internal_read(event, args):
            "Reject an excluded input before its actual file can be opened."
            if event == "open" and isinstance(args[0], (str, bytes)):
                if Path(os.fsdecode(args[0])).resolve() in excluded:
                    raise AssertionError("opened an excluded design source")

        sys.addaudithook(deny_internal_read)
        collect = namespace["_raw_includes"]
        collect.__globals__["_DOCS"] = docs
        assert collect() == [
            (docs / "public.md", docs / "visible.html"),
            (docs / "reference/superpowers/public.md", docs / "visible.html"),
        ]
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", code, str(Path(__file__)), str(docs)],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
