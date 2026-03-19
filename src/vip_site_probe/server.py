"""FastMCP server entry point and tool registrations."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.apps import AppConfig, ResourceCSP
from fastmcp.tools import ToolResult

from vip_site_probe.formatting import (
    format_plugins_table_md,
    format_probe_report_md,
    format_security_checklist_md,
    format_site_report_md,
    format_zendesk_preview_md,
    render_plugins_app,
    render_plugins_app_shell,
    render_probe_report_app,
    render_probe_report_app_shell,
    render_security_app,
    render_security_app_shell,
    render_site_probe_app,
    render_site_probe_app_shell,
    render_zendesk_preview_app,
    render_zendesk_preview_app_shell,
)
from vip_site_probe.probes.plugins import check_plugins
from vip_site_probe.probes.report import probe
from vip_site_probe.probes.security import check_security
from vip_site_probe.probes.site import probe_site
from vip_site_probe.zendesk import submit_to_zendesk

load_dotenv()

mcp = FastMCP("VIP Site Probe")

PROBE_REPORT_APP_URI = "ui://vip-site-probe/probe-report"
PROBE_SITE_APP_URI = "ui://vip-site-probe/probe-site"
CHECK_PLUGINS_APP_URI = "ui://vip-site-probe/check-plugins"
CHECK_SECURITY_APP_URI = "ui://vip-site-probe/check-security"
ZENDESK_PREVIEW_APP_URI = "ui://vip-site-probe/zendesk-preview"
APP_RESOURCE_CSP = ResourceCSP(
    resourceDomains=["https://unpkg.com"],
    connectDomains=["https://unpkg.com"],
)


def _tool_result(
    data: dict[str, Any],
    summary: str,
    renderer: Callable[[dict[str, Any] | None], str],
) -> ToolResult:
    """Build a ToolResult with full structured data and pre-rendered widget HTML."""
    structured_content = dict(data)
    structured_content["html"] = renderer(data)
    return ToolResult(content=summary, structured_content=structured_content)


@mcp.resource(
    PROBE_REPORT_APP_URI,
    title="Combined probe report",
    description="Unified dashboard for the most recent probe result.",
    app=AppConfig(prefersBorder=True, csp=APP_RESOURCE_CSP),
)
def probe_report_app_resource() -> str:
    """Render the static combined probe MCP App shell."""
    return render_probe_report_app_shell()


@mcp.resource(
    PROBE_SITE_APP_URI,
    title="Site health dashboard",
    description="Dashboard for the most recent probe_site result.",
    app=AppConfig(prefersBorder=True, csp=APP_RESOURCE_CSP),
)
def probe_site_app_resource() -> str:
    """Render the static site probe MCP App shell."""
    return render_site_probe_app_shell()


@mcp.resource(
    CHECK_PLUGINS_APP_URI,
    title="Plugin status dashboard",
    description="Table view for the most recent check_plugins result.",
    app=AppConfig(prefersBorder=True, csp=APP_RESOURCE_CSP),
)
def check_plugins_app_resource() -> str:
    """Render the static plugin MCP App shell."""
    return render_plugins_app_shell()


@mcp.resource(
    CHECK_SECURITY_APP_URI,
    title="Security findings dashboard",
    description="Checklist view for the most recent check_security result.",
    app=AppConfig(prefersBorder=True, csp=APP_RESOURCE_CSP),
)
def check_security_app_resource() -> str:
    """Render the static security MCP App shell."""
    return render_security_app_shell()


@mcp.resource(
    ZENDESK_PREVIEW_APP_URI,
    title="Zendesk preview",
    description="Preview card for the most recent submit_to_zendesk result.",
    app=AppConfig(prefersBorder=True, csp=APP_RESOURCE_CSP),
)
def zendesk_preview_app_resource() -> str:
    """Render the static Zendesk preview MCP App shell."""
    return render_zendesk_preview_app_shell()


@mcp.tool(app=AppConfig(resourceUri=PROBE_REPORT_APP_URI, prefersBorder=True))
async def probe_tool(url: str) -> ToolResult:
    """Run the full WordPress diagnostic and return a unified report."""
    data = await probe(url)
    return _tool_result(data, format_probe_report_md(data), render_probe_report_app)


@mcp.tool(app=AppConfig(resourceUri=PROBE_SITE_APP_URI, prefersBorder=True))
async def probe_site_tool(url: str) -> ToolResult:
    """Probe a WordPress site and produce a comprehensive diagnostic report.

    Fetches the site URL and /wp-json/ endpoint, reads HTTP response headers for
    infrastructure signals (cache status, CDN, TTFB), and extracts REST API metadata.
    """
    data = await probe_site(url)
    return _tool_result(data, format_site_report_md(data), render_site_probe_app)


@mcp.tool(app=AppConfig(resourceUri=CHECK_PLUGINS_APP_URI, prefersBorder=True))
async def check_plugins_tool(url: str) -> ToolResult:
    """Discover active plugins from REST API namespaces and cross-reference them
    against the WordPress.org Plugin API.

    Reports version currency, last update date, active installs, and flags
    outdated or abandoned plugins.
    """
    data = await check_plugins(url)
    return _tool_result(data, format_plugins_table_md(data), render_plugins_app)


@mcp.tool(app=AppConfig(resourceUri=CHECK_SECURITY_APP_URI, prefersBorder=True))
async def check_security_tool(url: str) -> ToolResult:
    """Check for common WordPress security exposures.

    Tests xmlrpc.php accessibility, user enumeration, security headers,
    directory listing, and login page exposure.
    """
    data = await check_security(url)
    return _tool_result(data, format_security_checklist_md(data), render_security_app)


@mcp.tool(app=AppConfig(resourceUri=ZENDESK_PREVIEW_APP_URI, prefersBorder=True))
async def submit_to_zendesk_tool(
    action: str,
    ticket_id: int | None = None,
    subject: str | None = None,
    priority: str = "normal",
    requester_email: str | None = None,
    tags: list[str] | None = None,
) -> ToolResult:
    """Submit the most recent probe findings to Zendesk.

    Args:
        action: "create" for a new ticket or "update" to add an internal note.
        ticket_id: Required when action is "update" -- the existing ticket number.
        subject: Ticket subject (create only). Defaults to "Site probe: {url}".
        priority: "low", "normal", "high", or "urgent".
        requester_email: Customer email (create only).
        tags: List of tags, e.g. ["vip-site-probe", "cache-issue"].
    """
    data = await submit_to_zendesk(
        action=action,
        ticket_id=ticket_id,
        subject=subject,
        priority=priority,
        requester_email=requester_email,
        tags=tags,
    )
    return _tool_result(data, format_zendesk_preview_md(data), render_zendesk_preview_app)
