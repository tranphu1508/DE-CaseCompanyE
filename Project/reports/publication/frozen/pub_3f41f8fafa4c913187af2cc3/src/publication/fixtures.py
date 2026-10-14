"""Failure/concurrency tests against actual PostgreSQL, Oracle and Iceberg.

Only ce_pub_test / CE_STAGE.PUB_PROBE_* / ce.publication_test are mutated.
Production candidate, source seed and source tables are never test fixtures.
"""
from pathlib import Path
from datetime import datetime
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json,time,uuid
from analytics_runtime.etl_io import Jdbc
from publication.core import Coordinator,Connection,Reader,canonical,digest,pin_tag,verify_pins,save

OUT=Path('/workspace/reports/publication')
def run(spark):
    co=Coordinator(spark,'ce_pub_test');writer=Jdbc(spark,'postgres');ora=Jdbc(spark,'oracle');seal=Connection(spark,'publisher','oracle');checks=[]
    fixture_epoch=uuid.uuid4().hex[:12]
    def passed(name):checks.append(name);print('PASS '+name,flush=True)
    def rejected(name,fn,reason):
        try:fn()
        except Exception as e:
            assert reason in str(e),name+': unexpected error '+str(e)[-700:];passed(name);return
        raise AssertionError('Expected rejection: '+name)
    def table(eid,slot,value,snapshot):
        kind='dim' if eid=='D01' else 'fact';name='pub_probe_'+kind
        return dict(name=name,mode='TABLE',oracle_object='CE_STAGE.PUB_PROBE_'+slot+'_'+kind.upper(),iceberg_table='ce.publication_test.'+name,rows=1,content_sha256=digest([[1,value]]),snapshot_id=snapshot)
    def snapshot(name,value):
        target='ce.publication_test.pub_probe_'+name
        spark.sql('CREATE NAMESPACE IF NOT EXISTS ce.publication_test')
        spark.sql('CREATE TABLE IF NOT EXISTS '+target+' (id bigint NOT NULL,v bigint NOT NULL) USING iceberg')
        spark.sql('INSERT OVERWRITE '+target+' VALUES (1,'+str(value)+')')
        native=spark._jvm.org.apache.iceberg.spark.Spark3Util.loadIcebergTable(spark._jsparkSession,target)
        return native.currentSnapshot().snapshotId()
    def make(slot,previous,value):
        pid='pub_fixture_'+slot.lower()+'_'+fixture_epoch;rid='fixture_'+slot.lower()
        writer.execute("INSERT INTO ce_pub_test.pipeline_run VALUES(?,?,?,?,?,'ETL_READY',?,NULL,'{}')",[rid,'fixture','0'*64,'0'*64,datetime.utcnow(),'CE_DWH_'+slot])
        gen=co.begin(pid,rid,'CE_DWH_'+slot,previous)
        for kind,v in [('dim',value),('fact',value*10)]:ora.execute('INSERT INTO CE_STAGE.PUB_PROBE_'+slot+'_'+kind.upper()+' VALUES(1,?)',[v])
        return dict(version='fixture-only',publication_id=pid,run_id=rid,oracle_slot='CE_DWH_'+slot,generation=gen,expected_active=previous,
                    tables={},helpers={},quality_metrics={'B01.01':dict(status='PARTIAL',reason='Intentional fixture missingness; do not replace with previous batch')},validation=dict(all_columns_equal=True,oracle_sealed=True,tags_pinned=True))
    try:
        assert co.active() is None
        rejected('no_publication_is_error_not_empty_report',lambda:Reader(spark,schema='ce_pub_test'),'NO_ACTIVE_PUBLICATION')
        a=make('A',None,1)
        a['tables']['D01']=table('D01','A',1,snapshot('dim',1))
        rejected('oracle_done_iceberg_incomplete_keeps_pointer',lambda:co.prepare(a),'INCOMPLETE_ENTITY_INVENTORY');assert co.active() is None
        a['tables']['F01']=table('F01','A',10,snapshot('fact',10))
        for t in a['tables'].values():pin_tag(spark,t['iceberg_table'],a['publication_id'],t['snapshot_id'])
        # A writer already in flight must finish before seal becomes durable.
        ora.conn.setAutoCommit(False)
        ora.execute('INSERT INTO CE_STAGE.PUB_PROBE_A_FACT VALUES(2,999)')
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending=pool.submit(seal.execute,'BEGIN ce_stage.seal_publication_slot(?,?); END;',['TEST_A',a['publication_id']])
            try:
                time.sleep(0.25);assert not pending.done(),'Seal did not wait for in-flight DML'
            finally:ora.conn.rollback();ora.conn.setAutoCommit(True)
            pending.result(timeout=10)
        passed('oracle_seal_waits_for_inflight_writer_transaction')
        bad=deepcopy(a);bad['generation']+=1
        rejected('stale_generation_is_fenced',lambda:co.prepare(bad),'FENCED_OR_WRONG_RUN')
        bad=deepcopy(a);bad['validation']['all_columns_equal']=False
        rejected('mismatched_targets_block_publication',lambda:co.prepare(bad),'TARGET_VALIDATION_MISSING')
        bad=deepcopy(a);bad['quality_metrics']={}
        rejected('missing_quality_blocks_publication',lambda:co.prepare(bad),'INCOMPLETE_KPI_QUALITY')
        co.prepare(a);assert co.active() is None;passed('prepared_is_not_visible')
        missing=deepcopy(a);missing['tables']['F01']['snapshot_id']+=1
        rejected('missing_snapshot_has_no_latest_fallback',lambda:verify_pins(spark,missing),'Lost publication snapshot/tag')
        missing=deepcopy(a);missing['helpers']={'test':dict(path='/analytics/publication-fixture-missing-helper',sha256={'required.parquet':'0'*64})}
        rejected('missing_helper_has_no_empty_fallback',lambda:verify_pins(spark,missing),'Missing or modified helper')
        bad=deepcopy(a);bad['tables']['F01']['rows']=2
        rejected('prepared_manifest_is_immutable',lambda:co.prepare(bad),'IMMUTABLE_MANIFEST_CONFLICT')
        # Simulate transaction abort after pointer write but before COMMIT.
        co.db.conn.setAutoCommit(False)
        try:
            co.publish(a,None)
            other=Coordinator(spark,'ce_pub_test')
            try:assert other.active() is None
            finally:other.close()
        finally:co.db.conn.rollback();co.db.conn.setAutoCommit(True)
        assert co.active() is None;passed('abort_before_commit_exposes_no_new_batch')
        co.publish(a,None);passed('partial_quality_can_publish_without_old_batch_fallback')
        # Lost acknowledgement: reconnect and retry the same identity.
        retry=Coordinator(spark,'ce_pub_test')
        try:assert retry.publish(a,None)['outcome']=='ALREADY_COMMITTED'
        finally:retry.close()
        passed('lost_acknowledgement_reconciles_without_duplicate')
        rejected('sealed_oracle_slot_blocks_stale_writer',lambda:ora.execute('INSERT INTO CE_STAGE.PUB_PROBE_A_FACT VALUES(2,999)'),'PUBLICATION_SLOT_SEALED')
        reader=Reader(spark,'old-publication-reader',ttl=300,schema='ce_pub_test')
        def pair(r,engine):return [int(v) for v in r.query('SELECT d.v,f.v FROM {D01} d JOIN {F01} f ON d.id=f.id',engine)['rows'][0]]
        assert pair(reader,'oracle')==pair(reader,'iceberg')==[1,10]
        b=make('B',a['publication_id'],2)
        b['tables']['D01']=table('D01','B',2,snapshot('dim',2))
        # An unpinned latest query is already mixed; the reader must stay old.
        latest=spark.sql('SELECT d.v,f.v FROM ce.publication_test.pub_probe_dim d JOIN ce.publication_test.pub_probe_fact f ON d.id=f.id').first()
        assert list(latest)==[2,10] and pair(reader,'iceberg')==[1,10]
        passed('pinned_reader_avoids_actual_mixed_latest_tables')
        rejected('second_branch_incomplete_keeps_old_publication',lambda:co.prepare(b),'INCOMPLETE_ENTITY_INVENTORY');assert co.active()==a['publication_id']
        b['tables']['F01']=table('F01','B',20,snapshot('fact',20))
        for t in b['tables'].values():pin_tag(spark,t['iceberg_table'],b['publication_id'],t['snapshot_id'])
        seal.execute('BEGIN ce_stage.seal_publication_slot(?,?); END;',['TEST_B',b['publication_id']])
        co.prepare(b)
        rejected('compare_and_set_rejects_wrong_previous',lambda:co.publish(b,None),'STALE_ACTIVE')
        # Two concurrent publishers, one durable transition, one idempotent retry.
        def race():
            c=Coordinator(spark,'ce_pub_test')
            try:return c.publish(b,a['publication_id'])['outcome']
            finally:c.close()
        with ThreadPoolExecutor(max_workers=2) as pool:outcomes=sorted(pool.map(lambda _:race(),range(2)))
        assert outcomes==['ALREADY_COMMITTED','COMMITTED'];passed('concurrent_publishers_commit_once')
        assert pair(reader,'oracle')==pair(reader,'iceberg')==[1,10];passed('existing_reader_stays_on_old_publication')
        with Reader(spark,'new-reader',schema='ce_pub_test') as new:
            assert pair(new,'oracle')==pair(new,'iceberg')==[2,20]
            assert new.manifest['quality_metrics']['B01.01']['status']=='PARTIAL'
        passed('new_reader_sees_complete_new_pair_and_quality')
        with Reader(spark,'slow-result-reader',schema='ce_pub_test') as slow:
            slow.ttl=1;original=slow.ora.query
            def delayed(sql,params=()):
                rows=original(sql,params);time.sleep(1.2);return rows
            slow.ora.query=delayed
            rejected('expired_long_query_result_is_discarded',lambda:slow.query('SELECT COUNT(*) FROM {F01}','oracle'),'LEASE_EXPIRED_OR_RELEASED')
        writer.execute("INSERT INTO ce_pub_test.pipeline_run VALUES('fixture_c','fixture',?,?,?,'ETL_READY','CE_DWH_A',NULL,'{}')",['0'*64,'0'*64,datetime.utcnow()])
        rejected('live_reader_prevents_slot_reservation',lambda:co.begin('pub_fixture_c','fixture_c','CE_DWH_A',b['publication_id']),'SLOT_HAS_LIVE_READER')
        reader.close()
        rejected('retained_publication_is_not_recycled_after_release',lambda:co.begin('pub_fixture_c','fixture_c','CE_DWH_A',b['publication_id']),'SLOT_RETAINED_NO_AUTOMATIC_REUSE')
        assert co.publish(a,None)['outcome']=='ALREADY_COMMITTED' and co.active()==b['publication_id'];passed('late_retry_never_rewinds_active_pointer')
        # TTL test via DB clock: bypass constructor work to avoid timing flakiness.
        lease=Connection(spark,'reader');lid=str(uuid.uuid4())
        try:
            lease.query('SELECT ce_pub_test.acquire_reader(?,?,?)',[lid,'expiry-probe',1]);time.sleep(1.2)
            rejected('expired_lease_cannot_renew',lambda:lease.query('SELECT ce_pub_test.renew_reader(?,?,?)',[lid,b['publication_id'],300]),'LEASE_EXPIRED_OR_RELEASED')
            rejected('expired_lease_cannot_release_results',lambda:lease.query('SELECT ce_pub_test.assert_reader(?,?)',[lid,b['publication_id']]),'LEASE_EXPIRED_OR_RELEASED')
            lease.query('SELECT ce_pub_test.release_reader(?,?)',[lid,b['publication_id']])
            rejected('reader_cannot_change_active_pointer',lambda:lease.execute("UPDATE ce_pub_test.active_publication SET publication_id='x'"),'permission denied')
        finally:lease.close()
        rejected('publisher_cannot_bypass_atomic_api',lambda:co.db.execute("UPDATE ce_pub_test.active_publication SET publication_id='x'"),'permission denied')
        assert co.db.query("SELECT count(*) FROM ce_pub_test.publication_event WHERE action='PUBLISHED'")[0][0]=='2'
        assert co.db.query('SELECT count(*) FROM ce_pub_test.reader_lease WHERE expires_at>clock_timestamp()')[0][0]=='0'
        # Production is untouched by all test publishes.
        prod=Coordinator(spark)
        try:assert prod.active() is None
        finally:prod.close()
        save(OUT/'fixtures.json',dict(status='PASSED',count=len(checks),checks=checks,scope='ce_pub_test + CE_STAGE.PUB_PROBE_* + ce.publication_test',fixture_publications=[a,b],production_publication_unchanged=True,live_readers=0,limits='Controlled rollback/disconnection boundaries, not a host power-loss durability test.'))
        print('PASSED '+str(len(checks))+' publication fixtures',flush=True)
    finally:co.close();writer.close();ora.close();seal.close()
