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