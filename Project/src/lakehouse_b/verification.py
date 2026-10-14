from copy import deepcopy
from decimal import Decimal
from datetime import datetime,timedelta
import socket
from lakehouse_b.common import *
from lakehouse_b.publication import prepare,activate,validate_manifest
from semantic.main import cases
from semantic.reference import RawReference
from semantic.service import SemanticSession,decode,policy
from semantic.queries import build,COUNTS
from semantic.fixtures import data_cases,inline

def explore(spark,db):
    pointer=read(LAKE/'manifests/silver-active.json');assert sha(pointer['path'])==pointer['sha256']
    silver=read(pointer['path']);spec=silver['tables']['hotel_ops.bookings']
    pinned(spark,spec).createOrReplaceTempView('b_silver_booking_exploration')
    sql='SELECT status,COUNT(*) AS bookings FROM b_silver_booking_exploration GROUP BY status ORDER BY status'
    rows=[r.asDict() for r in spark.sql(sql).collect()]
    save(OUT/'silver-before-gold.json',{'status':'PASSED','checked_at':now(),'active_gold_publication':db.active(),'gold_report_exists':(OUT/'gold.json').exists(),'input_table':spec['table'],'input_snapshot':spec['snapshot_id'],'sql':sql,'rows':rows,'gold_tables_used':False})
    print('Silver exploration '+canonical(rows),flush=True)

def verify(spark,db):
    # No Oracle DNS or socket dependency; the runtime has its own Compose network.
    try:socket.getaddrinfo('oracle',1521)
    except socket.gaierror:oracle_unresolvable=True
    else:raise AssertionError('Oracle unexpectedly visible in B network')
    reference=RawReference(LAKE);reader=Reader(spark,db);session=SemanticSession(reader);reports={}
    try:
        assert reader.manifest['source_catalog_sha256']==sha(LAKE/'catalog/catalog.json')
        validate_manifest(spark,reader.manifest)
        for phase in ['baseline','slices']:
            historical=read(Path('/baseline/semantic')/(phase+'.json'))['checks'];checks=[]
            for label,group,ctx,metrics in cases(phase,reference):
                actual=session.query(group,ctx,'iceberg',metrics)['metrics'];expected=reference.compute(group,ctx)
                old=next(x for x in historical if x['case']==label and x['group']==group and x['context']==ctx)
                for mid,v in actual.items():
                    assert (v['diagnostic_accepted_numerator'],v['diagnostic_accepted_denominator'])==expected[mid],(label,mid,'raw mismatch')
                    h=old['oracle'][mid]
                    for field in ['value','numerator','denominator','diagnostic_accepted_numerator','diagnostic_accepted_denominator']:
                        wanted=None if h[field] is None else Decimal(str(h[field]))
                        assert v[field]==wanted,(label,mid,field,'historical Oracle mismatch',v[field],wanted)
                    assert v['quality']==h['quality'] and v['reasons']==h['reasons']
                checks.append({'case':label,'group':group,'context':ctx,'selected':list(actual),'iceberg':actual,'raw_reference_equal':True,'historical_oracle_equal':True})
                save(OUT/(phase+'-progress.json'),{'status':'RUNNING','publication_id':reader.pid,'completed':len(checks),'checks':checks})
                print('B KPI '+phase+' '+label+' '+group,flush=True)
            reports[phase]={'status':'PASSED','publication_id':reader.pid,'contexts':len(checks),'metric_comparisons':sum(len(c['selected']) for c in checks),'checks':checks}
            save(OUT/(phase+'.json'),reports[phase])
        # This SQL references only Silver; explore() separately records a pre-Gold run.
        silver=read(reader.manifest['silver_manifest']['path']);spec=silver['tables']['hotel_ops.bookings']
        pinned(spark,spec).createOrReplaceTempView('b_silver_booking_exploration')
        rows=[r.asDict() for r in spark.sql('SELECT status,COUNT(*) AS bookings FROM b_silver_booking_exploration GROUP BY status ORDER BY status').collect()]
        save(OUT/'silver-exploration.json',{'status':'PASSED','input_snapshot':spec['snapshot_id'],'table':spec['table'],'sql':'SELECT status, COUNT(*) AS bookings FROM Silver bookings GROUP BY status','rows':rows,'gold_tables_used':False})
        save(OUT/'verification.json',{'status':'PASSED','checked_at':now(),'publication_id':reader.pid,'source_batch_id':reader.manifest['source_batch_id'],'baseline_metrics':reports['baseline']['metric_comparisons'],'slice_metrics':reports['slices']['metric_comparisons'],'contexts':sum(v['contexts'] for v in reports.values()),'raw_reference_equal':True,'historical_oracle_equal':True,'oracle_hostname_unresolvable':oracle_unresolvable,'oracle_connections':0,'external_warnings':len(reader.manifest['external_warnings']),'gold_tables':len(reader.manifest['tables']),'gold_rows':sum(s['rows'] for s in reader.manifest['tables'].values()),'silver_tables':len(silver['tables']),'limitations':['Oracle comparison uses immutable previously certified results; no new Oracle query was executed.','Power BI and public web remain on their earlier certified publication until a separate UI migration is accepted.','No performance benchmark or distributed scale claim.']})
    finally:reader.close()

def fixtures(spark,db):
    manifest=read(OUT/'gold.json');entities={e['id']:e for e in read(CONFIG/'analytics/ddl/manifest.json')['entities']};checks=[]
    for name,g,ctx,data,expected in data_cases():
        sql,selected,ratios=build(g,ctx)
        result=decode([list(r) for r in spark.sql(inline(sql,data,entities,'iceberg')).collect()],selected,ratios,ctx,manifest)
        for mid,(n,d) in zip(selected,expected):assert (result[mid]['diagnostic_accepted_numerator'],result[mid]['diagnostic_accepted_denominator'])==(Decimal(n),Decimal(d)),name
        checks.append({'name':name,'metrics':len(selected)})
    policies=[]
    def expect(name,mid,ctx,m,status,reason):
        actual=policy(mid,ctx,m);assert actual[0]==status and reason in actual[1],name
        policies.append(name)
    expect('mixed_units','B06.01',{},manifest,'NOT_APPLICABLE','SELECT_ONE_ITEM_FOR_COMPATIBLE_QUANTITY')
    expect('mixed_inventory','B07.02',{},manifest,'NOT_APPLICABLE','SELECT_ONE_ITEM_FOR_COMPATIBLE_QUANTITY')
    expect('breakfast_not_lunch','B04.01',{'filters':{'meal':'LUNCH'}},manifest,'NOT_APPLICABLE','MEAL_OUTSIDE_METRIC_SCOPE')
    expect('no_bar_cost','B04.06',{'filters':{'meal':'BAR'}},manifest,'NOT_APPLICABLE','MEAL_OUTSIDE_METRIC_SCOPE')
    expect('out_of_coverage','B01.01',{'start':'2023-01-01'},manifest,'UNAVAILABLE','OUTSIDE_VERIFIED_V2_COVERAGE')
    partial=deepcopy(manifest);partial['quality_entities']['F04']['status']='PARTIAL'
    expect('partial_cross_sell','B03.02',{},partial,'PARTIAL','DEPENDENCY_QUALITY_PARTIAL_CONSERVATIVE_BATCH_SCOPE')
    missing=deepcopy(manifest);missing['quality_entities']['F17']['status']='UNAVAILABLE'
    expect('missing_weather','B05.03',{'filters':{'severe_weather':1}},missing,'UNAVAILABLE','DEPENDENCY_QUALITY_UNAVAILABLE_CONSERVATIVE_BATCH_SCOPE')
    broken=deepcopy(manifest);broken['quality_scope']=[{'entity':'F14','from_date':'2024-02-01'}]
    expect('negative_lot','B07.02',{'filters':{'item':'RICE'}},broken,'UNAVAILABLE','LOT_HISTORY_UNRELIABLE_CONSERVATIVE_SCOPE')
    assert policy('B07.01',{'start':'2024-02-01','filters':{'item':'RICE'}},broken)[0]=='COMPLETE';policies.append('opening_before_invalid_day')
    for name,g,ctx in [('channel_capacity','B01',{'filters':{'channel':'AGODA'}}),('usage_balance','B07',{'filters':{'usage_area':'BAR'}}),('asset_capacity','B08',{'filters':{'asset_type':'AC'}}),('date_order','B01',{'start':'2024-02-01','end':'2024-01-01'}),('sql_injection','B02',{'filters':{'channel':"x' OR 1=1--"}})]:
        try:build(g,ctx)
        except ValueError:policies.append(name)
        else:raise AssertionError(name)
    reader=Reader(spark,db)
    try:
        try:SemanticSession(reader).query('B02',{'filters':{'hotel':'NOT_A_HOTEL'}},'iceberg')
        except ValueError:policies.append('unknown_member')
        else:raise AssertionError('Unknown member accepted')
    finally:reader.close()
    # Isolated fault fixtures never alter the business pointer or business tables.
    fdb=Database(spark,'ce_b_fixture');prior=db.active();faults=[]
    import uuid
    token=uuid.uuid4().hex[:10];table='ce.b_fixture.pin_'+token
    a=put_table(spark,table,spark.createDataFrame([(1,10)],'id int, amount int'),['id','amount'])
    m=deepcopy(manifest);m['publication_id']='fixture_'+token+'_a';m['tables']={'F01':a}
    prepare(fdb,m);before=fdb.active()
    assert fdb.active()==before;faults.append('prepare_does_not_publish')
    activate(fdb,m['publication_id'],before);held=Reader(spark,fdb)
    try:
        from pyspark.sql import functions as F
        spark.createDataFrame([(1,20)],'id int, amount int').writeTo(table).overwrite(F.lit(True))
        b=dict(a,snapshot_id=snapshot(spark,table),content_sha256=row_hash([{'id':1,'amount':20}],['id','amount']))
        m2=deepcopy(m);m2['publication_id']='fixture_'+token+'_b';m2['tables']={'F01':b};m2['quality_entities']['F04']['status']='PARTIAL'
        prepare(fdb,m2)
        try:activate(fdb,m2['publication_id'],'wrong-expected-pointer')
        except ValueError:faults.append('stale_pointer_rejected')
        else:raise AssertionError('CAS accepted stale pointer')
        assert fdb.active()==m['publication_id'];activate(fdb,m2['publication_id'],m['publication_id'])
        assert held.query('SELECT amount FROM {F01}')['rows']==[[10]];faults.append('reader_remains_on_old_snapshot_after_publish')
        spark.sql('ALTER TABLE '+table+' ADD COLUMNS (new_vendor_field STRING)')
        assert 'new_vendor_field' in spark.table(table).columns
        assert held.query('SELECT amount FROM {F01}')['rows']==[[10]];faults.append('schema_addition_preserves_pinned_read')
        fresh=Reader(spark,fdb)
        try:
            assert fresh.query('SELECT amount FROM {F01}')['rows']==[[20]]
            assert policy('B03.02',{},fresh.manifest)[0]=='PARTIAL';faults.append('partial_publication_exposes_quality')
        finally:fresh.close()
        try:prepare(fdb,dict(m2,source_batch_id='tampered'))
        except AssertionError:faults.append('immutable_manifest_rejected')
        else:raise AssertionError('Manifest mutation accepted')
        fdb.execute("UPDATE ce_b.lease SET expires_at=clock_timestamp()-interval '1 second' WHERE token=?",[held.token])
        try:held.query('SELECT amount FROM {F01}')
        except AssertionError:faults.append('expired_reader_rejected')
        else:raise AssertionError('Expired reader accepted')
    finally:held.close();fdb.close()
    assert db.active()==prior;faults.append('business_publication_unchanged')
    # Shared SCD reducer: ordered/out-of-order/no-op/conflicting effective events.
    from analytics_runtime.scd2 import timeline,EffectiveConflict
    base=datetime(2024,1,1)
    events=[{'effective_at':base,'row_hash':'a'},{'effective_at':base+timedelta(days=2),'row_hash':'b'},{'effective_at':base+timedelta(days=1),'row_hash':'a'}]
    assert timeline(events)==timeline(list(reversed(events))) and len(timeline(events))==2;faults.append('scd2_out_of_order_and_noop')
    try:timeline(events+[{'effective_at':base,'row_hash':'conflict'}])
    except EffectiveConflict:faults.append('scd2_conflict_rejected')
    else:raise AssertionError('SCD conflict accepted')
    save(OUT/'fixtures.json',{'status':'PASSED','checked_at':now(),'sql_fixture_cases':len(checks),'metric_checks':sum(c['metrics'] for c in checks),'policy_checks':policies,'publication_and_scd_checks':faults,'checks':checks,'business_tables_mutated':False,'scope':'SQL/policy/SCD and isolated publication faults; actual crash-resume evidence recorded separately.'})
