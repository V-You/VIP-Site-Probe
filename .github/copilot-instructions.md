# Project overview

VIP Site Probe is an MCP server (Python / FastMCP) that probes WordPress sites via their public REST API and HTTP headers, producing CSE intake reports with rich UI (MCP Apps) and optionally pushing findings to Zendesk.

See [md/tool_20260316_prep.md](../md/tool_20260316_prep.md) for full design doc -- architecture, data sources, MCP tools, and conversation flows.

# General

- Before changing any file, create a backup copy, extension .bak.YYYYMMDD, in bak/
- If code seems missing anywhere, look in bak/ for most recent version and cherry pick from there
- Use PyLance MCP server when needed for Python code
- Use Context7 MCP server to get the latest documentation for libraries and frameworks
- Use Chrome DevTools MCP server to browse the web (or your built-in web tool)

# Tech stack

- Python 3.10+ -- use modern syntax (match/case, `X | Y` unions, etc.)
- FastMCP -- MCP server framework; use MCP Apps for rich inline UI
- httpx -- async HTTP client for all outbound requests (probing sites, wordpress.org API, Zendesk)
- python-dotenv -- load `.env` for secrets (Zendesk creds, `ZENDESK_DRY_RUN`)
- Standard library only where sufficient: `json`, `re`, `html.parser`, `urllib.parse`, `statistics`

# Architecture

```
src/
  vip_site_probe/
    __init__.py
    server.py          # FastMCP server entry point, tool registrations
    probes/
      site.py          # probe_site logic
      plugins.py       # check_plugins logic
      security.py      # check_security logic
    zendesk.py         # submit_to_zendesk logic
    cache.py           # in-memory result cache (last probe)
    formatting.py      # HTML/Markdown formatters for MCP App cards
```

- Each MCP tool maps to a module under `probes/` or a top-level module
- Result cache is in-memory, holds the most recent probe output for Zendesk submission
- All HTTP calls go through httpx async client -- never use `requests` or `urllib`
- Zendesk calls are gated by `ZENDESK_DRY_RUN` env var (default `true`)

# Build and test

```bash
# install
pip install -e ".[dev]"

# run server (stdio transport for MCP)
python -m vip_site_probe

# tests
pytest

# lint + type check
ruff check .
mypy src/
```

# Conventions

- All HTTP probing functions must be async (httpx async client)
- Timeout all outbound HTTP requests (10s default, configurable)
- Never send credentials or auth tokens to target WordPress sites -- probes use public endpoints only
- Zendesk API auth uses basic auth (`email/token:{api_token}`) -- credentials come from env vars only
- One MCP tool = one Python function decorated with `@mcp.tool()`
- MCP App UI cards use the FastMCP Apps API -- structured data, not raw HTML strings
- Cache probe results in memory so `submit_to_zendesk` can reference the last run without re-probing

# Skills

- Skills are located in `.github/skills/`

# Code style

- Do NOT use title capitalization in comments etc, use sentence case instead
- Do NOT use m-dashes in comments, use n-dashes instead (wrapped in spaces)
- Do NOT use emojis in comments or code -- unless asked (monochrome only)
- Use the KISS principle in code and comments -- "keep it simple"
- Use the DRY principle in code and comments -- "don't repeat yourself"

# Writing style

- Do NOT use title capitalization, use sentence case instead
- Do NOT use m-dashes, use n-dashes instead
- Do NOT use emojis -- unless asked (monochrome only)
