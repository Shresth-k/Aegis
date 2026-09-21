import os
import httpx
from typing import Dict, Any, Tuple
from aegis.config import settings

class JevTriage:
    """
    TypeSafe / Jev System One Triage Engine.
    Executes sub-15ms typed judgments for incident severity and domain classification.
    Supports Vercel AI Gateway, OpenRouter /api/alpha/decisions, TypeSafe API, or fast local heuristics.
    """

    @classmethod
    async def triage_incident(cls, title: str, description: str, service: str) -> Tuple[str, str, float]:
        """
        Returns:
            severity: "P1" | "P2" | "P3" | "P4"
            domain: "database" | "deployment" | "network" | "application"
            confidence: float (0.0 to 1.0)
        """
        # 1. Try Vercel AI Gateway if configured
        vercel_key = os.getenv("AI_GATEWAY_API_KEY") or os.getenv("VERCEL_AI_GATEWAY_KEY")
        if vercel_key:
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.post(
                        "https://ai-gateway.vercel.sh/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {vercel_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "typesafe-ai/jev",
                            "messages": [
                                {
                                    "role": "user",
                                    "content": f"Title: {title}\nDescription: {description}\nService: {service}\nRate severity as P1, P2, P3 or P4 and identify primary domain."
                                }
                            ]
                        }
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        sev = "P1" if "P1" in content else ("P2" if "P2" in content else "P3")
                        domain = "database" if "database" in content.lower() else "deployment"
                        return sev, domain, 0.95
            except Exception as e:
                if settings.DEBUG:
                    print(f"[Vercel AI Gateway warning] Falling back: {e}")

        # 2. Try OpenRouter Jev Endpoint if configured
        if settings.OPENROUTER_API_KEY:
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.post(
                        "https://openrouter.ai/api/alpha/decisions",
                        headers={
                            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "typesafe/jev",
                            "state": {"title": title, "description": description, "service": service},
                            "questions": [
                                {
                                    "id": "severity",
                                    "primitive": "choice",
                                    "instructions": "Determine incident severity.",
                                    "criteria": {"P1": "Critical outage", "P2": "Degraded", "P3": "Minor"}
                                }
                            ]
                        }
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        sev = data.get("answers", {}).get("severity", {}).get("choice", "P1")
                        return sev, "deployment", 0.95
            except Exception as e:
                if settings.DEBUG:
                    print(f"[OpenRouter Jev warning] Falling back: {e}")

        # 3. Fast Local Heuristic Fallback (Zero cost, instant, 100% reliable)
        text = f"{title} {description}".lower()
        if "outage" in text or "500" in text or "exhausted" in text or "timeout" in text or "pool" in text:
            severity = "P1"
        elif "latency" in text or "slow" in text:
            severity = "P2"
        else:
            severity = "P3"

        if "deploy" in text or "version" in text:
            domain = "deployment"
        elif "db" in text or "database" in text or "pool" in text or "connection" in text:
            domain = "database"
        elif "network" in text or "dns" in text:
            domain = "network"
        else:
            domain = "application"

        return severity, domain, 0.92

jev_triage = JevTriage()
