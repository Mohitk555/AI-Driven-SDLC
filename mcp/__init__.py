"""MCP (Model Context Protocol) layer for AI Engineering OS.

Provides a unified interface for agents to interact with external tools
such as Jira, GitHub, Slack, and Google Calendar.
"""

from mcp.mcp_server import MCPServer

__all__ = ["MCPServer"]
