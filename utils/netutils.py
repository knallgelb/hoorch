"""
Small network utility helpers for checking Internet connectivity.

Provides:
- check_host_port(host, port, timeout=3) -> bool
- has_internet(timeout=3, hosts=None, use_http=False, http_url='https://example.com') -> bool

By default `has_internet` attempts to open a TCP connection to a few public DNS servers
(on port 53). Optionally it can fall back to doing an HTTP(S) request (useful if DNS/TCP
53 is blocked but HTTP(S) works).

The functions are intentionally simple and return booleans only. They log debug/info
messages using the module logger.
"""

from __future__ import annotations

import logging
import socket
import urllib.error
import urllib.request
from typing import Iterable, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_HOSTS: Tuple[Tuple[str, int], ...] = (
    ("8.8.8.8", 53),
    ("1.1.1.1", 53),
    ("8.8.4.4", 53),
)


def check_host_port(host: str, port: int, timeout: float = 3.0) -> bool:
    """
    Try to open a TCP connection to host:port with the given timeout.

    Returns True on success, False on failure.
    """
    try:
        logger.debug(
            "Attempting TCP connect to %s:%s (timeout=%s)", host, port, timeout
        )
        with socket.create_connection((host, port), timeout):
            logger.debug("TCP connect to %s:%s succeeded", host, port)
            return True
    except OSError as e:
        logger.debug("TCP connect to %s:%s failed: %s", host, port, e)
        return False


def has_internet(
    timeout: float = 3.0,
    hosts: Optional[Iterable[Tuple[str, int]]] = None,
    use_http: bool = False,
    http_url: str = "https://example.com",
) -> bool:
    """
    Check for general Internet connectivity.

    Strategy:
    1. Try to open a short-lived TCP connection to one of the configured hosts (default
       public DNS servers) on the given port(s). This is fast and avoids DNS/HTTP stack.
    2. Optionally, if `use_http` is True or TCP checks fail, try a simple HTTP GET to
       `http_url` using urllib (with the same timeout).

    Parameters:
      timeout -- socket / HTTP timeout in seconds (float)
      hosts -- iterable of (host, port) pairs to try; if None, a small built-in list is used
      use_http -- if True, attempt an HTTP request when TCP checks fail (or immediately)
      http_url -- URL to request for the HTTP connectivity check

    Returns:
      True if connectivity appears to be working, False otherwise.
    """
    if hosts is None:
        hosts_to_try = DEFAULT_HOSTS
    else:
        hosts_to_try = tuple(hosts)

    logger.debug(
        "has_internet start: timeout=%s hosts=%s use_http=%s",
        timeout,
        hosts_to_try,
        use_http,
    )

    # First, try host:port TCP checks
    for host, port in hosts_to_try:
        if check_host_port(host, port, timeout=timeout):
            logger.info(
                "Internet connectivity detected via TCP to %s:%s", host, port
            )
            return True

    # If requested, try an HTTP(S) request as a fallback
    if use_http:
        try:
            logger.debug(
                "Attempting HTTP request to %s (timeout=%s)", http_url, timeout
            )
            req = urllib.request.Request(
                http_url, headers={"User-Agent": "hoorch-netutils/1.0"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                # Consider any 2xx or 3xx as success
                status = (
                    getattr(resp, "status", None)
                    or getattr(resp, "getcode", lambda: None)()
                )
                logger.debug(
                    "HTTP request to %s returned status %s", http_url, status
                )
                if status is None:
                    # If status is not available, consider it success since no exception was raised.
                    logger.info(
                        "Internet connectivity detected via HTTP to %s",
                        http_url,
                    )
                    return True
                if 200 <= int(status) < 400:
                    logger.info(
                        "Internet connectivity detected via HTTP to %s (status=%s)",
                        http_url,
                        status,
                    )
                    return True
        except urllib.error.URLError as e:
            logger.debug("HTTP request to %s failed: %s", http_url, e)
        except Exception as e:
            logger.debug(
                "Unexpected error during HTTP connectivity check to %s: %s",
                http_url,
                e,
            )

    logger.info("No Internet connectivity detected")
    return False


__all__ = ["check_host_port", "has_internet"]
