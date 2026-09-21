import os
import json
import httpx
from typing import Dict, Any, Tuple
from aegis.config import settings

class JevTriage:
    """
    Intelligent Triage Engine.
    Tier 1: Vercel AI Gateway (typesafe-ai/jev).
    Tier 2: Main AI LLM (Gemini / OpenAI) with structured JSON reasoning for genuine intelligence.
    Tier 3: Local heuristic (last-resort crash-prevention safety net).
    """

    @classmethod
    async def triage_incident(cls, title: str, description: str, service: str) -> Tuple[str, str, float]:
        """
        Returns:
            severity: "P1" | "P2" | "P3" | "P4"
            domain: "database" | "deployment" | "network" | "application"
            confidence: float (0.0 to 1.0)
        """
        # --- Tier 1: Vercel AI Gateway (Jev) ---
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
                    print(f"[Vercel AI Gateway] Fallback to Tier 2: {e}")

        # --- Tier 2: Main AI LLM Intelligent Triage (Gemini / OpenAI) ---
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
        if gemini_key:
            try:
                # Use Google GenAI SDK if available
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=gemini_key)
                prompt = f"""
                You are Aegis Incident Triage AI.
                Analyze the following incident alert and return a JSON object with:
                - severity: "P1" (critical outage/error rate > 20%), "P2" (degraded/high latency), "P3" (minor), or "P4" (cosmetic)
                - domain: "database", "deployment", "network", or "application"
                - confidence: float between 0.0 and 1.0

                INCIDENT:
                Title: {title}
                Description: {description}
                Service: {service}
                """
                response = client.models.generate_content(
                    model=settings.LLM_MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                res_data = json.loads(response.text)
                return res_data.get("severity", "P1"), res_data.get("domain", "deployment"), float(res_data.get("confidence", 0.92))
            except Exception as e:
                if settings.DEBUG:
                    print(f"[Gemini Triage] Fallback to Tier 3: {e}")

        # --- Tier 3: Local Heuristic (Last-resort crash safety net) ---
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

        return severity, domain, 0.85

jev_triage = JevTriage()
