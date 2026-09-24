#!/bin/bash
set -e

echo "[Aegis Provisioning] Starting automated setup at $(date)..."

# 1. System packages
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl gnupg lsb-release git python3-pip python3-venv jq nginx

# 2. Docker Engine & Compose plugin
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable docker
systemctl start docker
chmod 666 /var/run/docker.sock

# 3. Clone repository
mkdir -p /opt/aegis
if [ -d "/opt/aegis/.git" ]; then
    cd /opt/aegis
    git fetch origin beta3
    git reset --hard origin/beta3
else
    git clone -b beta3 https://github.com/Shresth-k/Aegis.git /opt/aegis
fi

cd /opt/aegis

# 4. Configure production environment via GCP Secret Manager
PROJECT_ID=$(gcloud config get-value project 2>/dev/null || echo "aegis-509604")
GEMINI_KEY=$(gcloud secrets versions access latest --secret=GEMINI_API_KEY --project="${PROJECT_ID}" 2>/dev/null || echo "")
AI_GATEWAY_KEY=$(gcloud secrets versions access latest --secret=AI_GATEWAY_API_KEY --project="${PROJECT_ID}" 2>/dev/null || echo "")

cat << EOF > /opt/aegis/.env
GEMINI_API_KEY=${GEMINI_KEY}
AI_GATEWAY_API_KEY=${AI_GATEWAY_KEY}
VERCEL_AI_GATEWAY_KEY=${AI_GATEWAY_KEY}
MOCK_ACME_CLOUD=false
PROMETHEUS_URL=http://localhost:9090
USE_MCP=true
ENVIRONMENT=production
EOF

cat << 'EOF' > /opt/aegis/acmecloud/.env
POSTGRES_DB=acmecloud
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
CHECKOUT_PORT=8001
PROMETHEUS_PORT=9090
GRAFANA_PORT=3001
CHECKOUT_VERSION=2.4.0
EOF

# 5. Launch AcmeCloud live Docker Compose topology
echo "[Aegis Provisioning] Launching AcmeCloud Docker Compose stack..."
cd /opt/aegis/acmecloud
docker compose up -d

# 6. Python virtualenv & dependencies
echo "[Aegis Provisioning] Installing Python virtualenv and packages..."
python3 -m venv /opt/aegis/venv
/opt/aegis/venv/bin/pip install --upgrade pip
/opt/aegis/venv/bin/pip install -r /opt/aegis/requirements.txt
/opt/aegis/venv/bin/pip install uvicorn

# 7. Node.js & Frontend compilation
echo "[Aegis Provisioning] Installing Node.js 20 and compiling Frontend..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs
cd /opt/aegis/frontend
npm ci
npm run build

# 8. Nginx configuration (port 3000 -> dist & proxy /api/ to 8000)
echo "[Aegis Provisioning] Configuring Nginx reverse proxy on port 3000..."
cat << 'EOF' > /etc/nginx/sites-available/default
server {
    listen 3000 default_server;
    listen [::]:3000 default_server;

    root /opt/aegis/frontend/dist;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_buffering off;
        proxy_read_timeout 86400s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_set_header Host $host;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
EOF
systemctl restart nginx

# 9. Systemd service for Aegis Backend API (port 8000)
echo "[Aegis Provisioning] Creating and starting Aegis API systemd service..."
cat << 'EOF' > /etc/systemd/system/aegis.service
[Unit]
Description=Aegis Autonomous IT Operations Platform
After=network.target docker.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/aegis
EnvironmentFile=/opt/aegis/.env
ExecStart=/opt/aegis/venv/bin/uvicorn aegis.api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable aegis
systemctl restart aegis

echo "[Aegis Provisioning] Setup successfully completed at $(date)!"
