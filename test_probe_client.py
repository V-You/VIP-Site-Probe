#!/usr/bin/env python3
"""Quick test client to call probe_tool via stdio MCP transport."""

import asyncio
import json
import sys
import subprocess
from typing import Any

async def call_probe_tool(url: str) -> dict[str, Any]:
    """Call probe_tool via stdio MCP protocol."""
    
    # Start the server process
    proc = subprocess.Popen(
        [sys.executable, "-m", "vip_site_probe"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    
    # Initialize MCP protocol
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0"},
        },
    }
    
    # Send initialize
    proc.stdin.write(json.dumps(init_request) + "\n")
    proc.stdin.flush()
    
    # Read initialize response
    response_line = proc.stdout.readline()
    print(f"Init response: {response_line}")
    
    # List tools
    tools_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
    }
    proc.stdin.write(json.dumps(tools_request) + "\n")
    proc.stdin.flush()
    
    response_line = proc.stdout.readline()
    print(f"Tools response: {response_line}")
    
    # Call probe_tool
    tool_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "probe_tool",
            "arguments": {"url": url},
        },
    }
    proc.stdin.write(json.dumps(tool_request) + "\n")
    proc.stdin.flush()
    
    # Read tool response
    response_line = proc.stdout.readline()
    print(f"Tool response: {response_line}")
    
    proc.stdin.close()
    proc.wait()
    
    return json.loads(response_line)

if __name__ == "__main__":
    import os
    os.chdir("/home/snlr/code/VIP-Site-Probe")
    result = asyncio.run(call_probe_tool("https://techcrunch.com"))
    print(json.dumps(result, indent=2))
