import re

from fastmcp.tools import ToolResult

from vip_site_probe.cache import ResultCache, cache
from vip_site_probe.probes.report import probe
from vip_site_probe.server import file_ticket_tool, probe_report_app_resource, probe_tool
from vip_site_probe.zendesk import submit_to_zendesk


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


async def test_file_ticket_tool_returns_tool_result(monkeypatch) -> None:
    fake_probe_data = {
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
    fake_zendesk_data = {
        "mode": "dry-run",
        "action": "create",
        "probed_url": "https://example.com",
        "note": "Set ZENDESK_DRY_RUN=false to actually send.",
        "payload": {
            "ticket": {
                "subject": "Site probe: https://example.com",
                "priority": "normal",
                "tags": ["vip-site-probe"],
            }
        },
    }
    captured: dict[str, object] = {}

    async def fake_probe(url: str) -> dict[str, object]:
        captured["probe_url"] = url
        return fake_probe_data

    async def fake_submit_to_zendesk(
        action: str,
        ticket_id: int | None = None,
        subject: str | None = None,
        priority: str = "normal",
        requester_email: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, object]:
        captured["action"] = action
        captured["ticket_id"] = ticket_id
        captured["subject"] = subject
        captured["priority"] = priority
        captured["requester_email"] = requester_email
        captured["tags"] = tags
        return fake_zendesk_data

    monkeypatch.setattr("vip_site_probe.server.probe", fake_probe)
    monkeypatch.setattr(
        "vip_site_probe.server.submit_to_zendesk",
        fake_submit_to_zendesk,
    )

    result = await file_ticket_tool("example.com")

    assert isinstance(result, ToolResult)
    assert isinstance(result.content, list)
    assert result.content
    assert result.content[0].type == "text"
    assert "Zendesk preview" in result.content[0].text
    assert isinstance(result.structured_content, dict)
    assert result.structured_content["url"] == "https://example.com"
    assert result.structured_content["probe_report"]["site_health"]["identity"]["name"] == "Example Site"
    assert result.structured_content["zendesk_result"]["mode"] == "dry-run"
    assert "html" in result.structured_content
    assert "File ticket" in result.structured_content["html"]
    assert "Zendesk summary" in result.structured_content["html"]
    assert captured["probe_url"] == "example.com"
    assert captured["action"] == "create"
    assert captured["priority"] == "normal"
    assert captured["ticket_id"] is None


def test_probe_report_app_resource_uses_client_side_result_handler() -> None:
    rendered = probe_report_app_resource()

    assert "@modelcontextprotocol/ext-apps" in rendered
    assert "app.ontoolresult" in rendered
    assert "structuredContent" in rendered
    assert "Waiting for tool result" in rendered


def test_result_cache_tracks_latest_url_across_tool_updates() -> None:
    result_cache = ResultCache()

    result_cache.store("probe_site", "https://blog.microsoft.com", {"url": "https://blog.microsoft.com"})
    result_cache.store(
        "check_plugins",
        "https://blog.microsoft.com",
        {"url": "https://blog.microsoft.com", "plugins": []},
    )
    result_cache.store(
        "check_security",
        "https://blog.microsoft.com",
        {"url": "https://blog.microsoft.com", "findings": []},
    )
    result_cache.store("probe_site", "https://blogs.microsoft.com", {"url": "https://blogs.microsoft.com"})

    assert result_cache.last_url() == "https://blogs.microsoft.com"
    assert [item.tool for item in result_cache.get_all()] == ["probe_site"]


async def test_submit_to_zendesk_uses_latest_url_bucket_only() -> None:
    cache.clear()
    try:
        cache.store("probe_site", "https://blog.microsoft.com", {"url": "https://blog.microsoft.com"})
        cache.store(
            "check_plugins",
            "https://blog.microsoft.com",
            {"url": "https://blog.microsoft.com", "plugins": []},
        )
        cache.store(
            "check_security",
            "https://blog.microsoft.com",
            {
                "url": "https://blog.microsoft.com",
                "findings": [
                    {
                        "severity": "warning",
                        "label": "Old finding",
                        "detail": "Should not leak into the next ticket preview.",
                    }
                ],
            },
        )

        cache.store(
            "probe_site",
            "https://blogs.microsoft.com",
            {
                "url": "https://blogs.microsoft.com",
                "identity": {"name": "Microsoft Blogs"},
            },
        )

        result = await submit_to_zendesk(action="create")

        assert result["probed_url"] == "https://blogs.microsoft.com"
        html_body = result["payload"]["ticket"]["comment"]["html_body"]
        assert "https://blogs.microsoft.com" in html_body
        assert "Old finding" not in html_body
        assert "https://blog.microsoft.com" not in html_body
    finally:
        cache.clear()
