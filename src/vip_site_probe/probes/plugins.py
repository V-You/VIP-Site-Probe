"""check_plugins -- discover plugins via REST API namespaces and cross-reference wordpress.org."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

import httpx

from vip_site_probe.cache import cache

HTTP_TIMEOUT = 10.0

# known namespace-to-plugin-slug mappings
NAMESPACE_PLUGIN_MAP: dict[str, str] = {
    "jetpack": "jetpack",
    "jp": "jetpack",
    "wc": "woocommerce",
    "yoast": "wordpress-seo",
    "wp-parsely": "developer-tools",
    "acf": "advanced-custom-fields",
    "redirection": "redirection",
    "contact-form-7": "contact-form-7",
    "wpcom": "jetpack",
    "wp-graphql": "wp-graphql",
    "tribe": "the-events-calendar",
    "relevanssi": "relevanssi",
}

WP_ORG_API = "https://api.wordpress.org/plugins/info/1.2/"


async def check_plugins(url: str) -> dict[str, Any]:
    """Discover and analyze plugins for a WordPress site."""
    parsed = urlparse(url)
    if not parsed.scheme:
        url = f"https://{url}"
        parsed = urlparse(url)

    base = f"{parsed.scheme}://{parsed.netloc}"
    result: dict[str, Any] = {"url": base, "plugins": []}

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=HTTP_TIMEOUT,
        headers={"User-Agent": "VIP-Site-Probe/0.1"},
    ) as client:
        # get namespaces from REST API index
        namespaces: list[str] = []
        try:
            api_resp = await client.get(f"{base}/wp-json/")
            if api_resp.status_code == 200:
                namespaces = api_resp.json().get("namespaces", [])
        except (httpx.HTTPError, ValueError):
            result["error"] = "Could not reach REST API"
            cache.store("check_plugins", base, result)
            return result

        # map namespaces to plugin slugs
        discovered_slugs: dict[str, str] = {}
        for ns in namespaces:
            prefix = ns.split("/")[0] if "/" in ns else ns
            if prefix in NAMESPACE_PLUGIN_MAP:
                slug = NAMESPACE_PLUGIN_MAP[prefix]
                discovered_slugs[slug] = ns

        # also scan home page HTML for plugin version hints
        try:
            home_resp = await client.get(base)
            if home_resp.status_code == 200:
                _scan_html_for_plugins(home_resp.text, discovered_slugs)
        except httpx.HTTPError:
            pass

        # query wordpress.org for each discovered plugin
        for slug, namespace in discovered_slugs.items():
            plugin_info = await _fetch_plugin_info(client, slug)
            plugin_info["namespace"] = namespace
            result["plugins"].append(plugin_info)

    cache.store("check_plugins", base, result)
    return result


def _scan_html_for_plugins(html: str, slugs: dict[str, str]) -> None:
    """Scan HTML source for plugin references in script/style tags."""
    # look for /wp-content/plugins/{slug}/ patterns
    for match in re.finditer(r"/wp-content/plugins/([a-z0-9_-]+)/", html):
        found = match.group(1)
        if found not in slugs:
            slugs[found] = f"html:{found}"


async def _fetch_plugin_info(client: httpx.AsyncClient, slug: str) -> dict[str, Any]:
    """Fetch plugin details from the WordPress.org Plugin API."""
    info: dict[str, Any] = {"slug": slug}
    try:
        resp = await client.get(
            WP_ORG_API,
            params={"action": "plugin_information", "request[slug]": slug},
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict) and "name" in data:
                info["name"] = data.get("name", slug)
                info["latest_version"] = data.get("version", "?")
                info["last_updated"] = data.get("last_updated", "?")
                info["tested"] = data.get("tested", "?")
                info["active_installs"] = data.get("active_installs", 0)
                info["status"] = _assess_plugin_health(data)
            else:
                info["status"] = "not found on wordpress.org"
        else:
            info["status"] = "wordpress.org lookup failed"
    except (httpx.HTTPError, ValueError):
        info["status"] = "lookup error"

    return info


def _assess_plugin_health(data: dict[str, Any]) -> str:
    """Assess plugin health based on wordpress.org metadata."""
    from datetime import datetime, timezone

    last_updated = data.get("last_updated", "")
    try:
        updated_dt = datetime.strptime(last_updated, "%Y-%m-%d %I:%M%p GMT")
        updated_dt = updated_dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        days_since = (now - updated_dt).days
        if days_since > 730:
            return "abandoned (>2 years)"
        if days_since > 365:
            return "outdated (>1 year)"
    except (ValueError, TypeError):
        pass

    return "current"
