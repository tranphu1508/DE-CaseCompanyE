-- CompanyE publication v3. Replace schema ce_control ONLY for isolated fixtures.
-- Security-definer APIs, immutable publications, retained slots, no automatic GC.
BEGIN;
CREATE TABLE IF NOT EXISTS ce_control.publication_policy(singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton), entities jsonb NOT NULL, metrics jsonb NOT NULL);
CREATE TABLE IF NOT EXISTS ce_control.slot_reservation(slot text PRIMARY KEY, generation bigint NOT NULL DEFAULT 0, publication_id text, CHECK(slot IN ('CE_DWH_A','CE_DWH_B')));
INSERT INTO ce_control.slot_reservation(slot) VALUES ('CE_DWH_A'),('CE_DWH_B') ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS ce_control.publication_candidate(
 publication_id text PRIMARY KEY, run_id text NOT NULL REFERENCES ce_control.pipeline_run,
 slot text NOT NULL REFERENCES ce_control.slot_reservation, generation bigint NOT NULL,
 expected_active text, state text NOT NULL CHECK(state IN ('BUILDING','PREPARED','PUBLISHED')),
 manifest_text text, manifest_sha256 char(64), created_at timestamptz NOT NULL DEFAULT clock_timestamp());
CREATE TABLE IF NOT EXISTS ce_control.publication_event(
 event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, publication_id text NOT NULL,
 action text NOT NULL, occurred_at timestamptz NOT NULL DEFAULT clock_timestamp(), detail jsonb NOT NULL DEFAULT '{}');

CREATE OR REPLACE FUNCTION ce_control.begin_publication(pid text,rid text,target_slot text,previous text) RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,ce_control AS $$
DECLARE c ce_control.publication_candidate; active_id text; gen bigint;
BEGIN
 PERFORM pg_advisory_xact_lock(5173,2);
 IF pid !~ '^pub_[a-z0-9_]{8,100}$' THEN RAISE EXCEPTION 'Invalid publication ID'; END IF;
 SELECT * INTO c FROM ce_control.publication_candidate WHERE publication_id=pid;
 IF FOUND THEN
  IF c.run_id<>rid OR c.slot<>target_slot OR c.expected_active IS DISTINCT FROM previous THEN RAISE EXCEPTION 'Publication identity conflict'; END IF;
  RETURN c.generation;
 END IF;
 SELECT publication_id INTO active_id FROM ce_control.active_publication WHERE singleton;
 IF active_id IS DISTINCT FROM previous THEN RAISE EXCEPTION 'STALE_ACTIVE'; END IF;
 IF NOT EXISTS(SELECT 1 FROM ce_control.pipeline_run WHERE run_id=rid AND oracle_slot=target_slot AND state='ETL_READY') THEN RAISE EXCEPTION 'Run is not ETL_READY in requested slot'; END IF;
 IF EXISTS(SELECT 1 FROM ce_control.reader_lease l JOIN ce_control.publication p USING(publication_id) WHERE p.oracle_slot=target_slot AND l.expires_at>clock_timestamp()) THEN RAISE EXCEPTION 'SLOT_HAS_LIVE_READER'; END IF;
 IF EXISTS(SELECT 1 FROM ce_control.publication WHERE oracle_slot=target_slot) THEN RAISE EXCEPTION 'SLOT_RETAINED_NO_AUTOMATIC_REUSE'; END IF;
 UPDATE ce_control.slot_reservation SET generation=generation+1,publication_id=pid WHERE slot=target_slot AND publication_id IS NULL RETURNING generation INTO gen;
 IF gen IS NULL THEN RAISE EXCEPTION 'SLOT_RESERVED'; END IF;
 INSERT INTO ce_control.publication_candidate VALUES(pid,rid,target_slot,gen,previous,'BUILDING',NULL,NULL,clock_timestamp());
 INSERT INTO ce_control.publication_event(publication_id,action) VALUES(pid,'RESERVED');
 RETURN gen;
END $$;

CREATE OR REPLACE FUNCTION ce_control.prepare_publication(payload text,expected_generation bigint) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,ce_control AS $$
DECLARE m jsonb:=payload::jsonb; pid text:=m->>'publication_id'; c ce_control.publication_candidate;
 policy ce_control.publication_policy; item record; digest text:=encode(sha256(convert_to(payload,'UTF8')),'hex');
BEGIN
 PERFORM pg_advisory_xact_lock(5173,2);
 SELECT * INTO STRICT c FROM ce_control.publication_candidate WHERE publication_id=pid FOR UPDATE;
 IF c.generation IS DISTINCT FROM expected_generation OR (m->>'generation')::bigint IS DISTINCT FROM c.generation OR (m->>'oracle_slot') IS DISTINCT FROM c.slot OR (m->>'run_id') IS DISTINCT FROM c.run_id THEN RAISE EXCEPTION 'FENCED_OR_WRONG_RUN'; END IF;
 IF NOT EXISTS(SELECT 1 FROM ce_control.slot_reservation WHERE slot=c.slot AND generation=c.generation AND publication_id=pid) THEN RAISE EXCEPTION 'FENCED_SLOT'; END IF;
 IF c.state IN ('PREPARED','PUBLISHED') THEN
  IF c.manifest_text IS DISTINCT FROM payload THEN RAISE EXCEPTION 'IMMUTABLE_MANIFEST_CONFLICT'; END IF;
  RETURN c.manifest_sha256;
 END IF;
 SELECT * INTO STRICT policy FROM ce_control.publication_policy WHERE singleton;
 IF jsonb_typeof(m->'tables') IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(m->'tables'))<>(SELECT count(*) FROM jsonb_object_keys(policy.entities)) THEN RAISE EXCEPTION 'INCOMPLETE_ENTITY_INVENTORY'; END IF;
 FOR item IN SELECT key,value FROM jsonb_each(policy.entities) LOOP
  IF m->'tables'->item.key->>'name' IS DISTINCT FROM item.value->>'name' THEN RAISE EXCEPTION 'ENTITY_NAME_MISMATCH %',item.key; END IF;
  IF coalesce((m->'tables'->item.key->>'rows')::bigint,-1)<0 OR coalesce(m->'tables'->item.key->>'content_sha256','') !~ '^[0-9a-f]{64}$' THEN RAISE EXCEPTION 'INVALID_TABLE_EVIDENCE'; END IF;
  IF (item.value->>'mode') IS DISTINCT FROM (m->'tables'->item.key->>'mode') THEN RAISE EXCEPTION 'ENTITY_MODE_MISMATCH'; END IF;
  IF item.value->>'mode'='TABLE' AND coalesce((m->'tables'->item.key->>'snapshot_id')::bigint,0)<=0 THEN RAISE EXCEPTION 'MISSING_SNAPSHOT'; END IF;
  IF item.value->>'mode'='DISABLED' AND ((m->'tables'->item.key->>'rows')::bigint<>0 OR m->'tables'->item.key->>'snapshot_id' IS NOT NULL) THEN RAISE EXCEPTION 'DISABLED_ENTITY_HAS_DATA'; END IF;
  IF item.value->>'mode'='HELPER' AND NOT (coalesce(m->'helpers','{}') ? (item.value->>'name')) THEN RAISE EXCEPTION 'MISSING_HELPER'; END IF;
 END LOOP;
 IF jsonb_typeof(m->'quality_metrics') IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(m->'quality_metrics'))<>jsonb_array_length(policy.metrics) THEN RAISE EXCEPTION 'INCOMPLETE_KPI_QUALITY'; END IF;
 IF EXISTS(SELECT 1 FROM jsonb_array_elements_text(policy.metrics) x WHERE coalesce(m->'quality_metrics'->x.value->>'status','') NOT IN ('COMPLETE','PARTIAL','UNAVAILABLE')) THEN RAISE EXCEPTION 'INVALID_QUALITY_STATUS'; END IF;
 IF (m->'validation'->>'all_columns_equal') IS DISTINCT FROM 'true' OR (m->'validation'->>'oracle_sealed') IS DISTINCT FROM 'true' OR (m->'validation'->>'tags_pinned') IS DISTINCT FROM 'true' THEN RAISE EXCEPTION 'TARGET_VALIDATION_MISSING'; END IF;
 UPDATE ce_control.publication_candidate SET state='PREPARED',manifest_text=payload,manifest_sha256=digest WHERE publication_id=pid;
 INSERT INTO ce_control.publication_event(publication_id,action,detail) VALUES(pid,'PREPARED',jsonb_build_object('sha256',digest));
 RETURN digest;
END $$;

CREATE OR REPLACE FUNCTION ce_control.publish(pid text,expected_previous text,expected_generation bigint) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,ce_control AS $$
DECLARE c ce_control.publication_candidate; active_id text; m jsonb;
BEGIN
 PERFORM pg_advisory_xact_lock(5173,2);
 SELECT * INTO STRICT c FROM ce_control.publication_candidate WHERE publication_id=pid FOR UPDATE;
 IF c.generation IS DISTINCT FROM expected_generation THEN RAISE EXCEPTION 'FENCED_PUBLISHER'; END IF;
 SELECT publication_id INTO active_id FROM ce_control.active_publication WHERE singleton;
 IF c.state='PUBLISHED' THEN RETURN jsonb_build_object('outcome','ALREADY_COMMITTED','publication_id',pid,'active_publication',active_id); END IF;
 IF c.state<>'PREPARED' THEN RAISE EXCEPTION 'CANDIDATE_NOT_PREPARED'; END IF;
 IF active_id IS DISTINCT FROM expected_previous OR c.expected_active IS DISTINCT FROM expected_previous THEN RAISE EXCEPTION 'STALE_ACTIVE'; END IF;
 IF NOT EXISTS(SELECT 1 FROM ce_control.slot_reservation WHERE slot=c.slot AND generation=c.generation AND publication_id=pid) THEN RAISE EXCEPTION 'FENCED_SLOT'; END IF;
 m=c.manifest_text::jsonb;
 INSERT INTO ce_control.publication(publication_id,run_id,oracle_slot,manifest_sha256,manifest) VALUES(pid,c.run_id,c.slot,c.manifest_sha256,m);
 INSERT INTO ce_control.publication_table SELECT pid,key,(value->>'snapshot_id')::bigint,value->>'content_sha256' FROM jsonb_each(m->'tables');
 INSERT INTO ce_control.active_publication VALUES(true,pid) ON CONFLICT(singleton) DO UPDATE SET publication_id=excluded.publication_id;
 UPDATE ce_control.pipeline_run SET state='PUBLISHED' WHERE run_id=c.run_id;
 UPDATE ce_control.publication_candidate SET state='PUBLISHED' WHERE publication_id=pid;
 INSERT INTO ce_control.publication_event(publication_id,action,detail) VALUES(pid,'PUBLISHED',jsonb_build_object('previous',active_id));
 RETURN jsonb_build_object('outcome','COMMITTED','publication_id',pid,'active_publication',pid);
END $$;

CREATE OR REPLACE FUNCTION ce_control.acquire_reader(lid text,reader text,ttl integer) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,ce_control AS $$
DECLARE p ce_control.publication; expires timestamptz;
BEGIN
 PERFORM pg_advisory_xact_lock(5173,2);
 IF ttl<1 OR ttl>3600 OR length(lid)<32 OR length(reader) NOT BETWEEN 1 AND 128 THEN RAISE EXCEPTION 'INVALID_READER_REQUEST'; END IF;
 SELECT p0.* INTO p FROM ce_control.active_publication a JOIN ce_control.publication p0 USING(publication_id) WHERE a.singleton;
 IF NOT FOUND THEN RAISE EXCEPTION 'NO_ACTIVE_PUBLICATION'; END IF;
 expires:=clock_timestamp()+make_interval(secs=>ttl);
 INSERT INTO ce_control.reader_lease VALUES(lid,p.publication_id,expires,reader);
 RETURN jsonb_build_object('lease_id',lid,'expires_at',expires,'manifest',p.manifest,'manifest_sha256',p.manifest_sha256);
END $$;
CREATE OR REPLACE FUNCTION ce_control.renew_reader(lid text,pid text,ttl integer) RETURNS timestamptz
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,ce_control AS $$
DECLARE expires timestamptz;
BEGIN
 PERFORM pg_advisory_xact_lock(5173,2);
 IF ttl<1 OR ttl>3600 THEN RAISE EXCEPTION 'INVALID_TTL'; END IF;
 UPDATE ce_control.reader_lease SET expires_at=clock_timestamp()+make_interval(secs=>ttl) WHERE lease_id=lid AND publication_id=pid AND expires_at>clock_timestamp() RETURNING expires_at INTO expires;
 IF expires IS NULL THEN RAISE EXCEPTION 'LEASE_EXPIRED_OR_RELEASED'; END IF;
 RETURN expires;
END $$;
CREATE OR REPLACE FUNCTION ce_control.assert_reader(lid text,pid text) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,ce_control AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM ce_control.reader_lease WHERE lease_id=lid AND publication_id=pid AND expires_at>clock_timestamp()) THEN RAISE EXCEPTION 'LEASE_EXPIRED_OR_RELEASED'; END IF;
 RETURN true;
END $$;
CREATE OR REPLACE FUNCTION ce_control.release_reader(lid text,pid text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,ce_control AS $$
BEGIN
 PERFORM pg_advisory_xact_lock(5173,2);
 DELETE FROM ce_control.reader_lease WHERE lease_id=lid AND publication_id=pid;
END $$;
CREATE OR REPLACE FUNCTION ce_control.reject_publication_mutation() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN RAISE EXCEPTION 'PUBLICATION_IS_IMMUTABLE'; END $$;
DROP TRIGGER IF EXISTS publication_immutable ON ce_control.publication;
CREATE TRIGGER publication_immutable BEFORE UPDATE OR DELETE ON ce_control.publication FOR EACH STATEMENT EXECUTE FUNCTION ce_control.reject_publication_mutation();
DROP TRIGGER IF EXISTS publication_table_immutable ON ce_control.publication_table;
CREATE TRIGGER publication_table_immutable BEFORE UPDATE OR DELETE ON ce_control.publication_table FOR EACH STATEMENT EXECUTE FUNCTION ce_control.reject_publication_mutation();
REVOKE ALL ON FUNCTION ce_control.begin_publication(text,text,text,text),ce_control.prepare_publication(text,bigint),ce_control.publish(text,text,bigint),ce_control.acquire_reader(text,text,integer),ce_control.renew_reader(text,text,integer),ce_control.assert_reader(text,text),ce_control.release_reader(text,text) FROM PUBLIC;
GRANT USAGE ON SCHEMA ce_control TO ce_publisher,ce_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA ce_control TO ce_publisher;
GRANT EXECUTE ON FUNCTION ce_control.begin_publication(text,text,text,text),ce_control.prepare_publication(text,bigint),ce_control.publish(text,text,bigint) TO ce_publisher;
GRANT EXECUTE ON FUNCTION ce_control.acquire_reader(text,text,integer),ce_control.renew_reader(text,text,integer),ce_control.assert_reader(text,text),ce_control.release_reader(text,text) TO ce_reader;
INSERT INTO ce_control.schema_version VALUES(3,now()) ON CONFLICT DO NOTHING;
COMMIT;
