"""Prepare narrowly scoped fact staging privileges, run ETL, or verify replay."""
from pathlib import Path
import argparse,importlib.util,json,subprocess
spec=importlib.util.spec_from_file_location('services',Path(__file__).with_name('analytics-services.py'))
svc=importlib.util.module_from_spec(spec);spec.loader.exec_module(svc)
ROOT=svc.ROOT;OUT=ROOT/'reports/fact-etl';OUT.mkdir(exist_ok=True)

def bootstrap():
    manifest=json.loads((ROOT/'config/analytics/ddl/manifest.json').read_text(encoding='utf8'))
    sql="set echo off verify off define off feedback off\nwhenever sqlerror exit sql.sqlcode rollback\nalter session set container=FREEPDB1;\n"
    for e in manifest['entities']:
        if e['id'].startswith('D') or e['id']=='F15':continue
        name=e['physical_name'];target='ce_stage.'+name+'_input_a' if e['kind']=='VALIDATION_VIEW' else 'ce_dwh_a.'+name
        stage='ce_stage.etl_'+e['id']
        sql+="begin execute immediate 'create table "+stage+" as select * from "+target+" where 1=0'; exception when others then if sqlcode != -955 then raise; end if; end;\n/\n"
        sql+='grant select,insert,delete on '+stage+' to ce_loader;\n'
        sql+='grant select,insert on '+target+' to ce_loader;\n'
        if e['kind']=='VALIDATION_VIEW':
            # View owner must be able to delegate reads of its underlying helper.
            sql+='grant select,read on '+target+' to ce_dwh_a with grant option;\n'
    sql+='exit\n'
    (OUT/'bootstrap-oracle.sql').write_text(sql,encoding='utf8')
    pg="""BEGIN;
ALTER TABLE ce_control.pipeline_run DROP CONSTRAINT IF EXISTS pipeline_run_state_check;
ALTER TABLE ce_control.pipeline_run ADD CONSTRAINT pipeline_run_state_check CHECK(state IN ('RUNNING','DIMENSIONS_READY','ETL_READY','FAILED','PUBLISHED'));
INSERT INTO ce_control.schema_version VALUES (2,now()) ON CONFLICT DO NOTHING;
COMMIT;
"""
    (OUT/'bootstrap-control.sql').write_text(pg,encoding='utf8')
    for service,args,text in [('oracle',['sqlplus','-S','/ as sysdba'],sql),('metadata',['psql','-U','ce_meta_admin','-d','ce_metadata','-X','-v','ON_ERROR_STOP=1'],pg)]:
        print(svc.command(['docker','exec','-i',svc.container(service),*args],input=text,timeout=300))
    print('Fact staging ready; loader can INSERT candidate A and clean only its disposable staging tables.')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['bootstrap','run','verify']);a=ap.parse_args()
    if a.phase=='bootstrap':bootstrap()
    else:
        jars=json.loads((ROOT/'reports/analytics-runtime/jars.json').read_text())['jars']
        cmd=['docker','exec',svc.container('spark'),'/opt/spark/bin/spark-submit','--jars',','.join(j['file'] for j in jars),'/workspace/src/fact_etl/pipeline.py',a.phase]
        with (OUT/(a.phase+'.log')).open('w',encoding='utf8') as log:
            p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT);code=p.wait(timeout=7200)
        print((OUT/(a.phase+'.log')).read_text(encoding='utf8')[-4500:])
        if code:raise SystemExit(code)
