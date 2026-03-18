from vip_site_probe.server import (
    CHECK_PLUGINS_APP_URI,
    CHECK_SECURITY_APP_URI,
    PROBE_REPORT_APP_URI,
    PROBE_SITE_APP_URI,
    ZENDESK_PREVIEW_APP_URI,
    check_plugins_app_resource,
    check_security_app_resource,
    mcp,
    probe_report_app_resource,
    probe_site_app_resource,
    zendesk_preview_app_resource,
)


def test_tools_expose_mcp_app_resources() -> None:
    provider = mcp._local_provider
    components = provider._components

    expected_tool_meta = {
        "tool:probe_tool@": PROBE_REPORT_APP_URI,
        "tool:probe_site_tool@": PROBE_SITE_APP_URI,
        "tool:check_plugins_tool@": CHECK_PLUGINS_APP_URI,
        "tool:check_security_tool@": CHECK_SECURITY_APP_URI,
        "tool:submit_to_zendesk_tool@": ZENDESK_PREVIEW_APP_URI,
    }

    for tool_key, resource_uri in expected_tool_meta.items():
        tool = components[tool_key]
        assert tool.meta is not None
        assert tool.meta["ui"]["resourceUri"] == resource_uri

    expected_resources = {
        f"resource:{PROBE_REPORT_APP_URI}@",
        f"resource:{PROBE_SITE_APP_URI}@",
        f"resource:{CHECK_PLUGINS_APP_URI}@",
        f"resource:{CHECK_SECURITY_APP_URI}@",
        f"resource:{ZENDESK_PREVIEW_APP_URI}@",
    }
    assert expected_resources.issubset(set(components))


def test_app_resources_use_client_side_result_handlers() -> None:
    resources = [
        probe_report_app_resource(),
        probe_site_app_resource(),
        check_plugins_app_resource(),
        check_security_app_resource(),
        zendesk_preview_app_resource(),
    ]

    for resource in resources:
        assert "@modelcontextprotocol/ext-apps" in resource
        assert "app.ontoolresult" in resource
        assert "structuredContent" in resource


def test_app_resources_handle_tool_result_variants() -> None:
    resources = [
        probe_report_app_resource(),
        probe_site_app_resource(),
        check_plugins_app_resource(),
        check_security_app_resource(),
        zendesk_preview_app_resource(),
    ]

    for resource in resources:
        assert "normalizeToolResult" in resource
        assert "payload.toolResult" in resource
        assert "payload.result" in resource
        assert "No tool-result notification arrived for this widget" in resource
