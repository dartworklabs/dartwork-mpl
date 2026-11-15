"""The MCP server: five tools that connect an agent to the other slices.

``guide`` reads the skill or one reference page, ``search_reference`` and
``get_reference`` look up templates, presets, colours and lint rules,
``lint`` checks a script without running it and ``render`` runs it once in
a child process and returns the image, the source, a check report and a
manifest, written as a bundle to a directory (see :mod:`.render`; it is
not a sandbox). No resources, no prompts, no store: sharing a bundle is a
separate service's job. Transport is stdio only.

The bundle contract (``manifest.json``, schema ``dartwork-mpl.bundle``
version 1, :class:`.model.Manifest`)::

    status    rendered | lint_blocked | no_figure | raised | timed_out | crashed
    created   ISO-8601 UTC time; seconds: wall time of the call
    versions  dartwork-mpl, matplotlib, python
    files     [{path, sha256, bytes}] for figure.png, figure.pdf,
              source.py and report.json (paths relative to the bundle)
    inputs    [{path, sha256, bytes}] for the data files the caller declared
    canvas    {width_in, height_in, width_px, height_px} or null

``dartwork-mpl-mcp`` (:func:`main`) starts the server.
"""

from __future__ import annotations

import sys

__all__ = ["main"]


def main() -> None:
    """Run the server over stdio; without the ``[mcp]`` extra, exit 1 with a hint."""
    try:
        from .server import server
    except ImportError as exc:
        sys.stderr.write(
            "dartwork-mpl-mcp needs the [mcp] extra:"
            " pip install 'dartwork-mpl[mcp]'\n"
            f"({exc})\n"
        )
        sys.exit(1)
    server.run(transport="stdio", show_banner=False)
