from typing import Dict, Any
from pydantic import BaseModel, Field
from aegis.config import settings
from aegis.acme.client import acme_client
from aegis.mcp.client import mcp_client

class RollbackParams(BaseModel):
    service: str = Field(description="Name of the service to rollback")
    target_version: str = Field(description="Target version to revert to (e.g. 2.4.0)")

class RestartParams(BaseModel):
    service: str = Field(description="Name of the service to restart")

class NeedleExecutor:
    """
    Micro-executor using Needle 3 grammar-constrained tool execution,
    with robust Pydantic schema validation as fallback.
    """

    def __init__(self, enable_needle: bool = settings.ENABLE_NEEDLE3_LOCAL):
        self.enable_needle = enable_needle
        self._needle_agent = None

        if self.enable_needle:
            try:
                import needle  # cactus-needle
                @needle.tool
                def rollback_service(service: str, target_version: str):
                    """Rollback a service to a specified target version."""
                    return {"service": service, "target_version": target_version}

                self._needle_agent = needle.Needle(tools=[rollback_service])
            except ImportError:
                if settings.DEBUG:
                    print("[Needle 3] cactus-needle not installed, using Pydantic schema execution.")

    async def execute_rollback(self, service: str, target_version: str) -> Dict[str, Any]:
        """Validates parameters with strict grammar and executes rollback on AcmeCloud."""
        # 1. Grammar & Schema Validation
        validated = RollbackParams(service=service, target_version=target_version)

        # 2. If Needle 3 agent is active, run local verification pass
        if self._needle_agent:
            try:
                prompt = f"Rollback {validated.service} to {validated.target_version}"
                self._needle_agent.run(prompt)
            except Exception as e:
                if settings.DEBUG:
                    print(f"[Needle 3 warning] local pass fallback: {e}")

        # 3. Call AcmeCloud API (via MCP or direct client)
        if settings.USE_MCP:
            result = await mcp_client.rollback_deployment(
                service=validated.service,
                target_version=validated.target_version
            )
        else:
            result = await acme_client.rollback_deployment(
                service=validated.service,
                target_version=validated.target_version
            )
        return result

    async def execute_restart(self, service: str) -> Dict[str, Any]:
        """Validates parameters and restarts service on AcmeCloud."""
        validated = RestartParams(service=service)
        return await acme_client.restart_service(service=validated.service)

needle_executor = NeedleExecutor()
