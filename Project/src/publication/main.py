from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
from analytics_runtime.session import create_session
from analytics_runtime.etl_io import oracle_rows
from publication.core import Coordinator,Connection,Reader,read,save,file_hash,canonical,digest,content_hash,pin_tag,verify_pins

ROOT=Path('/workspace');OUT=ROOT/'reports/publication';OUT.mkdir(exist_ok=True)
def identity():
    d=read(ROOT/'reports/dimension-etl/run.json');f=read(ROOT/'reports/fact-etl/run.json')
    return 'pub_'+digest([d['run_id'],f['run_id'],'CE_DWH_A'])[:24],d,f
def assert_sealed(spark,m):
    ora=Connection(spark,'publisher','oracle')
    try:assert ora.query('SELECT state,publication_id FROM ce_stage.publication_guard WHERE slot=?',[m['oracle_slot']])==[['SEALED',m['publication_id']]],'Oracle slot is not sealed for publication'
    finally:ora.close()
def prepare(spark):
    pid,d,f=identity();co=Coordinator(spark);ora=Connection(spark,'publisher','oracle')
    try:
        assert co.db.query('SELECT pg_try_advisory_lock(5173,1)')[0][0]=='t','ETL writer still running'
        previous=co.active();existing=co.candidate(pid)
        if existing and existing[0] in ('PREPARED','PUBLISHED'):
            m=json.loads(existing[1]);assert digest(m)==existing[2];verify_pins(spark,m);assert_sealed(spark,m)
            save(OUT/'manifest.json',m);return m
        assert read(ROOT/'reports/fact-etl/verification.json')['status']=='PASSED_FACT_ETL'
        for evidence in [d,f]:
            for rel,sha in evidence['input_sha256'].items():assert file_hash(ROOT/rel)==sha,'ETL input contract changed: '+rel
        # Frozen ETL evidence itself is checked before trusting its row hashes.
        for report_path in ['reports/dimension-etl/verification.json','reports/fact-etl/verification.json']:
            evidence=read(ROOT/report_path)
            for rel,sha in evidence['evidence_sha256'].items():
                path=ROOT/rel.replace('\\','/');assert file_hash(path)==sha,'ETL evidence changed: '+rel
        generation=co.begin(pid,f['run_id'],'CE_DWH_A',previous)
        ora.execute('BEGIN ce_stage.seal_publication_slot(?,?); END;',['CE_DWH_A',pid])
        ddl=read(ROOT/'config/analytics/ddl/manifest.json');frozen=read(Path(f['canonical_path'])/'manifest.json')
        assert file_hash(Path(f['canonical_path'])/'manifest.json')==f['canonical_manifest_sha256']
        dimfrozen=read(Path(d['canonical_path'])/'manifest.json')
        assert file_hash(Path(d['canonical_path'])/'manifest.json')==d['canonical_manifest_sha256']
        for folder,artifact in [(Path(d['canonical_path']),dimfrozen),(Path(f['canonical_path']),frozen)]:
            for rel,sha in artifact['files'].items():assert file_hash(folder/rel)==sha,'Canonical changed: '+rel
        catalog=read(ROOT/'lake/v2/catalog/catalog.json')
        for ds in catalog['datasets']:assert file_hash(ROOT/'lake/v2'/ds['relative_path'])==ds['sha256']
        expected={t['entity']:t for t in d['tables']+f['tables']};tables={};helpers={}
        for e in ddl['entities']:
            eid=e['id'];name=e['physical_name'];mode='DISABLED' if eid=='F15' else 'HELPER' if e['kind']=='VALIDATION_VIEW' else 'TABLE'
            print('Validate publication target '+eid,flush=True)
            actual=oracle_rows(spark,e);oracle_hash=content_hash(actual,e)
            item=dict(name=name,mode=mode,oracle_object='CE_DWH_A.'+name,rows=len(actual),content_sha256=oracle_hash,snapshot_id=None)
            if mode=='DISABLED':
                assert not actual and spark.table('ce.gold.'+name).count()==0
            else:
                assert oracle_hash==expected[eid]['content_sha256'],'Oracle differs from accepted ETL '+eid
                if mode=='HELPER':
                    path=Path(f['canonical_path'])/name;df=spark.read.parquet(str(path))
                    helpers[name]=dict(path=str(path),sha256={str(p.relative_to(path)):file_hash(p) for p in sorted(path.rglob('*')) if p.is_file()},schema=df.schema.jsonValue())
                else:
                    table='ce.gold.'+name;snapshot=expected[eid]['iceberg_snapshot_id'];assert snapshot is not None
                    item.update(iceberg_table=table,snapshot_id=snapshot)
                    df=spark.read.option('snapshot-id',str(snapshot)).table(table)
                assert content_hash([r.asDict() for r in df.collect()],e)==oracle_hash,'Pinned Iceberg/helper differs '+eid
            tables[eid]=item
        for t in tables.values():
            if t['mode']=='TABLE':pin_tag(spark,t['iceberg_table'],pid,t['snapshot_id'])
        metrics=read(Path(f['canonical_path'])/'metric-readiness.json')
        m=dict(version='companye-publication-1',publication_id=pid,run_id=f['run_id'],dimension_run_id=d['run_id'],
            source_batch_id=catalog['batch_id'],source_catalog_sha256=file_hash(ROOT/'lake/v2/catalog/catalog.json'),
            source_cutoff=dict(kind='PINNED_FINAL_SNAPSHOT',catalog_batch=catalog['batch_id'],source_file_count=len(catalog['datasets'])),
            oracle_slot='CE_DWH_A',generation=generation,expected_active=previous,tables=tables,helpers=helpers,
            quality_entities={**d['quality'],**f['quality']},quality_metrics=metrics,
            quality_scope=read(Path(f['canonical_path'])/'scope-quality.json'),external_warnings=read(Path(f['canonical_path'])/'external-reconciliation.json')['newest_invalid'],
            validation=dict(all_columns_equal=True,oracle_sealed=True,tags_pinned=True),
            retention=dict(policy='RETAIN_ALL_NO_AUTOMATIC_GC',reader_max_ttl_seconds=3600),
            provenance=dict(fact_verification_sha256=file_hash(ROOT/'reports/fact-etl/verification.json'),dimension_verification_sha256=file_hash(ROOT/'reports/dimension-etl/verification.json')))
        verify_pins(spark,m);assert_sealed(spark,m);sha=co.prepare(m)
        save(OUT/'manifest.json',m);save(OUT/'prepare.json',dict(status='PREPARED',publication_id=pid,manifest_sha256=sha,table_entries=len(tables),tags=34,oracle_slot='CE_DWH_A',active_unchanged=co.active()==previous))
        print('PREPARED '+pid,flush=True);return m
    finally:
        co.db.query('SELECT pg_advisory_unlock(5173,1)');co.close();ora.close()

def publish(spark):
    m=read(OUT/'manifest.json');co=Coordinator(spark)
    try:
        assert co.db.query('SELECT pg_try_advisory_lock(5173,1)')[0][0]=='t'
        verify_pins(spark,m);assert_sealed(spark,m)
        result=co.publish(m,m['expected_active']);save(OUT/'publish.json',result);print(canonical(result),flush=True)
    finally:co.db.query('SELECT pg_advisory_unlock(5173,1)');co.close()

def verify(spark):
    m=read(OUT/'manifest.json');co=Coordinator(spark)
    try:
        assert co.active()==m['publication_id'];assert_sealed(spark,m);verify_pins(spark,m)
        checks=[]
        with Reader(spark,'publication-acceptance') as reader:
            assert reader.pid==m['publication_id']
            for eid,t in m['tables'].items():
                if t['mode']=='DISABLED':continue
                query='SELECT COUNT(*) FROM {'+eid+'}'
                oracle=reader.query(query,'oracle');ice=reader.query(query,'iceberg')
                assert int(oracle['rows'][0][0])==int(ice['rows'][0][0])==t['rows']
                checks.append(dict(entity=eid,rows=t['rows'],publication_id=reader.pid))
            # Cross-table query and arithmetic prove the pinned alias path is usable.
            query='SELECT COUNT(*),SUM(b.customer_due_vnd) FROM {F01} b JOIN {D03} h ON b.hotel_key=h.hotel_key'
            o=reader.query(query,'oracle');i=reader.query(query,'iceberg')
            assert [str(v) for v in o['rows'][0]]==[str(v) for v in i['rows'][0]]
        assert co.db.query('SELECT count(*) FROM ce_control.reader_lease WHERE expires_at>clock_timestamp()')[0][0]=='0'
        replay=co.publish(m,m['expected_active']);assert replay['outcome']=='ALREADY_COMMITTED'
        save(OUT/'verify.json',dict(status='PASSED_PUBLICATION_READER',publication_id=m['publication_id'],checks=checks,cross_table=o['rows'],publish_replay=replay,active_publication=co.active(),released_readers=True,quality_metrics=len(m['quality_metrics'])))
        print('PASSED_PUBLICATION_READER '+m['publication_id'],flush=True)
    finally:co.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase');args=parser.parse_args();spark=create_session('CompanyE-publication-'+args.phase)
    try:
        if args.phase=='prepare':prepare(spark)
        elif args.phase=='publish':publish(spark)
        elif args.phase=='verify':verify(spark)
        elif args.phase=='fixtures':
            from publication.fixtures import run
            run(spark)
        elif args.phase=='status':
            co=Coordinator(spark)
            try:print(canonical(dict(active_publication=co.active())),flush=True)
            finally:co.close()
        else:raise ValueError(args.phase)
    finally:spark.stop()
