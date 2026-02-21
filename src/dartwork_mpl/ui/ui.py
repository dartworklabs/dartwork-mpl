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

    run(my_plot, Params)
"""

from __future__ import annotations

import base64
import io
import sys
from pathlib import Path
from typing import Any, Callable

import matplotlib
import matplotlib.pyplot as plt
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response
from matplotlib.figure import Figure
from pydantic import BaseModel

from ._config import (
    append_history,
    load_config,
    load_presets,
    save_config,
    set_base_dir,
)
from ._param import ParamModel
from ._template import get_html
from ._widget import (
    descriptors_from_model,
)

# Use non-interactive backend for server usage
matplotlib.use("Agg")


# ============================================================================
# Request / response models
# ============================================================================


class PresetSaveRequest(BaseModel):
    label: str
    params: dict[str, Any]


# ============================================================================
# Public API
# ============================================================================


def run(
    figure_fn: Callable[[ParamModel], Figure],
    param_model: type[ParamModel],
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
    param_model : type[ParamModel]
        The Pydantic model class defining the parameters.
    title : str
        Page / app title.
    host : str
        Server host. Defaults to ``"127.0.0.1"``.
    port : int
        Server port. Defaults to ``8501``.
    """
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
        model = _build_model(params, param_model, descriptors)
        fig = figure_fn(model)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
        plt.close(fig)
        buf.seek(0)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")

        # Auto-save config
        save_config(
            model.model_dump(), function_name=figure_fn.__name__
        )
        append_history(model.model_dump())

        return {"image": b64}

    @app.post("/api/export/{fmt}")
    async def export(fmt: str, params: dict[str, Any]) -> Response:
        model = _build_model(params, param_model, descriptors)
        fig = figure_fn(model)
        buf = io.BytesIO()
        fig.savefig(buf, format=fmt, bbox_inches="tight", dpi=150)
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
        cfg = load_config()
        if cfg is None:
            return {"params": None}
        return {"params": cfg}

    @app.post("/api/config")
    async def post_config(params: dict[str, Any]) -> dict[str, str]:
        save_config(params, function_name=figure_fn.__name__)
        return {"status": "ok"}

    @app.post("/api/preset")
    async def save_preset(req: PresetSaveRequest) -> dict[str, str]:
        append_history(req.params, label=req.label)
        return {"status": "ok"}

    @app.get("/api/presets")
    async def get_presets() -> list[dict[str, Any]]:
        return load_presets()

    # ── Launch (retry ports if in use) ──────────────────────────────
    current_port = port
    while True:
        try:
            print(f"\n  Dartwork Viewer running at:")
            print(f"  \033[1;36mhttp://{host}:{current_port}\033[0m\n")
            uvicorn.run(
                app, host=host, port=current_port, log_level="warning"
            )
            break
        except SystemExit:
            current_port += 1
            print(
                f"  Port {current_port - 1} in use, "
                f"trying {current_port}..."
            )


# ============================================================================
# Helpers
# ============================================================================


def _build_model(
    raw_params: dict[str, Any],
    model_cls: type[ParamModel],
    descriptors: list,
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


def _parse_list(value: Any, item_type: type) -> list:
    """Parse a comma-separated string or existing list into typed list."""
    if isinstance(value, list):
        return [item_type(x) for x in value]
    if isinstance(value, str):
        raw = [s.strip() for s in value.split(",") if s.strip()]
        return [item_type(x) for x in raw]
    return [item_type(value)]
