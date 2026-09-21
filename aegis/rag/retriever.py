from typing import List
from aegis.core.state import RetrievedRunbook

# Built-in operational knowledge base for AcmeCloud
KNOWLEDGE_BASE = [
    RetrievedRunbook(
        doc_id="RB-001",
        title="Database Connection Pool Exhaustion Runbook",
        content="""
        Symptoms:
        - HTTP 500 errors on checkout or payment endpoints.
        - Log messages containing 'timeout acquiring DB connection' or 'connection pool exhausted'.
        - High latency (P95 > 2000ms).
        
        Investigation Steps:
        1. Check recent deployments for the affected service.
        2. Inspect DB connection pool configuration in the latest release.
        3. If DB connection pool was reduced or recent deployment introduced connection leaks, perform immediate rollback.
        
        Remediation:
        - Execute rollback_deployment to previous known healthy version.
        - Verify database connection wait times and error rate return to normal (<0.5%).
        """,
        source_type="runbook"
    ),
    RetrievedRunbook(
        doc_id="RB-002",
        title="Production Deployment Rollback Standard Operating Procedure",
        content="""
        Overview:
        Rollbacks in production are HIGH risk actions because they alter active customer traffic versions.
        
        Requirements:
        1. Must obtain explicit operator approval before executing rollback in production.
        2. Validate target version exists in deployment history.
        3. Perform post-rollback health checks across error rate and latency.
        """,
        source_type="policy"
    ),
    RetrievedRunbook(
        doc_id="RB-003",
        title="SSL/TLS Certificate Expiration Runbook",
        content="""
        Symptoms:
        - SSL handshake errors, NET::ERR_CERT_DATE_INVALID.
        - API Gateway rejecting incoming requests.
        
        Remediation:
        - Trigger certificate rotation via Cert-Manager or Vault.
        """,
        source_type="runbook"
    ),
]

class RunbookRetriever:
    """Lightweight knowledge retriever over operational runbooks and postmortems."""

    @classmethod
    async def search(cls, query: str, top_k: int = 2) -> List[RetrievedRunbook]:
        query_terms = set(query.lower().split())
        scored_docs = []

        for doc in KNOWLEDGE_BASE:
            text = f"{doc.title} {doc.content}".lower()
            overlap = sum(1 for term in query_terms if term in text)
            if overlap > 0:
                doc_copy = doc.model_copy()
                doc_copy.score = float(overlap) / max(len(query_terms), 1)
                scored_docs.append(doc_copy)

        scored_docs.sort(key=lambda x: x.score, reverse=True)
        return scored_docs[:top_k]

runbook_retriever = RunbookRetriever()
