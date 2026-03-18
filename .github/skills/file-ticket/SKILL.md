---
name: "file-ticket"
description: "Run a full site probe and create a new Zendesk ticket with the findings."
argument-hint: "[url]"
---

# /file-ticket {url}

Run a full diagnostic probe against `{url}`, then create a new Zendesk ticket with the results.

## Steps

1. Run the `/probe` skill workflow (probe_site, check_plugins, check_security)
2. Call `submit_to_zendesk_tool` with `action="create"`
   - Subject defaults to "Site probe: {url}" unless the user specifies otherwise
   - Priority defaults to "normal"
   - Tags: `["vip-site-probe"]`
3. If `ZENDESK_DRY_RUN=true` (default), show the ticket preview
4. If `ZENDESK_DRY_RUN=false`, confirm the ticket was created with the ticket ID and URL
