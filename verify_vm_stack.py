import os
import sys
import asyncio
from dotenv import load_dotenv

# Load VM environment if present
if os.path.exists("/opt/aegis/.env"):
    load_dotenv("/opt/aegis/.env")

sys.path.insert(0, "/opt/aegis")

from aegis.triage.jev_triage import jev_triage
from aegis.rag.jev_reranker import JevReranker
from aegis.acme.client import AcmeClient
from google import genai

async def test_all():
    print("=== AEGIS CLOUD STACK VERIFICATION ===")
    
    # 1. Gemini API
    gem_key = os.getenv("GEMINI_API_KEY")
    print(f"1. Gemini API Key Present: {bool(gem_key)}")
    working_model = None
    if gem_key:
        client = genai.Client(api_key=gem_key)
        candidates = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.0-flash-lite", "gemini-flash-latest", "gemini-3.6-flash"]
        for cand in candidates:
            try:
                res = client.models.generate_content(model=cand, contents="Reply with 'GEMINI_OK'")
                print(f"   [SUCCESS] Model {cand} is WORKING: {res.text.strip()}")
                working_model = cand
                break
            except Exception as e:
                print(f"   [FAILED] Model {cand}: {e}")

    # 2. Vercel AI Gateway / Jev Key
    ai_gw_key = os.getenv("AI_GATEWAY_API_KEY") or os.getenv("VERCEL_AI_GATEWAY_KEY")
    print(f"2. Jev / AI Gateway Key Present: {bool(ai_gw_key)}")
    
    # 3. Jev Triage
    try:
        sev, dom, conf = await jev_triage.triage_incident(
            "High error rate in checkout-service",
            "500 DatabaseTimeout connection pool exhausted",
            "checkout-service"
        )
        print(f"3. Jev Triage Output: Severity={sev}, Domain={dom}, Confidence={conf:.2f}")
    except Exception as e:
        print(f"   Jev Triage Error: {e}")

    # 4. Jev Reranker
    try:
        docs = [
            {"doc_id": "RB-001", "title": "Connection Pool Exhaustion Runbook", "content": "Rollback checkout-service to v2.4.0"},
            {"doc_id": "RB-002", "title": "DNS Configuration Error", "content": "Check route53 or cloud dns"},
        ]
        ranked = await JevReranker.rerank("Database connection pool timeout", docs)
        print(f"4. Jev Reranker Top Doc: {ranked[0]['doc_id']} (Score: {ranked[0].get('score')})")
    except Exception as e:
        print(f"   Jev Reranker Error: {e}")

    # 5. AcmeClient / MCP Prometheus Metrics
    try:
        acme = AcmeClient()
        metrics = await acme.get_metrics("checkout-service")
        print(f"5. AcmeClient Metrics: Error Rate={metrics.get('error_rate')}%, P95 Latency={metrics.get('latency_p95_ms')}ms, Source={metrics.get('source')}")
    except Exception as e:
        print(f"   Metrics Error: {e}")

    # 6. Container Logs via FastMCP / Docker
    try:
        logs = await acme.get_logs("checkout-service")
        print(f"6. Container Log Lines Retrieved: {len(logs)}")
        for l in logs[:2]:
            print(f"   - {l.strip()[:80]}")
    except Exception as e:
        print(f"   Logs Error: {e}")

    print("=== VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_all())
