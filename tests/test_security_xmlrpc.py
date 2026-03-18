from vip_site_probe.probes.security import (
    XmlRpcProbeObservation,
    classify_xmlrpc_observations,
)


def test_classify_xmlrpc_auth_gated_with_vip_signals() -> None:
    observations = {
        "get": XmlRpcProbeObservation(
            probe="get",
            http_method="GET",
            status_code=405,
            content_type="text/html",
            is_xml=False,
        ),
        "list_methods": XmlRpcProbeObservation(
            probe="list_methods",
            http_method="POST",
            status_code=200,
            content_type="text/xml; charset=UTF-8",
            is_xml=True,
            method_count=66,
        ),
        "bad_login": XmlRpcProbeObservation(
            probe="bad_login",
            http_method="POST",
            status_code=200,
            content_type="text/xml; charset=UTF-8",
            is_xml=True,
            fault_code=403,
            fault_string="Incorrect username or password.",
        ),
    }

    assessment, findings = classify_xmlrpc_observations(
        observations,
        application_passwords_advertised=True,
        jetpack_detected=True,
    )

    assert assessment["reachable"] is True
    assert assessment["auth_gated"] is True
    assert assessment["block_observed"] is False
    assert (
        assessment["suspected_mode"]
        == "consistent_with_jetpack_or_app_password_controls"
    )

    labels = {finding["label"] for finding in findings}
    assert "xmlrpc.php endpoint reachable" in labels
    assert "xmlrpc.php authentication gate observed" in labels
    assert "xmlrpc.php Jetpack/app-password-compatible posture likely" in labels



def test_classify_xmlrpc_explicit_block() -> None:
    observations = {
        "get": XmlRpcProbeObservation(
            probe="get",
            http_method="GET",
            status_code=405,
            content_type="text/html",
            is_xml=False,
        ),
        "list_methods": XmlRpcProbeObservation(
            probe="list_methods",
            http_method="POST",
            status_code=403,
            content_type="text/html",
            is_xml=False,
        ),
        "bad_login": XmlRpcProbeObservation(
            probe="bad_login",
            http_method="POST",
            status_code=403,
            content_type="text/html",
            is_xml=False,
        ),
    }

    assessment, findings = classify_xmlrpc_observations(
        observations,
        application_passwords_advertised=False,
        jetpack_detected=False,
    )

    assert assessment["reachable"] is True
    assert assessment["auth_gated"] is False
    assert assessment["block_observed"] is True
    assert assessment["suspected_mode"] == "explicit_block_or_elevated_security"

    labels = {finding["label"] for finding in findings}
    assert "xmlrpc.php endpoint reachable" in labels
    assert "xmlrpc.php edge or policy block observed" in labels
