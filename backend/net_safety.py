"""
SSRF guard shared by URL validation, the fetch chain and the GEO checks.

An address is public only when ipaddress calls it global: this rejects private,
loopback, link-local (cloud metadata), CGNAT 100.64/10, unique-local fc00::/7,
documentation and reserved ranges. IPv4-mapped IPv6 (::ffff:127.0.0.1) is
judged by the IPv4 address inside it.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import requests


_NAT64_NET = ipaddress.ip_network("64:ff9b::/96")
_V6_NEVER_PUBLIC = (ipaddress.ip_network("::/96"), ipaddress.ip_network("fec0::/10"))


class HostLookupError(Exception):
    """The host name could not be resolved."""


def is_public_ip(addr: str) -> bool:
    try:
        ip = ipaddress.ip_address(str(addr).split("%")[0])
    except ValueError:
        return False
    if ip.version == 6:
        if ip.ipv4_mapped is not None:
            ip = ip.ipv4_mapped
        elif ip in _NAT64_NET:                       # 64:ff9b::a.b.c.d reaches a.b.c.d via NAT64
            ip = ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)
        elif ip.sixtofour is not None or ip.teredo is not None or any(ip in n for n in _V6_NEVER_PUBLIC):
            return False                             # 6to4/Teredo tunnels, IPv4-compatible, site-local
    return ip.is_global and not ip.is_multicast


def host_is_public(host: str) -> bool:
    """True only if every address `host` resolves to (all families) is public.

    Raises HostLookupError when the name can't be resolved, so callers can fail closed.
    """
    host = (host or "").strip("[]")
    if not host:
        return False
    try:
        ipaddress.ip_address(host.split("%")[0])
        return is_public_ip(host)          # a literal address needs no lookup
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(host, None)
    except (OSError, UnicodeError) as exc:
        raise HostLookupError(host) from exc
    if not infos:
        raise HostLookupError(host)
    return all(is_public_ip(info[4][0]) for info in infos)


def url_hosts(url: str) -> set:
    """Host names of `url` as urllib.parse AND as urllib3 (what requests connects to) read it.

    They can disagree: for "http://127.0.0.1\\@example.com/" urlparse says example.com
    but requests connects to 127.0.0.1. Checking both closes that parser gap.
    """
    hosts = {(urlparse(url).hostname or "")}
    try:
        from urllib3.util import parse_url
        hosts.add((parse_url(url).host or "").strip("[]").lower())
    except Exception:
        hosts.add("")                                # unparseable for requests: not public
    return hosts


def url_hosts_public(url: str) -> bool:
    """True only if every host reading of `url` is public. Raises HostLookupError on lookup failure."""
    return all(host_is_public(h) for h in url_hosts(url))


def url_is_public(url: str) -> bool:
    """True if the URL is http(s) and its host is public; False on lookup failure."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    try:
        return url_hosts_public(url)
    except HostLookupError:
        return False


def safe_get(url: str, max_bytes: int = 500_000, max_hops: int = 5, timeout: int = 10, headers=None):
    """GET that re-checks every redirect hop against private addresses.

    Returns the final requests.Response (body capped at max_bytes, readable via
    .text/.content), or None when any hop is private, unresolvable or there are
    too many redirects. Network errors propagate to the caller.
    """
    current = url
    for _ in range(max_hops + 1):
        if not url_is_public(current):
            return None
        resp = requests.get(current, headers=headers, timeout=timeout, allow_redirects=False, stream=True)
        if resp.is_redirect:
            location = resp.headers.get("Location", "")
            resp.close()
            if not location:
                return None
            current = urljoin(current, location)
            continue
        raw = b""
        for chunk in resp.iter_content(chunk_size=65536):
            raw += chunk
            if len(raw) >= max_bytes:
                raw = raw[:max_bytes]
                break
        resp.close()
        resp._content = raw
        resp._content_consumed = True
        resp.url = current
        return resp
    return None


def visitor_bucket(ip: str) -> str:
    """One visitor = one IPv4 address or one IPv6 /64 (a single host usually owns a
    whole /64, so counting full IPv6 addresses would let one machine rotate forever)."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return ip
    if addr.version == 6:
        if addr.ipv4_mapped is not None:
            return str(addr.ipv4_mapped)
        return str(ipaddress.ip_network(f"{addr}/64", strict=False))
    return str(addr)
