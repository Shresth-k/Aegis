# Aegis & AcmeCloud: Complete Google Cloud Platform (GCP) Deployment Guide

This guide provides end-to-end instructions for deploying the entire Aegis Autonomous SRE platform and AcmeCloud simulated microservices onto Google Cloud Platform.

---

## 1. System Topology & GCP Service Mapping

```
[ User Browser ]
       |
       +---> [ Cloud Load Balancing / Cloud CDN ]
                   |
                   +---> [ Cloud Run: aegis-frontend (:80) ] (Aegis Mission Control)
                   |           | (Proxies /api/*)
                   +---> [ Cloud Run: acme-store (:80) ]    (Independent Acme Store)
                   |           | (Proxies /checkout/* & /api/*)
                   +---> [ Cloud Run: aegis-api (:8000) ]   (Aegis Agent Engine)
                               |
                               +---> Gemini 3.5 Flash-Lite (Google AI API)
                               +---> TypeSafe Jev AI (Vercel AI Gateway)
                               +---> [ Cloud Run: acmecloud-checkout (:8000) ]
                                           |
                                           +---> [ Cloud SQL: PostgreSQL 17 ]
                                           +---> [ Managed Service for Prometheus (GMP) ]
```

| Local Component | Local Port | GCP Production Service | Description |
| :--- | :--- | :--- | :--- |
| **Aegis FastAPI Backend** | `8000` | **Google Cloud Run** (`aegis-api`) | LangGraph, Gemini 3.5 Flash-Lite, FastMCP, SSE Streaming |
| **Aegis Mission Control** | `3000` | **Google Cloud Run** (`aegis-frontend`) | React + Vite + React Flow Canvas + Live Agent Chat |
| **Acme Storefront** | `3002` | **Google Cloud Run** (`acme-store`) | Customer-facing store + simulated deployment injector |
| **Checkout Microservice** | `8001` | **Google Cloud Run** (`acmecloud-checkout`) | Target microservice with `/metrics` and simulated faults |
| **PostgreSQL Database** | `5432` | **Google Cloud SQL** (PostgreSQL 17) | Fully managed production database with private IP |
| **Prometheus Metrics** | `9090` | **Google Cloud Managed Prometheus** | Native scraping of checkout `/metrics` endpoint |
| **Secrets & Keys** | `.env` | **Google Secret Manager** | Secure injection of `GEMINI_API_KEY` & `AI_GATEWAY_API_KEY` |

---

## 2. Prerequisites & GCP Initial Setup

### 2.1 Install & Authenticate Google Cloud CLI
Ensure you have the Google Cloud SDK installed on your workstation:
```powershell
# Verify installation
gcloud version

# Login to your Google account
gcloud auth login

# Set your active GCP project
gcloud config set project YOUR_GCP_PROJECT_ID

# Set your default compute region
gcloud config set run/region us-central1
```

### 2.2 Enable Required GCP APIs
Run the following command to enable all necessary Google Cloud APIs:
```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  sqladmin.googleapis.com \
  vpcaccess.googleapis.com \
  compute.googleapis.com \
  monitoring.googleapis.com
```

### 2.3 Create Artifact Registry Docker Repository
Create a secure, private Docker registry to store your container images:
```bash
gcloud artifacts repositories create aegis-repo \
  --repository-format=docker \
  --location=us-central1 \
  --description="Aegis and AcmeCloud container images"
```

---

## 3. Configure Google Secret Manager

Store sensitive API credentials securely in Secret Manager instead of hardcoding them into environment variables:

```bash
# Store Gemini API Key
echo -n "YOUR_GEMINI_API_KEY" | gcloud secrets create GEMINI_API_KEY \
  --replication-policy="automatic" \
  --data-file=-

# Store Vercel / TypeSafe AI Gateway Key
echo -n "YOUR_AI_GATEWAY_API_KEY" | gcloud secrets create AI_GATEWAY_API_KEY \
  --replication-policy="automatic" \
  --data-file=-

# Store PostgreSQL Database Password
echo -n "StrongDatabasePassword123" | gcloud secrets create POSTGRES_PASSWORD \
  --replication-policy="automatic" \
  --data-file=-
```

Grant Cloud Run's default compute service account access to read these secrets:
```bash
PROJECT_NUM=$(gcloud projects describe $(gcloud config get-value project) --format='value(projectNumber)')

gcloud secrets add-iam-policy-binding GEMINI_API_KEY \
  --member="serviceAccount:${PROJECT_NUM}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding AI_GATEWAY_API_KEY \
  --member="serviceAccount:${PROJECT_NUM}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding POSTGRES_PASSWORD \
  --member="serviceAccount:${PROJECT_NUM}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## 4. Provision Cloud SQL (PostgreSQL 17)

Provision a managed PostgreSQL instance for AcmeCloud:

```bash
# Create Cloud SQL Instance
gcloud sql instances create acmecloud-postgres-db \
  --database-version=POSTGRES_17 \
  --tier=db-custom-2-7680 \
  --region=us-central1 \
  --root-password="StrongDatabasePassword123" \
  --storage-auto-increase \
  --availability-type=zonal

# Create Application Database
gcloud sql databases create acmedb --instance=acmecloud-postgres-db

# Create Application User
gcloud sql users create acmeuser \
  --instance=acmecloud-postgres-db \
  --password="StrongDatabasePassword123"
```

---

## 5. Build Container Images via Cloud Build

Submit builds for all four services directly to Google Cloud Build (no local Docker required):

```bash
PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"
REPO="aegis-repo"

# 1. Build & Push Aegis FastAPI Backend
gcloud builds submit \
  --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/aegis-api:latest \
  -f Dockerfile.api .

# 2. Build & Push Aegis Mission Control Frontend
gcloud builds submit \
  --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/aegis-frontend:latest \
  frontend

# 3. Build & Push Acme Storefront
gcloud builds submit \
  --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/acme-store:latest \
  acmecloud/frontend

# 4. Build & Push AcmeCloud Checkout Microservice
gcloud builds submit \
  --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/acmecloud-checkout:latest \
  -f acmecloud/simulator/services/checkout/Dockerfile \
  acmecloud
```

---

## 6. Deploy Services to Google Cloud Run

### 6.1 Deploy AcmeCloud Checkout Service
```bash
PROJECT_ID=$(gcloud config get-value project)
INSTANCE_CONNECTION_NAME=$(gcloud sql instances describe acmecloud-postgres-db --format='value(connectionName)')

gcloud run deploy acmecloud-checkout \
  --image=us-central1-docker.pkg.dev/${PROJECT_ID}/aegis-repo/acmecloud-checkout:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --port=8000 \
  --cpu=1 \
  --memory=1Gi \
  --min-instances=1 \
  --add-cloudsql-instances=${INSTANCE_CONNECTION_NAME} \
  --set-env-vars="DATABASE_URL=postgresql+psycopg://acmeuser:StrongDatabasePassword123@/acmedb?host=/cloudsql/${INSTANCE_CONNECTION_NAME},CHECKOUT_VERSION=2.4.0"
```
Retrieve the Checkout Service URL:
```bash
CHECKOUT_URL=$(gcloud run services describe acmecloud-checkout --region=us-central1 --format='value(status.url)')
echo "Checkout Service URL: $CHECKOUT_URL"
```

### 6.2 Deploy Aegis FastAPI Backend
> **Critical Cloud Run Flags for Autonomous Agent Streaming**:
> - `--no-cpu-throttling`: Keeps CPU active outside request handling to maintain continuous SSE streams.
> - `--session-affinity`: Ensures multi-turn interactive chat sessions route consistently.
> - `--timeout=3600`: Prevents Cloud Run from terminating long-running LangGraph investigation pipelines.
> - `--min-instances=1`: Eliminates cold-start latency for real-time SRE reasoning.

```bash
gcloud run deploy aegis-api \
  --image=us-central1-docker.pkg.dev/${PROJECT_ID}/aegis-repo/aegis-api:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --port=8000 \
  --cpu=2 \
  --memory=2Gi \
  --min-instances=1 \
  --max-instances=10 \
  --timeout=3600 \
  --no-cpu-throttling \
  --session-affinity \
  --set-env-vars="ENVIRONMENT=production,DEBUG=false,LLM_PROVIDER=google,LLM_MODEL=gemini-3.5-flash-lite,USE_JEV_TRIAGE=true,USE_JEV_RERANKER=true,ACME_CLOUD_API_URL=${CHECKOUT_URL}" \
  --set-secrets="GEMINI_API_KEY=GEMINI_API_KEY:latest,AI_GATEWAY_API_KEY=AI_GATEWAY_API_KEY:latest"
```
Retrieve the Aegis API URL:
```bash
AEGIS_API_URL=$(gcloud run services describe aegis-api --region=us-central1 --format='value(status.url)')
echo "Aegis API URL: $AEGIS_API_URL"
```

### 6.3 Deploy Aegis Mission Control Frontend
```bash
gcloud run deploy aegis-frontend \
  --image=us-central1-docker.pkg.dev/${PROJECT_ID}/aegis-repo/aegis-frontend:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --port=80 \
  --cpu=1 \
  --memory=512Mi \
  --set-env-vars="BACKEND_API_URL=${AEGIS_API_URL}"
```

### 6.4 Deploy Acme Storefront
```bash
gcloud run deploy acme-store \
  --image=us-central1-docker.pkg.dev/${PROJECT_ID}/aegis-repo/acme-store:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --port=80 \
  --cpu=1 \
  --memory=512Mi \
  --set-env-vars="BACKEND_API_URL=${AEGIS_API_URL},CHECKOUT_SERVICE_URL=${CHECKOUT_URL}"
```

---

## 7. Alternative: Single-VM Lift-and-Shift on Compute Engine (GCE)

If you require 100% parity with the local Docker daemon (e.g. for a live demo or hackathon presentation where `docker_ps`, `docker_logs`, and `docker_restart_container` run directly on the host VM daemon):

```bash
# Create an e2-standard-4 Ubuntu VM on Google Compute Engine
gcloud compute instances create aegis-demo-vm \
  --zone=us-central1-a \
  --machine-type=e2-standard-4 \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=50GB \
  --tags=http-server,https-server \
  --metadata=startup-script='#!/bin/bash
    apt-get update && apt-get install -y docker.io docker-compose git curl
    usermod -aG docker ubuntu
    systemctl enable docker
  '

# Allow ports in GCP firewall
gcloud compute firewall-rules create allow-aegis-ports \
  --allow=tcp:3000,tcp:3001,tcp:3002,tcp:8000,tcp:8001,tcp:9090 \
  --target-tags=http-server

# SSH into the VM and clone the repository
gcloud compute ssh aegis-demo-vm --zone=us-central1-a
```

Inside the VM:
```bash
git clone https://github.com/Shresth-k/Aegis.git
cd Aegis
# Add your .env credentials
cp .env.example .env
nano .env

# Launch services
docker compose -f acmecloud/docker-compose.yml up -d
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn aegis.api.main:app --host 0.0.0.0 --port 8000 &
```

---

## 8. Post-Deployment Verification Runbook

Once deployed, verify the entire live topology:

1. **Verify Aegis API Health**:
   ```bash
   curl -s ${AEGIS_API_URL}/api/health
   # Expected response: {"status":"healthy","service":"aegis-api"}
   ```

2. **Verify Gemini & Jev Reasoning over Cloud Run**:
   ```bash
   curl -X POST ${AEGIS_API_URL}/api/chat \
     -H "Content-Type: application/json" \
     -d '{"incident_id": "INC-001", "message": "Investigate checkout service telemetry"}'
   ```

3. **Verify Mission Control UI**:
   Open the `aegis-frontend` URL in your browser. The Workflow Canvas will initialize in clean standby, and the right-hand Chat Panel will connect directly to the Cloud Run backend.

4. **Verify Acme Storefront & Cross-Service Synchronicity**:
   Open the `acme-store` URL. Deploy a simulated build (e.g. `v2.4.1`) from the header dropdown. Verify that Aegis Mission Control immediately detects the degradation and displays the alert in real time.
