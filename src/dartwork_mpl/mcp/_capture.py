"""Bounded child diagnostics for trusted MCP execution, without a log spool.

Two independent views preserve completed universal-newline and timeout direct
UTF-8 replacement semantics. Retained payload bytes never exceed twice the
selected view budget (or four channel budgets); decoder/read working chunks
are bounded separately. This is not an OS-wide or child-memory limit.
"""

import codecs
import io
import math
import os
import re
import selectors
import stat
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from typing import IO, cast

_CHANNEL_BYTES = 64 * 1024
_READ_BYTES = 8 * 1024


def _marker(channel: str) -> str:
    """Describe a retained prefix without claiming an original output size."""
    return f"\n[dartwork-mpl: {channel} truncated; retained prefix only]\n"


def _utf8_prefix(data: bytes | bytearray, limit: int) -> bytes:
    """Keep at most limit UTF-8 bytes, dropping only a partial final character."""
    return (
        bytes(data[: max(0, limit)]).decode("utf-8", "ignore").encode("utf-8")
    )


def diagnostic(
    text: str,
    channel: str,
    *,
    truncated: bool = False,
    marked: bool = False,
    byte_limit: int = _CHANNEL_BYTES,
    char_limit: int | None = None,
    suffix: str = "",
) -> str:
    """Fit a processed diagnostic, marker and optional timeout suffix in its view.

    Below-limit text is unchanged. Set marked only for text already decorated
    by a known collector truncation. A clipped result retains the whole channel
    marker, including in a template's 2,000-character presentation.
    """
    marker = _marker(channel)
    if marked:
        text = text[: -len(marker)]
        truncated = True
    decorated = text + ("\n" if text and suffix else "") + suffix
    if (
        not truncated
        and len(decorated.encode("utf-8")) <= byte_limit
        and (char_limit is None or len(decorated) <= char_limit)
    ):
        return decorated
    tail = marker + suffix
    available = max(0, byte_limit - len(tail.encode("utf-8")))
    prefix = _utf8_prefix(text.encode("utf-8"), available).decode("utf-8")
    if char_limit is not None:
        prefix = prefix[: max(0, char_limit - len(tail))]
    return prefix + tail


def strip_diagnostic(text: str, channel: str, *, marked: bool = False) -> str:
    """Strip user whitespace; preserve a suffix only when collector metadata marks it."""
    marker = _marker(channel)
    if marked:
        return diagnostic(text[: -len(marker)].strip(), channel, truncated=True)
    return text.strip()


class _View:
    """Own one completion view's prefixes and shared or per-channel budget.

    Once a shared artifact budget is exceeded, only diagnostic prefixes remain.
    Independent normal/timeout views never make each other's refusal decision.
    """

    def __init__(self, shared_limit: int | None, strip_stderr: bool) -> None:
        """Create empty channel state; shared_limit=None gives legacy budgets."""
        if shared_limit is not None and (
            type(shared_limit) is not int or shared_limit <= 0
        ):
            raise ValueError("Shared log budget must be a positive integer")
        self.shared_limit = shared_limit
        self.prefixes = {"stdout": bytearray(), "stderr": bytearray()}
        self.truncated = {"stdout": False, "stderr": False}
        self.overrun = False
        self.strip_stderr = strip_stderr
        self.started = False
        self.pending = bytearray()
        self.pending_bytes = 0

    @property
    def retained_bytes(self) -> int:
        """Expose payload retention, including deferred stderr whitespace."""
        return sum(map(len, self.prefixes.values())) + len(self.pending)

    def _append(
        self, channel: str, data: bytes, size: int | None = None
    ) -> None:
        """Retain only a complete-character prefix, discarding excess now."""
        count = len(data) if size is None else size
        if self.shared_limit is not None and not self.overrun:
            used = sum(map(len, self.prefixes.values()))
            if used + count > self.shared_limit:
                self.overrun = True
                for name, prefix in self.prefixes.items():
                    if len(prefix) > _CHANNEL_BYTES:
                        self.truncated[name] = True
                        self.prefixes[name] = bytearray(
                            _utf8_prefix(prefix, _CHANNEL_BYTES)
                        )
        if self.truncated[channel]:
            return
        limit = (
            self.shared_limit
            if self.shared_limit is not None and not self.overrun
            else _CHANNEL_BYTES
        )
        prefix = self.prefixes[channel]
        available = max(0, limit - len(prefix))
        if self.shared_limit is not None:
            available = min(
                available,
                max(
                    0, self.shared_limit - sum(map(len, self.prefixes.values()))
                ),
            )
        kept = _utf8_prefix(data, available)
        prefix.extend(kept)
        if count > len(kept):
            self.truncated[channel] = True

    def feed(self, channel: str, text: str) -> None:
        """Account processed text, implementing legacy stderr strip incrementally."""
        if channel != "stderr" or not self.strip_stderr:
            self._append(channel, text.encode("utf-8"))
            return
        # Strip discards unlimited leading/trailing whitespace without retaining
        # it. Deferred interior whitespace only consumes a bounded prefix.
        if self.truncated[channel]:
            return
        for match in re.finditer(r"\s+|\S+", text):
            segment = match.group()
            encoded = segment.encode("utf-8")
            if segment.isspace():
                if self.started:
                    self.pending_bytes += len(encoded)
                    self.pending.extend(
                        _utf8_prefix(
                            encoded, _CHANNEL_BYTES - len(self.pending)
                        )
                    )
                continue
            if self.pending_bytes:
                self._append(channel, bytes(self.pending), self.pending_bytes)
                self.pending.clear()
                self.pending_bytes = 0
            self.started = True
            self._append(channel, encoded)

    def logs(self, timeout_suffix: str = "") -> tuple[str, str]:
        """Return exact accepted logs or bounded marked selected-view diagnostics."""
        texts = {}
        for channel, prefix in self.prefixes.items():
            text = prefix.decode("utf-8")
            texts[channel] = diagnostic(
                text,
                channel,
                truncated=self.truncated[channel],
                suffix=timeout_suffix if channel == "stderr" else "",
                byte_limit=(
                    _CHANNEL_BYTES
                    if self.shared_limit is None or self.overrun
                    else self.shared_limit
                ),
            )
        return texts["stdout"], texts["stderr"]


class _Capture:
    """Incrementally retain independent bounded normal and timeout views.

    Legacy payload retention <= 6*64 KiB (four prefixes and two deferred
    whitespace prefixes). Artifact retention <= 2*shared_limit; no whitespace
    deferral is used there. Raw reads <=8 KiB and each decode <=24 KiB UTF-8;
    Python object/allocator overhead and final report serialization are separate.
    """

    def __init__(self, shared_limit: int | None, strip_stderr: bool) -> None:
        """Choose independent view budgets before reading any child bytes."""
        self.normal = _View(shared_limit, strip_stderr)
        self.timeout = _View(shared_limit, strip_stderr)
        self.decoders = {}
        for view, translate in ((self.normal, True), (self.timeout, False)):
            for channel in ("stdout", "stderr"):
                decoder = codecs.getincrementaldecoder("utf-8")("replace")
                self.decoders[id(view), channel] = (
                    io.IncrementalNewlineDecoder(decoder, translate=True)
                    if translate
                    else decoder
                )

    @property
    def retained_bytes(self) -> int:
        """Report both views' currently retained payload bytes for bound checks."""
        return self.normal.retained_bytes + self.timeout.retained_bytes

    def feed(self, channel: str, raw: bytes, *, final: bool = False) -> None:
        """Decode one <=8 KiB read and discard any excess during this update."""
        for view in (self.normal, self.timeout):
            text = self.decoders[id(view), channel].decode(raw, final)
            view.feed(channel, text)


@dataclass(frozen=True)
class CapturedProcess:
    """A reaped child, selected output and known collector-prefix truncation flags.

    Flags describe collector provenance, never a match against user log text.
    """

    returncode: int
    timed_out: bool
    stdout: str
    stderr: str
    log_overrun: bool
    stdout_truncated: bool = False
    stderr_truncated: bool = False


def _windows_available(stream: IO[bytes]) -> int | None:
    """Peek a Windows pipe without blocking; None means its write end closed.

    HANDLE uses pointer width and DWORD uses 32 bits on supported Windows
    Pythons. Broken/no-data pipe errors are EOF; other OS errors propagate so
    the owner can kill/reap the direct child and close all handles.
    """
    if sys.platform != "win32":
        raise OSError("Windows pipe polling is only available on Windows")
    import ctypes
    import msvcrt
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    peek = kernel.PeekNamedPipe
    peek.argtypes = [
        wintypes.HANDLE,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.POINTER(wintypes.DWORD),
        ctypes.POINTER(wintypes.DWORD),
    ]
    peek.restype = wintypes.BOOL
    available = wintypes.DWORD()
    handle = wintypes.HANDLE(msvcrt.get_osfhandle(stream.fileno()))
    if not peek(handle, None, 0, None, ctypes.byref(available), None):
        error = ctypes.get_last_error()
        if error in (109, 232):  # ERROR_BROKEN_PIPE / ERROR_NO_DATA
            return None
        raise ctypes.WinError(error)
    return int(available.value)


def run_child(
    args: list[str],
    *,
    stdin: str = "",
    timeout_seconds: float,
    shared_log_limit: int | None = None,
    strip_stderr: bool = False,
    timeout_message: bool = False,
) -> CapturedProcess:
    """Run trusted code with inherited cwd/environment and bounded diagnostics.

    Only finite submitted stdin framing uses a private temporary file; output
    never spools. Polling owns all pipe handles, avoids blocking drain/writer
    threads. POSIX nonblocking selectors bound inherited-pipe polling by the
    deadline. Windows peeks from the sole owner of each read handle; synchronous
    PeekNamedPipe retains Win32 blocking caveats. Only the direct child is
    killed/reaped. Every owned resource closes when the operation exits.
    """
    if not math.isfinite(timeout_seconds):
        raise ValueError("Subprocess timeout must be finite")
    capture = _Capture(shared_log_limit, strip_stderr)
    timed_out = False
    with tempfile.TemporaryFile(mode="w+b") as source:
        source.write(stdin.encode("utf-8"))
        source.seek(0)
        with subprocess.Popen(
            args,
            stdin=source,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        ) as process:
            assert process.stdout is not None and process.stderr is not None
            streams = {process.stdout: "stdout", process.stderr: "stderr"}
            deadline = time.monotonic() + timeout_seconds
            try:
                with selectors.DefaultSelector() as selector:
                    if os.name != "nt":
                        for stream in streams:
                            os.set_blocking(stream.fileno(), False)
                            selector.register(stream, selectors.EVENT_READ)
                    while streams or process.poll() is None:
                        exited = process.poll() is not None
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            timed_out = not exited
                            break
                        if os.name == "nt":
                            ready = []
                            for stream in list(streams):
                                available = _windows_available(stream)
                                if available is None or available:
                                    ready.append((stream, available or 0))
                            if not ready:
                                if exited:
                                    break
                                time.sleep(min(0.005, remaining))
                                continue
                        else:
                            events = selector.select(
                                0 if exited else min(0.05, remaining)
                            )
                            if not events and exited:
                                break
                            ready = [
                                # Only these owned binary streams were registered.
                                (cast(IO[bytes], key.fileobj), _READ_BYTES)
                                for key, _ in events
                            ]
                        for stream, available in ready:
                            channel = streams[stream]
                            try:
                                raw = os.read(
                                    stream.fileno(), min(_READ_BYTES, available)
                                )
                            except BlockingIOError:
                                continue
                            if raw:
                                capture.feed(channel, raw)
                            else:
                                if os.name != "nt":
                                    selector.unregister(stream)
                                stream.close()
                                del streams[stream]
                if timed_out:
                    process.kill()
                process.wait()
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait()
                for stream in streams:
                    stream.close()
                for channel in ("stdout", "stderr"):
                    capture.feed(channel, b"", final=True)
            selected = capture.timeout if timed_out else capture.normal
            suffix = (
                f"Subprocess exceeded {timeout_seconds}s timeout."
                if timed_out and timeout_message
                else ""
            )
            stdout, stderr = selected.logs(suffix)
            return CapturedProcess(
                process.returncode,
                timed_out,
                stdout,
                stderr,
                selected.overrun,
                stdout_truncated=selected.truncated["stdout"],
                stderr_truncated=selected.truncated["stderr"],
            )


def publish_png(png_bytes: bytes, prefix: str) -> str:
    """Publish one private unique regular PNG after descriptor write and close.

    Persistent temp lifetime belongs to the caller. Any failure removes only
    this newly created file; the caller maps OS errors to its existing envelope.
    """
    descriptor, name = tempfile.mkstemp(prefix=prefix, suffix=".png")
    try:
        output = os.fdopen(descriptor, "wb")
        # Ownership transferred; never close a reused descriptor after this.
        descriptor = -1
        with output:
            if not stat.S_ISREG(os.fstat(output.fileno()).st_mode):
                raise OSError("Template output is not a regular file")
            output.write(png_bytes)
        return os.path.abspath(name)
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        os.unlink(name)
        raise
