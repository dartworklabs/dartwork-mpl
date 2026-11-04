"""Template render and compose outcomes and the reply fields each one serialises to."""

import base64

from dartwork_mpl.mcp.templates.compose import (
    Composed,
    InvalidTier,
    NoTemplate,
    _select,
    compose,
)
from dartwork_mpl.mcp.templates.render import (
    PublicationFailed,
    Published,
    Rendered,
    RenderFailed,
    RenderTimedOut,
    _reply_fields,
)


def test_each_render_outcome_has_its_reply_fields():
    """Every variant maps to the legacy status, PNG and stderr fields."""
    png = b"\x89PNG"
    assert _reply_fields(Rendered(png, "warn")) == (
        "ok",
        base64.b64encode(png).decode("ascii"),
        None,
        "warn",
    )
    assert _reply_fields(Published("/tmp/x.png", "")) == (
        "ok",
        None,
        "/tmp/x.png",
        "",
    )
    assert _reply_fields(RenderTimedOut(0.5)) == (
        "timeout",
        None,
        None,
        "Render exceeded 0.5s timeout.",
    )
    assert _reply_fields(RenderFailed("Traceback")) == (
        "render_error",
        None,
        None,
        "Traceback",
    )
    assert _reply_fields(PublicationFailed()) == (
        "render_error",
        None,
        None,
        "Template output publication failed.",
    )


def test_compose_selects_one_outcome_per_request():
    """An unknown tier, a missing template and a found one are distinct outcomes."""
    assert _select("bar", "x") == InvalidTier("x")
    assert _select("nope", "advanced") == NoTemplate("basic")
    found = _select("bar", "basic")
    assert isinstance(found, Composed) and found.tier == "basic"


def test_compose_reply_marks_requested_layers():
    """Missing lists only requested layers that the template does not apply."""
    reply = compose("bar", ["callout", "zzz"], "advanced")
    assert reply["status"] == "ok"
    assert "zzz" in reply["missing"]
    assert set(reply["missing"]).isdisjoint(reply["applied"])
    assert compose("bar", None, "x")["missing"] == []
