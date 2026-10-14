"""Independent expected SCD boundaries plus real Oracle/Iceberg writes.

Uses empty CE_DWH_B.DIM_SITE and isolated ce.etl_test.dim_site. All fixture
business rows are removed in finally; gold tables and source lake stay intact.
"""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta
from pathlib import Path
import csv,hashlib,json
from pyspark.sql import functions as F
from analytics_runtime.scd2 import canonical,payload_hash,materialize,timeline,lookup,EffectiveConflict,scalar
from analytics_runtime.etl_io import Jdbc,frame,oracle_rows,fingerprint
from analytics_runtime.dimension_transform import read_sources,dimension_inputs,BOOTSTRAP,parse

def exercise(spark):
    from analytics_runtime.dimensions import validate,save,OUT
    manifest=json.loads(Path('/workspace/config/analytics/ddl/manifest.json').read_text())
    entity=next(e for e in manifest['entities'] if e['id']=='D02')
    pg=Jdbc(spark,'postgres');ora=Jdbc(spark,'oracle');tests=[]
    assert pg.query('SELECT pg_try_advisory_lock(5173,1)')[0][0]=='t'
    assert pg.query('SELECT count(*) FROM ce_control.publication')[0][0]=='0'
    assert ora.query('SELECT count(*) FROM CE_DWH_B.DIM_SITE')[0][0]=='0','Fixture slot not empty'
    table='ce.etl_test.dim_site';spark.sql('CREATE NAMESPACE IF NOT EXISTS ce.etl_test')
    ddl=next(x['sql'] for x in manifest['iceberg_statements'] if 'ce.gold.dim_site ' in x['sql'])
    spark.sql(ddl.replace('ce.gold.dim_site','ce.etl_test.dim_site'))
    assert spark.table(table).count()==0,'Previous fixture requires investigation'
    def expect(name,fn):fn();tests.append(name);print('FIXTURE '+name,flush=True)
    now=datetime(2026,10,14);t0=datetime(2024,1,1);t1=datetime(2024,2,1);t2=datetime(2024,3,1)
    def event(t,label):
        payload=dict(source_system='hotel_ops',member_kind='NORMAL',site_id='ETL_FIXTURE_SITE',site_name=label,climate_region='TEST')
        return dict(effective_at=t,payload=payload,row_hash=payload_hash(payload,['site_name','climate_region']),
                    basis='SOURCE_EFFECTIVE',batch='ETL_FIXTURE',transform='f'*64)
    events=[event(t0,'A'),event(t1,'B'),event(t2,'A')]
    # A shared registry identity is independent of payload and ordinal.
    keys=[['TEST_D02','hotel_ops','ETL_FIXTURE_SITE',scalar(t)] for t in [t0,t1,t2,t0+timedelta(days=15)]]
    reg=pg.registry(keys);key_for=lambda t:reg[canonical(['TEST_D02','hotel_ops','ETL_FIXTURE_SITE',scalar(t)])]
    def roundtrip(rows):
        validate(spark,entity,rows,manifest['row_checks']['D02'])
        ora.execute("DELETE FROM CE_DWH_B.DIM_SITE WHERE source_batch_id='ETL_FIXTURE'")
        ora.write('CE_DWH_B.DIM_SITE',rows,[c['name'] for c in entity['columns']])
        frame(spark,entity,rows).writeTo(table).overwrite(F.lit(True))
        assert fingerprint(oracle_rows(spark,entity,'CE_DWH_B'),entity)==fingerprint(rows,entity)
        assert fingerprint([r.asDict() for r in spark.table(table).collect()],entity)==fingerprint(rows,entity)
    try:
        base=materialize(events[:1],[],key_for,'site_key',now)
        roundtrip(base);tests.append('bootstrap_both_engines')
        unchanged=materialize(events[:1]+[event(t1,'A')],base,key_for,'site_key',now+timedelta(days=1))
        assert unchanged==base;roundtrip(unchanged);tests.append('unchanged_payload_preserves_key_and_audit')
        changed=materialize(events[:2],base,key_for,'site_key',now+timedelta(days=1))
        assert [(r['valid_from_utc'],r['valid_to_utc'],r['site_name']) for r in changed]==[(t0,t1,'A'),(t1,None,'B')]
        roundtrip(changed);tests.append('changed_payload_closes_opens')
        aba=materialize(events,changed,key_for,'site_key',now+timedelta(days=2))
        assert len({r['site_key'] for r in aba})==3 and [r['site_name'] for r in aba]==['A','B','A']
        roundtrip(aba);tests.append('A_B_A_has_three_durable_keys')
        assert lookup(aba,t1)['site_name']=='B' and lookup(aba,t1-timedelta(microseconds=1))['site_name']=='A'
        tests.append('exclusive_end_exact_microsecond_boundary')
        late=event(t0+timedelta(days=15),'C')
        split=materialize(events+[late],aba,key_for,'site_key',now+timedelta(days=3))
        assert [r['site_name'] for r in split]==['A','C','B','A']
        assert split[2]['site_key']==aba[1]['site_key'] and split[2]['version_no']==3
        roundtrip(split);tests.append('late_event_split_preserves_future_keys_and_renumbers_ordinal')
        replay=materialize(events+[late,late],split,key_for,'site_key',now+timedelta(days=4))
        assert replay==split;roundtrip(replay);tests.append('event_replay_noop_both_engines')
        try:timeline(events+[event(t1,'CONFLICT')])
        except EffectiveConflict:tests.append('same_time_conflict_rejected')
        else:raise AssertionError('Conflict not rejected')
        try:lookup(aba,t0-timedelta(microseconds=1))
        except ValueError:tests.append('missing_history_lookup_rejected')
        else:raise AssertionError('Missing interval accepted')
        invalid=deepcopy(split);invalid[0]['valid_to_utc']=t2
        try:validate(spark,entity,invalid,manifest['row_checks']['D02'])
        except AssertionError:tests.append('overlap_rejected_before_both_writes')
        else:raise AssertionError('Overlap accepted')
        # Retain no-op input events so a later correction does not erase a known future observation.
        assert [r['payload']['site_name'] for r in timeline([event(t0,'A'),event(t2,'A'),event(t1,'B')])]==['A','B','A']
        tests.append('noop_event_retained_for_late_history_rebuild')
        assert parse('2024-01-01T00:00:00+07:00','TIMESTAMPTZ')==datetime(2023,12,31,17)
        tests.append('Vietnam_midnight_normalized_to_UTC')
        for value,typ in [('1.2504','NUMERIC(18,3)'),('1.5','INTEGER'),('2024-01-01T00:00:00','TIMESTAMPTZ')]:
            try:parse(value,typ)
            except ValueError:pass
            else:raise AssertionError('Lossy parse accepted')
        tests.append('fraction_precision_and_missing_timezone_rejected')
        # Registry race on two independent database connections.
        def race(_):
            conn=Jdbc(spark,'postgres')
            try:return conn.registry([['TEST_CONCURRENT','fixture','same_key']])
            finally:conn.close()
        with ThreadPoolExecutor(max_workers=2) as pool:answers=list(pool.map(race,[1,2]))
        assert answers[0]==answers[1];tests.append('concurrent_registry_allocation_same_key')
        # Credential really lacks registry mutation and Oracle DDL privileges.
        assert pg.query("SELECT has_table_privilege(current_user,'ce_control.key_registry','UPDATE')")[0][0]=='f'
        assert ora.query("SELECT count(*) FROM session_privs WHERE privilege IN ('CREATE TABLE','CREATE USER','ALTER ANY TABLE')")[0][0]=='0'
        tests.append('loader_privileges_restricted')
        # Run corrupted fixtures through the same input validation and actual targets.
        root=Path('/analytics/fixtures/dimension-quality');root.mkdir(parents=True,exist_ok=True)
        src_catalog=json.loads(Path('/workspace/lake/v2/catalog/catalog.json').read_text())
        ds=deepcopy(next(d for d in src_catalog['datasets'] if d['dataset_id']=='hotel_ops.sites'))
        p=root/'sites.csv'
        with p.open('w',encoding='utf-8',newline='') as f:
            writer=csv.writer(f);writer.writerow(['site_id','site_name','climate_region'])
            writer.writerows([['ETL_FIXTURE_SITE','Valid','TEST'],['BAD','\\N','TEST'],['DUP','one','TEST'],['DUP','two','TEST']])
        ds.update(relative_path='sites.csv',row_count=4,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        fullmap=json.loads(Path('/workspace/config/source_target_mapping_v1.json').read_text())
        mapping=dict(entities=[e for e in fullmap['entities'] if e['id']=='D02'],
                     source_validation_contracts=[s for s in fullmap['source_validation_contracts'] if s['source_table']=='hotel_ops.sites'])
        src,report=read_sources(spark,root,dict(datasets=[ds]),mapping)
        assert len(src['hotel_ops.sites'])==1 and len(report['quarantine'])==3 and report['source_status']['hotel_ops.sites']=='PARTIAL'
        partial=materialize([event(t0,'Valid')],[],key_for,'site_key',now)
        # Use the actual accepted source payload, not an unrelated hand-written expected row.
        partial[0]['site_name']=src['hotel_ops.sites'][0]['site_name'];partial[0]['row_hash']=payload_hash(partial[0],['site_name','climate_region'])
        roundtrip(partial)
        pg.execute("INSERT INTO ce_control.pipeline_run(run_id,source_batch_id,input_manifest_sha256,transform_version,started_at,state,oracle_slot) VALUES('fixture_dimension_partial','FIXTURE',?,?,?,'DIMENSIONS_READY','CE_DWH_B') ON CONFLICT(run_id) DO NOTHING",['f'*64,'f'*64,now])
        pg.execute("INSERT INTO ce_control.quality_entity VALUES('fixture_dimension_partial','D02','PARTIAL',1,3,0.25,?::jsonb) ON CONFLICT(run_id,entity_id) DO UPDATE SET detail=EXCLUDED.detail",[canonical(report)])
        # Fixture run is not a production candidate; keep evidence but mark closed.
        pg.execute("UPDATE ce_control.pipeline_run SET state='FAILED',evidence='{"+'"fixture_only":true,"intentional_close":true' +"}'::jsonb WHERE run_id='fixture_dimension_partial'")
        tests.append('PARTIAL_rejects_three_keeps_one_actual_engines_and_control')
        missing=deepcopy(ds);missing['relative_path']='missing.csv'
        _,missing_report=read_sources(spark,root,dict(datasets=[missing]),mapping)
        assert missing_report['source_status']['hotel_ops.sites']=='UNAVAILABLE'
        tests.append('missing_file_explicit_UNAVAILABLE')
        save(OUT/'fixture-quality.json',report)
    finally:
        ora.execute("DELETE FROM CE_DWH_B.DIM_SITE WHERE source_batch_id='ETL_FIXTURE'")
        spark.sql('DELETE FROM '+table)
        assert ora.query('SELECT count(*) FROM CE_DWH_B.DIM_SITE')[0][0]=='0'
        assert spark.table(table).count()==0
        ora.close();pg.close()
    save(OUT/'fixtures.json',dict(status='PASSED',tests=tests,count=len(tests),fixture_rows_removed=True,
        oracle_table='CE_DWH_B.DIM_SITE',iceberg_table=table,source_mutated=False,
        limits=['No full publication/coordinator crash test until facts and publication are implemented.']))
    print('FIXTURES_RESULT '+canonical(dict(status='PASSED',count=len(tests))),flush=True)
