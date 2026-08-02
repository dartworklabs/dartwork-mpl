"""Custom Sphinx build hooks for dartwork-mpl documentation.

Extracted from conf.py for maintainability. Handles:
- Gallery index generation (manual indices after sphinx-gallery)
- Color system asset generation
- Font file copying for HTML specimens
- AI plot-template metadata index (T6 in the AI-readiness roadmap)
"""

import contextlib
import json
import re
from pathlib import Path

_GALLERY_HEADER = """Examples Gallery
================

This gallery contains examples demonstrating the features and capabilities
of dartwork-mpl. Browse the categories below for ready-to-use patterns
and techniques.
"""

_GALLERY_CATEGORIES = [
    "01_styling_and_themes",
    "02_color_system",
    "03_formatting",
    "04_layout_and_annotations",
    "05_helpers_api",
    "06_chart_recipes",
    "07_real_world_dashboards",
    "08_creative_visualizations",
    "09_ai_templates",
    # sphinx-gallery renders 09_ai_templates_advanced (it is in conf.py's
    # examples_dirs/gallery_dirs), so it must appear here too — otherwise
    # its 18 tier-2 pages are orphaned from the manual toctree.
    "09_ai_templates_advanced",
]


def create_placeholder_index(app):
    """Create placeholder index.rst so toctree finds it before sphinx-gallery."""
    gallery_dir = Path(app.srcdir) / "examples_gallery"
    gallery_dir.mkdir(parents=True, exist_ok=True)

    index_file = gallery_dir / "index.rst"
    if not index_file.exists():
        index_file.write_text(
            "Examples Gallery\n================\n\nLoading...\n"
        )
        print("Created placeholder: examples_gallery/index.rst")


def cleanup_sg_execution_times(app):
    """Remove sphinx-gallery's auto-generated execution-times index before build.

    sphinx-gallery writes ``sg_execution_times.rst`` at the end of every build,
    listing every example it executed. When examples are renamed or deleted
    between builds, the previous file leaves stale cross-references that
    Sphinx then reports as "undefined label" warnings. The file is fully
    regenerated each build, so deleting it up-front is safe and removes the
    noise without losing any information.
    """
    src = Path(app.srcdir)
    for stale in src.glob("**/sg_execution_times.rst"):
        with contextlib.suppress(OSError):
            stale.unlink()


_STALE_GALLERY_SUFFIXES = (
    ".rst",
    ".py",
    ".py.md5",
    ".ipynb",
    ".zip",
    ".codeobj.json",
)


def purge_stale_gallery_artifacts(app):
    """Drop ``examples_gallery/<group>/plot_<stem>.*`` whose source ``.py`` is gone.

    ``examples_gallery/`` is gitignored and regenerated each build by
    sphinx-gallery, but sphinx-gallery only *adds* files — when a source
    example is removed from ``examples_source/`` the previously-generated
    artifacts linger in a developer's local checkout. Sphinx then flags
    the now-orphaned ``plot_*.rst`` with ``toc.not_included`` warnings.

    Scan every gallery group; for each plot stem with no matching source
    file in ``examples_source/<group>/plot_<stem>.py``, remove the
    well-known artifact suffixes. Safe by construction because we only
    touch files inside the gitignored ``examples_gallery/`` tree.
    """
    src = Path(app.srcdir)
    gallery_root = src / "examples_gallery"
    source_root = src / "examples_source"
    if not gallery_root.is_dir() or not source_root.is_dir():
        return

    for group_dir in sorted(gallery_root.iterdir()):
        if not group_dir.is_dir():
            continue
        source_group = source_root / group_dir.name
        if not source_group.is_dir():
            continue
        for rst in group_dir.glob("plot_*.rst"):
            stem = rst.stem  # e.g. "plot_grid_customization"
            if (source_group / f"{stem}.py").exists():
                continue
            for suffix in _STALE_GALLERY_SUFFIXES:
                artifact = group_dir / f"{stem}{suffix}"
                with contextlib.suppress(OSError):
                    artifact.unlink()


def generate_gallery_assets(_app):
    """Bake high-res color system, usage guide, and API images during the build."""
    from color_system.generate_assets import build_gallery_assets

    build_gallery_assets()

    from usage_guide.generate_assets import build_usage_guide_assets

    build_usage_guide_assets()

    from api.generate_assets import build_api_assets

    build_api_assets()

    from fonts.generate_assets import build_font_assets

    build_font_assets()

    from fonts.generate_html_specimens import build_html_specimens

    build_html_specimens()


_LLMS_FULL_HEADER = """\
# dartwork-mpl — full agent reference (llms-full.txt)

This file is generated from the canonical sources listed below and verified
without mutation at docs-build time. Do **not** hand-edit; edit the upstream
files, regenerate this authority explicitly, and then rebuild the docs.

Companions:

- `CLAUDE.md` / `AGENTS.md` — 30-second onboarding for agents.
- `llms.txt` — link index following the llmstxt.org spec.
"""

# Canonical sources, in the order they appear in the concatenated dump.
# (header, repo-relative path) pairs. ``path = None`` means the header
# alone is appended (used for the top-level title block).
_LLMS_FULL_SOURCES: list[tuple[str, str | None]] = [
    ("\n\n---\n## Quickstart\n", "docs/usage_guide/quickstart.md"),
    ("\n\n---\n## Migration guide\n", "docs/migration.md"),
    (
        "\n\n---\n## Anti-pattern catalog (SSOT, YAML)\n",
        "src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml",
    ),
    (
        "\n\n---\n## AI plot templates index\n",
        "docs/examples_source/09_ai_templates/README.rst",
    ),
]


def _check_or_write_authority(
    path: Path, expected: str, *, label: str, write: bool
) -> None:
    """Check one tracked generated authority, or explicitly replace it."""
    encoded = expected.encode("utf-8")
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_file() and path.read_bytes() == encoded:
            print(f"Unchanged generated authority: {label}")
            return
        path.write_bytes(encoded)
        print(f"Wrote generated authority: {label}")
        return

    if not path.is_file():
        raise RuntimeError(
            f"{label} is missing; regenerate it explicitly before the docs build"
        )
    if path.read_bytes() != encoded:
        raise RuntimeError(
            f"{label} is stale; regenerate it explicitly before the docs build"
        )
    print(f"Verified generated authority: {label}")


def generate_llms_full_txt(app, *, write=False):
    """Check ``llms-full.txt`` against its canonical agent-doc sources.

    The Sphinx hook uses the non-writing default so a build cannot hide a
    stale committed authority by mutating the checkout. Maintainers may call
    this function with ``write=True`` as an explicit regeneration action.
    Missing canonical sources always fail before either path can succeed.
    """
    repo_root = Path(app.srcdir).parent

    parts: list[str] = [_LLMS_FULL_HEADER]
    for header, rel in _LLMS_FULL_SOURCES:
        parts.append(header)
        if rel is None:
            continue
        src = repo_root / rel
        if not src.exists():
            raise FileNotFoundError(
                f"llms-full.txt source missing: {src} "
                f"(update _LLMS_FULL_SOURCES in build_hooks.py)"
            )
        parts.append(src.read_text(encoding="utf-8"))

    out = repo_root / "llms-full.txt"
    _check_or_write_authority(
        out, "".join(parts), label=str(out.relative_to(repo_root)), write=write
    )


# ---------------------------------------------------------------------------
# AI plot-template metadata index (T6 in the AI-readiness roadmap).
#
# Each ``docs/examples_source/09_ai_templates/plot_*.py`` carries a
# fenced metadata block:
#
#     # ai-template-meta-start
#     # use_case: <one-sentence purpose>
#     # difficulty: beginner | intermediate | advanced
#     # data_shape: <inputs the agent needs>
#     # tags: comma, separated, keywords
#     # ai-template-meta-end
#
# This hook concatenates every block into a single
# ``05-templates/_index.json`` so MCP and docs-fetching agents can rank
# templates by intent. A missing or incomplete block fails the build,
# which keeps the metadata catalog from drifting silently.
# ---------------------------------------------------------------------------

_TEMPLATE_META_RE: re.Pattern[str] = re.compile(
    r"# ai-template-meta-start\s*\n((?:#[^\n]*\n)+?)# ai-template-meta-end",
    re.MULTILINE,
)
_TEMPLATE_META_REQUIRED: frozenset[str] = frozenset(
    {"use_case", "difficulty", "data_shape", "tags"}
)
_TEMPLATE_DIFFICULTY_VALUES: frozenset[str] = frozenset(
    {"beginner", "intermediate", "advanced"}
)


def _parse_template_meta(block_body: str, source: str) -> dict[str, object]:
    """Parse an ``ai-template-meta`` comment block into a dict.

    Each line inside the fence has the shape ``# key: value``. The
    ``tags`` value is split on commas; everything else stays a string.
    """
    fields: dict[str, object] = {}
    for line in block_body.splitlines():
        body = line.lstrip("#").rstrip()
        if not body.strip():
            continue
        # Allow ``data_shape`` to legitimately contain colons (e.g.
        # ``data_shape: x: list[float], y: list[float]``), so split on
        # the *first* colon only.
        if ":" not in body:
            continue
        key_part, _, value_part = body.partition(":")
        key = key_part.strip()
        value = value_part.strip()
        if key == "tags":
            fields[key] = [t.strip() for t in value.split(",") if t.strip()]
        else:
            fields[key] = value

    missing = _TEMPLATE_META_REQUIRED - fields.keys()
    if missing:
        raise ValueError(
            f"{source}: ai-template-meta missing required keys: "
            f"{sorted(missing)}"
        )
    diff = fields["difficulty"]
    if diff not in _TEMPLATE_DIFFICULTY_VALUES:
        raise ValueError(
            f"{source}: difficulty {diff!r} not in "
            f"{sorted(_TEMPLATE_DIFFICULTY_VALUES)}"
        )
    return fields


def generate_template_index(app, *, write=False):
    """Check ``05-templates/_index.json`` against gallery metadata blocks.

    The Sphinx hook is non-writing; ``write=True`` is reserved for an explicit
    maintainer regeneration. Both modes fail if any
    ``09_ai_templates/plot_*.py`` lacks a complete metadata block, so
    drift is caught immediately rather than silently shipping a stale
    or partial index.

    Tier-2 (advanced) templates live in
    ``09_ai_templates/advanced/plot_*.py`` and get registered under the
    ``"advanced"`` key in the JSON. Each entry carries an explicit
    ``"tier"`` field (``"basic"`` / ``"advanced"``) so MCP / docs
    consumers can filter without re-parsing source paths.
    """
    repo_root = Path(app.srcdir).parent
    template_dir = repo_root / "docs" / "examples_source" / "09_ai_templates"
    if not template_dir.exists():
        raise FileNotFoundError(
            f"AI template source directory is missing: {template_dir}"
        )

    def _scan_tier(
        scan_dir: Path, tier: str
    ) -> tuple[dict[str, dict[str, object]], list[str]]:
        """Scan one tier directory and return (index, missing-files)."""
        tier_index: dict[str, dict[str, object]] = {}
        tier_missing: list[str] = []
        for path in sorted(scan_dir.glob("plot_*.py")):
            text = path.read_text(encoding="utf-8")
            match = _TEMPLATE_META_RE.search(text)
            if not match:
                tier_missing.append(path.name)
                continue
            meta = _parse_template_meta(
                match.group(1), source=str(path.relative_to(repo_root))
            )
            stem = path.stem
            template_id = (
                stem if stem == "plot_3d" else stem.removeprefix("plot_")
            )
            meta["source_path"] = str(path.relative_to(repo_root))
            meta.setdefault("tier", tier)
            tier_index[template_id] = meta
        return tier_index, tier_missing

    index, missing = _scan_tier(template_dir, "basic")

    advanced_dir = (
        repo_root / "docs" / "examples_source" / "09_ai_templates_advanced"
    )
    if advanced_dir.exists():
        advanced_index, advanced_missing = _scan_tier(advanced_dir, "advanced")
        # Top-level "advanced" key holds the full tier-2 sub-index so
        # the JSON keeps a single round-trip with two clear sections.
        index["advanced"] = advanced_index  # type: ignore[assignment]
        missing.extend(advanced_missing)

    if missing:
        raise FileNotFoundError(
            "ai-template-meta block missing in: "
            f"{missing}. Add the fenced block immediately after the "
            "module docstring."
        )

    out = (
        repo_root
        / "src"
        / "dartwork_mpl"
        / "asset"
        / "prompt"
        / "05-templates"
        / "_index.json"
    )
    _check_or_write_authority(
        out,
        json.dumps(index, indent=2, sort_keys=True) + "\n",
        label=str(out.relative_to(repo_root)),
        write=write,
    )


def copy_fonts_to_static(app):
    """Copy bundled TTF fonts to _static/fonts/ for HTML specimens."""
    import shutil

    font_src = (
        Path(app.srcdir).parent / "src" / "dartwork_mpl" / "asset" / "font"
    )
    font_dst = Path(app.srcdir) / "_static" / "fonts"
    font_dst.mkdir(parents=True, exist_ok=True)

    for pattern in ("*.ttf", "*.otf"):
        for font_file in font_src.glob(pattern):
            dst_file = font_dst / font_file.name
            if (
                not dst_file.exists()
                or font_file.stat().st_mtime > dst_file.stat().st_mtime
            ):
                shutil.copy2(font_file, dst_file)


def write_manual_indices(app, env, docnames):
    """Write manual index files AFTER sphinx-gallery but BEFORE Sphinx reads."""
    gallery_dir = Path(app.srcdir) / "examples_gallery"

    content_parts = [_GALLERY_HEADER]
    toctree_entries = []

    for cat in _GALLERY_CATEGORIES:
        cat_index_path = gallery_dir / cat / "index.rst"
        if not cat_index_path.exists():
            print(f"Warning: Category index not found: {cat_index_path}")
            continue

        content = cat_index_path.read_text()

        # Remove :orphan: from category index files
        if ":orphan:" in content:
            clean_content = content.replace(":orphan:\n", "").replace(
                ":orphan:", ""
            )
            cat_index_path.write_text(clean_content)

        content = content.replace(":orphan:", "")

        # Cut off at toctree
        if ".. toctree::" in content:
            content = content.split(".. toctree::")[0]

        # Downgrade headers (=== -> ---)
        lines = content.splitlines()
        new_lines = []
        for line in lines:
            if (
                line.strip()
                and all(c == "=" for c in line.strip())
                and len(line.strip()) > 3
            ):
                new_lines.append("-" * len(line))
            else:
                new_lines.append(line)

        content_parts.append("\n".join(new_lines))
        toctree_entries.append(f"{cat}/index")

    # Hidden toctree for sidebar
    toctree_block = "\n.. toctree::\n   :hidden:\n\n"
    for entry in toctree_entries:
        toctree_block += f"   {entry}\n"
    content_parts.append(toctree_block)

    main_index = gallery_dir / "index.rst"
    main_index.write_text("\n".join(content_parts))
    print("Wrote concatenated manual index: examples_gallery/index.rst")

    if "examples_gallery/index" not in docnames:
        docnames.append("examples_gallery/index")
