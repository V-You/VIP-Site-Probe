"""submit_to_zendesk -- push probe findings to Zendesk as ticket or internal note."""

from __future__ import annotations

import os
from typing import Any

import httpx

from vip_site_probe.cache import cache
from vip_site_probe.formatting import format_zendesk_html

HTTP_TIMEOUT = 10.0


async def submit_to_zendesk(
    action: str,
    ticket_id: int | None = None,
    subject: str | None = None,
    priority: str = "normal",
    requester_email: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Submit cached probe results to Zendesk or preview the payload."""
    cached = cache.get_all()
    if not cached:
        return {"error": "No probe results cached. Run a probe first."}

    html_body = format_zendesk_html(
        [{"tool": r.tool, "data": r.data} for r in cached]
    )
    probed_url = cache.last_url() or "unknown"

    if action not in ("create", "update"):
        return {"error": f"Invalid action: {action}. Use 'create' or 'update'."}

    if action == "update" and not ticket_id:
        return {"error": "ticket_id is required for 'update' action."}

    # build the Zendesk payload
    payload = _build_payload(
        action=action,
        ticket_id=ticket_id,
        html_body=html_body,
        subject=subject or f"Site probe: {probed_url}",
        priority=priority,
        requester_email=requester_email,
        tags=tags or ["vip-site-probe"],
    )

    # dry-run mode -- return the payload as a preview
    dry_run = os.getenv("ZENDESK_DRY_RUN", "true").lower() != "false"
    if dry_run:
        result: dict[str, Any] = {
            "mode": "dry-run",
            "action": action,
            "ticket_id": ticket_id,
            "probed_url": probed_url,
            "payload": payload,
            "note": "Set ZENDESK_DRY_RUN=false to actually send.",
        }
        cache.store("submit_to_zendesk", probed_url, result)
        return result

    # live mode -- send to Zendesk
    result = await _send_to_zendesk(action, ticket_id, payload)
    result["probed_url"] = probed_url
    cache.store("submit_to_zendesk", probed_url, result)
    return result


def _build_payload(
    action: str,
    ticket_id: int | None,
    html_body: str,
    subject: str,
    priority: str,
    requester_email: str | None,
    tags: list[str],
) -> dict[str, Any]:
    """Build the Zendesk API payload."""
    comment: dict[str, Any] = {"html_body": html_body, "public": False}

    if action == "create":
        ticket: dict[str, Any] = {
            "subject": subject,
            "comment": comment,
            "priority": priority,
            "tags": tags,
        }
        if requester_email:
            ticket["requester"] = {"email": requester_email}
        return {"ticket": ticket}

    # update -- add internal note
    return {"ticket": {"comment": comment}}


async def _send_to_zendesk(
    action: str,
    ticket_id: int | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Make the actual Zendesk API call."""
    subdomain = os.getenv("ZENDESK_SUBDOMAIN", "")
    email = os.getenv("ZENDESK_EMAIL", "")
    token = os.getenv("ZENDESK_API_TOKEN", "")

    if not all([subdomain, email, token]):
        return {"error": "Missing Zendesk credentials. Check .env file."}

    base_url = f"https://{subdomain}.zendesk.com/api/v2"

    async with httpx.AsyncClient(
        timeout=HTTP_TIMEOUT,
        auth=(f"{email}/token", token),
    ) as client:
        try:
            if action == "create":
                resp = await client.post(f"{base_url}/tickets", json=payload)
            else:
                resp = await client.put(f"{base_url}/tickets/{ticket_id}", json=payload)

            if resp.status_code in (200, 201):
                data = resp.json()
                tid = data.get("ticket", {}).get("id", ticket_id)
                return {
                    "status": "success",
                    "action": action,
                    "ticket_id": tid,
                    "ticket_url": f"https://{subdomain}.zendesk.com/agent/tickets/{tid}",
                }
            else:
                return {
                    "status": "error",
                    "http_status": resp.status_code,
                    "detail": resp.text[:500],
                }
        except httpx.HTTPError as exc:
            return {"status": "error", "detail": str(exc)}
