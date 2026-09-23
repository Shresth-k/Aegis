# Aegis & AcmeCloud: Local Setup and Operational Guide

Welcome to **Aegis**, an agentic IT operations and autonomous incident resolution platform paired with the **AcmeCloud** enterprise digital twin simulator.

This guide provides end-to-end instructions for installing all dependencies, configuring API keys, starting each tier (Docker infrastructure, Python backend, React frontend), and simulating closed-loop incident resolution.

---

## 1. System Architecture

Aegis consists of three tightly integrated tiers:

1. **AcmeCloud Digital Twin (Docker Compose)**:
   - `acmecloud-checkout`: Microservice simulating e-commerce checkout (`http://localhost:8001`). Supports nominal release `v2.4.0` (pool size 50) and faulty release `v2.4.1` (pool size 5, causing database pool exhaustion under load).
   - `acmecloud-postgres`: PostgreSQL database (`port 5432`).
   - `acmecloud-prometheus`: Prometheus metrics scraper collecting error rate, latency, and DB pool stats (`http://localhost:9090`).
   - `acmecloud-grafana`: Telemetry visualization dashboards (`http://localhost:3001`).

2. **Aegis Mission Control Backend (`aegis/`)**:
   - Built on FastAPI with Model Context Protocol (FastMCP) and asynchronous tool calling.
   - Powered by **Google Gemini 3.5 Flash-Lite** for chain-of-thought root cause diagnosis and tool dispatch.
   - Integrated with **TypeSafe Jev AI** (sub-20ms P1 incident classification and Jev Noul semantic runbook reranker).
   - Enforces deterministic safety rules via **PolicyEngine** (human-in-the-loop approval gate for production rollback).
   - Executes remediation and verification via **Needle Executor** (`http://localhost:8000`).

3. **Aegis Studio Frontend (`frontend/`)**:
   - Modern React + TypeScript + Vite interface.
   - Dynamic workflow execution graph powered by `@xyflow/react` (interactive canvas generates DAG nodes as the agent executes tools).
   - ChatGPT-style interactive Agent Stream Panel with live tool outputs and in-conversation approval gates (`http://localhost:3000`).

---

## 2. Prerequisites

Ensure you have the following installed on your host system:

- **Docker Desktop** (with Docker Compose enabled)
- **Python 3.11** or **Python 3.12**
- **Node.js 18+** and **npm**
- **Git**
- A **Google Gemini API Key** (Get one free from [Google AI Studio](https://aistudio.google.com/app/apikey))

---

## 3. Quickstart: Step-by-Step Installation

### Step 1: Clone Repository & Checkout Branch
```bash
git clone https://github.com/Shresth-k/Aegis.git
cd Aegis
git checkout beta2
```

---

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env` in the root directory:

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**Linux / macOS:**
```bash
cp .env.example .env
```

Open `.env` and add your **Gemini API Key**:
```ini
LLM_PROVIDER=google
LLM_MODEL=gemini-3.5-flash-lite
GEMINI_API_KEY=your_actual_gemini_api_key_here

# Direct connection to live AcmeCloud Docker containers
MOCK_ACME_CLOUD=false
ACME_CLOUD_API_URL=http://localhost:8001
USE_MCP=true
MCP_SERVER_TRANSPORT=direct
```

*(Optional)* If you have a Vercel AI Gateway or TypeSafe key, set `AI_GATEWAY_API_KEY`. If left blank, Aegis automatically uses its high-speed local classifier fallback.

---

### Step 3: Start AcmeCloud Digital Twin (Docker Compose)
Launch the 4 AcmeCloud containers in background mode:

```bash
cd acmecloud
docker compose up -d
```

Verify all 4 containers are healthy and running:
```bash
docker ps
```

You should see:
- `acmecloud-checkout` on port `8001`
- `acmecloud-postgres` on port `5432`
- `acmecloud-prometheus` on port `9090`
- `acmecloud-grafana` on port `3001`

Return to the repository root:
```bash
cd ..
```

---

### Step 4: Setup & Start the Python Backend

Create a Python virtual environment and install dependencies:

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -e .
```

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

Start the Aegis Mission Control API server on port 8000:
```bash
uvicorn aegis.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Verify backend health at: [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

### Step 5: Setup & Start the Frontend

Open a new terminal window, navigate to `frontend/`, install npm packages, and launch Vite:

```bash
cd frontend
npm install
npm run dev -- --port 3000
```

Open your browser and navigate to:
**[http://localhost:3000](http://localhost:3000)**

---

## 4. End-to-End Operational Testing

### A. Simulating Chaos (Faulty Release v2.4.1)
To inject connection pool starvation and generate live 5xx error spikes in Prometheus:

1. Click **"Inject Chaos v2.4.1"** in the top navigation bar, OR run via curl:
   ```bash
   curl -X POST "http://localhost:8000/api/chaos/inject?service=checkout-service&version=2.4.1"
   ```
2. Start continuous traffic generation to produce authentic Prometheus spikes:
   ```powershell
   python -u -c "
   import time, urllib.request
   for i in range(150):
       try:
           req = urllib.request.Request('http://localhost:8001/checkout', data=b'{\"customer_id\":\"cust-123\",\"items\":[\"sku-99\"],\"amount\":99.99}', headers={'Content-Type':'application/json'})
           urllib.request.urlopen(req, timeout=1.0)
       except Exception:
           pass
       time.sleep(0.08)
   "
   ```

---

### B. Chatting with Aegis Co-Pilot
In the right panel chat stream:

1. **Inspect Host Docker Containers**:
   - Type: `"Show running docker containers"`
   - Aegis autonomously calls `docker_ps()` and returns container IDs, names, images, ports, and uptime.
2. **Autonomous Incident Investigation**:
   - Type: `"Investigate incident on checkout-service and diagnose root cause"`
   - Aegis autonomously calls:
     - `triage_incident`: Jev AI fast severity/domain triage (`database`, `P1`).
     - `get_metrics`: Prometheus error rate (e.g. 48.6%) and DB connection pool saturation (5/5).
     - `get_service_logs`: Extracts connection pool timeout stack traces.
     - `search_runbooks`: Matches `RB-001` via semantic vector similarity.
     - `evaluate_policy`: Triggers policy rule `PROD_ROLLBACK_APPROVAL`.
   - The Canvas dynamically builds the execution graph in real time!
3. **Operator Approval & Remediation**:
   - The assistant explicitly requests human authorization and hooks an interactive **`[Approve Rollback to v2.4.0]`** card directly into the conversation.
   - Click **`Approve Rollback to v2.4.0`** (or type `"Approve rollback"`).
   - Aegis invokes Needle Executor, rolls back the container to `v2.4.0`, monitors post-remediation SLO recovery, and marks the incident **`RESOLVED`**!

---

### C. Resetting to Nominal Baseline
To restore nominal baseline v2.4.0 without going through the investigation:
- Click **"Reset Baseline v2.4.0"** in the top navigation bar, OR:
  ```bash
  curl -X POST "http://localhost:8000/api/chaos/reset?service=checkout-service"
  ```

---

## 5. Running Automated Tests

Run the full pytest suite (15 integration, MCP, API, and closed-loop tests):

```bash
pytest -v
```

All 15 tests should pass:
- `tests/test_api.py` (Health, list incidents, chaos inject/reset, approval flow, SSE chat, traces)
- `tests/test_closed_loop.py` (Policy guardrails, closed-loop auto-heal flow)
- `tests/test_mcp.py` (FastMCP server tools, resources, direct adapter, stdio adapter, closed-loop MCP)

---

## 6. Ports & Services Reference

| Service | Port | Description |
|---|---|---|
| **Aegis Frontend** | `3000` | React + TypeScript mission control console |
| **Aegis Backend API** | `8000` | FastAPI core, LangGraph, Copilot chat, SSE stream |
| **AcmeCloud Checkout** | `8001` | Live microservice container target |
| **Prometheus** | `9090` | Time-series metrics scraper |
| **Grafana** | `3001` | Metrics dashboard (`admin` / `admin`) |
| **PostgreSQL** | `5432` | AcmeCloud relational database |
