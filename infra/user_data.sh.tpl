#!/bin/bash
# Runs once, as root, the first time the server boots.
set -euxo pipefail
exec > /var/log/meetup-setup.log 2>&1

# 1. Install Docker (engine + compose plugin) and git
apt-get update
apt-get install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker

# 2. Get the app code
git clone ${repo_url} /opt/meetup-rsvp
cd /opt/meetup-rsvp

# 3. Secrets and settings (readable by root only)
cat > .env <<'ENV'
GOOGLE_CLIENT_ID=${google_client_id}
GOOGLE_CLIENT_SECRET=${google_client_secret}
SESSION_SECRET=${session_secret}
SITE_ADDRESS=${domain}
HTTPS_ONLY=true
ENV
chmod 600 .env

# 4. Start app + PostgreSQL + Caddy (HTTPS)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build