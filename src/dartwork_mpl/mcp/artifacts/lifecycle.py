"""Own opt-in retention from each SDK RUN through joined synchronous delivery.

Construction and binding are inert. The local operator's policy is authorized
only at session startup; no request can mint or widen that capability. A narrow
FastMCP bridge composes the SDK lifespan because FastMCP's user lifespan skips
independent overlapping memory clients on both supported majors.
"""

import asyncio
import inspect
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, TypeAlias, TypeVar

import anyio
from mcp.server.lowlevel import Server

from .input_access import InputGrant, InputsDisabled, authorize_inputs
from .inputs import InputStore
from .policy import ConfigurationError
from .store import ArtifactStore

__all__ = ["ArtifactRuntime"]

Inputs: TypeAlias = InputStore | InputsDisabled | ConfigurationError
T = TypeVar("T")
_sleep = asyncio.sleep


async def _join(task: asyncio.Task[T]) -> T:
    """Join owned work despite caller cancellation, then propagate cancellation.

    Shield both AnyIO scopes (SDK task groups) and direct/repeated Task.cancel.
    The owned task itself must finish; cancellation of an await is not a join.
    """
    cancelled = None
    with anyio.CancelScope(shield=True):
        while True:
            try:
                result = await asyncio.shield(task)
                break
            except asyncio.CancelledError as error:
                if task.cancelled():
                    raise
                cancelled = error
    if cancelled is not None:
        raise cancelled
    await anyio.lowlevel.checkpoint_if_cancelled()
    return result


async def run_owned(operation: Callable[[], T]) -> T:
    """Offload blocking delivery, keeping its caller until all synchronous work ends.

    Delivery already owns stages, worker deadlines/reaping and settlement until
    return. This adapter never abandons that ownership when its awaiter cancels.
    """
    return await _join(asyncio.create_task(asyncio.to_thread(operation)))


@dataclass
class _Resources:
    """One startup generation; a grant exists only alongside its owned input store."""

    inputs: Inputs
    grant: InputGrant | None = None

    def __post_init__(self) -> None:
        """Reject unpaired resource ownership before any close or admission can use it."""
        if not isinstance(
            self.inputs, (InputStore, InputsDisabled, ConfigurationError)
        ) or isinstance(self.inputs, InputStore) != isinstance(
            self.grant, InputGrant
        ):
            raise ValueError("Input store and startup grant must be paired")

    def close(self) -> None:
        """Close store FDs/lock before grant pins, including partial startup cleanup."""
        try:
            if isinstance(self.inputs, InputStore):
                self.inputs.close()
        finally:
            if self.grant is not None:
                self.grant.close()


@dataclass
class _Session:
    """One live generation with serial retention and an explicit drain barrier."""

    resources: _Resources
    owners: int = 0
    calls: int = 0
    accepting: bool = True
    pipeline: asyncio.Lock = field(default_factory=asyncio.Lock)
    idle: asyncio.Event = field(default_factory=asyncio.Event)
    maintenance: asyncio.Task[None] | None = None


class ArtifactRuntime:
    """Inert owner of optional input authority, sessions, calls and maintenance.

    Sessions on one event loop share one startup. Last close stops admission,
    joins maintenance/accepted work, then closes store and grant. A later session
    reopens from policy; explicit close is idempotent and ends that generation.
    Legacy artifact workflows can operate with disabled or erroneous retention.
    """

    def __init__(
        self, store: ArtifactStore | ConfigurationError, policy_path: str | None
    ) -> None:
        """Remember configuration without reading it or creating resources/tasks."""
        self._store = store
        self._policy_path = policy_path
        self._gate = asyncio.Lock()
        self._live: _Session | None = None
        self._supported = True
        self._bound: object | None = None

    @property
    def accepting(self) -> bool:
        """Report admission status without exposing policy or storage details."""
        return self._live is not None and self._live.accepting

    def bind(self, mcp: Any) -> bool:
        """Compose each SDK RUN's original lifespan on the existing FastMCP object.

        `_mcp_server` is the only private framework bridge used. Require the
        SDK Server/callable shape observed on FastMCP 2.13.3 and 3.4.2; unknown
        shapes disable retention without modifying framework counters or legacy
        registrations. Preserve the original context object and nesting order.
        """
        if self._bound is mcp:
            return self._supported
        if self._bound is not None:
            return False
        low = getattr(mcp, "_mcp_server", None)
        original = getattr(low, "lifespan", None)
        try:
            if not isinstance(low, Server) or not callable(original):
                raise TypeError("Unsupported SDK lifespan")
            inspect.signature(original).bind(low)
            parameters = inspect.signature(low.run).parameters
            if (
                not {"read_stream", "write_stream", "initialization_options"}
                <= parameters.keys()
            ):
                raise TypeError("Unsupported SDK run")

            @asynccontextmanager
            async def lifespan(server: Any) -> AsyncIterator[Any]:
                """Enter our owner before the saved SDK context; exit in reverse."""
                async with self.session(), original(server) as context:
                    yield context

            low.lifespan = lifespan
        except (AttributeError, TypeError, ValueError):
            self._supported = False
            return False
        self._bound = mcp
        return True

    def _open(self) -> _Resources:
        """Authorize once and transfer both resources, closing partial acquisitions."""
        if not self._supported or isinstance(self._store, ConfigurationError):
            return _Resources(ConfigurationError())
        grant = authorize_inputs(
            self._policy_path, self._store.check_input_roots
        )
        if not isinstance(grant, InputGrant):
            return _Resources(grant)
        try:
            inputs = InputStore.open(grant, datetime.now(timezone.utc))
            if isinstance(inputs, InputStore):
                return _Resources(inputs, grant)
            grant.close()
            return _Resources(inputs)
        except BaseException:
            grant.close()
            raise

    @asynccontextmanager
    async def session(self) -> AsyncIterator["ArtifactRuntime"]:
        """Count each transport RUN; serialize startup against complete last-close."""
        async with self._gate:
            if self._live is None:
                task = asyncio.create_task(asyncio.to_thread(self._open))
                try:
                    resources = await _join(task)
                except BaseException:
                    # _join has already waited for a late thread result. It must
                    # be reclaimed even when cancellation prevented assignment.
                    if not task.cancelled() and task.exception() is None:
                        await run_owned(task.result().close)
                    raise
                live = _Session(resources)
                live.idle.set()
                self._live = live
                if isinstance(resources.inputs, InputStore):
                    live.maintenance = asyncio.create_task(self._maintain(live))
            live = self._live
            live.owners += 1
        try:
            yield self
        finally:
            await _join(asyncio.create_task(self._leave(live)))

    async def _leave(self, live: _Session) -> None:
        """Release only this generation; old owners cannot close a reopened one."""
        async with self._gate:
            if self._live is live:
                live.owners -= 1
                if live.owners == 0:
                    await self._stop(live)

    @asynccontextmanager
    async def admission(self) -> AsyncIterator[Inputs]:
        """Accept before queuing; serialize without sweeping before target lookup.

        Accepted callers own their place through synchronous termination and fresh
        operation-tail maintenance. Closing callers receive a deny capability.
        """
        live = self._live
        if live is None or not live.accepting:
            yield ConfigurationError()
            return
        live.calls += 1
        live.idle.clear()
        try:
            async with live.pipeline:
                try:
                    yield live.resources.inputs
                finally:
                    inputs = live.resources.inputs
                    if isinstance(inputs, InputStore):
                        await run_owned(
                            lambda: inputs.maintain(datetime.now(timezone.utc))
                        )
        finally:
            live.calls -= 1
            if live.calls == 0:
                live.idle.set()

    async def _maintain(self, live: _Session) -> None:
        """Own a 60-second tick; queue behind work and sample time at execution."""
        while True:
            await _sleep(60)
            if not live.accepting:
                return
            # Admission's finally block is the same serialized fresh-clock sweep
            # used at operation tails, without a preliminary lookup sweep.
            async with self.admission():
                pass

    async def _stop(self, live: _Session) -> None:
        """Stop admission before joining timer/calls and closing store then grant."""
        live.accepting = False
        if live.maintenance is not None:
            live.maintenance.cancel()
            with suppress(asyncio.CancelledError):
                await live.maintenance
        await live.idle.wait()
        try:
            await run_owned(live.resources.close)
        finally:
            self._live = None

    async def close(self) -> None:
        """End this generation once; cancellation still waits for owned cleanup."""

        async def close_locked() -> None:
            """Serialize explicit close with startup and all session releases."""
            async with self._gate:
                if self._live is not None:
                    await self._stop(self._live)

        await _join(asyncio.create_task(close_locked()))
