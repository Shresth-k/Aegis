import os
import json
import asyncio
import httpx
from typing import Dict, Any, Tuple
from aegis.config import settings

class JevTriage:
    """
    Intelligent Triage Engine.
    Tier 1: Live Vercel AI Gateway (typesafe-ai/jev) via /v1/evaluate.
    Tier 2: Main AI LLM (Gemini 3.5 Flash-Lite) with structured JSON reasoning.
    Tier 3: Local heuristic (last-resort safety net).
    """

    @classmethod
    async def triage_incident(cls, title: str, description: str, service: str) -> Tuple[str, str, float]:
        """
        Returns:
            severity: "P1" | "P2" | "P3" | "P4"
            domain: "database" | "deployment" | "network" | "application"
            confidence: float (0.0 to 1.0)
        """
        # --- Tier 1: Direct TypeSafe AI or Vercel AI Gateway (typesafe-ai/jev) ---
        typesafe_key = os.getenv("TYPESAFE_API_KEY")
        vercel_key = os.getenv("AI_GATEWAY_API_KEY") or os.getenv("VERCEL_AI_GATEWAY_KEY")
        active_key = typesafe_key or vercel_key
        if active_key:
            target_url = "https://api.typesafe.ai/v1/systemone" if typesafe_key else "https://ai-gateway.vercel.sh/v1/evaluate"
            target_model = "jev-latest" if typesafe_key else "typesafe-ai/jev"
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(
                        target_url,
                        headers={
                            "Authorization": f"Bearer {active_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": target_model,
                            "state": {
                                "title": title,
                                "description": description,
                                "service": service
                            },
                            "questions": {
                                "severity": {
                                    "type": "choice",
                                    "instructions": "Determine incident severity level.",
                                    "criteria": {
                                        "P1": "Critical outage, service completely unavailable, or elevated 5xx errors",
                                        "P2": "Degraded performance, high latency, or intermittent errors",
                                        "P3": "Minor issue or non-critical background error",
                                        "P4": "Informational or cosmetic notice"
                                    }
                                },
                                "domain": {
                                    "type": "choice",
                                    "instructions": "Identify the primary failing domain.",
                                    "criteria": {
                                        "deployment": "Recent software release, rollback, or version change",
                                        "database": "Connection pool exhaustion, slow queries, or DB timeouts",
                                        "network": "DNS failure, packet loss, or gateway timeouts",
                                        "application": "Unhandled code exception, memory leak, or crash"
                                    }
                                }
                            }
                        }
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        answers = data.get("answers", {})
                        sev = answers.get("severity", {}).get("choice", "P1")
                        domain = answers.get("domain", {}).get("choice", "deployment")
                        conf = float(answers.get("severity", {}).get("confidence", 0.90))
                        return sev, domain, conf
            except Exception as e:
                if settings.DEBUG:
                    print(f"[Vercel Jev Triage error] Falling back to Tier 2: {e}")

        # --- Tier 2: Main AI LLM Intelligent Triage (Gemini 3.5 Flash-Lite) ---
        gemini_key = os.getenv("GEMINI_API_KEY") or settings.LLM_API_KEY
        if gemini_key:
            try:
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
                response = await asyncio.to_thread(
                    client.models.generate_content,
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
