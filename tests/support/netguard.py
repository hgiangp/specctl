"""Block every network call, so that "no network" is a fact rather than an intention.

§9.5 requires that `specctl` make no network call, and says why: *this is what makes
DEC-03 mechanically testable — with no network there is no LLM in the ingest path,
whatever the code appears to do.* A contractual document must not have a sentence in it
that came from a model instead of from the source file.

The guard is installed for the **whole** suite (see `tests/conftest.py`), not just for
tests that think about it. A dependency added later reaches the network exactly once
before a test fails.

AF_UNIX is left alone: a local socket is not the network, and blocking it would break
tooling without protecting anything.
"""

from __future__ import annotations

import socket
from contextlib import contextmanager
from typing import Iterator


class NetworkAccessBlocked(RuntimeError):
    """Raised when code under test tries to reach the network."""


def _refuse(what: str, detail: object = "") -> NetworkAccessBlocked:
    suffix = f" ({detail})" if detail else ""
    return NetworkAccessBlocked(
        f"network access is blocked in tests: {what}{suffix}. "
        "specctl must make no network call (§9.5)."
    )


@contextmanager
def blocked_network() -> Iterator[None]:
    """Patch the socket entry points that reach outside this machine."""
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_create = socket.create_connection
    real_getaddrinfo = socket.getaddrinfo
    real_gethostbyname = socket.gethostbyname

    def guard_connect(self: socket.socket, address: object, *args: object) -> object:
        if self.family == socket.AF_UNIX:
            return real_connect(self, address, *args)  # type: ignore[arg-type]
        raise _refuse("socket.connect", address)

    def guard_connect_ex(self: socket.socket, address: object, *args: object) -> object:
        if self.family == socket.AF_UNIX:
            return real_connect_ex(self, address, *args)  # type: ignore[arg-type]
        raise _refuse("socket.connect_ex", address)

    def guard_create(address: object, *args: object, **kwargs: object) -> object:
        raise _refuse("socket.create_connection", address)

    def guard_getaddrinfo(host: object, port: object, *args: object, **kwargs: object) -> object:
        raise _refuse("socket.getaddrinfo", host)

    def guard_gethostbyname(host: object) -> object:
        raise _refuse("socket.gethostbyname", host)

    socket.socket.connect = guard_connect  # type: ignore[method-assign]
    socket.socket.connect_ex = guard_connect_ex  # type: ignore[method-assign]
    socket.create_connection = guard_create  # type: ignore[assignment]
    socket.getaddrinfo = guard_getaddrinfo  # type: ignore[assignment]
    socket.gethostbyname = guard_gethostbyname  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket.connect = real_connect  # type: ignore[method-assign]
        socket.socket.connect_ex = real_connect_ex  # type: ignore[method-assign]
        socket.create_connection = real_create  # type: ignore[assignment]
        socket.getaddrinfo = real_getaddrinfo  # type: ignore[assignment]
        socket.gethostbyname = real_gethostbyname  # type: ignore[assignment]
