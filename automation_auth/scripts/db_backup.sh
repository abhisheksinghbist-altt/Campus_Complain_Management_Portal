#!/usr/bin/env bash
# =============================================================================
# Module 4 — OS Focus: Shell Scripting + Cron Job
# Purpose: Automated nightly PostgreSQL database backup
# Cron schedule: 0 0 * * *   (midnight every day)
# Add to crontab: crontab -e  →  0 0 * * * /path/to/db_backup.sh
# =============================================================================
set -euo pipefail

DB_NAME="campus_portal_db"
DB_USER="postgres"
BACKUP_DIR="/var/backups/campus_portal"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.sql.gz"
LOG_FILE="${BACKUP_DIR}/backup.log"
RETENTION_DAYS=7

# Ensure backup directory exists with restricted permissions
mkdir -p "${BACKUP_DIR}"
chmod 700 "${BACKUP_DIR}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

log "INFO  Starting backup of ${DB_NAME}..."

# Dump and compress in one pipe — no uncompressed file on disk
if pg_dump -U "${DB_USER}" "${DB_NAME}" | gzip > "${BACKUP_FILE}"; then
    chmod 600 "${BACKUP_FILE}"
    SIZE=$(du -sh "${BACKUP_FILE}" | cut -f1)
    log "INFO  Backup successful: ${BACKUP_FILE} (${SIZE})"
else
    log "ERROR Backup FAILED for ${DB_NAME}"
    exit 1
fi

# Remove backups older than RETENTION_DAYS
log "INFO  Purging backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "backup_*.sql.gz" -mtime "+${RETENTION_DAYS}" -delete

log "INFO  Backup job complete."
