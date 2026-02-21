"""Dartwork interactive figure viewer — FastAPI server.

Usage
-----
::

    from dartwork_mpl.ui import ParamModel, run
    from pydantic import Field

    class Params(ParamModel):
        n: int = Field(default=100, ge=10, le=1000)
        alpha: float = Field(default=0.5, ge=0.0, le=1.0)

    def my_plot(params: Params) -> Figure:
        ...
        return fig

    run(my_plot, Params)  # explicit
    run(my_plot)           # auto-extracted from type annotation
"""

import base64
import inspect
import io
import os
import sys
import textwrap
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, Response
from matplotlib.figure import Figure
from pydantic import BaseModel

from ..util import save_formats
from ._config import (
    delete_preset,
    load_config,
    load_presets,
    save_config,
    save_preset,
    set_base_dir,
)
from ._param import ParamModel
from ._template import get_html
from ._widget import descriptors_from_model

# Use non-interactive backend for server usage
matplotlib.use("Agg")


# ============================================================================
# Request / response models
# ============================================================================


class PresetSaveRequest(BaseModel):
    """Request body for saving a preset."""

    label: str
    params: dict[str, Any]


class ServerSaveRequest(BaseModel):
    """Request body for server-side save with optional name."""

    params: dict[str, Any]
    filename: str | None = None


# ============================================================================
# Public API
# ============================================================================


def run(
    figure_fn: Callable[[ParamModel], Figure],
    param_model: type[ParamModel] | None = None,
    *,
    title: str = "Dartwork Viewer",
    host: str = "127.0.0.1",
    port: int = 8501,
) -> None:
    """Launch the FastAPI interactive figure viewer.

    Parameters
    ----------
    figure_fn : callable
        A function that accepts a single ``ParamModel`` instance and
        returns a ``matplotlib.figure.Figure``.
    param_model : type[ParamModel], optional
        The Pydantic model class defining the parameters.
        If omitted, it is automatically extracted from the
        function's type annotation.
    title : str
        Page / app title.
    host : str
        Server host. Defaults to ``"127.0.0.1"``.
    port : int
        Server port. Defaults to ``8501``.

    Raises
    ------
    TypeError
        If the function signature does not match
        ``(params: ParamModel) -> Figure``.
    """
    # ── Extract / validate param model ────────────────────────────
    if param_model is None:
        param_model = _extract_param_model(figure_fn)

    # Set base dir to script location for config persistence
    script_path = Path(sys.argv[0]).resolve().parent
    set_base_dir(script_path)

    # Resolve parameter descriptors from the model
    descriptors = descriptors_from_model(param_model)
    descriptor_dicts = [d.to_dict() for d in descriptors]

    # ── FastAPI app ──────────────────────────────────────────────────
    app = FastAPI(title=title)

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return get_html(title=title)

    @app.get("/api/descriptors")
    async def get_descriptors() -> list[dict[str, Any]]:
        return descriptor_dicts

    @app.post("/api/render")
    async def render(params: dict[str, Any]) -> dict[str, str]:
        try:
            model = _build_model(params, param_model, descriptors)
        except Exception as exc:
            error_msg = _format_validation_error(exc)
            return JSONResponse(
                status_code=422,
                content={"detail": error_msg},
            )
        fig = figure_fn(model)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")

        return {"image": b64}

    @app.post("/api/save-state")
    async def save_state(
        body: dict[str, Any],
    ) -> dict[str, str]:
        """Save full UI state (tabs) to config."""
        tabs = body.get("tabs", [])
        params = body.get("params", {})
        save_config(
            params,
            function_name=figure_fn.__name__,
            tabs=tabs,
        )
        return {"status": "ok"}

    @app.post("/api/export/{fmt}")
    async def export(fmt: str, params: dict[str, Any]) -> Response:
        model = _build_model(params, param_model, descriptors)
        fig = figure_fn(model)
        buf = io.BytesIO()
        fig.savefig(buf, format=fmt, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)

        mime_map = {
            "png": "image/png",
            "svg": "image/svg+xml",
            "pdf": "application/pdf",
        }
        return Response(
            content=buf.getvalue(),
            media_type=mime_map.get(fmt, "application/octet-stream"),
            headers={
                "Content-Disposition": f'attachment; filename="figure.{fmt}"'
            },
        )

    @app.get("/api/config")
    async def get_config() -> dict[str, Any]:
        """Return saved config (params + tabs)."""
        return load_config() or {}

    @app.get("/api/meta")
    async def get_meta() -> dict[str, str]:
        """Return metadata for frontend defaults."""
        return {
            "function_name": figure_fn.__name__,
        }

    @app.post("/api/config")
    async def post_config(params: dict[str, Any]) -> dict[str, str]:
        save_config(params, function_name=figure_fn.__name__)
        return {"status": "ok"}

    @app.post("/api/preset")
    async def save_preset_endpoint(
        req: PresetSaveRequest,
    ) -> dict[str, str]:
        save_preset(req.label, req.params)
        return {"status": "ok"}

    @app.get("/api/presets")
    async def get_presets() -> list[dict[str, Any]]:
        return load_presets()

    @app.delete("/api/preset/{index}")
    async def delete_preset_endpoint(
        index: int,
    ) -> dict[str, str]:
        """Delete a preset by index."""
        ok = delete_preset(index)
        if not ok:
            return JSONResponse(
                status_code=404,
                content={"detail": "Preset not found"},
            )
        return {"status": "ok"}

    @app.get("/api/defaults")
    async def get_defaults() -> dict[str, Any]:
        """Return default parameter values for reset."""
        return {
            d.name: d.default for d in descriptors
        }

    # ── Script generation ────────────────────────────────────────────

    @app.post("/api/script")
    async def generate_script(params: dict[str, Any]) -> Response:
        """Generate a standalone Python script and return as download."""
        model = _build_model(params, param_model, descriptors)
        code = _generate_script(model, param_model, figure_fn, script_path)
        return Response(
            content=code.encode("utf-8"),
            media_type="text/x-python",
            headers={
                "Content-Disposition": 'attachment; filename="generate_figure.py"'
            },
        )

    # ── Server-side save ─────────────────────────────────────────────

    @app.post("/api/save-server/image/{fmt}")
    async def save_image_server(
        fmt: str, req: ServerSaveRequest,
    ) -> dict[str, str]:
        """Save figure image to the script directory."""
        model = _build_model(
            req.params, param_model, descriptors,
        )
        fig = figure_fn(model)

        if req.filename:
            stem = req.filename
        else:
            ts = _timestamp_slug()
            stem = f"{figure_fn.__name__}_{ts}"
        image_stem = str(script_path / stem)

        save_formats(
            fig, image_stem, formats=(fmt,),
            bbox_inches="tight",
        )
        plt.close(fig)

        filename = f"{stem}.{fmt}"
        return {
            "status": "ok",
            "path": image_stem + f".{fmt}",
            "filename": filename,
        }

    @app.post("/api/save-server/script")
    async def save_script_server(
        req: ServerSaveRequest,
    ) -> dict[str, str]:
        """Save standalone Python script to the script dir."""
        model = _build_model(
            req.params, param_model, descriptors,
        )
        code = _generate_script(
            model, param_model, figure_fn, script_path,
        )

        if req.filename:
            filename = (
                req.filename
                if req.filename.endswith(".py")
                else f"{req.filename}.py"
            )
        else:
            ts = _timestamp_slug()
            filename = f"{figure_fn.__name__}_{ts}.py"
        out_path = script_path / filename
        out_path.write_text(code, encoding="utf-8")

        return {
            "status": "ok",
            "path": str(out_path),
            "filename": filename,
        }

    # ── Reload ───────────────────────────────────────────────────────

    @app.post("/api/reload")
    async def reload_server() -> dict[str, str]:
        """Restart the server process to pick up code changes."""
        import threading

        def _restart() -> None:
            import time

            time.sleep(0.3)  # Let the response return first
            os.execv(sys.executable, [sys.executable] + sys.argv)

        threading.Thread(target=_restart, daemon=True).start()
        return {"status": "reloading"}

    # ── Health check (heartbeat for frontend) ────────────────────────

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        """Return server health status for frontend heartbeat."""
        return {"status": "ok"}

    # ── Launch (retry ports if in use) ──────────────────────────────
    current_port = port
    while True:
        try:
            print("\n  Dartwork Viewer running at:")
            print(f"  \033[1;36mhttp://{host}:{current_port}\033[0m\n")
            uvicorn.run(app, host=host, port=current_port, log_level="warning")
            break
        except SystemExit:
            current_port += 1
            print(f"  Port {current_port - 1} in use, trying {current_port}...")


# ============================================================================
# Helpers
# ============================================================================


def _format_validation_error(exc: Exception) -> str:
    """Format a Pydantic ValidationError into a readable string.

    Parameters
    ----------
    exc : Exception
        The exception to format. If it is a Pydantic
        ``ValidationError``, field-level details are
        extracted.

    Returns
    ----------
    str
        Human-readable error message.
    """
    try:
        from pydantic import ValidationError

        if isinstance(exc, ValidationError):
            parts: list[str] = []
            for err in exc.errors():
                loc = " → ".join(str(x) for x in err["loc"])
                parts.append(f"{loc}: {err['msg']}")
            return "; ".join(parts)
    except ImportError:
        pass
    return str(exc)


def _build_model(
    raw_params: dict[str, Any], model_cls: type[ParamModel], descriptors: list
) -> ParamModel:
    """Coerce raw params from the frontend and build a model instance.

    Handles type coercion for scalars and parsing of comma-separated
    strings for list/tuple fields.
    """
    coerced: dict[str, Any] = {}

    type_map = {d.name: d.type_name for d in descriptors}

    for k, v in raw_params.items():
        tname = type_map.get(k, "str")

        try:
            if tname == "int":
                coerced[k] = int(v)
            elif tname == "float":
                coerced[k] = float(v)
            elif tname == "bool":
                coerced[k] = bool(v) if isinstance(v, bool) else v
            elif tname == "list_int":
                coerced[k] = _parse_list(v, int)
            elif tname == "list_float":
                coerced[k] = _parse_list(v, float)
            elif tname == "list_str":
                coerced[k] = _parse_list(v, str)
            else:
                coerced[k] = v
        except (ValueError, TypeError):
            coerced[k] = v

    return model_cls(**coerced)


def _extract_param_model(fn: Callable) -> type[ParamModel]:
    """Extract the ParamModel subclass from a figure function's signature.

    Validates that ``fn`` has exactly one parameter whose annotation
    is a ``ParamModel`` subclass.

    Raises
    ------
    TypeError
        If the signature does not match expectations.
    """
    import typing

    try:
        hints = typing.get_type_hints(fn)
    except Exception:
        hints = dict(fn.__annotations__)

    ret = hints.pop("return", None)

    if len(hints) == 0:
        raise TypeError(
            f"{fn.__name__}() has no type annotations. "
            "Expected signature: (params: YourParamModel) -> Figure"
        )

    if len(hints) > 1:
        raise TypeError(
            f"{fn.__name__}() has {len(hints)} annotated parameters, "
            "expected exactly 1. "
            "Expected signature: (params: YourParamModel) -> Figure"
        )

    param_name, param_type = next(iter(hints.items()))

    if not (
        isinstance(param_type, type) and issubclass(param_type, ParamModel)
    ):
        raise TypeError(
            f"{fn.__name__}({param_name}: {param_type!r}) — "
            f"annotation must be a ParamModel subclass"
        )

    # Optional: warn if return type is not Figure
    if ret is not None and ret is not Figure:
        import warnings

        warnings.warn(
            f"{fn.__name__}() return type is annotated as {ret!r}, "
            f"expected Figure.",
            stacklevel=3,
        )

    return param_type


def _parse_list(value: Any, item_type: type) -> list:
    """Parse a comma-separated string or existing list into typed list."""
    if isinstance(value, list):
        return [item_type(x) for x in value]
    if isinstance(value, str):
        raw = [s.strip() for s in value.split(",") if s.strip()]
        return [item_type(x) for x in raw]
    return [item_type(value)]


def _timestamp_slug() -> str:
    """Return a compact timestamp string for filenames."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _generate_script(
    model: ParamModel,
    model_cls: type[ParamModel],
    figure_fn: Callable,
    script_dir: Path,
) -> str:
    """Generate a standalone Python script that reproduces the figure.

    The script includes the figure function source, the ParamModel class
    source, and the current parameter values.
    """
    # Get source of the figure function and model class
    try:
        fn_source = textwrap.dedent(inspect.getsource(figure_fn))
    except (OSError, TypeError):
        fn_source = f"# Could not retrieve source for {figure_fn.__name__}"

    try:
        model_source = textwrap.dedent(inspect.getsource(model_cls))
    except (OSError, TypeError):
        model_source = f"# Could not retrieve source for {model_cls.__name__}"

    # Get the module where figure_fn is defined for imports
    fn_module = inspect.getmodule(figure_fn)
    try:
        module_source = inspect.getsource(fn_module)
        # Extract import lines from the top of the module
        import_lines = []
        for line in module_source.split("\n"):
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                # Skip the 'run' function import (not needed in standalone)
                if "import run" in stripped or "import run," in stripped:
                    # Keep ParamModel but drop run
                    cleaned = stripped.replace(", run", "").replace("run, ", "")
                    if "import" in cleaned and cleaned != stripped:
                        import_lines.append(cleaned)
                else:
                    import_lines.append(line)
            elif (
                stripped
                and not stripped.startswith(("#", '"""', "'''", '"'))
                and import_lines
            ):
                # Stop after the import block ends
                if not stripped.startswith(("import ", "from ")):
                    break
        imports_block = "\n".join(import_lines)
    except (OSError, TypeError):
        imports_block = (
            "import matplotlib.pyplot as plt\n"
            "from matplotlib.figure import Figure\n"
            "from dartwork_mpl.ui import ParamModel"
        )

    # Serialize current params
    params_dict = model.model_dump()
    params_lines = []
    for key, val in params_dict.items():
        params_lines.append(f"    {key}={val!r},")
    params_str = "\n".join(params_lines)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    script = f'''"""Auto-generated figure script.

Generated at: {ts}
Parameters: {model_cls.__name__}
Function:   {figure_fn.__name__}
"""

{imports_block}
from pydantic import Field

from dartwork_mpl.util import save_formats


{model_source}


{fn_source}


if __name__ == "__main__":
    params = {model_cls.__name__}(
{params_str}
    )
    fig = {figure_fn.__name__}(params)
    save_formats(fig, "{figure_fn.__name__}", bbox_inches="tight")
    print("Saved: {figure_fn.__name__}.[svg|png|pdf|eps]")
    plt.show()
'''
    return script
