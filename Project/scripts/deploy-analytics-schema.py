"""Apply generated DDL and inspect actual database metadata, without destructive reset."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,json,re
spec=importlib.util.spec_from_file_location('services',Path(__file__).with_name('analytics-services.py'))
svc=importlib.util.module_from_spec(spec);spec.loader.exec_module(svc)
ROOT=svc.ROOT; DDL=ROOT/'config/analytics/ddl'; OUT=ROOT/'reports/schema-deployment'
OUT.mkdir(parents=True,exist_ok=True)
m=json.loads((DDL/'manifest.json').read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for file,value in m['ddl_sha256'].items():assert sha(DDL/file)==value
assert sha(ROOT/'config/logical_model_v1_1.json')==m['logical_model_sha256']
assert sha(ROOT/'config/physical_design_v1.json')==m['physical_model_sha256'], 'Physical contract changed; regenerate and review DDL first'
def save(name,obj):(OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def oracle(sql):
    return svc.command(['docker','exec','-i',svc.container('oracle'),'sqlplus','-S','/ as sysdba'],input=sql,timeout=2400)
prefix='set echo off verify off define off feedback off heading off pagesize 0 linesize 32767 trimspool on tab off\nwhenever sqlerror exit sql.sqlcode rollback\nwhenever oserror exit failure rollback\nalter session set container=FREEPDB1;\n'
def query(sql):
    output=oracle(prefix+sql+';\nexit\n')
    return [json.loads(line.strip()[4:]) for line in output.splitlines() if line.strip().startswith('ROW:')]
def normalized(s):return re.sub(r'\s+','',s or '').replace('"','').upper()
owners="('CE_DWH_A','CE_DWH_B','CE_STAGE')"

def verify():
    principals=query("SELECT 'ROW:'||JSON_OBJECT('name' VALUE username,'authentication' VALUE authentication_type,'tablespace' VALUE default_tablespace) FROM dba_users WHERE username IN "+owners)
    assert {p['name'] for p in principals}=={'CE_DWH_A','CE_DWH_B','CE_STAGE'}
    assert all(p['authentication']=='NONE' for p in principals),'Owners must be schema-only accounts'
    columns=query("SELECT 'ROW:'||JSON_OBJECT('owner' VALUE owner,'table' VALUE table_name,'name' VALUE column_name,'position' VALUE column_id,'type' VALUE data_type,'precision' VALUE data_precision,'scale' VALUE data_scale,'char_length' VALUE char_length,'char_used' VALUE char_used,'nullable' VALUE nullable) FROM dba_tab_columns WHERE owner IN "+owners+" ORDER BY owner,table_name,column_id")
    objects=query("SELECT 'ROW:'||JSON_OBJECT('owner' VALUE owner,'name' VALUE object_name,'kind' VALUE object_type,'status' VALUE status) FROM dba_objects WHERE owner IN "+owners+" AND object_type IN ('TABLE','VIEW')")
    assert {(o['owner'].lower(),o['name'].lower(),o['kind']) for o in objects}=={(o['owner'],o['name'],o['kind']) for o in m['oracle_objects']},'Oracle object inventory drift'
    assert all(o['status']=='VALID' for o in objects),'Invalid object'
    for obj in m['oracle_objects']:
        got=[c for c in columns if c['owner'].lower()==obj['owner'] and c['table'].lower()==obj['name']]
        assert len(got)==len(obj['columns']),'Column count: '+obj['name']
        for c,w in zip(got,obj['columns']):
            assert c['name'].lower()==w['name'],'Column order/name'
            typ=w['oracle_type']
            if typ.startswith('NUMBER'):
                precision,scale=map(int,re.findall(r'\d+',typ))
                assert c['type']=='NUMBER' and (c['precision'],c['scale'])==(precision,scale),(obj['name'],w['name'])
            elif typ.startswith('VARCHAR2'):
                assert c['type']=='VARCHAR2' and c['char_length']==int(re.search(r'\d+',typ[8:]).group()) and c['char_used']=='C'
            else:assert c['type']==typ,(c,typ)
            if obj['kind']=='TABLE':assert (c['nullable']=='Y')==w['nullable'],(obj['name'],w['name'],'nullability')
    constraints=query("SELECT 'ROW:'||JSON_OBJECT('owner' VALUE owner,'name' VALUE constraint_name,'table' VALUE table_name,'kind' VALUE constraint_type,'status' VALUE status,'validated' VALUE validated,'condition' VALUE search_condition_vc,'ref_owner' VALUE r_owner,'ref_name' VALUE r_constraint_name,'delete_rule' VALUE delete_rule) FROM dba_constraints WHERE owner IN "+owners)
    keys=query("SELECT 'ROW:'||JSON_OBJECT('owner' VALUE owner,'name' VALUE constraint_name,'column' VALUE column_name,'position' VALUE position) FROM dba_cons_columns WHERE owner IN "+owners+" ORDER BY position")
    ci={(c['owner'].lower(),c['name'].lower()):c for c in constraints}
    declared={(c['owner'],c['name']) for c in m['oracle_constraints']}
    for c in constraints:
        if (c['owner'].lower(),c['name'].lower()) not in declared:
            assert c['kind']=='C' and c['name'].startswith('SYS_') and 'IS NOT NULL' in c['condition'], 'Unexpected Oracle constraint'
    for wanted in m['oracle_constraints']:
        c=ci[(wanted['owner'],wanted['name'])]
        assert c['table'].lower()==wanted['table'] and c['kind']==wanted['kind']
        assert c['status']=='ENABLED' and c['validated']=='VALIDATED'
        cols=[k['column'].lower() for k in keys if k['owner']==c['owner'] and k['name']==c['name']]
        if wanted['kind']!='C':assert cols==wanted['columns']
        else:assert normalized(c['condition'])==normalized(wanted['expression']),(c,wanted)
        if wanted['kind']=='R':
            ref=ci[(c['ref_owner'].lower(),c['ref_name'].lower())]
            target=wanted['reference']; assert ref['owner'].lower()==target['owner'] and ref['table'].lower()==target['table'] and c['delete_rule']=='NO ACTION'
            rcols=[k['column'].lower() for k in keys if k['owner']==ref['owner'] and k['name']==ref['name']]
            assert rcols==[target['column']]
    indexes=query("SELECT 'ROW:'||JSON_OBJECT('owner' VALUE owner,'name' VALUE index_name,'table' VALUE table_name,'uniqueness' VALUE uniqueness,'status' VALUE status,'tablespace' VALUE tablespace_name,'type' VALUE index_type) FROM dba_indexes WHERE owner IN "+owners)
    assert {(i['owner'].lower(),i['name'].lower()) for i in indexes}=={(i['owner'],i['name']) for i in m['oracle_indexes']}
    assert all(i['status']=='VALID' and i['uniqueness']=='UNIQUE' for i in indexes)
    for ix in m['oracle_indexes']:
        actual=next(i for i in indexes if i['owner'].lower()==ix['owner'] and i['name'].lower()==ix['name'])
        assert actual['table'].lower()==ix['table'] and actual['tablespace'].lower()==ix['tablespace']
    table_storage=query("SELECT 'ROW:'||JSON_OBJECT('owner' VALUE owner,'name' VALUE table_name,'tablespace' VALUE tablespace_name,'partitioned' VALUE partitioned,'compression' VALUE compression,'degree' VALUE TRIM(degree)) FROM dba_tables WHERE owner IN "+owners)
    for obj in m['oracle_objects']:
        if obj['kind']!='TABLE':continue
        actual=next(t for t in table_storage if t['owner'].lower()==obj['owner'] and t['name'].lower()==obj['name'])
        assert actual['tablespace'].lower()==obj['tablespace'] and actual['partitioned']=='NO' and actual['compression']=='DISABLED' and actual['degree']=='1'
    # Retrieve LONG expressions through DBMS_METADATA's generated index DDL.
    index_ddls=query("SELECT 'ROW:'||JSON_OBJECT('owner' VALUE owner,'name' VALUE index_name,'ddl' VALUE DBMS_LOB.SUBSTR(DBMS_METADATA.GET_DDL('INDEX',index_name,owner),3500,1)) FROM dba_indexes WHERE owner IN "+owners+" AND index_type='FUNCTION-BASED NORMAL'")
    index_ddl_map={(i['owner'].lower(),i['name'].lower()):i['ddl'] for i in index_ddls}
    for ix in m['oracle_indexes']:
        if not ix['function_based']:continue
        ddl=index_ddl_map[(ix['owner'],ix['name'])]
        def indexnorm(s):
            value=normalized(s).replace('(','').replace(')','')
            # Oracle stores this equivalent searched CASE as a simple CASE.
            return re.sub(r"CASEWHEN([A-Z_]+)=('NORMAL')THEN",r"CASE\1WHEN\2THEN",value)
        assert all(indexnorm(expr) in indexnorm(ddl) for expr in ix['expressions']), 'Index expression drift'
    views=query("SELECT 'ROW:'||JSON_OBJECT('owner' VALUE owner,'name' VALUE view_name,'ddl' VALUE DBMS_LOB.SUBSTR(DBMS_METADATA.GET_DDL('VIEW',view_name,owner),3500,1)) FROM dba_views WHERE owner IN "+owners)
    for obj in m['oracle_objects']:
        if obj['kind']!='VIEW':continue
        actual=next(v for v in views if v['owner'].lower()==obj['owner'] and v['name'].lower()==obj['name'])
        expected='SELECT '+','.join(c['name'] for c in obj['columns'])+' FROM '+obj['helper']
        assert normalized(expected) in normalized(actual['ddl']), 'View definition drift'
    counts=query('\nUNION ALL\n'.join(f"SELECT 'ROW:'||JSON_OBJECT('owner' VALUE '{o['owner']}','name' VALUE '{o['name']}','rows' VALUE COUNT(*)) FROM {o['owner']}.{o['name']}" for o in m['oracle_objects']))
    datafiles=query("SELECT 'ROW:'||JSON_OBJECT('tablespace' VALUE tablespace_name,'file' VALUE file_name,'bytes' VALUE bytes,'maxbytes' VALUE maxbytes,'autoextensible' VALUE autoextensible) FROM dba_data_files WHERE tablespace_name IN ('CE_DATA','CE_STAGE_DATA')")
    assert {d['tablespace']:d['maxbytes'] for d in datafiles}=={'CE_DATA':8*1024**3,'CE_STAGE_DATA':1024**3}
    report=dict(status='PASSED',checked_at=datetime.now(timezone.utc).isoformat(),manifest_sha256=sha(DDL/'manifest.json'),principals=principals,objects=objects,columns=columns,constraints=constraints,indexes=indexes,datafiles=datafiles,row_counts=counts,all_tables_empty=all(c['rows']==0 for c in counts))
    save('oracle-verification.json',report)
    print(json.dumps(dict(status='PASSED',objects=len(objects),indexes=len(indexes),declared_constraints=len(m['oracle_constraints']),all_tables_empty=report['all_tables_empty'])),flush=True)

parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['oracle','verify-oracle','iceberg']);phase=parser.parse_args().phase
if phase=='oracle':
    output=oracle((DDL/'oracle_schema.sql').read_text(encoding='utf-8'))
    (OUT/'oracle-apply.log').write_text(output,encoding='utf-8');assert 'SCHEMA_DDL_COMPLETE' in output
    print('Oracle schema DDL applied.',flush=True)
elif phase=='verify-oracle':verify()
else:
    jars=json.loads((ROOT/'reports/analytics-runtime/jars.json').read_text())['jars']
    output=svc.command(['docker','exec',svc.container('spark'),'/opt/spark/bin/spark-submit','--jars',','.join(j['file'] for j in jars),'/workspace/src/analytics_runtime/deploy_schema.py'])
    (OUT/'iceberg-apply.log').write_text(output,encoding='utf-8');print(output[-1500:])
