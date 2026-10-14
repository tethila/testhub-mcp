"""SSRF 防护单测（不依赖外网）。"""
import socket

import pytest

from security import UnsafeUrlError, is_blocked_ip, validate_url


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",
        "10.0.0.5",
        "172.16.3.4",
        "192.168.1.1",
        "169.254.169.254",  # 云元数据
        "0.0.0.0",
        "100.64.0.1",
        "::1",
        "fc00::1",
        "fe80::1",
    ],
)
def test_blocked_ips(ip):
    assert is_blocked_ip(ip) is True


@pytest.mark.parametrize("ip", ["8.8.8.8", "1.1.1.1", "93.184.216.34", "2606:4700::1111"])
def test_public_ips_ok(ip):
    assert is_blocked_ip(ip) is False


def test_unparsable_ip_treated_as_blocked():
    assert is_blocked_ip("not-an-ip") is True


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.com", "gopher://x", "", "   "])
def test_bad_scheme_or_empty_rejected(url):
    with pytest.raises(UnsafeUrlError):
        validate_url(url)


def test_loopback_literal_rejected():
    with pytest.raises(UnsafeUrlError):
        validate_url("http://127.0.0.1/")


def test_metadata_endpoint_rejected():
    with pytest.raises(UnsafeUrlError):
        validate_url("http://169.254.169.254/latest/meta-data/")


def test_private_literal_rejected():
    with pytest.raises(UnsafeUrlError):
        validate_url("http://192.168.1.1/admin")


def test_public_host_ok(monkeypatch):
    def fake_getaddrinfo(host, port, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    assert validate_url("https://example.com/page") == "https://example.com/page"


def test_domain_resolving_to_private_rejected(monkeypatch):
    def fake_getaddrinfo(host, port, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.1.2.3", port))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    with pytest.raises(UnsafeUrlError):
        validate_url("http://evil.example.com/")


def test_any_bad_record_rejects(monkeypatch):
    """多记录里只要有一条是内网 → 拒绝。"""

    def fake_getaddrinfo(host, port, **kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port)),
        ]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    with pytest.raises(UnsafeUrlError):
        validate_url("http://mixed.example.com/")
