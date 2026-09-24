# Aegis & AcmeCloud: GCP Operations & Live Presentation Guide

This guide contains everything needed to manage, pause, resume, inspect, and present the live Aegis Autonomous IT Operations platform running on Google Cloud Platform (GCE).

---

## 1. Live Presentation Endpoints

All services are accessible globally from any laptop, tablet, or smartphone without VPN or local software:

| Service | Public URL | Description |
| :--- | :--- | :--- |
| **Aegis Mission Control** | `http://34.61.166.87:3000/` | AI SRE Co-Pilot interactive chat, autonomous tool execution cards, and live DAG workflow canvas. |
| **Acme Systems Storefront** | `http://34.61.166.87:8001/` | Customer-facing hardware store, checkout transaction ledger, live service telemetry, and build deployment simulator. |
| **Grafana Dashboards** | `http://34.61.166.87:3001/` | Real-time SRE metrics dashboards, connection pool gauges, and error rates. |
| **Prometheus TSDB** | `http://34.61.166.87:9090/` | Raw metrics scraper gathering transaction times and error rates from the checkout microservice. |

> **Permanent IP Guarantee**: The IP `34.61.166.87` has been promoted to a **Reserved Static External IP** (`aegis-static-ip`). Even if you stop and resume the VM, this IP address will never change.

---

## 2. Pausing, Stopping, and Resuming the Cloud VM

To avoid consuming your $300 Google Cloud Free Trial credits when not presenting, you can stop or resume the VM at any time.

### Difference Between Stop and Suspend

| Action | What Happens | Billing Impact | When to Use |
| :--- | :--- | :--- | :--- |
| **STOP** (Recommended) | Fully shuts down the VM. Memory is cleared. All services automatically restart on boot via systemd and Docker `restart: unless-stopped`. | **$0 / hour for CPU & RAM**. You only pay pennies per month for persistent disk storage (~$0.04/GB/month). | Use when finished testing or overnight before presentation day. |
| **SUSPEND** | Pauses VM execution and writes memory state to disk. Resumes slightly faster. | Disk storage charges apply for the memory image. | Short breaks (15-30 minutes). |

### How to Stop the VM

#### Option A: Google Cloud Console
1. Open [Compute Engine VM Instances](https://console.cloud.google.com/compute/instances?project=aegis-509604).
2. Select the checkbox next to **`aegis-vm`**.
3. Click the **STOP** button at the top toolbar (square stop icon).
4. Wait approximately 30 seconds until the status icon turns gray.

#### Option B: Google Cloud CLI (from your terminal)
```powershell
gcloud compute instances stop aegis-vm --zone=us-central1-a --project=aegis-509604
```

### How to Resume (Start) the VM

#### Option A: Google Cloud Console
1. Open [Compute Engine VM Instances](https://console.cloud.google.com/compute/instances?project=aegis-509604).
2. Select the checkbox next to **`aegis-vm`**.
3. Click the **START / RESUME** button at the top toolbar (play triangle icon).
4. Wait approximately 45-60 seconds.

#### Option B: Google Cloud CLI (from your terminal)
```powershell
gcloud compute instances start aegis-vm --zone=us-central1-a --project=aegis-509604
```

> **Automatic Recovery on Boot**: All services (Docker containers, PostgreSQL, Prometheus, Grafana, Nginx reverse proxy, and Aegis FastAPI) are configured with automatic boot persistence. When you start the VM, everything boots up cleanly without running any manual commands.

---

## 3. Where API Keys and Secrets Live in GCP

Security best practice: No API keys are hardcoded in the repository.

### How Cloud Architecture Manages Secrets
1. **GCP Secret Manager**:
   - Primary storage for production credentials.
   - `GEMINI_API_KEY`: Google Gemini API key.
   - `AI_GATEWAY_API_KEY`: Vercel AI Gateway / TypeSafe Jev API key.
2. **VM Boot Decryption**:
   - The VM startup script fetches the latest secret payloads directly from Secret Manager via GCP IAM Service Account tokens.
   - Writes secrets to `/opt/aegis/.env` with strict `chmod 600` (root-only access).
3. **Process Isolation**:
   - The systemd unit `/etc/systemd/system/aegis.service` passes `/opt/aegis/.env` into the Python process.
   - Keys are kept in process memory only.

### Where to See Secrets in Google Cloud Console
- Direct Link: [GCP Secret Manager](https://console.cloud.google.com/security/secret-manager?project=aegis-509604)
- Path: Top-left navigation menu -> **Security** -> **Secret Manager**.
- You will see:
  - `GEMINI_API_KEY`
  - `AI_GATEWAY_API_KEY`
- Click any secret name and go to the **Versions** tab to see creation dates, add new versions, or inspect metadata.

### How to View the Environment File on the VM (via SSH)
```bash
sudo cat /opt/aegis/.env
```

---

## 4. How to Verify Docker Container Actions in Real Time

During a live presentation, judges or evaluators will want proof that Aegis is managing real Linux containers and not a simulation.

### Verification 1: Terminal Proof via Docker CLI
Run these commands over SSH to inspect the live container:
```bash
# Check container status and running duration
docker ps --filter "name=acmecloud-checkout"

# Inspect exact timestamp when container started/restarted
docker inspect --format='{{.State.StartedAt}}' acmecloud-checkout

# Inspect container restart count
docker inspect --format='Restart Count: {{.RestartCount}}' acmecloud-checkout

# View real container logs showing connection pool recovery
docker logs --tail 25 acmecloud-checkout
```

### Verification 2: In the Acme Systems Storefront UI (`:8001`)
1. Look at the bottom **Live Service Status** drawer.
2. The **Containers** indicator displays real-time health, uptime (e.g. `Up 45 seconds`), and container IDs directly from Docker engine.
3. When Aegis restarts or rolls back the container, the uptime counter resets to `Up 1 second`.

### Verification 3: In the Aegis Mission Control Chat UI (`:3000`)
1. In the agent stream, expand the **Tool Execution Card** for `docker_restart_container` or `rollback_deployment`.
2. It outputs:
   - Command: `docker restart acmecloud-checkout`
   - Exit Code: `0`
   - Execution Time: ~1,200ms
3. The subsequent `verify_slo` card shows the real-time Prometheus error rate dropping from 38% down to 0.0%.

---

## 5. Google Cloud Console Navigation Cheat-Sheet

Use these direct links during your presentation to showcase GCP cloud-native infrastructure:

| Resource | Console Navigation Path | Direct Link |
| :--- | :--- | :--- |
| **Virtual Machine** | Navigation Menu -> Compute Engine -> VM instances | [VM Instances](https://console.cloud.google.com/compute/instances?project=aegis-509604) |
| **VM Observability** | Compute Engine -> click `aegis-vm` -> Monitoring tab | [VM Monitoring](https://console.cloud.google.com/compute/instancesDetail/zones/us-central1-a/instances/aegis-vm?project=aegis-509604&tab=monitoring) |
| **Static IP Address** | Navigation Menu -> VPC network -> IP addresses | [External IP Addresses](https://console.cloud.google.com/networking/addresses/list?project=aegis-509604) |
| **Cloud Firewall** | Navigation Menu -> VPC network -> Firewall | [Firewall Rules](https://console.cloud.google.com/net-security/firewall-manager/firewall-policies/list?project=aegis-509604) |
| **Secret Manager** | Navigation Menu -> Security -> Secret Manager | [Secret Manager](https://console.cloud.google.com/security/secret-manager?project=aegis-509604) |
| **Cloud Logging** | Navigation Menu -> Logging -> Logs Explorer | [Logs Explorer](https://console.cloud.google.com/logs/query?project=aegis-509604) |
| **Free Trial Credits** | Navigation Menu -> Billing -> Overview | [Billing Overview](https://console.cloud.google.com/billing?project=aegis-509604) |

---

## 6. Recommended 3-Minute Live Presentation Runbook

Follow this sequence for a compelling live demonstration:

### Step 1: Show the Healthy Storefront (30 seconds)
1. Open `http://34.61.166.87:8001/` in your browser.
2. Add an item (e.g. "Google Cloud TPU v5e") to the cart.
3. Click **Proceed to Checkout**.
4. Point out the green order confirmation and nominal latency (<50ms).
5. Open the bottom drawer to show `v2.4.0 Baseline Production Release` is active.

### Step 2: Inject an Operational Incident (30 seconds)
1. In the bottom drawer of the storefront, find the **Deploy Operational Builds** selector.
2. Select **v2.4.1 (DB Connection Pool Starvation)** and click **Deploy**.
3. Try clicking **Checkout** again: The transaction fails with **HTTP 500 Database Connection Pool Exhausted**.
4. Show that real customers are experiencing an outage.

### Step 3: Open Aegis Mission Control (60 seconds)
1. Open `http://34.61.166.87:3000/`.
2. Notice the clean, minimalist canvas waiting for conversation.
3. In the chat box, type:
   > *"Investigate checkout service outage and resolve it"*
4. Highlight the live agentic execution:
   - **Jev AI Incident Triage**: Classified severity as P1 database outage with 98% confidence.
   - **Telemetry MCP**: Live Prometheus metrics card showing error rate spike.
   - **Log Scraper MCP**: Docker container logs showing connection timeouts.
   - **Jev Noul Reranker**: Retaining runbook `RB-001 (Connection Pool Exhaustion)`.
   - **Dynamic DAG Graph**: Canvas nodes generate progressively in sync with agent actions.

### Step 4: Human-in-the-Loop Safety Gate & Auto-Heal (60 seconds)
1. Point out the **Policy Guardrail Card**: Aegis identifies that production rollback is HIGH risk and halts execution.
2. Click the green **Approve Rollback** button in the chat (or type *"approve"* in the chat input).
3. Aegis executes the container rollback to `v2.4.0` in live Docker, clears database locks, and runs SLO verification.
4. Show the status turning to **RESOLVED**.
5. Switch back to `http://34.61.166.87:8001/`, click **Checkout**, and show that customer transactions are immediately working again.
