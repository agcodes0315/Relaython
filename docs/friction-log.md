## Entry 1

**Date:** October 5, 2026  
**Tool / API / SDK:** MCP Python SDK  
**Task attempted:** Run the first Relay MCP server.

**Steps taken:**
1. Created a Python virtual environment.
2. Installed the latest `mcp` package using pip.
3. Attempted to import `FastMCP` from `mcp.server.fastmcp`.

**Expected result:**  
The MCP server should start successfully.

**Actual result:**  
The server failed with `ModuleNotFoundError` because MCP SDK 2.x renamed `FastMCP` to `MCPServer`.

**Severity:** Low

**Workaround:**  
Updated the import to `from mcp.server.mcpserver import MCPServer` and replaced `FastMCP` with `MCPServer`.

**Suggested improvement:**  
Beginner documentation and hackathon starter examples should clearly distinguish MCP Python SDK v1 and v2 code to avoid version-mismatch errors.