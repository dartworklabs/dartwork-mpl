"""Extract one CHANGELOG section and reflow it for GitHub Releases.

CHANGELOG.md follows the Keep a Changelog convention with hard-wrapped
paragraphs at ~72 chars. GitHub Releases render single newlines as soft
breaks (``<br>``-like behaviour) inside list items, so pasting the
CHANGELOG section verbatim produces a release page that only uses about
half of the available column width.

This helper extracts the section for a given version (e.g. ``0.5.3``)
and collapses each list item or paragraph onto a single line so the
release page flows to the full column width. The CHANGELOG file itself
stays wrapped — the reflow is a *render-time* transform for the release
page only.

Usage
-----

::

    python scripts/extract_release_notes.py CHANGELOG.md 0.5.3 > notes.md
    gh release create v0.5.3 --notes-file notes.md ...

In CI (``.github/workflows/release.yml``) the script is invoked with the
tag's version (``${GITHUB_REF_NAME#v}``) right before ``gh release
create`` runs, so every tagged release ships reflowed notes
automatically.

Exit codes
----------

* ``0``  — section found and printed
* ``1``  — invalid CLI usage
* ``2``  — version section not found in the CHANGELOG
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Matches the start of a top-level CHANGELOG section, e.g.
# ``## [0.5.3] - 2026-06-20`` or ``## [Unreleased]``. Captures the
# version inside the brackets.
_SECTION_START = re.compile(r"^##\s+\[([^\]]+)\]")

# Matches a Markdown bullet item start: ``- foo``, ``* bar``, ``+ baz``
# with optional indentation. Used to detect when a continuation line
# should *not* be folded into the previous one.
_BULLET_START = re.compile(r"^(\s*)[-*] ")


def extract_section(changelog: str, version: str) -> str:
    """Return the body of the section for ``version`` (without its header).

    Stops at the next ``## [...]`` heading or end of file.

    Raises
    ------
    LookupError
        If no section matches ``version``.
    """
    in_section = False
    body: list[str] = []
    for line in changelog.splitlines():
        match = _SECTION_START.match(line)
        if match:
            if in_section:
                break
            if match.group(1) == version:
                in_section = True
                continue  # skip the section header itself
        elif in_section:
            body.append(line)
    if not in_section:
        raise LookupError(f"no [{version}] section in CHANGELOG")
    # Trim leading + trailing blank lines so the rendered output is clean.
    while body and not body[0].strip():
        body.pop(0)
    while body and not body[-1].strip():
        body.pop()
    return "\n".join(body)


def reflow(text: str) -> str:
    """Collapse hard-wrapped list items and paragraphs onto single lines.

    The reflow preserves Markdown structure:

    * Headings (``#`` / ``##`` / …) and horizontal rules (``---``) stay
      on their own line.
    * Blank lines separate paragraphs and are preserved.
    * A list item start (``-`` / ``*`` only — ``+`` is *not* treated as
      a list marker so it doesn't misparse ``lint + execution`` style
      continuations) starts a fresh buffer with the original leading
      indentation.
    * Continuation lines (anything that isn't a bullet, heading, or
      blank line) are folded into the current item with a single space.
    """
    out: list[str] = []
    buf: list[str] = []

    def flush() -> None:
        if not buf:
            return
        match = re.match(r"^\s*", buf[0])
        leading = match.group(0) if match else ""
        joined = " ".join(line.strip() for line in buf)
        out.append(leading + joined)
        buf.clear()

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            flush()
            out.append("")
            continue
        if stripped.startswith("#") or stripped == "---":
            flush()
            out.append(line.rstrip())
            continue
        if _BULLET_START.match(line):
            flush()
            buf.append(line.rstrip())
            continue
        buf.append(line.rstrip())

    flush()
    return "\n".join(out).rstrip() + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "usage: extract_release_notes.py CHANGELOG.md VERSION",
            file=sys.stderr,
        )
        return 1
    changelog_path = Path(argv[1])
    version = argv[2]
    try:
        section = extract_section(
            changelog_path.read_text(encoding="utf-8"), version
        )
    except LookupError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2
    sys.stdout.write(reflow(section))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
