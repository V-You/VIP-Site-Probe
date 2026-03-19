---
name: "file-ticket"
description: "Run a full site probe and create a new Zendesk ticket with the findings."
argument-hint: "[url]"
---

# /file-ticket {url}

Run a full diagnostic probe against `{url}`, then create a new Zendesk ticket with the results.

## Steps

1. Call `file_ticket_tool` with `url`
   - The tool runs the full probe workflow and then calls Zendesk create in one MCP tool result
   - Subject defaults to "Site probe: {url}" unless the user specifies otherwise
   - Priority defaults to "normal"
   - Tags default to `["vip-site-probe"]`
2. If `ZENDESK_DRY_RUN=true` (default), show the unified rich preview card from `file_ticket_tool`
3. If `ZENDESK_DRY_RUN=false`, confirm the ticket was created with the ticket ID and URL
