"""Native MCP tools/resources with explicit v1 schemas and version adapters."""

import base64
import json
from datetime import datetime, timezone
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ResourceError
from fastmcp.tools.tool import ToolResult
from mcp.types import CallToolResult, ImageContent, ResourceLink, TextContent
from pydantic import AnyUrl

from ..execution import ExecutionRejected, ExportRejected, LogLimitRejected
from .delivery import (
    ArtifactFailure,
    delete_inputs,
    get_artifact,
    render_artifact,
)
from .input_access import InputsDisabled
from .input_policy import parse_revision
from .inputs import AbsentInputs, DeletedInputs
from .lifecycle import ArtifactRuntime, run_owned
from .policy import (
    ArtifactMember,
    ArtifactTooLarge,
    ConfigurationError,
    CorruptArtifact,
    Expired,
    InvalidRequest,
    NotFound,
    PublicationError,
    StoredBundle,
    parse_artifact_id,
    parse_render_request,
)
from .store import ArtifactStore

# Public resource wrappers were introduced in FastMCP 3. FastMCP 2 uses the
# decorator's MIME and converts raw bytes/text itself; there the names stay
# unbound and only _RESOURCE_WRAPPERS is read.
try:
    from fastmcp.resources import ResourceContent, ResourceResult
except ImportError:
    _RESOURCE_WRAPPERS = False
else:
    _RESOURCE_WRAPPERS = True

_SCHEMA: dict[str, Any] = {
    "type": "object",
    "oneOf": [
        {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "schema_version",
                "delivery_status",
                "artifact_id",
                "created_at",
                "expires_at",
                "files",
                "validation",
            ],
            "properties": {
                "schema_version": {"const": 1},
                "delivery_status": {"const": "ready"},
                "artifact_id": {
                    "type": "string",
                    "pattern": "^[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}$",
                },
                "created_at": {
                    "type": "string",
                    "format": "date-time",
                    "pattern": "Z$",
                },
                "expires_at": {
                    "type": "string",
                    "format": "date-time",
                    "pattern": "Z$",
                },
                "files": {
                    "type": "array",
                    "minItems": 5,
                    "maxItems": 5,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["name", "uri", "mime_type", "size_bytes"],
                        "if": {
                            "properties": {"name": {"const": "manifest.json"}}
                        },
                        "then": {"not": {"required": ["sha256"]}},
                        "else": {"required": ["sha256"]},
                        "properties": {
                            "name": {
                                "enum": [
                                    member.value for member in ArtifactMember
                                ]
                            },
                            "uri": {"type": "string"},
                            "mime_type": {"type": "string"},
                            "size_bytes": {"type": "integer", "minimum": 0},
                            "sha256": {
                                "type": "string",
                                "pattern": "^[0-9a-f]{64}$",
                            },
                        },
                    },
                },
                "validation": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "status",
                        "validation_complete",
                        "failed_checks",
                    ],
                    "properties": {
                        "status": {"enum": ["ok", "validation_incomplete"]},
                        "validation_complete": {"type": "boolean"},
                        "failed_checks": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            },
        },
        {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "schema_version",
                "delivery_status",
                "error_code",
                "message",
            ],
            "properties": {
                "schema_version": {"const": 1},
                "delivery_status": {"const": "error"},
                "error_code": {
                    "enum": [
                        "invalid_request",
                        "configuration_error",
                        "not_found",
                        "expired",
                        "corrupt",
                        "artifact_too_large",
                        "publication_error",
                        "lint_blocked",
                        "exec_error",
                        "no_figure",
                        "timeout",
                    ]
                },
                "message": {"type": "string"},
                "report": {"type": "object"},
            },
        },
    ],
}

_DELETE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "oneOf": [
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["schema_version", "artifact_id", "state"],
            "properties": {
                "schema_version": {"const": 1},
                "artifact_id": _SCHEMA["oneOf"][0]["properties"]["artifact_id"],
                "state": {"enum": ["deleted", "absent"]},
            },
        },
        _SCHEMA["oneOf"][1],
    ],
}

# Registration-bound authority decisions, checked against actual discovery.
ENTRY_POLICIES = {
    "render_plot": "local_user_store_bounded_execution",
    "get_plot_artifact": "local_user_store_verified_read",
    "delete_plot_inputs": "local_operator_grant_bounded_delete",
    **{
        f"dartwork-mpl://artifacts/{{artifact_id}}/{member.value}": "local_user_store_verified_read"
        for member in ArtifactMember
    },
}


class _ArtifactErrorResult(ToolResult):
    """Preserve structured errors on both supported FastMCP major versions."""

    def to_mcp_result(self) -> CallToolResult:
        """Use the public MCP result protocol instead of text-only exceptions."""
        return CallToolResult(
            content=self.content,
            structuredContent=self.structured_content,
            isError=True,
        )


def _failure_metadata(failure: ArtifactFailure) -> dict[str, Any]:
    """Map typed refusals to stable categories without infrastructure paths."""
    if isinstance(failure, LogLimitRejected):
        code = "artifact_too_large"
        message = "Artifact exceeds the byte limit."
    elif isinstance(failure, ExecutionRejected):
        code = failure.report["status"]
        message = "Plot execution did not complete."
    else:
        code = {
            InvalidRequest: "invalid_request",
            ConfigurationError: "configuration_error",
            NotFound: "not_found",
            Expired: "expired",
            CorruptArtifact: "corrupt",
            ArtifactTooLarge: "artifact_too_large",
            PublicationError: "publication_error",
            ExportRejected: "publication_error",
        }[type(failure)]
        message = {
            "invalid_request": "Artifact request is invalid.",
            "configuration_error": "Artifact storage configuration is invalid.",
            "not_found": "Artifact was not found.",
            "expired": "Artifact has expired.",
            "corrupt": "Artifact contents are invalid.",
            "artifact_too_large": "Artifact exceeds the byte limit.",
            "publication_error": "Artifact publication failed.",
        }[code]
    if isinstance(failure, InvalidRequest):
        message = f"{failure.field}: {failure.message}"
    metadata: dict[str, Any] = {
        "schema_version": 1,
        "delivery_status": "error",
        "error_code": code,
        "message": message,
    }
    if isinstance(
        failure, (ExecutionRejected, LogLimitRejected, ExportRejected)
    ):
        metadata["report"] = failure.report
    return metadata


def _result(outcome: StoredBundle | ArtifactFailure) -> ToolResult:
    """Serialize ready bytes or a stable error into matching text/structured data."""
    if not isinstance(outcome, StoredBundle):
        metadata = _failure_metadata(outcome)
        return _ArtifactErrorResult(
            content=[
                TextContent(
                    type="text", text=json.dumps(metadata, ensure_ascii=False)
                )
            ],
            structured_content=metadata,
        )
    manifest = json.loads(outcome.contents[ArtifactMember.MANIFEST])
    files = []
    links = []
    for member in ArtifactMember:
        uri = f"dartwork-mpl://artifacts/{outcome.manifest.artifact_id.value}/{member.value}"
        entry = {
            "name": member.value,
            "uri": uri,
            "mime_type": member.mime_type,
            "size_bytes": len(outcome.contents[member]),
        }
        if member != ArtifactMember.MANIFEST:
            entry["sha256"] = next(
                item["sha256"]
                for item in manifest["files"]
                if item["name"] == member.value
            )
        files.append(entry)
        links.append(
            ResourceLink(
                type="resource_link",
                name=member.value,
                uri=AnyUrl(uri),
                mimeType=member.mime_type,
                size=len(outcome.contents[member]),
            )
        )
    metadata = {
        key: manifest[key]
        for key in (
            "schema_version",
            "artifact_id",
            "created_at",
            "expires_at",
            "validation",
        )
    }
    metadata.update(delivery_status="ready", files=files)
    return ToolResult(
        content=[
            ImageContent(
                type="image",
                data=base64.b64encode(
                    outcome.contents[ArtifactMember.PNG]
                ).decode("ascii"),
                mimeType="image/png",
            ),
            *links,
            TextContent(
                type="text", text=json.dumps(metadata, ensure_ascii=False)
            ),
        ],
        structured_content=metadata,
    )


def register_artifacts(
    mcp: FastMCP,
    store: ArtifactStore | ConfigurationError,
    *,
    runtime: ArtifactRuntime | None = None,
) -> None:
    """Bind artifact routes; only an explicitly supplied runtime enables retention.

    Direct registration remains usable without a session owner or input policy.
    """
    if runtime is not None and not runtime.bind(mcp):
        # An unknown SDK bridge cannot own resources; legacy routes still work.
        runtime = None

    @mcp.tool(output_schema=_SCHEMA)
    async def render_plot(
        code: str,
        figure_var: str = "fig",
        timeout_seconds: float = 20.0,
        chart_type_hint: str | None = None,
        revision: object | None = None,
    ) -> ToolResult:
        """Execute trusted plotting code once and deliver PNG/PDF/source/report.

        Source is limited to 512 KiB UTF-8 and timeout to finite (0, 120]
        seconds. Bundles total at most 32 MiB and remain retrievable for seven
        days through get_plot_artifact and the five linked resources. Code has
        the local server user's OS access; execution is not an OS sandbox.

        Optional closed v1 revision explicitly selects a parent and/or Copy or
        Retained inputs. Copy opens only an operator-granted logical root/file;
        Retained selects fixed server-local snapshot bytes, never current upstream
        data. Input-bearing source uses read-only dartwork_inputs[name] paths.
        report.json contains creation-time selection/hash/child-locator receipts;
        child creation time is publication time, not data capture/latest time.
        Delete/expiry may remove inputs while the report remains readable. Actual
        Retained admission checks availability; failures never substitute inputs.
        """
        request = parse_render_request(
            code, figure_var, timeout_seconds, chart_type_hint
        )
        if isinstance(request, InvalidRequest):
            return _result(request)
        parsed = parse_revision(revision)
        if isinstance(parsed, InvalidRequest):
            return _result(parsed)
        if isinstance(store, ConfigurationError):
            return _result(store)

        def deliver() -> StoredBundle | ArtifactFailure:
            """Use fresh clocks in synchronous delivery with disabled input authority."""
            return render_artifact(
                store,
                request,
                lambda: datetime.now(timezone.utc),
                revision=parsed,
            )

        if runtime is None:
            return _result(await run_owned(deliver))
        # No await between this gate and admission: accepted work is counted
        # before it can wait for the serial pipeline. Legacy calls also drain.
        if not runtime.accepting:
            return _result(ConfigurationError())
        async with runtime.admission() as inputs:
            return _result(
                await run_owned(
                    lambda: render_artifact(
                        store,
                        request,
                        lambda: datetime.now(timezone.utc),
                        revision=parsed,
                        inputs=inputs,
                    )
                )
            )

    @mcp.tool(output_schema=_SCHEMA)
    def get_plot_artifact(artifact_id: str) -> ToolResult:
        """Read a verified artifact without execution or renewal.

        report.json receipts identify fixed server-local input copies and selection
        history. They do not assert current input availability or upstream freshness;
        actual Retained admission rechecks the grant, expiry and commit.
        """
        identity = parse_artifact_id(artifact_id)
        if isinstance(identity, InvalidRequest):
            return _result(identity)
        if isinstance(store, ConfigurationError):
            return _result(store)
        return _result(
            get_artifact(store, identity, datetime.now(timezone.utc))
        )

    def read(artifact_id: str, member: ArtifactMember) -> Any:
        """Validate identity and complete bundle before serving a literal member."""
        identity = parse_artifact_id(artifact_id)
        if isinstance(identity, InvalidRequest):
            failure: ArtifactFailure = identity
        elif isinstance(store, ConfigurationError):
            failure = store
        else:
            outcome = store.read_member(
                identity, member, datetime.now(timezone.utc)
            )
            if not isinstance(
                outcome,
                (
                    NotFound,
                    Expired,
                    CorruptArtifact,
                    ArtifactTooLarge,
                    PublicationError,
                ),
            ):
                data: bytes | str = outcome.data
                if member not in (ArtifactMember.PNG, ArtifactMember.PDF):
                    data = outcome.data.decode("utf-8")
                if _RESOURCE_WRAPPERS:
                    return ResourceResult(
                        contents=[
                            ResourceContent(data, mime_type=member.mime_type)
                        ]
                    )
                return data
            failure = outcome
        metadata = _failure_metadata(failure)
        raise ResourceError(f"{metadata['error_code']}: {metadata['message']}")

    @mcp.resource(
        "dartwork-mpl://artifacts/{artifact_id}/plot.png", mime_type="image/png"
    )
    def artifact_png(artifact_id: str) -> Any:
        """Read verified PNG bytes."""
        return read(artifact_id, ArtifactMember.PNG)

    @mcp.resource(
        "dartwork-mpl://artifacts/{artifact_id}/plot.pdf",
        mime_type="application/pdf",
    )
    def artifact_pdf(artifact_id: str) -> Any:
        """Read verified PDF bytes."""
        return read(artifact_id, ArtifactMember.PDF)

    @mcp.resource(
        "dartwork-mpl://artifacts/{artifact_id}/source.py",
        mime_type="text/x-python",
    )
    def artifact_source(artifact_id: str) -> Any:
        """Read exact submitted UTF-8 source."""
        return read(artifact_id, ArtifactMember.SOURCE)

    @mcp.resource(
        "dartwork-mpl://artifacts/{artifact_id}/report.json",
        mime_type="application/json",
    )
    def artifact_report(artifact_id: str) -> Any:
        """Read the complete execution report."""
        return read(artifact_id, ArtifactMember.REPORT)

    @mcp.resource(
        "dartwork-mpl://artifacts/{artifact_id}/manifest.json",
        mime_type="application/json",
    )
    def artifact_manifest(artifact_id: str) -> Any:
        """Read the published v1 manifest without a recursive self-digest."""
        return read(artifact_id, ArtifactMember.MANIFEST)

    @mcp.tool(output_schema=_DELETE_SCHEMA)
    async def delete_plot_inputs(artifact_id: str) -> ToolResult:
        """Revoke this operator-granted input set, leaving artifacts and children intact.

        Requires startup input policy. Returns deleted or absent only after safe
        deletion barriers; unknown/unsafe residue stays counted and is an error.
        """
        identity = parse_artifact_id(artifact_id)
        if isinstance(identity, InvalidRequest):
            return _result(identity)
        if runtime is None:
            outcome = delete_inputs(InputsDisabled(), identity)
        else:
            if not runtime.accepting:
                return _result(ConfigurationError())
            async with runtime.admission() as inputs:
                outcome = await run_owned(
                    lambda: delete_inputs(inputs, identity)
                )
        if not isinstance(outcome, (DeletedInputs, AbsentInputs)):
            return _result(outcome)
        metadata = {
            "schema_version": 1,
            "artifact_id": outcome.artifact_id.value,
            "state": "deleted"
            if isinstance(outcome, DeletedInputs)
            else "absent",
        }
        return ToolResult(
            content=[
                TextContent(
                    type="text", text=json.dumps(metadata, ensure_ascii=False)
                )
            ],
            structured_content=metadata,
        )
