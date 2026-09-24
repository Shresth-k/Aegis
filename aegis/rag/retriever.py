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
    RetrievedRunbook(
        doc_id="RB-004",
        title="Application Heap Exhaustion & Memory Leak Runbook",
        content="""
        Symptoms:
        - Monotonic increase in memory utilization (RSS > 90%).
        - Frequent garbage collection (GC) pauses causing latency spikes (P95 > 2500ms).
        - Worker threads becoming unresponsive or container crashing with OOMKilled.
        
        Investigation Steps:
        1. Check container memory metrics and heap allocation profiles.
        2. Inspect if heap bloat is caused by cached request state rather than new code binary.
        3. Determine whether container recycling or code rollback is required.
        
        Remediation:
        - Execute docker_restart_container on the affected service container to flush heap buffers.
        - Verify worker thread health and memory consumption nominal baseline (< 60%).
        - Note: Rollback is NOT required if application code release is stable.
        """,
        source_type="runbook"
    ),
    RetrievedRunbook(
        doc_id="RB-005",
        title="PostgreSQL Row Lock Contention & Transaction Deadlock Runbook",
        content="""
        Symptoms:
        - API requests timing out while executing database updates or checkouts.
        - Database query logs reporting 'deadlock detected' or 'waiting for ExclusiveLock'.
        - Spikes in active database transactions with zero throughput.
        
        Investigation Steps:
        1. Query pg_stat_activity for long-running transactions and lock waiters.
        2. Identify blocking transaction backend PIDs.
        3. Check if transaction isolation or uncommitted transactions locked table rows.
        
        Remediation:
        - Terminate blocking PIDs or restart database container (acmecloud-postgres) to release locks.
        - Verify database transaction throughput and zero lock waiters.
        - Note: Rollback of checkout service is NOT required.
        """,
        source_type="runbook"
    ),
    RetrievedRunbook(
        doc_id="RB-006",
        title="Upstream Payment Gateway Timeout & Circuit Breaker Runbook",
        content="""
        Symptoms:
        - HTTP 502 / 504 Bad Gateway on external payment authorization requests.
        - Third-party gateway connection resets or timeout exceptions.
        - Elevated checkout failure rate (> 20%).
        
        Investigation Steps:
        1. Test upstream gateway reachability and endpoint latency.
        2. Verify if upstream outage is isolated to third-party provider or deployment misconfiguration.
        3. If upstream endpoint configuration was modified in latest release, execute rollback.
        
        Remediation:
        - Evaluate policy and rollback deployment to stable baseline v2.4.0 if release altered gateway routes.
        - Activate circuit breaker or fallback payment processor if provider is experiencing outage.
        """,
        source_type="runbook"
    ),
]

class RunbookRetriever:
    """Lightweight knowledge retriever over operational runbooks and postmortems."""

    @classmethod
    async def search(cls, query: str, top_k: int = 3) -> List[RetrievedRunbook]:
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
        if scored_docs:
            return scored_docs[:top_k]

        # Semantic candidate fallback for downstream Jev AI reranker
        return [doc.model_copy() for doc in KNOWLEDGE_BASE[:top_k]]

runbook_retriever = RunbookRetriever()
