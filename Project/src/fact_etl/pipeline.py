"""Initial, unpublished ETL candidate; atomic Oracle table inserts and Iceberg appends.

Canonical Parquet is frozen before loading either target. A retry may fill an
empty target or verify an identical one; it cannot overwrite business data.
Oracle partition writes land in disposable stage tables, then INSERT SELECT is
committed once. No distributed atomic publication is claimed by this stage.
"""
import argparse,hashlib,json,time,shutil
from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal
from collections import defaultdict,Counter
from pyspark.sql import functions as F
from analytics_runtime.session import create_session,secret
from analytics_runtime.etl_io import Jdbc,frame,oracle_rows
from analytics_runtime.dimension_transform import read_sources
from analytics_runtime.scd2 import canonical,scalar
from fact_etl.transform import Transformer,AUDIT

ROOT=Path('/workspace');OUT=ROOT/'reports/fact-etl';OUT.mkdir(exist_ok=True)
ORDER=['L04','L03','F01','F08','F10','F11','F12','F16','F17','L02','F02','F04','F05','F07','F09','F13','L01','F03','F14','F06']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=scalar)+'\n',encoding='utf8')
def read(p):return json.loads(p.read_text(encoding='utf8'))
def fingerprint(rows,e):
    return hashlib.sha256('\n'.join(canonical([r[c['name']] for c in e['columns']]) for r in sorted(rows,key=lambda r:tuple(r[c] for c in e['primary_key']))).encode()).hexdigest()

def validate(spark,e,rows,manifest,dimensions,transform):
    bad=[];kept=[]
    for r in rows:
        reasons=[]
        for c in e['columns']:
            v=r.get(c['name'])
            if v is None and not c['nullable']:reasons.append('NULL:'+c['name'])
            if c.get('references'):
                parent,col=c['references'].split('.')
                if parent.startswith('D') and v not in transform.by_sk[parent]:reasons.append('FK:'+c['name'])
        if reasons:transform.exclude(e['id'],[r[c] for c in e['unique_keys'][0]],';'.join(reasons))
        else:kept.append(r)
    if not kept:return []
    df=frame(spark,e,kept)
    predicates=manifest['row_checks'].get(e['id'],[])
    bad_expr=F.lit(False)
    for c in predicates:bad_expr=bad_expr|(~F.coalesce(F.expr(c['spark']),F.lit(True)))
    # Run the complete physical CHECK contract with ANSI decimal semantics.
    invalid=df.filter(bad_expr).collect()
    rejected={r[e['primary_key'][0]] for r in invalid} if len(e['primary_key'])==1 else {tuple(r[c] for c in e['primary_key']) for r in invalid}
    for r in invalid:transform.exclude(e['id'],[r[c] for c in e['unique_keys'][0]],'TARGET_CHECK')
    return [r for r in kept if (r[e['primary_key'][0]] if len(e['primary_key'])==1 else tuple(r[c] for c in e['primary_key'])) not in rejected]

def enrich(e,rows,transform,pg,batch,version,now):
    keys=[[e['id']]+[r[c] for c in e['unique_keys'][0]] for r in rows] if e['id'].startswith('F') else []
    registry=pg.registry(keys) if keys else {}
    for i,r in enumerate(rows):
        if keys:r['fact_key']=registry[canonical(keys[i])]
        for c in e['columns']:
            name=c['name'];typ=c['spark_sql_type']
            if name in r and r[name] is not None and typ.startswith('DECIMAL'):
                scale=int(typ.split(',')[1].rstrip(')'))
                value=Decimal(r[name]);quantized=value.quantize(Decimal(1).scaleb(-scale))
                assert value==quantized,'Unapproved numeric rounding: '+e['id']+'.'+name
                r[name]=quantized
        payload=[]
        for c in e['columns']:
            name=c['name']
            if name in AUDIT or name=='fact_key':continue
            v=r[name]
            # Canonical business payload uses durable identities, not allocated SK.
            if c.get('references'):
                dim,_=c['references'].split('.')
                if dim.startswith('D'):
                    parent=transform.by_sk[dim].get(v)
                    if parent is not None:
                        if parent['member_kind']!='NORMAL':v=[dim,parent['member_kind']]
                        elif dim=='D01':v=['calendar',parent['calendar_date']]
                        elif dim=='D10':v=['reference',parent['meal_code']]
                        else:v=[parent[k] for k in transform.design[dim]['business_key']]
            payload.append(v)
        r.update(source_batch_id=batch,transform_version=version,row_hash=hashlib.sha256(canonical(payload).encode()).hexdigest(),created_at_utc=now,updated_at_utc=now)
    return registry

def reconciliation(t):
    paid=Counter();included=Counter()
    for r in t.out['F07']:paid[(r['outlet_key'],r['service_date_key'],r['meal_key'])]+=r['covers']
    for r in t.out['F06']:included[(r['outlet_key'],r['service_date_key'],r['meal_key'])]+=r['redeemed_covers']
    meals=[]
    for r in t.out['F08']:
        k=(r['outlet_key'],r['service_date_key'],r['meal_key']);expected=paid[k]+included[k]
        if r['actual_covers']!=expected:meals.append(dict(session_id=r['session_id'],actual=r['actual_covers'],expected=expected))
    lotdays=defaultdict(lambda:defaultdict(Decimal))
    for r in t.out['F14']:lotdays[r['receipt_id']][r['movement_date_key']]+=r['signed_qty']
    negatives=[]
    for lot,events in lotdays.items():
        total=Decimal(0)
        for d,qty in sorted(events.items()):
            total+=qty
            if total<0:negatives.append(dict(receipt_id=lot,from_date=d,closing_qty=total));break
    return dict(meal_session_mismatches=meals,negative_lot_prefixes=negatives,
                stock_policy='Balance is unavailable from an invalid/missing movement; retained transaction facts do not certify complete balances.')

def external_reconcile(spark,mapping,t):
    inputs={};records={}
    for ds in mapping['external_reconciliation_inputs']:
        path=Path(ds['standardized_path']);files={str(p.relative_to(path)):sha(p) for p in sorted(path.rglob('*')) if p.is_file()}
        if not files:inputs[ds['dataset_id']]=dict(status='MISSING',coverage=None);continue
        df=spark.read.parquet(str(path));rows=[r.asDict(recursive=True) for r in df.collect()]
        assert len(rows)==ds['row_count'],'External standardized row count drift'
        records[ds['dataset_id'].rsplit('.',1)[-1]]=rows
        inputs[ds['dataset_id']]=dict(rows=len(rows),sha256=files,columns=df.columns)
    # Exact feed field comparisons are supplied by the standardized schema.
    mismatches=[];newest_invalid=[]
    latest={r['receipt_ref']:r for r in records.get('receipt_latest',[])}
    versions=defaultdict(list)
    for r in records.get('receipt_versions',[]):versions[r['receipt_ref']].append(r)
    for ref,group in versions.items():
        assert latest[ref]['revision']==max(r['revision'] for r in group),'Latest feed chosen by arrival instead of revision'
    for r in records.get('receipt_quarantine',[]):
        revision=r.get('revision');old=latest.get(r.get('receipt_ref'))
        if old is None or revision is None or revision>=old['revision']:
            newest_invalid.append(dict(receipt_ref=r.get('receipt_ref'),revision=revision,reason=r.get('quality_reason'),older_valid_revision=None if old is None else old['revision']))
    for r in records.get('receipt_latest',[]):
        ref=r.get('receipt_ref');db=t.index[ 'hotel_ops.receipts'].get(ref)
        reasons=[]
        if db is None:reasons.append('RECEIPT_NOT_IN_DB')
        else:
            line=t.index['hotel_ops.purchase_lines'][db['purchase_line_id']];po=t.index['hotel_ops.purchase_orders'][line['purchase_order_id']]
            for field,expected in [('purchase_line_ref',db['purchase_line_id']),('supplier_id',po['supplier_id']),('hotel_id',po['hotel_id']),('accepted_qty_kg',db['accepted_qty']),('unit_price_vnd',line['unit_price_vnd'])]:
                if field not in r:reasons.append('FEED_FIELD_UNAVAILABLE:'+field)
                elif r[field]!=expected:reasons.append('MISMATCH:'+field)
        if reasons:mismatches.append(dict(receipt_ref=ref,reasons=reasons))
    return dict(inputs=inputs,mismatches=mismatches,newest_invalid=newest_invalid,policy='DB receipts alone feed F13; external latest/revisions/replays/quarantine remain reconciliation evidence, never additive facts. A bad newest revision does not certify the older valid one as complete.')

def load(spark,ora,e,path,rows,write):
    name=e['physical_name'];expected=fingerprint(rows,e);helper=e['kind']=='VALIDATION_VIEW'
    target='CE_STAGE.'+name+'_input_a' if helper else 'CE_DWH_A.'+name
    stage='CE_STAGE.ETL_'+e['id'];count=int(ora.query('SELECT COUNT(*) FROM '+target)[0][0]);started=time.monotonic()
    if count==0 and rows and write:
        ora.execute('DELETE FROM '+stage) # Isolated disposable stage only, under coordinator lock.
        df=spark.read.parquet(str(path))
        # Spark 3.5 JDBC maps TimestampType; the session is pinned to UTC.
        for c in e['columns']:
            if c['spark_sql_type']=='TIMESTAMP_NTZ':df=df.withColumn(c['name'],F.col(c['name']).cast('timestamp'))
        (df.coalesce(2).write.format('jdbc').option('url','jdbc:oracle:thin:@//oracle:1521/FREEPDB1')
         .option('driver','oracle.jdbc.OracleDriver').option('user','CE_LOADER').option('password',secret('CE_ORACLE_LOADER_PASSWORD_FILE'))
         .option('dbtable',stage).option('batchsize','2000').mode('append').save())
        cols=','.join(c['name'] for c in e['columns'])
        assert int(ora.query('SELECT COUNT(*) FROM '+stage)[0][0])==len(rows)
        # Oracle constraints and one INSERT SELECT transaction prevent partial A-table writes.
        ora.execute('INSERT INTO '+target+' ('+cols+') SELECT '+cols+' FROM '+stage)
    actual=oracle_rows(spark,e)
    assert fingerprint(actual,e)==expected,'Oracle full content mismatch '+e['id']
    oracle_seconds=time.monotonic()-started;started=time.monotonic();snapshot=None
    if helper:
        spark.read.parquet(str(path)).createOrReplaceTempView(name)
        ice=[r.asDict() for r in spark.table(name).collect()]
    else:
        table='ce.gold.'+name;old=spark.table(table).count()
        if old==0 and rows and write:spark.read.parquet(str(path)).writeTo(table).append()
        ice=[r.asDict() for r in spark.table(table).collect()]
        native=spark._jvm.org.apache.iceberg.spark.Spark3Util.loadIcebergTable(spark._jsparkSession,table)
        if native.currentSnapshot() is not None:snapshot=native.currentSnapshot().snapshotId()
    assert fingerprint(ice,e)==expected,'Iceberg/helper full content mismatch '+e['id']
    return dict(entity=e['id'],table=name,rows=len(rows),content_sha256=expected,oracle_rows=len(actual),iceberg_rows=len(ice),iceberg_snapshot_id=snapshot,oracle_seconds=oracle_seconds,iceberg_seconds=time.monotonic()-started)

def run(spark,phase):
    inputs={p:sha(ROOT/p) for p in ['config/warehouse_design_v1.json','config/source_target_mapping_v1.json','config/analytics/ddl/manifest.json','config/physical_design_v1.json','config/logical_model_v1_1.json','config/kpi_contract_v1.json','lake/v2/catalog/catalog.json','reports/dimension-etl/verification.json']}
    codes={str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'src/fact_etl').glob('*.py'))}
    for p in (ROOT/'src/analytics_runtime').glob('*.py'):codes[str(p.relative_to(ROOT))]=sha(p)
    version=hashlib.sha256(canonical([codes,inputs]).encode()).hexdigest();catalog=read(ROOT/'lake/v2/catalog/catalog.json')
    run_id='facts_'+catalog['batch_id']+'_'+version[:12];folder=Path('/analytics/canonical')/run_id
    manifest=read(ROOT/'config/analytics/ddl/manifest.json');mapping=read(ROOT/'config/source_target_mapping_v1.json');design=read(ROOT/'config/warehouse_design_v1.json')
    entities={e['id']:e for e in manifest['entities']};pg=Jdbc(spark,'postgres');ora=Jdbc(spark,'oracle');registered=False
    try:
        assert pg.query('SELECT pg_try_advisory_lock(5173,1)')[0][0]=='t','Another ETL coordinator is running'
        assert pg.query('SELECT count(*) FROM ce_control.active_publication')[0][0]=='0','Initial candidate loader cannot modify a publication'
        assert pg.query('SELECT count(*) FROM ce_control.reader_lease WHERE expires_at>now()')[0][0]=='0'
        # Every catalog-pinned file is checked, including external raw evidence.
        for ds in catalog['datasets']:
            p=ROOT/'lake/v2'/ds['relative_path']
            if p.exists():assert sha(p)==ds['sha256'],'Raw input changed: '+ds['dataset_id']
        frozen=folder/'manifest.json'
        if not frozen.exists():
            assert phase=='run','No canonical fact candidate for this exact code/configuration'
            # Do not generate a new candidate on top of an already populated different one.
            for eid in ORDER:
                e=entities[eid];assert ora.query('SELECT COUNT(*) FROM CE_DWH_A.'+e['physical_name'])[0][0]=='0','Existing target candidate differs; explicit reconciliation required'
            folder.mkdir(parents=True,exist_ok=True);now=datetime.now(timezone.utc).replace(tzinfo=None)
            dimension_report=read(ROOT/'reports/dimension-etl/run.json');dimfolder=Path(dimension_report['canonical_path'])
            dimensions={eid:[r.asDict() for r in spark.read.parquet(str(dimfolder/e['physical_name'])).collect()] for eid,e in entities.items() if eid.startswith('D')}
            print('Validating all 41 source tables against source CHECK/PK/UK/FK contracts',flush=True)
            allmapping=dict(mapping,entities=[dict(id='D_ALL',aliases={str(i):d['dataset_id'] for i,d in enumerate(catalog['datasets']) if 'columns' in d})])
            sources,sq=read_sources(spark,ROOT/'lake/v2',catalog,allmapping)
            sq['accounting']={}
            for ds in catalog['datasets']:
                if 'columns' not in ds:continue
                name=ds['dataset_id'];bad=[q for q in sq['quarantine'] if q['source']==name]
                accepted=len(sources.get(name,[]));direct=sum(q['code']!='DEPENDENCY_EXCLUDED' for q in bad);dependency=len(bad)-direct
                missing=sq['source_status'].get(name)=='UNAVAILABLE'
                if not missing:assert accepted+direct+dependency==ds['row_count'],'Source records are not partitioned once: '+name
                sq['accounting'][name]=dict(expected=ds['row_count'],accepted=accepted,direct_quarantine=direct,dependency_excluded=dependency,coverage=None if missing else accepted/ds['row_count'] if ds['row_count'] else 1)
            save(folder/'source-quality.json',sq)
            t=Transformer(sources,dimensions,design,mapping,sq);registry={};quality={};tables=[]
            for eid in ORDER:
                e=entities[eid];begin=time.monotonic();print('Transform '+eid+' '+e['physical_name'],flush=True)
                rows=t.build(eid);registry.update(enrich(e,rows,t,pg,catalog['batch_id'],version,now))
                rows=validate(spark,e,rows,manifest,dimensions,t);t.accept(eid,rows)
                path=folder/e['physical_name'];frame(spark,e,rows).coalesce(2).write.mode('overwrite').parquet(str(path))
                bad=[q for q in t.bad if q['entity']==eid];source_tables=sorted(set(t.mapping[eid]['aliases'].values()))
                flags=[sq['source_status'].get(n,'UNAVAILABLE') for n in source_tables]
                parent_flags=[quality[p]['status'] for p in t.mapping[eid]['depends_on'] if p in quality]
                status='COMPLETE' if not bad and all(f=='COMPLETE' for f in flags+parent_flags) else 'PARTIAL' if rows else 'UNAVAILABLE'
                quality[eid]=dict(status=status,accepted=len(rows),rejected=len(bad),business_filtered=t.filtered[eid],coverage=(len(rows)/(len(rows)+len(bad)) if rows or bad else None) if all(f=='COMPLETE' for f in flags+parent_flags) else None,source_tables=source_tables,unit='target grain; source record accounting is separate')
                tables.append(dict(entity=eid,rows=len(rows),content_sha256=fingerprint(rows,e),transform_seconds=time.monotonic()-begin))
                print('Accepted '+eid+': '+str(len(rows))+'; rejected: '+str(len(bad)),flush=True)
            recon=reconciliation(t);external=external_reconcile(spark,mapping,t)
            save(folder/'scope-quality.json',t.scope)
            for eid,reason in [('F08','meal_session_mismatches'),('F14','negative_lot_prefixes')]:
                if recon[reason]:quality[eid]['status']='PARTIAL';quality[eid]['coverage']=None;quality[eid]['reconciliation_warning']=reason
            save(folder/'quarantine.json',t.bad);save(folder/'reconciliation.json',recon);save(folder/'external-reconciliation.json',external)
            save(folder/'registry.json',[[json.loads(k),v] for k,v in sorted(registry.items())])
            metrics={}
            for metric in mapping['metric_mapping']:
                deps=metric['primary_facts']+metric['supporting_facts'];flags=[quality[d]['status'] for d in deps if d in quality]
                status='UNAVAILABLE' if 'UNAVAILABLE' in flags else 'PARTIAL' if 'PARTIAL' in flags else 'COMPLETE'
                metrics[metric['id']]=dict(status=status,dependencies=deps,reason='Input readiness only; query/filter coverage must be propagated by the semantic layer. Weather-filtered requests additionally depend on F17.')
            save(folder/'metric-readiness.json',metrics)
            frozen_data=dict(run_id=run_id,started_at=now,source_batch_id=catalog['batch_id'],transform_version=version,input_sha256=inputs,code_sha256=codes,dimension_run_id=dimension_report['run_id'],quality=quality,tables=tables,optional_disabled=['F15'],files={str(p.relative_to(folder)):sha(p) for p in sorted(folder.rglob('*')) if p.is_file()})
            save(frozen,frozen_data);del t,sources,dimensions,registry
        frozen_data=read(frozen)
        assert frozen_data['input_sha256']==inputs and frozen_data['code_sha256']==codes
        for rel,digest in frozen_data['files'].items():assert sha(folder/rel)==digest,'Canonical changed: '+rel
        # Recheck source hashes after transformations too; no mutable input window.
        for ds in catalog['datasets']:
            p=ROOT/'lake/v2'/ds['relative_path']
            if p.exists():assert sha(p)==ds['sha256'],'Source changed during ETL'
        for ds in mapping['external_reconciliation_inputs']:
            path=Path(ds['standardized_path']);external=read(folder/'external-reconciliation.json')['inputs'][ds['dataset_id']]
            if 'sha256' in external:
                assert {str(p.relative_to(path)):sha(p) for p in sorted(path.rglob('*')) if p.is_file()}==external['sha256'],'Standardized feed changed'
        pg.execute("INSERT INTO ce_control.pipeline_run(run_id,source_batch_id,input_manifest_sha256,transform_version,started_at,state,oracle_slot) VALUES(?,?,?,?,?,'RUNNING','CE_DWH_A') ON CONFLICT(run_id) DO NOTHING",[run_id,catalog['batch_id'],inputs['lake/v2/catalog/catalog.json'],version,datetime.fromisoformat(frozen_data['started_at'].rstrip('Z'))])
        registered=True;tables=[]
        for metric,q in read(folder/'metric-readiness.json').items():
            pg.execute('INSERT INTO ce_control.quality_metric VALUES(?,?,?,?::jsonb) ON CONFLICT(run_id,metric_id) DO UPDATE SET status=excluded.status,reason=excluded.reason',[run_id,metric,q['status'],canonical(q)])
        for eid in ORDER:
            e=entities[eid];path=folder/e['physical_name'];rows=[r.asDict() for r in spark.read.parquet(str(path)).collect()]
            print('Load/compare '+eid+' '+str(len(rows)),flush=True)
            tables.append(load(spark,ora,e,path,rows,phase=='run'))
            q=frozen_data['quality'][eid]
            pg.execute('INSERT INTO ce_control.quality_entity VALUES(?,?,?,?,?,?,?::jsonb) ON CONFLICT(run_id,entity_id) DO UPDATE SET status=excluded.status,accepted=excluded.accepted,rejected=excluded.rejected,coverage=excluded.coverage,detail=excluded.detail',[run_id,eid,q['status'],q['accepted'],q['rejected'],None if q['coverage'] is None else Decimal(str(q['coverage'])),canonical(q)])
        result=dict(status='PASSED_FACT_ETL',run_id=run_id,canonical_path=str(folder),canonical_manifest_sha256=sha(frozen),input_sha256=inputs,code_sha256=codes,quality=frozen_data['quality'],tables=tables,published=False,optional_disabled=['F15'])
        first=OUT/'first-load.json'
        if first.exists():
            original=read(first)
            def stable(r):return [{k:v for k,v in t.items() if not k.endswith('_seconds')} for t in r['tables']]
            assert original['run_id']==run_id and stable(original)==stable(result),'Replay changed rows/content/snapshot'
            result['replay_unchanged']=True
        elif phase=='run':save(first,result)
        else:raise ValueError('First-load evidence missing')
        save(OUT/(phase+'.json'),result)
        pg.execute("UPDATE ce_control.pipeline_run SET state='ETL_READY',finished_at=now(),evidence=?::jsonb WHERE run_id=?",[canonical(dict(report=str(OUT/(phase+'.json')),published=False)),run_id])
        print(json.dumps(dict(status=result['status'],run_id=run_id,rows=sum(t['rows'] for t in tables),published=False)),flush=True)
    except Exception as error:
        if registered:pg.execute("UPDATE ce_control.pipeline_run SET state='FAILED',finished_at=now() WHERE run_id=?",[run_id])
        raise
    finally:
        pg.query('SELECT pg_advisory_unlock(5173,1)');pg.close();ora.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['run','verify']);args=parser.parse_args()
    spark=create_session('CompanyE-fact-etl')
    try:run(spark,args.phase)
    finally:spark.stop()
