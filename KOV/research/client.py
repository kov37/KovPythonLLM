"""Bounded public page retrieval treating all content as untrusted evidence."""

from __future__ import annotations

import ipaddress
import socket
import urllib.parse

import httpx

from KOV.observations.compressor import CPRSCompressor, ReductionResult


class PublicResearchClient:
    def __init__(self, *, max_bytes: int = 1_000_000, timeout_seconds: float = 10) -> None:
        self.max_bytes = max_bytes
        self.timeout_seconds = timeout_seconds
        self.compressor = CPRSCompressor()

    def fetch(self, url: str, *, objective: str) -> ReductionResult:
        self._validate_public_url(url)
        with httpx.Client(follow_redirects=False, timeout=self.timeout_seconds) as client:
            response = client.get(url, headers={"User-Agent": "KOV-Research/0.1"})
            response.raise_for_status()
            if len(response.content) > self.max_bytes:
                raise ValueError("Research response exceeds protected byte limit")
            media_type = response.headers.get("content-type", "")
            if not any(kind in media_type for kind in ("text/", "json", "xml")):
                raise ValueError("Research client accepts text evidence only")
            return self.compressor.compress(response.text, objective=objective)

    @staticmethod
    def _validate_public_url(url: str) -> None:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise PermissionError("Research URLs must be credential-free HTTPS URLs")
        addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if not ip.is_global:
                raise PermissionError("Research URL resolves to a non-public address")
