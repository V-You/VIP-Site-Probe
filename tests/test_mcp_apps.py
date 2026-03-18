from vip_site_probe.server import (
    CHECK_PLUGINS_APP_URI,
    CHECK_SECURITY_APP_URI,
    PROBE_SITE_APP_URI,
    ZENDESK_PREVIEW_APP_URI,
    mcp,
)


def test_tools_expose_mcp_app_resources() -> None:
    provider = mcp._local_provider
    components = provider._components

    expected_tool_meta = {
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
        f"resource:{PROBE_SITE_APP_URI}@",
        f"resource:{CHECK_PLUGINS_APP_URI}@",
        f"resource:{CHECK_SECURITY_APP_URI}@",
        f"resource:{ZENDESK_PREVIEW_APP_URI}@",
    }
    assert expected_resources.issubset(set(components))
