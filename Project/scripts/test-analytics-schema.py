"""Exercise native constraints inside a transaction and roll back all test rows.

Run after metadata verification, against empty business schemas. Also explicitly
demonstrate that overlapping SCD2 history needs the future ETL validator.
"""
from pathlib import Path
import importlib.util,json
from datetime import datetime,timezone
spec=importlib.util.spec_from_file_location('services',Path(__file__).with_name('analytics-services.py'))
svc=importlib.util.module_from_spec(spec);spec.loader.exec_module(svc)
root=svc.ROOT;out=root/'reports/schema-deployment'
m=json.loads((root/'config/analytics/ddl/manifest.json').read_text())
verified=json.loads((out/'oracle-verification.json').read_text())
assert verified['status']=='PASSED' and verified['all_tables_empty'], 'Only run fixture on verified empty schemas'
entities={e['id']:e for e in m['entities']}
def lit(s):return "'"+s.replace("'","''")+"'"
def insert(owner,entity,overrides):
    vals={}
    for c in entity['columns']:
        n=c['name'];typ=c['logical_type']
        if c['nullable'] and not c['required_for_normal_member']:value='NULL'
        elif typ in ['KEY','DATEKEY','COUNT','INT','FLAG','MONEY','QTY','VALUE']:value='1'
        elif typ=='UTC':value="TIMESTAMP '2026-01-01 00:00:00'"
        elif typ=='DATE':value="DATE '2026-01-01'"
        elif typ=='HASH':value=lit('a'*64)
        else:value=lit('SCHEMA_TEST_20261014')
        vals[n]=value
    if 'member_kind' in vals:vals['member_kind']="'NORMAL'"
    vals.update(overrides)
    return f"INSERT INTO {owner}.{entity['physical_name']} ({','.join(vals)}) VALUES ({','.join(vals.values())})"
sql="""set echo off verify off define off feedback off
set serveroutput on size unlimited
whenever sqlerror exit sql.sqlcode rollback
whenever oserror exit failure rollback
alter session set container=FREEPDB1;
set serveroutput on size unlimited
DECLARE
 n NUMBER;
 PROCEDURE rejected(stmt VARCHAR2, expected NUMBER, label VARCHAR2) IS
 BEGIN
  BEGIN EXECUTE IMMEDIATE stmt;
  EXCEPTION WHEN OTHERS THEN
   IF SQLCODE=expected THEN DBMS_OUTPUT.PUT_LINE('PASS:'||label); RETURN; ELSE RAISE; END IF;
  END;
  RAISE_APPLICATION_ERROR(-20001,'Constraint did not reject: '||label);
 END;
BEGIN
"""
expected=[]
for slot in ['a','b']:
    owner='ce_dwh_'+slot
    base={'site_key':'999999999999990001'}
    first=insert(owner,entities['D02'],base)
    sql+=' EXECUTE IMMEDIATE '+lit(first)+';\n'
    tests=[('duplicate_pk',insert(owner,entities['D02'],dict(base,site_id="'DUPLICATE_PK_ONLY'")),-1),
           ('duplicate_current',insert(owner,entities['D02'],dict(base,site_key='999999999999990002',version_no='2',valid_from_utc="TIMESTAMP '2026-02-01 00:00:00'")),-1),
           ('normal_required_attribute',insert(owner,entities['D02'],dict(base,site_key='999999999999990003',site_id="'OTHER'",site_name='NULL')),-2290),
           ('current_end_consistency',insert(owner,entities['D02'],dict(base,site_key='999999999999990004',site_id="'OTHER2'",valid_to_utc="TIMESTAMP '2026-03-01 00:00:00'")),-2290),
           ('not_null',insert(owner,entities['D02'],dict(base,site_key='999999999999990005',site_id="'OTHER3'",source_batch_id='NULL')),-1400),
           ('orphan_fk',insert(owner,entities['L01'],{'room_key':'999999999999999999','rate_plan_key':'999999999999999999'}),-2291)]
    for label,statement,code in tests:
        label=slot+'_'+label;expected.append(label)
        sql+=' rejected('+lit(statement)+','+str(code)+','+lit(label)+');\n'
    overlap=insert(owner,entities['D02'],dict(base,site_key='999999999999990006',version_no='3',is_current='0',valid_from_utc="TIMESTAMP '2025-06-01 00:00:00'",valid_to_utc="TIMESTAMP '2026-06-01 00:00:00'"))
    sql+=' EXECUTE IMMEDIATE '+lit(overlap)+';\n'
    sql+=" DBMS_OUTPUT.PUT_LINE('OBSERVED:"+slot+"_overlap_requires_pipeline');\n"
sql+=" ROLLBACK;\n"
sql+=" SELECT (SELECT COUNT(*) FROM ce_dwh_a.dim_site)+(SELECT COUNT(*) FROM ce_dwh_b.dim_site)+(SELECT COUNT(*) FROM ce_dwh_a.bridge_booking_room)+(SELECT COUNT(*) FROM ce_dwh_b.bridge_booking_room) INTO n FROM dual;\n"
sql+=" IF n<>0 THEN RAISE_APPLICATION_ERROR(-20002,'Fixture tables not empty after rollback'); END IF;\n DBMS_OUTPUT.PUT_LINE('FIXTURES_ROLLED_BACK');\nEND;\n/\nexit rollback\n"
(out/'oracle-constraint-fixtures.sql').write_text(sql,encoding='utf-8')
output=svc.command(['docker','exec','-i',svc.container('oracle'),'sqlplus','-S','/ as sysdba'],input=sql)
(out/'oracle-constraint-fixtures.log').write_text(output,encoding='utf-8')
passed=[s.removeprefix('PASS:') for s in output.splitlines() if s.startswith('PASS:')]
assert passed==expected and 'FIXTURES_ROLLED_BACK' in output, output
report=dict(status='PASSED',checked_at=datetime.now(timezone.utc).isoformat(),native_rejections=passed,
            scd_overlap_requires_pipeline=True,fixtures_rolled_back=True)
(out/'oracle-constraint-fixtures.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
