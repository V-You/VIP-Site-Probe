import re

from fastmcp.tools import ToolResult

from vip_site_probe.cache import cache
from vip_site_probe.probes.report import probe
from vip_site_probe.server import probe_report_app_resource, probe_tool


async def test_probe_combines_results_without_caching_report(monkeypatch) -> None:
    async def fake_probe_site(url: str) -> dict[str, object]:
        return {
            "url": "https://example.com",
            "identity": {"name": "Example Site"},
            "infrastructure": {"x-cache": "HIT", "ttfb_seconds": 0.123},
            "rest_api": {"status": "reachable", "namespaces": ["wp/v2"]},
            "content": {"route_count": 42},
            "cdn": ["Automattic"],
        }

    async def fake_check_plugins(url: str) -> dict[str, object]:
        return {
            "url": "https://example.com",
            "plugins": [
                {
                    "slug": "jetpack",
                    "name": "Jetpack",
                    "namespace": "jetpack/v4",
                    "latest_version": "15.6",
                    "status": "current",
                }
            ],
        }

    async def fake_check_security(url: str) -> dict[str, object]:
        return {
            "url": "https://example.com",
            "findings": [
                {
                    "severity": "warning",
                    "label": "WordPress version exposed",
                    "detail": "Version 6.9.4 found in meta generator tag.",
                }
            ],
            "xmlrpc": {"suspected_mode": "auth_gated"},
        }

    cache.clear()
    monkeypatch.setattr("vip_site_probe.probes.report.probe_site", fake_probe_site)
    monkeypatch.setattr(
        "vip_site_probe.probes.report.check_plugins",
        fake_check_plugins,
    )
    monkeypatch.setattr(
        "vip_site_probe.probes.report.check_security",
        fake_check_security,
    )

    try:
        result = await probe("example.com")

        assert result["url"] == "https://example.com"
        assert re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00",
            str(result["timestamp"]),
        )
        assert result["site_health"]["identity"]["name"] == "Example Site"
        assert result["plugin_status"]["plugins"][0]["slug"] == "jetpack"
        assert result["security_findings"]["findings"][0]["severity"] == "warning"
        assert cache.get("probe") is None
    finally:
        cache.clear()


async def test_probe_tool_returns_tool_result(monkeypatch) -> None:
    fake_data = {
        "url": "https://example.com",
        "timestamp": "2026-03-18T13:50:30+00:00",
        "site_health": {
            "identity": {"name": "Example Site"},
            "infrastructure": {"x-cache": "HIT", "ttfb_seconds": 0.123},
            "rest_api": {"status": "reachable", "namespaces": ["wp/v2"]},
            "content": {"route_count": 42},
            "cdn": ["Automattic"],
        },
        "plugin_status": {
            "plugins": [
                {
                    "slug": "jetpack",
                    "name": "Jetpack",
                    "namespace": "jetpack/v4",
                    "latest_version": "15.6",
                    "status": "current",
                }
            ]
        },
        "security_findings": {
            "findings": [
                {
                    "severity": "warning",
                    "label": "WordPress version exposed",
                    "detail": "Version 6.9.4 found in meta generator tag.",
                }
            ],
            "xmlrpc": {"suspected_mode": "auth_gated"},
        },
    }

    async def fake_probe(url: str) -> dict[str, object]:
        return fake_data

    monkeypatch.setattr("vip_site_probe.server.probe", fake_probe)

    result = await probe_tool("example.com")

    assert isinstance(result, ToolResult)
    assert isinstance(result.content, list)
    assert result.content
    assert result.content[0].type == "text"
    assert "https://example.com" in result.content[0].text
    assert isinstance(result.structured_content, dict)
    assert result.structured_content["url"] == "https://example.com"
    assert result.structured_content["site_health"]["identity"]["name"] == "Example Site"
    assert "html" in result.structured_content
    assert "Probe report" in result.structured_content["html"]
    assert "Security findings" in result.structured_content["html"]


def test_probe_report_app_resource_uses_client_side_result_handler() -> None:
    rendered = probe_report_app_resource()

    assert "@modelcontextprotocol/ext-apps" in rendered
    assert "app.ontoolresult" in rendered
    assert "structuredContent" in rendered
    assert "Waiting for tool result" in rendered
