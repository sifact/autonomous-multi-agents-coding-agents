"""Fixture that makes any non-loopback network access fail the test loudly."""
import ipaddress
import socket

import pytest

_LOOPBACK_NAMES = {"localhost", "localhost.localdomain", "ip6-localhost"}


def _is_loopback(host) -> bool:
    if isinstance(host, bytes):
        host = host.decode()
    if host in (None, ""):
        return True
    if host in _LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(str(host).split("%")[0]).is_loopback
    except ValueError:
        return False


@pytest.fixture
def no_external_network(monkeypatch):
    real_getaddrinfo = socket.getaddrinfo
    real_connect, real_connect_ex = socket.socket.connect, socket.socket.connect_ex

    def getaddrinfo(host, *args, **kwargs):
        if not _is_loopback(host):
            raise AssertionError(f"test tried to resolve a non-loopback host: {host!r}")
        return real_getaddrinfo(host, *args, **kwargs)

    def guard(real):
        def connect(self, address, *args):
            if isinstance(address, tuple) and not _is_loopback(address[0]):
                raise AssertionError(f"test tried to connect to {address[0]!r}")
            return real(self, address, *args)
        return connect

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket.socket, "connect", guard(real_connect))
    monkeypatch.setattr(socket.socket, "connect_ex", guard(real_connect_ex))
