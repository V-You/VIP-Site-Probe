"""check_security -- common WordPress security exposure checks."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, cast
from urllib.parse import urlparse
from xml.etree import ElementTree

import httpx

from vip_site_probe.cache import cache

HTTP_TIMEOUT = 10.0

SECURITY_HEADERS = [
    "strict-transport-security",
    "x-content-type-options",
    "x-frame-options",
    "content-security-policy",
    "referrer-policy",
    "permissions-policy",
]


@dataclass
class XmlRpcProbeObservation:
    """One XML-RPC probe request and the key facts we need for classification."""

    probe: str
    http_method: str
    status_code: int | None
    content_type: str | None
    is_xml: bool
    fault_code: int | None = None
    fault_string: str | None = None
    method_count: int | None = None
    error: str | None = None


async def check_security(url: str) -> dict[str, Any]:
    """Run security exposure checks against a WordPress site."""
    parsed = urlparse(url)
    if not parsed.scheme:
        url = f"https://{url}"
        parsed = urlparse(url)

    base = f"{parsed.scheme}://{parsed.netloc}"
    findings: list[dict[str, str]] = []

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=HTTP_TIMEOUT,
        headers={"User-Agent": "VIP-Site-Probe/0.1"},
    ) as client:
        # -- security headers on the home page --
        try:
            home_resp = await client.get(base)
            _check_security_headers(home_resp, findings)
            _check_wp_version_meta(home_resp.text, findings)
            _check_cors(home_resp, findings)
        except httpx.HTTPError:
            findings.append({
                "severity": "warning",
                "label": "Home page unreachable",
                "detail": "Could not fetch home page for header analysis.",
            })

        # -- xmlrpc.php --
        xmlrpc = await _check_xmlrpc(client, base, findings)

        # -- user enumeration via REST API --
        await _check_user_enum_rest(client, base, findings)

        # -- user enumeration via ?author=1 --
        await _check_user_enum_author(client, base, findings)

        # -- login page exposure --
        await _check_login_page(client, base, findings)

        # -- directory listing --
        await _check_directory_listing(client, base, findings)

    result: dict[str, Any] = {"url": base, "findings": findings, "xmlrpc": xmlrpc}
    cache.store("check_security", base, result)
    return result


def _check_security_headers(resp: httpx.Response, findings: list[dict[str, str]]) -> None:
    """Check for presence of key security headers."""
    for header in SECURITY_HEADERS:
        if header in resp.headers:
            findings.append({
                "severity": "info",
                "label": f"{header} present",
                "detail": resp.headers[header],
            })
        else:
            findings.append({
                "severity": "warning",
                "label": f"{header} missing",
                "detail": "This security header is not set.",
            })


def _check_wp_version_meta(html: str, findings: list[dict[str, str]]) -> None:
    """Check if WP version is exposed in the HTML meta generator tag."""
    match = re.search(r'<meta\s+name="generator"\s+content="WordPress\s+([\d.]+)"', html)
    if match:
        findings.append({
            "severity": "warning",
            "label": "WordPress version exposed",
            "detail": f"Version {match.group(1)} found in meta generator tag.",
        })


def _check_cors(resp: httpx.Response, findings: list[dict[str, str]]) -> None:
    """Check CORS configuration."""
    origin = resp.headers.get("access-control-allow-origin")
    if origin:
        severity = "warning" if origin == "*" else "info"
        findings.append({
            "severity": severity,
            "label": "CORS: Access-Control-Allow-Origin",
            "detail": origin,
        })


async def _check_xmlrpc(
    client: httpx.AsyncClient, base: str, findings: list[dict[str, str]]
) -> dict[str, Any]:
    """Classify XML-RPC posture with a few low-cost public requests."""
    endpoint = f"{base}/xmlrpc.php"
    observations: dict[str, XmlRpcProbeObservation] = {
        "get": await _send_xmlrpc_probe(client, endpoint, "get", "GET"),
        "list_methods": await _send_xmlrpc_probe(
            client,
            endpoint,
            "list_methods",
            "POST",
            _build_xmlrpc_method_call("system.listMethods"),
        ),
        "bad_login": await _send_xmlrpc_probe(
            client,
            endpoint,
            "bad_login",
            "POST",
            _build_xmlrpc_method_call(
                "wp.getUsersBlogs",
                ["definitely-not-a-user", "definitely-not-a-password"],
            ),
        ),
    }
    rest_context = await _get_xmlrpc_rest_context(client, base)
    assessment, xmlrpc_findings = classify_xmlrpc_observations(
        observations,
        application_passwords_advertised=rest_context["application_passwords_advertised"],
        jetpack_detected=rest_context["jetpack_detected"],
    )
    findings.extend(xmlrpc_findings)
    return {
        **assessment,
        "endpoint": endpoint,
        "rest_context": rest_context,
        "observations": {name: asdict(obs) for name, obs in observations.items()},
    }


async def _send_xmlrpc_probe(
    client: httpx.AsyncClient,
    endpoint: str,
    probe: str,
    http_method: str,
    payload: str | None = None,
) -> XmlRpcProbeObservation:
    """Send one probe request and normalize the response for classification."""
    try:
        if payload is None:
            response = await client.request(http_method, endpoint)
        else:
            response = await client.request(http_method, endpoint, content=payload)
    except httpx.HTTPError as exc:
        return XmlRpcProbeObservation(
            probe=probe,
            http_method=http_method,
            status_code=None,
            content_type=None,
            is_xml=False,
            error=str(exc),
        )

    content_type = response.headers.get("content-type")
    is_xml = bool(content_type and "xml" in content_type.lower())
    fault_code: int | None = None
    fault_string: str | None = None
    method_count: int | None = None

    if is_xml:
        try:
            xml_root = ElementTree.fromstring(response.text)
            fault_code, fault_string = _extract_xmlrpc_fault(xml_root)
            method_count = _extract_xmlrpc_method_count(xml_root)
        except ElementTree.ParseError:
            is_xml = False

    return XmlRpcProbeObservation(
        probe=probe,
        http_method=http_method,
        status_code=response.status_code,
        content_type=content_type,
        is_xml=is_xml,
        fault_code=fault_code,
        fault_string=fault_string,
        method_count=method_count,
    )


def _build_xmlrpc_method_call(method_name: str, params: list[str] | None = None) -> str:
    """Build a small XML-RPC methodCall document."""
    xml = [
        '<?xml version="1.0"?>',
        "<methodCall>",
        f"  <methodName>{method_name}</methodName>",
        "  <params>",
    ]
    for param in params or []:
        xml.extend(
            [
                "    <param>",
                f"      <value><string>{param}</string></value>",
                "    </param>",
            ]
        )
    xml.extend(["  </params>", "</methodCall>"])
    return "\n".join(xml)


async def _get_xmlrpc_rest_context(client: httpx.AsyncClient, base: str) -> dict[str, bool]:
    """Fetch small REST API signals that help interpret XML-RPC behavior."""
    try:
        response = await client.get(f"{base}/wp-json/")
        if response.status_code != 200:
            return {
                "application_passwords_advertised": False,
                "jetpack_detected": False,
            }
        data = cast(dict[str, Any], response.json())
    except (httpx.HTTPError, ValueError):
        return {
            "application_passwords_advertised": False,
            "jetpack_detected": False,
        }

    authentication_raw = data.get("authentication", {})
    namespaces_raw = data.get("namespaces", [])
    authentication = (
        cast(dict[str, Any], authentication_raw)
        if isinstance(authentication_raw, dict)
        else {}
    )
    namespaces_any = namespaces_raw if isinstance(namespaces_raw, list) else []
    namespaces = [namespace for namespace in namespaces_any if isinstance(namespace, str)]
    app_passwords = bool(authentication.get("application-passwords"))
    jetpack_detected = any(
        namespace.startswith("jetpack/")
        or namespace.startswith("wpcom/")
        or namespace.startswith("my-jetpack/")
        for namespace in namespaces
    )
    return {
        "application_passwords_advertised": app_passwords,
        "jetpack_detected": jetpack_detected,
    }


def classify_xmlrpc_observations(
    observations: dict[str, XmlRpcProbeObservation],
    application_passwords_advertised: bool,
    jetpack_detected: bool,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Turn XML-RPC probe observations into a conservative public classification."""
    findings: list[dict[str, str]] = []
    reachable = any(_observation_shows_reachability(obs) for obs in observations.values())
    auth_gated = _observation_shows_auth_gate(observations["bad_login"])
    block_observed = any(
        obs.status_code in {403, 406, 429, 503} and not obs.is_xml
        for obs in observations.values()
    )

    suspected_mode = "unreachable"
    if block_observed:
        suspected_mode = "explicit_block_or_elevated_security"
    elif auth_gated and (application_passwords_advertised or jetpack_detected):
        suspected_mode = "consistent_with_jetpack_or_app_password_controls"
    elif auth_gated:
        suspected_mode = "auth_gated"
    elif reachable:
        suspected_mode = "reachable_without_auth_signal"

    if reachable:
        findings.append({
            "severity": "info",
            "label": "xmlrpc.php endpoint reachable",
            "detail": _build_xmlrpc_reachability_detail(observations),
        })
    elif any(obs.error for obs in observations.values()):
        findings.append({
            "severity": "info",
            "label": "xmlrpc.php unreachable",
            "detail": "One or more XML-RPC probe requests failed to connect.",
        })
    else:
        findings.append({
            "severity": "info",
            "label": "xmlrpc.php blocked or not found",
            "detail": _build_xmlrpc_blocked_detail(observations),
        })

    if auth_gated:
        findings.append({
            "severity": "info",
            "label": "xmlrpc.php authentication gate observed",
            "detail": _build_xmlrpc_auth_detail(observations["bad_login"]),
        })

    if auth_gated and (application_passwords_advertised or jetpack_detected):
        findings.append({
            "severity": "info",
            "label": "xmlrpc.php Jetpack/app-password-compatible posture likely",
            "detail": _build_xmlrpc_mode_detail(
                application_passwords_advertised, jetpack_detected
            ),
        })

    if block_observed:
        findings.append({
            "severity": "info",
            "label": "xmlrpc.php edge or policy block observed",
            "detail": (
                "At least one XML-RPC probe returned a non-XML 403/406/429/503 "
                "response, consistent with edge/WAF blocking or Elevated Security."
            ),
        })

    assessment: dict[str, Any] = {
        "reachable": reachable,
        "auth_gated": auth_gated,
        "application_passwords_advertised": application_passwords_advertised,
        "jetpack_detected": jetpack_detected,
        "block_observed": block_observed,
        "suspected_mode": suspected_mode,
    }
    return assessment, findings


def _observation_shows_reachability(observation: XmlRpcProbeObservation) -> bool:
    """Determine whether one observation shows a live XML-RPC endpoint."""
    if observation.probe == "get":
        return observation.status_code == 405
    return observation.status_code == 200 and observation.is_xml


def _observation_shows_auth_gate(observation: XmlRpcProbeObservation) -> bool:
    """Detect an auth challenge from an invalid credential attempt."""
    return observation.is_xml and observation.fault_code in {401, 403}


def _build_xmlrpc_reachability_detail(
    observations: dict[str, XmlRpcProbeObservation],
) -> str:
    """Summarize the evidence that XML-RPC is live."""
    details: list[str] = []
    get_obs = observations["get"]
    list_obs = observations["list_methods"]
    if get_obs.status_code is not None:
        details.append(f"GET /xmlrpc.php -> HTTP {get_obs.status_code}")
    if list_obs.is_xml and list_obs.method_count is not None:
        details.append(
            f"system.listMethods -> 200 XML with {list_obs.method_count} method(s)"
        )
    elif list_obs.status_code is not None:
        details.append(f"system.listMethods -> HTTP {list_obs.status_code}")
    return "; ".join(details)


def _build_xmlrpc_auth_detail(observation: XmlRpcProbeObservation) -> str:
    """Summarize the auth gate observation from the bad login probe."""
    detail = "Bogus wp.getUsersBlogs credentials returned an XML-RPC auth fault"
    if observation.fault_code is not None:
        detail += f" ({observation.fault_code})"
    if observation.fault_string:
        detail += f": {observation.fault_string}"
    return detail


def _build_xmlrpc_mode_detail(
    application_passwords_advertised: bool,
    jetpack_detected: bool,
) -> str:
    """Explain why the current behavior looks compatible with VIP controls."""
    signals: list[str] = []
    if application_passwords_advertised:
        signals.append("REST API advertises application-password support")
    if jetpack_detected:
        signals.append("Jetpack namespaces are present")
    joined = "; ".join(signals) if signals else "Public probe signals are limited"
    return (
        f"{joined}. Public probing cannot prove app-password-only or "
        "Jetpack-only mode, but the behavior is consistent with VIP XML-RPC "
        "authentication controls."
    )


def _build_xmlrpc_blocked_detail(
    observations: dict[str, XmlRpcProbeObservation],
) -> str:
    """Summarize blocked or missing XML-RPC responses."""
    parts: list[str] = []
    for name, observation in observations.items():
        if observation.status_code is not None:
            parts.append(f"{name} -> HTTP {observation.status_code}")
    return "; ".join(parts)


def _extract_xmlrpc_fault(
    xml_root: ElementTree.Element,
) -> tuple[int | None, str | None]:
    """Extract faultCode and faultString from an XML-RPC methodResponse."""
    fault = xml_root.find("fault")
    if fault is None:
        return None, None

    values: dict[str, str] = {}
    for member in fault.findall(".//member"):
        name = member.findtext("name")
        value = member.find("value")
        if name is None or value is None:
            continue
        values[name] = _extract_xmlrpc_value_text(value)

    fault_code: int | None = None
    try:
        if "faultCode" in values:
            fault_code = int(values["faultCode"])
    except ValueError:
        fault_code = None
    return fault_code, values.get("faultString")


def _extract_xmlrpc_method_count(xml_root: ElementTree.Element) -> int | None:
    """Count methods returned by system.listMethods, if present."""
    data = xml_root.find(".//params/param/value/array/data")
    if data is None:
        return None
    return len(data.findall("value"))


def _extract_xmlrpc_value_text(value: ElementTree.Element) -> str:
    """Extract the text content from an XML-RPC value element."""
    if len(value) == 0:
        return value.text or ""
    child = value[0]
    return child.text or ""


async def _check_user_enum_rest(
    client: httpx.AsyncClient, base: str, findings: list[dict[str, str]]
) -> None:
    """Check user enumeration via REST API."""
    try:
        resp = await client.get(f"{base}/wp-json/wp/v2/users")
        if resp.status_code == 200:
            users_raw = resp.json()
            if isinstance(users_raw, list):
                users: list[dict[str, Any]] = [
                    user for user in users_raw if isinstance(user, dict)
                ]
            else:
                users = []
            if users:
                names = [str(user.get("slug", "?")) for user in users[:5]]
                findings.append({
                    "severity": "warning",
                    "label": "User enumeration via REST API",
                    "detail": f"Found {len(users)} user(s): {', '.join(names)}",
                })
            else:
                findings.append({
                    "severity": "info",
                    "label": "REST API users endpoint returns empty",
                    "detail": "No users exposed.",
                })
        else:
            findings.append({
                "severity": "info",
                "label": "REST API users endpoint blocked",
                "detail": f"HTTP {resp.status_code}",
            })
    except httpx.HTTPError:
        pass


async def _check_user_enum_author(
    client: httpx.AsyncClient, base: str, findings: list[dict[str, str]]
) -> None:
    """Check user enumeration via ?author=1 redirect."""
    try:
        resp = await client.get(f"{base}/?author=1")
        if resp.status_code == 200 and "/author/" in str(resp.url):
            author = str(resp.url).split("/author/")[-1].strip("/")
            findings.append({
                "severity": "warning",
                "label": "User enumeration via ?author=1",
                "detail": f"Redirected to /author/{author}",
            })
    except httpx.HTTPError:
        pass


async def _check_login_page(
    client: httpx.AsyncClient, base: str, findings: list[dict[str, str]]
) -> None:
    """Check if the login page is publicly reachable."""
    try:
        resp = await client.get(f"{base}/wp-login.php")
        if resp.status_code == 200:
            findings.append({
                "severity": "info",
                "label": "Login page reachable",
                "detail": "wp-login.php returns 200.",
            })
    except httpx.HTTPError:
        pass


async def _check_directory_listing(
    client: httpx.AsyncClient, base: str, findings: list[dict[str, str]]
) -> None:
    """Check for directory listing on common paths."""
    paths = ["/wp-content/uploads/", "/wp-content/plugins/"]
    for path in paths:
        try:
            resp = await client.get(f"{base}{path}")
            if resp.status_code == 200 and "<title>Index of" in resp.text:
                findings.append({
                    "severity": "critical",
                    "label": f"Directory listing enabled: {path}",
                    "detail": "Server returns a directory index.",
                })
        except httpx.HTTPError:
            pass
