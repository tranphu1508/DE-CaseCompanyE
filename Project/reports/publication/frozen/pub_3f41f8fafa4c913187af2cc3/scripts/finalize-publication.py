"""Validate publication evidence, freeze implementation, back up control metadata."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, importlib.util, json, subprocess

spec=importlib.util.spec_from_file_location('publication_launcher',Path(__file__).with_name('publication.py'))
pub=importlib.util.module_from_spec(spec);spec.loader.exec_module(pub)
ROOT=pub.ROOT;OUT=pub.OUT
def read(path): return json.loads(path.read_text(encoding='utf8'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,obj): path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

m=read(OUT/'manifest.json');pid=m['publication_id']
manifest_sha=hashlib.sha256(json.dumps(m,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
prepared=read(OUT/'prepare.json');published=read(OUT/'publish.json');verified=read(OUT/'verify.json');fixtures=read(OUT/'fixtures.json')
assert prepared['status']=='PREPARED' and prepared['active_unchanged']
assert prepared['manifest_sha256']==manifest_sha
assert published['outcome'] in ('COMMITTED','ALREADY_COMMITTED')
assert verified['status']=='PASSED_PUBLICATION_READER' and verified['released_readers']
assert verified['publish_replay']['outcome']=='ALREADY_COMMITTED'
assert fixtures['status']=='PASSED' and fixtures['count']==len(fixtures['checks'])==28
assert all(r['publication_id']==pid for r in [prepared,published,verified])
assert len(verified['checks'])==36 and len(m['tables'])==37 and len(m['quality_metrics'])==47
assert sum(t['rows'] for t in m['tables'].values())==771564
assert sum(t['mode']=='TABLE' for t in m['tables'].values())==34 and len(m['helpers'])==2
assert m['tables']['F15']['mode']=='DISABLED'

# Preserve the previously accepted ETL and source generation evidence.
for phase in ['dimension-etl','fact-etl']:
    run=read(ROOT/'reports'/phase/'run.json')
    for rel,digest in run['input_sha256'].items(): assert sha(ROOT/rel)==digest,rel
    code=run.get('execution_code_sha256',run['code_sha256'])
    code_root=ROOT/'src/analytics_runtime' if phase=='dimension-etl' else ROOT
    for rel,digest in code.items(): assert sha(code_root/rel)==digest,rel
    evidence=read(ROOT/'reports'/phase/'verification.json')
    for rel,digest in evidence['evidence_sha256'].items(): assert sha(ROOT/rel)==digest,rel
catalog=read(ROOT/'lake/v2/catalog/catalog.json')
for entry in catalog['datasets']: assert sha(ROOT/'lake/v2'/entry['relative_path'])==entry['sha256']
assert len(catalog['datasets'])==267

mid=pub.svc.container('metadata')
sql="""SELECT json_build_object(
 'active',(SELECT coalesce(json_agg(x),'[]') FROM ce_control.active_publication x),
 'publications',(SELECT coalesce(json_agg(x),'[]') FROM (SELECT publication_id,run_id,oracle_slot,manifest_sha256,created_at FROM ce_control.publication) x),
 'candidates',(SELECT coalesce(json_agg(x),'[]') FROM (SELECT publication_id,state,generation,manifest_sha256 FROM ce_control.publication_candidate) x),
 'publication_table_count',(SELECT count(*) FROM ce_control.publication_table),
 'live_readers',(SELECT count(*) FROM ce_control.reader_lease WHERE expires_at>clock_timestamp()),
 'events',(SELECT json_agg(x ORDER BY event_id) FROM ce_control.publication_event x),
 'schema_versions',(SELECT json_agg(version ORDER BY version) FROM ce_control.schema_version),
 'roles',(SELECT json_agg(x) FROM (SELECT rolname,rolsuper,rolcreaterole,rolcreatedb FROM pg_roles WHERE rolname IN ('ce_publisher','ce_reader')) x),
 'role_grants',(SELECT json_agg(x) FROM (SELECT grantee,table_name,privilege_type FROM information_schema.role_table_grants WHERE table_schema='ce_control' AND grantee IN ('ce_publisher','ce_reader') ORDER BY grantee,table_name,privilege_type) x),
 'reader_direct_update',has_table_privilege('ce_reader','ce_control.active_publication','UPDATE'),
 'publisher_direct_update',has_table_privilege('ce_publisher','ce_control.active_publication','UPDATE'));
"""
metadata=json.loads(pub.call(['docker','exec','-i',mid,'psql','-U','ce_meta_admin','-d','ce_metadata','-X','-At','-v','ON_ERROR_STOP=1'],sql))
assert metadata['active']==[dict(singleton=True,publication_id=pid)]
assert len(metadata['publications'])==1 and metadata['publications'][0]['manifest_sha256']==manifest_sha
assert metadata['candidates']==[dict(publication_id=pid,state='PUBLISHED',generation=m['generation'],manifest_sha256=manifest_sha)]
assert metadata['publication_table_count']==37 and metadata['live_readers']==0
assert [e['action'] for e in metadata['events']]==['RESERVED','PREPARED','PUBLISHED']
assert not metadata['reader_direct_update'] and not metadata['publisher_direct_update']
assert all(not any(r[k] for k in ['rolsuper','rolcreaterole','rolcreatedb']) for r in metadata['roles'])
save(OUT/'control-verification.json',metadata)

oracle_sql="""set heading off feedback off pagesize 0 linesize 300 trimspool on
whenever sqlerror exit sql.sqlcode rollback
alter session set container=FREEPDB1;
select 'GUARD|'||slot||'|'||state||'|'||publication_id from ce_stage.publication_guard order by slot;
select 'TRIGGERS|'||status||'|'||count(*) from dba_triggers where owner in ('CE_STAGE','CE_DWH_A','CE_DWH_B') and trigger_name like 'PUB_GUARD_%' group by status;
select 'INVALID|'||count(*) from dba_objects where owner in ('CE_STAGE','CE_DWH_A','CE_DWH_B') and object_name like 'PUB_GUARD_%' and status<>'VALID';
exit
"""
ora=pub.call(['docker','exec','-i',pub.svc.container('oracle'),'sqlplus','-S','/ as sysdba'],oracle_sql)
lines=[line.strip() for line in ora.splitlines() if '|' in line]
assert 'GUARD|CE_DWH_A|SEALED|'+pid in lines
assert 'TRIGGERS|ENABLED|78' in lines and 'INVALID|0' in lines
assert not any(line.startswith('TRIGGERS|DISABLED|') for line in lines)
save(OUT/'oracle-verification.json',dict(lines=lines,enabled_guard_triggers=78))

recovery=read(OUT/'reboot-recovery.json')
assert recovery['metadata']['active']==[]
assert recovery['metadata']['candidates'][0]['state']=='BUILDING'
assert recovery['metadata']['candidates'][0]['publication_id']==pid
assert recovery['metadata']['candidates'][0]['generation']==m['generation']==1
assert sha(OUT/'prepare-interrupted-reboot.log')==recovery['interrupted_log_sha256']

backup=ROOT/'databases/ce_control-after-publication.dump'
with backup.open('wb') as target:
    completed=subprocess.run(['docker','exec',mid,'pg_dump','-U','ce_meta_admin','-d','ce_metadata','-Fc','--schema=ce_control'],stdout=target,stderr=subprocess.PIPE)
assert completed.returncode==0,'Metadata backup failed'
listing=subprocess.run(['docker','exec','-i',mid,'pg_restore','--list'],input=backup.read_bytes(),capture_output=True)
assert listing.returncode==0 and all(x in listing.stdout for x in [b'publication_candidate',b'active_publication',b'key_registry'])
save(OUT/'metadata-backup.json',dict(path=backup.relative_to(ROOT).as_posix(),sha256=sha(backup),bytes=backup.stat().st_size,archive_list_verified=True,restore_drill_performed=False))

paths=[p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'src/publication').glob('*.py'))]+[
 'scripts/publication.py','scripts/inspect-publication-recovery.py','scripts/finalize-publication.py',
 'config/analytics/ddl/publication_v3.sql','compose.publication.yaml',
 'docs/CompanyE_Physical_Design.md','README.md','reports/publication/oracle-guards.sql']
archive=OUT/'frozen'/pid
for rel in paths:
    dest=archive/rel;dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists(): assert sha(dest)==sha(ROOT/rel),'Cannot overwrite frozen artifact '+rel
    else: dest.write_bytes((ROOT/rel).read_bytes())
save(OUT/'frozen-code.json',dict(path=archive.relative_to(ROOT).as_posix(),sha256={rel:sha(archive/rel) for rel in paths},secrets_included=False))
evidence={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(OUT.glob('*')) if p.is_file() and p.name!='verification.json'}
result=dict(status='PASSED_CONSISTENT_PUBLICATION',checked_at=datetime.now(timezone.utc).isoformat(),publication_id=pid,
 manifest_sha256=manifest_sha,published=True,active_publications=1,entity_entries=37,reader_entities_checked=36,
 iceberg_snapshot_tags=34,canonical_helpers=2,optional_disabled=['F15'],total_logical_rows_per_branch=771564,
 fault_tests_passed=28,source_files_unchanged=267,etl_frozen_evidence_unchanged=True,metric_input_readiness_count=47,
 all_columns_equal_between_engines=True,cross_table_query=verified['cross_table'],live_readers=0,
 interrupted_prepare_resumed_same_id_and_generation=True,duplicate_publications=0,
 retention='RETAIN_ALL_NO_AUTOMATIC_GC',next_step='Semantic KPI queries and quality propagation; Power BI/web; controlled comparative benchmarks.',
 limitations=['Atomic visibility for protocol-compliant readers, not distributed XA or 2PC.',
 'Initial baseline published; production incremental loader and slot retirement/GC are not implemented.',
 'Real interrupted BUILDING recovery observed; no guarantee for every power-loss or storage failure and no full backup restore drill.',
 'KPI input readiness is not acceptance of 47 KPI formulas; Power BI/web integration remains.',
 'Oracle and catalog admins remain trusted; shared local Spark catalog credentials can mutate catalog.',
 'Local prototype; no high availability, scale benchmark or stress-test conclusion.'],evidence_sha256=evidence)
save(OUT/'verification.json',result)
print(json.dumps({k:v for k,v in result.items() if k not in ['evidence_sha256','limitations']},ensure_ascii=False,indent=2))
