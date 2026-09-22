"""The network guard must actually block. A guard that silently passes is worse than none.

These tests exist because the autouse fixture in `conftest.py` protects the whole suite:
if it stopped working, every other test would keep passing and §9.5 would be unenforced.
"""

from __future__ import annotations

import socket

import pytest

from .support.netguard import NetworkAccessBlocked


def test_connect_is_blocked() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with pytest.raises(NetworkAccessBlocked):
        sock.connect(("example.invalid", 80))


def test_connect_ex_is_blocked() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with pytest.raises(NetworkAccessBlocked):
        sock.connect_ex(("example.invalid", 80))


def test_create_connection_is_blocked() -> None:
    with pytest.raises(NetworkAccessBlocked):
        socket.create_connection(("example.invalid", 80), timeout=0.01)


def test_name_resolution_is_blocked() -> None:
    """DNS counts. A tool that resolves a name is a tool that was about to connect."""
    with pytest.raises(NetworkAccessBlocked):
        socket.getaddrinfo("example.invalid", 80)
    with pytest.raises(NetworkAccessBlocked):
        socket.gethostbyname("example.invalid")


def test_urllib_is_blocked_through_the_socket_layer() -> None:
    """Guarding sockets covers every HTTP client, not just the ones we thought of."""
    import urllib.error
    import urllib.request

    with pytest.raises((NetworkAccessBlocked, urllib.error.URLError)):
        urllib.request.urlopen("http://example.invalid/", timeout=0.01)


def test_specctl_imports_no_network_client() -> None:
    """Importing the package must not pull in an HTTP client or an LLM SDK."""
    import importlib
    import sys

    for module in [m for m in sys.modules if m.startswith("specctl")]:
        del sys.modules[module]
    importlib.import_module("specctl.cli")
    forbidden = {"requests", "httpx", "aiohttp", "urllib3", "anthropic", "openai"}
    leaked = forbidden & set(sys.modules)
    assert not leaked, f"specctl.cli pulled in network clients: {sorted(leaked)}"


def test_unix_sockets_still_work(tmp_path) -> None:
    """A local socket is not the network; blocking it would protect nothing."""
    path = str(tmp_path / "s")
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(path)
    server.listen(1)
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.connect(path)  # must not raise
    client.close()
    server.close()
