"""HTML and Markdown formatters for MCP App cards and Zendesk ticket bodies."""

from __future__ import annotations

from typing import Any


def format_site_report_md(data: dict[str, Any]) -> str:
    """Format probe_site results as Markdown."""
    lines = [f"## Site probe: {data.get('url', 'unknown')}"]

    if identity := data.get("identity"):
        lines.append("\n### Site identity")
        for key, val in identity.items():
            lines.append(f"- **{key}:** {val}")

    if infra := data.get("infrastructure"):
        lines.append("\n### Infrastructure signals")
        for key, val in infra.items():
            lines.append(f"- **{key}:** {val}")

    if rest := data.get("rest_api"):
        lines.append("\n### REST API")
        for key, val in rest.items():
            lines.append(f"- **{key}:** {val}")

    if content := data.get("content"):
        lines.append("\n### Content summary")
        for key, val in content.items():
            lines.append(f"- **{key}:** {val}")

    return "\n".join(lines)


def format_plugins_table_md(data: dict[str, Any]) -> str:
    """Format check_plugins results as a Markdown table."""
    plugins = data.get("plugins", [])
    if not plugins:
        return "_No plugins discovered._"

    lines = [
        "## Plugin report",
        "",
        "| Plugin | Installed | Latest | Last updated | Status |",
        "|--------|-----------|--------|--------------|--------|",
    ]
    for p in plugins:
        status = p.get("status", "ok")
        lines.append(
            f"| {p.get('slug', '?')} "
            f"| {p.get('installed_version', '?')} "
            f"| {p.get('latest_version', '?')} "
            f"| {p.get('last_updated', '?')} "
            f"| {status} |"
        )
    return "\n".join(lines)


def format_security_checklist_md(data: dict[str, Any]) -> str:
    """Format check_security results as a Markdown checklist."""
    findings = data.get("findings", [])
    if not findings:
        return "_No security findings._"

    lines = ["## Security report", ""]
    for f in findings:
        severity = f.get("severity", "info")
        label = f.get("label", "?")
        detail = f.get("detail", "")
        lines.append(f"- **[{severity}]** {label}: {detail}")
    return "\n".join(lines)


def format_zendesk_html(results: list[dict[str, Any]]) -> str:
    """Combine all cached results into an HTML body for Zendesk html_body."""
    # minimal HTML -- Zendesk renders it in the agent UI
    sections: list[str] = []
    for r in results:
        tool = r.get("tool", "")
        data = r.get("data", {})
        if tool == "probe_site":
            sections.append(_md_to_simple_html(format_site_report_md(data)))
        elif tool == "check_plugins":
            sections.append(_md_to_simple_html(format_plugins_table_md(data)))
        elif tool == "check_security":
            sections.append(_md_to_simple_html(format_security_checklist_md(data)))

    return "<br>".join(sections) if sections else "<p>No probe results cached.</p>"


def _md_to_simple_html(md: str) -> str:
    """Naive Markdown-to-HTML for Zendesk -- just wraps in <pre> for now."""
    # TODO: replace with proper conversion if needed
    from html import escape

    return f"<pre>{escape(md)}</pre>"
