"""Initial dimension candidate and read-only replay verification on both engines.

Production updates are deliberately gated until fact rekey/publication is built.
The same SCD reducer is exercised against real isolated target fixtures.
"""
from pathlib import Path
from collections import defaultdict
from datetime import datetime,timezone
from decimal import Decimal
import argparse,hashlib,json,sys
from pyspark.sql import functions as F
from analytics_runtime.session import create_session
from analytics_runtime.scd2 import canonical,payload_hash,materialize,scalar
from analytics_runtime.etl_io import Jdbc,frame,oracle_rows,fingerprint
from analytics_runtime.dimension_transform import BOOTSTRAP,read_sources,dimension_inputs

ROOT=Path('/workspace');OUT=ROOT/'reports/dimension-etl';OUT.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=scalar)+'\n',encoding='utf-8')

def validate(spark,entity,rows,checks):
    pk=entity['primary_key'][0]
    assert len({r[pk] for r in rows})==len(rows),'Duplicate SK'
    for cols in entity['unique_keys']:
        values=[tuple(r[c] for c in cols) for r in rows if r['member_kind']=='NORMAL' and all(r[c] is not None for c in cols)]
        assert len(values)==len(set(values)),'Duplicate natural key'
    if entity['history_policy']=='SCD_TYPE2':
        groups=defaultdict(list)
        for r in rows:
            if r['member_kind']=='NORMAL':groups[tuple(r[c] for c in entity['conditional_unique_keys'][0]['columns'])].append(r)
        for group in groups.values():
            group.sort(key=lambda r:r['valid_from_utc'])
            assert sum(r['is_current'] for r in group)==1
            for i,r in enumerate(group):
                assert r['version_no']==i+1
                if i+1<len(group):assert r['valid_to_utc']==group[i+1]['valid_from_utc']
                else:assert r['valid_to_utc'] is None
    df=frame(spark,entity,rows)
    predicates=[F.sum(F.when(~F.coalesce(F.expr(c['spark']),F.lit(True)),1).otherwise(0)).alias(c['name']) for c in checks]
    failures=df.agg(*predicates).first().asDict()
    assert not any(failures.values()),'Row predicates failed: '+str({k:v for k,v in failures.items() if v})
    return df

def load_or_compare(spark,ora,entity,rows,write):
    name=entity['physical_name'];table='ce.gold.'+name;expected=fingerprint(rows,entity)
    before=int(ora.query('SELECT COUNT(*) FROM CE_DWH_A.'+name)[0][0])
    if not before and write:ora.write('CE_DWH_A.'+name,rows,[c['name'] for c in entity['columns']])
    actual=oracle_rows(spark,entity)
    assert fingerprint(actual,entity)==expected,'Oracle content mismatch: '+name
    current=spark.table(table).count()
    if not current and write:frame(spark,entity,rows).writeTo(table).append()
    ice=[r.asDict() for r in spark.table(table).collect()]
    assert fingerprint(ice,entity)==expected,'Iceberg content mismatch: '+name
    snapshots=spark.sql('SELECT snapshot_id FROM '+table+'.snapshots ORDER BY committed_at DESC').collect()
    native=spark._jvm.org.apache.iceberg.spark.Spark3Util.loadIcebergTable(spark._jsparkSession,table)
    return dict(entity=entity['id'],table=name,rows=len(rows),normal=sum(r['member_kind']=='NORMAL' for r in rows),
                specials=sum(r['member_kind']!='NORMAL' for r in rows),content_sha256=expected,
                oracle_rows=len(actual),iceberg_rows=len(ice),iceberg_snapshot_id=native.currentSnapshot().snapshotId(),
                iceberg_snapshot_count=len(snapshots))

def run(spark,phase):
    files=['config/warehouse_design_v1.json','config/source_target_mapping_v1.json','config/analytics/ddl/manifest.json',
           'config/physical_design_v1.json','config/logical_model_v1_1.json','config/kpi_contract_v1.json','lake/v2/catalog/catalog.json']
    inputs={p:sha(ROOT/p) for p in files}
    codefiles=sorted((ROOT/'src/analytics_runtime').glob('*.py'))
    code={p.name:sha(p) for p in codefiles}
    version=hashlib.sha256(canonical([code,inputs]).encode()).hexdigest()
    execution_code=dict(code);compatibility=None
    compatibility_path=ROOT/'config/analytics/dimension_replay_compatibility_v1.json'
    if compatibility_path.exists():
        candidate=json.loads(compatibility_path.read_text())
        if candidate['execution_code_sha256']==code and candidate['input_sha256']==inputs:
            # Exact before/after hashes pin a reviewed compatibility repair.
            # No reallocation or rewrite of existing canonical business rows.
            previous_code=candidate['transform_code_sha256']
            assert set(code)==set(previous_code)
            assert {k for k in code if code[k]!=previous_code[k]}<={'dimensions.py','dimension_transform.py','dimension_fixtures.py'}
            code=previous_code
            version=hashlib.sha256(canonical([code,inputs]).encode()).hexdigest()
            compatibility=dict(path=str(compatibility_path),sha256=sha(compatibility_path),reason=candidate['reason'],revalidate_dates=candidate.get('revalidate_dates',False))
    manifest=json.loads((ROOT/files[2]).read_text());design=json.loads((ROOT/files[0]).read_text())
    mapping=json.loads((ROOT/files[1]).read_text());catalog=json.loads((ROOT/files[-1]).read_text())
    entities=[e for e in manifest['entities'] if e['kind']=='DIMENSION']
    run_id='dim_'+catalog['batch_id']+'_'+version[:12]
    folder=Path('/analytics/canonical')/run_id
    pg=Jdbc(spark,'postgres');ora=Jdbc(spark,'oracle')
    lock=pg.query('SELECT pg_try_advisory_lock(5173,1)')[0][0]
    if lock!='t':raise RuntimeError('Another dimension coordinator is running')
    registered=False
    try:
        assert pg.query('SELECT count(*) FROM ce_control.active_publication')[0][0]=='0','Initial loader cannot modify a published warehouse'
        assert pg.query('SELECT count(*) FROM ce_control.reader_lease WHERE expires_at>now()')[0][0]=='0'
        other=pg.query("SELECT run_id FROM ce_control.pipeline_run WHERE run_id<>? AND state='DIMENSIONS_READY'",[run_id])
        if other:raise RuntimeError('A previous dimension candidate exists; use pinned code or implement reviewed incremental coordinator')
        previous=pg.query("SELECT to_char(started_at AT TIME ZONE 'UTC','YYYY-MM-DD\"T\"HH24:MI:SS.US'),state FROM ce_control.pipeline_run WHERE run_id=?",[run_id])
        if phase=='verify' and not previous:raise ValueError('No matching candidate; code or input changed')
        now=datetime.now(timezone.utc).replace(tzinfo=None)
        if previous:now=datetime.fromisoformat(previous[0][0])
        else:
            pg.execute("INSERT INTO ce_control.pipeline_run(run_id,source_batch_id,input_manifest_sha256,transform_version,started_at,state,oracle_slot) VALUES(?,?,?,?,?,'RUNNING','CE_DWH_A')",
                       [run_id,catalog['batch_id'],inputs[files[-1]],version,now])
        registered=True
        # Freeze canonical inputs before any target write. Resume uses exactly the same files.
        frozen=folder/'manifest.json'
        if frozen.exists():
            frozen_manifest=json.loads(frozen.read_text())
            assert frozen_manifest['input_sha256']==inputs and frozen_manifest['code_sha256']==code
            for rel,digest in frozen_manifest['files'].items():assert sha(folder/rel)==digest,'Canonical artifact changed'
            for ds in catalog['datasets']:
                p=ROOT/'lake/v2'/ds['relative_path']
                if p.exists():assert sha(p)==ds['sha256'],'Source changed after freeze'
            quality=frozen_manifest['quality']
            if compatibility and compatibility['revalidate_dates']:
                print('Revalidating PostgreSQL timestamp offsets and all dimension payloads against frozen canonical',flush=True)
                sources,recheck=read_sources(spark,ROOT/'lake/v2',catalog,mapping)
                assert not recheck['date_errors'] and not recheck['quarantine'],'Revalidation still has source errors'
                assert all(v=='COMPLETE' for v in recheck['source_status'].values())
                for e in entities:
                    d=next(t for t in design['tables'] if t['id']==e['id']);m=next(t for t in mapping['entities'] if t['id']==e['id'])
                    recomputed,bad=dimension_inputs(e,d,m,sources,recheck);assert not bad
                    old=[r.asDict() for r in spark.read.parquet(str(folder/e['physical_name'])).filter("member_kind='NORMAL'").collect()]
                    columns=sorted(recomputed[0]) if recomputed else []
                    assert sorted(canonical([r[c] for c in columns]) for r in recomputed)==sorted(canonical([r[c] for c in columns]) for r in old),'Parser repair changes business payload: '+e['id']
                quality['D01']=dict(quality['D01'],status='COMPLETE',coverage=1,rejected=0)
                recheck['business_payloads_identical_to_frozen_canonical']=True
                recheck['original_canonical_manifest_sha256']=sha(frozen)
                recheck['execution_code_sha256']=execution_code
                save(OUT/'quality-revalidation.json',recheck)
        else:
            if phase=='verify':raise ValueError('Frozen canonical manifest missing')
            folder.mkdir(parents=True,exist_ok=True)
            print('Reading pinned lake inputs and validating dimension dependencies',flush=True)
            sources,source_report=read_sources(spark,ROOT/'lake/v2',catalog,mapping)
            quality={};built={};events_by_entity={};allkeys=[]
            for e in entities:
                d=next(t for t in design['tables'] if t['id']==e['id']);m=next(t for t in mapping['entities'] if t['id']==e['id'])
                normals,bad=dimension_inputs(e,d,m,sources,source_report);source_report['quarantine']+=bad
                relevant=list(m['aliases'].values())
                flags=[source_report['source_status'].get(s,'UNAVAILABLE') for s in relevant]
                if e['id']=='D01':flags=list(source_report['source_status'].values())+(['PARTIAL'] if source_report['date_errors'] else [])
                status='COMPLETE' if not bad and all(x=='COMPLETE' for x in flags) else ('PARTIAL' if normals else 'UNAVAILABLE')
                rejected=sum(1 for q in source_report['quarantine'] if q.get('source') in relevant or q.get('entity')==e['id'])
                quality[e['id']]=dict(status=status,accepted=len(normals),rejected=rejected,
                                     coverage=None if flags and any(x!='COMPLETE' for x in flags) else (1 if not bad else len(normals)/(len(normals)+len(bad))),
                                     source_tables=relevant,reason='Dimension coverage only; no KPI completeness inferred')
                for r in normals:
                    tracked=d.get('tracked_attributes',[c['name'] for c in e['columns'] if c['name'] in r and c['name'] not in e['primary_key']+['source_system','member_kind']])
                    r['row_hash']=payload_hash(r,tracked)
                    if e['history_policy']=='SCD_TYPE2':
                        key=[e['id']]+[r[c] for c in d['business_key']]+[scalar(BOOTSTRAP)]
                        allkeys.append(key)
                built[e['id']]=normals
            registry=pg.registry(allkeys)
            save(folder/'registry.json',[[json.loads(k),v] for k,v in sorted(registry.items())])
            for e in entities:
                d=next(t for t in design['tables'] if t['id']==e['id']);pk=e['primary_key'][0];rows=[];events=[]
                for r in built[e['id']]:
                    if e['history_policy']=='SCD_TYPE2':
                        event=dict(effective_at=BOOTSTRAP,payload={k:v for k,v in r.items() if k!='row_hash'},row_hash=r['row_hash'],
                                   basis='BOOTSTRAP_ASSUMPTION',batch=catalog['batch_id'],transform=version)
                        bk=[r[c] for c in d['business_key']]
                        rows+=materialize([event],[],lambda t:registry[canonical([e['id']]+bk+[scalar(t)])],pk,now)
                        events.append(dict(business_key=bk,**event))
                    else:rows.append(dict(r,source_batch_id=catalog['batch_id'],transform_version=version,created_at_utc=now,updated_at_utc=now))
                for key,kind in [(0,'UNKNOWN'),(-1,'NOT_APPLICABLE')]:
                    r={c['name']:None for c in e['columns']};r.update({pk:key,'source_system':'system','member_kind':kind,
                        'source_batch_id':catalog['batch_id'],'transform_version':version,'created_at_utc':now,'updated_at_utc':now})
                    r['row_hash']=payload_hash(r,d.get('tracked_attributes',[c['name'] for c in e['columns'] if c['name'] not in e['primary_key']+['source_batch_id','transform_version','row_hash','created_at_utc','updated_at_utc']]))
                    if e['history_policy']=='SCD_TYPE2':r.update(valid_from_utc=BOOTSTRAP,valid_to_utc=None,is_current=1,version_no=1,effective_time_basis='BOOTSTRAP_ASSUMPTION')
                    rows.append(r)
                # Source business errors are quarantined before the canonical
                # assertion, never silently skipped by a target JDBC writer.
                bad_predicate=F.lit(False)
                for check in manifest['row_checks'][e['id']]:
                    bad_predicate=bad_predicate|(~F.coalesce(F.expr(check['spark']),F.lit(True)))
                invalid=[r.asDict() for r in frame(spark,e,rows).filter(bad_predicate).collect()]
                if invalid:
                    assert all(r['member_kind']=='NORMAL' for r in invalid),'Invalid special member is an implementation error'
                    rejected_keys={r[pk] for r in invalid}
                    rows=[r for r in rows if r[pk] not in rejected_keys]
                    source_report['quarantine'] += [dict(entity=e['id'],code='TARGET_CHECK',payload=r) for r in invalid]
                    q=quality[e['id']];q['accepted']-=len(invalid);q['rejected']+=len(invalid)
                    q['status']='PARTIAL' if q['accepted'] else 'UNAVAILABLE';q['coverage']=None
                validate(spark,e,rows,manifest['row_checks'][e['id']])
                # Explicit typed Parquet is reusable by either engine and kept on E volume.
                path=folder/e['physical_name']
                if path.exists():raise ValueError('Incomplete canonical preparation found; preserve it for investigation, use a fresh reviewed run')
                frame(spark,e,rows).coalesce(1).write.mode('errorifexists').parquet(str(path))
                save(folder/(e['id']+'-events.json'),events)
            save(folder/'source-quality.json',source_report)
            frozen_manifest=dict(run_id=run_id,input_sha256=inputs,code_sha256=code,transform_version=version,
                                 source_batch_id=catalog['batch_id'],started_at_utc=scalar(now),quality=quality,
                                 files={str(p.relative_to(folder)):sha(p) for p in sorted(folder.rglob('*')) if p.is_file()},
                                 publication_state='NOT_PUBLISHED')
            save(frozen,frozen_manifest)
        result=[]
        for e in entities:
            rows=[r.asDict() for r in spark.read.parquet(str(folder/e['physical_name'])).collect()]
            validate(spark,e,rows,manifest['row_checks'][e['id']])
            q=quality[e['id']]
            if phase=='run':
                pg.execute('INSERT INTO ce_control.quality_entity(run_id,entity_id,status,accepted,rejected,coverage,detail) VALUES(?,?,?,?,?,?,?::jsonb) ON CONFLICT(run_id,entity_id) DO UPDATE SET status=EXCLUDED.status,accepted=EXCLUDED.accepted,rejected=EXCLUDED.rejected,coverage=EXCLUDED.coverage,detail=EXCLUDED.detail',
                           [run_id,e['id'],q['status'],q['accepted'],q['rejected'],None if q['coverage'] is None else Decimal(str(q['coverage'])),canonical(q)])
            print('Checking/loading '+e['id']+' '+e['physical_name']+' rows='+str(len(rows)),flush=True)
            result.append(load_or_compare(spark,ora,e,rows,phase=='run'))
        # No facts/bridges, no active publication or fabricated zero KPI values.
        remaining=[e for e in manifest['entities'] if e['kind'] not in ('DIMENSION','VALIDATION_VIEW')]
        for e in remaining:
            assert ora.query('SELECT COUNT(*) FROM CE_DWH_A.'+e['physical_name'])[0][0]=='0'
            assert spark.table('ce.gold.'+e['physical_name']).count()==0
        registry_pairs=json.loads((folder/'registry.json').read_text())
        checkkeys={canonical(json.loads(k)):int(v) for k,v in pg.query('SELECT canonical_key::text,surrogate_key FROM ce_control.key_registry')}
        assert all(checkkeys[canonical(k)]==v for k,v in registry_pairs),'Registry mapping drift'
        report=dict(status='PASSED',phase=phase,run_id=run_id,checked_at=datetime.now(timezone.utc).isoformat(),
                    tables=result,rows=sum(t['rows'] for t in result),registry_keys=len(registry_pairs),quality=quality,
                    input_sha256=inputs,code_sha256=code,execution_code_sha256=execution_code,coordinator_compatibility=compatibility,
                    quality_revalidation_sha256=sha(OUT/'quality-revalidation.json') if compatibility and compatibility['revalidate_dates'] else None,
                    canonical_path=str(folder),canonical_manifest_sha256=sha(frozen),
                    facts_loaded=False,published=False,oracle_slot='CE_DWH_A',scd_initial_basis='BOOTSTRAP_ASSUMPTION',
                    limits=['Initial snapshot/replay only; later production SCD events require fact rekey and publication coordinator.',
                            'Dimension adapter bounded to 100000 rows per source on driver; not a distributed scaling benchmark.'])
        if phase=='verify':
            prior=json.loads((OUT/'run.json').read_text())
            assert prior['tables']==result,'Read-only verification changed rows or snapshots'
            report['replay_unchanged']=True
        else:
            pg.execute("UPDATE ce_control.pipeline_run SET state='DIMENSIONS_READY',finished_at=now(),evidence=?::jsonb WHERE run_id=?",[canonical(dict(report_path=str(OUT/'run.json'),manifest_sha256=sha(frozen))),run_id])
        save(OUT/(phase+'.json'),report)
        print('DIMENSION_RESULT '+canonical(dict(status='PASSED',phase=phase,rows=report['rows'],tables=len(result),published=False)),flush=True)
    except Exception:
        if registered and phase=='run':pg.execute("UPDATE ce_control.pipeline_run SET state='FAILED',finished_at=now() WHERE run_id=?",[run_id])
        raise
    finally:ora.close();pg.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['run','verify','fixtures']);args=parser.parse_args()
    spark=create_session('CompanyE dimension '+args.phase);spark.sparkContext.setLogLevel('WARN')
    try:
        if args.phase=='fixtures':
            from analytics_runtime.dimension_fixtures import exercise
            exercise(spark)
        else:run(spark,args.phase)
    finally:spark.stop()
