"""Server-authorized export/retrieval and paired independent-input publication."""

import hashlib
from collections.abc import Callable
from datetime import datetime
from typing import TypeAlias

from ..execution import ExecutionRejected, ExportRejected, export_plot
from .input_access import InputsDisabled
from .input_policy import (
    InputMetadata,
    PinnedParent,
    Revision,
    build_provenance,
)
from .inputs import (
    AbsentInputs,
    DeletedInputs,
    InputStage,
    InputStore,
    InputTransaction,
)
from .policy import (
    ArtifactId,
    ArtifactMember,
    ArtifactTooLarge,
    ConfigurationError,
    CorruptArtifact,
    Expired,
    InvalidRequest,
    Manifest,
    NotFound,
    PublicationError,
    RenderRequest,
    StoredBundle,
    StoreFailure,
)
from .store import ArtifactStore, StagedBundle

_INPUTS_DISABLED = InputsDisabled()

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
    store: ArtifactStore,
    request: RenderRequest,
    clock: Callable[[], datetime],
    *,
    revision: Revision | None = None,
    inputs: InputStore | InputsDisabled | ConfigurationError = _INPUTS_DISABLED,
) -> StoredBundle | ArtifactFailure:
    """Export once; opt-in revisions pin a live parent and independent input bytes.

    Callers supply a parsed request/revision and a fresh UTC clock. Legacy calls
    retain their original serialization and inject no input mapping. Input-bearing
    calls own the serial transaction through synchronous execution, one postcheck,
    paired publication and post-artifact-exit settlement. Cancellation propagates
    after that settlement; asynchronous admission/draining belongs to the caller.
    """
    if revision is not None:
        return _render_revision(store, request, clock, revision, inputs)
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


def _render_revision(
    store: ArtifactStore,
    request: RenderRequest,
    clock: Callable[[], datetime],
    revision: Revision,
    inputs: InputStore | InputsDisabled | ConfigurationError,
) -> StoredBundle | ArtifactFailure:
    """Pin parent bytes once at admission, composing only public store capabilities.

    Input policy is required only for nonempty selections. A pinned parent's later
    expiry/corruption cannot change this child's receipt or validation. Filesystem
    errors refuse publication without disclosing configuration or original paths.
    """
    try:
        if not revision.inputs:
            parent = _pin_parent(store, revision.parent_artifact_id, clock())
            if parent is not None and not isinstance(parent, PinnedParent):
                return parent
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
                report = {
                    **outcome.report,
                    "provenance": build_provenance(revision, parent, None),
                }
                return store.publish(
                    stage, request.code.encode("utf-8"), report, clock()
                )
        if not isinstance(inputs, InputStore):
            return _input_unavailable(inputs)
        with inputs.transaction() as tx:
            admitted_at = clock()
            parent = _pin_parent(
                store, revision.parent_artifact_id, admitted_at
            )
            if parent is not None and not isinstance(parent, PinnedParent):
                return parent
            copied = None
            try:
                with store.staging() as stage:
                    prepared = tx.prepare(
                        stage.artifact_id,
                        revision.inputs,
                        admitted_at,
                        store.observe_commit,
                    )
                    if not isinstance(prepared, InputStage):
                        return prepared
                    copied = prepared
                    result = _publish_inputs(
                        store,
                        request,
                        clock,
                        revision,
                        parent,
                        tx,
                        stage,
                        copied,
                    )
            finally:
                # The complete artifact context (including cleanup/FD close) has
                # exited before observing any commit, even on exceptions/cancel.
                if copied is not None:
                    settled = _settle_inputs(
                        store, tx, copied, stage.artifact_id
                    )
            if isinstance(result, StoredBundle) and settled is not None:
                return settled
            return result
    except OSError:
        return PublicationError()


def _pin_parent(
    store: ArtifactStore, artifact_id: ArtifactId | None, admitted_at: datetime
) -> PinnedParent | None | StoreFailure:
    """Hash verified parent manifest/source bytes once, without interpreting ancestry.

    Absence means this revision selected no parent. A selected parent's full load
    must succeed at admission; later export/publication uses only these digests.
    """
    if artifact_id is None:
        return None
    loaded = store.load(artifact_id, admitted_at)
    if not isinstance(loaded, StoredBundle):
        return loaded
    return PinnedParent(
        loaded.manifest.artifact_id,
        hashlib.sha256(loaded.contents[ArtifactMember.MANIFEST]).hexdigest(),
        hashlib.sha256(loaded.contents[ArtifactMember.SOURCE]).hexdigest(),
    )


def _publish_inputs(
    store: ArtifactStore,
    request: RenderRequest,
    clock: Callable[[], datetime],
    revision: Revision,
    parent: PinnedParent | None,
    tx: InputTransaction,
    stage: StagedBundle,
    copied: InputStage,
) -> StoredBundle | ArtifactFailure:
    """Keep authorized copies alive through export, then commit inputs before bundle.

    Postcheck runs exactly once after successful export. Both commits receive the
    same freshly sampled completion instant; only both successful returns can be
    Ready. The new receipt overrides any exporter-authored provenance, leaving
    the original report value and submitted UTF-8 source unchanged.
    """
    outcome = export_plot(
        request.code,
        request.figure_var,
        request.timeout_seconds,
        request.chart_type_hint,
        output_stem=stage.output_stem,
        input_paths=copied.execution_inputs,
    )
    if isinstance(outcome, (ExecutionRejected, ExportRejected)):
        return outcome
    checked = tx.check(copied)
    if checked is not None:
        return checked
    completed_at = clock()
    metadata = tx.commit(copied, completed_at)
    if not isinstance(metadata, InputMetadata):
        return metadata
    report = {
        **outcome.report,
        "provenance": build_provenance(revision, parent, metadata),
    }
    return store.publish(
        stage, request.code.encode("utf-8"), report, completed_at
    )


def _settle_inputs(
    store: ArtifactStore,
    tx: InputTransaction,
    copied: InputStage,
    artifact_id: ArtifactId,
) -> None | PublicationError:
    """Settle after artifact exit, preserving matching or uncertain input commits.

    Only public NotFound permits rollback. Observer I/O exceptions are ambiguous;
    settlement must still run while owning the transaction. A safe rollback is
    cleanup, never evidence that an otherwise successful result remains Ready.
    """
    try:
        observation = store.observe_commit(artifact_id)
    except OSError:
        observation = PublicationError()
    try:
        settled = tx.settle(copied, observation)
    except OSError:
        return PublicationError()
    if settled is not None:
        return settled
    return None if isinstance(observation, Manifest) else PublicationError()


def _input_unavailable(
    inputs: InputsDisabled | ConfigurationError,
) -> ConfigurationError:
    """Pass through safe configuration refusal or deny the default unset policy."""
    return (
        inputs
        if isinstance(inputs, ConfigurationError)
        else ConfigurationError("Input retention is disabled.")
    )


def delete_inputs(
    inputs: InputStore | InputsDisabled | ConfigurationError, id: ArtifactId
) -> DeletedInputs | AbsentInputs | ArtifactFailure:
    """Revoke only this authorized input set, never bundles or original files.

    The store owns all six deletion states and durability barriers. Disabled or
    invalid policy denies access; an I/O exception never becomes deletion success.
    """
    if not isinstance(inputs, InputStore):
        return _input_unavailable(inputs)
    try:
        return inputs.delete(id)
    except OSError:
        return PublicationError()


def get_artifact(
    store: ArtifactStore, artifact_id: ArtifactId, now: datetime
) -> StoredBundle | StoreFailure:
    """Retrieve only a fully verified, unexpired server-bound bundle."""
    return store.load(artifact_id, now)
