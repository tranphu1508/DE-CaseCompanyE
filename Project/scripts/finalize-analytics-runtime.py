"""Record successful provisioning from persisted probe evidence; never starts services."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/analytics-runtime'
def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def save(path,value): path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
run=read(OUT/'active-probe.json')['run_id']
before=read(OUT/f'{run}-write.json')
after=read(OUT/f'{run}-verify.json')
bootstrap=read(OUT/'bootstrap.json')
jars=read(OUT/'jars.json')
services=read(OUT/'services.json')
assert before['status']==after['status']==bootstrap['status']=='PASSED'
assert before['snapshots']==after['snapshots']
assert before['run_id']==after['run_id']==run
assert jars['status']=='VERIFIED'
assert len(services['services'])==3
for service in services['services']:
    assert service['state']=='running'
    if service['service']!='spark': assert service['health']=='healthy'
    # Every tested service was actually restarted after the initial write.
    assert service['started_at']>before['checked_at']
    assert service['started_at']<after['checked_at']
lockpath=ROOT/'config/analytics_runtime_lock_v1.json'
backup=OUT/'runtime-lock-before-provision.json'
if not backup.exists(): shutil.copy2(lockpath,backup)
lock=read(lockpath)
lock['status']='PROVISIONED_SERVICE_SMOKE_AND_RESTART_PASSED'
lock['provisioned_at']=after['checked_at']
lock['oracle']['database_runtime_version']='23.26.3.0.0'
assert '23.26.3.0.0' in after['oracle_version']
lock['oracle']['verification']='Pinned image pulled; FREEPDB1 READ WRITE, AL32UTF8, JDBC typed round trip and restart persistence passed. See reports/analytics-runtime/verification.json.'
lock['spark']['verification']='Analytics Spark session 3.5.7 with Iceberg 1.10.2 and both JDBC drivers passed typed round trip and restart persistence.'
lock['spark']['python']='3.8.10'
lock['metadata_postgres']['new_service_started']=True
assert 'PostgreSQL 17.11' in bootstrap['postgres']
lock['metadata_postgres']['database_runtime_version']='17.11'
for package in lock['packages']:
    jar=next(p for p in jars['jars'] if p['coordinate']==package['coordinate'])
    package.update(jar_url=jar['url'],jar_sha256=jar['sha256'],jar_sha512=jar['sha512'],
                   jar_published_checksum_algorithm=jar['published_checksum_algorithm'],
                   jar_published_checksum=jar['published_checksum'],jar_bytes=jar['bytes'])
lock['artifact_verification_limit']='Three runtime JARs downloaded and matched published HTTPS Maven checksums; local SHA-256 pins saved. Iceberg publishes SHA-512; PostgreSQL and Oracle artifacts publish SHA-1. Integration and restart probe passed; no dependency vulnerability audit claimed.'
save(lockpath,lock)
evidence=['bootstrap.json','jars.json','services.json','host-storage.json','active-probe.json',f'{run}-write.json',f'{run}-verify.json']
code=['compose.analytics.yaml','config/analytics/spark-defaults.conf','scripts/analytics-services.py',
      'scripts/analytics-probe.py','src/analytics_runtime/session.py','src/analytics_runtime/install_jars.py',
      'src/analytics_runtime/probe.py','scripts/finalize-analytics-runtime.py']
report=dict(status='PASSED_SERVICE_PROVISIONING_AND_RESTART',recorded_at=datetime.now(timezone.utc).isoformat(),
            run_id=run,services=services['services'],versions=dict(oracle='23.26.3.0.0',postgres='17.11',
            spark=after['spark_version'],iceberg=after['iceberg_version'],java='11.0.27',python='3.8.10'),
            checks=after['checks'],published_checksums_verified=True,
            oracle_host_endpoint='127.0.0.1:11521/FREEPDB1',oracle_host_tcp_checked=True,
            metadata='ce_metadata.iceberg_catalog, owned by ce_catalog; ce_control schema, owned by ce_meta_admin',
            catalog_tables=['iceberg_catalog.iceberg_tables','iceberg_catalog.iceberg_namespace_properties'],
            storage_windows_vhdx=lock['storage_observation']['windows_vhdx'],
            host_storage=read(OUT/'host-storage.json'),business_schema_deployed=False,
            business_etl_run=False,benchmark_run=False,
            secret_locations=['.env.analytics','.secrets/analytics/'],
            evidence_sha256={f:sha(OUT/f) for f in evidence},code_sha256={f:sha(ROOT/f) for f in code},
            runtime_lock_sha256=sha(lockpath),
            limitations=['Three-row service integration fixture only; business DDL, SCD2, 47 KPIs and performance remain untested.',
                        'Spark runs local[2] jobs via spark-submit, not a persistent Thrift/JDBC SQL server.',
                        'ce_control currently has a schema only; publication/control tables and coordinator are not implemented.',
                        'Probe tables intentionally retained for verification; they are separate from business tables.'])
save(OUT/'verification.json',report)
print(json.dumps({'status':report['status'],'run_id':run,'business_schema_deployed':False},indent=2))
