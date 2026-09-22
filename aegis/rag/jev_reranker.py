import os
import json
import httpx
from typing import List
from aegis.core.state import RetrievedRunbook
from aegis.config import settings

class JevReranker:
    """
    Intelligent Reranking Engine.
    Tier 1: Live Vercel AI Gateway (typesafe-ai/jev) via /v1/evaluate.
    Tier 2: Main AI LLM (Gemini 3.5 Flash-Lite) semantic scoring.
    Tier 3: Local heuristic (safety net).
    """

    @classmethod
    async def rerank(cls, incident_symptoms: str, documents: List[RetrievedRunbook]) -> List[RetrievedRunbook]:
        if not documents:
            return []

        # --- Tier 1: Live Vercel AI Gateway (typesafe-ai/jev) ---
        vercel_key = os.getenv("AI_GATEWAY_API_KEY") or os.getenv("VERCEL_AI_GATEWAY_KEY")
        if vercel_key:
            try:
                questions = {}
                for d in documents:
                    questions[f"relevance_{d.doc_id}"] = {
                        "type": "boolean",
                        "instructions": f"Does the document titled '{d.title}' describe the resolution or runbook for these symptoms: '{incident_symptoms}'?"
                    }

                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(
                        "https://ai-gateway.vercel.sh/v1/evaluate",
                        headers={
                            "Authorization": f"Bearer {vercel_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "typesafe-ai/jev",
                            "state": {
                                "symptoms": incident_symptoms,
                                "documents": [{"doc_id": d.doc_id, "title": d.title} for d in documents]
                            },
                            "questions": questions
                        }
                    )
                    if resp.status_code == 200:
                        answers = resp.json().get("answers", {})
                        for d in documents:
                            ans = answers.get(f"relevance_{d.doc_id}", {})
                            # Boolean primitive returns probability of true
                            prob = ans.get("probability", ans.get("probabilities", {}).get("true", 0.5))
                            d.score = float(prob)
                        documents.sort(key=lambda x: x.score, reverse=True)
                        return documents
            except Exception as e:
                if settings.DEBUG:
                    print(f"[Vercel Jev Reranker error] Falling back to Tier 2: {e}")

        # --- Tier 2: Main AI LLM Intelligent Scoring (Gemini 3.5 Flash-Lite) ---
        gemini_key = os.getenv("GEMINI_API_KEY") or settings.LLM_API_KEY
        if gemini_key:
            try:
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=gemini_key)
                docs_payload = [{"doc_id": d.doc_id, "title": d.title, "content": d.content} for d in documents]
                prompt = f"""
                You are Aegis Operational Knowledge Reranker.
                Rate the relevance of each operational runbook for the following incident symptoms on a scale of 0.0 to 1.0.
                Return JSON list of objects: [{{"doc_id": "...", "score": 0.95}}]

                INCIDENT SYMPTOMS:
                {incident_symptoms}

                RUNBOOKS:
                {json.dumps(docs_payload)}
                """
                response = client.models.generate_content(
                    model=settings.LLM_MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                scores = json.loads(response.text)
                score_map = {item["doc_id"]: float(item["score"]) for item in scores if "doc_id" in item and "score" in item}
                for d in documents:
                    if d.doc_id in score_map:
                        d.score = score_map[d.doc_id]
                documents.sort(key=lambda x: x.score, reverse=True)
                return documents
            except Exception as e:
                if settings.DEBUG:
                    print(f"[Gemini Reranker] Fallback to Tier 3: {e}")

        # --- Tier 3: Local Semantic Keyword Overlap (Safety net) ---
        symptoms_lower = incident_symptoms.lower()
        for d in documents:
            if "database" in symptoms_lower and "database" in d.title.lower():
                d.score = 0.95
            elif "rollback" in symptoms_lower and "rollback" in d.title.lower():
                d.score = 0.88
            else:
                d.score = 0.50

        documents.sort(key=lambda x: x.score, reverse=True)
        return documents

jev_reranker = JevReranker()
