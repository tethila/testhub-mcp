"""
security.py · SSRF 防护（公共工具必备）

规则：
  · 只允许 http / https
  · 域名解析出的**任一** IP 落在内网/保留网段 → 拒绝
  · 覆盖云元数据地址（169.254.169.254）、回环、私有段、链路本地、组播等

无第三方依赖，可单测。
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

# 禁止访问的网段（含 IPv4 / IPv6）
BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),        # 本网络
    ipaddress.ip_network("10.0.0.0/8"),       # 私有
    ipaddress.ip_network("100.64.0.0/10"),    # CGNAT
    ipaddress.ip_network("127.0.0.0/8"),      # 回环
    ipaddress.ip_network("169.254.0.0/16"),   # 链路本地（含 169.254.169.254 云元数据）
    ipaddress.ip_network("172.16.0.0/12"),    # 私有
    ipaddress.ip_network("192.0.0.0/24"),     # IETF 协议
    ipaddress.ip_network("192.168.0.0/16"),   # 私有
    ipaddress.ip_network("198.18.0.0/15"),    # 基准测试
    ipaddress.ip_network("224.0.0.0/4"),      # 组播
    ipaddress.ip_network("240.0.0.0/4"),      # 保留
    ipaddress.ip_network("::1/128"),          # IPv6 回环
    ipaddress.ip_network("fc00::/7"),         # IPv6 唯一本地
    ipaddress.ip_network("fe80::/10"),        # IPv6 链路本地
]

ALLOWED_SCHEMES = ("http", "https")


class UnsafeUrlError(ValueError):
    """URL 未通过安全策略。"""


def is_blocked_ip(ip: str) -> bool:
    """判断单个 IP 是否落在禁止网段。"""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True  # 解析不出来 → 一律当不安全
    return any(addr in net for net in BLOCKED_NETWORKS)


def validate_url(url: str) -> str:
    """校验 URL 安全性，通过则原样返回，否则抛 UnsafeUrlError。"""
    if not url or not isinstance(url, str):
        raise UnsafeUrlError("URL 为空")

    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsafeUrlError(f"只允许 http/https，收到：{parsed.scheme or '(空)'}")
    if not parsed.hostname:
        raise UnsafeUrlError("缺少主机名")

    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)

    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UnsafeUrlError(f"域名解析失败：{host}") from exc

    if not infos:
        raise UnsafeUrlError(f"域名无解析结果：{host}")

    for info in infos:
        ip = info[4][0]
        if is_blocked_ip(ip):
            raise UnsafeUrlError(f"目标解析到内网/保留地址，已拦截：{host} -> {ip}")

    return url
