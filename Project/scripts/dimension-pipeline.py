"""Bootstrap least-privilege ETL accounts or run/check the initial dimension candidate.

No source reset, fact load, publication switch, or destructive schema operation.
"""
from pathlib import Path
import argparse, importlib.util, json, re, secrets, subprocess
spec=importlib.util.spec_from_file_location('services',Path(__file__).with_name('analytics-services.py'))
svc=importlib.util.module_from_spec(spec);spec.loader.exec_module(svc)
ROOT=svc.ROOT
OUT=ROOT/'reports/dimension-etl';OUT.mkdir(exist_ok=True)

def bootstrap():
    sd=ROOT/'.secrets/analytics'; passwords={}
    for name in ['control_password','oracle_loader_password']:
        p=sd/name
        if not p.exists():p.write_text('Ce9a'+secrets.token_hex(16),encoding='utf-8')
        passwords[name]=p.read_text().strip()
        if not re.fullmatch('[A-Za-z0-9]{20,128}',passwords[name]):
            raise ValueError('Unsupported private secret format; no SQL executed')
    pg="""\\set ON_ERROR_STOP on
DO $$ BEGIN IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname='ce_control_writer') THEN
CREATE ROLE ce_control_writer LOGIN PASSWORD '%s' NOSUPERUSER NOCREATEDB NOCREATEROLE; END IF; END $$;
"""%passwords['control_password']
    pg+=(ROOT/'config/analytics/ddl/control_schema.sql').read_text()
    ora="""set echo off verify off define off feedback off
whenever sqlerror exit sql.sqlcode rollback
alter session set container=FREEPDB1;
declare n number; begin select count(*) into n from dba_users where username='CE_LOADER';
if n=0 then execute immediate 'create user ce_loader identified by "%s"'; end if; end;
/
grant create session to ce_loader;
"""%passwords['oracle_loader_password']
    manifest=json.loads((ROOT/'config/analytics/ddl/manifest.json').read_text())
    dimension_names={e['physical_name'] for e in manifest['entities'] if e['kind']=='DIMENSION'}
    for obj in manifest['oracle_objects']:
        privilege='select'
        if obj['owner']=='ce_dwh_a' and obj['name'] in dimension_names:privilege='select, insert'
        if obj['owner']=='ce_dwh_b' and obj['name']=='dim_site':privilege='select, insert, delete'
        ora+=f"grant {privilege} on {obj['owner']}.{obj['name']} to ce_loader;\n"
    ora+='exit\n'
    # Keep passwords out of command lines, output, exceptions and durable logs.
    for service,args,sql in [('metadata',['psql','-U','ce_meta_admin','-d','ce_metadata','-X'],pg),
                             ('oracle',['sqlplus','-S','/ as sysdba'],ora)]:
        r=subprocess.run(['docker','exec','-i',svc.container(service),*args],input=sql,
                         encoding='utf-8',capture_output=True,timeout=300)
        if r.returncode:
            msg=r.stdout+r.stderr
            for value in passwords.values():msg=msg.replace(value,'[REDACTED]')
            raise RuntimeError(msg[-2000:])
    svc.compose('up','-d','--no-deps','spark')
    print('Control schema and ETL accounts ready; Spark secret mounts refreshed.',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['bootstrap','run','verify','fixtures']);a=ap.parse_args()
    if a.phase=='bootstrap':bootstrap()
    else:
        jars=json.loads((ROOT/'reports/analytics-runtime/jars.json').read_text())['jars']
        # Stream progress but never credentials. Runtime exception messages are kept local.
        cmd=['docker','exec',svc.container('spark'),'/opt/spark/bin/spark-submit','--jars',
             ','.join(j['file'] for j in jars),'/workspace/src/analytics_runtime/dimensions.py',a.phase]
        with (OUT/(a.phase+'.log')).open('w',encoding='utf-8') as log:
            p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT)
            code=p.wait(timeout=3600)
        print((OUT/(a.phase+'.log')).read_text(encoding='utf-8')[-4500:])
        if code:raise SystemExit(code)
