---
name: "probe"
description: "Run a full WordPress site diagnostic -- probes site health, plugin status, and security exposures, then presents a unified report."
argument-hint: "[url]"
---

# /probe {url}

Run `probe_site`, `check_plugins`, and `check_security` in sequence against `{url}`, then present a combined report.

## Steps

1. Call `probe_site_tool` with the given URL
2. Call `check_plugins_tool` with the same URL
3. Call `check_security_tool` with the same URL
4. Present the combined results as a structured diagnostic report with three sections:
   - Site health (identity, infrastructure, CDN, REST API)
   - Plugin status (table with version currency and health flags)
   - Security findings (checklist with severity badges)
   - Add the output's timestamp
