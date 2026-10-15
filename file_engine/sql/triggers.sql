-- =============================================================================
-- Module 2 — DBMS Focus: PostgreSQL Triggers
-- Purpose:
--   1. Auto-log every complaint status change into system_logs.
--   2. Auto-update the complaints.updated_at timestamp.
--   3. Auto-update category avg_resolution_hours after a complaint resolves.
-- =============================================================================

-- Trigger 1: Log status changes automatically
CREATE OR REPLACE FUNCTION log_status_change()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO system_logs (action, complaint_id, description, old_value, new_value, timestamp)
        VALUES (
            'status_change',
            NEW.id,
            'Status changed for complaint #' || NEW.id::TEXT,
            OLD.status,
            NEW.status,
            NOW()
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_log_status_change ON complaints;
CREATE TRIGGER trg_log_status_change
    AFTER UPDATE OF status ON complaints
    FOR EACH ROW
    EXECUTE FUNCTION log_status_change();


-- Trigger 2: Auto-update last_modified timestamp on complaints
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_complaints_updated_at ON complaints;
CREATE TRIGGER trg_complaints_updated_at
    BEFORE UPDATE ON complaints
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();


-- Trigger 3: Recalculate avg resolution time for a category when complaint resolves
CREATE OR REPLACE FUNCTION update_category_avg_resolution()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'resolved' AND NEW.resolved_at IS NOT NULL THEN
        UPDATE complaint_categories
        SET avg_resolution_hours = (
            SELECT AVG(
                EXTRACT(EPOCH FROM (resolved_at - submitted_at)) / 3600.0
            )
            FROM complaints
            WHERE category_id = NEW.category_id
              AND status = 'resolved'
              AND resolved_at IS NOT NULL
        )
        WHERE id = NEW.category_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_avg_resolution ON complaints;
CREATE TRIGGER trg_update_avg_resolution
    AFTER UPDATE OF status, resolved_at ON complaints
    FOR EACH ROW
    EXECUTE FUNCTION update_category_avg_resolution();
