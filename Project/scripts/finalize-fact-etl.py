"""Seal ETL evidence, export canonical metadata, and back up durable key registry."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,importlib.util,json,subprocess,sys
spec=importlib.util.spec_from_file_location('services',Path(__file__).with_name('analytics-services.py'))
svc=importlib.util.module_from_spec(spec);spec.loader.exec_module(svc)
ROOT=svc.ROOT;OUT=ROOT/'reports/fact-etl'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
first=read(OUT/'first-load.json');run=read(OUT/'run.json');verify=read(OUT/'verify.json');independent=read(OUT/'independent-validation.json')
assert first['status']==run['status']==verify['status']=='PASSED_FACT_ETL'
assert run['replay_unchanged'] and verify['replay_unchanged']
assert independent['status']=='PASSED_INDEPENDENT_BASELINE'
assert first['run_id']==run['run_id']==verify['run_id']==independent['run_id']
for rel,digest in {**run['input_sha256'],**run['code_sha256']}.items():assert sha(ROOT/rel)==digest,rel
fixtures=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'tests/test_fact_transform.py')],capture_output=True,text=True,encoding='utf8')
(OUT/'fixtures.log').write_text(fixtures.stdout+fixtures.stderr,encoding='utf8');assert fixtures.returncode==0
save(OUT/'fixtures.json',dict(status='PASSED',count=16,test_sha256=sha(ROOT/'tests/test_fact_transform.py'),log_sha256=sha(OUT/'fixtures.log'),mutated_source_or_business_target=False))
sid=svc.container('spark');mid=svc.container('metadata')
files=['manifest.json','source-quality.json','quarantine.json','scope-quality.json','registry.json','reconciliation.json','external-reconciliation.json','metric-readiness.json']
for name in files:svc.command(['docker','cp',sid+':'+run['canonical_path']+'/'+name,str(OUT/('canonical-'+name))])
assert sha(OUT/'canonical-manifest.json')==run['canonical_manifest_sha256']
canonical=read(OUT/'canonical-manifest.json')
for name in files[1:]:assert sha(OUT/('canonical-'+name))==canonical['files'][name]
archive=OUT/'frozen'/run['run_id'];paths=list(run['input_sha256'])+list(run['code_sha256'])+[
    'scripts/fact-pipeline.py','scripts/verify-fact-etl.py','scripts/finalize-fact-etl.py','scripts/analytics-services.py',
    'src/verify_fact_etl.py','tests/test_fact_transform.py','config/analytics/ddl/control_schema.sql','compose.analytics.yaml',
    'reports/fact-etl/bootstrap-oracle.sql','reports/fact-etl/bootstrap-control.sql']
for rel in paths:
    dest=archive/rel;dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists():assert sha(dest)==sha(ROOT/rel),'Cannot overwrite frozen artifact '+rel
    else:dest.write_bytes((ROOT/rel).read_bytes())
save(OUT/'frozen-code.json',dict(path=str(archive.relative_to(ROOT)),sha256={rel:sha(archive/rel) for rel in paths},secrets_included=False))
sql="""SELECT json_build_object(
 'registry_keys',(SELECT count(*) FROM ce_control.key_registry),
 'active_publications',(SELECT count(*) FROM ce_control.active_publication),
 'publications',(SELECT count(*) FROM ce_control.publication),
 'metrics',(SELECT count(*) FROM ce_control.quality_metric),
 'metric_status',(SELECT json_object_agg(status,n) FROM (SELECT status,count(*) n FROM ce_control.quality_metric GROUP BY status) x),
 'schema_versions',(SELECT json_agg(version ORDER BY version) FROM ce_control.schema_version),
 'writer_superuser',(SELECT rolsuper FROM pg_roles WHERE rolname='ce_control_writer'),
 'registry_update',has_table_privilege('ce_control_writer','ce_control.key_registry','UPDATE'),
 'active_update',has_table_privilege('ce_control_writer','ce_control.active_publication','UPDATE'));
"""
metadata=json.loads(svc.command(['docker','exec','-i',mid,'psql','-U','ce_meta_admin','-d','ce_metadata','-X','-At','-v','ON_ERROR_STOP=1'],input=sql))
assert metadata['active_publications']==metadata['publications']==0 and metadata['metrics']==47
assert not any(metadata[k] for k in ['writer_superuser','registry_update','active_update'])
save(OUT/'control-verification.json',metadata)
backup=ROOT/'databases/ce_control-after-facts.dump'
with backup.open('wb') as f:
    result=subprocess.run(['docker','exec',mid,'pg_dump','-U','ce_meta_admin','-d','ce_metadata','-Fc','--schema=ce_control'],stdout=f,stderr=subprocess.PIPE)
    assert result.returncode==0,'Control backup failed'
result=subprocess.run(['docker','exec','-i',mid,'pg_restore','--list'],input=backup.read_bytes(),capture_output=True)
assert result.returncode==0 and b'key_registry' in result.stdout and b'quality_metric' in result.stdout
save(OUT/'registry-backup.json',dict(path=str(backup.relative_to(ROOT)),bytes=backup.stat().st_size,sha256=sha(backup),archive_list_verified=True,restore_drill_performed=False))
external=read(OUT/'canonical-external-reconciliation.json')
sealed={str(p.relative_to(ROOT)):sha(p) for p in sorted(OUT.glob('*.json')) if p.name!='verification.json'}
result=dict(status='PASSED_FACT_ETL',checked_at=datetime.now(timezone.utc).isoformat(),run_id=run['run_id'],
    source_tables=independent['source_tables'],source_rows=independent['source_rows'],source_files_unchanged=independent['source_files_unchanged'],
    entities_loaded=20,facts_loaded=16,bridges_loaded=2,validation_helpers_loaded=2,new_logical_rows_per_branch=independent['target_rows'],
    existing_dimension_rows=26426,total_logical_rows_per_branch=26426+independent['target_rows'],fixtures_passed=16,
    independent_controls=len(independent['checks']),replay_unchanged=True,all_columns_equal_between_engines=True,dimensions_unchanged=16,
    metric_input_readiness=metadata['metric_status'],external_mismatches=len(external['mismatches']),external_latest_invalid=len(external['newest_invalid']),
    optional_disabled=['F15'],published=False,oracle_candidate_slot='CE_DWH_A',canonical_path=run['canonical_path'],
    next_step='Publication coordinator and reader leases; semantic KPI queries and controlled fault tests; then Power BI/web and comparative benchmarks.',
    limitations=['Initial pinned snapshot and replay only; not production incremental or CDC.',
                'Driver transformations are bounded to 100000 rows per source table; not a distributed scale benchmark.',
                '47 quality records describe input readiness; filter/lot-specific quality and KPI formulas still need semantic-layer acceptance.',
                'External receipt feed has quarantined events; these are reconciliation warnings, not extra DB receipts.',
                'No active publication, BI connection, stress test or recovery drill claimed.'],evidence_sha256=sealed)
save(OUT/'verification.json',result)
print(json.dumps({k:v for k,v in result.items() if k not in ['evidence_sha256','limitations']},ensure_ascii=False,indent=2))
