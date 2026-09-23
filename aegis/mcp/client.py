"""
AcmeCloud MCP Client and Host Adapter for Aegis.
Provides clean async methods to discover and invoke AcmeCloud MCP tools:
- get_service_logs
- get_metrics
- rollback_deployment
- get_incident_state

Supports both direct in-memory invocation (fastest, robust for tests and microservices)
and out-of-process stdio transport via the official MCP ClientSession.
"""

from __future__ import annotations

import sys
import json
from typing import Dict, Any, List, Optional
from aegis.config import settings


class AcmeMCPClient:
    """
    Client adapter connecting Aegis agentic workflows to the AcmeCloud MCP Server.
    """

    def __init__(self, transport: Optional[str] = None):
        self.transport = transport or settings.MCP_SERVER_TRANSPORT

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool on the AcmeCloud MCP server and unpack the result.
        """
        if self.transport == "direct":
            from aegis.mcp.server import mcp_server
            result = await mcp_server.call_tool(name, arguments)
            return self._unpack_mcp_result(result)
        elif self.transport == "stdio":
            import os
            from pathlib import Path
            from mcp.client.stdio import stdio_client, StdioServerParameters
            from mcp.client.session import ClientSession

            project_root = Path(__file__).resolve().parent.parent.parent
            server_params = StdioServerParameters(
                command=sys.executable,
                args=["-m", "aegis.mcp.server"],
                env=dict(os.environ),
                cwd=project_root,
            )
            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool(name, arguments)
                    return self._unpack_mcp_result(result)
        else:
            from aegis.mcp.server import mcp_server
            result = await mcp_server.call_tool(name, arguments)
            return self._unpack_mcp_result(result)

    def _unpack_mcp_result(self, result: Any) -> Any:
        """
        Unpack structured data, JSON strings, or plain text from an MCP tool result.
        """
        if hasattr(result, "structured_content") and result.structured_content is not None:
            if isinstance(result.structured_content, dict) and "result" in result.structured_content:
                return result.structured_content["result"]
            return result.structured_content

        if hasattr(result, "content") and result.content:
            text_blocks = []
            for item in result.content:
                if hasattr(item, "text"):
                    text_blocks.append(item.text)

            if len(text_blocks) == 1:
                raw_text = text_blocks[0]
                try:
                    return json.loads(raw_text)
                except (json.JSONDecodeError, TypeError):
                    return raw_text
            elif len(text_blocks) > 1:
                # Check if all blocks are strings (e.g. list of logs)
                return text_blocks

        return result

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        List all available tools on the AcmeCloud MCP server.
        """
        if self.transport == "stdio":
            import os
            from pathlib import Path
            from mcp.client.stdio import stdio_client, StdioServerParameters
            from mcp.client.session import ClientSession

            project_root = Path(__file__).resolve().parent.parent.parent
            server_params = StdioServerParameters(
                command=sys.executable,
                args=["-m", "aegis.mcp.server"],
                env=dict(os.environ),
                cwd=project_root,
            )
            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    res = await session.list_tools()
                    return [
                        {
                            "name": t.name,
                            "description": t.description,
                            "parameters": getattr(t, "inputSchema", {}),
                        }
                        for t in res.tools
                    ]
        else:
            from aegis.mcp.server import mcp_server
            tools = await mcp_server.list_tools()
            return [
                {
                    "name": t.name,
                    "description": t.description,
                    "parameters": getattr(t, "inputSchema", {}),
                }
                for t in tools
            ]

    async def get_service_logs(
        self,
        service: str,
        query: str = "error",
        window: str = "15m",
    ) -> List[str]:
        """
        Retrieve service log entries matching query filters and time window from AcmeCloud via MCP.
        """
        res = await self.call_tool(
            "get_service_logs",
            {"service": service, "query": query, "window": window},
        )
        if isinstance(res, list):
            return res
        elif isinstance(res, str):
            return [res]
        return []

    async def get_metrics(
        self,
        service: str,
        window: str = "15m",
    ) -> Dict[str, Any]:
        """
        Fetch operational telemetry metrics for a service via MCP.
        """
        res = await self.call_tool(
            "get_metrics",
            {"service": service, "window": window},
        )
        return res if isinstance(res, dict) else {}

    async def rollback_deployment(
        self,
        service: str,
        target_version: str,
    ) -> Dict[str, Any]:
        """
        Execute a deployment rollback for a service to a target version via MCP.
        """
        res = await self.call_tool(
            "rollback_deployment",
            {"service": service, "target_version": target_version},
        )
        return res if isinstance(res, dict) else {}

    async def get_incident_state(
        self,
        incident_id: str,
    ) -> Dict[str, Any]:
        """
        Query the current status and metadata of an operational incident via MCP.
        """
        res = await self.call_tool(
            "get_incident_state",
            {"incident_id": incident_id},
        )
        return res if isinstance(res, dict) else {}

    async def get_service_health(
        self,
        service: str,
    ) -> Dict[str, Any]:
        """
        Fetch operational health status for a service via MCP.
        """
        res = await self.call_tool(
            "get_service_health",
            {"service": service},
        )
        return res if isinstance(res, dict) else {}

    async def list_incidents(self) -> List[Dict[str, Any]]:
        """
        List all operational incidents via MCP.
        """
        res = await self.call_tool(
            "list_incidents",
            {},
        )
        return res if isinstance(res, list) else []


mcp_client = AcmeMCPClient()

