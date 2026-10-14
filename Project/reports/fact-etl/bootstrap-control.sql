BEGIN;
ALTER TABLE ce_control.pipeline_run DROP CONSTRAINT IF EXISTS pipeline_run_state_check;
ALTER TABLE ce_control.pipeline_run ADD CONSTRAINT pipeline_run_state_check CHECK(state IN ('RUNNING','DIMENSIONS_READY','ETL_READY','FAILED','PUBLISHED'));
INSERT INTO ce_control.schema_version VALUES (2,now()) ON CONFLICT DO NOTHING;
COMMIT;
