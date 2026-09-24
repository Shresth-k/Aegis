import os
from typing import Optional, Literal
from pydantic import BaseModel, Field

def _load_env():
    """Simple, zero-dependency .env loader."""
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip()
                    if k not in os.environ:
                        os.environ[k] = v

_load_env()

class Settings(BaseModel):
    # Environment
    ENVIRONMENT: Literal["development", "staging", "production"] = Field(
        default_factory=lambda: os.getenv("ENVIRONMENT", "development")
    )
    DEBUG: bool = Field(
        default_factory=lambda: os.getenv("DEBUG", "true").lower() in ("1", "true", "yes")
    )

    # Main AI Model Provider
    LLM_PROVIDER: Literal["google", "openai", "anthropic", "mock"] = Field(
        default_factory=lambda: os.getenv("LLM_PROVIDER", "google")
    )
    LLM_MODEL: str = Field(
        default_factory=lambda: os.getenv("LLM_MODEL", "gemini-3.5-flash-lite")
    )
    LLM_API_KEY: Optional[str] = Field(
        default_factory=lambda: os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY")
    )
    OPENAI_API_KEY: Optional[str] = Field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY")
    )
    ANTHROPIC_API_KEY: Optional[str] = Field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY")
    )

    # TypeSafe / Jev Settings
    TYPESAFE_API_KEY: Optional[str] = Field(
        default_factory=lambda: os.getenv("TYPESAFE_API_KEY")
    )
    OPENROUTER_API_KEY: Optional[str] = Field(
        default_factory=lambda: os.getenv("OPENROUTER_API_KEY")
    )
    AI_GATEWAY_API_KEY: Optional[str] = Field(
        default_factory=lambda: os.getenv("AI_GATEWAY_API_KEY") or os.getenv("VERCEL_AI_GATEWAY_KEY")
    )
    USE_JEV_TRIAGE: bool = Field(
        default_factory=lambda: os.getenv("USE_JEV_TRIAGE", "true").lower() in ("1", "true", "yes")
    )
    USE_JEV_RERANKER: bool = Field(
        default_factory=lambda: os.getenv("USE_JEV_RERANKER", "true").lower() in ("1", "true", "yes")
    )

    # Needle 3 Local Settings
    ENABLE_NEEDLE3_LOCAL: bool = Field(
        default_factory=lambda: os.getenv("ENABLE_NEEDLE3_LOCAL", "false").lower() in ("1", "true", "yes")
    )

    # AcmeCloud Simulated Enterprise Connectivity
    ACME_CLOUD_API_URL: str = Field(
        default_factory=lambda: os.getenv("ACME_CLOUD_API_URL", "http://localhost:8001")
    )
    MOCK_ACME_CLOUD: bool = Field(
        default_factory=lambda: os.getenv("MOCK_ACME_CLOUD", "true").lower() in ("1", "true", "yes")
    )
    PROMETHEUS_URL: str = Field(
        default_factory=lambda: os.getenv("PROMETHEUS_URL", "http://localhost:9090")
    )

    # Model Context Protocol (MCP) Settings
    USE_MCP: bool = Field(
        default_factory=lambda: os.getenv("USE_MCP", "true").lower() in ("1", "true", "yes")
    )
    MCP_SERVER_TRANSPORT: Literal["direct", "stdio", "sse"] = Field(
        default_factory=lambda: os.getenv("MCP_SERVER_TRANSPORT", "direct")
    )

    # Tracing
    TRACE_LOG_PATH: str = Field(
        default_factory=lambda: os.getenv("TRACE_LOG_PATH", "traces.jsonl")
    )

settings = Settings()
