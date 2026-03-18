"""HTML and Markdown formatters for MCP App cards and Zendesk ticket bodies."""

from __future__ import annotations

import html
import json
from typing import Any, cast

from fastmcp.utilities.ui import create_page

APP_STYLES = """
body {
    display: block;
    min-height: 100vh;
    padding: 24px;
    background:
        radial-gradient(circle at top left, #fff6e6 0%, transparent 36%),
        linear-gradient(180deg, #fffdfa 0%, #f2f7ff 100%);
    color: #14213d;
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
}

.app-shell {
    max-width: 1120px;
    margin: 0 auto;
}

.hero {
    padding: 28px 30px;
    border: 1px solid #d7dfeb;
    border-radius: 24px;
    background: linear-gradient(135deg, #ffffff 0%, #f8fbff 100%);
    box-shadow: 0 14px 34px rgba(20, 33, 61, 0.08);
}

.eyebrow {
    margin: 0 0 8px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #9a6700;
}

.hero h1 {
    margin: 0;
    font-size: 34px;
    line-height: 1.1;
    font-family: Georgia, 'Times New Roman', serif;
}

.subtitle {
    margin: 12px 0 0;
    color: #44546f;
    font-size: 15px;
}

.card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 14px;
    margin-top: 18px;
}

.metric-card,
.section,
.empty-state {
    border: 1px solid #d7dfeb;
    border-radius: 20px;
    background: rgba(255, 255, 255, 0.92);
    box-shadow: 0 8px 24px rgba(20, 33, 61, 0.05);
}

.metric-card {
    padding: 18px;
}

.metric-label {
    color: #6b7280;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

.metric-value {
    margin-top: 10px;
    font-size: 26px;
    font-weight: 700;
}

.metric-help {
    margin-top: 8px;
    color: #54657d;
    font-size: 13px;
}

.sections {
    display: grid;
    gap: 16px;
    margin-top: 18px;
}

.section {
    padding: 22px;
}

.section h2 {
    margin: 0 0 16px;
    font-size: 20px;
    font-family: Georgia, 'Times New Roman', serif;
}

.table-wrap {
    overflow-x: auto;
}

table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}

th,
td {
    padding: 12px 10px;
    border-bottom: 1px solid #e7edf5;
    text-align: left;
    vertical-align: top;
}

th {
    font-size: 12px;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

.chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.chip,
.badge {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 6px 10px;
    font-size: 12px;
    font-weight: 700;
}

.chip {
    border: 1px solid #d6e4f0;
    background: #f7fafc;
    color: #1f3b57;
}

.badge-neutral {
    background: #eef4ff;
    color: #224fa3;
}

.badge-good {
    background: #e7f6ec;
    color: #17663a;
}

.badge-warn {
    background: #fff3d9;
    color: #9a6700;
}

.badge-danger {
    background: #fdebec;
    color: #b42318;
}

.finding-list {
    display: grid;
    gap: 12px;
}

.finding {
    padding: 14px 16px;
    border: 1px solid #e3e8ef;
    border-radius: 16px;
    background: #fcfdff;
}

.finding-head {
    display: flex;
    gap: 10px;
    align-items: center;
    flex-wrap: wrap;
}

.finding-title {
    font-weight: 700;
}

.finding-detail,
.muted {
    margin-top: 8px;
    color: #54657d;
}

.empty-state {
    margin-top: 18px;
    padding: 28px;
    text-align: center;
}

.pre-block {
    margin: 0;
    padding: 18px;
    border-radius: 16px;
    background: #16202f;
    color: #eff5ff;
    overflow-x: auto;
    font-size: 13px;
    line-height: 1.5;
}

@media (max-width: 720px) {
    body {
        padding: 12px;
    }

    .hero,
    .section,
    .empty-state {
        padding: 18px;
    }

    .hero h1 {
        font-size: 28px;
    }
}
"""

APP_SDK_URL = "https://unpkg.com/@modelcontextprotocol/ext-apps@0.4.0/app-with-deps"


def format_probe_report_md(data: dict[str, Any]) -> str:
    """Format the combined probe results as Markdown."""
    sections = [
        "## Probe report",
        "",
        f"- **timestamp:** {data.get('timestamp', '-')}",
        f"- **target:** {data.get('url', 'unknown')}",
        "",
        format_site_report_md(_as_dict(data.get("site_health"))),
        "",
        format_plugins_table_md(_as_dict(data.get("plugin_status"))),
        "",
        format_security_checklist_md(_as_dict(data.get("security_findings"))),
    ]
    return "\n".join(section for section in sections if section)


def format_site_report_md(data: dict[str, Any]) -> str:
    """Format probe_site results as Markdown."""
    lines = [f"## Site probe: {data.get('url', 'unknown')}"]

    if identity := _as_dict(data.get("identity")):
        lines.append("\n### Site identity")
        for key, val in identity.items():
            lines.append(f"- **{key}:** {val}")

    if infra := _as_dict(data.get("infrastructure")):
        lines.append("\n### Infrastructure signals")
        for key, val in infra.items():
            lines.append(f"- **{key}:** {val}")

    if rest := _as_dict(data.get("rest_api")):
        lines.append("\n### REST API")
        for key, val in rest.items():
            lines.append(f"- **{key}:** {val}")

    if content := _as_dict(data.get("content")):
        lines.append("\n### Content summary")
        for key, val in content.items():
            lines.append(f"- **{key}:** {val}")

    return "\n".join(lines)


def format_plugins_table_md(data: dict[str, Any]) -> str:
    """Format check_plugins results as a Markdown table."""
    plugins = _dicts_from_list(data.get("plugins"))
    if not plugins:
        return "_No plugins discovered._"

    lines = [
        "## Plugin report",
        "",
        "| Plugin | Installed | Latest | Last updated | Status |",
        "|--------|-----------|--------|--------------|--------|",
    ]
    for plugin in plugins:
        status = plugin.get("status", "ok")
        lines.append(
            f"| {plugin.get('slug', '?')} "
            f"| {plugin.get('installed_version', '?')} "
            f"| {plugin.get('latest_version', '?')} "
            f"| {plugin.get('last_updated', '?')} "
            f"| {status} |"
        )
    return "\n".join(lines)


def format_security_checklist_md(data: dict[str, Any]) -> str:
    """Format check_security results as a Markdown checklist."""
    findings = _dicts_from_list(data.get("findings"))
    if not findings:
        return "_No security findings._"

    lines = ["## Security report", ""]
    for finding in findings:
        severity = finding.get("severity", "info")
        label = finding.get("label", "?")
        detail = finding.get("detail", "")
        lines.append(f"- **[{severity}]** {label}: {detail}")
    return "\n".join(lines)


def format_zendesk_preview_md(data: dict[str, Any]) -> str:
    """Format submit_to_zendesk results as Markdown."""
    if error := data.get("error"):
        return f"## Zendesk preview\n\n- **error:** {error}"

    lines = [
        "## Zendesk preview",
        "",
        f"- **mode:** {data.get('mode', data.get('status', 'unknown'))}",
        f"- **action:** {data.get('action', '-')}",
        f"- **ticket_id:** {data.get('ticket_id', 'new')}",
        f"- **probed_url:** {data.get('probed_url', 'unknown')}",
    ]
    if note := data.get("note"):
        lines.append(f"- **note:** {note}")
    if payload := _as_dict(data.get("payload")):
        lines.extend(["", "```json", json.dumps(payload, indent=2, sort_keys=True), "```"])
    elif detail := data.get("detail"):
        lines.extend(["", f"- **detail:** {detail}"])
    return "\n".join(lines)


def format_zendesk_html(results: list[dict[str, Any]]) -> str:
    """Combine all cached results into an HTML body for Zendesk html_body."""
    sections: list[str] = []
    for result in results:
        tool = result.get("tool", "")
        data = _as_dict(result.get("data"))
        if tool == "probe_site":
            sections.append(_md_to_simple_html(format_site_report_md(data)))
        elif tool == "check_plugins":
            sections.append(_md_to_simple_html(format_plugins_table_md(data)))
        elif tool == "check_security":
            sections.append(_md_to_simple_html(format_security_checklist_md(data)))

    return "<br>".join(sections) if sections else "<p>No probe results cached.</p>"


def render_probe_report_app(data: dict[str, Any] | None) -> str:
    """Render the combined probe MCP App from the most recent cached result."""
    if not data:
        return _render_empty_page(
            title="Probe report",
            eyebrow="Probe",
            message="Run probe_tool to populate the combined diagnostic report.",
        )

    site_health = _as_dict(data.get("site_health"))
    identity = _as_dict(site_health.get("identity"))
    infrastructure = _as_dict(site_health.get("infrastructure"))
    rest_api = _as_dict(site_health.get("rest_api"))
    content = _as_dict(site_health.get("content"))
    namespaces = [ns for ns in _as_list(rest_api.get("namespaces")) if isinstance(ns, str)]
    cdn = [name for name in _as_list(site_health.get("cdn")) if isinstance(name, str)]

    plugin_status = _as_dict(data.get("plugin_status"))
    plugins = _dicts_from_list(plugin_status.get("plugins"))

    security_findings = _as_dict(data.get("security_findings"))
    findings = _dicts_from_list(security_findings.get("findings"))
    xmlrpc = _as_dict(security_findings.get("xmlrpc"))
    review_findings = sum(
        1
        for finding in findings
        if finding.get("severity") in {"warning", "critical"}
    )

    cards = _render_cards(
        [
            _metric_card(
                "Cache",
                infrastructure.get("x-cache", "unknown"),
                "Homepage cache state",
            ),
            _metric_card(
                "TTFB",
                _format_ttfb(infrastructure.get("ttfb_seconds")),
                "Time to first byte for the homepage",
            ),
            _metric_card(
                "Plugins",
                len(plugins),
                "Detected plugins with status metadata",
            ),
            _metric_card(
                "Needs review",
                review_findings,
                "Warning or critical security findings",
            ),
        ]
    )

    sections = [
        _render_key_value_section(
            "Report summary",
            {
                "url": data.get("url", "unknown"),
                "generated_at": data.get("timestamp", "-"),
                "rest_api_status": rest_api.get("status", "unknown"),
                "routes": content.get("route_count", "-"),
            },
        ),
        _render_intro_section(
            "Site health",
            "Identity, infrastructure, CDN, and REST API signals from the latest run.",
        ),
        _render_key_value_section("Site identity", identity),
        _render_key_value_section("Infrastructure signals", infrastructure),
    ]
    if namespaces:
        sections.append(_render_chip_section("Namespaces", namespaces))
    if cdn:
        sections.append(_render_chip_section("CDN indicators", cdn))

    sections.append(
        _render_intro_section(
            "Plugin status",
            "Version currency and health flags from detected plugins.",
        )
    )
    if plugins:
        sections.append(_render_plugins_table(plugins))
    else:
        sections.append(_render_empty_section("No plugins were detected in the latest run."))

    sections.append(
        _render_intro_section(
            "Security findings",
            "Checklist with severity badges and XML-RPC posture evidence.",
        )
    )
    if xmlrpc:
        sections.append(_render_xmlrpc_section(xmlrpc))
    sections.append(_render_findings_section(findings))

    subtitle_parts = [_display_value(data.get("url", "unknown"))]
    if timestamp := data.get("timestamp"):
        subtitle_parts.append(f"Generated {timestamp}")

    return _render_page(
        title="Probe report",
        eyebrow="Probe",
        subtitle=_safe_text(" | ".join(subtitle_parts)),
        body=cards + _wrap_sections(sections),
    )


def render_probe_report_app_shell() -> str:
    """Render the static combined probe MCP App shell."""
    return _render_app_shell(
        title="Probe report",
        eyebrow="Probe",
        waiting_message="Run probe_tool to populate the combined diagnostic report.",
    )


def render_site_probe_app(data: dict[str, Any] | None) -> str:
    """Render the probe_site MCP App from the most recent cached result."""
    if not data:
        return _render_empty_page(
            title="Site health",
            eyebrow="Probe site",
            message="Run probe_site to populate the site dashboard.",
        )

    identity = _as_dict(data.get("identity"))
    infrastructure = _as_dict(data.get("infrastructure"))
    rest_api = _as_dict(data.get("rest_api"))
    content = _as_dict(data.get("content"))
    namespaces = [ns for ns in _as_list(rest_api.get("namespaces")) if isinstance(ns, str)]
    cdn = [name for name in _as_list(data.get("cdn")) if isinstance(name, str)]

    cards = _render_cards(
        [
            _metric_card(
                "Cache",
                infrastructure.get("x-cache", "unknown"),
                "Homepage cache state",
            ),
            _metric_card(
                "TTFB",
                _format_ttfb(infrastructure.get("ttfb_seconds")),
                "Time to first byte for the homepage",
            ),
            _metric_card(
                "REST API",
                rest_api.get("status", "unknown"),
                "Public index reachability",
            ),
            _metric_card(
                "Routes",
                content.get("route_count", "-"),
                "Routes exposed by /wp-json/",
            ),
        ]
    )

    sections = [
        _render_key_value_section("Site identity", identity),
        _render_key_value_section("Infrastructure signals", infrastructure),
    ]
    if namespaces:
        sections.append(_render_chip_section("Namespaces", namespaces))
    if cdn:
        sections.append(_render_chip_section("CDN indicators", cdn))
    if content:
        sections.append(_render_key_value_section("Content summary", content))

    return _render_page(
        title="Site health",
        eyebrow="Probe site",
        subtitle=_safe_text(data.get("url", "unknown")),
        body=cards + _wrap_sections(sections),
    )


def render_site_probe_app_shell() -> str:
    """Render the static site probe MCP App shell."""
    return _render_app_shell(
        title="Site health",
        eyebrow="Probe site",
        waiting_message="Run probe_site_tool to populate the site dashboard.",
    )


def render_plugins_app(data: dict[str, Any] | None) -> str:
    """Render the check_plugins MCP App from the most recent cached result."""
    if not data:
        return _render_empty_page(
            title="Plugin status",
            eyebrow="Check plugins",
            message="Run check_plugins to populate the plugin table.",
        )

    plugins = _dicts_from_list(data.get("plugins"))
    current = sum(
        1
        for plugin in plugins
        if _status_tone(str(plugin.get("status", ""))) == "good"
    )
    unresolved = sum(
        1
        for plugin in plugins
        if _status_tone(str(plugin.get("status", ""))) in {"warn", "danger"}
    )
    cards = _render_cards(
        [
            _metric_card(
                "Detected",
                len(plugins),
                "Plugins inferred from REST and HTML signals",
            ),
            _metric_card(
                "Current",
                current,
                "Plugins that look current on wordpress.org",
            ),
            _metric_card(
                "Needs review",
                unresolved,
                "Lookup failures or stale plugin metadata",
            ),
        ]
    )

    if plugins:
        sections = [_render_plugins_table(plugins)]
    else:
        sections = [_render_empty_section("No plugins were detected in the latest run.")]

    return _render_page(
        title="Plugin status",
        eyebrow="Check plugins",
        subtitle=_safe_text(data.get("url", "unknown")),
        body=cards + _wrap_sections(sections),
    )


def render_plugins_app_shell() -> str:
    """Render the static plugin MCP App shell."""
    return _render_app_shell(
        title="Plugin status",
        eyebrow="Check plugins",
        waiting_message="Run check_plugins_tool to populate the plugin table.",
    )


def render_security_app(data: dict[str, Any] | None) -> str:
    """Render the check_security MCP App from the most recent cached result."""
    if not data:
        return _render_empty_page(
            title="Security findings",
            eyebrow="Check security",
            message="Run check_security to populate the security report.",
        )

    findings = _dicts_from_list(data.get("findings"))
    xmlrpc = _as_dict(data.get("xmlrpc"))
    severity_counts = {
        "critical": sum(
            1 for finding in findings if finding.get("severity") == "critical"
        ),
        "warning": sum(
            1 for finding in findings if finding.get("severity") == "warning"
        ),
        "info": sum(1 for finding in findings if finding.get("severity") == "info"),
    }
    cards = _render_cards(
        [
            _metric_card(
                "Critical",
                severity_counts["critical"],
                "Highest-severity findings",
            ),
            _metric_card(
                "Warnings",
                severity_counts["warning"],
                "Findings needing review",
            ),
            _metric_card(
                "Informational",
                severity_counts["info"],
                "Signals and controls observed",
            ),
            _metric_card(
                "XML-RPC mode",
                xmlrpc.get("suspected_mode", "unknown"),
                "Classifier output from public XML-RPC probes",
            ),
        ]
    )

    sections: list[str] = []
    if xmlrpc:
        sections.append(_render_xmlrpc_section(xmlrpc))
    sections.append(_render_findings_section(findings))

    return _render_page(
        title="Security findings",
        eyebrow="Check security",
        subtitle=_safe_text(data.get("url", "unknown")),
        body=cards + _wrap_sections(sections),
    )


def render_security_app_shell() -> str:
    """Render the static security MCP App shell."""
    return _render_app_shell(
        title="Security findings",
        eyebrow="Check security",
        waiting_message="Run check_security_tool to populate the security report.",
    )


def render_zendesk_preview_app(data: dict[str, Any] | None) -> str:
    """Render the submit_to_zendesk MCP App from the most recent cached result."""
    if not data:
        return _render_empty_page(
            title="Zendesk preview",
            eyebrow="Submit to Zendesk",
            message="Run submit_to_zendesk to preview or confirm a ticket action.",
        )

    payload = _as_dict(data.get("payload"))
    cards = _render_cards(
        [
            _metric_card(
                "Mode",
                data.get("mode", data.get("status", "unknown")),
                "Dry-run or live API result",
            ),
            _metric_card(
                "Action",
                data.get("action", "-"),
                "Create ticket or update existing ticket",
            ),
            _metric_card(
                "Ticket",
                data.get("ticket_id", "new"),
                "Existing ticket id or created ticket id",
            ),
        ]
    )

    sections = [
        _render_key_value_section(
            "Summary",
            {
                "probed_url": data.get("probed_url", "unknown"),
                "note": data.get("note", ""),
                "ticket_url": data.get("ticket_url", ""),
            },
        )
    ]
    if error := data.get("error"):
        sections.append(_render_code_section("Error", str(error)))
    elif payload:
        sections.append(
            _render_code_section("Payload", json.dumps(payload, indent=2, sort_keys=True))
        )
    elif detail := data.get("detail"):
        sections.append(_render_code_section("Response detail", str(detail)))

    return _render_page(
        title="Zendesk preview",
        eyebrow="Submit to Zendesk",
        subtitle=_safe_text(data.get("probed_url", "latest cached probe")),
        body=cards + _wrap_sections(sections),
    )


def render_zendesk_preview_app_shell() -> str:
    """Render the static Zendesk preview MCP App shell."""
    return _render_app_shell(
        title="Zendesk preview",
        eyebrow="Submit to Zendesk",
        waiting_message="Run submit_to_zendesk_tool to preview or confirm a ticket action.",
    )


def _render_page(title: str, eyebrow: str, subtitle: str, body: str) -> str:
    """Render the core markup shown inside an MCP App iframe."""
    return f"""
    <main class="app-shell">
        <section class="hero">
            <p class="eyebrow">{_safe_text(eyebrow)}</p>
            <h1>{_safe_text(title)}</h1>
            <p class="subtitle">{subtitle}</p>
        </section>
        {body}
    </main>
    """


def _render_empty_page(title: str, eyebrow: str, message: str) -> str:
    """Render a neutral empty-state app fragment."""
    body = f"<section class=\"empty-state\"><p class=\"muted\">{_safe_text(message)}</p></section>"
    return _render_page(title=title, eyebrow=eyebrow, subtitle="No cached result", body=body)


def _render_app_shell(title: str, eyebrow: str, waiting_message: str) -> str:
    """Render a static HTML shell that hydrates from the host tool result."""
    waiting_markup = _render_page(
        title=title,
        eyebrow=eyebrow,
        subtitle="Waiting for tool result",
        body=(
            f"<section class=\"empty-state\"><p class=\"muted\">"
            f"{_safe_text(waiting_message)}</p></section>"
        ),
    )
    content = f"""
    <div id="app-root">{waiting_markup}</div>
    <script type="module">
        import {{ App }} from "{APP_SDK_URL}";

        const app = new App({{ name: "VIP Site Probe", version: "0.1.0" }});
        const root = document.getElementById("app-root");
        const title = {json.dumps(title)};
        const eyebrow = {json.dumps(eyebrow)};

        const escapeHtml = (value) => String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\"/g, "&quot;")
            .replace(/'/g, "&#39;");

        const fallbackText = (content) => {{
            if (typeof content === "string") {{
                return content;
            }}
            if (Array.isArray(content)) {{
                return content
                    .filter((block) => block && block.type === "text")
                    .map((block) => block.text ?? "")
                    .join("\\n\\n");
            }}
            return "";
        }};

        const fallbackMarkup = (text) => `
            <main class="app-shell">
                <section class="hero">
                    <p class="eyebrow">${{escapeHtml(eyebrow)}}</p>
                    <h1>${{escapeHtml(title)}}</h1>
                    <p class="subtitle">Model text output</p>
                </section>
                <div class="sections">
                    <section class="section">
                        <h2>Summary</h2>
                        <pre class="pre-block">${{escapeHtml(text)}}</pre>
                    </section>
                </div>
            </main>
        `;

        app.ontoolresult = (result) => {{
            const data = result?.structuredContent ?? result?.structured_content ?? null;
            const html = data && typeof data === "object" ? data.html : null;
            if (typeof html === "string" && html.trim()) {{
                root.innerHTML = html;
                return;
            }}

            const text = fallbackText(result?.content);
            if (text) {{
                root.innerHTML = fallbackMarkup(text);
            }}
        }};

        await app.connect();
    </script>
    """
    return create_page(content=content, title=title, additional_styles=APP_STYLES)


def _render_cards(cards: list[str]) -> str:
    """Wrap metric cards in the responsive grid."""
    return f"<section class=\"card-grid\">{''.join(cards)}</section>"


def _metric_card(label: str, value: Any, help_text: str) -> str:
    """Render a single metric card."""
    return f"""
    <article class="metric-card">
        <div class="metric-label">{_safe_text(label)}</div>
        <div class="metric-value">{_safe_text(value)}</div>
        <div class="metric-help">{_safe_text(help_text)}</div>
    </article>
    """


def _wrap_sections(sections: list[str]) -> str:
    """Wrap non-empty sections in the standard stack container."""
    rendered = ''.join(section for section in sections if section)
    return f"<div class=\"sections\">{rendered}</div>"


def _render_key_value_section(title: str, mapping: dict[str, Any]) -> str:
    """Render a key-value table section."""
    rows: list[str] = []
    for key, value in mapping.items():
        if value in (None, "", [], {}):
            continue
        rows.append(
            "<tr>"
            f"<th>{_safe_text(key)}</th>"
            f"<td>{_safe_text(_display_value(value))}</td>"
            "</tr>"
        )
    if not rows:
        return ""
    return f"""
    <section class="section">
        <h2>{_safe_text(title)}</h2>
        <div class="table-wrap">
            <table>
                <tbody>{''.join(rows)}</tbody>
            </table>
        </div>
    </section>
    """


def _render_chip_section(title: str, values: list[str]) -> str:
    """Render a chip list section."""
    chips = ''.join(f"<span class=\"chip\">{_safe_text(value)}</span>" for value in values)
    return f"""
    <section class="section">
        <h2>{_safe_text(title)}</h2>
        <div class="chips">{chips}</div>
    </section>
    """


def _render_plugins_table(plugins: list[dict[str, Any]]) -> str:
    """Render the plugin table used by the plugin MCP App."""
    rows: list[str] = []
    for plugin in plugins:
        status = str(plugin.get("status", "unknown"))
        tone = _status_tone(status)
        name = plugin.get("name") or plugin.get("slug", "unknown")
        rows.append(
            "<tr>"
            f"<td>{_safe_text(name, decode_entities=True)}</td>"
            f"<td>{_safe_text(plugin.get('namespace', '-'))}</td>"
            f"<td>{_safe_text(plugin.get('installed_version', '-'))}</td>"
            f"<td>{_safe_text(plugin.get('latest_version', '-'))}</td>"
            f"<td>{_safe_text(plugin.get('tested', '-'))}</td>"
            f"<td>{_safe_text(plugin.get('last_updated', '-'))}</td>"
            f"<td>{_safe_text(plugin.get('active_installs', '-'))}</td>"
            f"<td><span class=\"badge badge-{tone}\">{_safe_text(status)}</span></td>"
            "</tr>"
        )

    return f"""
    <section class="section">
        <h2>Discovered plugins</h2>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Plugin</th>
                        <th>Namespace</th>
                        <th>Installed</th>
                        <th>Latest</th>
                        <th>Tested</th>
                        <th>Last updated</th>
                        <th>Installs</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>{''.join(rows)}</tbody>
            </table>
        </div>
    </section>
    """


def _render_findings_section(findings: list[dict[str, Any]]) -> str:
    """Render the standard security findings list."""
    items: list[str] = []
    for finding in findings:
        severity = str(finding.get("severity", "info"))
        items.append(
            f"""
            <article class="finding">
                <div class="finding-head">
                    <span class="badge badge-{_severity_tone(severity)}">
                        {_safe_text(severity)}
                    </span>
                    <span class="finding-title">{_safe_text(finding.get('label', 'finding'))}</span>
                </div>
                <div class="finding-detail">{_safe_text(finding.get('detail', ''))}</div>
            </article>
            """
        )
    if not items:
        return _render_empty_section("No security findings were reported in the latest run.")
    return f"""
    <section class="section">
        <h2>Findings</h2>
        <div class="finding-list">{''.join(items)}</div>
    </section>
    """


def _render_xmlrpc_section(xmlrpc: dict[str, Any]) -> str:
    """Render XML-RPC posture and probe evidence."""
    badges = [
        _badge("reachable", bool(xmlrpc.get("reachable")), "good"),
        _badge("auth gated", bool(xmlrpc.get("auth_gated")), "neutral"),
        _badge(
            "app passwords advertised",
            bool(xmlrpc.get("application_passwords_advertised")),
            "neutral",
        ),
        _badge("jetpack detected", bool(xmlrpc.get("jetpack_detected")), "neutral"),
        _badge("edge block observed", bool(xmlrpc.get("block_observed")), "warn"),
    ]
    observations = _as_dict(xmlrpc.get("observations"))
    rows: list[str] = []
    for name, observation_raw in observations.items():
        observation = _as_dict(observation_raw)
        rows.append(
            "<tr>"
            f"<td>{_safe_text(name)}</td>"
            f"<td>{_safe_text(observation.get('http_method', '-'))}</td>"
            f"<td>{_safe_text(observation.get('status_code', '-'))}</td>"
            f"<td>{_safe_text(observation.get('content_type', '-'))}</td>"
            f"<td>{_safe_text(observation.get('fault_code', '-'))}</td>"
            f"<td>{_safe_text(observation.get('method_count', '-'))}</td>"
            "</tr>"
        )
    return f"""
    <section class="section">
        <h2>XML-RPC posture</h2>
        <p class="muted">Suspected mode: {_safe_text(xmlrpc.get('suspected_mode', 'unknown'))}</p>
        <div class="chips">{''.join(badges)}</div>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Probe</th>
                        <th>Method</th>
                        <th>Status</th>
                        <th>Content type</th>
                        <th>Fault</th>
                        <th>Methods</th>
                    </tr>
                </thead>
                <tbody>{''.join(rows)}</tbody>
            </table>
        </div>
    </section>
    """


def _render_code_section(title: str, payload: str) -> str:
    """Render preformatted payload or response content."""
    return f"""
    <section class="section">
        <h2>{_safe_text(title)}</h2>
        <pre class="pre-block">{_safe_text(payload)}</pre>
    </section>
    """


def _render_intro_section(title: str, message: str) -> str:
    """Render a simple section heading with supporting copy."""
    return f"""
    <section class="section">
        <h2>{_safe_text(title)}</h2>
        <p class="muted">{_safe_text(message)}</p>
    </section>
    """


def _render_empty_section(message: str) -> str:
    """Render a section-level empty state."""
    return f"""
    <section class="section">
        <p class="muted">{_safe_text(message)}</p>
    </section>
    """


def _badge(label: str, enabled: bool, tone: str) -> str:
    """Render a boolean badge for status chips."""
    badge_tone = tone if enabled else "neutral"
    state = "yes" if enabled else "no"
    return (
        f"<span class=\"badge badge-{badge_tone}\">"
        f"{_safe_text(label)}: {state}"
        "</span>"
    )


def _format_ttfb(value: Any) -> str:
    """Format a TTFB value for the site health dashboard."""
    if isinstance(value, (int, float)):
        return f"{value:.3f}s"
    return _display_value(value)


def _display_value(value: Any) -> str:
    """Convert nested JSON-ish values into compact text."""
    if isinstance(value, list):
        items = cast(list[Any], value)
        return ", ".join(_display_value(item) for item in items) or "-"
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    if value in (None, ""):
        return "-"
    return str(value)


def _status_tone(status: str) -> str:
    """Map plugin status text to a badge tone."""
    lowered = status.lower()
    if "current" in lowered or "ok" in lowered:
        return "good"
    if "abandoned" in lowered or "error" in lowered:
        return "danger"
    if "lookup" in lowered or "outdated" in lowered or "not found" in lowered:
        return "warn"
    return "neutral"


def _severity_tone(severity: str) -> str:
    """Map finding severity to a badge tone."""
    if severity == "critical":
        return "danger"
    if severity == "warning":
        return "warn"
    return "neutral"


def _as_dict(value: Any) -> dict[str, Any]:
    """Return a dict[str, Any] view of JSON-like data or an empty dict."""
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    """Return a list[Any] view of JSON-like data or an empty list."""
    return cast(list[Any], value) if isinstance(value, list) else []


def _dicts_from_list(value: Any) -> list[dict[str, Any]]:
    """Return only dict items from a JSON-like list."""
    items = _as_list(value)
    return [item for item in items if isinstance(item, dict)]


def _safe_text(value: Any, decode_entities: bool = False) -> str:
    """Escape text for HTML output and optionally decode HTML entities first."""
    text = _display_value(value)
    if decode_entities:
        text = html.unescape(text)
    return html.escape(text)


def _md_to_simple_html(md: str) -> str:
    """Naive Markdown-to-HTML for Zendesk -- just wraps in <pre> for now."""
    return f"<pre>{html.escape(md)}</pre>"
