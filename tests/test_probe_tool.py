import re

from vip_site_probe.cache import cache
from vip_site_probe.probes.report import probe
from vip_site_probe.server import probe_report_app_resource


async def test_probe_combines_results_and_caches_report(monkeypatch) -> None:
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

        cached = cache.get("probe")
        assert cached is not None
        assert cached.data == result
    finally:
        cache.clear()


def test_probe_report_app_resource_renders_combined_sections() -> None:
    cache.clear()
    cache.store(
        "probe",
        "https://example.com",
        {
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
        },
    )

    try:
        rendered = probe_report_app_resource()

        assert "Probe report" in rendered
        assert "Site health" in rendered
        assert "Plugin status" in rendered
        assert "Security findings" in rendered
        assert "2026-03-18T13:50:30+00:00" in rendered
        assert "https://example.com" in rendered
    finally:
        cache.clear()
