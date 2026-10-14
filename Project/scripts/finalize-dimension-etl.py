"""Export canonical metadata, preserve registry backup and seal execution evidence."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,importlib.util,json,re,subprocess
spec=importlib.util.spec_from_file_location('services',Path(__file__).with_name('analytics-services.py'))
svc=importlib.util.module_from_spec(spec);spec.loader.exec_module(svc)
ROOT=svc.ROOT;OUT=ROOT/'reports/dimension-etl'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,data):p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

first=read(OUT/'first-load.json');run=read(OUT/'run.json');verify=read(OUT/'verify.json');fixtures=read(OUT/'fixtures.json')
assert all(r['status']=='PASSED' for r in [first,run,verify,fixtures])
assert first['tables']==run['tables']==verify['tables'],'Replay changed payload, rows or Iceberg snapshots'
assert verify['replay_unchanged'] and fixtures['fixture_rows_removed']
assert run['published'] is False and run['facts_loaded'] is False
assert len(run['tables'])==16 and all(t['specials']==2 for t in run['tables'])
for path,digest in run['input_sha256'].items():assert sha(ROOT/path)==digest,path
for name,digest in run.get('execution_code_sha256',run['code_sha256']).items():assert sha(ROOT/'src/analytics_runtime'/name)==digest,name
archive=OUT/'frozen'/run['run_id']
paths=list(run['input_sha256'])+['src/analytics_runtime/'+name for name in run['code_sha256']]+[
    'scripts/dimension-pipeline.py','scripts/analytics-services.py','config/analytics/ddl/control_schema.sql','compose.analytics.yaml']
for rel in paths:
    dest=archive/rel;dest.parent.mkdir(parents=True,exist_ok=True)
    expected=run['code_sha256'][Path(rel).name] if rel.startswith('src/analytics_runtime/') else run['input_sha256'].get(rel,sha(ROOT/rel))
    if dest.exists():assert sha(dest)==expected,'Archived code/input must not be overwritten'
    else:dest.write_bytes((ROOT/rel).read_bytes())
save(OUT/'frozen-code.json',dict(path=str(archive.relative_to(ROOT)),sha256={rel:sha(archive/rel) for rel in paths},secrets_included=False))
if run.get('coordinator_compatibility'):
    compat=ROOT/'config/analytics/dimension_replay_compatibility_v1.json'
    assert sha(compat)==run['coordinator_compatibility']['sha256']
    replay_archive=OUT/'frozen'/('replay_'+run['run_id']);replay_archive.mkdir(parents=True,exist_ok=True)
    changed=[ROOT/'src/analytics_runtime'/name for name,digest in run['execution_code_sha256'].items() if digest!=run['code_sha256'][name]]
    for p in changed+[compat]:
        dest=replay_archive/p.name
        if dest.exists():assert sha(dest)==sha(p)
        else:dest.write_bytes(p.read_bytes())
    save(OUT/'coordinator-patch.json',dict(reason=run['coordinator_compatibility']['reason'],
         files={str(p.relative_to(ROOT)):sha(p) for p in replay_archive.iterdir()}))
if run.get('quality_revalidation_sha256'):
    assert sha(OUT/'quality-revalidation.json')==run['quality_revalidation_sha256']==verify['quality_revalidation_sha256']
    recheck=read(OUT/'quality-revalidation.json')
    assert not recheck['date_errors'] and not recheck['quarantine'] and recheck['business_payloads_identical_to_frozen_canonical']
catalog=read(ROOT/'lake/v2/catalog/catalog.json')
for ds in catalog['datasets']:
    assert sha(ROOT/'lake/v2'/ds['relative_path'])==ds['sha256'],'Source file changed'
# Independent frozen-v2 cardinality expectations, not copied from the loader.
# Valid only for this complete baseline; a future PARTIAL batch needs its own audit.
expected_normal={'D01':1461,'D02':4,'D03':8,'D04':240,'D05':15,'D06':40,'D07':24120,
                 'D08':72,'D09':16,'D10':4,'D11':4,'D12':12,'D13':120,'D14':16,'D15':6,'D16':256}
assert all(q['status']=='COMPLETE' for q in run['quality'].values()),'Frozen v2 baseline unexpectedly incomplete'
assert {t['entity']:t['normal'] for t in run['tables']}==expected_normal,'Independent baseline count mismatch'
save(OUT/'baseline-counts.json',dict(source_batch_id=catalog['batch_id'],normal_members=expected_normal,
      date_years=[2023,2026],customer_profile_rule='12120 hotel + 12000 entertainment, no entity merge',
      channel_rule='13 hotel + 2 entertainment',special_members_per_dimension=2))
sid=svc.container('spark');mid=svc.container('metadata')
for name in ['manifest.json','source-quality.json','registry.json']:
    svc.command(['docker','cp',sid+':'+run['canonical_path']+'/'+name,str(OUT/('canonical-'+name))])
assert sha(OUT/'canonical-manifest.json')==run['canonical_manifest_sha256']
canonical=read(OUT/'canonical-manifest.json')
assert sha(OUT/'canonical-source-quality.json')==canonical['files']['source-quality.json']
assert sha(OUT/'canonical-registry.json')==canonical['files']['registry.json']
sql="""SELECT json_build_object(
 'tables',(SELECT json_agg(tablename ORDER BY tablename) FROM pg_tables WHERE schemaname='ce_control'),
 'registry_keys',(SELECT count(*) FROM ce_control.key_registry),
 'pipeline_runs',(SELECT json_agg(json_build_object('run_id',run_id,'state',state,'slot',oracle_slot)) FROM ce_control.pipeline_run),
 'active_publications',(SELECT count(*) FROM ce_control.active_publication),
 'publications',(SELECT count(*) FROM ce_control.publication),
 'metrics',(SELECT count(*) FROM ce_control.quality_metric),
 'writer_superuser',(SELECT rolsuper FROM pg_roles WHERE rolname='ce_control_writer'),
 'registry_update',has_table_privilege('ce_control_writer','ce_control.key_registry','UPDATE'),
 'active_update',has_table_privilege('ce_control_writer','ce_control.active_publication','UPDATE')
);"""
metadata=json.loads(svc.command(['docker','exec','-i',mid,'psql','-U','ce_meta_admin','-d','ce_metadata','-X','-At','-v','ON_ERROR_STOP=1'],input=sql))
assert len(metadata['tables'])==10 and metadata['active_publications']==metadata['publications']==metadata['metrics']==0
assert not any(metadata[k] for k in ['writer_superuser','registry_update','active_update'])
assert any(r['run_id']==run['run_id'] and r['state']=='DIMENSIONS_READY' for r in metadata['pipeline_runs'])
save(OUT/'control-verification.json',metadata)
backup=ROOT/'databases/ce_control-after-dimensions.dump'
with backup.open('wb') as f:
    r=subprocess.run(['docker','exec',mid,'pg_dump','-U','ce_meta_admin','-d','ce_metadata','-Fc','--schema=ce_control'],stdout=f,stderr=subprocess.PIPE)
    if r.returncode:raise RuntimeError('Metadata backup failed')
# pg_restore --list validates the archive header/index without modifying a DB.
r=subprocess.run(['docker','exec','-i',mid,'pg_restore','--list'],input=backup.read_bytes(),capture_output=True)
assert r.returncode==0 and b'key_registry' in r.stdout and b'pipeline_run' in r.stdout
save(OUT/'registry-backup.json',dict(path=str(backup.relative_to(ROOT)),sha256=sha(backup),bytes=backup.stat().st_size,archive_list_verified=True,restore_drill_performed=False))
sealed={str(p.relative_to(ROOT)):sha(p) for p in sorted(OUT.glob('*.json')) if p.name!='verification.json'}
sealed.update({str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'config/analytics/ddl/control_schema.sql',ROOT/'scripts/dimension-pipeline.py',Path(__file__)]})
report=dict(status='PASSED_DIMENSION_ETL',checked_at=datetime.now(timezone.utc).isoformat(),run_id=run['run_id'],
            tables_per_branch=16,rows_per_branch=run['rows'],special_members=32,scd2_dimensions=14,static_dimensions=2,
            production_registry_keys=run['registry_keys'],fixtures_passed=fixtures['count'],replay_unchanged=True,
            all_columns_equal_between_engines=True,source_files_unchanged=len(catalog['datasets']),
            published=False,facts_loaded=False,oracle_candidate_slot='CE_DWH_A',
            current_source_quality='reports/dimension-etl/quality-revalidation.json',
            initial_source_quality_preserved='reports/dimension-etl/canonical-source-quality.json',
            next_step='ETL fact/bridge/helper, quality by KPI, publication coordinator and reader lease',
            limitations=run['limits']+['Publication tables exist but coordinator/reader lease lifecycle are not implemented.','No benchmark, stress test or Power BI connection claimed.'],
            evidence_sha256=sealed)
save(OUT/'verification.json',report)
print(json.dumps({k:v for k,v in report.items() if k not in ['evidence_sha256','limitations']},ensure_ascii=False,indent=2))
