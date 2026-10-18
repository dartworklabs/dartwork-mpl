"""Server-authorized render/retrieve use cases over one validated export."""

from collections.abc import Callable
from datetime import datetime
from typing import TypeAlias

from ..execution import ExecutionRejected, ExportRejected, export_plot
from .policy import (
    ArtifactId,
    ArtifactTooLarge,
    ConfigurationError,
    CorruptArtifact,
    Expired,
    InvalidRequest,
    NotFound,
    PublicationError,
    RenderRequest,
    StoredBundle,
    StoreFailure,
)
from .store import ArtifactStore

ArtifactFailure: TypeAlias = (
    InvalidRequest
    | ConfigurationError
    | NotFound
    | Expired
    | CorruptArtifact
    | ArtifactTooLarge
    | PublicationError
    | ExecutionRejected
    | ExportRejected
)


def render_artifact(
    store: ArtifactStore, request: RenderRequest, clock: Callable[[], datetime]
) -> StoredBundle | ArtifactFailure:
    """Export once, preserve all logs, then publish against the completion clock."""
    try:
        with store.staging() as stage:
            outcome = export_plot(
                request.code,
                request.figure_var,
                request.timeout_seconds,
                request.chart_type_hint,
                output_stem=stage.output_stem,
            )
            if isinstance(outcome, (ExecutionRejected, ExportRejected)):
                return outcome
            return store.publish(
                stage, request.code.encode("utf-8"), outcome.report, clock()
            )
    except OSError:
        return PublicationError()


def get_artifact(
    store: ArtifactStore, artifact_id: ArtifactId, now: datetime
) -> StoredBundle | StoreFailure:
    """Retrieve only a fully verified, unexpired server-bound bundle."""
    return store.load(artifact_id, now)
