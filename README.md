# Campus Complaint Management Portal

A Django + PostgreSQL web application for managing campus maintenance complaints,
built as a PBL project demonstrating **DBMS** and **OS** concepts.

## Module Structure

| Folder | Module | Key Concepts |
|---|---|---|
| `automation_auth/` | Module 4 | Auth/RBAC, Shell backup script, Cron |
| `submission_monitoring/` | Module 5 | Complaint submission, Process health-check script |
| `concurrency_transactions/` | Module 1 | ACID transactions, SELECT FOR UPDATE (mutex) |
| `file_engine/` | Module 2 | Secure file I/O, directory permissions, DB Triggers |
| `analytics_scheduling/` | Module 3 | Dashboard aggregates, Priority/SJF scheduling |
| `status_caching/` | Module 6 | Status tracking, File-based caching |

## Setup

```bash
# 1. Create the PostgreSQL database
createdb campus_portal_db

# 2. Install dependencies
pip install -r requirements.txt

# 3. Apply migrations
python manage.py migrate

# 4. Load default categories
python manage.py loaddata initial_categories

# 5. Create a superuser (admin role)
python manage.py createsuperuser

# 6. Run the development server
python manage.py runserver
```

## Apply PostgreSQL Triggers

After running migrations:
```bash
psql -U postgres -d campus_portal_db -f file_engine/sql/triggers.sql
```

## Cron Jobs (OS Module)

```
# Nightly DB backup at midnight (Module 4)
0 0 * * * /path/to/automation_auth/scripts/db_backup.sh

# Process health check every 5 minutes (Module 5)
*/5 * * * * /path/to/submission_monitoring/scripts/health_check.sh
```
