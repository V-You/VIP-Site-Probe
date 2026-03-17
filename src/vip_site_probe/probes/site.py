"""probe_site -- full site diagnostic via WordPress REST API and HTTP headers."""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlparse

import httpx

from vip_site_probe.cache import cache

HTTP_TIMEOUT = 10.0

# headers that reveal infrastructure signals
INFRA_HEADERS = [
    "x-cache",
    "cache-control",
    "x-served-by",
    "vary",
    "x-hacker",
    "cf-ray",
    "x-fastly-request-id",
    "x-ac",
    "x-akamai-transformed",
]

SECURITY_HEADERS = [
    "strict-transport-security",
    "x-content-type-options",
    "x-frame-options",
    "content-security-policy",
    "referrer-policy",
    "permissions-policy",
]

CDN_INDICATORS: dict[str, str] = {
    "cf-ray": "Cloudflare",
    "x-fastly-request-id": "Fastly",
    "x-ac": "Automattic",
    "x-akamai-transformed": "Akamai",
}


async def probe_site(url: str) -> dict[str, Any]:
    """Probe a WordPress site and return structured diagnostic data."""
    parsed = urlparse(url)
    if not parsed.scheme:
        url = f"https://{url}"
        parsed = urlparse(url)

    base = f"{parsed.scheme}://{parsed.netloc}"
    result: dict[str, Any] = {"url": base}

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=HTTP_TIMEOUT,
        headers={"User-Agent": "VIP-Site-Probe/0.1"},
    ) as client:
        # -- fetch the home page for headers and timing --
        start = time.monotonic()
        try:
            home_resp = await client.get(base)
            ttfb = round(time.monotonic() - start, 3)
        except httpx.HTTPError as exc:
            result["error"] = f"Failed to reach site: {exc}"
            cache.store("probe_site", base, result)
            return result

        result["identity"] = {}
        result["infrastructure"] = _extract_infra(home_resp, ttfb)
        result["cdn"] = _detect_cdn(home_resp)
        result["rest_api"] = {}
        result["content"] = {}

        # -- fetch /wp-json/ for REST API index --
        try:
            api_resp = await client.get(f"{base}/wp-json/")
            if api_resp.status_code == 200:
                api_data = api_resp.json()
                result["identity"] = _extract_identity(api_data)
                result["rest_api"] = _extract_rest_api(api_data)
                result["content"] = _extract_content(api_data)
            else:
                result["rest_api"]["status"] = f"HTTP {api_resp.status_code}"
        except (httpx.HTTPError, ValueError):
            result["rest_api"]["status"] = "unreachable"

    cache.store("probe_site", base, result)
    return result


def _extract_infra(resp: httpx.Response, ttfb: float) -> dict[str, Any]:
    """Pull infrastructure signals from response headers."""
    infra: dict[str, Any] = {"ttfb_seconds": ttfb, "http_version": resp.http_version}
    for header in INFRA_HEADERS:
        val = resp.headers.get(header)
        if val:
            infra[header] = val
    return infra


def _detect_cdn(resp: httpx.Response) -> list[str]:
    """Detect CDN providers from response headers."""
    found = []
    for header, name in CDN_INDICATORS.items():
        if header in resp.headers:
            found.append(name)
    return found


def _extract_identity(api_data: dict[str, Any]) -> dict[str, Any]:
    """Extract site identity from the WP REST API index."""
    return {
        "name": api_data.get("name", ""),
        "description": api_data.get("description", ""),
        "url": api_data.get("url", ""),
        "home": api_data.get("home", ""),
        "gmt_offset": api_data.get("gmt_offset"),
        "timezone_string": api_data.get("timezone_string", ""),
    }


def _extract_rest_api(api_data: dict[str, Any]) -> dict[str, Any]:
    """Extract REST API metadata -- namespaces and auth methods."""
    return {
        "status": "reachable",
        "namespaces": api_data.get("namespaces", []),
        "authentication": api_data.get("authentication", {}),
    }


def _extract_content(api_data: dict[str, Any]) -> dict[str, Any]:
    """Extract content summary from API index routes."""
    routes = api_data.get("routes", {})
    return {
        "route_count": len(routes),
    }
