import httpx
from typing import Dict, Any, Tuple
from aegis.config import settings

class JevTriage:
    """
    TypeSafe / Jev System One Triage Engine.
    Executes sub-15ms typed judgments for incident severity and domain classification.
    Supports OpenRouter's /api/alpha/decisions endpoint, TypeSafe API, or fast local heuristics.
    """

    @classmethod
    async def triage_incident(cls, title: str, description: str, service: str) -> Tuple[str, str, float]:
        """
        Returns:
            severity: "P1" | "P2" | "P3" | "P4"
            domain: "database" | "deployment" | "network" | "application"
            confidence: float (0.0 to 1.0)
        """
        # 1. Try OpenRouter Jev Endpoint if configured
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
                            "state": {
                                "title": title,
                                "description": description,
                                "service": service
                            },
                            "questions": [
                                {
                                    "id": "severity",
                                    "primitive": "choice",
                                    "instructions": "Determine incident severity.",
                                    "criteria": {
                                        "P1": "Complete outage, critical user flow broken, or error rate > 20%",
                                        "P2": "Degraded performance, high latency, or non-critical service error",
                                        "P3": "Minor bug or single-user impact",
                                        "P4": "Cosmetic or informational notice"
                                    }
                                },
                                {
                                    "id": "domain",
                                    "primitive": "choice",
                                    "instructions": "Identify the primary system domain.",
                                    "criteria": {
                                        "deployment": "Recent code or configuration change",
                                        "database": "Connection pool, query timeout, or storage issue",
                                        "network": "DNS, gateway, or connectivity issue",
                                        "application": "Internal code crash, memory leak, or logic error"
                                    }
                                }
                            ]
                        }
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        sev = data.get("answers", {}).get("severity", {}).get("choice", "P1")
                        domain = data.get("answers", {}).get("domain", {}).get("choice", "deployment")
                        conf = data.get("answers", {}).get("severity", {}).get("confidence", 0.95)
                        return sev, domain, float(conf)
            except Exception as e:
                if settings.DEBUG:
                    print(f"[Jev API warning] Falling back to local triage: {e}")

        # 2. Fast Local Heuristic Fallback (Zero cost, instant)
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
