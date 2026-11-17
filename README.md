# Aegis: Agentic IT Operations & Autonomous Incident Resolution Platform

Aegis is an enterprise-grade agentic IT operations and autonomous incident resolution platform. Powered by **Google Gemini 3.5 Flash-Lite**, **TypeSafe Jev AI**, and **Model Context Protocol (FastMCP)**, Aegis investigates production outages, probes live telemetry, diagnoses root causes, enforces deterministic safety guardrails, and executes verified closed-loop remediations.

Paired with the **AcmeCloud** enterprise digital twin, Aegis provides a complete, runnable environment simulating real-world containerized microservice architectures.

---

## Key Features

- **Autonomous Agentic Copilot**: Chat-driven SRE assistant equipped with 10 native platform and Docker tools (`docker_ps`, `docker_logs`, `get_metrics`, `get_service_logs`, `search_runbooks`, `evaluate_policy`, `rollback_deployment`, `verify_slo`).
- **Dynamic DAG Graph Generation**: React Flow canvas dynamically constructs and animates workflow execution nodes in real time as tools are dispatched.
- **Sub-20ms Jev AI Triage**: Ultra-fast P1 classification and domain routing paired with Jev Noul semantic runbook reranker.
- **Human-in-the-Loop Policy Guardrail**: Deterministic `PolicyEngine` enforcing mandatory human operator authorization before executing high-risk remediations (like production container rollbacks).
- **Needle Executor & SLO Verification**: Autonomous container rollback via Docker Compose followed by post-remediation Prometheus SLO health verification.
- **Enterprise Digital Twin**: Bundled `AcmeCloud` stack featuring a checkout microservice, PostgreSQL, Prometheus, and Grafana.

---

## Architecture

```
                  ┌───────────────────────────────────────────────┐
                  │          Aegis Studio (React + Vite)          │
                  │   - Dynamic React Flow Workflow DAG Canvas    │
                  │   - ChatGPT-Style Agent Stream Panel & Tools   │
                  └───────────────────────▲───────────────────────┘
                                          │ HTTP / SSE / REST
                                          ▼
                  ┌───────────────────────────────────────────────┐
                  │       Aegis Backend API (FastAPI + MCP)       │
                  │   - Gemini 3.5 Flash-Lite Reasoning Engine    │
                  │   - Jev AI Sub-20ms Fast Classifier & Rerank │
                  │   - FastMCP Server (Prometheus / Docker Tools)│
                  │   - PolicyEngine (Human-in-the-Loop Gate)     │
                  │   - Needle Executor & SLO Verification Engine │
                  └───────────────────────▲───────────────────────┘
                                          │ Docker Daemon & HTTP
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           AcmeCloud Digital Twin                                │
│  ┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────────┐  │
│  │  Checkout Container   │ │  PostgreSQL Database  │ │      Prometheus       │  │
│  │   (v2.4.0 / v2.4.1)   │ │      (Port 5432)      │ │   Metrics Scraper     │  │
│  │      (Port 8001)      │ │                       │ │      (Port 9090)      │  │
│  └───────────────────────┘ └───────────────────────┘ └───────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Quickstart

For full step-by-step installation instructions, environment variable setup, API key configuration, and testing walkthroughs, please see:

👉 **[SETUP_AND_RUN_GUIDE.md](./SETUP_AND_RUN_GUIDE.md)**

### Rapid Summary:
1. **Configure API Keys**: Copy `.env.example` to `.env` and add your `GEMINI_API_KEY`.
2. **Start AcmeCloud Infrastructure**:
   ```bash
   cd acmecloud && docker compose up -d && cd ..
   ```
3. **Start Aegis API Server**:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # On Linux/macOS: source .venv/bin/activate
   pip install -e .
   uvicorn aegis.api.main:app --host 0.0.0.0 --port 8000 --reload
   ```
4. **Start Aegis Web Console**:
   ```bash
   cd frontend && npm install && npm run dev -- --port 3000
   ```
5. **Open Studio**: Navigate to `http://localhost:3000`.

---

## Automated Test Suite

Aegis includes 15 automated pytest tests covering the API, FastMCP server, closed-loop resolution, and policy engine:

```bash
pytest -v
```

---

## License

Apache 2.0. Built for autonomous IT operations and resilient site reliability engineering.
