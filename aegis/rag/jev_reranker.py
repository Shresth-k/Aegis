import os
import json
import httpx
from typing import List, Any
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
    async def rerank(cls, incident_symptoms: str, documents: List[Any]) -> List[Any]:
        if not documents:
            return []

        def get_id(doc):
            return doc.doc_id if hasattr(doc, "doc_id") else doc.get("doc_id", "")

        def get_title(doc):
            return doc.title if hasattr(doc, "title") else doc.get("title", "")

        def get_content(doc):
            return doc.content if hasattr(doc, "content") else doc.get("content", "")

        def set_score(doc, sc):
            if hasattr(doc, "score"):
                doc.score = float(sc)
            elif isinstance(doc, dict):
                doc["score"] = float(sc)

        def get_score(doc):
            return float(getattr(doc, "score", 0.0) if hasattr(doc, "score") else doc.get("score", 0.0))

        # --- Tier 1: Direct TypeSafe AI or Vercel AI Gateway (typesafe-ai/jev) ---
        typesafe_key = os.getenv("TYPESAFE_API_KEY")
        vercel_key = os.getenv("AI_GATEWAY_API_KEY") or os.getenv("VERCEL_AI_GATEWAY_KEY")
        active_key = typesafe_key or vercel_key
        if active_key:
            target_url = "https://api.typesafe.ai/v1/systemone" if typesafe_key else "https://ai-gateway.vercel.sh/v1/evaluate"
            target_model = "jev-latest" if typesafe_key else "typesafe-ai/jev"
            try:
                questions = {}
                for d in documents:
                    did = get_id(d)
                    dtitle = get_title(d)
                    questions[f"relevance_{did}"] = {
                        "type": "boolean",
                        "instructions": f"Does the document titled '{dtitle}' describe the resolution or runbook for these symptoms: '{incident_symptoms}'?"
                    }

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
                                "symptoms": incident_symptoms,
                                "documents": [{"doc_id": get_id(d), "title": get_title(d)} for d in documents]
                            },
                            "questions": questions
                        }
                    )
                    if resp.status_code == 200:
                        answers = resp.json().get("answers", {})
                        for d in documents:
                            did = get_id(d)
                            ans = answers.get(f"relevance_{did}", {})
                            # Boolean primitive returns probability of true
                            prob = ans.get("probability", ans.get("probabilities", {}).get("true", 0.5))
                            set_score(d, prob)
                        documents.sort(key=get_score, reverse=True)
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
                docs_payload = [{"doc_id": get_id(d), "title": get_title(d), "content": get_content(d)} for d in documents]
                prompt = f"""
                You are Aegis Operational Knowledge Reranker.
                Rate the relevance of each operational runbook for the following incident symptoms on a scale of 0.0 to 1.0.
                Return JSON list of objects: [{{"doc_id": "...", "score": 0.95}}]

                INCIDENT SYMPTOMS:
                {incident_symptoms}

                RUNBOOKS:
                {json.dumps(docs_payload)}
                """
                response = await asyncio.to_thread(
                    client.models.generate_content,
                    model=settings.LLM_MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                scores = json.loads(response.text)
                score_map = {item["doc_id"]: float(item["score"]) for item in scores if "doc_id" in item and "score" in item}
                for d in documents:
                    did = get_id(d)
                    if did in score_map:
                        set_score(d, score_map[did])
                documents.sort(key=get_score, reverse=True)
                return documents
            except Exception as e:
                if settings.DEBUG:
                    print(f"[Gemini Reranker] Fallback to Tier 3: {e}")

        # --- Tier 3: Local Semantic Keyword Overlap (Safety net) ---
        symptoms_lower = incident_symptoms.lower()
        for d in documents:
            dtitle_lower = get_title(d).lower()
            if "database" in symptoms_lower and "database" in dtitle_lower:
                set_score(d, 0.95)
            elif "rollback" in symptoms_lower and "rollback" in dtitle_lower:
                set_score(d, 0.88)
            else:
                set_score(d, 0.50)

        documents.sort(key=get_score, reverse=True)
        return documents

jev_reranker = JevReranker()
