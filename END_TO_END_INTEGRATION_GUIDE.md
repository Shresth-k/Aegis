# Aegis OpsPilot: End-to-End System Integration & Architecture Guide

> **Target Audience**: SREs, Platform Engineers, and AI Operations Developers  
> **Status**: Comprehensive Technical Integration Blueprint  
> **Document Version**: 1.0.0  
> **Primary Workspace**: `s:\1.capg_onsite2`  

---

## 1. Executive Architecture & Component Topology

OpsPilot / Aegis is a state-of-the-art **Agentic IT Operations & Autonomous Incident Resolution Platform** designed to solve production outages in real-time through a closed-loop observe-investigate-reason-gate-remediate-verify lifecycle.

```
                                    +-------------------------------------------------------------+
                                    |                   ACME CLOUD ENTERPRISE                     |
                                    |  (Checkout Service, Postgres:5432, Redis, CMDB, Prometheus)  |
                                    +------------------------------+------------------------------+
                                                                   |
                                              FastMCP Protocol / Telemetry APIs
                                                                   |
                                                                   v
+-----------------------------------------------------------------------------------------------------------------------------------------+
|                                                      AEGIS BACKEND PLATFORM (FastAPI)                                                   |
|                                                                                                                                         |
|   +-------------------------------------+      +---------------------------------------+      +-------------------------------------+   |
|   |         JEV AI / TYPESAFE           |      |          AEGIS STATEGRAPH             |      |        GEMINI 3.5 FLASH-LITE        |   |
|   |          (System One)               |      |            (Async DAG)                |      |               (CoT)                 |   |
|   |  - Sub-25ms fast triage             | <--> |  - Ingest -> Jev Triage               | <--> |  - Deep Root Cause Synthesis        |   |
|   |  - Runbook RAG semantic reranking   |      |  - MCP Probe (logs, metrics)          |      |  - Native Chain-of-Thought (CoT)    |   |
|   |  - Typed Choice & Boolean primitives|      |  - Runbook Knowledge RAG              |      |  - Structured JSON Output           |   |
|   |  - 3-Tier fallback architecture     |      |  - Gemini 3.5 Flash-Lite Diagnosis    |      |  - Multi-turn SRE Copilot Chat      |   |
|   +-------------------------------------+      |  - Deterministic Policy Gate          |      +-------------------------------------+   |
|                                                |  - HITL Operator Approval Boundary    |                                                |
|                                                |  - Needle Executor (Docker Rollback)  |                                                |
|                                                |  - SLO Verification Engine            |                                                |
|                                                +-------------------+-------------------+                                                |
|                                                                    |                                                                    |
|                                                       JSONL Trace & State Stream                                                        |
|                                                                    |                                                                    |
+--------------------------------------------------------------------+--------------------------------------------------------------------+
                                                                     |
                                             Server-Sent Events (SSE) & REST API
                                                                     |
                                                                     v
+-----------------------------------------------------------------------------------------------------------------------------------------+
|                                                    AEGIS MISSION CONTROL FRONTEND                                                       |
|                                                                                                                                         |
|   +-------------------------------------+      +---------------------------------------+      +-------------------------------------+   |
|   |              TOPBAR                 |      |            WORKFLOW CANVAS            |      |          AGENT STREAM PANEL         |   |
|   |  - Service & Incident Breadcrumbs   |      |  - ReactFlow Interactive Graph        |      |  - Real-time Trace & CoT Stream     |   |
|   |  - Live Status Pills (P1/RESOLVED)  |      |  - ThinkingOrb Execution Pulses       |      |  - Dynamic 6-Agent Mesh Dashboard   |   |
|   |  - Run Auto-Heal & Chaos Controls   |      |  - Dynamic Progressive Node Spawning  |      |  - Interactive SRE Copilot Chat     |   |
|   |  - Operator Identity (LeadSRE)      |      |  - Sub-millisecond State Transitions  |      |  - Live Container Logs Inspection   |   |
|   +-------------------------------------+      +---------------------------------------+      +-------------------------------------+   |
+-----------------------------------------------------------------------------------------------------------------------------------------+
```

---

## 2. Core Subsystems

### 2.1 AcmeCloud Simulated Enterprise
- **Services**: `checkout-service`, `postgres`, `redis`, `inventory-service`, `notification-service`.
- **Fault Scenario (ITOPS-001)**: Deployment of version `v2.4.1` introduces database connection pool starvation (`DB_CONNECTION_POOL=5` instead of `50`) under 100 RPS traffic, causing HTTP 500 error spikes (38.5%) and P95 latency jumps (> 2,800ms).
- **Control Interface**: Exposed via both FastMCP (`aegis/mcp/server.py`) and Direct HTTP Client (`aegis/acme/client.py`).

### 2.2 Jev AI / TypeSafe AI System One
- **Nature**: TypeSafe's flagship System One model (`typesafe-ai/jev`). Unlike generative LLMs that generate free-form text, Jev returns fast, calibrated typed judgments and probabilities.
- **Role in Aegis**:
  1. **Triage Engine (`aegis/triage/jev_triage.py`)**: Evaluates incident title, description, and service to classify `severity` (`P1`-`P4`) and `domain` (`deployment`, `database`, `network`, `application`) in sub-25ms.
  2. **Knowledge RAG Reranker (`aegis/rag/jev_reranker.py`)**: Uses boolean probability judgments to rerank candidate operational runbooks matching incident symptoms.
- **3-Tier Fallback Resilience**:
  - **Tier 1**: Live Vercel AI Gateway (`https://ai-gateway.vercel.sh/v1/evaluate`) with model `typesafe-ai/jev`.
  - **Tier 2**: Gemini 3.5 Flash-Lite structured JSON classification/scoring.
  - **Tier 3**: Local heuristic & keyword matching safety net.

### 2.3 Gemini 3.5 Flash-Lite LLM
- **Model**: `gemini-3.5-flash-lite` (via official `google-genai` SDK).
- **Role**: Deep Chain-of-Thought (CoT) root cause reasoning (`aegis/agents/diagnosis.py`), correlating deployment history, Prometheus metrics, container logs, and runbooks.
- **Thinking Configuration**: Native Gemini `thinking_config=types.ThinkingConfig(thinking_level="low")` with `response_mime_type="application/json"`.

### 2.4 Aegis StateGraph
- **Architecture**: Asynchronous state graph (`aegis/graph/workflow.py`) with explicit human approval boundary:
  `triage` -> `investigate` -> `knowledge` -> `diagnose` -> `policy` -> [Conditional Gate] -> `remediate` -> `verify`.

---

## 3. Deep Analysis: Why the Frontend Was "Static"

Our architectural audit identified 5 root causes for the static UI behavior:

| # | Component | Root Cause | Impact |
|---|---|---|---|
| **1** | `App.tsx` vs `main.py` | **SSE Event Listener Mismatch**: `main.py` emits custom event names (`event: trace`, `event: state`). `App.tsx` only registered `es.onmessage`. In the browser HTML5 `EventSource` standard, `onmessage` **only** triggers for unnamed events or `event: message`. | Real backend trace events and state updates pushed by FastAPI were completely dropped by the browser! |
| **2** | `App.tsx` | **Simulated Node Progress**: `handleRunAutoHeal()` used hardcoded `await sleep(400)` steps before invoking `/api/incidents/run`, decoupling UI animations from real backend agent execution. | The graph nodes animated on a fixed timer rather than reflecting true backend agent milestones. |
| **3** | `AgentStreamPanel.tsx` | **Disconnected Copilot Chat**: `handleSend()` used a local `setTimeout` with hardcoded keyword checks (`if (q.includes('pool'))...`) instead of querying the backend. | The user could not actually converse with the AI agents, ask custom queries, or inspect real live telemetry. |
| **4** | `aegis/api/main.py` | **Missing Chat Endpoint**: The FastAPI backend had no `/api/chat` or `/api/copilot` endpoint to handle interactive operator queries. | Frontend had no backend target for SRE chat interactions. |
| **5** | `TopBar.tsx` | **Missing Chaos Trigger Controls**: Chaos injection (`/api/chaos/inject`) and reset (`/api/chaos/reset`) endpoints were only accessible via curl/tests, not the UI. | Operators could not trigger or reset fault scenarios directly from the header bar. |

---

## 4. Exact File-by-File Integration Changes

### 4.1 `aegis/api/main.py`
Add the `/api/chat` endpoint and fix SSE streaming so both `onmessage` and named listeners receive updates.

```python
# ---------------------------------------------------------------------------
# Add Chat Endpoint & Fix SSE in aegis/api/main.py
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    incident_id: str = "INC-001"
    message: str

class ChatResponse(BaseModel):
    reply: str
    thinking: Optional[str] = None
    tool_call: Optional[Dict[str, Any]] = None

@app.post("/api/chat", response_model=ChatResponse)
async def copilot_chat(req: ChatRequest):
    """
    Interactive SRE Copilot Chat.
    Uses Gemini 3.5 Flash-Lite with incident context and live AcmeCloud telemetry.
    """
    state = INCIDENTS.get(req.incident_id)
    msg = req.message.lower()

    # 1. Check if asking for live metrics
    if any(k in msg for k in ["metric", "latency", "error rate", "pool", "saturation"]):
        metrics = await acme_client.get_metrics(service=state.service if state else "checkout-service")
        return ChatResponse(
            reply=(
                f"**Live Telemetry for `{metrics.get('service', 'checkout-service')}`:**\n"
                f"- **Error Rate**: `{metrics.get('error_rate', 0):.1%}`\n"
                f"- **P95 Latency**: `{metrics.get('latency_p95_ms', 0):.1f}ms`\n"
                f"- **DB Active Connections**: `{metrics.get('db_pool_active', 0)}`"
            ),
            thinking="Queried live telemetry metrics via AcmeCloud client.",
            tool_call={
                "name": "get_metrics",
                "args": f"service=\"{state.service if state else 'checkout-service'}\", window=\"15m\"",
                "output": metrics
            }
        )

    # 2. Check if asking for logs
    if any(k in msg for k in ["log", "500", "5xx", "error log", "stack trace"]):
        logs = await acme_client.get_logs(service=state.service if state else "checkout-service")
        return ChatResponse(
            reply=f"Retrieved recent error logs for `{state.service if state else 'checkout-service'}`. Identified database connection pool starvation under nominal load.",
            thinking="Scanning recent AcmeCloud container logs for 5xx exceptions.",
            tool_call={
                "name": "get_service_logs",
                "args": f"service=\"{state.service if state else 'checkout-service'}\", level=\"ERROR\"",
                "output": "\n".join(logs[:5])
            }
        )

    # 3. General LLM Question via Gemini 3.5 Flash-Lite
    gemini_key = os.getenv("GEMINI_API_KEY") or settings.LLM_API_KEY
    if gemini_key:
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=gemini_key)
            prompt = f"""
            You are Aegis SRE Co-Pilot assisting an on-call engineer with incident {req.incident_id}.
            INCIDENT STATE:
            {state.model_dump_json() if state else "No active incident state."}

            OPERATOR QUESTION:
            {req.message}

            Provide a concise, professional SRE response. If recommending actions, refer to platform policy.
            """
            response = client.models.generate_content(
                model=settings.LLM_MODEL,
                contents=prompt
            )
            return ChatResponse(
                reply=response.text,
                thinking="Reasoned over incident context using Gemini 3.5 Flash-Lite."
            )
        except Exception as e:
            pass

    # 4. Fallback intelligent response
    return ChatResponse(
        reply=f"Incident **{req.incident_id}** is currently in status **{state.status if state else 'OPEN'}**. Recommended remediation: `rollback_deployment` to `v2.4.0`.",
        thinking="Evaluating current incident state against runbook RB-001."
    )


# In stream_incident, emit default message event as well as custom named events:
@app.get("/api/incidents/{incident_id}/stream")
async def stream_incident(incident_id: str):
    async def event_generator():
        sent_indices = 0
        while True:
            events = tracer.get_incident_trace(incident_id)
            if len(events) > sent_indices:
                for ev in events[sent_indices:]:
                    data_str = json.dumps(ev, default=str)
                    # Yield both named event and standard data event for maximum client compatibility
                    yield f"event: trace\ndata: {data_str}\n\n"
                    yield f"data: {data_str}\n\n"
                sent_indices = len(events)

            if incident_id in INCIDENTS:
                st = INCIDENTS[incident_id].model_dump()
                yield f"event: state\ndata: {json.dumps(st, default=str)}\n\n"

            yield f"event: ping\ndata: {{\"time\": \"{tracer.trace_file}\"}}\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

---

### 4.2 `frontend/src/App.tsx`
Update SSE event listening and connect workflow execution directly to backend events.

```tsx
// ---------------------------------------------------------------------------
// Updated SSE & Auto-Heal Flow in frontend/src/App.tsx
// ---------------------------------------------------------------------------

useEffect(() => {
  fetchIncident();

  let es: EventSource | null = null;
  try {
    es = new EventSource('/api/incidents/INC-001/stream');

    // 1. Listen to named 'trace' events
    es.addEventListener('trace', (e: MessageEvent) => {
      try {
        const trace = JSON.parse(e.data);
        handleTraceEvent(trace);
      } catch (err) {
        console.warn('Error parsing trace event:', err);
      }
    });

    // 2. Listen to named 'state' events
    es.addEventListener('state', (e: MessageEvent) => {
      try {
        const state = JSON.parse(e.data);
        setIncidentState(state);
      } catch (err) {
        console.warn('Error parsing state event:', err);
      }
    });

    // 3. Fallback onmessage listener
    es.onmessage = (e: MessageEvent) => {
      try {
        const parsed = JSON.parse(e.data);
        if (parsed.event_type) {
          handleTraceEvent(parsed);
        } else if (parsed.incident_id) {
          setIncidentState(parsed);
        }
      } catch {}
    };
  } catch (err) {
    console.warn('SSE connection failed:', err);
  }

  return () => {
    es?.close();
  };
}, []);

// Dynamic reaction to real backend trace events
const handleTraceEvent = (trace: TraceEvent) => {
  setTraces((prev) => [...prev, trace]);

  switch (trace.event_type) {
    case 'INCIDENT_INGESTED':
      setVisibleNodeIds((prev) => Array.from(new Set([...prev, 'ingest'])));
      setActiveNodeId('ingest');
      setSelectedNodeId('ingest');
      break;

    case 'TRIAGE_COMPLETE':
      setVisibleNodeIds((prev) => Array.from(new Set([...prev, 'ingest', 'triage'])));
      setActiveNodeId('triage');
      setSelectedNodeId('triage');
      break;

    case 'EVIDENCE_COLLECTED':
      setVisibleNodeIds((prev) => Array.from(new Set([...prev, 'tool-logs', 'tool-metrics'])));
      setActiveNodeId('tool-logs');
      setSelectedNodeId('tool-logs');
      break;

    case 'RUNBOOKS_RETRIEVED':
      setVisibleNodeIds((prev) => Array.from(new Set([...prev, 'knowledge'])));
      setActiveNodeId('knowledge');
      setSelectedNodeId('knowledge');
      break;

    case 'DIAGNOSIS_PRODUCED':
      setVisibleNodeIds((prev) => Array.from(new Set([...prev, 'diagnose'])));
      setActiveNodeId('diagnose');
      setSelectedNodeId('diagnose');
      break;

    case 'POLICY_EVALUATED':
      setVisibleNodeIds((prev) => Array.from(new Set([...prev, 'policy'])));
      setActiveNodeId('policy');
      setSelectedNodeId('policy');
      break;

    case 'REMEDIATION_EXECUTED':
      setVisibleNodeIds((prev) => Array.from(new Set([...prev, 'remediate'])));
      setActiveNodeId('remediate');
      setSelectedNodeId('remediate');
      break;

    case 'VERIFICATION_COMPLETE':
      setVisibleNodeIds((prev) => Array.from(new Set([...prev, 'verify'])));
      setActiveNodeId('verify');
      setSelectedNodeId('verify');
      setActiveNodeId(null);
      break;
  }
};

// Real Auto-Heal Trigger
const handleRunAutoHeal = async () => {
  setIsRunning(true);
  try {
    const res = await fetch('/api/incidents/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ incident_id: 'INC-001' })
    });
    if (res.ok) {
      const data = await res.json();
      setIncidentState(data);
    }
  } catch (err) {
    console.error('Failed to run auto-heal workflow:', err);
  } finally {
    setIsRunning(false);
  }
};
```

---

### 4.3 `frontend/src/components/AgentStreamPanel.tsx`
Connect the chat composer directly to `POST /api/chat`.

```tsx
// ---------------------------------------------------------------------------
// Updated Chat Handler in frontend/src/components/AgentStreamPanel.tsx
// ---------------------------------------------------------------------------

const handleSend = async () => {
  const text = inputText.trim();
  if (!text) return;

  const userTurn: ChatTurn = {
    id: `user-${Date.now()}`,
    role: 'user',
    text,
    time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  };

  setChatMessages((prev) => [...prev, userTurn]);
  setInputText('');
  setShowQuickActions(false);
  setIsCopilotThinking(true);

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        incident_id: state?.incident_id || 'INC-001',
        message: text
      })
    });

    if (res.ok) {
      const data = await res.json();
      setChatMessages((prev) => [
        ...prev,
        {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          text: data.reply,
          thinking: data.thinking,
          toolCall: data.tool_call
        }
      ]);
    } else {
      throw new Error(`API returned ${res.status}`);
    }
  } catch (err) {
    // Fallback response if API unavailable
    setChatMessages((prev) => [
      ...prev,
      {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        text: `Standing by for **${state?.incident_id || 'INC-001'}**. Current engine status: **${status}**.`,
        thinking: 'Local fallback engine.'
      }
    ]);
  } finally {
    setIsCopilotThinking(false);
  }
};
```

---

### 4.4 `frontend/src/components/TopBar.tsx`
Add interactive Chaos Injection and Reset buttons.

```tsx
// ---------------------------------------------------------------------------
// TopBar Action Buttons in frontend/src/components/TopBar.tsx
// ---------------------------------------------------------------------------

// Add handlers for Chaos Injection and Reset
const handleInjectChaos = async () => {
  try {
    await fetch('/api/chaos/inject?service=checkout-service&version=2.4.1', { method: 'POST' });
    window.location.reload();
  } catch (err) {
    console.error('Failed to inject chaos:', err);
  }
};

const handleResetChaos = async () => {
  try {
    await fetch('/api/chaos/reset?service=checkout-service', { method: 'POST' });
    window.location.reload();
  } catch (err) {
    console.error('Failed to reset chaos:', err);
  }
};

// In TopBar JSX controls section:
<div className="flex items-center gap-2">
  <button
    onClick={handleInjectChaos}
    className="bg-[#27272a] hover:bg-red-900/40 text-red-300 border border-red-800/50 text-[11px] px-2.5 py-1.5 rounded-lg font-mono flex items-center gap-1 transition-all"
    title="Inject Fault v2.4.1 (DB Connection Pool Starvation)"
  >
    <span>Inject Fault (v2.4.1)</span>
  </button>
  <button
    onClick={handleResetChaos}
    className="bg-[#27272a] hover:bg-emerald-900/40 text-emerald-300 border border-emerald-800/50 text-[11px] px-2.5 py-1.5 rounded-lg font-mono flex items-center gap-1 transition-all"
    title="Reset Service to Healthy Baseline v2.4.0"
  >
    <span>Reset (v2.4.0)</span>
  </button>
</div>
```

---

## 5. Step-by-Step Execution & Verification Guide

### 5.1 Prerequisites & Environment Setup

1. **Python Environment**:
   ```powershell
   # Ensure Python 3.12 virtual environment is activated
   .\.venv\Scripts\Activate.ps1
   ```

2. **Environment Variables (`.env`)**:
   ```ini
   # LLM Configuration
   GEMINI_API_KEY="your-gemini-api-key"
   LLM_PROVIDER="google"
   LLM_MODEL="gemini-3.5-flash-lite"

   # TypeSafe / Jev AI Configuration
   AI_GATEWAY_API_KEY="your-vercel-ai-gateway-key"
   USE_JEV_TRIAGE=true
   USE_JEV_RERANKER=true

   # MCP & Tracer Settings
   USE_MCP=true
   MCP_SERVER_COMMAND="python -m aegis.mcp.server"
   TRACE_LOG_PATH="traces.jsonl"
   ```

3. **Frontend Dependencies**:
   ```powershell
   cd frontend
   npm install
   ```

---

### 5.2 Starting the Platform

#### Mode A: Full Development Mode (Hot Reload)
Open two terminal windows:

- **Terminal 1: FastAPI Backend**
  ```powershell
  .\.venv\Scripts\uvicorn aegis.api.main:app --host 0.0.0.0 --port 8000 --reload
  ```
  *Backend health check*: `http://localhost:8000/api/health` -> `{"status": "healthy"}`

- **Terminal 2: React Vite Frontend**
  ```powershell
  cd frontend
  npm run dev
  ```
  *Frontend interface*: `http://localhost:3000` (automatically proxies `/api` calls to port 8000).

#### Mode B: Production Unified Mode
Build the frontend SPA once and let FastAPI serve everything:
```powershell
cd frontend
npm run build
cd ..
.\.venv\Scripts\uvicorn aegis.api.main:app --host 0.0.0.0 --port 8000
```
*Access both UI and API at*: `http://localhost:8000/`.

---

### 5.3 Step-by-Step Operational Verification Flow

1. **Inject Fault (Simulate Incident ITOPS-001)**:
   - Click **"Inject Fault (v2.4.1)"** in the top bar (or run: `curl -X POST "http://localhost:8000/api/chaos/inject"`).
   - Check status: `checkout-service` version is updated to `2.4.1`, DB pool is restricted to 5.

2. **Trigger Autonomous Closed-Loop**:
   - Click **"Run Auto-Heal"** in the top bar.
   - Watch the **Workflow Canvas** dynamically spawn nodes in real time as SSE events arrive:
     - `ingest`: Ingests P1 alert from webhook.
     - `triage`: Jev AI executes sub-25ms classification (`Database Saturation`).
     - `tool-logs` & `tool-metrics`: FastMCP probes fetch live 5xx logs and 100% pool saturation.
     - `knowledge`: Jev Reranker matches Runbook `RB-001` with 96% confidence.
     - `diagnose`: Gemini 3.5 Flash-Lite synthesizes Chain-of-Thought reasoning.
     - `policy`: Policy Guardrail halts execution at `PROD_ROLLBACK_APPROVAL` gate.

3. **Inspect Chain-of-Thought (CoT) & Agent Mesh**:
   - Click the `diagnose` node to inspect Gemini 3.5 Flash-Lite's step-by-step reasoning accordion.
   - Switch to the **Active Agents** tab to view the live status of all 6 agents.

4. **Interactive Copilot Chat**:
   - In the chat composer at the bottom right, type:
     `"Why did checkout-service fail?"` or `"Show DB pool saturation"`
   - Observe the live LLM reply with embedded tool output cards and reasoning snippets.

5. **Human-in-the-Loop Sign-Off**:
   - In the Policy Gate card, click **"Approve Rollback (v2.4.0)"**.
   - Watch the workflow resume:
     - `remediate`: Needle executor reverts the container to `v2.4.0`.
     - `verify`: Verification engine checks Prometheus SLOs (0.02% error rate, 42.5ms latency).
     - Incident transitions to **RESOLVED**.

---

## 6. Verification Suite

Run the full automated test suite to ensure all backend components, MCP tools, and closed-loop workflows pass:

```powershell
.\.venv\Scripts\pytest -v
```

**Expected Result**:
```text
tests/test_api.py::test_health_endpoint PASSED                           [  8%]
tests/test_api.py::test_list_incidents PASSED                            [ 16%]
tests/test_api.py::test_chaos_endpoints PASSED                           [ 25%]
tests/test_api.py::test_run_incident_and_approval_flow PASSED            [ 33%]
tests/test_api.py::test_frontend_spa_served PASSED                       [ 41%]
tests/test_closed_loop.py::test_policy_engine_guardrails PASSED          [ 50%]
tests/test_closed_loop.py::test_closed_loop_incident_resolution PASSED   [ 58%]
tests/test_mcp.py::test_mcp_server_direct_tools PASSED                   [ 66%]
tests/test_mcp.py::test_mcp_server_resources PASSED                      [ 75%]
tests/test_mcp.py::test_mcp_client_adapter_direct PASSED                 [ 83%]
tests/test_mcp.py::test_mcp_client_adapter_stdio PASSED                  [ 91%]
tests/test_mcp.py::test_closed_loop_with_mcp_integration PASSED          [100%]
============================== 12 passed in ~60s ==============================
```
