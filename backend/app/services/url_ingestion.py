import ipaddress
import socket
from pathlib import Path
from typing import Tuple
from urllib.parse import urlparse
import httpx

from app.core.config import settings
from app.core.errors import AppException

FORBIDDEN_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("255.255.255.255/32"),
    # IPv6
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("::/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("::ffff:0:0/96"),
]

def is_ip_forbidden(ip_str: str) -> bool:
    try:
        ip_obj = ipaddress.ip_address(ip_str)
        if ip_obj.is_loopback or ip_obj.is_private or ip_obj.is_link_local or ip_obj.is_multicast or ip_obj.is_reserved:
            return True
        for net in FORBIDDEN_NETWORKS:
            if ip_obj in net:
                return True
        return False
    except ValueError:
        return True

def validate_url_safety(target_url: str) -> Tuple[str, str]:
    """
    Validate that target_url uses http/https and does not resolve to private,
    loopback, or link-local network addresses.
    Returns (hostname, scheme).
    """
    parsed = urlparse(target_url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise AppException(
            code="UNSUPPORTED_URL_SCHEME",
            message=f"URL scheme '{parsed.scheme}' is unsupported. Only 'http' and 'https' are allowed.",
            status_code=400
        )

    hostname = parsed.hostname
    if not hostname:
        raise AppException(
            code="INVALID_URL",
            message="Provided URL is missing a valid host name.",
            status_code=400
        )

    # Check literal IP in hostname
    try:
        ip_obj = ipaddress.ip_address(hostname)
        if is_ip_forbidden(str(ip_obj)):
            raise AppException(
                code="SSRF_BLOCKED",
                message="Access to private, loopback, or internal network addresses is prohibited.",
                status_code=400
            )
    except ValueError:
        # Not a raw IP literal; resolve DNS
        try:
            port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
            addr_info = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
            if not addr_info:
                raise AppException(
                    code="HOST_UNRESOLVABLE",
                    message=f"Failed to resolve hostname '{hostname}'.",
                    status_code=400
                )
            for item in addr_info:
                ip_resolved = item[4][0]
                if is_ip_forbidden(ip_resolved):
                    raise AppException(
                        code="SSRF_BLOCKED",
                        message=f"Destination address '{hostname}' resolves to forbidden private/internal IP.",
                        status_code=400
                    )
        except AppException:
            raise
        except Exception as e:
            raise AppException(
                code="DNS_RESOLUTION_FAILED",
                message=f"Could not resolve host '{hostname}': {str(e)}",
                status_code=400
            )

    return hostname, parsed.scheme.lower()

async def download_media_from_url(source_url: str, dest_path: Path) -> Path:
    """
    Safely download media from a validated URL with redirect verification and streaming size enforcement.
    """
    current_url = source_url
    max_redirects = 5

    async with httpx.AsyncClient(timeout=settings.URL_FETCH_TIMEOUT_SECONDS, follow_redirects=False) as client:
        for _ in range(max_redirects):
            validate_url_safety(current_url)

            # Send streaming GET request
            req = client.build_request("GET", current_url)
            resp = await client.send(req, stream=True)

            if resp.status_code in (301, 302, 303, 307, 308):
                location = resp.headers.get("Location")
                await resp.aclose()
                if not location:
                    raise AppException(code="INVALID_REDIRECT", message="Redirect missing Location header.", status_code=400)
                # Resolve relative redirect URLs if needed
                from urllib.parse import urljoin
                current_url = urljoin(current_url, location)
                continue

            if resp.status_code >= 400:
                await resp.aclose()
                raise AppException(
                    code="DOWNLOAD_FAILED",
                    message=f"Remote server returned HTTP {resp.status_code}.",
                    status_code=400
                )

            # Check Content-Length if provided
            content_length = resp.headers.get("Content-Length")
            if content_length and int(content_length) > settings.MAX_URL_DOWNLOAD_SIZE_BYTES:
                await resp.aclose()
                raise AppException(
                    code="PAYLOAD_TOO_LARGE",
                    message=f"Remote media size exceeds limit of {settings.MAX_URL_DOWNLOAD_SIZE_BYTES // (1024 * 1024)} MB.",
                    status_code=413
                )

            # Stream download to dest_path
            bytes_downloaded = 0
            with open(dest_path, "wb") as f:
                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    bytes_downloaded += len(chunk)
                    if bytes_downloaded > settings.MAX_URL_DOWNLOAD_SIZE_BYTES:
                        await resp.aclose()
                        if dest_path.exists():
                            dest_path.unlink(missing_ok=True)
                        raise AppException(
                            code="PAYLOAD_TOO_LARGE",
                            message=f"Downloaded file exceeded maximum allowed size of {settings.MAX_URL_DOWNLOAD_SIZE_BYTES // (1024 * 1024)} MB.",
                            status_code=413
                        )
                    f.write(chunk)
            await resp.aclose()
            return dest_path

        raise AppException(code="TOO_MANY_REDIRECTS", message="Too many HTTP redirects encountered.", status_code=400)
