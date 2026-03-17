---
description: "Run a full site probe and add the findings as an internal note on an existing Zendesk ticket."
---

# /add-to-ticket {url} {ticket_id}

Run a full diagnostic probe against `{url}`, then add the results as an internal note on Zendesk ticket `{ticket_id}`.

## Steps

1. Run the `/probe` skill workflow (probe_site, check_plugins, check_security)
2. Call `submit_to_zendesk_tool` with `action="update"` and the given `ticket_id`
3. If `ZENDESK_DRY_RUN=true` (default), show the internal note preview
4. If `ZENDESK_DRY_RUN=false`, confirm the note was added with ticket URL
