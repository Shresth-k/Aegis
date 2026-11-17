from aegis.mcp.client import AcmeMCPClient, mcp_client

def __getattr__(name: str):
    if name == "mcp_server":
        from aegis.mcp.server import mcp_server
        return mcp_server
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["AcmeMCPClient", "mcp_client", "mcp_server"]

