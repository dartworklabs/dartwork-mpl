"""Actual FastMCP clients pin durable artifacts, errors and resource encodings."""

import asyncio
import base64
import hashlib
import io
import json
import random
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import matplotlib.image as mpimg
import pytest

fastmcp = pytest.importorskip("fastmcp")
from dartwork_mpl.mcp.artifacts import (  # noqa: E402
    ArtifactStore,
    ConfigurationError,
    configure_store,
    register_artifacts,
)

SOURCE = """# exact Unicode source: 한글
import sys
import matplotlib.pyplot as plt
import dartwork_mpl as dm
dm.style.use('scientific')
fig, ax = plt.subplots(figsize=dm.figsize('6cm', 'square'))
ax.plot([1,2], [3,4], linewidth=dm.lw(0))
dm.simple_layout(fig)
print('  stdout  ')
print('  stderr  ', file=sys.stderr)
"""


def server(root):
    """Create a real server with one bound persistent store."""
    instance = fastmcp.FastMCP("artifact-contract")
    store = configure_store(str(root))
    register_artifacts(instance, store)
    return instance


def metadata(result, error=None):
    """Check native wire framing and JSON/structured equivalence."""
    value = json.loads(result.content[-1].text)
    assert result.structured_content == value
    assert result.is_error == (value["delivery_status"] == "error")
    if error is not None:
        assert value["error_code"] == error
        assert [block.type for block in result.content] == ["text"]
        assert "artifact_id" not in value
    return value


def test_render_retrieve_and_read_all_resources(tmp_path):
    """Real PNG/PDF/source/report/manifest survive another client and restart."""

    async def workflow():
        """Traverse tool schemas, calls and all resource readers for real."""
        root = tmp_path / "artifacts"
        async with fastmcp.Client(server(root)) as client:
            tools = await client.list_tools()
            assert all(tool.outputSchema["oneOf"] for tool in tools)
            assert {
                tool.name: set(tool.inputSchema["properties"]) for tool in tools
            } == {
                "render_plot": {
                    "code",
                    "figure_var",
                    "timeout_seconds",
                    "chart_type_hint",
                },
                "get_plot_artifact": {"artifact_id"},
            }
            rendered = await client.call_tool("render_plot", {"code": SOURCE})
            value = metadata(rendered)
            assert [block.type for block in rendered.content] == [
                "image",
                *(["resource_link"] * 5),
                "text",
            ]
            png = base64.b64decode(rendered.content[0].data)
            assert mpimg.imread(io.BytesIO(png)).shape[0] > 0
        async with fastmcp.Client(server(root)) as client:
            retrieved = await client.call_tool(
                "get_plot_artifact", {"artifact_id": value["artifact_id"]}
            )
            assert metadata(retrieved) == value
            bodies = {}
            for entry in value["files"]:
                blocks = await client.read_resource(entry["uri"])
                assert len(blocks) == 1
                block = blocks[0]
                assert block.mimeType == entry["mime_type"]
                body = (
                    base64.b64decode(block.blob)
                    if hasattr(block, "blob")
                    else block.text.encode("utf-8")
                )
                bodies[entry["name"]] = body
                assert len(body) == entry["size_bytes"]
                if "sha256" in entry:
                    assert hashlib.sha256(body).hexdigest() == entry["sha256"]
            assert bodies["plot.png"] == png
            assert bodies["plot.pdf"].startswith(b"%PDF-")
            assert bodies["source.py"] == SOURCE.encode("utf-8")
            report = json.loads(bodies["report.json"])
            assert report["stdout"] == "  stdout  \n"
            assert report["stderr"].endswith("  stderr  \n")
            assert report["status"] == "ok"
            manifest = json.loads(bodies["manifest.json"])
            assert len(manifest["files"]) == 4
            assert "sha256" not in value["files"][-1]

    asyncio.run(workflow())


@pytest.mark.parametrize(
    ("arguments", "error"),
    [
        ({"code": "plt.tight_layout()"}, "lint_blocked"),
        ({"code": "fig = 1"}, "exec_error"),
        (
            {
                "code": SOURCE
                + """from dartwork_mpl.validate._checks import register_check
@register_check('ORIGINAL', order=9999)
def failed_check(fig, renderer):
    raise ValueError('check failed')
def failed_export(*args, **kwargs):
    raise OSError('private /staging/path')
dm.save_formats = failed_export
"""
            },
            "publication_error",
        ),
        ({"code": "print(123)"}, "no_figure"),
        ({"code": 'raise ValueError("boom")'}, "exec_error"),
        (
            {"code": "import time; time.sleep(60)", "timeout_seconds": 0.1},
            "timeout",
        ),
        ({"code": SOURCE, "timeout_seconds": 121}, "invalid_request"),
        ({"code": SOURCE, "figure_var": "../../bad"}, "invalid_request"),
    ],
)
def test_tool_error_and_resource_mimes_match_on_fastmcp2_and3(
    tmp_path, arguments, error
):
    """Errors retain native isError and structured metadata without ready links."""

    async def workflow():
        """Observe stable error framing over the supported protocol."""
        async with fastmcp.Client(server(tmp_path / "store")) as client:
            result = await client.call_tool(
                "render_plot", arguments, raise_on_error=False
            )
            value = metadata(result, error)
            if error != "invalid_request":
                assert value["report"]["validation_complete"] is False
            if error == "publication_error":
                assert value["report"]["failed_checks"] == ["ORIGINAL"]
                assert "/staging/path" not in str(value)
            assert str(tmp_path) not in value["message"]
            assert not list((tmp_path / "store").glob("*/manifest.json"))

    asyncio.run(workflow())


def test_invalid_configuration_missing_corrupt_expired_and_malformed(tmp_path):
    """Request references never mint authority; store failures remain explicit."""

    async def workflow():
        """Test real retrieval and resource errors through independent Clients."""
        bad = fastmcp.FastMCP("invalid-root")
        register_artifacts(bad, ConfigurationError("private /path"))
        async with fastmcp.Client(bad) as client:
            metadata(
                await client.call_tool(
                    "render_plot", {"code": SOURCE}, raise_on_error=False
                ),
                "configuration_error",
            )
        root = tmp_path / "store"
        async with fastmcp.Client(server(root)) as client:
            metadata(
                await client.call_tool(
                    "get_plot_artifact",
                    {"artifact_id": uuid4().hex},
                    raise_on_error=False,
                ),
                "not_found",
            )
            for identity in [
                "../outside",
                "%2e%2e",
                "A" * 32,
                "0" * 32,
                "abc",
                uuid4().hex + "/source.py",
            ]:
                metadata(
                    await client.call_tool(
                        "get_plot_artifact",
                        {"artifact_id": identity},
                        raise_on_error=False,
                    ),
                    "invalid_request",
                )
            rng = random.Random(8675309)
            for _ in range(24):
                identity = uuid4().hex[: rng.randrange(1, 32)] + rng.choice(
                    ["%2f", "..", "/", "?", "A"]
                )
                metadata(
                    await client.call_tool(
                        "get_plot_artifact",
                        {"artifact_id": identity},
                        raise_on_error=False,
                    ),
                    "invalid_request",
                )
            for identity in ["0" * 32, "A" * 32]:
                with pytest.raises(Exception, match="invalid_request"):
                    await client.read_resource(
                        f"dartwork-mpl://artifacts/{identity}/source.py"
                    )
            # The Client's URL parser normalizes encoded dot segments before
            # route matching; the request is denied without reaching our reader.
            with pytest.raises(Exception, match="Unknown resource"):
                await client.read_resource(
                    "dartwork-mpl://artifacts/%2e%2e/source.py"
                )
            value = metadata(
                await client.call_tool("render_plot", {"code": SOURCE})
            )
            artifact = root / value["artifact_id"]
            (artifact / "source.py").write_text("tampered")
            metadata(
                await client.call_tool(
                    "get_plot_artifact",
                    {"artifact_id": value["artifact_id"]},
                    raise_on_error=False,
                ),
                "corrupt",
            )
            with pytest.raises(Exception, match="corrupt"):
                await client.read_resource(value["files"][0]["uri"])

    asyncio.run(workflow())


def test_incomplete_ready_repeats_concurrent_and_publication_clock(tmp_path):
    """Incomplete warnings remain ready, fresh IDs never overwrite and clock is late."""
    from dartwork_mpl.mcp.artifacts import (
        RenderRequest,
        StoredBundle,
        render_artifact,
    )

    code = (
        SOURCE
        + """from dartwork_mpl.validate._checks import register_check
@register_check('ORIGINAL', order=9999)
def failure(fig, renderer):
    raise ValueError('bbox')
"""
    )

    async def workflow():
        """Run independent requests concurrently against one store."""
        async with fastmcp.Client(server(tmp_path / "store")) as client:
            results = await asyncio.gather(
                *(
                    client.call_tool("render_plot", {"code": code})
                    for _ in range(3)
                )
            )
            values = [metadata(result) for result in results]
            assert len({value["artifact_id"] for value in values}) == 3
            assert all(
                value["validation"]
                == {
                    "status": "validation_incomplete",
                    "validation_complete": False,
                    "failed_checks": ["ORIGINAL"],
                }
                for value in values
            )

    asyncio.run(workflow())
    store = configure_store(str(tmp_path / "clock"))
    assert isinstance(store, ArtifactStore)
    marker = tmp_path / "finished"
    now = datetime.now(timezone.utc)

    def clock():
        """The clock can observe child completion before assigning publication time."""
        assert marker.exists()
        return now

    outcome = render_artifact(
        store,
        RenderRequest(
            SOURCE
            + f"from pathlib import Path\nPath({str(marker)!r}).touch()\n"
        ),
        clock,
    )
    assert isinstance(outcome, StoredBundle)
    assert outcome.manifest.created_at == now
    assert outcome.manifest.expires_at == now + timedelta(days=7)


@pytest.mark.parametrize(
    "failure", ["expired", "oversize", "report", "publication"]
)
def test_stored_failures_and_publication_errors_are_safe(
    tmp_path, monkeypatch, failure
):
    """Expiry, size limits and real failing writes never return ready artifacts."""
    import dartwork_mpl.mcp.artifacts.transport as transport
    from dartwork_mpl.mcp.artifacts import PublicationError

    root = tmp_path / "store"

    async def workflow():
        """Exercise failures over native Clients after real export/publication."""
        async with fastmcp.Client(server(root)) as client:
            if failure == "publication":

                def failed_publish(self, stage, source, report, now):
                    """Inject the owned publication adapter's safe typed refusal."""
                    return PublicationError("private /staging/path")

                monkeypatch.setattr(ArtifactStore, "publish", failed_publish)
                result = await client.call_tool(
                    "render_plot", {"code": SOURCE}, raise_on_error=False
                )
                value = metadata(result, "publication_error")
                assert "/staging/path" not in value["message"]
                assert not list(root.glob("*/manifest.json"))
                return
            if failure == "report":
                result = await client.call_tool(
                    "render_plot",
                    {"code": SOURCE + "print('x' * (33 * 1024 * 1024))\n"},
                    raise_on_error=False,
                )
                metadata(result, "artifact_too_large")
                assert not list(root.glob("*/manifest.json"))
                return
            value = metadata(
                await client.call_tool("render_plot", {"code": SOURCE})
            )
            if failure == "expired":
                future = datetime.now(timezone.utc) + timedelta(days=8)

                class FutureDateTime:
                    """Inject only our adapter clock; the real store decides expiry."""

                    @staticmethod
                    def now(tz):
                        """Supply a controlled UTC expiry time without sleeping."""
                        return future

                monkeypatch.setattr(transport, "datetime", FutureDateTime)
                expected = "expired"
            else:
                with (root / value["artifact_id"] / "plot.png").open(
                    "ab"
                ) as output:
                    output.truncate(33 * 1024 * 1024)
                expected = "artifact_too_large"
            metadata(
                await client.call_tool(
                    "get_plot_artifact",
                    {"artifact_id": value["artifact_id"]},
                    raise_on_error=False,
                ),
                expected,
            )

    asyncio.run(workflow())
