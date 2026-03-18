---
name: "probe"
description: "Run a full WordPress site diagnostic -- probes site health, plugin status, and security exposures, then presents a unified report."
argument-hint: "[url]"
---

# /probe {url}

Run `probe_tool` against `{url}`. The tool executes `probe_site`, `check_plugins`, and `check_security` in sequence and returns a combined MCP App report.

## Steps

1. Call `probe_tool` with the given URL
2. If the client does not automatically render the MCP App, present the combined results as a structured diagnostic report with three sections:
   - Site health (identity, infrastructure, CDN, REST API)
   - Plugin status (table with version currency and health flags)
   - Security findings (checklist with severity badges)
   - Add the output's timestamp
