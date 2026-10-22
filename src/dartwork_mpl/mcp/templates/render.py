"""Rendering a bundled template to PNG for ``render_template`` / ``render_template_advanced``.

Both tools run a template the same way (``_execute``); they differ only in
tier selection and reply shape, so each keeps its own reply builder.
"""

import base64
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any

from .. import _platform
from . import bundled


def _execute(
    path: Path, timeout_seconds: float
) -> tuple[_platform.CapturedProcess, bytes | None]:
    """Run the template file at ``path`` in a fresh Agg child inside a temporary directory.

    Returns the finished child and the bytes of the first PNG it wrote
    there, or None when the child timed out, failed, or wrote no PNG. The
    directory is removed before returning.
    """
    with tempfile.TemporaryDirectory() as tmp:
        out_base = Path(tmp) / "out"
        # The template ends with ``dm.save_formats(fig, "<name>")``
        # which writes to ``<cwd>/<name>.png``. We just need to
        # run it in our tmp dir and read whatever PNG appears.
        runner = textwrap.dedent(
            """\
            import os, sys
            os.chdir({tmp!r})
            import matplotlib
            matplotlib.use("Agg")
            sys.path.insert(0, {tmpdir!r})
            exec(compile(open({path!r}).read(), {path!r}, "exec"),
                 {{"__name__": "__render__"}})
            """
        ).format(
            tmp=str(out_base.parent),
            tmpdir=str(out_base.parent),
            path=str(path),
        )

        proc = _platform.run_child(
            [sys.executable, "-c", runner], timeout_seconds=timeout_seconds
        )
        if proc.timed_out:
            return proc, None

        pngs = sorted(out_base.parent.glob("*.png"))
        if proc.returncode != 0 or not pngs:
            return proc, None

        return proc, pngs[0].read_bytes()


def render_basic(
    plot_type: str, return_format: str, timeout_seconds: float
) -> dict[str, Any]:
    """The ``render_template`` reply for a basic-tier template.

    ``status`` is ``ok``, ``unknown_template``, ``render_error`` (child
    failed, wrote no PNG, or the ``path`` publication failed) or
    ``timeout``. ``return_format="path"`` publishes the PNG to a new
    private temp file the caller owns; otherwise it is base64-encoded.
    """
    template_dir = bundled._TEMPLATE_DIR
    path = bundled._resolve_template_path(plot_type)
    if path is None:
        available = sorted(p.stem for p in template_dir.glob("*.py"))
        return {
            "status": "unknown_template",
            "plot_type": plot_type,
            "png_base64": None,
            "png_path": None,
            "stderr": (
                f"No template named {plot_type!r}. Available: {available}"
            ),
        }

    proc, png_bytes = _execute(path, timeout_seconds)
    if proc.timed_out:
        return {
            "status": "timeout",
            "plot_type": plot_type,
            "png_base64": None,
            "png_path": None,
            "stderr": f"Render exceeded {timeout_seconds}s timeout.",
        }

    if png_bytes is None:
        return {
            "status": "render_error",
            "plot_type": plot_type,
            "png_base64": None,
            "png_path": None,
            "stderr": _platform.diagnostic(
                proc.stderr or proc.stdout,
                "stderr" if proc.stderr else "stdout",
                char_limit=2000,
                marked=(
                    proc.stderr_truncated
                    if proc.stderr
                    else proc.stdout_truncated
                ),
            ),
        }

    if return_format == "path":
        try:
            persistent = _platform.publish_png(
                png_bytes, f"dartwork-mpl-render-{plot_type}-"
            )
        except OSError:
            return {
                "status": "render_error",
                "plot_type": plot_type,
                "png_base64": None,
                "png_path": None,
                "stderr": "Template output publication failed.",
            }
        return {
            "status": "ok",
            "plot_type": plot_type,
            "png_base64": None,
            "png_path": str(persistent),
            "stderr": _platform.strip_diagnostic(
                proc.stderr, "stderr", marked=proc.stderr_truncated
            ),
        }
    return {
        "status": "ok",
        "plot_type": plot_type,
        "png_base64": base64.b64encode(png_bytes).decode("ascii"),
        "png_path": None,
        "stderr": _platform.strip_diagnostic(
            proc.stderr, "stderr", marked=proc.stderr_truncated
        ),
    }


def render_advanced(
    plot_type: str, return_format: str, timeout_seconds: float
) -> dict[str, Any]:
    """The ``render_template_advanced`` reply: the advanced tier, else the basic one.

    Same statuses as ``render_basic`` plus ``fell_back`` (rendered from the
    basic tier); every reply carries ``tier`` (``none`` when unknown).
    """
    template_dir = bundled._TEMPLATE_DIR
    advanced_path = bundled._resolve_template_path(plot_type, advanced=True)
    basic_path = bundled._resolve_template_path(plot_type)

    if advanced_path is not None:
        path = advanced_path
        tier = "advanced"
        fell_back = False
    elif basic_path is not None:
        path = basic_path
        tier = "basic"
        fell_back = True
    else:
        available = sorted(p.stem for p in template_dir.glob("*.py"))
        return {
            "status": "unknown_template",
            "plot_type": plot_type,
            "tier": "none",
            "png_base64": None,
            "png_path": None,
            "stderr": (
                f"No template named {plot_type!r}. "
                f"Available basic: {available}. "
                f"Available advanced: "
                f"{sorted(p.stem for p in (template_dir / 'advanced').glob('*.py'))}."
            ),
        }

    proc, png_bytes = _execute(path, timeout_seconds)
    if proc.timed_out:
        return {
            "status": "timeout",
            "plot_type": plot_type,
            "tier": tier,
            "png_base64": None,
            "png_path": None,
            "stderr": f"Render exceeded {timeout_seconds}s timeout.",
        }

    if png_bytes is None:
        return {
            "status": "render_error",
            "plot_type": plot_type,
            "tier": tier,
            "png_base64": None,
            "png_path": None,
            "stderr": _platform.diagnostic(
                proc.stderr or proc.stdout,
                "stderr" if proc.stderr else "stdout",
                char_limit=2000,
                marked=(
                    proc.stderr_truncated
                    if proc.stderr
                    else proc.stdout_truncated
                ),
            ),
        }

    status = "fell_back" if fell_back else "ok"
    if return_format == "path":
        try:
            persistent = _platform.publish_png(
                png_bytes, f"dartwork-mpl-render-advanced-{plot_type}-"
            )
        except OSError:
            return {
                "status": "render_error",
                "plot_type": plot_type,
                "tier": tier,
                "png_base64": None,
                "png_path": None,
                "stderr": "Template output publication failed.",
            }
        return {
            "status": status,
            "plot_type": plot_type,
            "tier": tier,
            "png_base64": None,
            "png_path": str(persistent),
            "stderr": _platform.strip_diagnostic(
                proc.stderr, "stderr", marked=proc.stderr_truncated
            ),
        }
    return {
        "status": status,
        "plot_type": plot_type,
        "tier": tier,
        "png_base64": base64.b64encode(png_bytes).decode("ascii"),
        "png_path": None,
        "stderr": _platform.strip_diagnostic(
            proc.stderr, "stderr", marked=proc.stderr_truncated
        ),
    }
