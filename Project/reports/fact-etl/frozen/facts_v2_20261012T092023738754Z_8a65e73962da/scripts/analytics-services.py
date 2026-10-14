"""Provision and verify the isolated CompanyE analytics Compose project.

Usage: python scripts/analytics-services.py prepare|up|bootstrap|jars|status|restart
No source database, lake dataset, business table or other Compose project is changed.
Secrets are generated locally, reused on reruns, and never printed into reports.
"""
from pathlib import Path
import argparse
import datetime as dt
import json
import re
import secrets
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'reports/analytics-runtime'
ENV = ROOT / '.env.analytics'
KEYS = ['COMPANYE_ORACLE_ADMIN_PASSWORD', 'COMPANYE_METADATA_ADMIN_PASSWORD',
        'COMPANYE_CATALOG_PASSWORD', 'COMPANYE_ORACLE_PROBE_PASSWORD']
REPORTS.mkdir(parents=True, exist_ok=True)


def credentials():
    if not ENV.exists():
        return {}
    return dict(line.split('=', 1) for line in ENV.read_text().splitlines()
                if '=' in line and not line.startswith('#'))


def redact(text):
    values=list(credentials().values())
    for name in ['control_password','oracle_loader_password']:
        path=ROOT/'.secrets/analytics'/name
        if path.exists():values.append(path.read_text(encoding='utf-8').strip())
    for value in values:
        if value:
            text = text.replace(value, '[REDACTED]')
    return text


def command(args, input=None, timeout=900):
    result = subprocess.run(args, cwd=ROOT, input=input, text=True,
                            encoding='utf-8', errors='replace', capture_output=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(redact(result.stdout + '\n' + result.stderr)[-7000:])
    return result.stdout


def compose(*args):
    return command(['docker', 'compose', '--env-file', str(ENV), '-f', 'compose.analytics.yaml',
                    '--profile', 'oracle', '--profile', 'lakehouse', *args])


def container(service):
    value = compose('ps', '-q', service).strip()
    if not value or '\n' in value:
        raise RuntimeError(f'Expected one running container for {service}')
    return value


def record(name, obj):
    (REPORTS / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def prepare():
    values = credentials()
    for key in KEYS:
        if not values.get(key):
            values[key] = 'Ce9a' + secrets.token_hex(16)
    # Restrict generated values to safe literal characters in bootstrap SQL and dotenv.
    if not all(re.fullmatch('[A-Za-z0-9]{20,128}', values[k]) for k in KEYS):
        raise RuntimeError('Existing analytics secret format requires review; credentials not changed')
    ENV.write_text('# Private local analytics credentials. Do not commit or publish.\n' +
                   ''.join(f'{key}={values[key]}\n' for key in KEYS), encoding='utf-8')
    secret_dir = ROOT / '.secrets/analytics'
    secret_dir.mkdir(parents=True, exist_ok=True)
    for file, key in [('catalog_password', KEYS[2]), ('oracle_probe_password', KEYS[3])]:
        (secret_dir / file).write_text(values[key], encoding='utf-8')
    # Compose mounts these before business bootstrap, including on a clean host.
    # Reuse pre-existing files: changing a secret here would desynchronize DB roles.
    for name in ['control_password','oracle_loader_password']:
        path=secret_dir/name
        if not path.exists():path.write_text('Ce9a'+secrets.token_hex(16),encoding='utf-8')
        if not re.fullmatch('[A-Za-z0-9]{20,128}',path.read_text(encoding='utf-8').strip()):
            raise RuntimeError('Existing ETL secret format requires review; credentials not changed')
    compose('config', '--quiet')
    print('Private credentials prepared; Compose configuration valid.', flush=True)


def status():
    rows = []
    for service in ['oracle', 'metadata', 'spark']:
        cid = container(service)
        # Deliberately do not persist full inspect: Config.Env includes passwords.
        item = json.loads(command(['docker', 'inspect', cid]))[0]
        rows.append(dict(service=service, container_id=cid, image=item['Image'],
                         configured_image=item['Config']['Image'], state=item['State']['Status'],
                         health=item['State'].get('Health', {}).get('Status'),
                         started_at=item['State']['StartedAt'],
                         ports=item['NetworkSettings']['Ports'],
                         memory_bytes=item['HostConfig']['Memory'],
                         cpu_quota_nano=item['HostConfig']['NanoCpus'], mounts=item['Mounts']))
    record('services.json', dict(captured_at=dt.datetime.now(dt.timezone.utc).isoformat(), services=rows))
    return rows


def wait_ready():
    deadline = time.monotonic() + 900
    while time.monotonic() < deadline:
        rows = status()
        print(' | '.join(f"{r['service']}: {r['state']}/{r['health'] or 'no healthcheck'}" for r in rows), flush=True)
        if all(r['state'] == 'running' and (r['health'] == 'healthy' if r['service'] in ['oracle','metadata'] else True) for r in rows):
            return
        time.sleep(15)
    raise TimeoutError('Analytics readiness timed out; inspect sanitized service logs')


def bootstrap():
    values = credentials()
    pg_sql = f"""\\set ON_ERROR_STOP on
DO $$ BEGIN
 IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='ce_catalog') THEN
   CREATE ROLE ce_catalog LOGIN PASSWORD '{values[KEYS[2]]}' NOSUPERUSER NOCREATEDB NOCREATEROLE;
 END IF;
END $$;
CREATE SCHEMA IF NOT EXISTS iceberg_catalog AUTHORIZATION ce_catalog;
CREATE SCHEMA IF NOT EXISTS ce_control AUTHORIZATION ce_meta_admin;
GRANT CONNECT ON DATABASE ce_metadata TO ce_catalog;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
SELECT version();
SELECT nspname, pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname IN ('iceberg_catalog','ce_control');
"""
    pg = command(['docker','exec','-i',container('metadata'),'psql','-U','ce_meta_admin','-d','ce_metadata','-X'], input=pg_sql)
    oracle_sql = f"""set echo off verify off define off feedback off pagesize 100 linesize 200
whenever sqlerror exit sql.sqlcode
whenever oserror exit failure
alter session set container=FREEPDB1;
declare n number; begin
 select count(*) into n from dba_users where username='CE_PROBE';
 if n=0 then execute immediate 'create user ce_probe identified by "{values[KEYS[3]]}" default tablespace users quota 20M on users'; end if;
end;
/
grant create session, create table to ce_probe;
begin
 execute immediate 'create table ce_probe.runtime_probe (run_id varchar2(64 char) not null, id number(19,0) not null, label varchar2(200 char), amount number(19,0), qty number(18,3), event_utc timestamp(6), optional_amount number(19,0), primary key(run_id,id))';
exception when others then if sqlcode != -955 then raise; end if; end;
/
select banner_full from v$version;
select parameter,value from nls_database_parameters where parameter='NLS_CHARACTERSET';
select name,open_mode from v$pdbs;
select name,display_value from v$parameter where name in ('cpu_count','sga_target','pga_aggregate_target');
exit
"""
    oracle = command(['docker','exec','-i',container('oracle'),'sqlplus','-S','/ as sysdba'], input=oracle_sql)
    record('bootstrap.json', dict(status='PASSED', timestamp=dt.datetime.now(dt.timezone.utc).isoformat(),
                                  postgres=redact(pg), oracle=redact(oracle), business_schema_created=False))
    print('Metadata schemas, restricted catalog role and isolated Oracle probe schema ready.', flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=['prepare','up','bootstrap','jars','status','restart'])
    phase=parser.parse_args().phase
    if phase=='prepare': prepare()
    elif phase=='up':
        compose('up','-d','--pull','missing')
        wait_ready()
    elif phase=='bootstrap': bootstrap()
    elif phase=='jars':
        output=command(['docker','exec',container('spark'),'python3','/workspace/src/analytics_runtime/install_jars.py'])
        data=json.loads(output)
        record('jars.json',data)
        print('Verified JARs: '+', '.join(p['coordinate'] for p in data['jars']))
    elif phase=='status': print(json.dumps(status(),indent=2))
    elif phase=='restart':
        compose('restart')
        wait_ready()


if __name__=='__main__':
    main()
