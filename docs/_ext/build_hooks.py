"""Custom Sphinx build hooks for dartwork-mpl documentation.

Extracted from conf.py for maintainability. Handles:
- Gallery index generation (manual indices after sphinx-gallery)
- Color system asset generation
- Font file copying for HTML specimens
- AI plot-template metadata index (T6 in the AI-readiness roadmap)
"""

import contextlib
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


def resolve_provenance_links(app, doctree):
    """Keep accepted ADR provenance links navigable without publishing inputs.

    MyST resolves document links before Sphinx's missing-reference event, so
    convert only these accepted targets before reference resolution. Each
    source must exist; missing and unrelated links retain their warnings.
    """
    from docutils import nodes
    from sphinx import addnodes

    targets = {
        "superpowers/specs/2026-10-18-mcp-artifact-delivery-design",
        "superpowers/plans/2026-10-29-finite-margins",
        "superpowers/plans/2026-10-29-template-format-preflight",
        "superpowers/specs/2026-10-29-input-preflight-design",
        "superpowers/plans/2026-11-05-python311-security-upgrade",
    }
    for node in doctree.findall(addnodes.pending_xref):
        target = node.get("reftarget")
        if (
            node.get("refdomain") != "doc"
            or node.get("reftype") != "myst"
            or target not in targets
            or not (Path(app.srcdir) / f"{target}.md").is_file()
        ):
            continue
        url = (
            "https://github.com/dartworklabs/dartwork-mpl/blob/main/docs/"
            f"{target}.md"
        )
        fragment = node.get("reftargetid")
        refuri = f"{url}#{fragment}" if fragment else url
        node.replace_self(
            nodes.reference("", "", node[0].deepcopy(), refuri=refuri)
        )


def setup(app):
    """Register link resolution with Sphinx's extension cache invalidation."""
    app.connect("doctree-read", resolve_provenance_links)
    return {"env_version": 3, "parallel_read_safe": True}


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


def copy_fonts_to_static(app):
    """Copy bundled TTF fonts to _static/fonts/ for HTML specimens."""
    import shutil

    font_src = (
        Path(app.srcdir).parent / "src" / "dartwork_mpl" / "font" / "assets"
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
