# VIP Site Probe

MCP server that probes WordPress sites via their public REST API and HTTP headers, producing CSE intake reports and optionally pushing findings to Zendesk.

## Quick start

```bash
# install in editable mode
pip install -e ".[dev]"

# copy env template and fill in Zendesk credentials (optional)
cp .env.example .env

# run the MCP server (stdio transport)
python -m vip_site_probe
```

## MCP tools

| Tool | Description |
|------|-------------|
| `probe_site_tool` | Full site diagnostic -- identity, infrastructure, REST API, CDN |
| `check_plugins_tool` | Plugin discovery via REST API namespaces + wordpress.org cross-reference |
| `check_security_tool` | Security exposure scan -- xmlrpc, user enum, headers, directory listing |
| `submit_to_zendesk_tool` | Push findings to Zendesk (create ticket or add internal note) |

## Skills

| Skill | Description |
|-------|-------------|
| `/probe {url}` | Run all three probes and present a unified report |
| `/file-ticket {url}` | Full probe + create a Zendesk ticket |
| `/add-to-ticket {url} {ticket_id}` | Full probe + add internal note to existing ticket |

## Configuration

Copy `.env.example` to `.env` and fill in:

```
ZENDESK_SUBDOMAIN=your-subdomain
ZENDESK_EMAIL=agent@example.com
ZENDESK_API_TOKEN=your-api-token
ZENDESK_DRY_RUN=true
```

When `ZENDESK_DRY_RUN=true` (default), Zendesk calls are previewed but not sent.

## Development

```bash
pytest                  # run tests
ruff check .            # lint
mypy src/               # type check
```

## Architecture

See [md/tool_20260316_prep.md](md/tool_20260316_prep.md) for the full design doc.

--- 

# Example investigation - /probe techcrunch

The report for <strong>`/probe` techcrunch</strong> on March 16th contained 2 warnings:

* WordPress version exposed: Version 6.9.4 visible in meta generator tag (facilitates targeted attacks)
* <strong>xmlrpc.php accessible:</strong> Enabled protocol for remote publishing (known brute-force and DDoS vector)

The same probe one day later showed: "Summary: One warning. All 6 security headers present. <strong>xmlrpc.php is now blocked</strong> (improved since last run). Only outstanding exposure is the WP version in the meta generator tag."

How plausible is it that Crunchbase fixed an issue overnight between these runs?

The Tool uses `_check_xmlrpc()` to send a single POST with `<methodCall/>` and checks for **HTTP 200 + `content-type: xml`**:

| Run | Result | HTTP status |
|-----|--------|-------------|
| 2026-03-16 | `xmlrpc.php accessible` (warning) | 200 + XML content-type |
| 2026-03-17 | `xmlrpc.php blocked or not found` (info) | 403 |

## Theories

### Vendor applied fix (least plausible)

- 403 is a *deliberate* status, if a real server was hit, someone configured this.
- VIP sites block xmlrpc.php at platform level, initial "accessible" result was the anomaly.
- The timeline is tight but not impossible for a platform-level toggle on VIP Go.

### Scan/probe drift (more plausible)

- **CDN edge node variability** - Automattic's VIP infrastructure uses Fastly. Different edge nodes may have different WAF rule sets or config rollout states. The 2 requests from the same machine may have landed on different nodes or data centers.  
- **WAF adaptive blocking** (feature) - Some WAFs (Fastly's Next-Gen WAF, WordFence at the CDN layer) will initially permit a malformed XML POST but flag the source IP. The *second* probe from the same IP then hits a 403.  
- **Single-sample fragility.** - `/probe` makes exactly one POST request with no retry or verification. An edge condition (connection reset, 503 briefly, others) that doesn't throw an `httpx.HTTPError` goes to `else` and report 403.  
- **No corroborating headers.** A real infrastructure change by TechCrunch/VIP Ops could be reflected in a deployment timestamp header or a version change. Nothing in `/probe` output suggests any other configuration changed between the 2 runs.

The single-sample POST probe is susceptible to CDN edge variability and adaptive WAF blocking, especially when run from the same IP twice. The initial "accessible" result was more likely a probe artifact. VIP environment does support platform-level xmlrpc blocks:

- Explicit XML-RPC platform protections: https://docs.wpvip.com/security-controls/wordpress/xml-rpc/ - 10 req per 30 sec, then 1h IP block - could be tested specifically. Initial tests look random (some 403, but mostly status 200, including #11 - however, it's unrealistic to expected this to be deterministic).
- Dynamic endpoint abuse protections at platform level: https://docs.wpvip.com/security/infrastructure-that-mitigates-security-threats/ - states that dynamic security protocols protect wp-login.php and xmlrpc.php, and that they can fully block automated attack attempts
- XML-RPC behavior is configurable per environment - https://docs.wpvip.com/security-controls/wordpress/ and https://docs.wpvip.com/security-controls/wordpress/xml-rpc/

### Interpretation is not correct (most plausible)

`/probe` treats 200 + XML as “xmlrpc.php accessible” -- too coarse for VIP/WordPress behavior. Alternative conclusion:
- xmlrpc.php is reachable 
- auth posture is unknown from this test alone 
- rate limiting / abuse controls are not deterministically triggered (not by /probe and not by 11r/30s burst test)

### Summary

TechCrunch’s XML-RPC endpoint appears reachable (not unusual). Our tests do not show a block-by-default config, and also do not prove dangerous openness. The observed mix of 200 and 403 suggests conditional or edge-dependent protections. Most likely, `/probe` currently overstates risk by equating 200 text/xml with “accessible” in a security-significant sense.

**Tool improvements:** `/probe` needs a verification step: ideally from a second POST vantage point, or corroborating with a GET to `/xmlrpc.php`. Planned: `/probe` to distinguish:

- endpoint reachable,
- auth-gated,
- Jetpack/app-password-only behavior,
- explicit edge/WAF block.

