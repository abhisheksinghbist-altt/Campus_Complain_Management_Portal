#!/usr/bin/env bash
# =============================================================================
# Module 5 — OS Focus: Process Monitoring
# Purpose: Check if Django (gunicorn) and PostgreSQL processes are running.
#          Logs an alert if either crashes.
# Usage: Run manually or via cron every 5 minutes:
#   */5 * * * * /path/to/health_check.sh
# =============================================================================
set -euo pipefail

LOG_FILE="/var/log/campus_portal/health.log"
ALERT_FILE="/var/log/campus_portal/alerts.log"
APP_PORT=8000
DB_HOST="localhost"
DB_PORT=5432

mkdir -p "$(dirname "${LOG_FILE}")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

alert() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ALERT: $1" | tee -a "${ALERT_FILE}"
    # Extend here: send email, Slack webhook, etc.
}

log "--- Health Check Start ---"

# 1. Check Django/Gunicorn process
if pgrep -f "gunicorn.*campus_portal" > /dev/null 2>&1; then
    log "OK    Django/Gunicorn is running."
else
    alert "Django/Gunicorn process NOT found! Attempting restart..."
    # Restart command (adjust path for your deployment)
    # systemctl restart campus_portal || true
fi

# 2. Check PostgreSQL connectivity
if pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -q 2>/dev/null; then
    log "OK    PostgreSQL is accepting connections on port ${DB_PORT}."
else
    alert "PostgreSQL is NOT accepting connections on ${DB_HOST}:${DB_PORT}!"
fi

# 3. Check HTTP endpoint responsiveness
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    "http://localhost:${APP_PORT}/complaints/health/" 2>/dev/null || echo "000")

if [ "${HTTP_STATUS}" = "200" ]; then
    log "OK    HTTP health endpoint returned 200."
else
    alert "HTTP health endpoint returned ${HTTP_STATUS} (expected 200)!"
fi

log "--- Health Check End ---"
