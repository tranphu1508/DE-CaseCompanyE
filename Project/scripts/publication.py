"""Bootstrap publication identities/guards or run the consistent publication API."""
from pathlib import Path
import argparse,importlib.util,json,re,secrets,subprocess
spec=importlib.util.spec_from_file_location('services',Path(__file__).with_name('analytics-services.py'))
svc=importlib.util.module_from_spec(spec);spec.loader.exec_module(svc)
ROOT=svc.ROOT;OUT=ROOT/'reports/publication';OUT.mkdir(exist_ok=True)
PASSWORDS=['publication_password','reader_password','oracle_publication_password','oracle_reader_password']
def call(args,sql=None,timeout=300):
    r=subprocess.run(args,input=sql,encoding='utf8',capture_output=True,timeout=timeout,cwd=ROOT)
    if r.returncode:
        error=r.stdout+r.stderr
        for name in PASSWORDS:
            p=ROOT/'.secrets/analytics'/name
            if p.exists():error=error.replace(p.read_text().strip(),'[REDACTED]')
        raise RuntimeError(svc.redact(error)[-4500:])
    return r.stdout
def bootstrap():
    pw={}
    for name in PASSWORDS:
        p=ROOT/'.secrets/analytics'/name
        if not p.exists():p.write_text('Ce9a'+secrets.token_hex(16),encoding='utf8')
        pw[name]=p.read_text().strip();assert re.fullmatch('[A-Za-z0-9]{20,128}',pw[name])
    pg=''
    for role,name in [('ce_publisher','publication_password'),('ce_reader','reader_password')]:
        pg+="DO $$ BEGIN IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname='"+role+"') THEN CREATE ROLE "+role+" LOGIN PASSWORD '"+pw[name]+"' NOSUPERUSER NOCREATEDB NOCREATEROLE; END IF; END $$;\n"
    migration=(ROOT/'config/analytics/ddl/publication_v3.sql').read_text(encoding='utf8');pg+=migration
    entities=json.loads((ROOT/'config/analytics/ddl/manifest.json').read_text(encoding='utf8'))['entities']
    policy={e['id']:dict(name=e['physical_name'],mode='DISABLED' if e['id']=='F15' else 'HELPER' if e['kind']=='VALIDATION_VIEW' else 'TABLE') for e in entities}
    metrics=[m['id'] for m in json.loads((ROOT/'config/source_target_mapping_v1.json').read_text(encoding='utf8'))['metric_mapping']]
    pg+="INSERT INTO ce_control.publication_policy VALUES(true,'"+json.dumps(policy)+"','"+json.dumps(metrics)+"') ON CONFLICT DO NOTHING;\n"
    # Dedicated fixture metadata: same APIs/locks, isolated table contents.
    pg+='CREATE SCHEMA IF NOT EXISTS ce_pub_test;\n'
    pg+=(ROOT/'config/analytics/ddl/control_schema.sql').read_text().replace('ce_control','ce_pub_test').replace('ce_pub_test_writer','ce_control_writer')
    pg+=(ROOT/'reports/fact-etl/bootstrap-control.sql').read_text().replace('ce_control','ce_pub_test')
    pg+=migration.replace('ce_control','ce_pub_test')
    policy_test={'D01':dict(name='pub_probe_dim',mode='TABLE'),'F01':dict(name='pub_probe_fact',mode='TABLE')}
    pg+="INSERT INTO ce_pub_test.publication_policy VALUES(true,'"+json.dumps(policy_test)+"','[\"B01.01\"]') ON CONFLICT DO NOTHING;\n"
    call(['docker','exec','-i',svc.container('metadata'),'psql','-U','ce_meta_admin','-d','ce_metadata','-X','-v','ON_ERROR_STOP=1'],pg)
    sql="set echo off verify off define off feedback off\nwhenever sqlerror exit sql.sqlcode rollback\nalter session set container=FREEPDB1;\n"
    for role,name in [('CE_PUBLISHER','oracle_publication_password'),('CE_READER','oracle_reader_password')]:
        sql+="declare n number; begin select count(*) into n from dba_users where username='"+role+"'; if n=0 then execute immediate 'create user "+role+' identified by "'+pw[name]+"\"'; end if; end;\n/\ngrant create session to "+role+";\n"
    sql+="""begin execute immediate 'create table ce_stage.publication_guard(slot varchar2(20) primary key, state varchar2(10) not null, publication_id varchar2(128))'; exception when others then if sqlcode<>-955 then raise; end if; end;
/
"""
    for slot in ['CE_DWH_A','CE_DWH_B','TEST_A','TEST_B']:
        sql+="merge into ce_stage.publication_guard g using (select '"+slot+"' slot from dual) s on(g.slot=s.slot) when not matched then insert(slot,state) values(s.slot,'OPEN');\n"
    sql+="""commit;
create or replace procedure ce_stage.assert_publication_writable(p_slot varchar2) authid definer as s varchar2(10);
begin
 select state into s from ce_stage.publication_guard where slot=p_slot for update;
 if s<>'OPEN' then raise_application_error(-20072,'PUBLICATION_SLOT_SEALED'); end if;
end;
/
create or replace procedure ce_stage.seal_publication_slot(p_slot varchar2,p_id varchar2) authid definer as s varchar2(10); old_id varchar2(128);
begin
 select state,publication_id into s,old_id from ce_stage.publication_guard where slot=p_slot for update;
 if s='SEALED' and old_id<>p_id then raise_application_error(-20073,'SLOT_SEALED_FOR_OTHER_PUBLICATION'); end if;
 update ce_stage.publication_guard set state='SEALED',publication_id=p_id where slot=p_slot;
end;
/
grant execute on ce_stage.seal_publication_slot to ce_publisher;
grant select on ce_stage.publication_guard to ce_publisher;
grant execute on ce_stage.assert_publication_writable to ce_dwh_a,ce_dwh_b;
"""
    objects=[]
    for slot in ['A','B']:
        owner='ce_dwh_'+slot.lower()
        for e in entities:
            name=e['physical_name'];obj=owner+'.'+name
            if e['kind']=='VALIDATION_VIEW':
                target='ce_stage.'+name+'_input_'+slot.lower()
                sql+='grant select,read on '+target+' to '+owner+' with grant option;\n'
            else:target=obj
            sql+='grant read on '+obj+' to ce_reader;\n'
            objects.append((target,'CE_DWH_'+slot,'pub_guard_'+e['id'].lower()+'_'+slot.lower()))
        for suffix in ['DIM','FACT']:
            target='ce_stage.pub_probe_'+slot.lower()+'_'+suffix.lower()
            sql+="begin execute immediate 'create table "+target+"(id number(18,0) primary key,v number(18,0) not null)'; exception when others then if sqlcode<>-955 then raise; end if; end;\n/\n"
            sql+='grant select,insert,delete on '+target+' to ce_loader;\ngrant read on '+target+' to ce_reader;\ngrant select on '+target+' to ce_publisher;\n'
            objects.append((target,'TEST_'+slot,'pub_guard_test_'+slot.lower()+'_'+suffix.lower()))
    for target,slot,trigger in objects:
        owner=target.split('.')[0]
        sql+='create or replace trigger '+owner+'.'+trigger+' before insert or update or delete on '+target+" begin ce_stage.assert_publication_writable('"+slot+"'); end;\n/\n"
    sql+='exit\n'
    redacted=sql
    for value in pw.values():redacted=redacted.replace(value,'[PRIVATE_SECRET]')
    (OUT/'oracle-guards.sql').write_text(redacted,encoding='utf8')
    call(['docker','exec','-i',svc.container('oracle'),'sqlplus','-S','/ as sysdba'],sql)
    call(['docker','compose','--env-file',str(ROOT/'.env.analytics'),'-f','compose.analytics.yaml','-f','compose.publication.yaml','--profile','oracle','--profile','lakehouse','up','-d','--no-deps','spark'])
    print('Publication APIs, isolated fixture namespace, Oracle guards and read-only reader identity ready.')

def reset_fixtures():
    # Only our dedicated metadata/probes. The policy and SQL APIs stay installed.
    pg="""DO $$ BEGIN
    IF EXISTS(SELECT 1 FROM pg_constraint c JOIN pg_class a ON a.oid=c.conrelid JOIN pg_namespace n ON n.oid=a.relnamespace JOIN pg_class b ON b.oid=c.confrelid JOIN pg_namespace nb ON nb.oid=b.relnamespace WHERE c.contype='f' AND nb.nspname='ce_pub_test' AND n.nspname<>'ce_pub_test') THEN RAISE EXCEPTION 'Fixture has external dependents'; END IF;
    END $$;
    TRUNCATE ce_pub_test.reader_lease,ce_pub_test.active_publication,ce_pub_test.publication_table,ce_pub_test.benchmark_run,ce_pub_test.publication,ce_pub_test.publication_candidate,ce_pub_test.publication_event,ce_pub_test.quality_entity,ce_pub_test.quality_metric,ce_pub_test.pipeline_run,ce_pub_test.key_registry RESTART IDENTITY;
    UPDATE ce_pub_test.slot_reservation SET publication_id=NULL,generation=0;
    """
    call(['docker','exec','-i',svc.container('metadata'),'psql','-U','ce_meta_admin','-d','ce_metadata','-X','-v','ON_ERROR_STOP=1'],pg)
    sql="set echo off feedback off\nwhenever sqlerror exit sql.sqlcode rollback\nalter session set container=FREEPDB1;\nupdate ce_stage.publication_guard set state='OPEN',publication_id=NULL where slot in ('TEST_A','TEST_B');\n"
    for slot in ['a','b']:
        for kind in ['dim','fact']:sql+='delete from ce_stage.pub_probe_'+slot+'_'+kind+';\n'
    sql+='commit;\nexit\n'
    call(['docker','exec','-i',svc.container('oracle'),'sqlplus','-S','/ as sysdba'],sql)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['bootstrap','fixtures','prepare','publish','verify','status']);args=ap.parse_args()
    if args.phase=='bootstrap':bootstrap()
    else:
        if args.phase=='fixtures':reset_fixtures()
        jars=json.loads((ROOT/'reports/analytics-runtime/jars.json').read_text())['jars']
        cmd=['docker','exec',svc.container('spark'),'/opt/spark/bin/spark-submit','--jars',','.join(j['file'] for j in jars),'/workspace/src/publication/main.py',args.phase]
        with (OUT/(args.phase+'.log')).open('w',encoding='utf8') as f:
            p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,cwd=ROOT);code=p.wait(timeout=3600)
        print((OUT/(args.phase+'.log')).read_text(encoding='utf8')[-4000:])
        raise SystemExit(code)
