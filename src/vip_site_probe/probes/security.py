"""check_security -- common WordPress security exposure checks."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

import httpx

from vip_site_probe.cache import cache

HTTP_TIMEOUT = 10.0

SECURITY_HEADERS = [
    "strict-transport-security",
    "x-content-type-options",
    "x-frame-options",
    "content-security-policy",
    "referrer-policy",
    "permissions-policy",
]


async def check_security(url: str) -> dict[str, Any]:
    """Run security exposure checks against a WordPress site."""
    parsed = urlparse(url)
    if not parsed.scheme:
        url = f"https://{url}"
        parsed = urlparse(url)

    base = f"{parsed.scheme}://{parsed.netloc}"
    findings: list[dict[str, str]] = []

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=HTTP_TIMEOUT,
        headers={"User-Agent": "VIP-Site-Probe/0.1"},
    ) as client:
        # -- security headers on the home page --
        try:
            home_resp = await client.get(base)
            _check_security_headers(home_resp, findings)
            _check_wp_version_meta(home_resp.text, findings)
            _check_cors(home_resp, findings)
        except httpx.HTTPError:
            findings.append({
                "severity": "warning",
                "label": "Home page unreachable",
                "detail": "Could not fetch home page for header analysis.",
            })

        # -- xmlrpc.php --
        await _check_xmlrpc(client, base, findings)

        # -- user enumeration via REST API --
        await _check_user_enum_rest(client, base, findings)

        # -- user enumeration via ?author=1 --
        await _check_user_enum_author(client, base, findings)

        # -- login page exposure --
        await _check_login_page(client, base, findings)

        # -- directory listing --
        await _check_directory_listing(client, base, findings)

    result: dict[str, Any] = {"url": base, "findings": findings}
    cache.store("check_security", base, result)
    return result


def _check_security_headers(resp: httpx.Response, findings: list[dict[str, str]]) -> None:
    """Check for presence of key security headers."""
    for header in SECURITY_HEADERS:
        if header in resp.headers:
            findings.append({
                "severity": "info",
                "label": f"{header} present",
                "detail": resp.headers[header],
            })
        else:
            findings.append({
                "severity": "warning",
                "label": f"{header} missing",
                "detail": "This security header is not set.",
            })


def _check_wp_version_meta(html: str, findings: list[dict[str, str]]) -> None:
    """Check if WP version is exposed in the HTML meta generator tag."""
    match = re.search(r'<meta\s+name="generator"\s+content="WordPress\s+([\d.]+)"', html)
    if match:
        findings.append({
            "severity": "warning",
            "label": "WordPress version exposed",
            "detail": f"Version {match.group(1)} found in meta generator tag.",
        })


def _check_cors(resp: httpx.Response, findings: list[dict[str, str]]) -> None:
    """Check CORS configuration."""
    origin = resp.headers.get("access-control-allow-origin")
    if origin:
        severity = "warning" if origin == "*" else "info"
        findings.append({
            "severity": severity,
            "label": "CORS: Access-Control-Allow-Origin",
            "detail": origin,
        })


async def _check_xmlrpc(
    client: httpx.AsyncClient, base: str, findings: list[dict[str, str]]
) -> None:
    """Check if xmlrpc.php is accessible."""
    try:
        resp = await client.post(f"{base}/xmlrpc.php", content="<methodCall/>")
        if resp.status_code == 200 and "xml" in resp.headers.get("content-type", ""):
            findings.append({
                "severity": "warning",
                "label": "xmlrpc.php accessible",
                "detail": "Potential brute-force / DDoS vector.",
            })
        else:
            findings.append({
                "severity": "info",
                "label": "xmlrpc.php blocked or not found",
                "detail": f"HTTP {resp.status_code}",
            })
    except httpx.HTTPError:
        findings.append({
            "severity": "info",
            "label": "xmlrpc.php unreachable",
            "detail": "Could not connect.",
        })


async def _check_user_enum_rest(
    client: httpx.AsyncClient, base: str, findings: list[dict[str, str]]
) -> None:
    """Check user enumeration via REST API."""
    try:
        resp = await client.get(f"{base}/wp-json/wp/v2/users")
        if resp.status_code == 200:
            users = resp.json()
            if isinstance(users, list) and users:
                names = [u.get("slug", "?") for u in users[:5]]
                findings.append({
                    "severity": "warning",
                    "label": "User enumeration via REST API",
                    "detail": f"Found {len(users)} user(s): {', '.join(names)}",
                })
            else:
                findings.append({
                    "severity": "info",
                    "label": "REST API users endpoint returns empty",
                    "detail": "No users exposed.",
                })
        else:
            findings.append({
                "severity": "info",
                "label": "REST API users endpoint blocked",
                "detail": f"HTTP {resp.status_code}",
            })
    except httpx.HTTPError:
        pass


async def _check_user_enum_author(
    client: httpx.AsyncClient, base: str, findings: list[dict[str, str]]
) -> None:
    """Check user enumeration via ?author=1 redirect."""
    try:
        resp = await client.get(f"{base}/?author=1")
        if resp.status_code == 200 and "/author/" in str(resp.url):
            author = str(resp.url).split("/author/")[-1].strip("/")
            findings.append({
                "severity": "warning",
                "label": "User enumeration via ?author=1",
                "detail": f"Redirected to /author/{author}",
            })
    except httpx.HTTPError:
        pass


async def _check_login_page(
    client: httpx.AsyncClient, base: str, findings: list[dict[str, str]]
) -> None:
    """Check if the login page is publicly reachable."""
    try:
        resp = await client.get(f"{base}/wp-login.php")
        if resp.status_code == 200:
            findings.append({
                "severity": "info",
                "label": "Login page reachable",
                "detail": "wp-login.php returns 200.",
            })
    except httpx.HTTPError:
        pass


async def _check_directory_listing(
    client: httpx.AsyncClient, base: str, findings: list[dict[str, str]]
) -> None:
    """Check for directory listing on common paths."""
    paths = ["/wp-content/uploads/", "/wp-content/plugins/"]
    for path in paths:
        try:
            resp = await client.get(f"{base}{path}")
            if resp.status_code == 200 and "<title>Index of" in resp.text:
                findings.append({
                    "severity": "critical",
                    "label": f"Directory listing enabled: {path}",
                    "detail": "Server returns a directory index.",
                })
        except httpx.HTTPError:
            pass
