"""FastMCP server entry point and tool registrations."""

from __future__ import annotations

from typing import Any

from dotenv import load_dotenv
from fastmcp import FastMCP

from vip_site_probe.probes.plugins import check_plugins
from vip_site_probe.probes.security import check_security
from vip_site_probe.probes.site import probe_site
from vip_site_probe.zendesk import submit_to_zendesk

load_dotenv()

mcp = FastMCP("VIP Site Probe")


@mcp.tool
async def probe_site_tool(url: str) -> dict[str, Any]:
    """Probe a WordPress site and produce a comprehensive diagnostic report.

    Fetches the site URL and /wp-json/ endpoint, reads HTTP response headers for
    infrastructure signals (cache status, CDN, TTFB), and extracts REST API metadata.
    """
    return await probe_site(url)


@mcp.tool
async def check_plugins_tool(url: str) -> dict[str, Any]:
    """Discover active plugins from REST API namespaces and cross-reference them
    against the WordPress.org Plugin API.

    Reports version currency, last update date, active installs, and flags
    outdated or abandoned plugins.
    """
    return await check_plugins(url)


@mcp.tool
async def check_security_tool(url: str) -> dict[str, Any]:
    """Check for common WordPress security exposures.

    Tests xmlrpc.php accessibility, user enumeration, security headers,
    directory listing, and login page exposure.
    """
    return await check_security(url)


@mcp.tool
async def submit_to_zendesk_tool(
    action: str,
    ticket_id: int | None = None,
    subject: str | None = None,
    priority: str = "normal",
    requester_email: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Submit the most recent probe findings to Zendesk.

    Args:
        action: "create" for a new ticket or "update" to add an internal note.
        ticket_id: Required when action is "update" -- the existing ticket number.
        subject: Ticket subject (create only). Defaults to "Site probe: {url}".
        priority: "low", "normal", "high", or "urgent".
        requester_email: Customer email (create only).
        tags: List of tags, e.g. ["vip-site-probe", "cache-issue"].
    """
    return await submit_to_zendesk(
        action=action,
        ticket_id=ticket_id,
        subject=subject,
        priority=priority,
        requester_email=requester_email,
        tags=tags,
    )
