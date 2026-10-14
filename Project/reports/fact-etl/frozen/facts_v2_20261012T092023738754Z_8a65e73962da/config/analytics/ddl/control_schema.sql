-- Version 1: operational metadata only; never a third analytical data store.
BEGIN;
CREATE TABLE IF NOT EXISTS ce_control.schema_version (
 version integer PRIMARY KEY, installed_at timestamptz NOT NULL DEFAULT now());
INSERT INTO ce_control.schema_version VALUES (1,now()) ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS ce_control.key_registry (
 surrogate_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY CHECK(surrogate_key>0),
 canonical_key jsonb NOT NULL UNIQUE CHECK(jsonb_typeof(canonical_key)='array'),
 registered_at timestamptz NOT NULL DEFAULT now());
-- No hash truncation; uniqueness compares the complete ordered JSON array.
CREATE OR REPLACE FUNCTION ce_control.allocate_keys(keys jsonb) RETURNS jsonb
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,ce_control AS $$
DECLARE result jsonb;
BEGIN
 IF jsonb_typeof(keys)<>'array' OR EXISTS(
 SELECT 1 FROM jsonb_array_elements(keys) x WHERE jsonb_typeof(x)<>'array' OR jsonb_array_length(x)<3)
 THEN RAISE EXCEPTION 'Invalid canonical key list'; END IF;
 INSERT INTO ce_control.key_registry(canonical_key)
 SELECT DISTINCT value FROM jsonb_array_elements(keys) ORDER BY value
 ON CONFLICT(canonical_key) DO NOTHING;
 SELECT coalesce(jsonb_agg(jsonb_build_array(k.canonical_key,k.surrogate_key)),'[]'::jsonb)
 INTO result FROM ce_control.key_registry k WHERE k.canonical_key IN (SELECT value FROM jsonb_array_elements(keys));
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION ce_control.allocate_keys(jsonb) FROM PUBLIC;
CREATE TABLE IF NOT EXISTS ce_control.pipeline_run (
 run_id text PRIMARY KEY, source_batch_id text NOT NULL, input_manifest_sha256 char(64) NOT NULL,
 transform_version char(64) NOT NULL, started_at timestamptz NOT NULL,
 state text NOT NULL CHECK(state IN ('RUNNING','DIMENSIONS_READY','FAILED','PUBLISHED')),
 oracle_slot text NOT NULL CHECK(oracle_slot IN ('CE_DWH_A','CE_DWH_B')),
 finished_at timestamptz, evidence jsonb NOT NULL DEFAULT '{}'::jsonb);
CREATE TABLE IF NOT EXISTS ce_control.quality_entity (
 run_id text REFERENCES ce_control.pipeline_run, entity_id text NOT NULL,
 status text NOT NULL CHECK(status IN ('COMPLETE','PARTIAL','UNAVAILABLE')),
 accepted bigint NOT NULL CHECK(accepted>=0), rejected bigint NOT NULL CHECK(rejected>=0),
 coverage numeric CHECK(coverage BETWEEN 0 AND 1), detail jsonb NOT NULL,
 PRIMARY KEY(run_id,entity_id));
CREATE TABLE IF NOT EXISTS ce_control.quality_metric (
 run_id text REFERENCES ce_control.pipeline_run, metric_id text NOT NULL,
 status text NOT NULL CHECK(status IN ('COMPLETE','PARTIAL','UNAVAILABLE')),
 reason jsonb NOT NULL, PRIMARY KEY(run_id,metric_id));
CREATE TABLE IF NOT EXISTS ce_control.publication (
 publication_id text PRIMARY KEY, run_id text NOT NULL REFERENCES ce_control.pipeline_run,
 oracle_slot text NOT NULL CHECK(oracle_slot IN ('CE_DWH_A','CE_DWH_B')),
 manifest_sha256 char(64) NOT NULL, manifest jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS ce_control.publication_table (
 publication_id text REFERENCES ce_control.publication, entity_id text NOT NULL,
 snapshot_id bigint, canonical_sha256 char(64) NOT NULL,
 PRIMARY KEY(publication_id,entity_id));
CREATE TABLE IF NOT EXISTS ce_control.active_publication (
 singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
 publication_id text NOT NULL REFERENCES ce_control.publication);
CREATE TABLE IF NOT EXISTS ce_control.reader_lease (
 lease_id text PRIMARY KEY, publication_id text NOT NULL REFERENCES ce_control.publication,
 expires_at timestamptz NOT NULL, reader_name text NOT NULL);
CREATE TABLE IF NOT EXISTS ce_control.benchmark_run (
 benchmark_id text PRIMARY KEY, publication_id text REFERENCES ce_control.publication,
 configuration jsonb NOT NULL, measurements jsonb NOT NULL);
GRANT USAGE ON SCHEMA ce_control TO ce_control_writer;
GRANT SELECT ON ALL TABLES IN SCHEMA ce_control TO ce_control_writer;
GRANT EXECUTE ON FUNCTION ce_control.allocate_keys(jsonb) TO ce_control_writer;
GRANT INSERT,UPDATE ON ce_control.pipeline_run,ce_control.quality_entity,ce_control.quality_metric TO ce_control_writer;
-- Publication and registry mutation cannot be performed directly by this loader.
COMMIT;
