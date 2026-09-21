import httpx
from typing import List
from aegis.core.state import RetrievedRunbook
from aegis.config import settings

class JevReranker:
    """
    TypeSafe / Jev Reranking Engine.
    Uses System One scoring to rank operational runbooks by relevance to incident evidence.
    """

    @classmethod
    async def rerank(cls, incident_symptoms: str, documents: List[RetrievedRunbook]) -> List[RetrievedRunbook]:
        if not documents:
            return []

        # 1. Try OpenRouter / TypeSafe Jev if configured
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
                                "symptoms": incident_symptoms,
                                "documents": [{"id": d.doc_id, "title": d.title} for d in documents]
                            },
                            "questions": [
                                {
                                    "id": f"relevance_{d.doc_id}",
                                    "primitive": "noul",
                                    "instructions": f"Does the document '{d.title}' provide direct remediation for: '{incident_symptoms}'?"
                                }
                                for d in documents
                            ]
                        }
                    )
                    if resp.status_code == 200:
                        answers = resp.json().get("answers", {})
                        for d in documents:
                            prob = answers.get(f"relevance_{d.doc_id}", {}).get("probability", 0.5)
                            d.score = float(prob)
                        documents.sort(key=lambda x: x.score, reverse=True)
                        return documents
            except Exception as e:
                if settings.DEBUG:
                    print(f"[Jev Reranker warning] Falling back to local reranking: {e}")

        # 2. Local Fallback Reranking
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
