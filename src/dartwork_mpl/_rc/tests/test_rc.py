"""The rcParams lock is a plain, non-reentrant lock shared by every writer."""

import threading

from dartwork_mpl._rc import rc_lock


def test_rc_lock_is_a_non_reentrant_lock() -> None:
    """A second acquire from the holder fails: writers cannot nest by accident."""
    assert type(rc_lock) is type(threading.Lock())
    with rc_lock:
        assert not rc_lock.acquire(blocking=False)
