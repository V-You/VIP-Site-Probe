"""probe -- combined site, plugin, and security diagnostic."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from vip_site_probe.probes.plugins import check_plugins
from vip_site_probe.probes.security import check_security
from vip_site_probe.probes.site import probe_site


async def probe(url: str) -> dict[str, Any]:
    """Run the full probe sequence and cache a combined report."""
    parsed = urlparse(url)
    if not parsed.scheme:
        url = f"https://{url}"

    site_health = await probe_site(url)
    plugin_status = await check_plugins(url)
    security_findings = await check_security(url)

    report_url = _pick_report_url(url, site_health, plugin_status, security_findings)
    result = {
        "url": report_url,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "site_health": site_health,
        "plugin_status": plugin_status,
        "security_findings": security_findings,
    }
    return result


def _pick_report_url(url: str, *results: dict[str, Any]) -> str:
    """Choose the normalized URL from the combined results when available."""
    for result in results:
        candidate = result.get("url")
        if isinstance(candidate, str) and candidate:
            return candidate
    return url
