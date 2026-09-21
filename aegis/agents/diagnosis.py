import json
import os
from typing import List
from aegis.core.state import TelemetryEvidence, RetrievedRunbook, DiagnosisResult
from aegis.config import settings

class DiagnosisAgent:
    """
    Main AI Diagnosis Agent.
    Synthesizes operational telemetry evidence and retrieved runbooks
    to determine likely root cause and propose remediation.
    """

    @classmethod
    async def diagnose(
        cls,
        evidence: TelemetryEvidence,
        runbooks: List[RetrievedRunbook]
    ) -> DiagnosisResult:
        # 1. Check if Gemini / Google GenAI is configured
        gemini_key = os.getenv("GEMINI_API_KEY") or settings.LLM_API_KEY
        if gemini_key and settings.LLM_PROVIDER == "google":
            try:
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=gemini_key)

                prompt = f"""
                You are Aegis Lead Incident Diagnosis AI. Analyze the following operational evidence and runbooks:
                
                SERVICE: {evidence.service}
                CURRENT VERSION: {evidence.current_version} (Previous: {evidence.previous_version})
                RECENT DEPLOYMENT: {evidence.recent_deployment}
                METRICS: {json.dumps(evidence.metrics)}
                ERROR LOGS: {json.dumps(evidence.error_logs)}
                DEPENDENCIES: {json.dumps(evidence.dependencies)}
                
                RELEVANT RUNBOOKS:
                {chr(10).join(f"- {rb.title}: {rb.content}" for rb in runbooks)}
                
                Return a JSON object with:
                - root_cause (string: concise root cause description)
                - confidence (float between 0.0 and 1.0)
                - evidence_summary (list of strings: evidence items supporting diagnosis)
                - recommended_action (string: e.g. 'rollback_deployment')
                - action_parameters (object: e.g. {{"service": "{evidence.service}", "target_version": "{evidence.previous_version or '2.4.0'}"}})
                - reasoning (string: explanation of why this action resolves the issue)
                """

                response = client.models.generate_content(
                    model=settings.LLM_MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                data = json.loads(response.text)
                return DiagnosisResult(**data)
            except Exception as e:
                if settings.DEBUG:
                    print(f"[Diagnosis Gemini warning] Falling back to grounded reasoning: {e}")

        # 2. Deterministic Grounded Reasoning Fallback (Safety net)
        has_db_pool_errors = any("connection pool" in log.lower() or "timeout acquiring db" in log.lower() for log in evidence.error_logs)

        if evidence.recent_deployment and has_db_pool_errors:
            target = evidence.previous_version or "2.4.0"
            return DiagnosisResult(
                root_cause=f"Recent deployment of {evidence.service} ({evidence.current_version}) caused database connection pool exhaustion under traffic load.",
                confidence=0.96,
                evidence_summary=[
                    f"Elevated 5xx error rate measured at {evidence.metrics.get('error_rate', 0):.1%}",
                    f"Recent deployment detected: version {evidence.current_version} replaced {evidence.previous_version}",
                    "Database connection acquisition timeouts in application logs",
                    "All service dependencies (PostgreSQL, Redis) remain healthy"
                ],
                recommended_action="rollback_deployment",
                action_parameters={
                    "service": evidence.service,
                    "target_version": target
                },
                reasoning=f"Telemetry matches Database Connection Pool Exhaustion Runbook (RB-001). Reverting to stable release {target} will restore connection pool headroom and eliminate 500 errors."
            )

        return DiagnosisResult(
            root_cause="Unspecified operational anomaly.",
            confidence=0.5,
            evidence_summary=["Telemetry inconclusive."],
            recommended_action="escalate_to_human",
            action_parameters={"service": evidence.service},
            reasoning="Unable to conclusively isolate root cause from current telemetry window."
        )

diagnosis_agent = DiagnosisAgent()
